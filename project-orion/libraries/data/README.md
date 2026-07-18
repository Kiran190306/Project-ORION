# Data Platform Foundation Library

## Overview

The Data Platform Foundation library provides the reusable data infrastructure for Project ORION. It serves as the platform layer underneath the Market Data Engine and other market modules.

## Architecture Reference

- HISTORICAL_DATA_PLATFORM_BACKTESTING_LABORATORY.md (Phase 6)
- ARCHITECTURE_FREEZE_REPOSITORY_BLUEPRINT.md (Phase 7)

## Module Structure

```
libraries/data/
├── data/              # Core data platform coordinator
├── providers/         # Provider abstraction layer
├── adapters/          # Provider-specific adapters
├── normalizers/       # Data normalization
├── validators/        # Data validation
├── schemas/           # Data schemas and models
├── serialization/     # Data serialization
├── deserialization/   # Data deserialization
├── compression/       # Compression abstraction
├── cache/             # Cache abstraction
├── storage/           # Storage abstraction
├── datasets/          # Dataset management
├── replay/            # Replay engine foundation
├── metadata/          # Metadata management
├── transform/         # Data transformation
├── quality/           # Data quality framework
└── pipelines/         # Data pipeline orchestration
```

## Dependencies

- `shared/` - Shared types, enums, constants, errors
- `libraries/infrastructure/persistence/` - Database infrastructure (reuse)
- `libraries/infrastructure/caching/` - Cache infrastructure (reuse)
- `libraries/utils/serialization/` - Serialization utilities (reuse)
- `libraries/utils/validation/` - Validation utilities (reuse)

## Dependency Rules

- NO dependencies on services/
- NO dependencies on apps/
- Can depend on shared/ and libraries/infrastructure/
- Can depend on libraries/utils/

## Key Responsibilities

- Multiple provider support
- Normalized market data
- Schema validation
- Immutable datasets
- Versioned datasets
- Replay compatibility
- Deterministic serialization
- Compression abstraction
- Cache abstraction
- Storage abstraction
- Provider abstraction

## Usage Example

```python
from libraries.data.data import initialize_platform, DataPlatformConfig

# Initialize platform
config = DataPlatformConfig(
    storage_path="./data_storage",
    enable_cache=True,
    enable_compression=True
)
platform = initialize_platform(config)

# Use platform components
storage = platform.get_storage()
metadata = platform.get_metadata()
datasets = platform.get_datasets()
quality = platform.get_quality()
transform = platform.get_transform()
```

## Module Details

### schemas/
Defines all data schemas for the data platform:
- Tick, OHLC data models
- Symbol, session, holiday metadata
- Data lineage, versioning
- Quality report schemas

### validators/
Provides validation logic:
- Tick/OHLC validators
- Metadata validators
- Quality checkers
- Overall quality scoring

### serialization/deserialization
Handles data serialization:
- JSON, MessagePack, Avro support
- Type conversion
- Schema-aware deserialization

### compression
Provides compression abstraction:
- Gzip, LZ4, Zstd support
- Compression level configuration

### cache
Provides cache abstraction:
- In-memory backend
- Redis backend (extensible)
- Cache key generation

### storage
Provides storage abstraction:
- File system backend
- S3 backend
- Compression and serialization integration

### providers/
Defines provider abstraction:
- Provider interface
- Provider configuration
- Provider registry

### adapters/
Provides provider-specific adapters:
- Base adapter class
- Adapter factory
- Extensible for new providers

### normalizers/
Handles data normalization:
- Tick normalization
- OHLC normalization
- Symbol normalization
- Timestamp normalization

### metadata/
Manages metadata:
- Symbol metadata storage
- Session metadata
- Holiday calendars
- DST configurations

### datasets/
Manages dataset lifecycle:
- Dataset creation
- Versioning
- Lifecycle management
- Lineage tracking

### quality/
Provides quality framework:
- Quality checks
- Quality scoring
- Quality reporting
- Approval thresholds

### transform/
Handles data transformation:
- Tick to OHLC aggregation
- Multi-timeframe generation
- Data resampling

### replay/
Provides replay engine foundation:
- Replay controller
- Tick/candle generators
- Speed control
- Checkpointing

### pipelines/
Orchestrates data workflows:
- Ingestion pipeline
- Processing pipeline
- Validation pipeline
- Storage pipeline
- Pipeline engine

### data/
Core coordinator:
- DataPlatform class
- Component initialization
- Public API exports

## Ownership

- Platform Team (primary)
- Data Team (consumers)
- Quant Team (consumers)

## Future Implementation Notes

- Add concrete provider implementations (broker-specific)
- Implement missing data detection
- Implement duplicate detection
- Implement outlier detection
- Implement OHLC resampling
- Add Redis cache backend
- Add database storage backend
- Implement session validation
- Implement DST adjustment logic
- Add more compression algorithms
- Add more serialization formats

## Testing

Run tests with:
```bash
pytest libraries/data/
```

## License

Proprietary - See project LICENSE
