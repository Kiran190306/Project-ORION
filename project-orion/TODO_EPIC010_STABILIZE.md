# EPIC-010 Stabilization TODO

## Phase 1: Critical Import Fixes
- [x] Fix `__init__.py` - Remove `SpreadType` import (doesn't exist in spread_model.py)

## Phase 2: Model Field Mismatches
- [ ] Fix `spread_model.py` - Add `SpreadType` enum for consistency
- [ ] Fix `monte_carlo.py` - Align result fields with `MonteCarloResult` model
- [ ] Fix `parameter_optimizer.py` - Align field names with `OptimizationConfig`/`OptimizationResult`
- [ ] Fix `walk_forward.py` - Align field names with `WalkForwardConfig`/`WalkForwardResult`

## Phase 3: Architecture/Consistency
- [ ] Fix `statistics.py` - Remove unused `EquitySnapshot` import
- [ ] Verify engine.py unused imports
- [ ] Validate async consistency

## Phase 4: Quality Gates
- [ ] Run `isort` 
- [ ] Run `black`
- [ ] Run `pytest`
- [ ] Generate coverage
- [ ] Generate final report

