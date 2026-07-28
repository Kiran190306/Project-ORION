# ORION CI/CD Architecture

## Overview

ORION uses GitHub Actions for continuous integration and deployment. The CI/CD pipeline consists of five workflows that provide build, test, security scanning, container management, and release automation.

## Pipeline Stages

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   CI        │────▶│  Security   │────▶│  Container  │────▶│  Release    │
│  (PR/Push)  │     │  (PR/Push)  │     │  (PR/Push)  │     │  (Tag Push) │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │                    │
       ▼                   ▼                   ▼                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         Quality Gates                                 │
│  • Coverage ≥ 95%    • No CVEs    • No secrets    • Lint passes      │
│  • Helm passes       • K8s passes • Tests pass    • SBOM generated  │
└──────────────────────────────────────────────────────────────────────┘
```

## Workflows

### 1. CI (`ci.yml`)
Triggers on push/PR to `main` and `develop`. Runs:
- **lint**: Black, isort, Pylint, ESLint
- **typecheck**: Mypy strict mode
- **test**: Pytest with coverage (≥95% threshold)
- **helm-validate**: Helm lint + Kubeconform validation
- **deps-audit**: pip-audit + npm audit

### 2. Security (`security.yml`)
Triggers on push/PR + weekly schedule. Runs:
- **codeql**: CodeQL SAST for Python, JavaScript, Go
- **semgrep**: Semgrep SAST with auto rules
- **gitleaks**: Secret scanning with Gitleaks
- **trivy/grype**: Container vulnerability scanning
- **dep-scan**: pip-audit + npm audit in JSON format
- **license-check**: pip-licenses compliance

### 3. Container (`container.yml`)
Triggers on changes to `docker/**` or `Dockerfile*`. Runs:
- **dockerfile-lint**: Hadolint validation
- **image-scan**: Trivy + Grype for each service image
- **base-image-verify**: Base image digest verification

### 4. Release (`release.yml`)
Triggers on tag push `v*.*.*`. Runs:
- **sbom**: CycloneDX and SPDX SBOM generation
- **build-and-sign**: Build, push, Cosign sign, attest images
- **release**: Create GitHub Release with signed artifacts

### 5. Documentation (`documentation.yml`)
Triggers on changes to `docs/**` or `*.md`. Runs:
- **markdown-lint**: Markdownlint
- **link-check**: Lychee link checker
- **spell-check**: Typos spell checker
- **deploy**: GitHub Pages deployment (main only)

## Dependency Caching

All workflows implement Poetry and npm dependency caching:
```yaml
- uses: actions/cache@v4
  with:
    path: .venv
    key: venv-${{ runner.os }}-${{ python-version }}-${{ hashFiles('poetry.lock') }}
```

## Matrix Builds

The CI test job uses matrix strategy for Python versions. The release build job uses matrix for services.

## Artifact Management

Test results, coverage reports, SBOM files, and security scan results are uploaded as artifacts with 14-30 day retention.

## Secrets Required

| Secret | Description |
|--------|-------------|
| `GITHUB_TOKEN` | Auto-provided, used for all workflows |
| `GITLEAKS_LICENSE` | Gitleaks license for secret scanning |
| `SLACK_API_URL` | Alertmanager Slack webhook |
| `PAGERDUTY_PLATFORM_KEY` | PagerDuty routing key for platform |
| `PAGERDUTY_EXECUTION_KEY` | PagerDuty routing key for execution |
| `OPSGENIE_API_KEY` | OpsGenie integration key |
| `SMTP_AUTH_PASSWORD` | SMTP password for Alertmanager |
