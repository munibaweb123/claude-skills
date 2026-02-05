{{/*
================================================================================
RESOURCES TEMPLATES
================================================================================
Standardized resource limits and requests for consistent sizing across workloads.
*/}}

{{/*
org-standards.resources - Resource limits and requests by size

Provides standardized resource configurations for common workload sizes.
Ensures consistent resource allocation and prevents resource starvation.

Usage:
  resources:
    {{- include "org-standards.resources" (dict "size" "medium" "context" .) | nindent 12 }}

Parameters:
  - size: Resource size preset (micro, small, medium, large, xlarge) (required)
  - context: Root context (required, pass as ".")

Values (from context):
  - .Values.resources.limits: Override specific limits (optional)
  - .Values.resources.requests: Override specific requests (optional)

Sizes:
  - micro: 100m CPU / 128Mi RAM (dev, sidecars)
  - small: 250m CPU / 256Mi RAM (small services)
  - medium: 500m CPU / 512Mi RAM (default services)
  - large: 1000m CPU / 1Gi RAM (high-traffic services)
  - xlarge: 2000m CPU / 2Gi RAM (compute-intensive)

Output: Resource limits and requests configuration
*/}}
{{- define "org-standards.resources" -}}
{{- $sizes := dict
  "micro" (dict "cpu" "100m" "memory" "128Mi" "cpuLimit" "200m" "memoryLimit" "256Mi")
  "small" (dict "cpu" "250m" "memory" "256Mi" "cpuLimit" "500m" "memoryLimit" "512Mi")
  "medium" (dict "cpu" "500m" "memory" "512Mi" "cpuLimit" "1000m" "memoryLimit" "1Gi")
  "large" (dict "cpu" "1000m" "memory" "1Gi" "cpuLimit" "2000m" "memoryLimit" "2Gi")
  "xlarge" (dict "cpu" "2000m" "memory" "2Gi" "cpuLimit" "4000m" "memoryLimit" "4Gi")
  "xxlarge" (dict "cpu" "4000m" "memory" "4Gi" "cpuLimit" "8000m" "memoryLimit" "8Gi")
}}
{{- $selected := index $sizes .size | default (index $sizes "medium") }}
{{- $limits := .context.Values.resources.limits | default dict }}
{{- $requests := .context.Values.resources.requests | default dict }}
limits:
  cpu: {{ $limits.cpu | default $selected.cpuLimit }}
  memory: {{ $limits.memory | default $selected.memoryLimit }}
requests:
  cpu: {{ $requests.cpu | default $selected.cpu }}
  memory: {{ $requests.memory | default $selected.memory }}
{{- end }}

{{/*
org-standards.resources.burstable - Burstable QoS resources

Configures resources for burstable QoS (requests < limits).
Allows bursting for traffic spikes while maintaining guaranteed baseline.

Usage:
  resources:
    {{- include "org-standards.resources.burstable" (dict "requestsCpu" "100m" "requestsMemory" "256Mi" "limitsCpu" "500m" "limitsMemory" "512Mi" "context" .) | nindent 12 }}

Parameters:
  - requestsCpu: CPU requests (required)
  - requestsMemory: Memory requests (required)
  - limitsCpu: CPU limits (required)
  - limitsMemory: Memory limits (required)
  - context: Root context (required, pass as ".")

Output: Burstable resource configuration
*/}}
{{- define "org-standards.resources.burstable" -}}
limits:
  cpu: {{ .limitsCpu }}
  memory: {{ .limitsMemory }}
requests:
  cpu: {{ .requestsCpu }}
  memory: {{ .requestsMemory }}
{{- end }}

{{/*
org-standards.resources.guaranteed - Guaranteed QoS resources

Configures resources for guaranteed QoS (requests == limits).
Provides highest priority and predictable performance.

Usage:
  resources:
    {{- include "org-standards.resources.guaranteed" (dict "cpu" "500m" "memory" "512Mi" "context" .) | nindent 12 }}

Parameters:
  - cpu: CPU allocation (required)
  - memory: Memory allocation (required)
  - context: Root context (required, pass as ".")

Output: Guaranteed resource configuration (requests == limits)
*/}}
{{- define "org-standards.resources.guaranteed" -}}
limits:
  cpu: {{ .cpu }}
  memory: {{ .memory }}
requests:
  cpu: {{ .cpu }}
  memory: {{ .memory }}
{{- end }}

{{/*
org-standards.resources.minimal - Minimal resources for sidecars

Minimal resource allocation for sidecars and utility containers.

Usage:
  resources:
    {{- include "org-standards.resources.minimal" . | nindent 12 }}

Output: Minimal resource configuration
*/}}
{{- define "org-standards.resources.minimal" -}}
limits:
  cpu: 50m
  memory: 64Mi
requests:
  cpu: 10m
  memory: 32Mi
{{- end }}

{{/*
org-standards.resources.gpu - GPU resources

Adds GPU resource requests for ML workloads.

Usage:
  resources:
    {{- include "org-standards.resources.gpu" (dict "size" "medium" "gpuCount" 1 "gpuType" "nvidia.com/gpu" "context" .) | nindent 12 }}

Parameters:
  - size: Base resource size (micro, small, medium, large, xlarge) (required)
  - gpuCount: Number of GPUs (default: 1)
  - gpuType: GPU resource type (default: nvidia.com/gpu)
  - context: Root context (required, pass as ".")

Output: Resource configuration including GPU requests
*/}}
{{- define "org-standards.resources.gpu" -}}
{{- $sizes := dict
  "micro" (dict "cpu" "100m" "memory" "128Mi" "cpuLimit" "200m" "memoryLimit" "256Mi")
  "small" (dict "cpu" "250m" "memory" "256Mi" "cpuLimit" "500m" "memoryLimit" "512Mi")
  "medium" (dict "cpu" "500m" "memory" "512Mi" "cpuLimit" "1000m" "memoryLimit" "1Gi")
  "large" (dict "cpu" "1000m" "memory" "1Gi" "cpuLimit" "2000m" "memoryLimit" "2Gi")
  "xlarge" (dict "cpu" "2000m" "memory" "2Gi" "cpuLimit" "4000m" "memoryLimit" "4Gi")
}}
{{- $selected := index $sizes .size | default (index $sizes "medium") }}
limits:
  cpu: {{ $selected.cpuLimit }}
  memory: {{ $selected.memoryLimit }}
  {{ .gpuType | default "nvidia.com/gpu" }}: {{ .gpuCount | default 1 }}
requests:
  cpu: {{ $selected.cpu }}
  memory: {{ $selected.memory }}
  {{ .gpuType | default "nvidia.com/gpu" }}: {{ .gpuCount | default 1 }}
{{- end }}

{{/*
org-standards.resources.spot - Resources for spot instances

Resource configuration optimized for spot/preemptible instances.
Lower requests to increase scheduling probability on spot nodes.

Usage:
  resources:
    {{- include "org-standards.resources.spot" (dict "size" "medium" "context" .) | nindent 12 }}

Parameters:
  - size: Resource size preset (micro, small, medium, large, xlarge) (required)
  - context: Root context (required, pass as ".")

Output: Resource configuration optimized for spot instances
*/}}
{{- define "org-standards.resources.spot" -}}
{{- $sizes := dict
  "micro" (dict "cpu" "50m" "memory" "64Mi" "cpuLimit" "200m" "memoryLimit" "256Mi")
  "small" (dict "cpu" "100m" "memory" "128Mi" "cpuLimit" "500m" "memoryLimit" "512Mi")
  "medium" (dict "cpu" "250m" "memory" "256Mi" "cpuLimit" "1000m" "memoryLimit" "1Gi")
  "large" (dict "cpu" "500m" "memory" "512Mi" "cpuLimit" "2000m" "memoryLimit" "2Gi")
  "xlarge" (dict "cpu" "1000m" "memory" "1Gi" "cpuLimit" "4000m" "memoryLimit" "4Gi")
}}
{{- $selected := index $sizes .size | default (index $sizes "medium") }}
limits:
  cpu: {{ $selected.cpuLimit }}
  memory: {{ $selected.memoryLimit }}
requests:
  cpu: {{ $selected.cpu }}
  memory: {{ $selected.memory }}
{{- end }}
