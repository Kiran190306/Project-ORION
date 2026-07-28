# ADR-006: Autoscaling Strategy

**Status**: Accepted
**Date**: 2024-07-27

## Context

ORION must handle variable trading workloads with rapid spikes during market events and predictable daily patterns. Cost optimization requires scaling down during off-hours.

## Decision

**HPA (Horizontal Pod Autoscaler) + VPA (Vertical Pod Autoscaler) + Cluster Autoscaler**

## Strategy Per Component

| Component | HPA | VPA | Cluster Autoscaler |
|-----------|-----|-----|-------------------|
| API Server | ✅ CPU+Memory | ✅ Recommender only | ✅ |
| Worker | ✅ Custom metrics (queue depth) | ✅ Recommender only | ✅ |
| Scheduler | ✅ Custom metrics | ❌ Static | ✅ |
| Database | ❌ Manual scaling | ❌ | ❌ (StatefulSet) |
| Redis | ❌ Manual scaling | ❌ | ❌ (StatefulSet) |

## HPA Configuration

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
spec:
  minReplicas: 3
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
    - type: Pods
      pods:
        metric:
          name: orion_queue_depth
        target:
          type: AverageValue
          averageValue: "100"
```

## VPA Configuration

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: orion-api
  updatePolicy:
    updateMode: "Off"  # Recommender only
```

## Cluster Autoscaler

- Integrates with Karpenter or standard Cluster Autoscaler
- Node pool: `orion-spot` for stateless, `orion-ondemand` for stateful
- Scale-down: 5 minute cooldown
- Schedule-based scale-up before market open

## Scaling Schedule

```yaml
00:00-06:00 UTC: Low volume (min replicas)
06:00-09:00 UTC: Pre-market ramp-up (predictive)
09:00-16:00 UTC: Peak hours (full HPA active)
16:00-20:00 UTC: Post-market cooldown
20:00-24:00 UTC: Maintenance window
```

## Trade-offs

- HPA by CPU alone can miss latency-driven scaling needs
- VPA in "Off" mode requires manual approval of recommendations
- Cluster Autoscaler adds 30-90s node provisioning latency
- Custom metrics (queue depth) requires Prometheus adapter
