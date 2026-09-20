# PROJECT ORION — EPIC-018 PHASE 8: PRODUCTION DEPLOYMENT RUNBOOK

**Project**: Project ORION — Institutional Forex Trading Platform  
**Epic**: EPIC-018 — Production Operations, Reliability, Security Hardening & Release Freeze  
**Phase**: Phase 8 — Production Deployment Runbook  
**Date**: 2026-09-20  
**Target Platform**: Render Cloud Production (Git-driven Web Services)  
**Git Remote**: `https://github.com/Kiran190306/Project-ORION.git`  
**Standard**: 21 Canonical Production Deployment Gates  

---

## 1. Executive Summary

Phase 8 defines the canonical, step-by-step production deployment procedure for Project ORION. 

Render employs a **Git-driven Continuous Deployment** model: when code is committed and pushed to `origin/main`, Render automatically triggers Docker builds for `orion-api` and `orion-dashboard`. 

A deployment is **NEVER** considered complete merely because Render reports "Live". A deployment is only finalized after passing all 21 verification gates, including database migration verification, dependency health probes, security header enforcement, and cloud E2E validation.

---

## 2. Canonical 21-Gate Production Deployment Workflow

```
[ LOCAL PRE-FLIGHT ] ──► [ SECURITY & STATIC CHECKS ] ──► [ LOCAL TEST GATES ]
                                                                 │
[ CLOUD VERIFICATION ] ◄── [ RENDER DEPLOYMENT ] ◄── [ GIT SYNC & PUSH ]
         │
[ FINAL PRODUCTION SIGNOFF ]
```

### Stage 1: Pre-Flight & Workspace Inspection
- **Gate 01 — Branch & Worktree Verification**:
  Ensure the active branch is `main` and working copy is clean:
  ```bash
  git status
  # Must show: On branch main, nothing to commit, working tree clean
  ```
- **Gate 02 — Unrelated Work Preservation**:
  Verify no personal or scratch files are staged or inadvertently modified:
  ```bash
  git diff --stat
  ```
- **Gate 03 — Environment & Config Pre-Check**:
  Verify `ORION_WORKER_ENABLED="false"` in `render.yaml` and application defaults.

### Stage 2: Static Analysis, Linting & Type Safety
- **Gate 04 — Linter & Code Quality (Ruff / Black / isort)**:
  ```bash
  python -m ruff check apps/ libraries/ shared/
  ```
- **Gate 05 — Strict Type Checking (mypy)**:
  ```bash
  python -m mypy --config-file pyproject.toml
  ```
- **Gate 06 — Secret Scanning**:
  Scan for accidental credentials or `.env` files:
  ```bash
  python -c "import os, sys; assert not os.path.exists('.env'), 'Plaintext .env detected!'"
  ```

### Stage 3: Automated Test Verification
- **Gate 07 — Backend Unit & Domain Tests**:
  ```bash
  python -m pytest tests/unit/ -v
  ```
- **Gate 08 — Database Migration Integration Tests**:
  ```bash
  python -m pytest tests/integration/database/ -v
  ```
- **Gate 09 — Operational Readiness Tests**:
  ```bash
  python -m pytest tests/unit/test_operational_readiness.py -v
  ```
- **Gate 10 — Frontend Build Verification**:
  ```bash
  cd apps/dashboard && npm run build && cd ../..
  ```

### Stage 4: Container & Infrastructure Validation
- **Gate 11 — Dockerfile Multi-Stage Build Check**:
  Verify backend and frontend Dockerfiles build cleanly without cache corruption.
- **Gate 12 — Render Blueprint Validation**:
  Validate `render.yaml` against the Render CLI schema:
  ```bash
  render blueprints validate render.yaml
  # Expected: Valid: true (0 errors, 4 resources)
  ```

### Stage 5: Git Synchronization & Render Deployment
- **Gate 13 — Atomic Commit Creation**:
  Create single clean semantic commit:
  ```bash
  git add <intended_files>
  git commit -m "ops(epic-018): harden production operations and release freeze"
  ```
- **Gate 14 — Git Remote Push**:
  ```bash
  git push origin main
  # Must push cleanly without --force
  ```
- **Gate 15 — Remote Synchronization Verification**:
  ```bash
  git rev-parse HEAD
  git rev-parse origin/main
  # Both hashes must match exactly
  ```
- **Gate 16 — Render Build & Container Deployment**:
  Monitor Render build logs for `orion-api` and `orion-dashboard`. Verify both transition to `Live`.

### Stage 6: Cloud Post-Deployment Verification
- **Gate 17 — Process Liveness Probe**:
  ```bash
  curl -s -f https://orion-api-68u2.onrender.com/health/live
  # Expected: HTTP 200 {"status":"alive"}
  ```
- **Gate 18 — Dependency Readiness Probe**:
  ```bash
  curl -s -f https://orion-api-68u2.onrender.com/health/ready
  # Expected: HTTP 200 {"overall":"healthy","database":true,"redis":true}
  ```
- **Gate 19 — Observability & Prometheus Metrics**:
  ```bash
  curl -s -f https://orion-api-68u2.onrender.com/metrics
  # Expected: HTTP 200 text exposition containing orion_http_requests_total
  ```
- **Gate 20 — Dashboard & Security Headers Check**:
  ```bash
  curl -s -I https://orion-dashboard-6d3z.onrender.com
  # Expected: HTTP 200 with X-Frame-Options: DENY, CSP, X-Content-Type-Options
  ```
- **Gate 21 — Strict Paper Safety Confirmation**:
  Verify `is_live=false`, `capital_at_risk=$0.00`, and `orion_worker_status 0.0`.

---

## 3. Post-Deployment Decision Gate

If all 21 gates pass:
- Declare deployment **SUCCESSFUL**.
- Update release tag and documentation.

If any gate between 17 and 21 fails:
- Immediately initiate `docs/EPIC-018-ROLLBACK-RUNBOOK.md`.
- Halt user traffic routing.
