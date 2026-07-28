# ADR-003: Database High Availability

**Status**: Accepted
**Date**: 2024-07-27

## Context

PostgreSQL is the primary data store for ORION. It must be highly available with automatic failover, read scalability, and zero data loss during region failover.

## Decision

**Deploy PostgreSQL with Patroni + HAProxy + WAL streaming replication.**

## Architecture

```
                    ┌──────────────┐
                    │   HAProxy     │
                    │  (port 5000)  │
                    └──┬───┬───┬───┘
                       │   │   │
              ┌────────▼──┐ │ ┌▼────────┐
              │  Primary   │ │ │ Replica 1│
              │  (RW)      │ │ │ (RO)     │
              └────────────┘ │ └──────────┘
                             │
                      ┌──────▼──────┐
                      │  Replica 2  │
                      │  (RO/async) │
                      │  (DR ready) │
                      └─────────────┘
```

## Component Details

| Component | Role | Details |
|-----------|------|---------|
| Patroni | HA management | Automatic failover, DCS-backed (etcd/Consul) |
| HAProxy | Connection routing | Read/write split, health checks |
| WAL Streaming | Replication | Synchronous for AZ, Async for cross-region |
| etcd | DCS | Distributed consensus for Patroni leader election |

## Failover Process

1. Patroni detects primary failure via DCS lease expiry
2. Replica with highest LSN promoted to primary
3. HAProxy configuration updated to route write traffic
4. Former primary rejoins as replica on recovery
5. Application retries via HAProxy (no connection string changes)

**Automatic failover**: < 30 seconds
**Manual intervention**: Not required for single-node failure

## Read Replicas

- **AZ-local**: Synchronous replication for zero data loss
- **Cross-region**: Asynchronous replication for DR standby
- **Read routing**: Application-level via HAProxy read port (5001)
- **Connection pooling**: PgBouncer between HAProxy and PostgreSQL

## Backup Integration

- WAL archiving to S3 (continuous)
- pg_dump full backups to S3 (daily)
- Backups automatically available for restore
- Retention managed by backup/retention-policy.sh

## Trade-offs

- Patroni adds operational complexity vs managed DB
- Synchronous replication increases write latency
- HAProxy is an additional component to manage
