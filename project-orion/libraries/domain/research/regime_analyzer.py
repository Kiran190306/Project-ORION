"""Market regime segmentation and strategy robustness analyzer."""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from libraries.domain.research.optimization_models import RegimePerformanceBreakdown

logger = logging.getLogger("research.regime_analyzer")


class RegimeAnalyzer:
    """Classifies market conditions and partitions strategy performance across market regimes."""

    @staticmethod
    def classify_candles(candles: list[dict[str, Any]]) -> dict[int, str]:
        """Classify each candle index into an institutional market regime deterministically."""
        if len(candles) < 20:
            return {i: "UNKNOWN" for i in range(len(candles))}

        closes = [float(c["close"]) for c in candles]
        highs = [float(c["high"]) for c in candles]
        lows = [float(c["low"]) for c in candles]

        # Calculate ATRs
        atrs: list[float] = [0.0] * len(candles)
        for i in range(1, len(candles)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
            if i < 14:
                atrs[i] = tr
            else:
                atrs[i] = (atrs[i - 1] * 13 + tr) / 14

        median_atr = sorted(atrs[14:])[len(atrs[14:]) // 2] if len(atrs) > 14 else 0.001

        regimes: dict[int, str] = {}
        for i in range(len(candles)):
            if i < 20:
                regimes[i] = "RANGING_LOW_VOL"
                continue

            sma20 = sum(closes[i - 20 : i]) / 20.0
            price = closes[i]
            atr = atrs[i]
            slope = (sma20 - (sum(closes[max(0, i - 25) : i - 5]) / 20.0)) / max(0.0001, sma20)

            is_high_vol = atr > (median_atr * 1.35)

            if is_high_vol and abs(slope) < 0.0005:
                regimes[i] = "HIGH_VOLATILITY_CHOP"
            elif slope > 0.0008 and price > sma20:
                regimes[i] = "TRENDING_BULL"
            elif slope < -0.0008 and price < sma20:
                regimes[i] = "TRENDING_BEAR"
            else:
                regimes[i] = "RANGING_LOW_VOL"

        return regimes

    @classmethod
    def analyze_regimes(
        cls,
        candles: list[dict[str, Any]],
        trades: list[Any],
        initial_capital: Decimal = Decimal("10000.00"),
    ) -> tuple[RegimePerformanceBreakdown, ...]:
        """Attribute trade performance to historical market regimes."""
        if not candles:
            return ()

        regimes_by_index = cls.classify_candles(candles)
        time_to_regime = {candles[i]["timestamp"]: regimes_by_index[i] for i in range(len(candles))}

        all_regimes = ["TRENDING_BULL", "TRENDING_BEAR", "RANGING_LOW_VOL", "HIGH_VOLATILITY_CHOP"]
        trades_by_regime: dict[str, list[Any]] = {r: [] for r in all_regimes}

        for trade in trades:
            entry_time = getattr(trade, "entry_time", None) or getattr(trade, "entry_timestamp", None)
            if not entry_time and isinstance(trade, dict):
                entry_time = trade.get("entry_time") or trade.get("entry_timestamp")

            regime = time_to_regime.get(entry_time, "RANGING_LOW_VOL") if entry_time else "RANGING_LOW_VOL"
            if regime not in trades_by_regime:
                trades_by_regime[regime] = []
            trades_by_regime[regime].append(trade)

        breakdowns: list[RegimePerformanceBreakdown] = []
        for r_name in all_regimes:
            r_trades = trades_by_regime[r_name]
            count = len(r_trades)

            if count == 0:
                breakdowns.append(
                    RegimePerformanceBreakdown(
                        regime_name=r_name,
                        trade_count=0,
                        win_rate=0.0,
                        profit_factor=0.0,
                        total_return=Decimal("0.0"),
                        sharpe_ratio=0.0,
                        drawdown=0.0,
                    )
                )
                continue

            pnls: list[Decimal] = []
            for t in r_trades:
                pnl = getattr(t, "net_pnl", None) or getattr(t, "realized_pnl", None) or getattr(t, "pnl", None)
                if pnl is None and isinstance(t, dict):
                    pnl = t.get("net_pnl") or t.get("realized_pnl") or t.get("pnl", 0.0)
                pnls.append(Decimal(str(pnl)))

            wins = [p for p in pnls if p > 0]
            losses = [p for p in pnls if p < 0]

            win_rate = round(len(wins) / count, 4)
            gross_win = sum(wins, Decimal("0.0"))
            gross_loss = abs(sum(losses, Decimal("0.0")))

            if gross_loss > 0:
                profit_factor = float(round(gross_win / gross_loss, 2))
            else:
                profit_factor = 10.0 if gross_win > 0 else 0.0

            net_pnl = sum(pnls, Decimal("0.0"))
            ret_pct = round((net_pnl / initial_capital) * Decimal("100.0"), 2)

            float_pnls = [float(p) for p in pnls]
            if len(float_pnls) > 3:
                mean_pnl = sum(float_pnls) / len(float_pnls)
                variance = sum((x - mean_pnl) ** 2 for x in float_pnls) / (len(float_pnls) - 1)
                std_pnl = variance ** 0.5
                sharpe = round((mean_pnl / std_pnl) * (count ** 0.5), 2) if std_pnl > 0.0001 else 0.0
            else:
                sharpe = 0.0

            max_loss = min(float_pnls) if float_pnls else 0.0
            dd = round(abs(min(0.0, max_loss / float(initial_capital) * 100.0)), 2)

            breakdowns.append(
                RegimePerformanceBreakdown(
                    regime_name=r_name,
                    trade_count=count,
                    win_rate=win_rate,
                    profit_factor=profit_factor,
                    total_return=ret_pct,
                    sharpe_ratio=sharpe,
                    drawdown=dd,
                )
            )

        return tuple(breakdowns)
