# ORION Go-Live Guide

## Pre-Flight Checklist

- [ ] helm lint passes
- [ ] helm template succeeds
- [ ] All tests pass: `poetry run pytest`
- [ ] CI pipeline green
- [ ] Security scan clear
- [ ] All monitoring dashboards load
- [ ] Alertmanager configured
- [ ] Backup scripts verified
- [ ] DR drill completed
- [ ] Performance benchmarks met
- [ ] Chaos experiments pass

## Deployment

```bash
# Validate
helm lint deployment/helm/orion
helm template orion deployment/helm/orion

# Deploy
helm upgrade --install orion deployment/helm/orion \
  --namespace orion \
  --values deployment/helm/orion/values-production.yaml \
  --atomic --timeout 10m
```

## Post-Deployment

```bash
# Verify pods
kubectl get pods -n orion -w

# Health checks
curl https://api.orion.example.com/health/live
curl https://api.orion.example.com/health/ready

# Helm tests
helm test orion --namespace orion
```

## Smoke Tests

- [ ] API health returns 200
- [ ] Database connectivity verified
- [ ] Redis connectivity verified
- [ ] Order placement succeeds
- [ ] Market data streams
- [ ] Monitoring metrics visible
- [ ] Alerts fire correctly

## Rollback

```bash
helm rollback orion 1 --namespace orion
./backup/restore-database.sh /var/backups/orion/database/latest/
