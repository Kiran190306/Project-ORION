# ORION Capacity Planning Guide

## Current Baseline (v0.12.0)

| Resource | API | Worker | Scheduler | DB | Redis |
|----------|-----|--------|-----------|-----|-------|
| CPU req | 500m | 250m | 100m | 2000m | 1000m |
| Mem req | 512Mi | 256Mi | 128Mi | 4Gi | 2Gi |
| CPU lim | 1000m | 500m | 250m | 4000m | 2000m |
| Mem lim | 1Gi | 512Mi | 256Mi | 8Gi | 4Gi |
| Replicas | 3-20 | 2-10 | 1-5 | 1+2 replicas | 1+2 replicas |

## Growth Projections (12 months)

### User Growth
| Month | Concurrent Users | Daily Orders | Data Volume |
|-------|-----------------|-------------|-------------|
| 1 | 500 | 100K | 50GB |
| 3 | 750 | 250K | 120GB |
| 6 | 1000 | 500K | 250GB |
| 12 | 2000 | 1M | 500GB |

### Resource Requirements
| Month | API (pods) | Worker (pods) | DB Storage | Redis Memory | Cluster Nodes |
|-------|-----------|-------------|-----------|-------------|--------------|
| 1 | 3-5 | 2-3 | 100GB | 4GB | 6 |
| 3 | 3-8 | 2-5 | 200GB | 8GB | 8 |
| 6 | 3-12 | 2-8 | 350GB | 12GB | 12 |
| 12 | 3-20 | 2-10 | 500GB | 16GB | 20 |

## Scaling Thresholds

### API Server
| Metric | Threshold | Action |
|--------|-----------|--------|
| CPU utilization | >70% for 30s | Scale up by 3 pods |
| Memory utilization | >80% for 30s | Scale up by 3 pods |
| P99 latency | >200ms for 2min | Review HPA metrics |
| Error rate | >1% for 1min | Alert + scale up |

### Worker
| Metric | Threshold | Action |
|--------|-----------|--------|
| Queue depth | >100 avg for 1min | Scale up by 2 pods |
| Queue depth | >500 avg for 5min | Alert + add more batch workers |
| Job latency | >30s P99 | Review worker capacity |

### Database
| Metric | Threshold | Action |
|--------|-----------|--------|
| Connections | >80% pool | Increase pool + add PgBouncer |
| CPU | >70% for 5min | Scale up instance |
| Storage | >75% used | Add storage or archive |
| Replication lag | >60s | Alert, investigate |

### Redis
| Metric | Threshold | Action |
|--------|-----------|--------|
| Memory | >75% used | Scale up instance |
| Evictions | >0/s | Increase maxmemory |
| Hit rate | <80% | Review cache strategy |
| Connected clients | >1000 | Add replicas |

## Cost Projections

| Month | Infrastructure | Managed Services | Licensing | Total |
|-------|---------------|------------------|-----------|-------|
| 1 | $5,000 | $2,000 | $1,000 | $8,000 |
| 3 | $6,500 | $2,500 | $1,000 | $10,000 |
| 6 | $10,000 | $4,000 | $1,000 | $15,000 |
| 12 | $16,000 | $6,000 | $1,000 | $23,000 |

## Optimization Recommendations

1. **Spot instances**: Use spot nodes for stateless workloads (40% cost reduction)
2. **Right-sizing**: VPA recommender optimizes resource requests
3. **Storage tiering**: Hot/warm/cold data tiers (S3 for cold data)
4. **Caching**: Aggressive cache TTL to reduce DB load
5. **Compression**: Message compression for inter-service communication

## Load Testing Frequency

| Phase | Frequency | Tool | Target Load |
|-------|-----------|------|-------------|
| CI pipeline | Per commit | k6 - smoke | 10 users for 30s |
| Nightly | Daily | k6 - load | 200 users for 5min |
| Weekly | Weekly | k6 - stress | 500 users for 10min |
| Pre-release | Per release | k6 - soak | 200 users for 24h |
| Quarterly | Quarterly | k6 - max | 2000 users for 30min |
