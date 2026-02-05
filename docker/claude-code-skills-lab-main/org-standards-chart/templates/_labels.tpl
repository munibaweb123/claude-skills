{{/*
================================================================================
LABELS TEMPLATES
================================================================================
Standardized Kubernetes labels following best practices and organizational requirements.
*/}}

{{/*
org-standards.labels.common - Common labels for all resources

Generates standard Kubernetes labels including:
- app.kubernetes.io/managed-by
- app.kubernetes.io/instance
- helm.sh/chart

Usage:
  metadata:
    labels:
      {{- include "org-standards.labels.common" . | nindent 4 }}

Values:
  - .Values.commonLabels: Additional custom labels (optional)

Output: YAML labels block
*/}}
{{- define "org-standards.labels.common" -}}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/instance: {{ .Release.Name }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
{{- if .Values.commonLabels }}
{{ toYaml .Values.commonLabels }}
{{- end }}
{{- end }}

{{/*
org-standards.labels.selector - Selector labels (immutable)

These labels are used for pod selectors and must remain stable across updates.

Usage:
  spec:
    selector:
      matchLabels:
        {{- include "org-standards.labels.selector" . | nindent 8 }}

Output: Minimal selector labels (name + instance)
*/}}
{{- define "org-standards.labels.selector" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
org-standards.labels.cost - Cost attribution labels

Financial operations (FinOps) labels for chargeback and cost optimization.
Required for production environments.

Usage:
  metadata:
    labels:
      {{- include "org-standards.labels.cost" . | nindent 4 }}

Values:
  - .Values.cost.center: Cost center code (required for production)
  - .Values.cost.businessUnit: Business unit name (required for production)
  - .Values.cost.spotEligible: Whether workload can use spot instances (optional)
  - .Values.environment: Environment name (required)

Output: FinOps labels for cost attribution
*/}}
{{- define "org-standards.labels.cost" -}}
{{- if .Values.cost }}
{{- if and (eq .Values.environment "production") (not .Values.cost.center) }}
{{- fail "cost.center is required for production deployments" }}
{{- end }}
{{- if and (eq .Values.environment "production") (not .Values.cost.businessUnit) }}
{{- fail "cost.businessUnit is required for production deployments" }}
{{- end }}
cost-center: {{ .Values.cost.center | default "unknown" | quote }}
business-unit: {{ .Values.cost.businessUnit | default "unknown" | quote }}
application: {{ .Chart.Name | quote }}
environment: {{ .Values.environment | default "unknown" | quote }}
cost-optimization/right-sizing: "enabled"
cost-optimization/spot-eligible: {{ .Values.cost.spotEligible | default "false" | quote }}
{{- end }}
{{- end }}

{{/*
org-standards.labels.recommended - Complete recommended labels

Combines all standard Kubernetes recommended labels in one template.

Usage:
  metadata:
    labels:
      {{- include "org-standards.labels.recommended" . | nindent 4 }}

Output: All recommended Kubernetes labels
*/}}
{{- define "org-standards.labels.recommended" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | default .Chart.Version | quote }}
app.kubernetes.io/component: {{ .Values.component | default "application" }}
app.kubernetes.io/part-of: {{ .Values.partOf | default .Chart.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" }}
{{- end }}

{{/*
org-standards.labels.full - Complete labels including common, selector, and cost

Convenience template that includes all labels.

Usage:
  metadata:
    labels:
      {{- include "org-standards.labels.full" . | nindent 4 }}

Output: All labels combined
*/}}
{{- define "org-standards.labels.full" -}}
{{- include "org-standards.labels.common" . }}
{{- if .Values.cost }}
{{ include "org-standards.labels.cost" . }}
{{- end }}
{{- end }}
