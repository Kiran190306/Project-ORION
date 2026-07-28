# ORION Operational Checklist

## Daily Operations

- [ ] Verify all pods Running: `kubectl get pods -n orion`
- [ ] Check cluster node health: `kubectl get nodes`
- [ ] Review recent alerts: Alertmanager UI
- [ ] Verify Prometheus targets are UP
- [ ] Check backup logs for failures
- [ ] Review error budgets (SLO compliance)
- [ ] Verify Jaeger trace sampling rate
- [ ] Check database replication lag

## Weekly Operations

- [ ] Run full backup restore verification
- [ ] Review dependency audit reports
- [ ] Update Grafana dashboard if needed
- [ ] Review security scan results
- [ ] Rotate any expiring secrets
- [ ] Audit Helm chart for drift
- [ ] Review resource utilization trends

## Monthly Operations

- [ ] Execute chaos experiment (rotate scenarios)
- [ ] Run full DR drill (including cross-region)
- [ ] Review and update RTO/RPO targets
- [ ] Patch base images (re-build Dockerfile)
- [ ] Update dependencies (poetry update + npm update)
- [ ] Review and update risk register
- [ ] Full performance benchmark run
- [ ] Review and archive audit logs

## Incident Response

- [ ] Acknowledge alert (PagerDuty/OpsGenie/Slack)
- [ ] Assess severity and impact
- [ ] Execute runbook from disaster-recovery-guide.md
- [ ] Communicate status to stakeholders
- [ ] Document post-mortem
- [ ] Update runbook if gaps found
