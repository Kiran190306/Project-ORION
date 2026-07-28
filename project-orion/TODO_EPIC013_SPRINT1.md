# EPIC-013 Sprint 1 — HA Infrastructure Implementation

## Phase 1 — PostgreSQL HA (Patroni)
- [ ] templates/patroni-statefulset.yaml
- [ ] templates/patroni-configmap.yaml
- [ ] templates/patroni-service.yaml (HAProxy)
- [ ] templates/patroni-pdb.yaml

## Phase 2 — Redis HA (Sentinel)
- [ ] templates/redis-statefulset.yaml
- [ ] templates/redis-sentinel-deployment.yaml
- [ ] templates/redis-service.yaml
- [ ] templates/redis-pdb.yaml

## Phase 3 — Argo CD
- [ ] templates/argocd-project.yaml
- [ ] templates/argocd-application.yaml

## Phase 4 — External Secrets
- [ ] templates/external-secret-store.yaml
- [ ] templates/external-secret.yaml

## Phase 5 — Multi-Region
- [ ] templates/region-configmap.yaml
- [ ] values-region-a.yaml
- [ ] values-region-b.yaml

## Phase 6 — Autoscaling
- [ ] Update templates/hpa.yaml (VPA recommender)
- [ ] Review resource requests/limits

## Phase 7 — Values Update
- [ ] Update values.yaml with new sections
- [ ] Update values-dev.yaml
- [ ] Update values-staging.yaml
- [ ] Update values-production.yaml

## Phase 8 — Operations Guides
- [ ] docs/operations/patroni-guide.md
- [ ] docs/operations/redis-sentinel-guide.md
- [ ] docs/operations/argocd-guide.md
- [ ] docs/operations/external-secrets-guide.md
- [ ] docs/operations/failover-test-guide.md

## Phase 9 — Validation
- [ ] helm lint deployment/helm/orion
- [ ] helm template orion deployment/helm/orion
