# Contributing to Project ORION

Thank you for your interest in contributing to Project ORION!

## Code of Conduct

This project adheres to a code of conduct. By participating, you are expected to uphold this code.

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
```

## Development Workflow

### Branch Strategy

- `main`: Production-ready code
- `develop`: Integration branch
- `feature/*`: Feature branches
- `bugfix/*`: Bug fix branches
- `hotfix/*`: Production hotfixes

### Creating a Branch

```bash
git checkout develop
git pull origin develop
git checkout -b feature/your-feature-name
```

### Making Changes

1. Make your changes
2. Write tests
3. Run linters: `make lint`
4. Run tests: `make test`
5. Format code: `make format`

### Committing

Follow conventional commits:

```
feat: add new feature
fix: fix bug
docs: update documentation
style: code style changes
refactor: code refactoring
perf: performance improvements
test: test changes
chore: maintenance tasks
```

### Pull Request

1. Push your branch
2. Create pull request to `develop`
3. Fill out PR template
4. Wait for review
5. Address feedback
6. Merge after approval

## Coding Standards

### Python
- PEP 8 compliance
- Type hints required
- Docstrings (Google style)
- Black formatter
- isort for imports

### Go
- gofmt compliance
- Effective Go guidelines
- GoDoc comments

### JavaScript/TypeScript
- ESLint configuration
- Prettier formatter
- TypeScript strict mode

## Testing

### Running Tests

```bash
# All tests
make test

# Unit tests
make test-unit

# Integration tests
make test-integration
```

### Test Coverage

Minimum 80% coverage required for all code.

## Documentation

Update documentation for all changes:
- API changes: Update API docs
- Architecture changes: Update ADRs
- User-facing changes: Update user guides

## Questions?

Open an issue or contact the team.
