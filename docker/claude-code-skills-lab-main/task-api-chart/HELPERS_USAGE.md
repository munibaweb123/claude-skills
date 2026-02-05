# Helm Helpers Usage Guide

This guide demonstrates how to use the helper templates defined in `templates/_helpers.tpl`.

## Available Helpers

### 1. Basic Naming Helpers

#### task-api-chart.name
Returns the chart name (can be overridden with `nameOverride`).

```yaml
# Usage in templates
metadata:
  name: {{ include "task-api-chart.name" . }}

# Output example: task-api
```

#### task-api-chart.fullname
Returns the full resource name (release-name + chart-name).

```yaml
# Usage in templates
metadata:
  name: {{ include "task-api-chart.fullname" . }}

# Output examples:
# - myrelease-task-api (if release name doesn't contain chart name)
# - myrelease (if release name already contains chart name)
```

#### task-api-chart.chart
Returns chart name and version for labels.

```yaml
# Usage in templates
labels:
  helm.sh/chart: {{ include "task-api-chart.chart" . }}

# Output example: task-api-0.1.0
```

### 2. Label Helpers

#### task-api-chart.labels
Returns all common labels (includes selector labels + metadata).

```yaml
# Usage in templates
metadata:
  labels:
    {{- include "task-api-chart.labels" . | nindent 4 }}

# Output:
# helm.sh/chart: task-api-0.1.0
# app.kubernetes.io/name: task-api
# app.kubernetes.io/instance: myrelease
# app.kubernetes.io/version: "1.0.0"
# app.kubernetes.io/managed-by: Helm
```

#### task-api-chart.selectorLabels
Returns only selector labels (used in pod selectors).

```yaml
# Usage in Deployment spec
spec:
  selector:
    matchLabels:
      {{- include "task-api-chart.selectorLabels" . | nindent 6 }}

# Output:
# app.kubernetes.io/name: task-api
# app.kubernetes.io/instance: myrelease
```

### 3. Image Helper

#### task-api-chart.image
Constructs the full container image string.

```yaml
# Usage in containers
containers:
  - name: {{ .Chart.Name }}
    image: {{ include "task-api-chart.image" . }}

# With values.yaml:
# image:
#   registry: "docker.io"
#   repository: "myuser/task-api"
#   tag: "v1.2.3"
#
# Output: docker.io/myuser/task-api:v1.2.3

# Without registry:
# image:
#   repository: "myuser/task-api"
#   tag: "v1.2.3"
#
# Output: myuser/task-api:v1.2.3
```

### 4. Resource Name with Suffix

#### task-api-chart.resourceName
Creates a resource name with a custom suffix.

```yaml
# Usage for related resources (ConfigMap, Secret, etc.)
metadata:
  name: {{ include "task-api-chart.resourceName" (dict "context" . "suffix" "config") }}

# Output: myrelease-task-api-config

# Other examples:
{{- include "task-api-chart.resourceName" (dict "context" . "suffix" "cache") }}
# Output: myrelease-task-api-cache

{{- include "task-api-chart.resourceName" (dict "context" . "suffix" "secret") }}
# Output: myrelease-task-api-secret
```

### 5. API Version Helpers

#### task-api-chart.ingress.apiVersion
Returns the correct Ingress API version based on Kubernetes version.

```yaml
# Usage in ingress.yaml
apiVersion: {{ include "task-api-chart.ingress.apiVersion" . }}
kind: Ingress

# Output (K8s >=1.19): networking.k8s.io/v1
# Output (K8s >=1.14): networking.k8s.io/v1beta1
# Output (K8s <1.14): extensions/v1beta1
```

#### task-api-chart.hpa.apiVersion
Returns the correct HPA API version based on Kubernetes version.

```yaml
# Usage in hpa.yaml
apiVersion: {{ include "task-api-chart.hpa.apiVersion" . }}
kind: HorizontalPodAutoscaler

# Output (K8s >=1.23): autoscaling/v2
# Output (K8s <1.23): autoscaling/v2beta2
```

### 6. Common Annotations

#### task-api-chart.commonAnnotations
Returns common annotations defined in values.yaml.

```yaml
# Usage in any resource
metadata:
  annotations:
    {{- include "task-api-chart.commonAnnotations" . | nindent 4 }}

# With values.yaml:
# commonAnnotations:
#   team: "backend"
#   project: "task-api"
#
# Output:
# team: "backend"
# project: "task-api"
```

### 7. Environment-Specific Replicas

#### task-api-chart.replicas
Returns replica count based on environment.

```yaml
# Usage in deployment.yaml
{{- if not .Values.autoscaling.enabled }}
replicas: {{ include "task-api-chart.replicas" . }}
{{- end }}

# With values.yaml:
# environment: production
# replicaCount: 5
#
# Defaults by environment:
# - production: 3 (or specified replicaCount)
# - staging: 2 (or specified replicaCount)
# - dev/other: 1 (or specified replicaCount)
```

## Complete Examples

### Deployment Using Multiple Helpers

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "task-api-chart.fullname" . }}
  labels:
    {{- include "task-api-chart.labels" . | nindent 4 }}
  annotations:
    {{- include "task-api-chart.commonAnnotations" . | nindent 4 }}
spec:
  {{- if not .Values.autoscaling.enabled }}
  replicas: {{ include "task-api-chart.replicas" . }}
  {{- end }}
  selector:
    matchLabels:
      {{- include "task-api-chart.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      labels:
        {{- include "task-api-chart.labels" . | nindent 8 }}
    spec:
      serviceAccountName: {{ include "task-api-chart.serviceAccountName" . }}
      containers:
        - name: {{ .Chart.Name }}
          image: {{ include "task-api-chart.image" . }}
          imagePullPolicy: {{ .Values.image.pullPolicy }}
```

### ConfigMap with Resource Name Helper

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ include "task-api-chart.resourceName" (dict "context" . "suffix" "config") }}
  labels:
    {{- include "task-api-chart.labels" . | nindent 4 }}
data:
  app.conf: |
    # Configuration file
```

### Ingress with API Version Helper

```yaml
{{- if .Values.ingress.enabled -}}
apiVersion: {{ include "task-api-chart.ingress.apiVersion" . }}
kind: Ingress
metadata:
  name: {{ include "task-api-chart.fullname" . }}
  labels:
    {{- include "task-api-chart.labels" . | nindent 4 }}
spec:
  rules:
    - host: {{ .Values.ingress.host }}
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: {{ include "task-api-chart.fullname" . }}
                port:
                  number: {{ .Values.service.port }}
{{- end }}
```

## Context Passing Examples

### Using Root Context ($) in Loops

```yaml
# Problem: Need to access root values inside a range loop
{{- range .Values.ingress.hosts }}
  - host: {{ .host }}  # . is the current host object
    http:
      paths:
        - path: /
          backend:
            service:
              # $ accesses the root context
              name: {{ include "task-api-chart.fullname" $ }}
              port:
                number: {{ $.Values.service.port }}
{{- end }}
```

### Passing Context to Custom Helpers

```yaml
# Pass the full context (.)
{{- include "task-api-chart.labels" . | nindent 4 }}

# Pass modified context with dict
{{- include "task-api-chart.resourceName" (dict "context" . "suffix" "cache") }}

# Store root in variable for clarity
{{- $root := . -}}
{{- range .Values.services }}
  name: {{ include "task-api-chart.fullname" $root }}-{{ .name }}
{{- end }}
```

## Indentation Guide

Use `nindent` to add proper indentation:

```yaml
# 2 spaces - Top-level YAML keys
annotations:
  {{- include "task-api-chart.commonAnnotations" . | nindent 2 }}

# 4 spaces - Nested under metadata
metadata:
  labels:
    {{- include "task-api-chart.labels" . | nindent 4 }}

# 6 spaces - Nested in spec.selector.matchLabels
spec:
  selector:
    matchLabels:
      {{- include "task-api-chart.selectorLabels" . | nindent 6 }}

# 8 spaces - Pod template labels
spec:
  template:
    metadata:
      labels:
        {{- include "task-api-chart.labels" . | nindent 8 }}

# 12 spaces - Container resources
containers:
  - name: app
    resources:
      {{- toYaml .Values.resources | nindent 12 }}
```

## Testing Your Templates

```bash
# Render templates locally to test helpers
helm template myrelease ./task-api-chart --debug

# Test with specific values
helm template myrelease ./task-api-chart \
  --set image.repository="myrepo/myapp" \
  --set image.tag="v2.0.0" \
  --debug

# Test with environment-specific values
helm template myrelease ./task-api-chart \
  -f values-prod.yaml \
  --debug

# Check only deployment output
helm template myrelease ./task-api-chart \
  --show-only templates/deployment.yaml
```

## Common Patterns

### Adding Custom Labels Alongside Helper Labels

```yaml
metadata:
  labels:
    {{- include "task-api-chart.labels" . | nindent 4 }}
    custom-label: "custom-value"
    environment: {{ .Values.environment | quote }}
```

### Conditional Resource Creation

```yaml
{{- if .Values.configMap.enabled }}
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ include "task-api-chart.resourceName" (dict "context" . "suffix" "config") }}
  labels:
    {{- include "task-api-chart.labels" . | nindent 4 }}
data:
  {{- range $key, $value := .Values.configMap.data }}
  {{ $key }}: {{ $value | quote }}
  {{- end }}
{{- end }}
```

## Further Reading

For more detailed information about helper templates and advanced patterns, see:
- [`.claude/skills/helm-chart-skill/references/HELPERS.md`](../.claude/skills/helm-chart-skill/references/HELPERS.md)
- [`.claude/skills/helm-chart-skill/references/TEMPLATES.md`](../.claude/skills/helm-chart-skill/references/TEMPLATES.md)
