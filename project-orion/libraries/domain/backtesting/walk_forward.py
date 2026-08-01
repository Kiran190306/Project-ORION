"""Walk-forward analysis for backtesting.

Supports training window, validation window, rolling window, and
anchored window walk-forward optimization methodologies.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable

from libraries.domain.backtesting.models import WalkForwardConfig, WalkForwardResult


@dataclass(frozen=True, slots=True)
class WalkForwardWindow:
    """A single walk-forward window segment."""

    window_index: int
    train_start: date
    train_end: date
    val_start: date
    val_end: date
    is_anchored: bool = False


class WalkForwardAnalyzer:
    """Executes walk-forward analysis for strategy validation.

    Supports both rolling and anchored walk-forward methodologies.
    """

    def __init__(self, config: WalkForwardConfig | None = None) -> None:
        """Initialize walk-forward analyzer.

        Args:
            config: Walk-forward configuration.
        """
        self._config = config or WalkForwardConfig(
            training_window_days=365,
            validation_window_days=90,
            step_size_days=90,
        )
        self._windows: list[WalkForwardWindow] = []
        self._results: list[WalkForwardResult] = []

    @property
    def config(self) -> WalkForwardConfig:
        return self._config

    @property
    def windows(self) -> list[WalkForwardWindow]:
        return list(self._windows)

    def generate_windows(
        self,
        start_date: date,
        end_date: date,
    ) -> list[WalkForwardWindow]:
        """Generate walk-forward windows.

        Args:
            start_date: Overall data start date.
            end_date: Overall data end date.

        Returns:
            List of walk-forward windows.
        """
        cfg = self._config
        windows: list[WalkForwardWindow] = []
        index = 0

        window_type = getattr(cfg, "window_type", "rolling")

        if window_type == "rolling":
            current_start = start_date
            while (
                current_start
                + timedelta(days=cfg.training_window_days + cfg.validation_window_days)
                <= end_date
            ):
                train_end = current_start + timedelta(days=cfg.training_window_days)
                val_start = train_end
                val_end = min(val_start + timedelta(days=cfg.validation_window_days), end_date)

                windows.append(
                    WalkForwardWindow(
                        window_index=index,
                        train_start=current_start,
                        train_end=train_end,
                        val_start=val_start,
                        val_end=val_end,
                        is_anchored=False,
                    )
                )

                current_start += timedelta(days=cfg.step_size_days)
                index += 1

        elif window_type == "anchored":
            anchor_start = start_date
            current_start = start_date + timedelta(days=cfg.training_window_days)
            while current_start + timedelta(days=cfg.validation_window_days) <= end_date:
                train_end = current_start
                val_start = train_end
                val_end = min(val_start + timedelta(days=cfg.validation_window_days), end_date)

                windows.append(
                    WalkForwardWindow(
                        window_index=index,
                        train_start=anchor_start,
                        train_end=train_end,
                        val_start=val_start,
                        val_end=val_end,
                        is_anchored=True,
                    )
                )

                current_start += timedelta(days=cfg.step_size_days)
                index += 1

        self._windows = windows
        return windows

    async def execute(
        self,
        train_func: Callable[[date, date], Any],
        validate_func: Callable[[Any, date, date], Any],
    ) -> list[WalkForwardResult]:
        """Execute walk-forward analysis.

        Args:
            train_func: Function that trains/optimizes on a date range.
            validate_func: Function that validates on a date range.

        Returns:
            List of walk-forward results per window.
        """
        if not self._windows:
            raise ValueError("No windows generated. Call generate_windows first.")

        self._results = []

        for window in self._windows:
            # Train
            model = await train_func(window.train_start, window.train_end)

            # Validate
            metrics = await validate_func(model, window.val_start, window.val_end)


            result = WalkForwardResult(
                window_index=window.window_index,
                training_start=datetime.combine(window.train_start, datetime.min.time()).replace(
                    tzinfo=timezone.utc
                ),
                training_end=datetime.combine(window.train_end, datetime.min.time()).replace(
                    tzinfo=timezone.utc
                ),
                validation_start=datetime.combine(window.val_start, datetime.min.time()).replace(
                    tzinfo=timezone.utc
                ),
                validation_end=datetime.combine(window.val_end, datetime.min.time()).replace(
                    tzinfo=timezone.utc
                ),
                parameters=metrics if isinstance(metrics, dict) else {},
            )
            self._results.append(result)

        return self._results

    def get_summary(self) -> dict[str, Any]:
        """Get summary statistics across all windows.

        Returns:
            Summary dict with mean, std, min, max of key metrics.
        """
        if not self._results:
            return {}

        # Extract common metrics from parameters dict
        sharpe = [
            r.parameters.get("sharpe_ratio", 0)
            for r in self._results
            if "sharpe_ratio" in r.parameters
        ]
        profit = [
            r.parameters.get("net_profit", 0) for r in self._results if "net_profit" in r.parameters
        ]
        dd = [
            r.parameters.get("max_drawdown_pct", 0)
            for r in self._results
            if "max_drawdown_pct" in r.parameters
        ]

        def mean(vals: list[float]) -> float:
            return sum(vals) / len(vals) if vals else 0.0

        return {
            "window_count": len(self._results),
            "avg_sharpe_ratio": round(mean(sharpe), 4),
            "avg_net_profit": round(mean(profit), 2),
            "avg_max_drawdown_pct": round(mean(dd), 2),
            "min_sharpe": round(min(sharpe), 4) if sharpe else 0.0,
            "max_sharpe": round(max(sharpe), 4) if sharpe else 0.0,
            "std_sharpe": round(
                (
                    (sum((s - mean(sharpe)) ** 2 for s in sharpe) / len(sharpe)) ** 0.5
                    if len(sharpe) > 1
                    else 0.0
                ),
                4,
            ),
        }
