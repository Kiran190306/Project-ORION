# ORION SBOM Guide

## Overview

ORION generates Software Bill of Materials (SBOM) for all releases to support supply chain transparency and vulnerability management.

## Supported Formats

| Format | File | Standard |
|--------|------|----------|
| CycloneDX | `sbom.cyclonedx.json` | OWASP CycloneDX v1.5 |
| SPDX | `sbom.spdx.json` | SPDX 2.3 |

## Generation

SBOMs are automatically generated during the Release workflow when a tag is pushed.

### Trigger

```bash
git tag -a v0.12.0 -m "ORION v0.12.0"
git push origin v0.12.0
```

### Generation Method

Uses `cyclonedx/gh-cyclonedx` GitHub Action which analyzes:
- Python dependencies from `poetry.lock`
- Node.js dependencies from `package-lock.json`
- Docker image layers and packages (via Syft)

### Output

SBOM files are:
1. Uploaded as workflow artifacts
2. Attached to GitHub Release
3. Signed with Cosign (checksums)

## Verification

```bash
# Download SBOM from release
gh release download v0.12.0 --pattern "sbom*.json"

# Verify with CycloneDX CLI
cyclonedx verify sbom.cyclonedx.json

# Verify signatures
cosign verify-blob --bundle checksums.sig sbom.cyclonedx.json
```

## Usage

### Vulnerability Scanning
```bash
# Scan SBOM with Grype
grype sbom:sbom.cyclonedx.json

# Scan SBOM with Trivy
trivy sbom sbom.cyclonedx.json
```

### Dependency Auditing
```bash
# Check for known vulnerabilities
pip-audit --require-hashes -r <(jq -r '.metadata.components[].purl' sbom.cyclonedx.json)
```

## Lifecycle

1. **Generation**: Every release tag
2. **Storage**: GitHub Release artifacts (permanent)
3. **Scanning**: Trivy + Grype on release
4. **Attestation**: Cosign-signed checksums
