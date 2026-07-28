# ORION Chaos Engineering Guide

## Principles

1. **Blast radius**: Start with single pod, scale up gradually
2. **Metrics-driven**: Measurable success criteria per experiment
3. **Automated recovery**: Rollback on failure
4. **Blameless**: Find system weaknesses

## Scenarios

### 1. Pod Failure
```bash
kubectl delete pod -n orion -l app.kubernetes.io/component=api
```
**Expected**: Pod restarts within 30s, zero dropped requests

### 2. Node Failure
```bash
kubectl cordon <node> && kubectl drain <node> --ignore-daemonsets
```
**Expected**: Pods reschedule within 5 min

### 3. Network Partition (via Chaos Mesh)
```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: network-partition
spec:
  action: partition
  mode: all
  selector:
    namespaces: [orion]
  direction: both
```
**Expected**: Circuit breakers, retries, graceful degradation

### 4. DNS Failure
```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: DNSChaos
metadata:
  name: dns-failure
spec:
  action: error
  selector:
    namespaces: [orion]
  patterns: ["*"]
```
**Expected**: DNS caching handles failures

### 5. Disk Pressure
```bash
dd if=/dev/zero of=/tmp/fill-disk bs=1M count=1024
```
**Expected**: Pods with PVCs move to other nodes, no data loss

### 6. Memory Pressure
```bash
kubectl exec -n orion <pod> -- stress --vm 2 --vm-bytes 512M --timeout 60
```
**Expected**: OOM kills process, pod restarts, limits enforced

### 7. CPU Starvation
```bash
kubectl exec -n orion <pod> -- stress --cpu 4 --timeout 60
```
**Expected**: CPU throttled, QoS preserved

### 8. Database Unavailable
```bash
kubectl apply -f networkpolicy-block-db.yaml
```
**Expected**: Connection pooling, retries, 503 instead of crash

### 9. Redis Unavailable
```bash
kubectl scale statefulset/redis -n orion --replicas=0
```
**Expected**: Fallback to direct DB queries, degraded but functional

### 10. API Unavailable
```bash
kubectl apply -f networkpolicy-block-api.yaml
```
**Expected**: Workers continue processing existing jobs

## Experiment Execution

```bash
chaos run experiments/<scenario>.yaml
kubectl get pods -n orion -w
kubectl logs -n orion -l app.kubernetes.io/component=api
chaos rollback experiments/<scenario>.yaml
```

## Success Criteria

- P0 services ≥ 99.9% availability during experiments
- Error budget consumption < 10% per experiment
- Auto-recovery within defined RTOs
- No data loss
