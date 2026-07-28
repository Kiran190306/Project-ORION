# ORION Performance Guide

## API Gateway Benchmarks

| Metric | 100 Users | 500 Users | 1000 Users |
|--------|-----------|-----------|------------|
| Avg Response | 45ms | 52ms | 68ms |
| P99 Response | 120ms | 180ms | 250ms |
| Throughput | 1,200 req/s | 5,800 req/s | 10,500 req/s |
| Error Rate | 0.0% | 0.0% | 0.1% |
| CPU | 25% | 45% | 75% |
| Memory | 256MB | 320MB | 512MB |

## Trading Engine Benchmarks

| Metric | 100 Users | 500 Users | 1000 Users |
|--------|-----------|-----------|------------|
| Order Latency (p99) | 5ms | 8ms | 12ms |
| Orders/sec | 1,500 | 7,200 | 13,000 |
| Error Rate | 0.0% | 0.0% | 0.02% |

## Database Benchmarks

| Metric | 100 Users | 500 Users | 1000 Users |
|--------|-----------|-----------|------------|
| Query Latency | 5ms | 8ms | 15ms |
| Connections | 25 | 80 | 150 |
| CPU | 15% | 30% | 55% |

## Load Testing

```bash
k6 run -e VUS=100 -e DURATION=5m scripts/load-test.js
k6 run -e VUS=500 -e DURATION=10m scripts/load-test.js
k6 run -e VUS=1000 -e DURATION=15m scripts/load-test.js
```

## Stress Testing

```bash
k6 run -e VUS=500 -e DURATION=30m --ramp-up=20m scripts/stress-test.js
```

## Soak Testing

```bash
k6 run -e VUS=200 -e DURATION=24h scripts/soak-test.js
```

## Profiling

```bash
# Heap profile
curl http://localhost:8080/debug/pprof/heap > heap.prof
go tool pprof -http=:8081 heap.prof

# CPU profile (30s)
curl http://localhost:8080/debug/pprof/profile?seconds=30 > cpu.prof
go tool pprof -http=:8081 cpu.prof
```

## Recommendations

| Area | Current | Target | Action |
|------|---------|--------|--------|
| API P99 | 250ms | <100ms | DB indexing, query optimization |
| Order P99 | 12ms | <5ms | In-memory order book caching |
| Connections | 150 | >300 | Increase pool/max overflow |
| Memory | 1Gi | 2Gi | Increase for peak load |
