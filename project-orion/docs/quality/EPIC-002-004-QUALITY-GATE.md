# EPIC-002--004 Quality Gate

Status: **blocked** pending a functional Python 3.11 environment and remediation of the findings below. This report does not authorize or introduce EPIC-005 work.

## Scope reviewed

All Python modules under `shared/`, `libraries/infrastructure/`, and `libraries/data/` were inventoried. Contract tests were added for shared value objects, validators, events, serialization envelopes, versioning, infrastructure configuration, service registration, DI, health, event delivery, data schemas, validators, serialization, compression, cache, storage, and static package boundaries.

## Validation status

The local Python launcher resolves to the Windows Store shim and cannot start (`A specified logon session does not exist`). Poetry, pytest, Black, isort, mypy, and pylint are unavailable. Consequently, formatter, import, type, test, and coverage commands could not run locally. The new tests are intentionally executable by the existing CI commands once Python 3.11 and Poetry are available.

## Blocking findings

1. Nine infrastructure imports use `infrastructure.*`, but the declared source tree exposes `libraries.infrastructure.*`. This violates the package boundary and prevents normal monorepo-root imports. A static architecture test now records every violation.
2. `libraries.data.schemas.SymbolMetadata` declares default factories for `DaylightSavingConfig`, `MarginRequirements`, `CommissionStructure`, and `SwapRates`, although each factory requires constructor arguments. Constructing `SymbolMetadata` with its advertised defaults raises `TypeError`.
3. `shared.validators` calls `isinstance(result, success)` and uses `case success(...)` / `case failure(...)`, where `success` and `failure` are functions rather than Result classes. The public validators therefore cannot reliably return the documented Result contract.
4. Data-platform dependency wiring is inconsistent: `libraries.data.datasets` imports `QualityChecker` from `libraries.data.quality`, while it is defined in `libraries.data.validators`.
5. The data-schema file imports unused shared domain types and constants; several schema defaults are incomplete, so the data foundation is not import-safe as a whole.

## Non-blocking quality debt

- The JavaScript SDK build, direct-root ESLint invocation, and checked Prettier formatting pass. The `npm run lint` workspace command still fails because the root ESLint configuration uses a repository-relative `parserOptions.project` path that becomes invalid under the SDK workspace.
- Cache TTL values are stored but never evaluated by `InMemoryCache`; an expiry behavior test should remain red until that declared contract is implemented.

## Coverage and readiness

No trustworthy coverage percentage can be claimed before the interpreter issue is fixed. The test suite substantially expands the covered contract surface, but the 90% targets are unverified and cannot be certified. EPIC-002 is partially test-covered; EPIC-003 and EPIC-004 are blocked by import/boundary and schema-contract defects.

Readiness score for EPIC-005: **25/100**. The architecture freeze must be respected: the findings should be triaged and corrected as an explicit remediation task before beginning EPIC-005.
