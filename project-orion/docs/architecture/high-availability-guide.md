# ORION High Availability Guide

## Architecture Overview

ORION runs as an Active-Passive multi-region deployment with 3 Availability Zones per region.

## HA Design Principles

1. **No single point of failure** at any layer
2. **N-1 capacity** per AZ (3 AZs = 66% load per AZ normal)
3. **Automatic recovery** from pod/node/AZ failures
4. **Graceful degradation** — partial functionality during partial failures
5. **RTO ≤ 15min** for cross-region failover
6. **RPO ≤ 5min** for database failover

## HA by Layer

### Compute (Kubernetes)

| Component | HA Mechanism | RTO |
|-----------|-------------|-----|
| API pods | ReplicaSet (min 3), PDB (minAvailable: 2) | <30s |
| Worker pods | ReplicaSet (min 2), PDB (minAvailable: 1) | <30s |
| Scheduler pods | ReplicaSet (min 1), PDB (minAvailable: 1) | <30s |
| Cluster API | Control plane HA (multi-master) | <5min |

### Pod Anti-Affinity

All deployments use `podAntiAffinity` to spread pods across AZs:

```yaml
podAntiAffinity:
  preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      podAffinityTerm:
        labelSelector:
          matchExpressions:
            - key: app.kubernetes.io/component
              operator: In
              values:
                - api
        topologyKey: kubernetes.io/hostname
```

### Database (PostgreSQL)

| Component | HA Mechanism | RTO |
|-----------|-------------|-----|
| Primary | Patroni automatic failover | <30s |
| Replicas | WAL streaming (sync/async) | — |
| Connection routing | HAProxy read/write split | <5s |
| Failover | Patroni + etcd consensus | <30s |

### Redis

| Component | HA Mechanism | RTO |
|-----------|-------------|-----|
| Primary | Sentinel automatic failover | <10s |
| Replicas | Master-replica replication | — |
| Failover detection | 2/3 Sentinel quorum | <5s |

### Network

| Component | HA Mechanism | RTO |
|-----------|-------------|-----|
| Ingress | Multiple replicas (nginx-ingress) | <30s |
| Load balancer | Cloud LB health checks | <60s |
| DNS | Route53 health checks + failover | <5min |
| Service mesh | mTLS, retries, circuit breakers | Instant |

## Failure Scenarios

### Single Pod Crash
- K8s ReplicaSet creates replacement
- Other pods serve traffic during transition
- No user impact

### Single AZ Failure (us-east-1a)
- Pods reschedule to remaining AZs (1b, 1c)
- Capacity degrades to N-1 (66% load per pod)
- Database replica in surviving AZ promoted if primary lost
- Kubernetes control plane unaffected (multi-AZ masters)

### Single Region Failure (us-east-1)
- DNS failover to us-west-2 (Route53 health check)
- Database replica in us-west-2 promoted to primary
- Full service resumes in standby region within 15 minutes
- RPO ≤ 5 minutes (asynchronous WAL replication)

## Monitoring HA Health

```yaml
Key metrics:
- kube_pod_status_ready{namespace="orion"}  # All pods ready?
- patroni_primary_replica  # Which node is DB primary?
- redis_master_status  # Which node is Redis primary?
- haproxy_backend_servers_status  # Connection pool healthy?
- route53_health_check_status  # DNS routing correct?
