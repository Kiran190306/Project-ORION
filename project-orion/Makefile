.PHONY: help install lint test format typecheck clean docker-up docker-down dev-up dev-down

POETRY ?= poetry
NPM ?= npm
DOCKER_COMPOSE ?= docker compose
COMPOSE_FILE ?= docker-compose.dev.yml

PYTHON_SOURCES := shared libraries tests
PYTHON_PACKAGES := shared libraries

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install Python and Node.js dependencies
	$(POETRY) install --no-interaction
	$(NPM) install

lint: ## Run Python and Node.js linters
	$(POETRY) run black --check $(PYTHON_SOURCES)
	$(POETRY) run isort --check-only $(PYTHON_SOURCES)
	$(POETRY) run pylint $(PYTHON_PACKAGES)
	$(NPM) run lint

format: ## Format Python and Node.js source files
	$(POETRY) run black $(PYTHON_SOURCES)
	$(POETRY) run isort $(PYTHON_SOURCES)
	$(NPM) run format

typecheck: ## Run static type checking
	$(POETRY) run mypy $(PYTHON_PACKAGES) tests

test: ## Run all tests
	$(POETRY) run pytest

clean: ## Remove local build artifacts and caches
	-$(POETRY) run python -c "import pathlib, shutil; \
targets = ['.pytest_cache', '.mypy_cache', 'htmlcov', 'dist']; \
[shutil.rmtree(path, ignore_errors=True) for path in targets]; \
[pathlib.Path('coverage.xml').unlink(missing_ok=True), pathlib.Path('.coverage').unlink(missing_ok=True)]; \
[shutil.rmtree(path, ignore_errors=True) for path in pathlib.Path('.').rglob('__pycache__')]"
	-$(NPM) run clean --if-present

docker-up: ## Start development infrastructure services
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) up -d

docker-down: ## Stop development infrastructure services
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) down

dev-up: docker-up ## Alias for docker-up

dev-down: docker-down ## Alias for docker-down
