# ORION Network Topology

## Overview

```
                         ┌─────────────────────────────┐
                         │     Internet                 │
                         └─────────┬───────────────────┘
                                   │
                         ┌─────────▼───────────────────┐
                         │     CloudFront / CDN          │
                         │     (static assets)          │
                         └─────────┬───────────────────┘
                                   │
                         ┌─────────▼───────────────────┐
                         │     Global Load Balancer      │
                         │     (Route53 / Cloud DNS)     │
                         └─────────┬───────────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
     ┌────────▼────────┐  ┌───────▼────────┐  ┌───────▼────────┐
     │  Region A       │  │  Region B      │  │  Future Regions │
     │  us-east-1      │  │  us-west-2     │  │  eu-west-1 etc  │
     └────────┬────────┘  └───────┬────────┘  └───────┬────────┘
              │                    │                    │
     ┌────────▼────────┐  ┌───────▼────────┐           │
     │  External LB     │  │  External LB   │           │
     │  (NLB/ALB)       │  │  (NLB/ALB)     │           │
     └────────┬────────┘  └───────┬────────┘           │
              │                    │                    │
     ┌────────▼────────────────────▼────────────────────▼────────┐
     │                    Service Mesh (Istio/Linkerd)            │
     │                                                           │
     │  ┌───────────┐  ┌──────────┐  ┌─────────┐  ┌─────────┐  │
     │  │ API       │  │ Worker   │  │Schedule │  │ Ingress  │  │
     │  └─────┬─────┘  └────┬─────┘  └────┬────┘  └────┬────┘  │
     │        │              │             │             │       │
     │  ┌─────▼─────┐  ┌────▼─────┐  ┌────▼────┐  ┌────▼────┐ │
     │  │Pgbouncer   │  │Pgbouncer  │  │Pgbouncer│  │Pgbouncer│ │
     │  └─────┬─────┘  └────┬─────┘  └────┬────┘  └────┬────┘ │
     │        │              │             │             │       │
     │  ┌─────▼──────────────▼─────────────▼─────────────▼────┐ │
     │  │                    HAProxy                           │ │
     │  │                    │                                 │ │
     │  │          ┌─────────▼────────┐                       │ │
     │  │          │  PostgreSQL       │                       │ │
     │  │          │  Patroni + etcd   │                       │ │
     │  │          └───────────────────┘                       │ │
     │  │                                                      │ │
     │  │          ┌───────────────────┐                       │ │
     │  │          │  Redis Sentinel   │                       │ │
     │  │          │  (3 instances)    │                       │ │
     │  │          └───────────────────┘                       │ │
     └──────────────────────────────────────────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │    S3 Gateway      │
                    │    (storage)       │
                    └───────────────────┘
```

## Network Policies

### Default Deny
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
```

### API Ingress
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-ingress
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/component: api
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: istio-system
      ports:
        - port: 8080
  egress:
    - to:
        - podSelector:
            matchLabels:
              app.kubernetes.io/component: database
      ports:
        - port: 5432
    - to:
        - podSelector:
            matchLabels:
              app: redis
      ports:
        - port: 6379
```

## Service Dependencies

```
api ───→ database (5432)
api ───→ redis (6379)
api ───→ kafka (9092)
api ───→ jaeger (4318)
api ───→ prometheus (9090)

worker ───→ database (5432)
worker ───→ redis (6379)
worker ───→ kafka (9092)
worker ───→ s3 (443)

scheduler ───→ database (5432)
scheduler ───→ redis (6379)

database(P) ←→ database(S) (5432, streaming)
redis(P) ←→ redis(S) (6379, replication)
```

## Port Mapping

| Service | Port | Protocol | Ingress | Egress |
|---------|------|----------|---------|--------|
| API HTTP | 8080 | TCP | Istio | Cluster |
| API gRPC | 50051 | TCP | Istio | Cluster |
| API Metrics | 9090 | TCP | Prometheus | Cluster |
| PostgreSQL | 5432 | TCP | App only | Replicas |
| HAProxy | 5000/5001 | TCP | App only | DB |
| PgBouncer | 6432 | TCP | App only | HAProxy |
| Redis | 6379 | TCP | App only | Replicas |
| Sentinel | 26379 | TCP | Sentinel | Redis |
| Jaeger gRPC | 4318 | TCP | App | Jaeger |
| Prometheus | 9090 | TCP | Grafana | All |

## Cloud Provider Connectivity

### AWS (Primary)
- VPC: 10.0.0.0/16
- Public subnets: 10.0.1.0/24, 10.0.2.0/24, 10.0.3.0/24
- Private subnets: 10.0.10.0/24, 10.0.20.0/24, 10.0.30.0/24
- Transit Gateway for cross-region connectivity
- Direct Connect for on-premises connectivity (future)

### Cross-Region
- VPC Peering or Transit Gateway
- Encrypted VPN tunnels between regions
- Bandwidth: 10 Gbps minimum
- Latency: < 50ms us-east-1 to us-west-2
