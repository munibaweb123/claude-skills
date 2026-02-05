# Helm Library Charts - Practical Guide

A hands-on guide to creating and using Helm library charts for organizational standards.

## What Are Library Charts?

Library charts are Helm charts that:
- **Cannot be installed** directly to a cluster
- **Provide reusable templates** that other charts can include
- **Standardize patterns** across an organization
- **Reduce duplication** and enforce best practices

Think of them as a "shared template library" for all your Helm charts.

## Quick Start

### 1. Create a Library Chart

```bash
# Create directory structure
mkdir org-standards
cd org-standards

# Create Chart.yaml
cat > Chart.yaml <<EOF
apiVersion: v2
name: org-standards
description: "Organizational standards library"
type: library
version: 1.0.0
EOF

# Create templates directory
mkdir templates

# All library templates start with underscore
touch templates/_labels.tpl
touch templates/_security.tpl
touch templates/_probes.tpl
```

### 2. Create Reusable Templates

```yaml
# templates/_labels.tpl
{{- define "org-standards.labels.common" -}}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/instance: {{ .Release.Name }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version }}
{{- end }}
```

### 3. Use in Application Chart

```yaml
# my-app/Chart.yaml
dependencies:
  - name: org-standards
    version: "1.0.0"
    repository: "file://../org-standards"
```

```bash
# Update dependencies
cd my-app
helm dependency update
```

```yaml
# my-app/templates/deployment.yaml
metadata:
  labels:
    {{- include "org-standards.labels.common" . | nindent 4 }}
```

## Common Patterns

### Pattern 1: Standard Labels

**Problem**: Every chart defines the same labels differently.

**Solution**: Library template for consistent labels.

```yaml
# Library: org-standards/templates/_labels.tpl
{{- define "org-standards.labels.common" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- if .Values.commonLabels }}
{{ toYaml .Values.commonLabels }}
{{- end }}
{{- end }}

{{- define "org-standards.labels.selector" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
```

**Usage in Application**:

```yaml
# Application: my-app/templates/deployment.yaml
metadata:
  labels:
    {{- include "org-standards.labels.common" . | nindent 4 }}
spec:
  selector:
    matchLabels:
      {{- include "org-standards.labels.selector" . | nindent 6 }}
```

### Pattern 2: Security Contexts

**Problem**: Different teams configure security contexts inconsistently.

**Solution**: Pre-defined security profiles in library.

```yaml
# Library: org-standards/templates/_security.tpl
{{- define "org-standards.securityContext.pod" -}}
runAsNonRoot: true
runAsUser: {{ .Values.security.runAsUser | default 1000 }}
runAsGroup: {{ .Values.security.runAsGroup | default 1000 }}
fsGroup: {{ .Values.security.fsGroup | default 1000 }}
seccompProfile:
  type: RuntimeDefault
{{- end }}

{{- define "org-standards.securityContext.container" -}}
allowPrivilegeEscalation: false
readOnlyRootFilesystem: true
runAsNonRoot: true
capabilities:
  drop:
    - ALL
{{- end }}

{{- define "org-standards.securityContext.restricted" -}}
# Kubernetes restricted security standard
runAsNonRoot: true
runAsUser: 65534
seccompProfile:
  type: RuntimeDefault
{{- end }}
```

**Usage**:

```yaml
# Application: my-app/templates/deployment.yaml
spec:
  template:
    spec:
      securityContext:
        {{- include "org-standards.securityContext.pod" . | nindent 8 }}
      containers:
        - name: app
          securityContext:
            {{- include "org-standards.securityContext.container" . | nindent 12 }}
```

### Pattern 3: Health Probes

**Problem**: Teams configure probes with different timings and formats.

**Solution**: Parameterized probe templates.

```yaml
# Library: org-standards/templates/_probes.tpl
{{- define "org-standards.probes.http" -}}
httpGet:
  path: {{ .path }}
  port: {{ .port }}
  scheme: {{ .scheme | default "HTTP" }}
initialDelaySeconds: {{ .context.Values.probes.initialDelaySeconds | default 30 }}
periodSeconds: {{ .context.Values.probes.periodSeconds | default 10 }}
timeoutSeconds: {{ .context.Values.probes.timeoutSeconds | default 5 }}
failureThreshold: {{ .context.Values.probes.failureThreshold | default 3 }}
{{- end }}

{{- define "org-standards.probes.tcp" -}}
tcpSocket:
  port: {{ .port }}
initialDelaySeconds: {{ .context.Values.probes.initialDelaySeconds | default 15 }}
periodSeconds: {{ .context.Values.probes.periodSeconds | default 10 }}
{{- end }}
```

**Usage with Parameters**:

```yaml
# Application: my-app/templates/deployment.yaml
livenessProbe:
  {{- include "org-standards.probes.http" (dict
    "path" "/health"
    "port" 8080
    "context" .
  ) | nindent 12 }}

readinessProbe:
  {{- include "org-standards.probes.http" (dict
    "path" "/ready"
    "port" 8080
    "context" .
  ) | nindent 12 }}
```

### Pattern 4: Resource Presets

**Problem**: Inconsistent resource allocations lead to over/under-provisioning.

**Solution**: Standard resource size presets.

```yaml
# Library: org-standards/templates/_resources.tpl
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

**Usage**:

```yaml
# Application: my-app/values.yaml
resources:
  size: medium  # or small, large, xlarge

# Application: my-app/templates/deployment.yaml
resources:
  {{- include "org-standards.resources" (dict "size" .Values.resources.size "context" .) | nindent 12 }}
```

### Pattern 5: Cost Attribution

**Problem**: No consistent way to track cloud costs by team/project.

**Solution**: Mandatory cost labels in production.

```yaml
# Library: org-standards/templates/_labels.tpl
{{- define "org-standards.labels.cost" -}}
{{- if eq .Values.environment "production" }}
{{- if not .Values.cost.center }}
{{- fail "cost.center is required for production deployments" }}
{{- end }}
{{- if not .Values.cost.businessUnit }}
{{- fail "cost.businessUnit is required for production deployments" }}
{{- end }}
{{- end }}
cost-center: {{ .Values.cost.center | default "unknown" | quote }}
business-unit: {{ .Values.cost.businessUnit | default "unknown" | quote }}
environment: {{ .Values.environment | quote }}
{{- end }}
```

**Usage**:

```yaml
# Application: my-app/values-prod.yaml
environment: production
cost:
  center: "engineering"
  businessUnit: "product"

# Application: my-app/templates/deployment.yaml
metadata:
  labels:
    {{- include "org-standards.labels.cost" . | nindent 4 }}
```

## Enterprise Use Cases

### Use Case 1: Multi-Tenant Security

Create network policies from library:

```yaml
# Library: org-standards/templates/_network.tpl
{{- define "org-standards.networkPolicy.isolation" -}}
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: {{ .Release.Name }}-isolation
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/instance: {{ .Release.Name }}
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
      - podSelector: {}  # Same namespace only
  egress:
    - to:
      - podSelector: {}
    - to:  # Allow DNS
      - namespaceSelector:
          matchLabels:
            name: kube-system
      ports:
      - protocol: UDP
        port: 53
{{- end }}
```

### Use Case 2: Compliance (SOC2, PCI-DSS)

```yaml
# Library: org-standards/templates/_security.tpl
{{- define "org-standards.securityContext.pciDSS" -}}
# PCI-DSS v4.0 compliant security context
runAsNonRoot: true
runAsUser: 10000
runAsGroup: 10000
fsGroup: 10000
seccompProfile:
  type: RuntimeDefault
{{- end }}
```

### Use Case 3: Observability Standards

```yaml
# Library: org-standards/templates/_annotations.tpl
{{- define "org-standards.annotations.observability" -}}
# Prometheus
prometheus.io/scrape: "true"
prometheus.io/port: {{ .Values.metrics.port | default "8080" | quote }}
prometheus.io/path: {{ .Values.metrics.path | default "/metrics" | quote }}

# Datadog
ad.datadoghq.com/{{ .Chart.Name }}.logs: '[{"source":"{{ .Chart.Name }}","service":"{{ .Chart.Name }}"}]'

# Jaeger
sidecar.jaegertracing.io/inject: {{ .Values.tracing.enabled | default "true" | quote }}

# Fluentd
fluentd.io/include: "true"
fluentd.io/parser-type: "json"
{{- end }}
```

## Advanced Techniques

### Technique 1: Conditional Templates

Allow applications to opt-out when needed:

```yaml
# Library: org-standards/templates/_labels.tpl
{{- define "org-standards.labels.smart" -}}
{{- if .Values.useOrgStandards | default true }}
{{- include "org-standards.labels.common" . }}
{{- else }}
app: {{ .Chart.Name }}
{{- end }}
{{- end }}
```

### Technique 2: Merging Library + Custom

```yaml
# Application: my-app/templates/_helpers.tpl
{{- define "my-app.labels" -}}
{{- include "org-standards.labels.common" . }}
app.my-company.com/custom: "value"
{{- end }}
```

### Technique 3: Environment-Specific Behavior

```yaml
# Library: Choose security profile by environment
{{- define "org-standards.securityContext.auto" -}}
{{- if eq .Values.environment "production" }}
{{- include "org-standards.securityContext.restricted" . }}
{{- else }}
{{- include "org-standards.securityContext.baseline" . }}
{{- end }}
{{- end }}
```

### Technique 4: Values Schema Validation

Create schema for library configuration:

```json
// Library: org-standards/values.schema.json
{
  "$schema": "https://json-schema.org/draft-07/schema#",
  "properties": {
    "cost": {
      "type": "object",
      "required": ["center", "businessUnit"],
      "properties": {
        "center": {"type": "string", "minLength": 1},
        "businessUnit": {"type": "string", "minLength": 1}
      }
    }
  }
}
```

## Distribution Strategies

### Strategy 1: OCI Registry (Recommended)

```bash
# Package library
helm package org-standards/

# Push to OCI registry
helm push org-standards-1.0.0.tgz oci://registry.company.com/helm-charts
```

```yaml
# Application Chart.yaml
dependencies:
  - name: org-standards
    version: "^1.0.0"
    repository: "oci://registry.company.com/helm-charts"
```

### Strategy 2: Git Submodule

```bash
# Add as submodule
git submodule add https://github.com/company/org-standards charts/org-standards
```

```yaml
# Application Chart.yaml
dependencies:
  - name: org-standards
    version: "*"
    repository: "file://charts/org-standards"
```

### Strategy 3: ChartMuseum

```bash
# Push to ChartMuseum
curl --data-binary "@org-standards-1.0.0.tgz" \
  https://chartmuseum.company.com/api/charts
```

```yaml
# Application Chart.yaml
dependencies:
  - name: org-standards
    version: "~1.0.0"
    repository: "https://chartmuseum.company.com"
```

## Migration Guide

### Migrating Existing Charts

**Step 1: Identify Common Patterns**

```bash
# Find duplicated code across charts
grep -r "app.kubernetes.io/name" */templates/ | sort | uniq -c
grep -r "runAsNonRoot" */templates/ | wc -l
```

**Step 2: Create Library Chart**

Extract common patterns into library templates.

**Step 3: Pilot with One Chart**

Choose simplest chart for initial migration:

```bash
# Before
cd my-simple-app
helm template .

# Add library dependency
# ... edit Chart.yaml ...

# Update dependencies
helm dependency update

# Replace inline templates with library includes
# ... edit templates/*.yaml ...

# After
helm template .

# Compare outputs
diff old-output.yaml new-output.yaml
```

**Step 4: Validate**

```bash
# Ensure same output
helm template my-simple-app . | sha256sum

# Test deployment
helm install test my-simple-app . --dry-run
```

**Step 5: Roll Out**

Migrate remaining charts one by one.

## Best Practices

### ✅ DO

1. **Use Clear Naming**: `library-name.category.specific`
   ```yaml
   org-standards.labels.common
   org-standards.probes.http
   ```

2. **Document Every Template**:
   ```yaml
   {{/*
   org-standards.labels.common - Common Kubernetes labels

   Usage: {{ include "org-standards.labels.common" . | nindent 4 }}
   Output: YAML labels block
   */}}
   ```

3. **Provide Defaults**:
   ```yaml
   runAsUser: {{ .Values.security.runAsUser | default 1000 }}
   ```

4. **Version Semantically**:
   - MAJOR: Breaking changes
   - MINOR: New features
   - PATCH: Bug fixes

5. **Test Thoroughly**:
   ```bash
   helm unittest org-standards/
   ```

### ❌ DON'T

1. **Don't Create God Templates**:
   ```yaml
   # Bad: One template does everything
   {{- define "org-standards.everything" -}}

   # Good: Focused templates
   {{- define "org-standards.labels.common" -}}
   {{- define "org-standards.labels.selector" -}}
   ```

2. **Don't Hardcode Values**:
   ```yaml
   # Bad
   runAsUser: 1000

   # Good
   runAsUser: {{ .Values.security.runAsUser | default 1000 }}
   ```

3. **Don't Break Backward Compatibility** (in MINOR versions):
   ```yaml
   # Bad: Renamed in 1.1.0
   {{- define "org-standards.commonLabels" -}}  # Was .labels.common

   # Good: Deprecated with alias
   {{- define "org-standards.labels.common" -}}
   {{- define "org-standards.commonLabels" -}}
   {{- include "org-standards.labels.common" . }}
   {{- end }}
   ```

4. **Don't Forget Context**:
   ```yaml
   # Bad: No context
   {{- include "org-standards.labels.common" }}

   # Good: Pass context
   {{- include "org-standards.labels.common" . }}
   ```

## Troubleshooting

### Problem: Template Not Found

```
Error: template: no template "org-standards.labels.common" associated with template
```

**Solutions**:
1. Run `helm dependency update`
2. Check library chart is in `charts/` directory
3. Verify template name spelling
4. Ensure library Chart.yaml has `type: library`

### Problem: Values Not Passed

Templates don't use your values.

**Solution**: Pass context correctly:
```yaml
# Wrong
{{- include "org-standards.probes.http" (dict "path" "/health" "port" 8080) }}

# Correct
{{- include "org-standards.probes.http" (dict "path" "/health" "port" 8080 "context" .) }}
```

### Problem: Validation Fails

```
Error: values don't meet the specifications of the schema
```

**Solution**: Check `values.schema.json` in library chart.

## Quick Reference

### Template Syntax

```yaml
# Define template
{{- define "library-name.template-name" -}}
content here
{{- end }}

# Include template
{{- include "library-name.template-name" . | nindent 4 }}

# Include with parameters
{{- include "library-name.template" (dict "key" "value" "context" .) | nindent 4 }}
```

### Common Commands

```bash
# Create library chart
helm create my-library --type library

# Package library
helm package my-library/

# Update dependencies
helm dependency update ./my-app

# Test rendering
helm template my-app ./my-app

# Lint
helm lint ./my-library
```

## Examples Repository

See complete working examples:
- [org-standards-chart/](../../org-standards-chart/) - Full library chart
- [example-app-chart/](../../example-app-chart/) - Application using library

## Further Reading

- [Complete Reference: LIBRARY.md](references/LIBRARY.md)
- [Helm Library Charts Docs](https://helm.sh/docs/topics/library_charts/)
- [Bitnami Common Library](https://github.com/bitnami/charts/tree/main/bitnami/common)
