# PROJECT ORION — EPIC-018 PHASE 9: PRODUCTION ROLLBACK RUNBOOK

**Project**: Project ORION — Institutional Forex Trading Platform  
**Epic**: EPIC-018 — Production Operations, Reliability, Security Hardening & Release Freeze  
**Phase**: Phase 9 — Production Rollback Runbook  
**Date**: 2026-09-20  
**Target Platform**: Render Cloud Production  
**Safety Mandate**: Never execute `git reset --hard` or destructive database downgrades as casual rollback actions.  

---

## 1. Executive Summary & Rollback Principles

Phase 9 defines the operational protocols for safely rolling back defective software releases, configuration errors, or failed database migrations on Project ORION.

### Core Principles:
1. **Never Use `git reset --hard`**: Destroys local worktree history and creates divergence with shared remotes.
2. **Never Downgrade Production Databases Casually**: Schema rollbacks (`alembic downgrade -1`) can drop populated columns or truncate tables, causing irreversible data loss.
3. **Prefer Forward-Fix Over Blind Revert**: If a database schema change has been applied and user data has been written, author a forward-fixing migration (`alembic upgrade head`) rather than rolling back migrations.
4. **Decouple Application Rollback from Database Rollback**: Most rollbacks involve reverting container code to a previous image while keeping the database schema intact (additive migrations guarantee backward compatibility).

---

## 2. Rollback Tiers & Decision Matrix

| Rollback Tier | Trigger Condition | Rollback Mechanism | Expected Recovery Time (RTO) |
|---|---|---|:---:|
| **Tier 1: Render Dashboard Image Rollback** | Bad release, 5xx spike immediately following deploy, frontend bundle broken. | Render Console: "Rollback to previous deploy" | **< 3 minutes** |
| **Tier 2: Git Revert Rollback** | Release causes business logic error or subtle bug not caught in smoke tests. | `git revert <bad_commit>` followed by `git push origin main` | **< 10 minutes** |
| **Tier 3: Configuration Rollback** | Misconfigured environment variable (e.g. invalid CORS origin or log level). | Update variable in Render Dashboard / CLI and redeploy | **< 5 minutes** |
| **Tier 4: Database Forward-Fix** | Migration defect or constraint conflict causing runtime SQL errors. | Author new migration (`0008_...`), test, and deploy | **< 30 minutes** |
| **Tier 5: Full Disaster Recovery** | Database corruption or data loss event. | Execute logical restore from backup (`docs/EPIC-018-BACKUP-RECOVERY.md`) | **< 60 minutes** |

---

## 3. Step-by-Step Rollback Procedures

### Procedure 1: Rapid Render Image Rollback (Tier 1)
When an immediate post-deployment failure occurs:
1. Log into the Render Dashboard: `https://dashboard.render.com`.
2. Navigate to **Services** -> **`orion-api`** (or **`orion-dashboard`**).
3. Under the **Events / Deploys** tab, locate the previous successful deployment (e.g. commit `a26a168`).
4. Click the three dots `...` next to the previous deploy and select **Rollback to this deploy**.
5. Render immediately spins up the prior container image without recompiling or rebuilding Docker caches.
6. Verify recovery:
   ```bash
   curl -s -f https://orion-api-68u2.onrender.com/health/live
   curl -s -f https://orion-api-68u2.onrender.com/health/ready
   ```

---

### Procedure 2: Git Revert Rollback (Tier 2)
When code needs to be cleanly undone in source control without rewriting history:
1. Identify the bad commit hash: `git log -n 5 --oneline`.
2. Create an automated revert commit:
   ```bash
   git revert <bad_commit_hash> -m 1 --no-edit
   ```
3. Run local regression:
   ```bash
   python -m pytest tests/unit/ -q
   ```
4. Push the revert commit normally:
   ```bash
   git push origin main
   ```
5. Render detects the push and deploys the reverted codebase cleanly.

---

### Procedure 3: Database Migration Forward-Fix (Tier 4)
When a migration introduces an issue (e.g. missing index, too restrictive constraint):
1. **DO NOT run `alembic downgrade` in production**.
2. Inspect the failure in `database/migrations/versions/`.
3. Author a new additive forward migration:
   ```bash
   alembic revision -m "fix_adjust_constraint_forward"
   ```
4. Test upgrade against local PostgreSQL instance.
5. Commit and push:
   ```bash
   git commit -m "fix(db): add forward migration to resolve constraint conflict"
   git push origin main
   ```
6. On startup, the API runs `alembic upgrade head` and resolves the schema drift safely.

---

## 4. Post-Rollback Verification Checklist

Following any rollback action, execute the standard verification checklist:
- [ ] Process Liveness: `GET /health/live` returns HTTP 200.
- [ ] Dependency Readiness: `GET /health/ready` returns HTTP 200 (`database: true`, `redis: true`).
- [ ] Metrics Exporter: `GET /metrics` returns HTTP 200.
- [ ] Paper Safety Invariant: Confirm `is_live=False`, `capital_at_risk=$0.00`, and `orion_worker_status 0.0`.
- [ ] Post-Rollback Incident Log: Document the rollback trigger, root cause, and recovery duration.
