#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════
# ORION Operational Validation Suite
# ════════════════════════════════════════════════════════════

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
PASS=0; FAIL=0; WARN=0
log_pass() { echo -e "${GREEN}[PASS]${NC} $*"; ((PASS++)); }
log_fail() { echo -e "${RED}[FAIL]${NC} $*"; ((FAIL++)); }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; ((WARN++)); }

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

echo "════════════════════════════════════════════════════════"
echo "  ORION Operational Validation Suite"
echo "════════════════════════════════════════════════════════"

validate_helm() {
  echo "── Helm Validation ──"
  if command -v helm &>/dev/null; then
    helm lint "$ROOT/deployment/helm/orion" &>/dev/null && log_pass "helm lint" || log_fail "helm lint"
    helm template orion "$ROOT/deployment/helm/orion" &>/dev/null && log_pass "helm template" || log_fail "helm template"
  else log_warn "helm not installed"; fi
}

validate_k8s() {
  echo "── Kubernetes Validation ──"
  if command -v kubectl &>/dev/null; then
    kubectl get nodes &>/dev/null && log_pass "cluster reachable" || log_fail "cluster unreachable"
  else log_warn "kubectl not installed"; fi
}

validate_monitoring() {
  echo "── Monitoring Validation ──"
  local m="$ROOT/monitoring"
  [ -f "$m/prometheus/prometheus.yml" ] && log_pass "prometheus config" || log_fail "prometheus config"
  [ -f "$m/alertmanager/alertmanager.yml" ] && log_pass "alertmanager config" || log_fail "alertmanager config"
  [ -f "$m/grafana/datasources/prometheus.yml" ] && log_pass "grafana datasource" || log_fail "grafana datasource"
  [ -f "$m/jaeger/jaeger-collector.yml" ] && log_pass "jaeger config" || log_fail "jaeger config"
}

validate_backup() {
  echo "── Backup Validation ──"
  local b="$ROOT/backup"
  for f in database-backup.sh redis-backup.sh restore-database.sh restore-redis.sh retention-policy.sh backup-config.yml; do
    [ -f "$b/$f" ] && log_pass "$f" || log_fail "$f"
  done
}

validate_cicd() {
  echo "── CI/CD Validation ──"
  local w="$ROOT/.github/workflows"
  for f in ci.yml security.yml release.yml container.yml documentation.yml; do
    [ -f "$w/$f" ] && log_pass "$f" || log_fail "$f"
  done
}

validate_docs() {
  echo "── Documentation Validation ──"
  local d="$ROOT/docs/devops"
  for f in cicd-architecture.md release-guide.md security-pipeline-guide.md supply-chain-security-guide.md sbom-guide.md; do
    [ -f "$d/$f" ] && log_pass "devops/$f" || log_fail "devops/$f"
  done
  local o="$ROOT/docs/operations"
  for f in disaster-recovery-guide.md backup-guide.md chaos-engineering-guide.md performance-guide.md go-live-guide.md; do
    [ -f "$o/$f" ] && log_pass "operations/$f" || log_fail "operations/$f"
  done
}

summary() {
  echo ""
  echo "════════════════════════════════════════════════════════"
  echo "  Results: ${GREEN}${PASS} PASS${NC}, ${RED}${FAIL} FAIL${NC},
