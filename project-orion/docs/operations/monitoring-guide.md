# ORION Monitoring Guide

## Overview

ORION uses Prometheus for metrics collection, alerting, and recording rules. This guide covers the monitoring architecture, configuration, and operational procedures.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌────────────────┐
│   API Service   │────▶│   Prometheus     │◀────│  Alertmanager  │
│   Workers       │     │   Scrape & Rules │     │  Routing       │
│   Scheduler     │     │                  │     │  Grouping      │
│   Research Eng  │     │  Recording Rules │     │  Inhibition    │
│   Execution Eng │     │  Alert Rules     │     │  Notifications │
│   Risk Eng      │     └────────┬─────────┘     └────────────────┘
│   Portfolio Eng │              │
└─────────────────┘              ▼
                        ┌──────────────────┐
                        │    Grafana       │
                        │   Dashboards     │
                        │   Alerting UI    │
                        └──────────────────┘
```

## Metrics Collection

### Scrape Targets

- **orion-api** — API service metrics (10s interval)
- **orion-worker** — Worker metrics (15s interval)
- **orion-scheduler** — Scheduler metrics (15s interval)
- **orion-research-engine** — Research engine metrics (15s interval)
- **orion-risk-engine** — Risk engine metrics (15s interval)
- **orion-portfolio-engine** — Portfolio engine metrics (15s interval)
- **orion-execution-engine** — Execution engine metrics (10s interval)
- **orion-infrastructure-nodes** — Node-level metrics (30s interval)
- **orion-kubernetes-*** — Kubernetes component metrics (30s interval)
- **orion-prometheus** — Prometheus self-monitoring (30s interval)

### Available Metrics

Metrics follow the `orion_<component>_<metric>` naming convention:

- `orion_http_requests_total` — HTTP request count by status
- `orion_http_request_duration_seconds` — Request duration histogram
- `orion_worker_jobs_total` — Worker job count by status
- `orion_research_jobs_total` — Research job count by status
- `orion_execution_orders_total` — Execution order count by status
- `orion_risk_checks_total` — Risk check count
- `orion_portfolio_value` — Portfolio value gauge
- `orion_worker_queue_depth` — Worker queue depth gauge

### Recording Rules

Pre-computed metrics available for querying:

| Rule | Description |
|------|-------------|
| `orion:api:request_rate:5m` | API request rate (5m avg) |
| `orion:api:error_rate:5m` | API error rate (5m avg) |
| `orion:api:latency_p50:5m` | P50 latency (5m avg) |
| `orion:api:latency_p95:5m` | P95 latency (5m avg) |
| `orion:api:latency_p99:5m` | P99 latency (5m avg) |
| `orion:node:cpu_utilization:5m` | Node CPU utilization |
| `orion:node:memory_utilization` | Node memory utilization |
| `orion:node:disk_utilization` | Node disk utilization |

## SLO Monitoring

SLOs are defined with recording rules for 30-day windows:

- **Availability SLO**: 99.9% — requires ≤ 43m 12s downtime per 30d
- **Latency SLO**: 95% of requests under 1s
- **Error Budget**: Calculated as `(1 - SLO/100) * total_requests`

## Alerting

Alerts are routed via Alertmanager with environment-specific routing:

- **Critical**: Page on-call via PagerDuty + notify Slack
- **Warning**: Notify Slack channel
- **Info**: Log only

## Production Readiness Checklist

- [ ] Prometheus configured with all scrape targets
- [ ] Recording rules loaded and computing
- [ ] Alert rules loaded and firing appropriately
- [ ] Grafana dashboards imported and rendering
- [ ] Alertmanager routing configured for all environments
- [ ] SLO recording rules in place
- [ ] Retention policies configured
- [ ] Backup strategy for metric data

