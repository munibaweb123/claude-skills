{{/*
================================================================================
PROBES TEMPLATES
================================================================================
Health check probes for liveness, readiness, and startup checks.
Supports HTTP, TCP, and exec probe types.
*/}}

{{/*
org-standards.probes.http - HTTP probe (GET request)

Configures an HTTP GET probe for health checks.

Usage:
  livenessProbe:
    {{- include "org-standards.probes.http" (dict "path" "/health" "port" 8080 "context" .) | nindent 12 }}

Parameters:
  - path: HTTP path to check (required)
  - port: Port number or name (required)
  - scheme: HTTP or HTTPS (optional, default: HTTP)
  - context: Root context (required, pass as ".")

Values (from context):
  - .Values.probes.initialDelaySeconds: Initial delay (default: 30)
  - .Values.probes.periodSeconds: Check interval (default: 10)
  - .Values.probes.timeoutSeconds: Timeout (default: 5)
  - .Values.probes.successThreshold: Success count (default: 1)
  - .Values.probes.failureThreshold: Failure count (default: 3)

Output: HTTP probe configuration
*/}}
{{- define "org-standards.probes.http" -}}
httpGet:
  path: {{ .path }}
  port: {{ .port }}
  scheme: {{ .scheme | default "HTTP" }}
  {{- if .headers }}
  httpHeaders:
{{ toYaml .headers | indent 4 }}
  {{- end }}
initialDelaySeconds: {{ .context.Values.probes.initialDelaySeconds | default 30 }}
periodSeconds: {{ .context.Values.probes.periodSeconds | default 10 }}
timeoutSeconds: {{ .context.Values.probes.timeoutSeconds | default 5 }}
successThreshold: {{ .context.Values.probes.successThreshold | default 1 }}
failureThreshold: {{ .context.Values.probes.failureThreshold | default 3 }}
{{- end }}

{{/*
org-standards.probes.tcp - TCP socket probe

Configures a TCP socket probe for health checks.
Useful for databases, message queues, and services without HTTP endpoints.

Usage:
  readinessProbe:
    {{- include "org-standards.probes.tcp" (dict "port" 5432 "context" .) | nindent 12 }}

Parameters:
  - port: Port number or name (required)
  - context: Root context (required, pass as ".")

Values (from context):
  - .Values.probes.initialDelaySeconds: Initial delay (default: 15)
  - .Values.probes.periodSeconds: Check interval (default: 10)
  - .Values.probes.timeoutSeconds: Timeout (default: 3)
  - .Values.probes.failureThreshold: Failure count (default: 3)

Output: TCP probe configuration
*/}}
{{- define "org-standards.probes.tcp" -}}
tcpSocket:
  port: {{ .port }}
initialDelaySeconds: {{ .context.Values.probes.initialDelaySeconds | default 15 }}
periodSeconds: {{ .context.Values.probes.periodSeconds | default 10 }}
timeoutSeconds: {{ .context.Values.probes.timeoutSeconds | default 3 }}
failureThreshold: {{ .context.Values.probes.failureThreshold | default 3 }}
{{- end }}

{{/*
org-standards.probes.exec - Exec command probe

Executes a command inside the container to check health.

Usage:
  livenessProbe:
    {{- include "org-standards.probes.exec" (dict "command" (list "pg_isready" "-U" "postgres") "context" .) | nindent 12 }}

Parameters:
  - command: List of command and arguments (required)
  - context: Root context (required, pass as ".")

Values (from context):
  - .Values.probes.initialDelaySeconds: Initial delay (default: 30)
  - .Values.probes.periodSeconds: Check interval (default: 10)
  - .Values.probes.timeoutSeconds: Timeout (default: 5)
  - .Values.probes.failureThreshold: Failure count (default: 3)

Output: Exec probe configuration
*/}}
{{- define "org-standards.probes.exec" -}}
exec:
  command:
{{ toYaml .command | indent 4 }}
initialDelaySeconds: {{ .context.Values.probes.initialDelaySeconds | default 30 }}
periodSeconds: {{ .context.Values.probes.periodSeconds | default 10 }}
timeoutSeconds: {{ .context.Values.probes.timeoutSeconds | default 5 }}
failureThreshold: {{ .context.Values.probes.failureThreshold | default 3 }}
{{- end }}

{{/*
org-standards.probes.grpc - gRPC probe

Configures a gRPC health check probe (Kubernetes 1.24+).

Usage:
  livenessProbe:
    {{- include "org-standards.probes.grpc" (dict "port" 9090 "service" "myapp" "context" .) | nindent 12 }}

Parameters:
  - port: gRPC port number (required)
  - service: gRPC service name (optional)
  - context: Root context (required, pass as ".")

Output: gRPC probe configuration
*/}}
{{- define "org-standards.probes.grpc" -}}
grpc:
  port: {{ .port }}
  {{- if .service }}
  service: {{ .service }}
  {{- end }}
initialDelaySeconds: {{ .context.Values.probes.initialDelaySeconds | default 30 }}
periodSeconds: {{ .context.Values.probes.periodSeconds | default 10 }}
timeoutSeconds: {{ .context.Values.probes.timeoutSeconds | default 5 }}
failureThreshold: {{ .context.Values.probes.failureThreshold | default 3 }}
{{- end }}

{{/*
org-standards.probes.startup - Startup probe for slow-starting applications

Special probe for applications that take a long time to start.
Only applicable to startupProbe, not liveness or readiness.

Usage:
  startupProbe:
    {{- include "org-standards.probes.startup" (dict "path" "/startup" "port" 8080 "context" .) | nindent 12 }}

Parameters:
  - path: HTTP path to check (required)
  - port: Port number or name (required)
  - context: Root context (required, pass as ".")

Output: Startup probe with extended thresholds
*/}}
{{- define "org-standards.probes.startup" -}}
httpGet:
  path: {{ .path }}
  port: {{ .port }}
  scheme: HTTP
initialDelaySeconds: {{ .context.Values.probes.initialDelaySeconds | default 0 }}
periodSeconds: {{ .context.Values.probes.periodSeconds | default 10 }}
timeoutSeconds: {{ .context.Values.probes.timeoutSeconds | default 5 }}
# Allow up to 5 minutes for startup (30 failures * 10s period)
failureThreshold: 30
{{- end }}

{{/*
org-standards.probes.default - Default HTTP probe set

Convenience template for standard HTTP health checks.
Provides liveness and readiness probes together.

Usage:
  # Use the full probe set
  {{- include "org-standards.probes.default" (dict "healthPath" "/health" "readyPath" "/ready" "port" 8080 "context" .) | nindent 10 }}

Parameters:
  - healthPath: Liveness endpoint path (default: /health)
  - readyPath: Readiness endpoint path (default: /ready)
  - port: Port number (required)
  - context: Root context (required, pass as ".")

Output: Both liveness and readiness probes
*/}}
{{- define "org-standards.probes.default" -}}
livenessProbe:
  {{- include "org-standards.probes.http" (dict "path" (.healthPath | default "/health") "port" .port "context" .context) | nindent 2 }}
readinessProbe:
  {{- include "org-standards.probes.http" (dict "path" (.readyPath | default "/ready") "port" .port "context" .context) | nindent 2 }}
{{- end }}
