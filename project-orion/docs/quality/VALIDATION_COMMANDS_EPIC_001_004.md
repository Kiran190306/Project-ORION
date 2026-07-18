# EPIC-001..EPIC-004 Quality Gate — Local Validation Commands

> IMPORTANT: This file documents the exact commands that must be executed in a **working local environment** to complete the Quality Gate sprint (EPIC-001..EPIC-004).

## 0) Environment prerequisites
- Python **3.11** installed
- `poetry` installed (preferred, if repo expects it)

## 1) Install deps
### Poetry (recommended)
```bash
cd project-orion
poetry install
```

## 2) Unit tests + coverage
```bash
cd project-orion
poetry run pytest -q
poetry run pytest -q --disable-warnings --maxfail=1
poetry run pytest -q --cov=shared --cov=libraries --cov-report=term-missing --cov-report=xml
```

## 3) Formatting & import sorting
```bash
cd project-orion
poetry run black --check .
poetry run isort --check-only .
```

## 4) Static analysis
```bash
cd project-orion
poetry run mypy
poetry run pylint shared libraries
```

## 5) Optional: run CI locally (if available)
```bash
cd project-orion
# If the CI workflow supports a single command runner, use it.
# Otherwise run steps 2-4 as above.
```

## 6) Expected outcome
- All commands pass.
- Coverage is meaningful and meets target thresholds **where verifiable**.

## 7) Evidence to record
When running locally, capture:
- `pytest` output
- `coverage` report (term-missing + xml)
- `black/isort` check outputs
- `mypy` and `pylint` outputs

