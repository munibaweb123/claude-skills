{{/*
================================================================================
ANNOTATIONS TEMPLATES
================================================================================
Standardized Kubernetes annotations for monitoring, logging, and observability.
*/}}

{{/*
org-standards.annotations.monitoring - Prometheus monitoring annotations

Configures Prometheus scraping for metrics collection.

Usage:
  metadata:
    annotations:
      {{- include "org-standards.annotations.monitoring" . | nindent 4 }}

Values:
  - .Values.metrics.enabled: Enable Prometheus scraping (default: true)
  - .Values.metrics.port: Metrics port (default: 8080)
  - .Values.metrics.path: Metrics endpoint path (default: /metrics)

Output: Prometheus scraping annotations
*/}}
{{- define "org-standards.annotations.monitoring" -}}
{{- if .Values.metrics.enabled | default true }}
prometheus.io/scrape: "true"
prometheus.io/port: {{ .Values.metrics.port | default 8080 | quote }}
prometheus.io/path: {{ .Values.metrics.path | default "/metrics" | quote }}
{{- end }}
{{- end }}

{{/*
org-standards.annotations.logging - Logging configuration annotations

Configures log collection and parsing for Fluentd/Fluent Bit.

Usage:
  metadata:
    annotations:
      {{- include "org-standards.annotations.logging" . | nindent 4 }}

Values:
  - .Values.logging.format: Log format (default: json)
  - .Chart.Name: Used as log source

Output: Logging configuration annotations
*/}}
{{- define "org-standards.annotations.logging" -}}
fluentd.io/include: "true"
fluentd.io/parser-type: {{ .Values.logging.format | default "json" | quote }}
logging/source: {{ .Chart.Name | quote }}
logging/format: {{ .Values.logging.format | default "json" | quote }}
{{- end }}

{{/*
org-standards.annotations.tracing - Distributed tracing annotations

Configures distributed tracing with Jaeger or other tracing systems.

Usage:
  metadata:
    annotations:
      {{- include "org-standards.annotations.tracing" . | nindent 4 }}

Values:
  - .Values.tracing.enabled: Enable tracing (default: true)
  - .Values.tracing.jaeger: Use Jaeger sidecar injection (default: true)

Output: Tracing configuration annotations
*/}}
{{- define "org-standards.annotations.tracing" -}}
{{- if .Values.tracing.enabled | default true }}
{{- if .Values.tracing.jaeger | default true }}
sidecar.jaegertracing.io/inject: "true"
{{- end }}
tracing/enabled: "true"
{{- end }}
{{- end }}

{{/*
org-standards.annotations.datadog - Datadog APM annotations

Configures Datadog APM and log collection.

Usage:
  metadata:
    annotations:
      {{- include "org-standards.annotations.datadog" . | nindent 4 }}

Values:
  - .Chart.Name: Used as service name and log source

Output: Datadog configuration annotations
*/}}
{{- define "org-standards.annotations.datadog" -}}
ad.datadoghq.com/{{ .Chart.Name }}.logs: '[{"source":"{{ .Chart.Name }}","service":"{{ .Chart.Name }}"}]'
ad.datadoghq.com/{{ .Chart.Name }}.check_names: '["{{ .Chart.Name }}"]'
{{- end }}

{{/*
org-standards.annotations.observability - Complete observability stack

Combines monitoring, logging, and tracing annotations.

Usage:
  metadata:
    annotations:
      {{- include "org-standards.annotations.observability" . | nindent 4 }}

Output: All observability annotations
*/}}
{{- define "org-standards.annotations.observability" -}}
{{- include "org-standards.annotations.monitoring" . }}
{{- include "org-standards.annotations.logging" . }}
{{- include "org-standards.annotations.tracing" . }}
{{- end }}

{{/*
org-standards.annotations.security - Security scanning annotations

Annotations for security scanning and compliance tools.

Usage:
  metadata:
    annotations:
      {{- include "org-standards.annotations.security" . | nindent 4 }}

Output: Security scanning annotations
*/}}
{{- define "org-standards.annotations.security" -}}
security.company.com/scan: "true"
security.company.com/compliance: "soc2,pci-dss"
container.apparmor.security.beta.kubernetes.io/{{ .Chart.Name }}: runtime/default
{{- end }}

{{/*
org-standards.annotations.common - Common annotations

Includes common custom annotations from values.

Usage:
  metadata:
    annotations:
      {{- include "org-standards.annotations.common" . | nindent 4 }}

Values:
  - .Values.commonAnnotations: Additional custom annotations (optional)

Output: Custom annotations from values
*/}}
{{- define "org-standards.annotations.common" -}}
{{- if .Values.commonAnnotations }}
{{ toYaml .Values.commonAnnotations }}
{{- end }}
{{- end }}

{{/*
org-standards.annotations.full - All standard annotations

Convenience template that includes all standard annotations.

Usage:
  metadata:
    annotations:
      {{- include "org-standards.annotations.full" . | nindent 4 }}

Output: All annotations combined
*/}}
{{- define "org-standards.annotations.full" -}}
{{- include "org-standards.annotations.observability" . }}
{{- include "org-standards.annotations.security" . }}
{{- include "org-standards.annotations.common" . }}
{{- end }}
