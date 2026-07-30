{{- /*
ORION Helm Template Helpers
*/}}

{{- define "orion.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "orion.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{- define "orion.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "orion.labels" -}}
helm.sh/chart: {{ include "orion.chart" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/part-of: orion
{{- end }}

{{- define "orion.selectorLabels" -}}
app.kubernetes.io/name: {{ include "orion.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "orion.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "orion.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{- define "orion.configName" -}}
{{- printf "%s-config" (include "orion.fullname" .) }}
{{- end }}

{{- define "orion.secretName" -}}
{{- printf "%s-secrets" (include "orion.fullname" .) }}
{{- end }}

{{- define "orion.probe" -}}
{{- $port := .port | default 8080 -}}
{{- $path := .path | default "/health" -}}
{{- $delay := .initialDelay | default 5 -}}
{{- $period := .period | default 10 -}}
{{- $timeout := .timeout | default 3 -}}
{{- $failure := .failureThreshold | default 3 -}}
httpGet:
  path: {{ $path }}
  port: {{ $port }}
  httpHeaders:
    - name: X-Forwarded-Proto
      value: https
initialDelaySeconds: {{ $delay }}
periodSeconds: {{ $period }}
timeoutSeconds: {{ $timeout }}
failureThreshold: {{ $failure }}
{{- end -}}

{{- define "orion.podSecurityContext" -}}
runAsNonRoot: true
runAsUser: {{ .uid | default 10001 }}
runAsGroup: {{ .uid | default 10001 }}
fsGroup: {{ .uid | default 10001 }}
seccompProfile:
  type: RuntimeDefault
{{- end -}}

{{- define "orion.containerSecurityContext" -}}
allowPrivilegeEscalation: false
capabilities:
  drop:
    - ALL
readOnlyRootFilesystem: true
runAsNonRoot: true
{{- end -}}

{{- define "orion.meshEnabled" -}}
{{- .Values.mesh.enabled | default false -}}
{{- end -}}

{{- define "orion.meshLabels" -}}
{{- if eq (include "orion.meshEnabled" .) "true" }}
istio.io/rev: istio
sidecar.istio.io/inject: {{ .Values.mesh.injection.enabled | toString | quote }}
{{- end }}
{{- end -}}

{{- define "orion.meshSelectorLabels" -}}
{{- if eq (include "orion.meshEnabled" .) "true" }}
app.kubernetes.io/managed-by: istio
{{- end }}
{{- end -}}
