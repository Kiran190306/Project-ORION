# EPIC-012 SPRINT-1.1 COVERAGE COMPLETION PLAN

## Information Gathered

### Source Modules (10 target modules):
1. **middleware.py** - ObservabilityMiddleware, CorrelationIdMiddleware, RequestMetricsMiddleware
2. **health.py** - HealthRegistry, HealthCheckResult, HealthStatus
3. **integration.py** - observe_service decorator, ServiceObserver, configure_observability
4. **market_classifier.py** - MarketClassifier aggregates trend/volatility/liquidity
5. **market_regime_detector.py** - MarketRegimeDetector wraps MarketClassifier
6. **parameter_stability.py** - ParameterStabilityAnalyzer
7. **feature_engineering.py** - ResearchFeatureEngineer
8. **fitness_engine.py** - CompositeFitnessEngine
9. **grid_search.py** - GridSearchOptimizer
10. **logging.py** - StructuredFormatter, StructuredLogger, configure_logging

### Existing Test Files:
- `tests/unit/test_observability_middleware.py` - 18 tests
- `tests/unit/test_observability_health.py` - 10 tests  
- `tests/unit/test_observability_integration.py` - 10 tests
- `tests/unit/domain/ai_research/test_market_classifier.py` - 7 tests
- `tests/unit/domain/ai_research/test_market_regime_detector.py` - 7 tests
- `tests/unit/domain/ai_research/test_parameter_stability.py` - 6 tests
- `tests/unit/domain/ai_research/test_feature_engineering.py` - ~20 tests
- `tests/unit/domain/ai_research/test_fitness_engine.py` - ~20 tests
- `tests/unit/domain/ai_research/test_grid_search.py` - ~15 tests
- `tests/unit/test_coverage_sprint1dot1.py` - comprehensive file with ~146 tests (has 1 failure due to production bug)

### Bug Found:
- `_Span` class in `tracing.py` is missing `set_attribute()` method
- Both `middleware.py` and `integration.py` call `span.set_attribute()` on `_Span` objects
- `_NoopSpan` has `set_attribute()` but `_Span` doesn't - this is an oversight
- This causes `test_decorator_span_cleanup_on_error` to fail with `AttributeError`

## Plan

### Step 1: Fix Production Bug
- Add `set_attribute()` method to `_Span` class in `tracing.py` that updates `self.attributes` dict

### Step 2: Consolidate All Tests into `test_coverage_sprint1dot1.py`
The file `test_coverage_sprint1dot1.py` already contains comprehensive tests for all 10 modules. We should:
- Keep all existing separate test files as-is (they complement coverage)
- Fix and run `test_coverage_sprint1dot1.py` to pass all tests
- The file already covers:
  - **Middleware**: Request lifecycle, response lifecycle, exception handling, correlation ID propagation, trace propagation, metrics recording, latency measurement, concurrent requests, missing headers, malformed requests, custom exclude paths, tracer disabled
  - **Health**: Healthy state, degraded state, unhealthy state, dependency failures, multiple simultaneous checks, startup, readiness, liveness, disk_space check, non-result returns, empty registry
  - **Integration**: Decorator with tracing, metrics+tracing, logging disabled, instance correlation_id, metrics failure handling, span cleanup on error, function name preserved, ServiceObserver with non-async, non-callable attrs, health without health_check, non-dict health return
  - **Market Classifier**: Unknown inputs, boundary thresholds, low sample counts, missing indicators, unknown condition, mixed signals, confidence calculation
  - **Market Regime Detector**: Insufficient history, volatile markets, stable markets, conflicting classifier outputs, ValueError wrapping, TypeError wrapping, regime transition detection, classify returns complete
  - **Feature Engineering**: Custom registration, duplicate registration overwrites, invalid registration, unregistered custom, empty dataset, empty definitions, large dataset, pipeline ordering, exception propagation, missing columns, invalid period, unsupported feature, all category tests
  - **Fitness Engine**: Weight validation, empty metrics, zero division protection, negative returns, extreme drawdown, NaN handling, infinite values, batch calculation, metric fallback names, win rate normalization
  - **Grid Search**: Empty space, single/multiple params, duplicate prevention, max combinations, cancellation, progress callback, all parameter types
  - **Logging**: Sensitive data masking, correlation IDs, exception formatting, exc_info fallback, exc_text fallback, structured metadata, nested exceptions, trace IDs, all logger methods, configure_logging, logger caching, hostname/service/module info

### Step 3: Run Quality Gates
- Run isort, black, pytest, and coverage reports

## Dependent Files to be edited:
1. `project-orion/libraries/observability/tracing.py` - Fix `_Span.set_attribute()`
2. `project-orion/tests/unit/test_coverage_sprint1dot1.py` - Already comprehensive, may need minor fixes

## Followup Steps:
1. Run `python -m isort .`
2. Run `python -m black .`
3. Run `python -m pytest`
4. Run `python -m pytest --cov=libraries.domain.ai_research --cov=libraries.observability --cov-report=html --cov-report=xml --cov-report=term-missing`
5. Generate coverage report and validate ≥95%
6. If all quality gates pass, recommend tag v0.12.0-alpha.2

