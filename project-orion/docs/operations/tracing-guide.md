# ORION Tracing Guide

## Overview

ORION uses Jaeger for distributed tracing based on OpenTelemetry instrumentation. This guide covers tracing architecture, configuration, and usage.

## Architecture

```
┌─────────────┐    ┌──────────────────┐    ┌────────────────┐
│ Application │───▶│  Jaeger Agent    │───▶│ Jaeger Collector│
│ (OTel SDK)  │    │  (DaemonSet)     │    │                │
└─────────────┘    └──────────────────┘    └───────┬────────┘
                                                   │
                                                   ▼
                                        ┌──────────────────┐
                                        │  Elasticsearch   │
                                        │  (Trace Storage) │
                                        └───────┬──────────┘
                                                │
                                                ▼
                                        ┌──────────────────┐
                                        │  Jaeger Query    │
                                        │  (UI & API)      │
                                        └──────────────────┘
```

## Sampling Configuration

Sampling strategies are configured per service in `jaeger-collector.yml`:

| Service | Strategy | Rate |
|---------|----------|------|
| orion-api | Probabilistic | 100% |
| orion-worker | Rate Limiting | 10 traces/s |
| orion-scheduler | Rate Limiting | 5 traces/s |
| orion-research-engine | Probabilistic | 50% |
| orion-execution-engine | Probabilistic | 100% |
| orion-risk-engine | Probabilistic | 50% |
| orion-portfolio-engine | Probabilistic | 50% |
| Default | Probabilistic | 10% |

## Context Propagation

Trace context is propagated via:

- **HTTP**: `traceparent` and `tracestate` headers (W3C Trace Context)
- **Messaging**: Correlation IDs in message headers
- **Async**: Thread-local context propagation

## Span Attributes

Standard span attributes for all services:

- `service.name` — Service identifier
- `span.kind` — Client/Server/Producer/Consumer
- `http.method` — HTTP method
- `http.url` — Request URL
- `http.status_code` — Response status code
- `correlation_id` — Cross-service correlation ID

## Trace Visualization

Access the Jaeger UI at `https://jaeger.orion.example.com`.

### Search

- Search by service name, operation, tags, or time range
- Max lookback: 7 days
- Max duration: 24 hours

### Dependencies

The DAG view shows service dependencies and call relationships.

### Integration with Grafana

Link traces from Grafana panels using:

```
https://jaeger.orion.example.com/trace/${traceID}
```

## Troubleshooting

### Missing Spans

1. Verify sampling configuration
2. Check Jaeger agent is running on the node
3. Verify collector is reachable
4. Check Elasticsearch storage

### High Trace Volume

1. Reduce sampling rate for high-volume services
2. Increase rate limiting for worker services
3. Check storage capacity

