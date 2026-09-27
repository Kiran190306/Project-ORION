"""Position sizing application service for Project ORION.

Wraps domain position sizers (Fixed, Risk%, ATR, Kelly, Volatility-Based)
and evaluates them against real account balances, live paper market data,
and institutional risk/margin constraints.

Operating strictly under Paper Trading ($0.00 Capital at risk).
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from libraries.domain.trading.models import (
    PositionSizingMethod,
    StrategyType,
    TradingSignal,
)
from libraries.domain.trading.position_sizer import (
    ATRPositionSizer,
    FixedPositionSizer,
    KellyPositionSizer,
    PositionSizer,
    RiskPercentPositionSizer,
    VolatilityBasedPositionSizer,
)
from libraries.domain.trading.signals import SignalDirection, SignalStrength
from libraries.infrastructure.execution.paper_execution import PaperExecutionAdapter
from libraries.infrastructure.persistence.models import AccountModel

from ..schemas import (
    PositionSizingMethodEnum,
    PositionSizingRequest,
    PositionSizingResponse,
)

logger = logging.getLogger("trading_engine.services.position_sizing")


class PositionSizingService:
    """Calculates position sizes using domain position sizers with real account context."""

    def __init__(
        self,
        account: AccountModel,
        adapter: PaperExecutionAdapter | None = None,
    ) -> None:
        self.account = account
        self.adapter = adapter

    async def calculate_size(self, request: PositionSizingRequest) -> PositionSizingResponse:
        """Calculate position sizing based on real account equity, risk, and instrument constraints."""
        symbol = request.symbol.upper().strip()
        validation_errors: list[str] = []
        warnings: list[str] = []
        constraints_applied: list[str] = []

        # 1. Resolve Account Equity and Balance
        account_balance = self.account.balance if self.account.balance > Decimal(0) else Decimal("10000.00")
        account_equity = self.account.equity if self.account.equity > Decimal(0) else account_balance
        leverage = Decimal(str(self.account.leverage or 100))
        available_margin = max(account_equity - (self.account.margin or Decimal(0)), Decimal(0))
        if available_margin == Decimal(0) and account_equity > Decimal(0):
            available_margin = account_equity

        # 2. Resolve Market Price & Status
        entry_price = request.entry_price
        market_data_status = "REALTIME"

        if entry_price is None:
            if self.adapter and hasattr(self.adapter, "_get_quote"):
                try:
                    bid, ask, _ = self.adapter._get_quote(symbol)
                    entry_price = (bid + ask) / Decimal(2)
                except Exception as quote_err:  # noqa: BLE001
                    logger.debug("Live quote lookup error for %s: %s", symbol, quote_err)
                    entry_price = None

            if entry_price is None:
                # Check for standard EUR/USD or common pair fallbacks
                fallback_prices = {
                    "EUR/USD": Decimal("1.08500"),
                    "GBP/USD": Decimal("1.26500"),
                    "USD/JPY": Decimal("151.200"),
                    "AUD/USD": Decimal("0.65500"),
                    "USD/CHF": Decimal("0.88500"),
                    "USD/CAD": Decimal("1.35500"),
                    "NZD/USD": Decimal("0.60500"),
                }
                if symbol in fallback_prices:
                    entry_price = fallback_prices[symbol]
                    market_data_status = "FALLBACK"
                    warnings.append(
                        f"Live market quote unavailable for {symbol}; used fallback reference price {entry_price:.5f}."
                    )
                else:
                    market_data_status = "UNAVAILABLE"
                    validation_errors.append(
                        f"Current market price unavailable for {symbol}. Please specify entry_price explicitly."
                    )
                    return PositionSizingResponse(
                        symbol=symbol,
                        method=request.method.value,
                        account_balance=account_balance,
                        account_equity=account_equity,
                        requested_risk_pct=request.risk_percent,
                        confidence=request.confidence,
                        entry_price=Decimal(0),
                        calculated_units=Decimal(0),
                        notional_value=Decimal(0),
                        monetary_risk=Decimal(0),
                        account_risk_pct=0.0,
                        required_margin=Decimal(0),
                        available_margin=available_margin,
                        market_data_status=market_data_status,
                        constraints_applied=constraints_applied,
                        warnings=warnings,
                        is_valid=False,
                        validation_errors=validation_errors,
                    )

        # 3. Validate Stop Loss and Stop Distance
        stop_distance: Decimal | None = None
        if request.stop_loss is not None:
            if request.stop_loss == entry_price:
                validation_errors.append(
                    "Stop loss price cannot be identical to entry price (zero stop distance)."
                )
            else:
                stop_distance = abs(entry_price - request.stop_loss)

        if request.method == PositionSizingMethodEnum.ATR:
            if request.atr is None or request.atr <= Decimal(0):
                validation_errors.append(
                    "ATR sizing method requires a positive 'atr' input value."
                )
            else:
                stop_distance = request.atr * Decimal(str(request.atr_multiplier))

        if validation_errors:
            return PositionSizingResponse(
                symbol=symbol,
                method=request.method.value,
                account_balance=account_balance,
                account_equity=account_equity,
                requested_risk_pct=request.risk_percent,
                confidence=request.confidence,
                entry_price=entry_price,
                stop_loss=request.stop_loss,
                stop_distance=stop_distance,
                calculated_units=Decimal(0),
                notional_value=Decimal(0),
                monetary_risk=Decimal(0),
                account_risk_pct=0.0,
                required_margin=Decimal(0),
                available_margin=available_margin,
                market_data_status=market_data_status,
                constraints_applied=constraints_applied,
                warnings=warnings,
                is_valid=False,
                validation_errors=validation_errors,
            )

        # 4. Instantiate Selected Domain Sizer
        sizer: PositionSizer
        if request.method == PositionSizingMethodEnum.FIXED:
            fixed_notional = request.fixed_notional or Decimal("10000.00")
            sizer = FixedPositionSizer(fixed_notional=fixed_notional)
        elif request.method == PositionSizingMethodEnum.ATR:
            sizer = ATRPositionSizer(
                atr_multiplier=request.atr_multiplier,
                risk_percent=request.risk_percent,
            )
        elif request.method == PositionSizingMethodEnum.KELLY:
            sizer = KellyPositionSizer(
                kelly_fraction=request.kelly_fraction,
                max_risk_percent=request.risk_percent,
            )
        elif request.method == PositionSizingMethodEnum.VOLATILITY_BASED:
            vol = request.volatility if request.volatility > 0 else 0.2
            base_notional = request.fixed_notional or Decimal("10000.00")
            sizer = VolatilityBasedPositionSizer(
                base_notional=base_notional,
                max_volatility=1.0,
            )
        else:  # RISK_PERCENT default
            sizer = RiskPercentPositionSizer(risk_percent=request.risk_percent)

        signal = TradingSignal(
            direction=SignalDirection.BUY,
            strength=SignalStrength.STRONG,
            strategy=StrategyType.SWING,
            symbol=symbol,
            confidence_score=request.confidence,
        )

        vol_val = request.volatility if request.volatility > 0 else 0.15
        sizing_result = await sizer.calculate(
            signal=signal,
            account_balance=account_equity,
            confidence=request.confidence,
            entry_price=entry_price,
            stop_loss=request.stop_loss,
            atr=request.atr,
            volatility=vol_val,
        )

        # 5. Apply Broker / Account Margin Constraints
        max_allowed_units = ((available_margin * leverage) / entry_price).quantize(Decimal("0.0001"))
        calculated_units = sizing_result.units

        if calculated_units > max_allowed_units and max_allowed_units > Decimal(0):
            constraints_applied.append(
                f"Position units capped by account available margin from {calculated_units} to {max_allowed_units} units."
            )
            calculated_units = max_allowed_units

        # Enforce minimum size of 1 unit
        if calculated_units < Decimal(1):
            calculated_units = Decimal(1)
            constraints_applied.append("Minimum position size constraint applied (1.0000 unit).")

        notional_value = (calculated_units * entry_price).quantize(Decimal("0.01"))
        required_margin = (notional_value / leverage).quantize(Decimal("0.01"))

        if required_margin > available_margin:
            warnings.append(
                f"Required margin ({required_margin:.2f}) exceeds free margin ({available_margin:.2f}). Trade may fail pre-trade margin check."
            )

        # Calculate actual monetary risk based on stop distance or calculated risk amount
        if stop_distance is not None and stop_distance > Decimal(0):
            monetary_risk = (calculated_units * stop_distance).quantize(Decimal("0.01"))
        else:
            monetary_risk = sizing_result.risk_amount

        account_risk_pct = (
            float((monetary_risk / account_equity) * Decimal(100))
            if account_equity > Decimal(0)
            else 0.0
        )

        return PositionSizingResponse(
            symbol=symbol,
            method=request.method.value,
            account_balance=account_balance,
            account_equity=account_equity,
            requested_risk_pct=request.risk_percent,
            confidence=request.confidence,
            entry_price=entry_price,
            stop_loss=request.stop_loss,
            stop_distance=stop_distance,
            calculated_units=calculated_units,
            notional_value=notional_value,
            monetary_risk=monetary_risk,
            account_risk_pct=round(account_risk_pct, 4),
            required_margin=required_margin,
            available_margin=available_margin,
            max_allowed_units=max_allowed_units,
            market_data_status=market_data_status,
            constraints_applied=constraints_applied,
            warnings=warnings,
            is_valid=True,
            validation_errors=[],
        )
