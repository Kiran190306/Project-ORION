"""Tests for EPIC-011 ResearchFeatureEngineer."""

from __future__ import annotations

import pytest

from libraries.domain.ai_research.exceptions import FeatureEngineeringError
from libraries.domain.ai_research.feature_engineering import ResearchFeatureEngineer
from libraries.domain.ai_research.models import FeatureDefinition, ResearchDataset


class TestResearchFeatureEngineer:
    """Test ResearchFeatureEngineer."""

    @pytest.fixture
    def engineer(self):
        return ResearchFeatureEngineer()

    @pytest.fixture
    def sample_dataset(self):
        from datetime import datetime, timezone

        ts = datetime.now(timezone.utc)
        return ResearchDataset(
            dataset_id="test",
            schema=("open", "high", "low", "close", "volume", "timestamp"),
            rows=(
                {
                    "open": 1.0,
                    "high": 1.1,
                    "low": 0.9,
                    "close": 1.05,
                    "volume": 1000,
                    "timestamp": ts,
                },
                {
                    "open": 1.05,
                    "high": 1.15,
                    "low": 0.95,
                    "close": 1.1,
                    "volume": 1200,
                    "timestamp": ts,
                },
                {
                    "open": 1.1,
                    "high": 1.2,
                    "low": 1.0,
                    "close": 1.15,
                    "volume": 900,
                    "timestamp": ts,
                },
            ),
        )

    @pytest.mark.asyncio
    async def test_empty_definitions_returns_empty(self, engineer, sample_dataset):
        result = await engineer.engineer(sample_dataset, [])
        assert result == ()

    @pytest.mark.asyncio
    async def test_sma_feature(self, engineer, sample_dataset):
        fd = FeatureDefinition(name="sma", category="trend", parameters={"period": 2})
        result = await engineer.engineer(sample_dataset, [fd])
        assert len(result) == 3
        # SMA(2): [1.05/1=1.05, (1.05+1.1)/2=1.075, (1.1+1.15)/2=1.125]
        assert result[0].values["sma"] == pytest.approx(1.05)
        assert result[1].values["sma"] == pytest.approx(1.075)
        assert result[2].values["sma"] == pytest.approx(1.125)

    @pytest.mark.asyncio
    async def test_ema_feature(self, engineer, sample_dataset):
        fd = FeatureDefinition(name="ema", category="trend", parameters={"period": 3})
        result = await engineer.engineer(sample_dataset, [fd])
        assert len(result) == 3
        # EMA(3): multiplier=2/(3+1)=0.5
        # [1.05, 1.05*0.5 + 1.05*0.5=1.05, 1.15*0.5+1.05*0.5=1.1]
        assert result[0].values["ema"] == pytest.approx(1.05)
        assert result[1].values["ema"] == pytest.approx(1.075)
        assert result[2].values["ema"] == pytest.approx(1.1125)

    @pytest.mark.asyncio
    async def test_rsi_feature(self, engineer, sample_dataset):
        fd = FeatureDefinition(name="rsi", category="momentum", parameters={"period": 2})
        result = await engineer.engineer(sample_dataset, [fd])
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_atr_feature(self, engineer, sample_dataset):
        fd = FeatureDefinition(name="atr", category="volatility", parameters={"period": 2})
        result = await engineer.engineer(sample_dataset, [fd])
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_macd_feature(self, engineer, sample_dataset):
        fd = FeatureDefinition(name="macd", category="momentum", parameters={"fast": 2, "slow": 3})
        result = await engineer.engineer(sample_dataset, [fd])
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_bollinger_feature(self, engineer, sample_dataset):
        fd = FeatureDefinition(
            name="bollinger", category="volatility", parameters={"period": 2, "stddev": 2.0}
        )
        result = await engineer.engineer(sample_dataset, [fd])
        assert len(result) == 3
        # bollinger width = 2*stddev*std/mean
        # window [1.05]: std=0, width=0
        # window [1.05, 1.1]: mean=1.075, dev from mean = 0.025^2+0.025^2=0.00125, var=0.000625, std=0.025, width=2*2*0.025/1.075≈0.093
        assert result[0].values["bollinger"] == pytest.approx(0.0)
        assert result[1].values["bollinger"] == pytest.approx(0.093023, abs=1e-5)

    @pytest.mark.asyncio
    async def test_missing_columns_raises_error(self, engineer, sample_dataset):
        fd = FeatureDefinition(name="test", category="trend", required_columns=("nonexistent",))
        with pytest.raises(FeatureEngineeringError, match="missing columns"):
            await engineer.engineer(sample_dataset, [fd])

    @pytest.mark.asyncio
    async def test_liquidity_category(self, engineer, sample_dataset):
        fd = FeatureDefinition(name="liq", category="liquidity")
        result = await engineer.engineer(sample_dataset, [fd])
        assert len(result) == 3
        assert result[0].values["liq"] == 1000.0

    @pytest.mark.asyncio
    async def test_invalid_period_raises_error(self, engineer, sample_dataset):
        fd = FeatureDefinition(name="sma", category="trend", parameters={"period": 0})
        with pytest.raises(FeatureEngineeringError, match="period"):
            await engineer.engineer(sample_dataset, [fd])

    @pytest.mark.asyncio
    async def test_custom_feature(self, engineer, sample_dataset):
        def my_feature(dataset, definition):
            return [row["close"] * 2 for row in dataset.rows]

        engineer.register_custom("double_close", my_feature)
        fd = FeatureDefinition(name="double_close", category="custom")
        result = await engineer.engineer(sample_dataset, [fd])
        assert len(result) == 3
        assert result[0].values["double_close"] == pytest.approx(2.1)

    @pytest.mark.asyncio
    async def test_custom_feature_no_implementation_raises_error(self, engineer, sample_dataset):
        fd = FeatureDefinition(name="unregistered", category="custom", required_columns=("close",))
        with pytest.raises(FeatureEngineeringError, match="no implementation"):
            await engineer.engineer(sample_dataset, [fd])

    @pytest.mark.asyncio
    async def test_register_custom_invalid_name(self, engineer):
        with pytest.raises(FeatureEngineeringError, match="name"):
            engineer.register_custom("", lambda d, f: [])

    @pytest.mark.asyncio
    async def test_register_custom_invalid_callable(self, engineer):
        with pytest.raises(FeatureEngineeringError, match="name"):
            engineer.register_custom("test", None)  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_trend_category(self, engineer, sample_dataset):
        fd = FeatureDefinition(name="sma_20", category="trend")
        result = await engineer.engineer(sample_dataset, [fd])
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_momentum_category(self, engineer, sample_dataset):
        fd = FeatureDefinition(name="momentum", category="momentum", parameters={"period": 2})
        result = await engineer.engineer(sample_dataset, [fd])
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_volatility_category(self, engineer, sample_dataset):
        fd = FeatureDefinition(name="std", category="volatility", parameters={"period": 2})
        result = await engineer.engineer(sample_dataset, [fd])
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_price_action_category(self, engineer, sample_dataset):
        fd = FeatureDefinition(name="return", category="price_action")
        result = await engineer.engineer(sample_dataset, [fd])
        assert len(result) == 3
        assert result[0].values["return"] == pytest.approx(0.0)
        assert result[1].values["return"] == pytest.approx(0.05)

    @pytest.mark.asyncio
    async def test_candlestick_body(self, engineer, sample_dataset):
        fd = FeatureDefinition(name="body", category="candlestick")
        result = await engineer.engineer(sample_dataset, [fd])
        assert len(result) == 3
        assert result[0].values["body"] == pytest.approx(0.05)
        assert result[1].values["body"] == pytest.approx(0.05)

    @pytest.mark.asyncio
    async def test_volume_category(self, engineer, sample_dataset):
        fd = FeatureDefinition(name="volume_change", category="volume")
        result = await engineer.engineer(sample_dataset, [fd])
        assert len(result) == 3
        assert result[0].values["volume_change"] == pytest.approx(0.0)

    @pytest.mark.asyncio
    async def test_multiple_features(self, engineer, sample_dataset):
        fds = [
            FeatureDefinition(name="sma", category="trend", parameters={"period": 2}),
            FeatureDefinition(name="rsi", category="momentum", parameters={"period": 2}),
        ]
        result = await engineer.engineer(sample_dataset, fds)
        assert len(result) == 3
        assert "sma" in result[0].values
        assert "rsi" in result[0].values
