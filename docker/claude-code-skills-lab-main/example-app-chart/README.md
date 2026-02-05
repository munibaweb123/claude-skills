# Example Application Chart

This chart demonstrates how to use the `org-standards` library chart in a real application.

## Overview

This example shows:
- How to declare `org-standards` as a dependency
- How to use library templates in your application manifests
- How to configure library behavior through values
- Best practices for organizational standardization

## Prerequisites

- Helm 3.x
- Kubernetes 1.23+

## Quick Start

### 1. Update Dependencies

First, download the `org-standards` library chart:

```bash
cd example-app-chart
helm dependency update
```

This downloads the library and places it in `charts/org-standards-1.0.0.tgz`.

### 2. Inspect Templates

Preview the rendered manifests to see how library templates expand:

```bash
helm template example-app . --debug
```

### 3. Install

```bash
helm install example-app . -n demo --create-namespace
```

### 4. Verify

```bash
# Check deployment
kubectl get deployment -n demo

# Check labels from org-standards
kubectl get deployment example-app -n demo -o yaml | grep -A 10 "labels:"

# Check security context
kubectl get deployment example-app -n demo -o yaml | grep -A 10 "securityContext:"
```

## What's Included

This chart includes:

### From org-standards Library

✅ **Labels**: Standardized labels including cost attribution
✅ **Annotations**: Monitoring (Prometheus), logging (Fluentd), tracing (Jaeger)
✅ **Security**: Pod and container security contexts (non-root, read-only root)
✅ **Probes**: HTTP liveness and readiness probes
✅ **Resources**: Medium-sized resource preset (500m CPU / 512Mi RAM)
✅ **Affinity**: Pod anti-affinity for high availability

### Application-Specific

- Deployment with 3 replicas
- ClusterIP Service on port 8080
- Ingress with TLS
- Horizontal Pod Autoscaler (3-10 replicas)

## Configuration

### Required Values

```yaml
# Cost attribution (required for production)
cost:
  center: "engineering"
  businessUnit: "product"

# Environment
environment: production
```

### Optional Overrides

```yaml
# Override security defaults
security:
  runAsUser: 1001
  capabilities:
    - NET_BIND_SERVICE

# Override resource preset
resources:
  size: large  # micro, small, medium, large, xlarge

# Override probe timing
probes:
  initialDelaySeconds: 60
  periodSeconds: 15
```

## Examples

### Development Deployment

```yaml
# values-dev.yaml
environment: development
replicaCount: 1

resources:
  size: small

autoscaling:
  enabled: false

cost:
  center: "engineering"
  businessUnit: "dev"
```

```bash
helm install example-app . -f values-dev.yaml -n dev
```

### Production Deployment

```yaml
# values-prod.yaml
environment: production
replicaCount: 5

resources:
  size: large

autoscaling:
  enabled: true
  minReplicas: 5
  maxReplicas: 20

cost:
  center: "engineering"
  businessUnit: "product"

affinity:
  podAntiAffinity:
    enabled: true
```

```bash
helm install example-app . -f values-prod.yaml -n prod --wait --atomic
```

## Understanding Library Integration

### Chart.yaml Dependency

```yaml
dependencies:
  - name: org-standards
    version: "1.0.0"
    repository: "file://../org-standards-chart"
```

This declares that your chart depends on `org-standards` library.

### Using Library Templates

In your templates, include library helpers:

```yaml
# templates/deployment.yaml
metadata:
  labels:
    {{- include "org-standards.labels.common" . | nindent 4 }}
```

The `include` function calls templates from the library chart.

### Passing Context

Always pass `.` (root context) to library templates:

```yaml
# Correct: passes context
{{- include "org-standards.labels.common" . | nindent 4 }}

# Correct: passes context in dict
{{- include "org-standards.probes.http" (dict "path" "/health" "port" 8080 "context" .) | nindent 12 }}
```

### Values Override

Library templates read values from `.Values`:

```yaml
# values.yaml
resources:
  size: medium  # Passed to org-standards.resources template

probes:
  initialDelaySeconds: 30  # Passed to org-standards.probes.* templates
```

## Customization

### Adding Custom Labels

```yaml
# values.yaml
commonLabels:
  team: backend
  project: api-gateway
  custom-label: value
```

These merge with org-standards labels.

### Conditional Library Usage

```yaml
{{- if .Values.useOrgStandards }}
{{- include "org-standards.labels.common" . }}
{{- else }}
# Custom labels here
{{- end }}
```

### Extending Library Templates

Create your own helpers that build on library templates:

```yaml
# templates/_helpers.tpl
{{- define "example-app.labels" -}}
{{- include "org-standards.labels.common" . }}
app-specific-label: value
{{- end }}
```

## Testing

### Lint

```bash
helm lint .
```

### Template Validation

```bash
# Render and validate
helm template example-app . | kubectl apply --dry-run=client -f -
```

### Verify Library Templates

```bash
# Check labels include org-standards
helm template example-app . | grep "app.kubernetes.io/managed-by"

# Check security context
helm template example-app . | grep "runAsNonRoot"

# Check resource limits
helm template example-app . | grep -A 5 "resources:"
```

## Troubleshooting

### Library Not Found

```
Error: found in Chart.yaml, but missing in charts/ directory: org-standards
```

**Solution**: Run `helm dependency update`

### Template Not Found

```
Error: template: example-app/templates/deployment.yaml:5:7: executing "example-app/templates/deployment.yaml" at <include "org-standards.labels.common" .>: error calling include: template: no template "org-standards.labels.common" associated with template "gotpl"
```

**Solution**: Ensure library chart is in `charts/` directory and has correct templates.

### Values Not Passing

If library templates aren't using your values, check:
1. Context is passed correctly (`. ` or `"context" .`)
2. Values are at the correct level (not nested incorrectly)
3. Library chart version matches

## Production Checklist

Before deploying to production:

- [ ] Set `environment: production`
- [ ] Configure `cost.center` and `cost.businessUnit`
- [ ] Enable autoscaling
- [ ] Configure appropriate resource size
- [ ] Enable pod anti-affinity
- [ ] Configure TLS for ingress
- [ ] Set appropriate probe timings
- [ ] Review security contexts
- [ ] Test with `--dry-run`

## Further Reading

- [org-standards Library Documentation](../org-standards-chart/README.md)
- [Helm Library Charts](https://helm.sh/docs/topics/library_charts/)
- [LIBRARY.md Reference](../.claude/skills/helm-chart-skill/references/LIBRARY.md)

## Support

- GitHub Issues: https://github.com/company/helm-charts/issues
- Slack: #platform-engineering
