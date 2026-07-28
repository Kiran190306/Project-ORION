# ORION Risk Register

## Active Risks

| ID | Category | Risk | Likelihood | Impact | Severity | Mitigation | Owner |
|----|----------|------|-----------|--------|----------|-----------|-------|
| RISK-001 | Infrastructure | Single node failure causes pod eviction | Medium | High | High | PDB, multi-AZ, anti-affinity | Platform |
| RISK-002 | Infrastructure | Availability Zone outage | Low | Critical | High | Cross-region DR, RTO <15min | Platform |
| RISK-003 | Data | Database corruption | Low | Critical | High | WAL archiving, daily backups, verification | Data |
| RISK-004 | Data | Redis data loss on restart | Low | Medium | Medium | AOF + RDB persistence, hourly backups | Data |
| RISK-005 | Security | Zero-day vulnerability in dependency | Medium | Medium | Medium | Weekly scans, automated patching | Security |
| RISK-006 | Security | Secret leakage in CI logs | Low | High | High | Gitleaks scanning, secret rotation | Security |
| RISK-007 | Operations | Configuration drift across environments | Low | Medium | Medium | GitOps, Helm values in version control | Ops |
| RISK-008 | Operations | Backup restore failure | Low | Critical | High | Daily restore verification tests | Ops |
| RISK-009 | Network | DNS resolution failure | Low | Medium | Medium | DNS caching, multiple upstream resolvers | Network |
| RISK-010 | Network | Network partition between services | Low | High | High | Circuit breakers, retries, timeouts | Platform |

## Residual Risks (Accepted)

| ID | Risk | Rationale | Review Date |
|----|------|-----------|-------------|
| ACC-001 | Market data latency during peak | Current P99 is within SLA (12ms < 15ms target) | Next sprint |
| ACC-002 | Single Redis instance SPOF | Redis Sentinel not deployed; acceptable for alpha | v0.13.0 |
| ACC-003 | No automated canary deployment | Manual traffic shift; budget for CI runner | v0.13.0 |
