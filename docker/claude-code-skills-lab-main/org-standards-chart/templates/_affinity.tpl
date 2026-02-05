{{/*
================================================================================
AFFINITY AND TOLERATIONS TEMPLATES
================================================================================
Pod affinity, anti-affinity, and tolerations for workload placement.
*/}}

{{/*
org-standards.affinity.podAntiAffinity - Pod anti-affinity for high availability

Spreads pods across nodes to prevent single point of failure.

Usage:
  affinity:
    {{- include "org-standards.affinity.podAntiAffinity" . | nindent 8 }}

Values:
  - .Values.affinity.podAntiAffinity.enabled: Enable anti-affinity (default: false)
  - .Values.affinity.podAntiAffinity.topologyKey: Topology key (default: kubernetes.io/hostname)

Output: Pod anti-affinity configuration
*/}}
{{- define "org-standards.affinity.podAntiAffinity" -}}
{{- if .Values.affinity.podAntiAffinity.enabled }}
podAntiAffinity:
  preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      podAffinityTerm:
        labelSelector:
          matchLabels:
            {{- include "org-standards.labels.selector" . | nindent 12 }}
        topologyKey: {{ .Values.affinity.podAntiAffinity.topologyKey | default "kubernetes.io/hostname" }}
{{- end }}
{{- end }}

{{/*
org-standards.affinity.nodeAffinity - Node affinity for specific node pools

Schedules pods to nodes with specific labels.

Usage:
  affinity:
    {{- include "org-standards.affinity.nodeAffinity" (dict "key" "nodepool" "value" "apps" "context" .) | nindent 8 }}

Parameters:
  - key: Node label key (required)
  - value: Node label value (required)
  - context: Root context (required, pass as ".")

Output: Node affinity configuration
*/}}
{{- define "org-standards.affinity.nodeAffinity" -}}
nodeAffinity:
  preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      preference:
        matchExpressions:
          - key: {{ .key }}
            operator: In
            values:
              - {{ .value }}
{{- end }}

{{/*
org-standards.affinity.zoneSpread - Spread pods across availability zones

Distributes pods across multiple availability zones for resilience.

Usage:
  topologySpreadConstraints:
    {{- include "org-standards.affinity.zoneSpread" . | nindent 4 }}

Output: Topology spread constraints for zone distribution
*/}}
{{- define "org-standards.affinity.zoneSpread" -}}
- maxSkew: 1
  topologyKey: topology.kubernetes.io/zone
  whenUnsatisfiable: ScheduleAnyway
  labelSelector:
    matchLabels:
      {{- include "org-standards.labels.selector" . | nindent 6 }}
{{- end }}

{{/*
org-standards.tolerations.spot - Tolerations for spot/preemptible instances

Allows pods to run on spot instances for cost optimization.

Usage:
  tolerations:
    {{- include "org-standards.tolerations.spot" . | nindent 4 }}

Values:
  - .Values.cost.spotEligible: Enable spot tolerations (default: false)

Output: Spot instance tolerations
*/}}
{{- define "org-standards.tolerations.spot" -}}
{{- if .Values.cost.spotEligible }}
- key: "spot"
  operator: "Equal"
  value: "true"
  effect: "NoSchedule"
- key: "kubernetes.azure.com/scalesetpriority"
  operator: "Equal"
  value: "spot"
  effect: "NoSchedule"
- key: "cloud.google.com/gke-preemptible"
  operator: "Equal"
  value: "true"
  effect: "NoSchedule"
{{- end }}
{{- end }}

{{/*
org-standards.tolerations.gpu - Tolerations for GPU nodes

Allows pods to run on GPU-tainted nodes.

Usage:
  tolerations:
    {{- include "org-standards.tolerations.gpu" . | nindent 4 }}

Output: GPU node tolerations
*/}}
{{- define "org-standards.tolerations.gpu" -}}
- key: "nvidia.com/gpu"
  operator: "Exists"
  effect: "NoSchedule"
{{- end }}

{{/*
org-standards.tolerations.custom - Custom tolerations from values

Applies custom tolerations defined in values.

Usage:
  tolerations:
    {{- include "org-standards.tolerations.custom" . | nindent 4 }}

Values:
  - .Values.tolerations: List of custom tolerations

Output: Custom tolerations from values
*/}}
{{- define "org-standards.tolerations.custom" -}}
{{- if .Values.tolerations }}
{{ toYaml .Values.tolerations }}
{{- end }}
{{- end }}
