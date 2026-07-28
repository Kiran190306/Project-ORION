# ORION Disaster Recovery Guide

## Recovery Objectives

| Tier | Component | RTO | RPO |
|------|-----------|-----|-----|
| Tier 0 | API Gateway | 5 min | N/A (stateless) |
| Tier 0 | API Deployment | 5 min | N/A (stateless) |
| Tier 1 | PostgreSQL | 30 min | 5 min |
| Tier 1 | Redis | 15 min | 1 min |
| Tier 2 | Worker | 15 min | N/A (stateless) |
| Tier 2 | Scheduler | 15 min | N/A (stateless) |
| Tier 3 | Monitoring | 60 min | 15 min |
| Tier 3 | Dashboards | 60 min | N/A |

## Failure Scenarios & Runbooks

### Scenario 1: Single Pod Crash
**Detection**: Pod crash loop, liveness probe failure
**Response**: Kubernetes auto-restarts (default)
**RTO**: < 30 seconds
**Runbook**:
```
kubectl get pods -n orion
kubectl logs -n orion <pod-name> --previous
kubectl describe pod -n orion <pod-name>
```

### Scenario 2: Node Failure
**Detection**: Node NotReady, Pod evictions
**Response**: Pods reschedule to healthy nodes
**RTO**: < 5 minutes
**Runbook**:
```
kubectl get nodes
kubectl describe node <failed-node>
kubectl get pods -n orion --field-selector=spec.nodeName=<failed-node>
# Pods will be rescheduled automatically by K8s
```

### Scenario 3: Database Failure
**Detection**: Connection errors, pg_isready failure
**Response**: Failover to replica or restore from backup
**RTO**: 30 min | **RPO**: 5 min
**Runbook**:
```
# Check replica status
psql -h <replica-host> -c "SELECT pg_is_in_recovery();"

# Promote replica if available
psql -h <replica-host> -c "SELECT pg_promote();"

# Or restore from latest backup
./backup/restore-database.sh /var/backups/orion/database/$(date +%Y-%m-%d)/orion-db-full-*.dump.gz
```

### Scenario 4: Redis Failure
**Detection**: Connection refused, replication lag
**Response**: Restart or restore from RDB
**RTO**: 15 min | **RPO**: 1 min
**Runbook**:
```
# Check Redis status
redis-cli -h <redis-host> ping

# Restart Redis
kubectl rollout restart statefulset/redis -n orion

# Restore from backup
./backup/restore-redis.sh /var/backups/orion/redis/$(date +%Y-%m-%d)/orion-redis-*.rdb.gz
```

### Scenario 5: Network Partition
**Detection**: Increased error rates, connectivity failures
**Response**: Pods in other AZ/host handle traffic
**RTO**: 0 (multi-AZ deployment)
**Runbook**:
```
# Verify cluster connectivity
kubectl get nodes --show-labels | grep topology.kubernetes.io/zone
kubectl get pods -n orion -o wide

# Check network policies
kubectl describe networkpolicy -n orion
```

### Scenario 6: Regional Failure
**Detection**: Entire region unavailable
**Response**: Failover to secondary region
**RTO**: 15 min | **RPO**: 5 min
**Runbook**:
```
# Switch DNS to secondary region
kubectl config use-context orion-secondary

# Verify secondary region state
kubectl get all -n orion

# Restore database from cross-region backup
./backup/restore-database.sh s3://orion-backups-dr/database/latest/
```

## Recovery Validation

After each recovery, validate:
1. `helm test orion deployment/helm/orion`
2. API health endpoint returns 200
3. Database connectivity: `pg_isready`
4. Redis connectivity: `redis-cli ping`
5. Prometheus targets are UP
6. Grafana dashboards load
7. Jaeger traces are visible
8. Alertmanager fires test alert

## Backup Verification Schedule

- **Daily**: Automated restore test to verify backup integrity
- **Weekly**: Full DR drill including failover
- **Monthly**: Regional failover exercise
