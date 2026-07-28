"""Dataset construction, schema validation, and deterministic splitting."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from libraries.domain.ai_research.exceptions import DatasetError
from libraries.domain.ai_research.models import ResearchDataset


class ResearchDatasetBuilder:
    """Builds immutable datasets without accessing external data sources."""

    async def build(self, dataset_id: str, rows: Sequence[Mapping[str, Any]]) -> ResearchDataset:
        if not rows:
            raise DatasetError("cannot build a dataset without rows")
        schema = tuple(rows[0].keys())
        if not schema:
            raise DatasetError("dataset rows must have a schema")
        try:
            return ResearchDataset(
                dataset_id=dataset_id,
                schema=schema,
                rows=tuple(rows),
                metadata={"statistics": self.statistics(rows, schema)},
            )
        except (TypeError, ValueError) as exc:
            raise DatasetError(str(exc)) from exc

    def validate_schema(self, dataset: ResearchDataset, required_columns: Sequence[str]) -> None:
        missing = set(required_columns).difference(dataset.schema)
        if missing:
            raise DatasetError(
                f"dataset '{dataset.dataset_id}' is missing columns: {sorted(missing)}"
            )

    def statistics(
        self, rows: Sequence[Mapping[str, Any]], schema: Sequence[str]
    ) -> dict[str, Any]:
        return {
            "row_count": len(rows),
            "column_count": len(schema),
            "null_counts": {
                column: sum(row.get(column) is None for row in rows) for column in schema
            },
        }

    def split_train_test(
        self, dataset: ResearchDataset, train_fraction: float = 0.8
    ) -> tuple[ResearchDataset, ResearchDataset]:
        if not 0.0 < train_fraction < 1.0:
            raise DatasetError("train_fraction must be between 0 and 1")
        split_at = int(dataset.row_count * train_fraction)
        if split_at == 0 or split_at == dataset.row_count:
            raise DatasetError("train_fraction must produce non-empty train and test sets")
        return self._split(dataset, "train", dataset.rows[:split_at]), self._split(
            dataset, "test", dataset.rows[split_at:]
        )

    def split_walk_forward(
        self, dataset: ResearchDataset, train_size: int, test_size: int
    ) -> tuple[tuple[ResearchDataset, ResearchDataset], ...]:
        if train_size < 1 or test_size < 1:
            raise DatasetError("train_size and test_size must be positive")
        windows = []
        start = 0
        while start + train_size + test_size <= dataset.row_count:
            windows.append(
                (
                    self._split(
                        dataset, f"train-{start}", dataset.rows[start : start + train_size]
                    ),
                    self._split(
                        dataset,
                        f"test-{start}",
                        dataset.rows[start + train_size : start + train_size + test_size],
                    ),
                )
            )
            start += test_size
        if not windows:
            raise DatasetError("dataset is too small for the requested walk-forward split")
        return tuple(windows)

    @staticmethod
    def _split(
        dataset: ResearchDataset, suffix: str, rows: Sequence[Mapping[str, Any]]
    ) -> ResearchDataset:
        return ResearchDataset(
            dataset_id=f"{dataset.dataset_id}:{suffix}",
            schema=dataset.schema,
            rows=tuple(rows),
            metadata={"parent_dataset_id": dataset.dataset_id},
        )


DatasetBuilder = ResearchDatasetBuilder
