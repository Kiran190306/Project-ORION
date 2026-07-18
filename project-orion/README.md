# Project ORION

An institutional-grade, automated Forex trading platform with clean architecture, deterministic decision-making, and rigorous scientific validation.

## Architecture Version

- **Version:** 1.0.0
- **Status:** FROZEN
- **Date:** July 2026

## Overview

Project ORION is a production-grade automated trading platform designed for institutional Forex trading. The platform features:

- Clean Architecture with DDD and SOLID principles
- Event-driven microservices architecture
- Deterministic, explainable trading decisions
- Institutional-grade strategy validation
- Comprehensive historical data platform
- Advanced market intelligence
- Rigorous backtesting framework

## Repository Structure

```
project-orion/
├── apps/              # Application entry points
├── services/          # Microservices
├── libraries/         # Shared libraries
├── shared/            # Shared utilities
├── sdk/               # Client SDKs
├── api/               # API definitions
├── infrastructure/    # Infrastructure as Code
├── deployment/        # Deployment configurations
├── docker/            # Docker configurations
├── kubernetes/        # Kubernetes manifests
├── monitoring/        # Monitoring configurations
├── security/          # Security configurations
├── configs/           # Configuration files
├── scripts/           # Utility scripts
├── tools/             # Development tools
├── workers/           # Background workers
├── plugins/           # Strategy plugins
├── research/          # Research code
├── backtesting/       # Backtesting code
├── paper-trading/     # Paper trading code
├── analytics/         # Analytics code
├── ai/                # AI/ML code
├── dashboard/         # Dashboard UI
├── mobile/            # Mobile applications
├── desktop/           # Desktop applications
├── notifications/     # Notification services
├── gateway/           # API gateway
├── broker/            # Broker integration
├── storage/           # Storage services
├── database/          # Database schemas
├── tests/             # Test suites
├── benchmarks/        # Performance benchmarks
├── examples/          # Example code
└── docs/              # Documentation
```

## Documentation

- [Architecture Documentation](docs/architecture/)
- [API Documentation](docs/api/)
- [User Guides](docs/guides/)
- [Operations Documentation](docs/operations/)
- [Security Documentation](docs/security/)

## Getting Started

### Prerequisites

- Docker
- Kubernetes
- Python 3.11+
- Go 1.21+
- Node.js 20+

### Setup

```bash
# Clone repository
git clone git@github.com:organization/project-orion.git
cd project-orion

# Install dependencies
make install

# Configure environment
cp configs/dev/env.yaml.example configs/dev/env.yaml
# Edit configs/dev/env.yaml

# Start services
make dev-up
```

## Development

### Running Tests

```bash
# Run all tests
make test

# Run unit tests
make test-unit

# Run integration tests
make test-integration
```

### Building

```bash
# Build all services
make build

# Build specific service
make build-service SERVICE=market-data
```

### Linting

```bash
# Run linters
make lint

# Format code
make format
```

## Deployment

### Staging

```bash
make deploy-staging
```

### Production

```bash
make deploy-production
```

## Architecture Documents

- [ARCHITECTURE.md](../ARCHITECTURE.md) - System Requirements Specification
- [TRADING_CORE_ARCHITECTURE.md](../TRADING_CORE_ARCHITECTURE.md) - Core Trading Engine
- [TRADING_DECISION_INTELLIGENCE_ENGINE.md](../TRADING_DECISION_INTELLIGENCE_ENGINE.md) - Decision Engine
- [MARKET_INTELLIGENCE_RESEARCH_ENGINE.md](../MARKET_INTELLIGENCE_RESEARCH_ENGINE.md) - Market Intelligence
- [INSTITUTIONAL_STRATEGY_RESEARCH_LABORATORY.md](../INSTITUTIONAL_STRATEGY_RESEARCH_LABORATORY.md) - Strategy Research
- [HISTORICAL_DATA_PLATFORM_BACKTESTING_LABORATORY.md](../HISTORICAL_DATA_PLATFORM_BACKTESTING_LABORATORY.md) - Data Platform & Backtesting
- [ARCHITECTURE_FREEZE_REPOSITORY_BLUEPRINT.md](../ARCHITECTURE_FREEZE_REPOSITORY_BLUEPRINT.md) - Repository Blueprint
- [ENGINEERING_EXECUTION_MASTER_PLAN.md](../ENGINEERING_EXECUTION_MASTER_PLAN.md) - Implementation Plan

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

## License

See [LICENSE](LICENSE) for license information.

## Security

See [SECURITY.md](SECURITY.md) for security information.

## Support

For support, email support@orion.example.com or open an issue in the repository.
