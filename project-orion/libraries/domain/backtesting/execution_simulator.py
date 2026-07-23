"""Execution simulator for backtesting.

Simulates order execution including market, limit, and stop orders
with configurable slippage, spread, commission, swap, latency,
liquidity constraints, and market impact.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from libraries.domain.backtesting.commission_model import CommissionModel, CommissionModelConfig
from libraries.domain.backtesting.latency_model import LatencyModel, LatencyModelConfig
from libraries.domain.backtesting.liquidity_model import LiquidityModel, LiquidityModelConfig
from libraries.domain.backtesting.market_impact_model import (
    MarketImpactModel,
    MarketImpactModelConfig,
)
from libraries.domain.backtesting.models import (
    ExecutionSimulationResult,
    ExecutionSimulationStatus,
    FillSimulation,
    OrderSimulation,
    OrderSimulationSide,
    OrderSimulationStatus,
    OrderSimulationType,
)
from libraries.domain.backtesting.slippage_model import SlippageModel, SlippageModelConfig
from libraries.domain.backtesting.spread_model import SpreadModel, SpreadModelConfig
from libraries.domain.backtesting.swap_model import SwapModel, SwapModelConfig


@dataclass(frozen=True, slots=True)
class ExecutionSimulationConfig:
    """Configuration for the execution simulator."""

    slippage_config: SlippageModelConfig = field(default_factory=SlippageModelConfig)
    spread_config: SpreadModelConfig = field(default_factory=SpreadModelConfig)
    commission_config: CommissionModelConfig = field(default_factory=CommissionModelConfig)
    swap_config: SwapModelConfig = field(default_factory=SwapModelConfig)
    latency_config: LatencyModelConfig = field(default_factory=LatencyModelConfig)
    liquidity_config: LiquidityModelConfig = field(default_factory=LiquidityModelConfig)
    market_impact_config: MarketImpactModelConfig = field(default_factory=MarketImpactModelConfig)
    allow_partial_fills: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


class ExecutionSimulator:
    """Simulates order execution for backtesting.

    Integrates all market models for realistic execution simulation.
    """

    def __init__(
        self,
        config: ExecutionSimulationConfig | None = None,
    ) -> None:
        """Initialize execution simulator.

        Args:
            config: Execution simulation configuration.
        """
        cfg = config or ExecutionSimulationConfig()
        self._config = cfg
        self._slippage = SlippageModel(cfg.slippage_config)
        self._spread = SpreadModel(cfg.spread_config)
        self._commission = CommissionModel(cfg.commission_config)
        self._swap = SwapModel(cfg.swap_config)
        self._latency = LatencyModel(cfg.latency_config)
        self._liquidity = LiquidityModel(cfg.liquidity_config)
        self._market_impact = MarketImpactModel(cfg.market_impact_config)

    @property
    def config(self) -> ExecutionSimulationConfig:
        return self._config

    async def execute_order(
        self,
        order: OrderSimulation,
        bid: Decimal,
        ask: Decimal,
        volatility: float = 0.0,
        liquidity_score: float = 0.8,
        average_daily_volume: Decimal = Decimal("100000"),
        timestamp: datetime | None = None,
    ) -> ExecutionSimulationResult:
        """Execute a simulated order.

        Args:
            order: Order to simulate.
            bid: Current bid price.
            ask: Current ask price.
            volatility: Current volatility measure.
            liquidity_score: Current liquidity score (0-1).
            average_daily_volume: Average daily volume.
            timestamp: Current timestamp.

        Returns:
            Execution simulation result.
        """
        ts = timestamp or datetime.now(timezone.utc)
        spread_pips = await self._spread.calculate_spread_pips(
            volatility=volatility,
        )

        # Check liquidity
        if not self._liquidity.is_executable(order.quantity):
            return ExecutionSimulationResult(
                order=order,
                status=ExecutionSimulationStatus.FAILURE,
                rejection_reason="Insufficient liquidity",
                timestamp=ts,
            )

        # Calculate execution price
        execution_price = self._calculate_execution_price(
            order, bid, ask, spread_pips, volatility, liquidity_score, average_daily_volume
        )

        # Calculate latency
        latency_ms = self._latency.calculate_latency_ms(
            order.order_type.value, float(order.quantity)
        )

        # Calculate commission
        commission = self._commission.calculate(order.quantity, execution_price)

        # Calculate slippage
        slippage_bps = self._slippage.calculate(
            order.quantity,
            spread_pips,
            volatility,
            liquidity_score,
            order.order_type == OrderSimulationType.MARKET,
        )

        # Build fill simulation
        fill_id = str(uuid.uuid4())
        fill = FillSimulation(
            fill_id=fill_id,
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=execution_price,
            commission=commission,
            slippage=Decimal(str(slippage_bps / 10000.0)),
            timestamp=ts,
        )

        # Simulate fill
        fill_quantity = order.quantity

        return ExecutionSimulationResult(
            order=order,
            status=ExecutionSimulationStatus.SUCCESS,
            fills=(fill,),
            total_quantity=fill_quantity,
            average_price=execution_price,
            total_commission=commission,
            total_slippage=Decimal(str(slippage_bps / 10000.0)),
            latency_ms=latency_ms,
            timestamp=ts,
        )

    def _calculate_execution_price(
        self,
        order: OrderSimulation,
        bid: Decimal,
        ask: Decimal,
        spread_pips: float,
        volatility: float,
        liquidity_score: float,
        average_daily_volume: Decimal,
    ) -> Decimal:
        """Calculate execution price based on order type and market conditions.

        Args:
            order: The order to execute.
            bid: Current bid.
            ask: Current ask.
            spread_pips: Current spread in pips.
            volatility: Current volatility.
            liquidity_score: Liquidity score.
            average_daily_volume: Average daily volume.

        Returns:
            Execution price.
        """
        if order.order_type == OrderSimulationType.MARKET:
            price = ask if order.side == OrderSimulationSide.BUY else bid
            # Apply slippage
            slippage_price = self._slippage.calculate_slippage_price(
                price, order.side.value, order.quantity, spread_pips, volatility, liquidity_score
            )
            return slippage_price

        elif order.order_type == OrderSimulationType.LIMIT:
            return order.price or (ask if order.side == OrderSimulationSide.BUY else bid)

        elif order.order_type == OrderSimulationType.STOP:
            return order.price or (bid if order.side == OrderSimulationSide.BUY else ask)

        return ask if order.side == OrderSimulationSide.BUY else bid
