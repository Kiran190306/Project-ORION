# ORION Known Limitations — v0.12.0-rc.1

## Functional Limitations

| # | Limitation | Impact | Planned Resolution |
|---|-----------|--------|-------------------|
| L-001 | Single Redis instance (no Sentinel/Cluster) | SPOF for cache/session; 15min RTO | v0.13.0 |
| L-002 | Manual canary deployment | No automated traffic shifting | v0.13.0 |
| L-003 | No automated chaos experiment execution | Requires manual `kubectl apply` | v0.13.0 |
| L-004 | Grafana dashboards provisioned but not auto-updated | Manual update on chart changes | v0.13.0 |
| L-005 | Cross-region DR requires manual DNS switch | Automatable via external-dns | v0.13.0 |

## Performance Limitations

| # | Limitation | Threshold | Notes |
|---|-----------|-----------|-------|
| P-001 | API P99 latency degrades above 1000 concurrent users | 250ms at 1000 users | Scale HPA before peak |
| P-002 | Database connection pool max at 150 connections | Soft limit | Increase db_max_overflow for spike |
| P-003 | Order book processing at 13,000 orders/sec | Hardware-dependent | Profile before scaling |

## Known Non-Issues

| Area | Status | Evidence |
|------|--------|----------|
| Helm chart idempotency | ✅ Verified | `helm template` output consistent |
| Migration backward compatibility | ✅ Verified | v0.11.x → v0.12.0 tested |
| Rollback | ✅ Verified | `helm rollback` tested |
| Data integrity during failover | ✅ Verified | WAL replication tested |
