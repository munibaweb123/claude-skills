# Library Charts Reference

Library charts are special Helm charts that provide reusable templates and utilities for other charts. They cannot be installed directly but are included as dependencies to standardize patterns across an organization.

## Library vs Application Charts

| Feature | Application Chart | Library Chart |
|---------|------------------|---------------|
| **Type** | `type: application` | `type: library` |
| **Deployable** | ✅ Yes | ❌ No |
| **Templates** | Creates K8s resources | Provides reusable helpers |
| **Usage** | Installed to cluster | Dependency for other charts |
| **Purpose** | Deploy applications | Share organizational standards |

## When to Use Library Charts

✅ **Use library charts when you need to:**
- Standardize labels, annotations, and naming across charts
- Share common templates (probes, security contexts, resource limits)
- Enforce organizational policies (security, compliance, cost attribution)
- Reduce duplication across multiple application charts
- Centralize template logic for easier updates

❌ **Don't use library charts for:**
- Single-use templates
- Application-specific logic
- Complete Kubernetes manifests (use application charts)

## Creating a Library Chart

### 1. Chart.yaml

```yaml
apiVersion: v2
name: org-standards           # Organization-wide library name
description: "Reusable templates and standards for organization charts"
type: library                 # Critical: marks as library chart
version: 1.0.0               # Library version

maintainers:
  - name: "Platform Team"
    email: "platform@company.com"

keywords:
  - library
  - standards
  - templates
```

**Key differences from application charts:**
- `type: library` is required
- No `appVersion` (doesn't deploy an application)
- Focus on `version` for template changes

### 2. Directory Structure

```
org-standards/          # Library chart name
├── Chart.yaml         # type: library
├── values.yaml        # Default values for templates
└── templates/
    └── _*.tpl         # ALL templates start with underscore
```

**Important:**
- Library charts contain ONLY `_*.tpl` files in `templates/`
- No deployable manifests (no `deployment.yaml`, `service.yaml`, etc.)
- All templates are helpers that other charts can include

### 3. Naming Convention

Library templates use the pattern: `library-name.template-name`

```yaml
{{- define "org-standards.labels.common" -}}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ include "org-standards.chart" . }}
{{- end }}

{{- define "org-standards.annotations.monitoring" -}}
prometheus.io/scrape: "true"
prometheus.io/port: "8080"
{{- end }}

{{- define "org-standards.securityContext.pod" -}}
runAsNonRoot: true
runAsUser: 1000
fsGroup: 1000
{{- end }}
```

**Pattern:** `{{ define "library-name.category.specific" }}`

## Common Library Templates

### Template Categories

| Category | Purpose | Examples |
|----------|---------|----------|
| **labels** | Standardized labels | `common`, `selector`, `cost-attribution` |
| **annotations** | Common annotations | `monitoring`, `logging`, `security` |
| **probes** | Health checks | `http`, `tcp`, `exec` |
| **security** | Security contexts | `pod`, `container`, `restricted` |
| **resources** | Resource limits | `small`, `medium`, `large` |
| **affinity** | Pod placement | `anti-affinity`, `node-affinity` |
| **tolerations** | Node taints | `spot-instances`, `gpu-nodes` |

### Example: Labels Template

```yaml
{{/*
org-standards.labels.common - Common labels for all resources
Usage: {{ include "org-standards.labels.common" . | nindent 4 }}
*/}}
{{- define "org-standards.labels.common" -}}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/instance: {{ .Release.Name }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" }}
{{- if .Values.commonLabels }}
{{ toYaml .Values.commonLabels }}
{{- end }}
{{- end }}

{{/*
org-standards.labels.selector - Selector labels (immutable)
Usage: {{ include "org-standards.labels.selector" . | nindent 4 }}
*/}}
{{- define "org-standards.labels.selector" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
org-standards.labels.cost - Cost attribution labels
Usage: {{ include "org-standards.labels.cost" . | nindent 4 }}
*/}}
{{- define "org-standards.labels.cost" -}}
{{- if .Values.cost }}
cost-center: {{ .Values.cost.center | default "unknown" }}
business-unit: {{ .Values.cost.businessUnit | default "unknown" }}
environment: {{ .Values.environment | default "unknown" }}
{{- end }}
{{- end }}
```

### Example: Probes Template

```yaml
{{/*
org-standards.probes.http - HTTP readiness/liveness probe
Usage: {{ include "org-standards.probes.http" (dict "path" "/health" "port" 8080 "context" .) | nindent 12 }}
*/}}
{{- define "org-standards.probes.http" -}}
httpGet:
  path: {{ .path }}
  port: {{ .port }}
  scheme: HTTP
initialDelaySeconds: {{ .context.Values.probes.initialDelaySeconds | default 30 }}
periodSeconds: {{ .context.Values.probes.periodSeconds | default 10 }}
timeoutSeconds: {{ .context.Values.probes.timeoutSeconds | default 5 }}
successThreshold: {{ .context.Values.probes.successThreshold | default 1 }}
failureThreshold: {{ .context.Values.probes.failureThreshold | default 3 }}
{{- end }}

{{/*
org-standards.probes.tcp - TCP socket probe
Usage: {{ include "org-standards.probes.tcp" (dict "port" 5432 "context" .) | nindent 12 }}
*/}}
{{- define "org-standards.probes.tcp" -}}
tcpSocket:
  port: {{ .port }}
initialDelaySeconds: {{ .context.Values.probes.initialDelaySeconds | default 15 }}
periodSeconds: {{ .context.Values.probes.periodSeconds | default 10 }}
timeoutSeconds: {{ .context.Values.probes.timeoutSeconds | default 3 }}
failureThreshold: {{ .context.Values.probes.failureThreshold | default 3 }}
{{- end }}
```

### Example: Security Context Template

```yaml
{{/*
org-standards.securityContext.pod - Pod-level security context
Usage: {{ include "org-standards.securityContext.pod" . | nindent 6 }}
*/}}
{{- define "org-standards.securityContext.pod" -}}
runAsNonRoot: true
runAsUser: {{ .Values.security.runAsUser | default 1000 }}
runAsGroup: {{ .Values.security.runAsGroup | default 1000 }}
fsGroup: {{ .Values.security.fsGroup | default 1000 }}
seccompProfile:
  type: RuntimeDefault
{{- end }}

{{/*
org-standards.securityContext.container - Container-level security context
Usage: {{ include "org-standards.securityContext.container" . | nindent 12 }}
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
Usage: {{ include "org-standards.securityContext.restricted" . | nindent 6 }}
*/}}
{{- define "org-standards.securityContext.restricted" -}}
runAsNonRoot: true
runAsUser: 65534
seccompProfile:
  type: RuntimeDefault
{{- end }}
```

### Example: Resources Template

```yaml
{{/*
org-standards.resources - Resource limits and requests
Usage: {{ include "org-standards.resources" (dict "size" "medium" "context" .) | nindent 12 }}
Sizes: micro, small, medium, large, xlarge
*/}}
{{- define "org-standards.resources" -}}
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
requests:
  cpu: {{ $selected.cpu }}
  memory: {{ $selected.memory }}
{{- end }}
```

## Using Library Charts in Application Charts

### 1. Declare Dependency

In your application chart's `Chart.yaml`:

```yaml
apiVersion: v2
name: my-application
description: "My application using org standards"
type: application
version: 1.0.0

dependencies:
  - name: org-standards
    version: "^1.0.0"
    repository: "oci://registry.company.com/helm-charts"
    # Or local path during development:
    # repository: "file://../org-standards"
```

### 2. Update Dependencies

```bash
# Download library chart
helm dependency update ./my-application

# Verify library is available
ls my-application/charts/
# Output: org-standards-1.0.0.tgz
```

### 3. Use Library Templates

In your application's templates:

```yaml
# templates/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Release.Name }}
  labels:
    {{- include "org-standards.labels.common" . | nindent 4 }}
    {{- include "org-standards.labels.selector" . | nindent 4 }}
    {{- include "org-standards.labels.cost" . | nindent 4 }}
  annotations:
    {{- include "org-standards.annotations.monitoring" . | nindent 4 }}
spec:
  selector:
    matchLabels:
      {{- include "org-standards.labels.selector" . | nindent 6 }}
  template:
    metadata:
      labels:
        {{- include "org-standards.labels.selector" . | nindent 8 }}
    spec:
      securityContext:
        {{- include "org-standards.securityContext.pod" . | nindent 8 }}
      containers:
        - name: app
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          securityContext:
            {{- include "org-standards.securityContext.container" . | nindent 12 }}
          resources:
            {{- include "org-standards.resources" (dict "size" .Values.resources.size "context" .) | nindent 12 }}
          livenessProbe:
            {{- include "org-standards.probes.http" (dict "path" "/health" "port" 8080 "context" .) | nindent 12 }}
          readinessProbe:
            {{- include "org-standards.probes.http" (dict "path" "/ready" "port" 8080 "context" .) | nindent 12 }}
```

### 4. Configure via Values

Application chart's `values.yaml`:

```yaml
# Application-specific values
image:
  repository: myapp
  tag: "1.0.0"

# Library configuration (passed to org-standards templates)
resources:
  size: medium  # Uses org-standards.resources template

cost:
  center: "engineering"
  businessUnit: "product"

environment: "production"

security:
  runAsUser: 1001
  capabilities:
    - NET_BIND_SERVICE

probes:
  initialDelaySeconds: 60
  periodSeconds: 15

commonLabels:
  team: "backend"
  project: "api-gateway"
```

## Override Patterns

### Pattern 1: Conditional Override

Allow applications to optionally use library defaults:

```yaml
{{- define "myapp.labels" -}}
{{- if .Values.useOrgStandards }}
{{- include "org-standards.labels.common" . }}
{{- else }}
app: {{ .Chart.Name }}
version: {{ .Chart.Version }}
{{- end }}
{{- end }}
```

### Pattern 2: Merge with Custom

Combine library standards with application-specific additions:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Release.Name }}
  labels:
    # Standard organizational labels
    {{- include "org-standards.labels.common" . | nindent 4 }}
    # Application-specific labels
    app.kubernetes.io/component: {{ .Values.component }}
    version: {{ .Values.version }}
```

### Pattern 3: Values-Based Selection

Choose library template based on environment:

```yaml
{{- if eq .Values.environment "production" }}
securityContext:
  {{- include "org-standards.securityContext.restricted" . | nindent 10 }}
{{- else }}
securityContext:
  {{- include "org-standards.securityContext.pod" . | nindent 10 }}
{{- end }}
```

### Pattern 4: Parameterized Templates

Pass application-specific parameters to library templates:

```yaml
# Application passes custom values to library template
livenessProbe:
  {{- include "org-standards.probes.http" (dict
    "path" .Values.healthCheck.path
    "port" .Values.service.port
    "context" .
  ) | nindent 12 }}
```

## Enterprise Use Cases

### Use Case 1: Security Compliance

Enforce security policies across all applications:

```yaml
# org-standards/templates/_security.tpl

{{/*
org-standards.podSecurityPolicy - PSP for SOC 2 compliance
*/}}
{{- define "org-standards.podSecurityPolicy" -}}
securityContext:
  # SOC 2 requirement: non-root execution
  runAsNonRoot: true
  runAsUser: {{ .Values.security.runAsUser | default 10000 }}

  # PCI-DSS requirement: filesystem restrictions
  readOnlyRootFilesystem: true

  # CIS Benchmark: drop all capabilities
  seccompProfile:
    type: RuntimeDefault
{{- end }}
```

### Use Case 2: Cost Attribution

Standardize cost tracking labels:

```yaml
{{/*
org-standards.labels.finops - FinOps cost attribution
*/}}
{{- define "org-standards.labels.finops" -}}
# Required for chargeback
cost-center: {{ required "cost.center is required for production" .Values.cost.center }}
business-unit: {{ required "cost.businessUnit is required" .Values.cost.businessUnit }}
application: {{ .Chart.Name }}
environment: {{ .Values.environment }}

# Optional for cost optimization
cost-optimization/right-sizing: "enabled"
cost-optimization/spot-eligible: {{ .Values.cost.spotEligible | default "false" | quote }}
{{- end }}
```

### Use Case 3: Observability Standards

Ensure consistent monitoring and logging:

```yaml
{{/*
org-standards.annotations.observability - Full observability stack
*/}}
{{- define "org-standards.annotations.observability" -}}
# Prometheus metrics
prometheus.io/scrape: "true"
prometheus.io/port: {{ .Values.metrics.port | default "8080" | quote }}
prometheus.io/path: {{ .Values.metrics.path | default "/metrics" | quote }}

# Datadog APM
ad.datadoghq.com/{{ .Chart.Name }}.logs: '[{"source":"{{ .Chart.Name }}","service":"{{ .Chart.Name }}"}]'

# Jaeger tracing
sidecar.jaegertracing.io/inject: {{ .Values.tracing.enabled | default "true" | quote }}

# Fluentd logging
fluentd.io/include: "true"
fluentd.io/parser-type: "json"
{{- end }}
```

### Use Case 4: Multi-Tenant Isolation

Network policies and resource quotas:

```yaml
{{/*
org-standards.networkPolicy - Tenant isolation policy
*/}}
{{- define "org-standards.networkPolicy" -}}
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: {{ .Release.Name }}-isolation
spec:
  podSelector:
    matchLabels:
      {{- include "org-standards.labels.selector" . | nindent 6 }}
  policyTypes:
    - Ingress
    - Egress
  ingress:
    # Allow from same namespace only
    - from:
      - podSelector: {}
  egress:
    # Allow DNS
    - to:
      - namespaceSelector:
          matchLabels:
            name: kube-system
      ports:
      - protocol: UDP
        port: 53
    # Allow same namespace
    - to:
      - podSelector: {}
{{- end }}
```

## Library Chart Versioning

### Version Strategy

```yaml
# Semantic versioning for library charts
version: MAJOR.MINOR.PATCH

# MAJOR: Breaking changes to template names or parameters
# 1.0.0 -> 2.0.0: Renamed "org-standards.labels" to "org-standards.labels.common"

# MINOR: New templates or parameters (backward compatible)
# 1.0.0 -> 1.1.0: Added "org-standards.probes.exec" template

# PATCH: Bug fixes or documentation updates
# 1.0.0 -> 1.0.1: Fixed nindent spacing in labels template
```

### Dependency Version Constraints

```yaml
dependencies:
  - name: org-standards
    # Pin exact version (safest, no surprises)
    version: "1.0.0"

    # Allow patch updates (safe, bug fixes only)
    version: "~1.0.0"  # Matches 1.0.x

    # Allow minor updates (new features, backward compatible)
    version: "^1.0.0"  # Matches 1.x.x

    # Range (flexible, risky)
    version: ">=1.0.0 <2.0.0"
```

## Testing Library Charts

### Unit Tests

```yaml
# org-standards/tests/labels_test.yaml
suite: test labels
templates:
  - ../templates/_labels.tpl
tests:
  - it: should generate common labels
    template: ../templates/_labels.tpl
    set:
      commonLabels:
        team: backend
    asserts:
      - matchRegex:
          path: .
          pattern: 'app.kubernetes.io/managed-by: .*'
      - matchRegex:
          path: .
          pattern: 'helm.sh/chart: .*'
```

### Integration Testing

Test library chart in a real application:

```bash
# Create test application using library
helm create test-app

# Add library dependency
# ... edit Chart.yaml ...

# Update dependencies
helm dependency update ./test-app

# Test rendering
helm template test-app ./test-app

# Validate output includes library templates
helm template test-app ./test-app | grep "org-standards"
```

## Publishing Library Charts

### OCI Registry (Recommended)

```bash
# Package library chart
helm package org-standards/

# Login to registry
helm registry login registry.company.com

# Push to OCI registry
helm push org-standards-1.0.0.tgz oci://registry.company.com/helm-charts

# Application charts reference it
dependencies:
  - name: org-standards
    version: "1.0.0"
    repository: "oci://registry.company.com/helm-charts"
```

### ChartMuseum

```bash
# Push to ChartMuseum
curl --data-binary "@org-standards-1.0.0.tgz" \
  https://chartmuseum.company.com/api/charts

# Add repo to Helm
helm repo add company https://chartmuseum.company.com

# Application charts reference it
dependencies:
  - name: org-standards
    version: "1.0.0"
    repository: "https://chartmuseum.company.com"
```

### Git Repository (Development)

```yaml
# For local development
dependencies:
  - name: org-standards
    version: "*"
    repository: "file://../org-standards"
```

## Best Practices

### 1. Naming Conventions

```yaml
# Good: Clear hierarchy
org-standards.labels.common
org-standards.labels.selector
org-standards.labels.cost

# Bad: Flat, unclear
org-standards.commonlabels
org-standards.labels1
```

### 2. Documentation

Document every template:

```yaml
{{/*
org-standards.labels.common - Common labels for all resources

This template generates standard Kubernetes labels including:
- app.kubernetes.io/managed-by
- app.kubernetes.io/instance
- helm.sh/chart

Usage:
  {{ include "org-standards.labels.common" . | nindent 4 }}

Values:
  - .Values.commonLabels: Additional custom labels (optional)

Output: YAML labels block
*/}}
{{- define "org-standards.labels.common" -}}
...
{{- end }}
```

### 3. Parameter Passing

Use dict for multiple parameters:

```yaml
# Good: Clear parameters
{{- include "org-standards.probes.http" (dict
  "path" "/health"
  "port" 8080
  "context" .
) }}

# Bad: Unclear order
{{- include "org-standards.probes.http" "/health" 8080 . }}
```

### 4. Default Values

Always provide sensible defaults:

```yaml
{{- define "org-standards.resources" -}}
limits:
  cpu: {{ .Values.resources.limits.cpu | default "500m" }}
  memory: {{ .Values.resources.limits.memory | default "512Mi" }}
requests:
  cpu: {{ .Values.resources.requests.cpu | default "100m" }}
  memory: {{ .Values.resources.requests.memory | default "128Mi" }}
{{- end }}
```

### 5. Validation

Add validation for required values:

```yaml
{{- define "org-standards.labels.cost" -}}
{{- if eq .Values.environment "production" }}
cost-center: {{ required "cost.center required for production" .Values.cost.center }}
business-unit: {{ required "cost.businessUnit required for production" .Values.cost.businessUnit }}
{{- end }}
{{- end }}
```

## Migration Strategy

### Migrating Existing Charts to Use Library

1. **Identify Common Patterns**
   ```bash
   # Find duplicated labels across charts
   grep -r "app.kubernetes.io/name" */templates/
   ```

2. **Create Library Chart**
   ```bash
   mkdir org-standards
   helm create org-standards
   rm -rf org-standards/templates/*
   # Edit Chart.yaml: type: library
   ```

3. **Extract Templates**
   Move common templates to library `_helpers.tpl`

4. **Update One Chart First**
   Pick a simple chart for pilot migration

5. **Test Thoroughly**
   ```bash
   helm template test-chart ./test-chart
   diff old-output.yaml new-output.yaml
   ```

6. **Roll Out Gradually**
   Migrate charts one by one, not all at once

## Quick Commands

| Command | Purpose |
|---------|---------|
| `helm lint org-standards/` | Validate library chart |
| `helm template -s templates/_helpers.tpl` | N/A (use in app chart) |
| `helm dependency update ./app/` | Download library chart |
| `helm template app ./app/` | Test library integration |
| `helm package org-standards/` | Package for distribution |
| `helm push *.tgz oci://registry/` | Publish to OCI registry |

## Further Reading

- [Helm Library Charts Documentation](https://helm.sh/docs/topics/library_charts/)
- [Bitnami Common Library](https://github.com/bitnami/charts/tree/main/bitnami/common)
- [Chart Best Practices](https://helm.sh/docs/chart_best_practices/)
