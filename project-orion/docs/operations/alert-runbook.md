# ORION Alert Runbook

## Alert Triage

### Priority Levels

- **P0 (Critical)**: Service unavailable, data loss, security incident
- **P1 (High)**: Degraded performance, partial outage
- **P2 (Medium)**: Non-critical failure, warning threshold
- **P3 (Low)**: Informational, minor anomaly

## Alert Catalog

### API Alerts

#### OrionAPIUnavailable
- **Severity**: Critical (P0)
- **Description**: API job is down for > 1 minute
- **Runbook**: [API Unavailable](https://docs.orion.example.com/runbooks/api-unavailable)
- **Steps**:
  1. Check pod status: `kubectl get pods -n orion -l app.kubernetes.io/component=api`
  2. Check pod logs: `kubectl logs -n orion -l app.kubernetes.io/component=api`
  3. Check resource usage: `kubectl top pods -n orion`
  4. If OOMKilled, increase memory limits
  5. If CrashLoopBackOff, check recent deployment changes
  6. Restart if necessary: `kubectl rollout restart -n orion deployment/orion-api`

#### OrionAPIHighErrorRate
- **Severity**: Critical (P0)
- **Description**: API 5xx error rate > 5%
- **Runbook**: [High Error Rate](https://docs.orion.example.com/runbooks/high-error-rate)
- **Steps**:
  1. Check recent deployment changes
  2. Verify upstream services (database, Redis)
  3. Check for traffic spikes
  4. Inspect logs for error patterns
  5. Consider rolling back recent changes

#### OrionAPIHighLatency
- **Severity**: Warning (P1)
- **Description**: P95 latency > 2s or P99 latency > 5s
- **Runbook**: [High Latency](https://docs.orion.example.com/runbooks/high-latency)
- **Steps**:
  1. Check database query performance
  2. Verify Redis cache hit rates
  3. Check for network congestion
  4. Scale up if under load: `kubectl scale -n orion deployment/orion-api --replicas=X`

#### OrionAPIHealthEndpointFailure
- **Severity**: Critical (P0)
- **Description**: Health endpoint returning failures
- **Steps**:
  1. Verify health endpoint: `curl http://<pod-ip>:8080/health`
  2. Check for dependency failures
  3. Check database connectivity
  4. Check Redis connectivity

### Worker Alerts

#### OrionWorkerFailures
- **Severity**: Critical (P0)
- **Description**: Worker error rate > 0.1/s
- **Steps**:
  1. Check worker logs
  2. Verify message queue connectivity
  3. Check for poisoned messages
  4. Scale workers if queue is backing up

#### OrionJobQueueGrowth
- **Severity**: Warning (P1)
- **Description**: Queue depth > 100 for 5 minutes
- **Steps**:
  1. Increase worker count
  2. Check for stuck workers
  3. Verify downstream services
  4. Monitor queue depth trend

### Resource Alerts

#### OrionHighCPUUsage
- **Severity**: Warning (P1)
- **Description**: Node CPU > 85% for 5 minutes
- **Steps**:
  1. Check which pods are consuming CPU
  2. Verify resource limits
  3. Consider scaling or rescheduling

#### OrionHighMemoryUsage
- **Severity**: Warning (P1)
- **Description**: Node memory > 85%
- **Steps**:
  1. Check memory consumers
  2. Look for memory leaks
  3. Scale or evacuate node

#### OrionHighDiskUsage
- **Severity**: Warning (P1)
- **Description**: Node disk > 85%
- **Steps**:
  1. Clean up old logs
  2. Check PVC usage
  3. Expand disk or clean up

### Infrastructure Alerts

#### OrionPrometheusUnavailable
- **Severity**: Critical (P0)
- **Description**: Prometheus itself is down
- **Steps**:
  1. Check Prometheus pod: `kubectl get pods -n monitoring`
  2. Check Prometheus logs
  3. Verify storage availability
  4. Restart Prometheus if necessary

## Escalation Matrix

| Severity | Response Time | Escalation |
|----------|---------------|------------|
| Critical | 5 minutes | On-call engineer → Tech lead |
| Warning | 15 minutes | On-call engineer |
| Info | 1 hour | Team lead (business hours) |

