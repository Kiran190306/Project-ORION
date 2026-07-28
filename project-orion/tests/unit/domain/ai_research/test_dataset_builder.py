"""Tests for EPIC-011 ResearchDatasetBuilder."""

from __future__ import annotations

import pytest

from libraries.domain.ai_research.dataset_builder import ResearchDatasetBuilder
from libraries.domain.ai_research.exceptions import DatasetError
from libraries.domain.ai_research.models import ResearchDataset


class TestResearchDatasetBuilder:
    """Test ResearchDatasetBuilder."""

    @pytest.fixture
    def builder(self):
        return ResearchDatasetBuilder()

    @pytest.mark.asyncio
    async def test_build_valid_dataset(self, builder):
        rows = [
            {"close": 1.0, "volume": 100},
            {"close": 1.1, "volume": 150},
        ]
        ds = await builder.build("test-ds", rows)
        assert isinstance(ds, ResearchDataset)
        assert ds.dataset_id == "test-ds"
        assert ds.row_count == 2
        assert "close" in ds.schema
        assert "volume" in ds.schema

    @pytest.mark.asyncio
    async def test_build_empty_rows_raises_error(self, builder):
        with pytest.raises(DatasetError, match="cannot build"):
            await builder.build("test-ds", [])

    @pytest.mark.asyncio
    async def test_build_with_empty_schema(self, builder):
        with pytest.raises(DatasetError, match="schema"):
            await builder.build("test-ds", [{}])

    @pytest.mark.asyncio
    async def test_build_includes_statistics(self, builder):
        rows = [
            {"close": 1.0, "volume": 100},
            {"close": 2.0, "volume": None},
        ]
        ds = await builder.build("test-ds", rows)
        stats = ds.metadata.get("statistics", {})
        assert stats["row_count"] == 2
        assert stats["column_count"] == 2
        assert stats["null_counts"]["volume"] == 1

    def test_validate_schema_valid(self, builder):
        ds = ResearchDataset(
            dataset_id="test",
            schema=("close", "volume"),
            rows=({"close": 1.0, "volume": 100},),
        )
        builder.validate_schema(ds, ("close",))
        builder.validate_schema(ds, ("close", "volume"))

    def test_validate_schema_missing_columns(self, builder):
        ds = ResearchDataset(
            dataset_id="test",
            schema=("close",),
            rows=({"close": 1.0},),
        )
        with pytest.raises(DatasetError, match="missing columns"):
            builder.validate_schema(ds, ("open", "high"))

    def test_split_train_test_default(self, builder):
        ds = ResearchDataset(
            dataset_id="test",
            schema=("close",),
            rows=tuple({"close": float(i)} for i in range(100)),
        )
        train, test = builder.split_train_test(ds)
        assert train.dataset_id == "test:train"
        assert test.dataset_id == "test:test"
        assert train.row_count == 80
        assert test.row_count == 20

    def test_split_train_test_custom_fraction(self, builder):
        ds = ResearchDataset(
            dataset_id="test",
            schema=("close",),
            rows=tuple({"close": float(i)} for i in range(100)),
        )
        train, test = builder.split_train_test(ds, train_fraction=0.7)
        assert train.row_count == 70
        assert test.row_count == 30

    def test_split_train_test_invalid_fraction(self, builder):
        ds = ResearchDataset(
            dataset_id="test",
            schema=("close",),
            rows=tuple({"close": float(i)} for i in range(100)),
        )
        with pytest.raises(DatasetError, match="train_fraction"):
            builder.split_train_test(ds, train_fraction=0.0)

        with pytest.raises(DatasetError, match="train_fraction"):
            builder.split_train_test(ds, train_fraction=1.0)

    def test_split_train_test_too_small(self, builder):
        ds = ResearchDataset(
            dataset_id="test",
            schema=("close",),
            rows=({"close": 1.0},),
        )
        with pytest.raises(DatasetError, match="train_fraction"):
            builder.split_train_test(ds, train_fraction=0.5)

    def test_split_walk_forward_valid(self, builder):
        ds = ResearchDataset(
            dataset_id="test",
            schema=("close",),
            rows=tuple({"close": float(i)} for i in range(50)),
        )
        windows = builder.split_walk_forward(ds, train_size=20, test_size=5)
        assert len(windows) == 6  # (50 - 20) / 5 = 6
        for train, test in windows:
            assert train.row_count == 20
            assert test.row_count == 5
            assert "train" in train.dataset_id
            assert "test" in test.dataset_id

    def test_split_walk_forward_invalid_params(self, builder):
        ds = ResearchDataset(
            dataset_id="test",
            schema=("close",),
            rows=tuple({"close": float(i)} for i in range(10)),
        )
        with pytest.raises(DatasetError, match="positive"):
            builder.split_walk_forward(ds, train_size=0, test_size=5)

        with pytest.raises(DatasetError, match="positive"):
            builder.split_walk_forward(ds, train_size=5, test_size=0)

    def test_split_walk_forward_too_small(self, builder):
        ds = ResearchDataset(
            dataset_id="test",
            schema=("close",),
            rows=tuple({"close": float(i)} for i in range(5)),
        )
        with pytest.raises(DatasetError, match="too small"):
            builder.split_walk_forward(ds, train_size=3, test_size=3)
