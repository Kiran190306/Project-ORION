# ADR-005: GitOps Architecture

**Status**: Accepted
**Date**: 2024-07-27

## Context

ORION deployments are currently managed via `helm upgrade --install`. To achieve reliable, auditable, and reproducible deployments across multi-region environments, we need a GitOps workflow.

## Decision

**Adopt Argo CD** as the GitOps operator.

## Rationale

| Factor | Argo CD | Flux v2 |
|--------|---------|---------|
| UI/UX | Excellent dashboard | CLI-focused |
| Multi-cluster | Native support | Requires Kustomize |
| Sync strategies | Manual/auto, prune, hooks | Similar |
| SSO integration | Built-in (Dex/OIDC) | Manual setup |
| Community adoption | Market leader | Growing fast |
| Helm support | Native | Native |

## Architecture

```
                   ┌────────────────────────────┐
                   │    Git Repository           │
                   │    orion-deployment         │
                   │    ├── base/                │
                   │    ├── overlays/            │
                   │    │   ├── dev/             │
                   │    │   ├── staging/         │
                   │    │   └── prod/            │
                   │    └── cluster/             │
                   └──────────┬─────────────────┘
                              │ (webhook/poll)
                              ▼
                   ┌────────────────────────────┐
                   │      Argo CD               │
                   │   (cluster-1)              │
                   └──┬──────────────┬──────────┘
                      │              │
              ┌───────▼──────┐ ┌─────▼────────┐
              │  Namespace   │ │  Helm Release │
              │  orion       │ │  orion        │
              │  Dev         │ │  version      │
              │  Staging     │ │  values-prod  │
              │  Production  │ │               │
              └──────────────┘ └──────────────┘
```

## Environment Promotion

```yaml
dev:     branch: develop    → auto-sync
staging: branch: release/*  → auto-sync after CI
prod:    branch: main       → manual sync (approval gate)
```

## Drift Detection

- Argo CD compares live cluster state vs Git manifests every 3 minutes
- Drift detected: auto-sync enabled for dev/staging, manual for prod
- Notifications on drift via Alertmanager webhook

## Rollback Strategy

```bash
argocd app rollback orion-production <revision>
helm rollback orion 1 --namespace orion  # fallback
```

## Repository Structure

```
orion-deployment/
├── base/
│   └── kustomization.yaml
├── overlays/
│   ├── dev/
│   │   └── kustomization.yaml
│   ├── staging/
│   │   └── kustomization.yaml
│   └── production/
│       ├── kustomization.yaml
│       └── helm-release.yaml
├── cluster/
│   ├── region-a/
│   │   └── argo-app.yaml
│   └── region-b/
│       └── argo-app.yaml
└── apps/
    └── orion.yaml
```

## Trade-offs

- Argo CD requires cluster-level RBAC permissions
- Git as single source of truth means secrets must be managed externally
- Additional operational overhead for Argo CD itself (HA deployment)
