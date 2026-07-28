# ORION SLO / SLA Documentation

## Overview

This document defines the Service Level Objectives (SLOs), Service Level Agreements (SLAs), and Error Budget policies for the ORION enterprise trading platform.

## SLO Summary

| SLO | Target | Window | Severity | Burn Rate (1h) | Burn Rate (6h) |
|-----|--------|--------|----------|----------------|----------------|
| API Availability | 99.9% | 30 days | Critical | 14.4 | 6.0 |
| API Latency (P99 < 1s) | 95.0% | 30 days | Critical | 14.4 | — |
| Execution Fill Rate | 99.5% | 30 days | Critical | 14.4 | — |
| Worker Job Success | 99.0% | 30 days | High | — | 6.0 |
| Research Job Success | 99.0% | 30 days | High | — | 6.0 |

## Error Budget Policy

- **Error Budget**: Total allowable failures over the SLO window.
- **Consumption**: Each 5xx error consumes from the budget.
- **Burn Rate Alerts**:
  - Critical: Budget exhausted in < 1 hour (14.4x burn rate)
  - Warning: Budget exhausted in < 6 hours (6.0x burn rate)
- **When Budget is Exhausted**:
  1. Immediate incident response
  2. Freeze non-critical deployments
  3. Conduct root cause analysis
  4. Implement mitigations before new features

## SLO Indicators

### API Availability
- **Good Events**: HTTP requests with status != 5xx
- **Total Events**: All HTTP requests
- **Measurement**: `(good / total) * 100`

### API Latency
- **Good Events**: Requests completing in < 1 second (P99)
- **Total Events**: All HTTP requests
- **Measurement**: `(fast / total) * 100`

### Execution Fill Rate
- **Good Events**: Orders with status "filled"
- **Total Events**: All orders
- **Measurement**: `(filled / total) * 100`

### Worker Job Success
- **Good Events**: Jobs with status != "error"
- **Total Events**: All worker jobs
- **Measurement**: `(successful / total) * 100`

### Research Job Success
- **Good Events**: Research jobs with status != "error"
- **Total Events**: All research jobs
- **Measurement**: `(successful / total) * 100`

## Monitoring

All SLOs are monitored via Prometheus recording rules:

- `orion:slo:api_availability_30d` — API availability over 30 days
- `orion:slo:api_latency_compliance_30d` — API latency compliance
- `orion:slo:error_budget_remaining_pct` — Remaining error budget
- `orion:slo:error_budget_burn_rate` — Current burn rate
- `orion:slo:compliance_score` — Overall compliance score

## Dashboards

The "Business KPIs" dashboard in Grafana displays:
- Current SLO compliance
- Error budget consumption
- Burn rate alerts
- Historical trends

## Runbooks

- [Monitoring Guide](./monitoring-guide.md)
- [Alert Runbook](./alert-runbook.md)

