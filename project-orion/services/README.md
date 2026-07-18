# Services

This directory contains all microservices for Project ORION.

## Services

| Service | Description | Language |
|---------|-------------|----------|
| market-data | Real-time market data ingestion and distribution | Python |
| trading-core | Core trading logic and order management | Go |
| decision-engine | Trading decision intelligence | Python |
| market-intelligence | Market structure and liquidity analysis | Python |
| execution | Order execution to brokers | Go |
| risk-management | Risk monitoring and control | Python |
| position-management | Position lifecycle management | Go |
| strategy-registry | Strategy lifecycle management | Python |
| historical-data | Historical data storage and access | Python |
| backtesting | Backtesting engine | Python |
| analytics | Analytics and reporting | Python |
| notifications | Notification delivery | Go |
| user-management | User authentication and authorization | Go |

## Service Structure

Each service has:
- `src/` - Source code
- `tests/` - Tests
- `k8s/` - Kubernetes manifests
- `Dockerfile` - Docker configuration
- `README.md` - Service documentation

## Dependencies

All services depend on:
- `libraries/` - Shared libraries
- `shared/` - Shared utilities
- `api/` - API definitions

Services do NOT depend on other services directly (use API/events).

## Ownership

- Backend Team: All services
- DevOps Team: Kubernetes manifests
- QA Team: Tests
