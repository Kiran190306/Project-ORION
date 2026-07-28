# ORION GitOps Guide

## Tool: Argo CD

Argo CD is the GitOps operator for ORION. It manages all Kubernetes manifests and Helm charts across all environments and regions.

## Architecture

```
                    ┌──────────────────────────────┐
                    │   Git Repository             │
                    │   github.com/orion/deploy    │
                    │                              │
                    │   branches:                  │
                    │   ├── main (production)      │
                    │   ├── release/* (staging)    │
                    │   └── develop (dev)          │
                    └──────────┬───────────────────┘
                               │ (webhook / 3min poll)
                               ▼
                    ┌──────────────────────────────┐
                    │   Argo CD (cluster-1)        │
                    │                              │
                    │   Applications:              │
                    │   ├── orion-dev              │
                    │   ├── orion-staging          │
                    │   └── orion-production       │
                    └──┬───────────────────────┬───┘
                       │                       │
              ┌────────▼────────┐    ┌─────────▼─────────┐
              │  Cluster us-east-1│   │  Cluster us-west-2 │
              │  ├─ orion-prod   │   │  ├─ orion-prod      │
              │  ├─ monitoring   │   │  ├─ monitoring      │
              │  └─ istio-system │   │  └─ istio-system    │
              └─────────────────┘   └────────────────────┘
```

## Repository Structure

```
orion-deployment/
├── apps/
│   └── orion.yaml              # App of Apps
├── base/
│   ├── kustomization.yaml
│   ├── namespace.yaml
│   ├── serviceaccount.yaml
│   └── ...
├── overlays/
│   ├── dev/
│   │   ├── kustomization.yaml
│   │   └── values-dev.yaml
│   ├── staging/
│   │   ├── kustomization.yaml
│   │   └── values-staging.yaml
│   └── production/
│       ├── kustomization.yaml
│       ├── values-production.yaml
│       └── helm-release.yaml
├── cluster/
│   ├── region-a/
│   │   ├── orion-app.yaml
│   │   └── monitoring-app.yaml
│   └── region-b/
│       ├── orion-app.yaml
│       └── monitoring-app.yaml
└── infrastructure/
    ├── argo-cd/
    ├── cert-manager/
    ├── external-secrets/
    ├── istio/
    ├── monitoring/
    └── redis-sentinel/
```

## Environment Promotion

```yaml
develop branch:
  - Auto-sync to orion-dev namespace
  - No manual approval required
  - Deployed after CI passes

release/* branch:
  - Auto-sync to orion-staging namespace
  - Requires CI + integration tests pass
  - Pre-production validation runs

main branch:
  - Manual sync to orion-production namespace
  - Requires approval from 2+ platform engineers
  - Change request + post-deployment validation
```

## Argo CD Application Definition

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: orion-production
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/orion/deploy
    targetRevision: main
    path: overlays/production
  destination:
    server: https://kubernetes.default.svc
    namespace: orion
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
      - ApplyOutOfSyncOnly=true
  sync:
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
```

## Drift Detection

Argo CD compares desired state (Git) vs live state (cluster) every 3 minutes.

| Condition | Action |
|-----------|--------|
| Git has new commits | Auto-sync (dev/staging), notification (production) |
| Live state drifts (manual `kubectl edit`) | Auto-sync restores Git state (dev/staging) |
| Live state drifts (configmap generated) | Notification sent, manual review required |
| Helm values change | Full re-render + sync |

## Rollback Strategy

```bash
# Argo CD rollback (preferred)
argocd app rollback orion-production --prune

# Helm rollback (fallback)
helm rollback orion 1 --namespace orion

# Git revert (long-term fix)
git revert HEAD
git push origin main
# Argo CD syncs reverted state
```

## Secrets Management

Secrets are NOT stored in Git. The GitOps workflow uses `external-secrets` operator:

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: orion-database
  namespace: orion
spec:
  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore
  target:
    name: orion-database-secret
  data:
    - secretKey: DATABASE_URL
      remoteRef:
        key: orion/production/database
        property: url
```

## Multi-Cluster Management

Argo CD manages multiple Kubernetes clusters across regions:

```bash
# Add cluster
argocd cluster add context-us-east-1
argocd cluster add context-us-west-2

# Sync to specific cluster
argocd app sync orion-production --server https://us-east-1.example.com
```

## Monitoring Argo CD

| Metric | Description | Alert |
|--------|-------------|-------|
| Sync status | OutOfSync for > 5min | P2 alert |
| Health status | Degraded for > 2min | P1 alert |
| Sync duration | > 10min | P3 alert |
| Argo CD pod | Not running | P1 alert |
