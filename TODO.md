# TODO - ORION Quality Gate Sprint

## Remaining failures (6)
### A) Architecture boundary tests (3)
1. Fix internal import boundary violations in `shared/` and `libraries/`.
2. Ensure package markers: every directory under `shared/`, `libraries/infrastructure/`, `libraries/data/` contains `__init__.py`.
3. Ensure monorepo-root importability: `importlib.import_module(<computed module name>)` works for all EPIC public modules.

### B) StructuredLogger compatibility (2)
4. Locate `StructuredLogger` implementation and adjust method names/signatures/return types to satisfy tests.

### C) RiskRewardRatio calculation (1)
5. Adjust `RiskRewardRatio.ratio` to match contract expectations in tests (rounding/precision).

## Workflow requirement
- Fix one failing test at a time.
- Run pytest after each fix.
- Do not redesign architecture; do not implement new features.

