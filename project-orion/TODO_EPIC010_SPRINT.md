# EPIC-010: Remaining Work

## Phase 1: Fix Source Code Issues
- [ ] Fix `engine.py` — add `BacktestEngineConfig` and `EngineStatus`
- [ ] Fix `reporting.py` — fix model attribute references, add missing classes
- [ ] Fix `statistics.py` — fix model attribute references  
- [ ] Fix `__init__.py` — fix imports to match actual exports
- [ ] Run first import test to verify

## Phase 2: Create Tests
- [ ] `tests/unit/domain/backtesting/__init__.py`
- [ ] `test_models.py` — Model creation, defaults, properties, serialization
- [ ] `test_exceptions.py` — Exception hierarchy
- [ ] `test_interfaces.py` — Protocol structural tests
- [ ] `test_commission_model.py` — Commission calculation
- [ ] `test_slippage_model.py` — Slippage calculation
- [ ] `test_spread_model.py` — Spread simulation
- [ ] `test_swap_model.py` — Swap calculation
- [ ] `test_latency_model.py` — Broker delay
- [ ] `test_liquidity_model.py` — Liquidity constraints
- [ ] `test_market_impact_model.py` — Market impact
- [ ] `test_execution_simulator.py` — Order execution simulation
- [ ] `test_portfolio_simulator.py` — Portfolio simulation
- [ ] `test_statistics.py` — Trade/portfolio/execution stats
- [ ] `test_performance.py` — Performance metrics
- [ ] `test_replay_engine.py` — Replay functionality
- [ ] `test_event_scheduler.py` — Event scheduling
- [ ] `test_historical_data.py` — Data loading
- [ ] `test_scenario_engine.py` — Scenario testing
- [ ] `test_walk_forward.py` — Walk-forward analysis
- [ ] `test_monte_carlo.py` — Monte Carlo simulation
- [ ] `test_parameter_optimizer.py` — Parameter optimization
- [ ] `test_reporting.py` — Report generation
- [ ] `test_engine.py` — Full backtest engine
- [ ] `test_manager.py` — Lifecycle management

## Phase 3: Quality Gates
- [ ] Run `python -m isort .`
- [ ] Run `python -m black .`
- [ ] Run `python -m pytest --tb=short`
- [ ] Generate coverage HTML
- [ ] Generate coverage XML

## Phase 4: Finalize
- [ ] Update TODO_EPIC010.md
- [ ] Update docs/epic010/FINAL_REPORT_EPIC010.md
- [ ] `git add . && git commit -m "Implement EPIC-010"`

