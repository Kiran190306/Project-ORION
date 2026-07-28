# ADR-001: High Availability Topology

**Status**: Accepted
**Date**: 2024-07-27
**Version**: v0.13.0-dev

## Context

ORION v0.12.0 runs as a single-region deployment with 3+ replica sets. To achieve enterprise-grade availability, we need a formal HA topology that eliminates single points of failure at every layer.

## Decision

**Adopt Active-Passive Multi-AZ with Read Replicas** for the primary deployment, with Active-Active blueprint for future use.

## Topology

```
                   ┌─────────────────────────────┐
                   │  Global Load Balancer (DNS)   │
                   │  Route53 / Cloud DNS          │
                   └──────┬──────────────┬────────┘
                          │              │
              ┌───────────▼──────┐  ┌────▼──────────────┐
              │   Region A (ACTIVE)│  │  Region B (STANDBY)│
              │   us-east-1       │  │  us-west-2        │
              └────────┬──────────┘  └────────┬──────────┘
                       │                      │
              ┌────────▼──────────┐  ┌────────▼──────────┐
              │  AZ-1a  AZ-1b     │  │  AZ-2a  AZ-2b     │
              │  API    API       │  │  API    API       │
              │  DB(P)  DB(S)     │  │  DB(S)  DB(S)     │
              │  Redis   Redis    │  │  Redis   Redis    │
              │  Wkr     Wkr      │  │  Wkr     Wkr      │
              └───────────────────┘  └───────────────────┘
```

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| AZ strategy | 3 AZs per region | Standard AWS/EKS, balances cost vs resilience |
| Cross-region | Active-Passive | Lower complexity; Active-Active requires conflict resolution |
| Load balancer | Global DNS-based | Route53/Cloud DNS with health-check routing |
| Pod anti-affinity | Required | Spread across AZs via topologySpreadConstraints |
| PDB | minAvailable: 2 for API | Ensures N-1 tolerance per AZ |

## Failure Scenarios

| Failure | Impact | Mitigation |
|---------|--------|------------|
| 1 AZ down | N-1 capacity | Other AZs absorb traffic |
| 1 region down | Failover to standby | DNS switch + DB promote |
| 1 pod crash | No impact | K8s ReplicaSet auto-heals |

## Trade-offs

- Active-Passive has higher latency during failover (DNS TTL + DB promote)
- Active-Active would reduce RTO but increase complexity significantly
- 3 AZs increase cost ~50% over 2 but provide true N-1 resilience
