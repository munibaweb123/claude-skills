{{/*
================================================================================
SECURITY CONTEXT TEMPLATES
================================================================================
Security contexts following Kubernetes security best practices, CIS benchmarks,
and compliance requirements (SOC2, PCI-DSS).
*/}}

{{/*
org-standards.securityContext.pod - Pod-level security context

Standard pod security context with non-root execution and seccomp profile.

Usage:
  spec:
    securityContext:
      {{- include "org-standards.securityContext.pod" . | nindent 6 }}

Values:
  - .Values.security.runAsUser: User ID (default: 1000)
  - .Values.security.runAsGroup: Group ID (default: 1000)
  - .Values.security.fsGroup: Filesystem group (default: 1000)

Output: Pod security context configuration
*/}}
{{- define "org-standards.securityContext.pod" -}}
runAsNonRoot: true
runAsUser: {{ .Values.security.runAsUser | default 1000 }}
runAsGroup: {{ .Values.security.runAsGroup | default 1000 }}
fsGroup: {{ .Values.security.fsGroup | default 1000 }}
seccompProfile:
  type: {{ .Values.security.seccompProfile.type | default "RuntimeDefault" }}
{{- end }}

{{/*
org-standards.securityContext.container - Container-level security context

Restrictive container security context that follows security best practices.

Usage:
  containers:
    - name: app
      securityContext:
        {{- include "org-standards.securityContext.container" . | nindent 8 }}

Values:
  - .Values.security.capabilities: List of capabilities to add (optional)

Output: Container security context with capabilities dropped
*/}}
{{- define "org-standards.securityContext.container" -}}
allowPrivilegeEscalation: false
readOnlyRootFilesystem: true
runAsNonRoot: true
capabilities:
  drop:
    - ALL
{{- if .Values.security.capabilities }}
  add:
{{ toYaml .Values.security.capabilities | indent 4 }}
{{- end }}
{{- end }}

{{/*
org-standards.securityContext.restricted - Kubernetes restricted security standard

Implements the Kubernetes "restricted" Pod Security Standard.
This is the most restrictive security profile.

Usage:
  spec:
    securityContext:
      {{- include "org-standards.securityContext.restricted" . | nindent 6 }}

Reference: https://kubernetes.io/docs/concepts/security/pod-security-standards/#restricted

Output: Restricted pod security context
*/}}
{{- define "org-standards.securityContext.restricted" -}}
runAsNonRoot: true
runAsUser: 65534
seccompProfile:
  type: RuntimeDefault
{{- end }}

{{/*
org-standards.securityContext.baseline - Kubernetes baseline security standard

Implements the Kubernetes "baseline" Pod Security Standard.
Prevents known privilege escalations.

Usage:
  spec:
    securityContext:
      {{- include "org-standards.securityContext.baseline" . | nindent 6 }}

Reference: https://kubernetes.io/docs/concepts/security/pod-security-standards/#baseline

Output: Baseline pod security context
*/}}
{{- define "org-standards.securityContext.baseline" -}}
runAsNonRoot: true
runAsUser: {{ .Values.security.runAsUser | default 1000 }}
{{- end }}

{{/*
org-standards.securityContext.privileged - Privileged container context (use sparingly)

Only use for containers that absolutely require privileged access.
Must be explicitly enabled.

Usage:
  containers:
    - name: privileged-container
      {{- if .Values.security.allowPrivileged }}
      securityContext:
        {{- include "org-standards.securityContext.privileged" . | nindent 8 }}
      {{- end }}

Values:
  - .Values.security.allowPrivileged: Must be true to render (default: false)

Output: Privileged container security context or error
*/}}
{{- define "org-standards.securityContext.privileged" -}}
{{- if not .Values.security.allowPrivileged }}
{{- fail "Privileged containers are not allowed. Set security.allowPrivileged=true to override (requires approval)" }}
{{- end }}
privileged: true
{{- end }}

{{/*
org-standards.securityContext.readOnlyRoot - Read-only root filesystem

Forces read-only root filesystem with no additional restrictions.
Useful for init containers or special cases.

Usage:
  containers:
    - name: init
      securityContext:
        {{- include "org-standards.securityContext.readOnlyRoot" . | nindent 8 }}

Output: Read-only root filesystem configuration
*/}}
{{- define "org-standards.securityContext.readOnlyRoot" -}}
readOnlyRootFilesystem: true
{{- end }}

{{/*
org-standards.securityContext.pciDSS - PCI-DSS compliant security context

Security context meeting PCI-DSS requirements for payment processing.

Usage:
  spec:
    securityContext:
      {{- include "org-standards.securityContext.pciDSS" . | nindent 6 }}

Compliance: PCI-DSS v4.0 requirements 2.2, 6.4

Output: PCI-DSS compliant security context
*/}}
{{- define "org-standards.securityContext.pciDSS" -}}
runAsNonRoot: true
runAsUser: {{ .Values.security.runAsUser | default 10000 }}
runAsGroup: {{ .Values.security.runAsGroup | default 10000 }}
fsGroup: {{ .Values.security.fsGroup | default 10000 }}
seccompProfile:
  type: RuntimeDefault
# PCI-DSS: Read-only root filesystem
readOnlyRootFilesystem: true
{{- end }}

{{/*
org-standards.securityContext.soc2 - SOC2 compliant security context

Security context meeting SOC2 Type 2 requirements.

Usage:
  spec:
    securityContext:
      {{- include "org-standards.securityContext.soc2" . | nindent 6 }}

Compliance: SOC2 Type 2 CC6.1, CC6.6

Output: SOC2 compliant security context
*/}}
{{- define "org-standards.securityContext.soc2" -}}
# SOC2: Non-root execution
runAsNonRoot: true
runAsUser: {{ .Values.security.runAsUser | default 1000 }}
runAsGroup: {{ .Values.security.runAsGroup | default 1000 }}
fsGroup: {{ .Values.security.fsGroup | default 1000 }}

# SOC2: Secure defaults
seccompProfile:
  type: RuntimeDefault
{{- end }}
