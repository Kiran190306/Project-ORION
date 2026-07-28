# EPIC-012 Sprint 4 — DevSecOps & Supply Chain Security

## Phase 1 — GitHub Actions Workflows
- [x] ci.yml — Lint, typecheck, test, helm, deps-audit
- [x] security.yml — CodeQL, Semgrep, Gitleaks, Trivy, Grype, pip-audit, npm audit, license check
- [x] release.yml — SBOM, build & sign, GitHub Release, artifact upload
- [x] container.yml — Hadolint, Trivy, Grype, Syft, base image verify
- [x] documentation.yml — Markdown lint, link check, spell check, GitHub Pages

## Phase 2 — Build Pipeline
- [x] Makefile targets (existing)
- [x] docker/base/Dockerfile — Production multi-stage build
- [x] scripts/build/entrypoint.sh — Container entrypoint

## Phase 3 — Supply Chain Security
- [x] SBOM generation (CycloneDX + SPDX) in release.yml
- [x] Cosign image signing in release.yml
- [x] SLSA provenance attestation
- [x] Dependency verification (pip-audit + npm audit)
- [x] Syft SBOM in container.yml

## Phase 4 — Security Scanning
- [x] Trivy (container + SBOM)
- [x] Grype (container + SBOM)
- [x] CodeQL (Python, JavaScript, Go)
- [x] Semgrep (SAST)
- [x] Gitleaks (secrets)
- [x] pip-audit (Python deps)
- [x] npm audit (Node.js deps)
- [x] License compliance

## Phase 5 — Documentation
- [x] docs/devops/cicd-architecture.md
- [x] docs/devops/release-guide.md
- [x] docs/devops/security-pipeline-guide.md
- [x] docs/devops/supply-chain-security-guide.md
- [x] docs/devops/sbom-guide.md

## Phase 6 — Validation
- [ ] GitHub Actions YAML syntax check
- [ ] docker/base/Dockerfile build test
- [ ] helm lint deployment/helm/orion
- [ ] helm template orion deployment/helm/orion
- [ ] pytest (existing)
