# ORION Multi-Region Guide

## Deployment Model: Active-Passive with Warm Standby

### Primary Region (Active)
- `us-east-1` — All services active
- Database: Read-write primary
- Market data: Real-time ingestion
- AI research: Full workloads
- Monitoring: Active alerting

### Secondary Region (Standby)
- `us-west-2` — All services running, no user traffic
- Database: Read-only replica (async WAL replication)
- Market data: Replicated from primary
- AI research: Idle (data available)
- Monitoring: Shadow alerting

## Region Architecture

```
                    ┌─────────────────────────────┐
                    │   Global Traffic Manager     │
                    │   (Route53 / Cloud DNS)      │
                    └──────┬──────────────┬────────┘
                           │              │
               ┌───────────▼──────┐  ┌────▼──────────────┐
               │   Region A       │  │   Region B         │
               │   us-east-1      │  │   us-west-2        │
               │                  │  │                    │
               │  ┌─ AZ1a ──┐    │  │  ┌─ AZ2a ──┐      │
               │  │ API x3   │    │  │  │ API x3   │      │
               │  │ DB (P)   │    │  │  │ DB (S)   │      │
               │  │ Redis(P) │    │  │  │ Redis(S) │      │
               │  │ Workers   │    │  │  │ Workers   │      │
               │  └──────────┘    │  │  └──────────┘      │
               │  ┌─ AZ1b ──┐    │  │  ┌─ AZ2b ──┐      │
               │  │ API x3   │    │  │  │ API x3   │      │
               │  │ DB (S)   │    │  │  │ DB (S)   │      │
               │  │ Redis(S) │    │  │  │ Redis(S) │      │
               │  └──────────┘    │  │  └──────────┘      │
               └──────────────────┘  └────────────────────┘
```

## DNS Strategy

| Record | Type | Value | TTL |
|--------|------|-------|-----|
| api.orion.example.com | CNAME | dualstack.primary-orion.example.com | 60s |
| api.orion.example.com (failover) | CNAME | dualstack.secondary-orion.example.com | 60s |
| *.orion.example.com | CNAME | Regional LB hostname | 300s |

## Traffic Routing Flow

```
User → api.orion.example.com (DNS)
       → Route53 health check on primary LB
         → Healthy: Route to us-east-1 LB
         → Unhealthy: Route to us-west-2 LB
           → LB distributes across AZs
             → Service mesh routes within region
```

## Failover Process

### Detection
- Route53 health check hits primary LB `/health/ready` every 10s
- 3 consecutive failures = unhealthy
- AWS CloudWatch alarm fires → PagerDuty

### Automation
```yaml
1. Health check fails 3x (30s)
2. Route53 updates DNS to secondary (60s TTL)
3. secondary DB replica promoted to primary (Patroni, ~30s)
4. Secondary ingress accepts traffic (immediate)
5. Monitoring verifies all services healthy
Total RTO: ~5 minutes
```

### Rollback
```yaml
1. Primary region restored
2. Database synced from secondary (WAL replay)
3. DNS switched back to primary (manual approval)
4. Secondary DB returns to read-replica mode
```

## Region Health Checks

```yaml
Primary region health:
  - API /health/live: must return 200
  - API /health/ready: must return 200 (probes)
  - Database connectivity: HAProxy port 5000
  - Redis connectivity: Sentinel port 26379
  - Cluster node count: >= 3

Secondary region health:
  - API /health/live: must return 200
  - API /health/ready: must return 200
  - Database replication lag: < 60s
  - DR readiness: all services running
```

## Data Replication Strategy

| Data Type | Method | Latency | RPO |
|-----------|--------|---------|-----|
| PostgreSQL | Async WAL streaming | < 5s | 5min |
| Redis | RDB shipping (hourly) | 1h | 1h |
| Market data | Kafka mirroring | < 1s | < 1s |
| Object storage | S3 cross-region replication | 15min | 15min |

## Future Expansion

| Region | Priority | Rationale |
|--------|----------|-----------|
| eu-west-1 | High | EU data residency (GDPR) |
| ap-southeast-1 | Medium | APAC latency optimization |
| sa-east-1 | Low | LATAM expansion |
