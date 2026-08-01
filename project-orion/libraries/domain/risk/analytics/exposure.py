"""Portfolio exposure analytics engine.

Computes gross/net/long/short exposure, sector exposure, asset
allocation weights, risk budgeting, and concentration metrics.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from libraries.domain.risk.analytics.models import (
    ConcentrationMetrics,
    ExposureMetrics,
    PositionExposure,
)
from libraries.domain.risk.analytics.validation import InvalidValueError


class ExposureEngine:
    """Computes portfolio exposure and allocation analytics."""

    async def calculate(
        self,
        positions: Sequence[PositionExposure],
        portfolio_equity: Decimal,
    ) -> ExposureMetrics:
        """Compute portfolio exposure analytics.

        Args:
            positions: Portfolio positions.
            portfolio_equity: Current portfolio equity.

        Returns:
            An ExposureMetrics result.

        Raises:
            InvalidValueError: If equity is non-positive or positions
                reference invalid quantities.
        """
        if portfolio_equity is None or portfolio_equity <= 0:
            raise InvalidValueError("portfolio_equity must be a positive Decimal")

        if not positions:
            return ExposureMetrics(
                gross_exposure=Decimal(0),
                net_exposure=Decimal(0),
                long_exposure=Decimal(0),
                short_exposure=Decimal(0),
                portfolio_equity=portfolio_equity,
                gross_exposure_pct=0.0,
                net_exposure_pct=0.0,
                long_exposure_pct=0.0,
                short_exposure_pct=0.0,
                sector_exposure={},
                asset_allocation={},
                risk_budget={},
                concentration=ConcentrationMetrics(
                    hhi=0.0,
                    effective_positions=0.0,
                    top_holding_pct=0.0,
                    top_n_concentration=0.0,
                    position_count=0,
                ),
            )

        long_exposure = Decimal(0)
        short_exposure = Decimal(0)
        gross_exposure = Decimal(0)
        sector_exposure: dict[str, Decimal] = {}
        symbol_notional: dict[str, Decimal] = {}
        risk_weights: dict[str, float] = {}

        for position in positions:
            market_value = position.market_value
            if market_value is None or market_value <= 0:
                raise InvalidValueError(
                    f"position {position.symbol} market_value must be positive"
                )
            side = position.side.lower()
            gross_exposure += market_value
            if side == "short":
                short_exposure += market_value
            else:
                long_exposure += market_value

            if position.sector:
                sector_exposure[position.sector] = (
                    sector_exposure.get(position.sector, Decimal(0)) + market_value
                )

            symbol_notional[position.symbol] = (
                symbol_notional.get(position.symbol, Decimal(0)) + market_value
            )
            risk_weights[position.symbol] = position.risk_weight

        net_exposure = long_exposure - short_exposure

        equity = portfolio_equity
        gross_pct = float(gross_exposure / equity * 100)
        net_pct = float(net_exposure / equity * 100)
        long_pct = float(long_exposure / equity * 100)
        short_pct = float(short_exposure / equity * 100)

        # Asset allocation weights (by market value).
        total_notional = sum(symbol_notional.values(), Decimal(0))
        asset_allocation: dict[str, float] = {}
        if total_notional > 0:
            for symbol, notional in symbol_notional.items():
                asset_allocation[symbol] = round(
                    float(notional / total_notional), 6
                )

        # Risk budget (normalize risk weights to sum to 1).
        risk_budget: dict[str, float] = {}
        total_risk = sum(risk_weights.values())
        if total_risk > 0:
            for symbol, weight in risk_weights.items():
                risk_budget[symbol] = round(weight / total_risk, 6)

        # Concentration from allocation weights.
        weights = list(asset_allocation.values())
        concentration = self._concentration(weights, top_n=3)

        return ExposureMetrics(
            gross_exposure=gross_exposure,
            net_exposure=net_exposure,
            long_exposure=long_exposure,
            short_exposure=short_exposure,
            portfolio_equity=equity,
            gross_exposure_pct=round(gross_pct, 4),
            net_exposure_pct=round(net_pct, 4),
            long_exposure_pct=round(long_pct, 4),
            short_exposure_pct=round(short_pct, 4),
            sector_exposure=sector_exposure,
            asset_allocation=asset_allocation,
            risk_budget=risk_budget,
            concentration=concentration,
        )

    @staticmethod
    def _concentration(
        weights: list[float],
        top_n: int,
    ) -> ConcentrationMetrics:
        """Compute HHI and top-N concentration metrics."""
        n = len(weights)
        if n == 0:
            return ConcentrationMetrics(
                hhi=0.0,
                effective_positions=0.0,
                top_holding_pct=0.0,
                top_n_concentration=0.0,
                position_count=0,
                top_n=top_n,
            )

        hhi = sum(w * w for w in weights)
        effective = 1.0 / hhi if hhi > 0 else 0.0
        sorted_weights = sorted(weights, reverse=True)
        top_holding = sorted_weights[0] if sorted_weights else 0.0
        k = min(top_n, n)
        top_n_sum = sum(sorted_weights[:k]) if k > 0 else 0.0

        return ConcentrationMetrics(
            hhi=round(hhi, 6),
            effective_positions=round(effective, 6),
            top_holding_pct=round(top_holding * 100.0, 4),
            top_n_concentration=round(top_n_sum * 100.0, 4),
            position_count=n,
            top_n=k,
        )

