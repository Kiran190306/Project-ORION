"""
Data Module

Module Description:
This module provides the core data platform foundation interfaces and coordination.
It serves as the main entry point for the data platform library.

Implementation Checklist:
- [ ] Data platform manager
- [ ] Data platform configuration
- [ ] Module initialization
- [ ] Public API exports

Dependency Notes:
- Depends on: shared/ (errors), all data platform submodules
- Used by: services/historical-data/, services/backtesting/, services/market-intelligence/
"""

from datetime import datetime
from typing import Optional

from libraries.data.adapters import AdapterFactory
from libraries.data.cache import CacheManager
from libraries.data.compression import compress, decompress
from libraries.data.datasets import DatasetManager
from libraries.data.metadata import MetadataManager
from libraries.data.normalizers import OHLCNormalizer, TickNormalizer
from libraries.data.pipelines import (
    IngestionPipeline,
    PipelineEngine,
    ProcessingPipeline,
    StoragePipeline,
    ValidationPipeline,
)
from libraries.data.providers import DataProvider, ProviderConfig, ProviderRegistry
from libraries.data.quality import QualityManager
from libraries.data.replay import ReplayController
from libraries.data.schemas import (
    OHLC,
    DatasetRegistry,
    DatasetType,
    Holiday,
    LifecycleStage,
    Session,
    SymbolMetadata,
    Tick,
)
from libraries.data.serialization import deserialize, serialize
from libraries.data.storage import FileSystemStorage, StorageManager
from libraries.data.transform import DataTransformer
from libraries.data.validators import OHLCValidator, TickValidator
from shared.errors import OrionError


class DataPlatformError(OrionError):
    """Data platform error."""

    pass


class DataPlatformConfig:
    """Configuration for data platform."""

    def __init__(
        self,
        storage_path: str = "./data_storage",
        enable_cache: bool = True,
        enable_compression: bool = True,
        compression_algorithm: str = "gzip",
        serialization_format: str = "json",
        approval_threshold: float = 0.9,
    ):
        """Initialize data platform configuration.

        Args:
            storage_path: Path for file system storage
            enable_cache: Whether to enable caching
            enable_compression: Whether to enable compression
            compression_algorithm: Compression algorithm to use
            serialization_format: Serialization format to use
            approval_threshold: Quality approval threshold
        """
        self.storage_path = storage_path
        self.enable_cache = enable_cache
        self.enable_compression = enable_compression
        self.compression_algorithm = compression_algorithm
        self.serialization_format = serialization_format
        self.approval_threshold = approval_threshold


class DataPlatform:
    """Main data platform coordinator."""

    def __init__(self, config: Optional[DataPlatformConfig] = None):
        """Initialize data platform.

        Args:
            config: Data platform configuration
        """
        self.config = config or DataPlatformConfig()

        # Initialize components
        self._initialize_components()

    def _initialize_components(self) -> None:
        """Initialize all platform components."""
        # Storage
        storage_backend = FileSystemStorage(self.config.storage_path)
        self.storage = StorageManager(
            backend=storage_backend,
            compress=self.config.enable_compression,
            compression_algorithm=self.config.compression_algorithm,
            serialization_format=self.config.serialization_format,
        )

        # Cache
        if self.config.enable_cache:
            self.cache: Optional[CacheManager] = CacheManager()
        else:
            self.cache = None

        # Metadata
        self.metadata = MetadataManager(self.storage, self.cache)

        # Datasets
        self.datasets = DatasetManager(self.storage)

        # Quality
        self.quality = QualityManager(self.config.approval_threshold)

        # Transform
        self.transform = DataTransformer()

        # Providers
        self.provider_registry = ProviderRegistry()

        # Adapters
        self.adapter_factory = AdapterFactory()

        # Pipelines
        self.pipeline_engine = PipelineEngine()

    def register_provider(self, provider_type: str, provider_class: type) -> None:
        """Register a provider class."""
        self.provider_registry.register_provider_class(provider_type, provider_class)

    def register_adapter(self, provider_type: str, adapter_class: type) -> None:
        """Register an adapter class."""
        self.adapter_factory.register_adapter(provider_type, adapter_class)

    def create_ingestion_pipeline(self, provider_config: ProviderConfig) -> IngestionPipeline:
        """Create an ingestion pipeline."""
        pipeline = IngestionPipeline(self.adapter_factory, provider_config)
        pipeline.setup()
        self.pipeline_engine.register_pipeline(pipeline)
        return pipeline

    def create_processing_pipeline(
        self, target_symbol: str, target_source: str
    ) -> ProcessingPipeline:
        """Create a processing pipeline."""
        pipeline = ProcessingPipeline(target_symbol, target_source)
        pipeline.setup()
        self.pipeline_engine.register_pipeline(pipeline)
        return pipeline

    def create_validation_pipeline(self) -> ValidationPipeline:
        """Create a validation pipeline."""
        pipeline = ValidationPipeline(self.quality)
        pipeline.setup()
        self.pipeline_engine.register_pipeline(pipeline)
        return pipeline

    def create_storage_pipeline(self) -> StoragePipeline:
        """Create a storage pipeline."""
        pipeline = StoragePipeline(self.storage, self.datasets)
        pipeline.setup()
        self.pipeline_engine.register_pipeline(pipeline)
        return pipeline

    def create_replay_controller(self) -> ReplayController:
        """Create a replay controller."""
        return ReplayController()

    def get_storage(self) -> StorageManager:
        """Get storage manager."""
        return self.storage

    def get_cache(self) -> Optional[CacheManager]:
        """Get cache manager."""
        return self.cache

    def get_metadata(self) -> MetadataManager:
        """Get metadata manager."""
        return self.metadata

    def get_datasets(self) -> DatasetManager:
        """Get dataset manager."""
        return self.datasets

    def get_quality(self) -> QualityManager:
        """Get quality manager."""
        return self.quality

    def get_transform(self) -> DataTransformer:
        """Get data transformer."""
        return self.transform

    def get_pipeline_engine(self) -> PipelineEngine:
        """Get pipeline engine."""
        return self.pipeline_engine


# Global platform instance
_platform: Optional[DataPlatform] = None


def initialize_platform(config: Optional[DataPlatformConfig] = None) -> DataPlatform:
    """Initialize global data platform instance.

    Args:
        config: Data platform configuration

    Returns:
        Data platform instance
    """
    global _platform
    _platform = DataPlatform(config)
    return _platform


def get_platform() -> Optional[DataPlatform]:
    """Get global data platform instance.

    Returns:
        Data platform instance or None if not initialized
    """
    return _platform


# Public API exports
__all__ = [
    # Schemas
    "Tick",
    "OHLC",
    "SymbolMetadata",
    "Session",
    "Holiday",
    "DatasetRegistry",
    "DatasetType",
    "LifecycleStage",
    # Providers
    "DataProvider",
    "ProviderConfig",
    "ProviderRegistry",
    # Adapters
    "AdapterFactory",
    # Normalizers
    "TickNormalizer",
    "OHLCNormalizer",
    # Validators
    "TickValidator",
    "OHLCValidator",
    # Serialization
    "serialize",
    "deserialize",
    # Compression
    "compress",
    "decompress",
    # Storage
    "StorageManager",
    "FileSystemStorage",
    # Cache
    "CacheManager",
    # Datasets
    "DatasetManager",
    # Metadata
    "MetadataManager",
    # Quality
    "QualityManager",
    # Transform
    "DataTransformer",
    # Replay
    "ReplayController",
    # Pipelines
    "PipelineEngine",
    "IngestionPipeline",
    "ProcessingPipeline",
    "ValidationPipeline",
    "StoragePipeline",
    # Core
    "DataPlatform",
    "DataPlatformConfig",
    "DataPlatformError",
    "initialize_platform",
    "get_platform",
]
