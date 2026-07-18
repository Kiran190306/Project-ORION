"""
Pipelines Module

Module Description:
This module provides pipeline orchestration for data platform.
It handles data ingestion, processing, validation, and storage workflows.

Implementation Checklist:
- [ ] Pipeline base class
- [ ] Ingestion pipeline
- [ ] Processing pipeline
- [ ] Validation pipeline
- [ ] Storage pipeline
- [ ] Pipeline registry
- [ ] Pipeline execution engine

Dependency Notes:
- Depends on: shared/ (errors), libraries/data/schemas/, libraries/data/providers/, libraries/data/adapters/, libraries/data/normalizers/, libraries/data/validators/, libraries/data/quality/, libraries/data/storage/, libraries/data/datasets/
- Used by: services/historical-data/
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable, Optional, cast

from libraries.data.adapters import AdapterFactory, BaseAdapter
from libraries.data.datasets import DatasetManager
from libraries.data.normalizers import OHLCNormalizer, TickNormalizer
from libraries.data.providers import ProviderConfig
from libraries.data.quality import QualityManager
from libraries.data.schemas import (OHLC, DataQualityReport, DatasetRegistry,
                                    DatasetType, LifecycleStage, Tick)
from libraries.data.storage import StorageManager
from libraries.data.transform import DataTransformer
from libraries.data.validators import OHLCValidator, TickValidator
from shared.errors import OrionError


class PipelineError(OrionError):
    """Pipeline error."""

    pass


PipelineContext = dict[str, Any]
PipelineStep = Callable[[PipelineContext], Any]


def _required_string(context: PipelineContext, key: str) -> str:
    """Return a required string pipeline input."""
    value = context.get(key)
    if not isinstance(value, str):
        raise PipelineError(f"Pipeline context requires a string '{key}'")
    return value


class Pipeline(ABC):
    """Abstract pipeline base class."""

    def __init__(self, name: str) -> None:
        """Initialize pipeline.

        Args:
            name: Pipeline name
        """
        self.name = name
        self._steps: list[tuple[PipelineStep, str]] = []
        self._context: PipelineContext = {}

    def add_step(self, step: PipelineStep, step_name: str) -> None:
        """Add a step to the pipeline."""
        self._steps.append((step, step_name))

    def execute(self, **kwargs: Any) -> PipelineContext:
        """Execute pipeline.

        Args:
            **kwargs: Pipeline input parameters

        Returns:
            Pipeline execution results
        """
        self._context = kwargs
        results: PipelineContext = {}

        for step, step_name in self._steps:
            try:
                step_result = step(self._context)
                results[step_name] = step_result
            except Exception as e:
                raise PipelineError(f"Pipeline step '{step_name}' failed: {str(e)}")

        return results

    def get_context(self) -> PipelineContext:
        """Get pipeline context."""
        return self._context


class IngestionPipeline(Pipeline):
    """Pipeline for data ingestion from providers."""

    def __init__(
        self, adapter_factory: AdapterFactory, provider_config: ProviderConfig
    ):
        """Initialize ingestion pipeline.

        Args:
            adapter_factory: Adapter factory
            provider_config: Provider configuration
        """
        super().__init__("ingestion")
        self.adapter_factory = adapter_factory
        self.provider_config = provider_config

    def setup(self) -> None:
        """Setup pipeline steps."""
        self.add_step(self._connect_adapter, "connect")
        self.add_step(self._fetch_data, "fetch")
        self.add_step(self._disconnect_adapter, "disconnect")

    def _connect_adapter(self, context: PipelineContext) -> bool:
        """Connect to data provider."""
        adapter = self.adapter_factory.create_adapter(self.provider_config)
        adapter.connect()
        context["adapter"] = adapter
        return True

    def _fetch_data(self, context: PipelineContext) -> list[Tick] | list[OHLC]:
        """Fetch data from provider."""
        adapter = cast(BaseAdapter, context["adapter"])
        symbol = _required_string(context, "symbol")
        start_time = cast(datetime, context["start_time"])
        end_time = cast(datetime, context["end_time"])
        data_type = cast(str, context.get("data_type", "tick"))

        if data_type == "tick":
            tick_data = adapter.fetch_ticks(symbol, start_time, end_time)
            context["raw_data"] = tick_data
            return tick_data

        timeframe = context.get("timeframe", "M1")
        ohlc_data = adapter.fetch_ohlc(
            symbol, cast(str, timeframe), start_time, end_time
        )
        context["raw_data"] = ohlc_data
        return ohlc_data

    def _disconnect_adapter(self, context: PipelineContext) -> bool:
        """Disconnect from data provider."""
        adapter = cast(Optional[BaseAdapter], context.get("adapter"))
        if adapter:
            adapter.disconnect()
        return True


class ProcessingPipeline(Pipeline):
    """Pipeline for data processing and normalization."""

    def __init__(self, target_symbol: str, target_source: str):
        """Initialize processing pipeline.

        Args:
            target_symbol: Target symbol name
            target_source: Target source name
        """
        super().__init__("processing")
        self.target_symbol = target_symbol
        self.target_source = target_source
        self.transformer = DataTransformer()

    def setup(self) -> None:
        """Setup pipeline steps."""
        self.add_step(self._normalize_data, "normalize")
        self.add_step(self._transform_data, "transform")

    def _normalize_data(self, context: PipelineContext) -> list[Tick] | list[OHLC]:
        """Normalize data to target format."""
        data_type = cast(str, context.get("data_type", "tick"))

        if data_type == "tick":
            tick_normalizer = TickNormalizer(self.target_symbol, self.target_source)
            raw_ticks = cast(list[Tick], context.get("raw_data", []))
            normalized_ticks = [tick_normalizer.normalize(tick) for tick in raw_ticks]
            context["normalized_data"] = normalized_ticks
            return normalized_ticks

        ohlc_normalizer = OHLCNormalizer(self.target_symbol, self.target_source)
        raw_ohlc = cast(list[OHLC], context.get("raw_data", []))
        normalized_ohlc = [ohlc_normalizer.normalize(ohlc) for ohlc in raw_ohlc]
        context["normalized_data"] = normalized_ohlc
        return normalized_ohlc

    def _transform_data(self, context: PipelineContext) -> list[OHLC]:
        """Transform data (aggregation, multi-timeframe)."""
        data_type = cast(str, context.get("data_type", "tick"))
        symbol = _required_string(context, "symbol")

        if data_type == "tick":
            # Generate OHLC from ticks
            ticks = cast(list[Tick], context.get("normalized_data", []))
            ohlc_data = self.transformer.ticks_to_ohlc(ticks, symbol)
            context["ohlc_data"] = ohlc_data

            # Generate multi-timeframe
            multi_tf = self.transformer.generate_multi_timeframe(ticks, symbol)
            context["multi_timeframe_data"] = multi_tf

        return cast(list[OHLC], context.get("ohlc_data", []))


class ValidationPipeline(Pipeline):
    """Pipeline for data validation and quality checking."""

    def __init__(self, quality_manager: QualityManager):
        """Initialize validation pipeline.

        Args:
            quality_manager: Quality manager
        """
        super().__init__("validation")
        self.quality_manager = quality_manager

    def setup(self) -> None:
        """Setup pipeline steps."""
        self.add_step(self._validate_data, "validate")
        self.add_step(self._check_quality, "quality")

    def _validate_data(self, context: PipelineContext) -> list[str]:
        """Validate data structure and constraints."""
        data_type = cast(str, context.get("data_type", "tick"))

        errors: list[str] = []
        if data_type == "tick":
            tick_validator = TickValidator()
            for tick_item in cast(list[Tick], context.get("normalized_data", [])):
                item_errors = tick_validator.validate_tick(tick_item)
                errors.extend(item_errors)
            context["validation_errors"] = errors
            return errors

        ohlc_validator = OHLCValidator()
        for ohlc_item in cast(list[OHLC], context.get("normalized_data", [])):
            item_errors = ohlc_validator.validate_ohlc(ohlc_item)
            errors.extend(item_errors)
        context["validation_errors"] = errors
        return errors

    def _check_quality(self, context: PipelineContext) -> DataQualityReport:
        """Check data quality."""
        data_type = cast(str, context.get("data_type", "tick"))
        dataset_id = _required_string(context, "dataset_id")
        dataset_version = cast(str, context.get("dataset_version", "1.0.0"))

        if data_type == "tick":
            report = self.quality_manager.check_tick_data_quality(
                dataset_id,
                dataset_version,
                cast(list[Tick], context.get("normalized_data", [])),
            )
        else:
            report = self.quality_manager.check_ohlc_data_quality(
                dataset_id,
                dataset_version,
                cast(list[OHLC], context.get("normalized_data", [])),
            )

        context["quality_report"] = report
        return report


class StoragePipeline(Pipeline):
    """Pipeline for data storage and dataset registration."""

    def __init__(
        self, storage_manager: StorageManager, dataset_manager: DatasetManager
    ):
        """Initialize storage pipeline.

        Args:
            storage_manager: Storage manager
            dataset_manager: Dataset manager
        """
        super().__init__("storage")
        self.storage_manager = storage_manager
        self.dataset_manager = dataset_manager

    def setup(self) -> None:
        """Setup pipeline steps."""
        self.add_step(self._create_dataset, "create_dataset")
        self.add_step(self._store_data, "store")
        self.add_step(self._update_lifecycle, "update_lifecycle")

    def _create_dataset(self, context: PipelineContext) -> DatasetRegistry:
        """Create dataset registry entry."""
        dataset_id = _required_string(context, "dataset_id")
        data_type = cast(str, context.get("data_type", "tick"))
        symbol = _required_string(context, "symbol")
        timeframe = cast(Optional[str], context.get("timeframe"))

        dataset_type = DatasetType.TICK if data_type == "tick" else DatasetType.OHLC

        registry = self.dataset_manager.create_dataset(
            dataset_id=dataset_id,
            dataset_type=dataset_type,
            symbol=symbol,
            timeframe=timeframe,
        )

        context["dataset_registry"] = registry
        return registry

    def _store_data(self, context: PipelineContext) -> bool:
        """Store data to storage."""
        normalized_data = context.get("normalized_data", [])
        dataset_id = _required_string(context, "dataset_id")
        dataset_version = cast(str, context.get("dataset_version", "1.0.0"))

        # Store data
        path = f"datasets/{dataset_id}/{dataset_version}/data.json"
        self.storage_manager.write(path, normalized_data)

        return True

    def _update_lifecycle(self, context: PipelineContext) -> bool:
        """Update dataset lifecycle stage."""
        dataset_id = _required_string(context, "dataset_id")
        dataset_version = cast(str, context.get("dataset_version", "1.0.0"))
        quality_report = cast(
            Optional[DataQualityReport], context.get("quality_report")
        )

        if quality_report and quality_report.approved:
            self.dataset_manager.update_lifecycle_stage(
                dataset_id, dataset_version, LifecycleStage.ACTIVE
            )
        else:
            self.dataset_manager.update_lifecycle_stage(
                dataset_id, dataset_version, LifecycleStage.VALIDATION
            )

        return True


class PipelineEngine:
    """Engine for executing data pipelines."""

    def __init__(self) -> None:
        """Initialize pipeline engine."""
        self._pipelines: dict[str, Pipeline] = {}

    def register_pipeline(self, pipeline: Pipeline) -> None:
        """Register a pipeline."""
        self._pipelines[pipeline.name] = pipeline

    def get_pipeline(self, name: str) -> Optional[Pipeline]:
        """Get pipeline by name."""
        return self._pipelines.get(name)

    def execute_pipeline(self, name: str, **kwargs: Any) -> PipelineContext:
        """Execute a pipeline."""
        pipeline = self.get_pipeline(name)
        if not pipeline:
            raise PipelineError(f"Pipeline not found: {name}")
        return pipeline.execute(**kwargs)

    def list_pipelines(self) -> list[str]:
        """List registered pipelines."""
        return list(self._pipelines.keys())
