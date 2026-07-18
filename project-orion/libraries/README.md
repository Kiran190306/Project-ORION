# Libraries

This directory contains all shared libraries for Project ORION.

## Library Categories

### Domain Libraries
Business logic and domain models:
- `trading/` - Trading domain models and logic
- `market/` - Market domain models and logic
- `risk/` - Risk domain models and logic
- `strategy/` - Strategy domain models and logic

### Infrastructure Libraries
Technical infrastructure:
- `messaging/` - Messaging infrastructure (Kafka)
- `persistence/` - Persistence infrastructure (database)
- `caching/` - Caching infrastructure (Redis)
- `logging/` - Logging infrastructure

### Utility Libraries
Common utilities:
- `validation/` - Validation utilities
- `serialization/` - Serialization utilities
- `datetime/` - Date/time utilities
- `math/` - Math utilities

## Dependencies

All libraries depend on:
- `shared/` - Shared types and constants

Libraries do NOT depend on:
- `services/` - Services
- `apps/` - Applications

## Ownership
- Platform Team (primary)
- All teams (consumers)
