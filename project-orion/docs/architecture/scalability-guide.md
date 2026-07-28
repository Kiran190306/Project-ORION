# ORION Scalability Guide

## Scalability Dimensions

1. **Horizontal scaling** — More replicas (HPA)
2. **Vertical scaling** — More resources per pod (VPA)
3. **Cluster scaling** — More nodes (Cluster Autoscaler)
4. **Data scaling** — Read replicas / sharding

## Scaling Strategy by Component

### API Server
```
Method: HPA (CPU 70%, Memory 80%)
Min replicas: 3
Max replicas: 20
Scale-up: 3 pods / 30s (aggressive)
Scale-down: 1 pod / 5min (conservative)
```

### Worker
```
Method: HPA (custom metric: orion_queue_depth)
Min replicas: 2
Max replicas: 10
Scale trigger: Average queue depth > 100
```

### Scheduler
```
Method: HPA (custom metric: scheduled_jobs_pending)
Min replicas: 1
Max replicas: 5
```

### PostgreSQL
```
Method: Read replicas + connection pooling
Read scaling: Add replicas (up to 5 per region)
Write scaling: Vertical (larger instance)
Connection pooling: PgBouncer (pool_size: 100)
```

### Redis
```
Method: Vertical scaling (larger instance)
Read scaling: Add replicas via Sentinel
Memory limit: 75% of instance RAM
```

## HPA Configuration Reference

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: orion-api
  namespace: orion
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: orion-api
  minReplicas: 3
  maxReplicas: 20
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
        - type: Pods
          value: 3
          periodSeconds: 30
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Pods
          value: 1
          periodSeconds: 60
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
```

## Cluster Autoscaler

```yaml
Node pools:
  orion-spot:
    instance: c5.xlarge
    min: 3
    max: 20
    use: stateless (api, worker, scheduler)
  orion-ondemand:
    instance: r5.xlarge
    min: 3
    max: 10
    use: stateful (db, redis)
```

## Predictive Scaling

Before market open (08:00 UTC), pre-scale to expected peak:
```yaml
Cron-based HPA overrides:
  06:00 UTC → minReplicas: 5 (pre-market ramp)
  08:00 UTC → minReplicas: 10 (market open)
  16:00 UTC → minReplicas: 5 (post-market cool)
  20:00 UTC → minReplicas: 3 (overnight)
```

## Capacity Planning

| Component | Baseline | Peak | Growth Rate |
|-----------|----------|------|-------------|
| API | 3 pods | 20 pods | +30% YoY |
| Worker | 2 pods | 10 pods | +50% YoY |
| DB storage | 100GB | 500GB | +100% YoY |
| Redis memory | 4GB | 16GB | +50% YoY |
| Cluster nodes | 6 | 30 | +30% YoY |

## Performance Benchmarks

| Scenario | v0.12.0 | v0.13.0 Target |
|----------|---------|----------------|
| 100 users | 45ms avg | <40ms avg |
| 500 users | 52ms avg | <50ms avg |
| 1000 users | 68ms avg | <60ms avg |
| 2000 users | — | <100ms avg (new) |
| Peak order rate | 13,000/s | 20,000/s |
