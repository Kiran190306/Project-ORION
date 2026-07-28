# ORION Security Pipeline Guide

## Overview

ORION implements a defense-in-depth security scanning pipeline with static analysis, dependency scanning, container scanning, and secret detection.

## Security Workflow

The `security.yml` workflow runs on every push/PR to main/develop and on a weekly schedule.

### Static Analysis (SAST)

**CodeQL**: Python, JavaScript, Go — `security-and-quality` queries — SARIF to GitHub Security tab

**Semgrep**: Auto-detected rules — `--config=auto` — blocking on findings — SARIF output

### Secret Detection

**Gitleaks**: Full git history (`fetch-depth: 0`) — blocks on high-severity leaks

### Container Scanning

**Trivy**: Base Docker image — CRITICAL/HIGH severity — blocks on findings — SARIF output

**Grype**: Base Docker image — `fail-build: true` — SARIF output

### Dependency Scanning

**pip-audit**: `--strict` mode — blocks on any advisory

**npm audit**: `--audit-level=high` — JSON artifact

### License Compliance

**pip-licenses**: Allows MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, Python-2.0, Unlicense, CC0-1.0 — blocks on unapproved

## Quality Gates

Pipeline fails if: coverage < 95%, critical CVEs found, high-severity secrets found, Helm lint fails, K8s validation fails, tests fail, SAST findings found, unapproved licenses found.

## Remediation

1. Critical CVEs: Update base image, patch dependencies, rebuild
2. Secrets: Rotate, remove from history with bfg
3. SAST findings: Fix code patterns, add edge case tests
4. Licenses: Evaluate alternatives, get legal approval
