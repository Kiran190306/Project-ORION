"""Risk Profiles - configurable risk parameter sets.

Provides built-in profiles:
- Conservative: Strict limits, low risk tolerance
- Balanced: Moderate limits, standard risk management
- Aggressive: Higher limits, higher risk tolerance
- Custom: Fully configurable by the user

Each profile defines thresholds for all risk policies.
"""

from __future__ import annotations

import asyncio
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from libraries.domain.risk.exceptions import (
    ProfileNotFoundError,
    ProfileValidationError,
)
from libraries.domain.risk.models import RiskProfileType

# ─── Default Profile Configurations ────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class RiskProfileConfig:
    """Configuration parameters for a risk profile.

    All values are policy thresholds used by the RiskEngine.
    """

    # Position Sizing
    max_position_size_pct: float = 10.0  # % of account
    max_position_size_units: float = 0.0  # 0 = unlimited

    # Loss Limits
    max_daily_loss_pct: float = 5.0
    max_weekly_loss_pct: float = 10.0
    max_monthly_loss_pct: float = 20.0
    max_drawdown_pct: float = 20.0
    max_consecutive_losses: int = 5

    # Exposure
    max_total_exposure_pct: float = 50.0
    max_symbol_exposure_pct: float = 20.0
    max_currency_exposure_pct: float = 30.0

    # Leverage
    max_leverage: float = 50.0

    # Position Count
    max_open_positions: int = 10

    # Market Conditions
    max_spread_pips: float = 5.0
    max_volatility: float = 0.8
    min_liquidity_score: float = 0.3
    max_slippage_pips: float = 2.0

    # Trading Hours
    allow_weekend_trading: bool = False
    allow_holiday_trading: bool = False
    require_market_open: bool = True

    # Account Protection
    soft_stop_loss_pct: float = 10.0
    hard_stop_loss_pct: float = 20.0
    cooldown_after_loss_minutes: float = 0.0  # 0 = no cooldown
    max_daily_trades: int = 20

    # Emergency
    auto_emergency_mode: bool = True
    emergency_spread_multiplier: float = 3.0
    emergency_slippage_multiplier: float = 3.0

    # Margin
    margin_call_threshold_pct: float = 100.0  # margin level %
    min_free_margin_pct: float = 10.0

    # Compliance (future-ready)
    allowed_symbols: tuple[str, ...] = ()
    blocked_symbols: tuple[str, ...] = ()
    max_trade_frequency_seconds: float = 0.0

    @classmethod
    def conservative(cls) -> RiskProfileConfig:
        """Conservative profile - strict limits, low risk."""
        return cls(
            max_position_size_pct=5.0,
            max_daily_loss_pct=2.0,
            max_weekly_loss_pct=5.0,
            max_monthly_loss_pct=10.0,
            max_drawdown_pct=10.0,
            max_consecutive_losses=3,
            max_total_exposure_pct=30.0,
            max_symbol_exposure_pct=10.0,
            max_currency_exposure_pct=15.0,
            max_leverage=20.0,
            max_open_positions=5,
            max_spread_pips=3.0,
            max_volatility=0.5,
            min_liquidity_score=0.5,
            max_slippage_pips=1.0,
            allow_weekend_trading=False,
            allow_holiday_trading=False,
            require_market_open=True,
            soft_stop_loss_pct=5.0,
            hard_stop_loss_pct=10.0,
            cooldown_after_loss_minutes=30.0,
            max_daily_trades=5,
            margin_call_threshold_pct=150.0,
            min_free_margin_pct=20.0,
        )

    @classmethod
    def balanced(cls) -> RiskProfileConfig:
        """Balanced profile - moderate limits, standard risk."""
        return cls(
            max_position_size_pct=10.0,
            max_daily_loss_pct=5.0,
            max_weekly_loss_pct=10.0,
            max_monthly_loss_pct=20.0,
            max_drawdown_pct=20.0,
            max_consecutive_losses=5,
            max_total_exposure_pct=50.0,
            max_symbol_exposure_pct=20.0,
            max_currency_exposure_pct=30.0,
            max_leverage=50.0,
            max_open_positions=10,
            max_spread_pips=5.0,
            max_volatility=0.8,
            min_liquidity_score=0.3,
            max_slippage_pips=2.0,
            allow_weekend_trading=False,
            allow_holiday_trading=False,
            require_market_open=True,
            soft_stop_loss_pct=10.0,
            hard_stop_loss_pct=20.0,
            cooldown_after_loss_minutes=15.0,
            max_daily_trades=10,
            margin_call_threshold_pct=100.0,
            min_free_margin_pct=10.0,
        )

    @classmethod
    def aggressive(cls) -> RiskProfileConfig:
        """Aggressive profile - higher limits, higher risk tolerance."""
        return cls(
            max_position_size_pct=20.0,
            max_daily_loss_pct=10.0,
            max_weekly_loss_pct=20.0,
            max_monthly_loss_pct=40.0,
            max_drawdown_pct=35.0,
            max_consecutive_losses=8,
            max_total_exposure_pct=80.0,
            max_symbol_exposure_pct=40.0,
            max_currency_exposure_pct=50.0,
            max_leverage=100.0,
            max_open_positions=20,
            max_spread_pips=10.0,
            max_volatility=1.0,
            min_liquidity_score=0.2,
            max_slippage_pips=5.0,
            allow_weekend_trading=True,
            allow_holiday_trading=True,
            require_market_open=False,
            soft_stop_loss_pct=20.0,
            hard_stop_loss_pct=40.0,
            cooldown_after_loss_minutes=5.0,
            max_daily_trades=30,
            margin_call_threshold_pct=80.0,
            min_free_margin_pct=5.0,
        )

    @classmethod
    def custom(cls) -> RiskProfileConfig:
        """Custom profile - starts with balanced defaults, user can override."""
        return cls.balanced()

    def to_dict(self) -> dict[str, Any]:
        """Convert to a flat dictionary."""
        return {
            "max_position_size_pct": self.max_position_size_pct,
            "max_position_size_units": self.max_position_size_units,
            "max_daily_loss_pct": self.max_daily_loss_pct,
            "max_weekly_loss_pct": self.max_weekly_loss_pct,
            "max_monthly_loss_pct": self.max_monthly_loss_pct,
            "max_drawdown_pct": self.max_drawdown_pct,
            "max_consecutive_losses": self.max_consecutive_losses,
            "max_total_exposure_pct": self.max_total_exposure_pct,
            "max_symbol_exposure_pct": self.max_symbol_exposure_pct,
            "max_currency_exposure_pct": self.max_currency_exposure_pct,
            "max_leverage": self.max_leverage,
            "max_open_positions": self.max_open_positions,
            "max_spread_pips": self.max_spread_pips,
            "max_volatility": self.max_volatility,
            "min_liquidity_score": self.min_liquidity_score,
            "max_slippage_pips": self.max_slippage_pips,
            "allow_weekend_trading": self.allow_weekend_trading,
            "allow_holiday_trading": self.allow_holiday_trading,
            "require_market_open": self.require_market_open,
            "soft_stop_loss_pct": self.soft_stop_loss_pct,
            "hard_stop_loss_pct": self.hard_stop_loss_pct,
            "cooldown_after_loss_minutes": self.cooldown_after_loss_minutes,
            "max_daily_trades": self.max_daily_trades,
            "auto_emergency_mode": self.auto_emergency_mode,
            "emergency_spread_multiplier": self.emergency_spread_multiplier,
            "emergency_slippage_multiplier": self.emergency_slippage_multiplier,
            "margin_call_threshold_pct": self.margin_call_threshold_pct,
            "min_free_margin_pct": self.min_free_margin_pct,
            "allowed_symbols": self.allowed_symbols,
            "blocked_symbols": self.blocked_symbols,
            "max_trade_frequency_seconds": self.max_trade_frequency_seconds,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RiskProfileConfig:
        """Create from a dictionary (for custom profiles)."""
        valid_keys = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


# ─── Built-in Profile Mapping ──────────────────────────────────────────────

BUILTIN_PROFILES: dict[RiskProfileType, RiskProfileConfig] = {
    RiskProfileType.CONSERVATIVE: RiskProfileConfig.conservative(),
    RiskProfileType.BALANCED: RiskProfileConfig.balanced(),
    RiskProfileType.AGGRESSIVE: RiskProfileConfig.aggressive(),
    RiskProfileType.CUSTOM: RiskProfileConfig.custom(),
}


# ─── Profile Manager ───────────────────────────────────────────────────────


class RiskProfileManager:
    """Manages risk profiles.

    Supports:
    - Getting built-in profiles
    - Applying a profile to get config
    - Creating custom profiles from base + overrides
    - Validating profile configurations
    """

    def __init__(self) -> None:
        self._profiles: dict[str, RiskProfileConfig] = {
            k.value: v for k, v in BUILTIN_PROFILES.items()
        }
        self._custom_profiles: dict[str, RiskProfileConfig] = {}
        self._lock = asyncio.Lock()

    async def get_profile(
        self,
        profile_type: RiskProfileType | str,
    ) -> RiskProfileConfig:
        """Get a profile configuration.

        Args:
            profile_type: Profile type or custom profile name.

        Returns:
            RiskProfileConfig for the requested profile.

        Raises:
            ProfileNotFoundError: If profile is not found.
        """
        async with self._lock:
            key = profile_type.value if isinstance(profile_type, RiskProfileType) else profile_type

            if key in self._custom_profiles:
                return self._custom_profiles[key]

            if key in self._profiles:
                return self._profiles[key]

            # Fallback: try matching enum value
            for pt in RiskProfileType:
                if pt.value == key:
                    return self._profiles[pt.value]

            raise ProfileNotFoundError(f"Profile '{key}' not found")

    async def apply_profile(
        self,
        profile_type: RiskProfileType | str,
    ) -> RiskProfileConfig:
        """Apply a profile and return its configuration.

        This is identical to get_profile() but named for semantic clarity
        in the RiskProfilePort interface.

        Args:
            profile_type: Profile type to apply.

        Returns:
            RiskProfileConfig.
        """
        return await self.get_profile(profile_type)

    async def customize_profile(
        self,
        base: RiskProfileType,
        overrides: dict[str, Any],
        custom_name: str | None = None,
    ) -> RiskProfileConfig:
        """Create a custom profile from a base profile with overrides.

        Args:
            base: Base profile type.
            overrides: Configuration overrides.
            custom_name: Optional name for the custom profile.

        Returns:
            Customized RiskProfileConfig.

        Raises:
            ProfileValidationError: If overrides contain invalid keys or values.
        """
        base_config = await self.get_profile(base)
        base_dict = base_config.to_dict()

        # Validate overrides
        valid_keys = set(RiskProfileConfig.__dataclass_fields__.keys())
        for key in overrides:
            if key not in valid_keys:
                raise ProfileValidationError(
                    f"Unknown profile parameter '{key}'. Valid keys: {sorted(valid_keys)}"
                )

        # Validate value ranges
        numeric_range_checks = {
            "max_position_size_pct": (0, 100),
            "max_daily_loss_pct": (0, 100),
            "max_weekly_loss_pct": (0, 100),
            "max_monthly_loss_pct": (0, 100),
            "max_drawdown_pct": (0, 100),
            "max_total_exposure_pct": (0, 100),
            "max_symbol_exposure_pct": (0, 100),
            "max_currency_exposure_pct": (0, 100),
            "max_leverage": (1, 1000),
            "max_open_positions": (1, 1000),
            "max_spread_pips": (0, 100),
            "max_volatility": (0, 10),
            "min_liquidity_score": (0, 1),
            "max_slippage_pips": (0, 100),
        }

        for key, value in overrides.items():
            if key in numeric_range_checks and isinstance(value, (int, float)):
                lo, hi = numeric_range_checks[key]
                if not lo <= value <= hi:
                    raise ProfileValidationError(f"'{key}' = {value} out of range [{lo}, {hi}]")

        # Merge: base first, then overrides
        merged = {**base_dict, **overrides}
        config = RiskProfileConfig.from_dict(merged)

        # Store as custom profile if named
        if custom_name:
            async with self._lock:
                self._custom_profiles[custom_name] = config

        return config

    async def list_profiles(self) -> list[str]:
        """List all available profile names.

        Returns:
            List of profile names (built-in + custom).
        """
        async with self._lock:
            return list(self._profiles.keys()) + list(self._custom_profiles.keys())

    async def delete_custom_profile(self, name: str) -> None:
        """Delete a custom profile.

        Args:
            name: Custom profile name.

        Raises:
            ProfileNotFoundError: If profile is not found or is built-in.
        """
        async with self._lock:
            if name in self._profiles:
                raise ProfileNotFoundError(f"Cannot delete built-in profile '{name}'")
            if name not in self._custom_profiles:
                raise ProfileNotFoundError(f"Custom profile '{name}' not found")
            del self._custom_profiles[name]

    async def validate_config(self, config: RiskProfileConfig) -> list[str]:
        """Validate a profile configuration.

        Args:
            config: Profile config to validate.

        Returns:
            List of validation errors (empty if valid).
        """
        errors: list[str] = []

        if not 0 < config.max_position_size_pct <= 100:
            errors.append("max_position_size_pct must be between 0 and 100")

        if not 0 <= config.max_daily_loss_pct <= 100:
            errors.append("max_daily_loss_pct must be between 0 and 100")

        if not 0 <= config.max_consecutive_losses <= 100:
            errors.append("max_consecutive_losses must be between 0 and 100")

        if config.max_leverage < 1:
            errors.append("max_leverage must be >= 1")

        if config.max_open_positions < 1:
            errors.append("max_open_positions must be >= 1")

        if config.max_spread_pips < 0:
            errors.append("max_spread_pips must be >= 0")

        if not 0 <= config.min_liquidity_score <= 1:
            errors.append("min_liquidity_score must be between 0 and 1")

        if config.soft_stop_loss_pct > config.hard_stop_loss_pct:
            errors.append("soft_stop_loss_pct must be <= hard_stop_loss_pct")

        return errors
