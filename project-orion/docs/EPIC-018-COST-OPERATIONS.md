# PROJECT ORION — EPIC-018 PHASE 11: COST & RESOURCE OPERATIONS

**Project**: Project ORION — Institutional Forex Trading Platform  
**Epic**: EPIC-018 — Production Operations, Reliability, Security Hardening & Release Freeze  
**Phase**: Phase 11 — Cost & Resource Operations  
**Date**: 2026-09-20  
**Target Platform**: Render Cloud Production  
**Current Plan Tier**: Free Tier (Development & Verification Baseline)  

---

## 1. Executive Summary

Phase 11 audits the resource utilization, scaling boundaries, operational constraints, and cost growth factors of Project ORION on Render Cloud. 

The current platform operates within Render's Free Plan tier across all 4 provisioned services. While this tier is ideal for functional verification, security testing, and paper-trading integration, institutional high-frequency execution and continuous multi-tenant SaaS scaling require upgrading to paid dedicated compute instances.

---

## 2. Provisioned Render Cloud Services & Resource Profiles

| Resource Name | Service Type | Plan Tier | CPU Allocation | RAM Allocation | Network / Storage Scope |
|---|---|:---:|:---:|:---:|---|
| `orion-api` | Web Service (Docker) | Free | Shared 0.5 CPU | 512 MB | Dynamic `$PORT` (10000); 15-min idle spin-down |
| `orion-dashboard` | Web Service (Docker) | Free | Shared 0.5 CPU | 512 MB | Nginx Alpine static serving; 15-min idle spin-down |
| `orion-postgres` | Managed PostgreSQL 15 | Free | Shared CPU | 256 MB RAM / 1 GB SSD | Private network only; max 100 connections; 30-day lifecycle |
| `orion-redis` | Managed Key-Value Redis 7 | Free | Shared CPU | 25 MB RAM | Private network only; eviction: `volatile-lru` |

---

## 3. Free-Tier Operational Constraints & Limitations

### 3.1. Container Spin-Down / Cold Starts
- **Behavior**: Render free-tier Web Services spin down to zero replicas after 15 minutes of inactivity.
- **Impact**: The first incoming HTTP request to `orion-api` or `orion-dashboard` after an idle period incurs a **30 to 50 second cold-start delay** while the container image is loaded and Uvicorn initializes.
- **Mitigation for Development**: External synthetic pingers (e.g. UptimeRobot or health check cron jobs) can emit periodic `GET /health/live` requests every 10 minutes to maintain container warmth during testing windows.

### 3.2. PostgreSQL Free-Tier Lifecycle
- **Constraint**: Render free-tier PostgreSQL databases expire or are suspended after 30 days unless upgraded to a paid plan.
- **Mitigation**: Automated logical backups (`pg_dump`) must be scheduled daily (as detailed in `docs/EPIC-018-BACKUP-RECOVERY.md`) to ensure zero data loss upon plan transitions.

### 3.3. Memory Bounding (512 MB RAM Ceiling)
- Python 3.11 with FastAPI and SQLAlchemy typically consumes ~120 MB idle and ~250 MB under concurrent load.
- If memory consumption exceeds 512 MB, Render's cgroup killer terminates the process with `Exit Code 137 (OOM)`.
- **Mitigation**: Pool size is strictly bounded (`pool_size=10`, `max_overflow=20`), and request body payloads are limited.

---

## 4. Scaling Upgrade Triggers & Commercial Roadmap

The transition from Free Tier to Render Team/Standard compute is governed by concrete technical triggers:

```
[ Free Tier: Development & Paper Verification ]
                    │
       Triggers: > 5 Concurrent Tenants OR
                 > 50 req/sec OR Cold-start elimination
                    ▼
[ Starter / Standard: 24/7 Always-On Compute ]
  - Dedicated CPU, 1-2 GB RAM per pod
  - 10 GB Persistent PostgreSQL SSD with automated daily backups
                    ▼
[ Pro / Enterprise: Multi-Pod Autoscaling ]
  - Horizontal pod autoscaling (2-5 replicas)
  - Dedicated Redis with automated replication
  - Zero spin-down guarantee
```

| Operational Milestone | Metric Trigger | Recommended Upgrade | Key Capability Unlocked |
|---|---|---|---|
| **Eliminate Cold Starts** | User onboarding begins | Upgrade `orion-api` & `orion-dashboard` to **Starter** | 24/7 always-on execution; instant response times. |
| **Data Retention Beyond 30 Days** | Production launch | Upgrade `orion-postgres` to **Starter** | Persistent SSD; automated 7-day backup retention. |
| **High-Frequency Ingestion** | Market tick stream active | Upgrade `orion-redis` to **Starter** | Dedicated cache memory; persistent snapshotting. |
| **Multi-Tenant Scale** | > 100 active organizations | Horizontal Autoscaling (Standard plan) | Multi-replica failover; zero-downtime rolling deploys. |

---

## 5. Cost-Risk Governance

1. **No Automatic Card Charges**: The repository contains zero automated cloud billing scripts or credit card hooks.
2. **Resource Right-Sizing**: Memory and connection pool allocations are locked in `render.yaml` and application configuration to prevent uncontrolled resource spikes.
3. **Billing Transparency**: Upgrades require explicit administrative authorization in the Render Web Dashboard.
