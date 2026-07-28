# EPIC-011 Stabilization TODO

## Phase 1: Import Fixes — `__init__.py`
- [ ] Fix `__init__.py` — Replace `BacktestConfig` with `ResearchPlatformConfig` (models.py does not export BacktestConfig)
- [ ] Fix `__init__.py` — Replace `FeatureEngineeringPipeline`, `CustomFeaturePipeline`, `FeatureTransformer`, `IndicatorFeature`, `TechnicalIndicatorFeature`, `TimeFeature` imports with actual exports from feature_engineering.py (`FeatureEngineer`, `TechnicalIndicators`, `PriceActionFeatures`, `VolumeFeatures`, `VolatilityFeatures`, `TrendFeatures`, `MomentumFeatures`, `TimeFeatures`)
- [ ] Fix `__init__.py` — Add proper `FeatureCategory`, `FeatureType`, `FeatureValue`, `FeaturePipeline` to __all__

## Phase 2: Import Fixes — `engine.py`
- [ ] Fix `engine.py` — Replace `EngineError` import with `AIResearchError` (exceptions.py has no `EngineError`)
- [ ] Fix `engine.py` — Replace `FeatureEngineeringPipeline` import with `FeatureEngineer` (actual class name)
- [ ] Fix `engine.py` — Fix `discover_strategies()` method signature: `StrategyLoader.load_strategies()` takes `strategy_ids`, not a directory
- [ ] Fix `engine.py` — Fix `_strategy_repo.register()` → `_strategy_repo.save_strategy()`
- [ ] Fix `engine.py` — Fix `_strategy_repo.list_all()` → `_strategy_repo.list_strategies()`
- [ ] Fix `engine.py` — Fix `_ranker.rank_and_update(strategies)` → `_ranker.rank(results, metric)` with proper signature
- [ ] Fix `engine.py` — Fix `self._context.default_dataset` → `self._context.dataset`
- [ ] Fix `engine.py` — Remove unused `ExperimentRun` import
- [ ] Fix `engine.py` — Fix `strategy.strategy.parameters` reference in optimize_strategy

## Phase 3: Import Fixes — `manager.py`
- [ ] Fix `manager.py` — Replace `EngineStateError` with `AIResearchError` (exceptions.py has no `EngineStateError`)

## Phase 4: Add Missing `FeatureCategory` and `FeatureType` exports
- [ ] Add `FeatureCategory`, `FeatureType`, `FeatureValue`, `FeaturePipeline` to __all__

## Phase 5: Validation
- [ ] Run import test: `python -c "from libraries.domain.ai_research import *"`
- [ ] Run `python -m pytest -q --tb=line`
- [ ] Run `python -m isort .`
- [ ] Run `python -m black .`

