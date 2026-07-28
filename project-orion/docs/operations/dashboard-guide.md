# ORION Dashboard Guide

## Overview

ORION provides 10 Grafana dashboards for monitoring all aspects of the trading platform.

## Dashboard Catalog

### 1. System Overview
- **UID**: `orion-system-overview`
- **Description**: High-level health of the entire platform
- **Panels**:
  - API Request Rate (req/s)
  - Error Rate (4xx/5xx)
  - P95 Latency
  - CPU / Memory / Disk Utilization
  - SLO Availability (7d)
  - Error Budget Remaining
  - Active Workers
  - Queue Depth
  - Research Active Jobs
  - Orders Today (24h)

### 2. API Performance
- **UID**: `orion-api-performance`
- **Description**: Detailed API service metrics
- **Panels**:
  - Request Rate by HTTP status (2xx/4xx/5xx)
  - Latency Percentiles (P50/P95/P99)
  - Success Rate %
  - Availability (1d/7d/30d)
  - Error Budget Remaining

### 3. Research Engine
- **UID**: `orion-research-engine`
- **Description**: Research job execution metrics
- **Panels**:
  - Job Rate
  - Error Rate
  - Job Duration (P50/P95)
  - Active Jobs
  - Queue Depth
  - Engine Availability

### 4. Execution Engine
- **UID**: `orion-execution-engine`
- **Description**: Order execution metrics
- **Panels**:
  - Order Rate
  - Error Rate
  - Fill Rate
  - Execution Latency (P50/P95)
  - Engine Availability

### 5. Risk Engine
- **UID**: `orion-risk-engine`
- **Description**: Risk check metrics
- **Panels**:
  - Risk Checks Rate
  - Violations
  - Check Duration
  - Engine Availability

### 6. Portfolio
- **UID**: `orion-portfolio`
- **Description**: Portfolio monitoring
- **Panels**:
  - Portfolio Value
  - P&L
  - Open Positions
  - Exposure
  - Engine Availability

### 7. Workers
- **UID**: `orion-workers`
- **Description**: Worker pool metrics
- **Panels**:
  - Job Processing Rate
  - Error Rate
  - Active Workers
  - Queue Depth
  - Job Duration
  - Worker Availability

### 8. Infrastructure
- **UID**: `orion-infrastructure`
- **Description**: Node-level infrastructure
- **Panels**:
  - Node CPU Usage
  - Node Memory Usage
  - Node Disk Usage
  - Network I/O
  - Prometheus Self-Monitoring

### 9. Kubernetes Cluster
- **UID**: `orion-kubernetes-cluster`
- **Description**: K8s cluster health
- **Panels**:
  - Cluster CPU / Memory Usage
  - Pod Count
  - Pod Status (Running/Pending/Failed)
  - API Server Request Rate
  - Node Status

### 10. Business KPIs
- **UID**: `orion-business-kpis`
- **Description**: Business-level metrics
- **Panels**:
  - Total Orders (24h)
  - Total Research Jobs (24h)
  - Total Errors (24h)
  - Error Budget Remaining
  - Availability (7d)
  - SLO Compliance (30d)

## Dashboard Provisioning

Dashboards are provisioned automatically via `dashboards/provisioning.yml`.

### Adding a New Dashboard

1. Create a JSON file in `monitoring/grafana/dashboards/`
2. Ensure the `uid` is unique
3. The provisioning system will auto-load the dashboard

### Best Practices

- Use recording rules for complex PromQL queries
- Set appropriate time ranges (default: last 1 hour)
- Use stat panels for SLO and availability
- Use graph panels for trends over time
- Include legendFormat for readability

