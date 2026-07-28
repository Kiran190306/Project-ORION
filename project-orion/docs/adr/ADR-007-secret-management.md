# ADR-007: Secret Management

**Status**: Accepted
**Date**: 2024-07-27

## Context

ORION manages secrets across multiple environments (dev, staging, production) and multiple regions. GitOps requires that secrets are not stored in Git. We need a secure, auditable, and GitOps-compatible secret management solution.

## Decision

**Adopt external-secrets operator with AWS Secrets Manager / HashiCorp Vault as the backend.**

## Architecture

```
                   ┌─────────────────────────┐
                   │   Git Repository         │
                   │   (no secrets)           │
                   └─────────────────────────┘
                              │
                              ▼
                   ┌─────────────────────────┐
                   │  external-secrets        │
                   │  (K8s operator)         │
                   └──────────┬──────────────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
     ┌────────▼────────┐            ┌─────────▼─────────┐
     │  AWS Secrets     │            │  HashiCorp Vault  │
     │  Manager         │            │  (self-hosted)    │
     │  (Production)    │            │  (Dev/Staging)    │
     └─────────────────┘            └───────────────────┘
              │                               │
              └───────────────┬───────────────┘
                              │
                   ┌──────────▼──────────┐
                   │  K8s Secrets        │
                   │  (auto-synced)      │
                   └─────────────────────┘
```

## Secret Types

| Secret | Backend | Rotation | Access |
|--------|---------|----------|--------|
| DB credentials | AWS Secrets Manager | 30 days | Pod identity |
| Redis password | AWS Secrets Manager | 30 days | Pod identity |
| JWT signing keys | AWS Secrets Manager | Custom | Pod identity |
| API keys (external) | AWS Secrets Manager | Per contract | Pod identity |
| TLS certificates | cert-manager + Let's Encrypt | 90 days | Automated renewal |

## GitOps Integration

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: orion-database
spec:
  refreshInterval: "1h"
  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore
  target:
    name: orion-database-secret
    creationPolicy: Owner
  data:
    - secretKey: DATABASE_URL
      remoteRef:
        key: orion/production/database
        property: url
```

## Certificate Lifecycle

- cert-manager for automated TLS certificate provisioning
- Let's Encrypt production issuer for external endpoints
- Cluster internal CA for service mesh (mTLS)
- Auto-renewal 30 days before expiry

## IAM/RBAC

| Principal | Access Scope | Auth Method |
|-----------|-------------|-------------|
| Pods (K8s) | Pod identity / IRSA | AWS IAM roles for SA |
| Humans | Least privilege | OIDC + RBAC |
| CI/CD | Environment-specific | Service account tokens |
| Argo CD | Cluster-wide | OIDC + SSO (Dex) |

## Network Segmentation

- NetworkPolicies enforced at namespace level
- Default deny ingress/egress
- Service mesh (Istio/Linkerd) for mTLS between services
- Database access restricted to application pods only

## Trade-offs

- external-secrets adds CRD overhead and operational complexity
- AWS Secrets Manager costs $0.40/secret/month + API call costs
- Vault requires dedicated infrastructure for HA
- Secret rotation requires careful coordination with zero-downtime deploys
