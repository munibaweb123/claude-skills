---
name: helm-chart
description: Comprehensive Helm chart creation and management from hello world to professional production charts. Use when creating, customizing, packaging, or deploying Kubernetes applications with Helm charts, including basic charts, production-ready configurations, templates, and dependency management.
---

# Helm Chart Skill

This skill provides comprehensive support for creating and managing Helm charts for Kubernetes applications, from simple hello world examples to professional production-ready charts.

## When to Use This Skill

Use this skill when you need to:
- Create new Helm charts from scratch
- Generate production-ready Helm charts with best practices
- Create library charts with reusable templates for organizational standards
- Customize existing charts with values, templates, and configurations
- Package charts for distribution and deployment
- Manage Helm templates (deployments, services, ingresses, configmaps, etc.)
- Handle chart dependencies and subcharts
- Deploy applications to Kubernetes using Helm
- Set up environment-specific configurations (dev, staging, prod)
- Share common patterns across teams (labels, security contexts, probes, resources)

## Prerequisites

- Helm CLI installed and configured
- Access to a Kubernetes cluster
- Basic understanding of Kubernetes resources

## Quick Start: Hello World Chart

```bash
# Create a new chart
helm create mychart

# Verify the chart
helm lint mychart

# Install to cluster
helm install myrelease mychart

# List releases
helm list
```

## Chart Structure

A typical Helm chart contains:

```
mychart/
├── Chart.yaml          # Chart metadata (name, version, dependencies)
├── values.yaml         # Default configuration values
├── values-dev.yaml     # Development overrides (optional)
├── values-staging.yaml # Staging overrides (optional)
├── values-prod.yaml    # Production overrides (optional)
├── charts/             # Dependency charts
├── templates/          # Kubernetes manifest templates
│   ├── _helpers.tpl    # Template helper functions
│   ├── deployment.yaml # Deployment manifest
│   ├── service.yaml    # Service manifest
│   ├── configmap.yaml  # ConfigMap manifest
│   ├── ingress.yaml    # Ingress manifest
│   ├── hpa.yaml        # HorizontalPodAutoscaler
│   ├── NOTES.txt       # Post-install notes
│   └── tests/          # Test templates
└── README.md           # Chart documentation
```

## Reference Documentation

### Core References

| Reference | Description |
|-----------|-------------|
| [CHART.md](references/CHART.md) | Chart.yaml metadata fields and structure |
| [VALUES.md](references/VALUES.md) | values.yaml organization and environment-specific files |
| [VALUES_SCHEMA.md](references/VALUES_SCHEMA.md) | Values hierarchy, merge order, and schema validation |
| [TEMPLATES.md](references/TEMPLATES.md) | Complete Deployment, Service, and other templates |
| [HELPERS.md](references/HELPERS.md) | _helpers.tpl patterns, define/include, nindent, and context passing |
| [HOOKS.md](references/HOOKS.md) | Helm hooks for lifecycle management, weights, and delete policies |
| [DEPENDENCIES.md](references/DEPENDENCIES.md) | Chart dependencies and subcharts |
| [LIBRARY.md](references/LIBRARY.md) | Library charts for organizational standards and reusable templates |
| [TESTING.md](references/TESTING.md) | Testing strategies including helm-unittest and integration tests |
| [WORKFLOWS.md](references/WORKFLOWS.md) | Deployment patterns and CI/CD integration |
| [ITERATIVE_REFINEMENT.md](references/ITERATIVE_REFINEMENT.md) | AI collaboration patterns: three-phase approach, critical evaluation, constraint teaching, and validation |

### AI Collaboration Patterns

This skill implements advanced AI collaboration patterns for iterative refinement:

- **Three-Phase Pattern**: Initial request → evaluation → constraint teaching
- **Critical Evaluation**: Infrastructure, team, and operational model questions
- **Domain Constraint Teaching**: Infrastructure, team, and operational constraints
- **Refinement Through Dialogue**: Interactive improvement process
- **Validation Against Requirements**: Functional, security, and operational validation
- **Safety Review**: Security configuration validation

### Practical Guides

| Guide | Description |
|-------|-------------|
| [LIBRARY_GUIDE.md](LIBRARY_GUIDE.md) | Hands-on guide to creating and using library charts with examples |
| [PRACTICAL_AI_GUIDE.md](PRACTICAL_AI_GUIDE.md) | Practical guide to using AI collaboration patterns for iterative refinement |


## Production Best Practices

For production charts, ensure you include:

### Required
- Proper resource limits and requests
- Health checks (readiness and liveness probes)
- Proper labels and annotations

### Recommended
- Security contexts
- PodDisruptionBudgets
- NetworkPolicies
- Image pull policies
- Secrets management
- Autoscaling configuration

### Environment Strategy
- `values.yaml` - Base defaults
- `values-dev.yaml` - Development (debug, minimal resources)
- `values-staging.yaml` - Staging (production-like, lower scale)
- `values-prod.yaml` - Production (full scale, strict policies)

## Common Commands

```bash
# Create chart
helm create mychart

# Lint chart
helm lint mychart

# Template locally (debug)
helm template mychart --debug

# Dry run install
helm install myrelease mychart --dry-run

# Install with values file
helm install myrelease mychart -f values-prod.yaml

# Upgrade release
helm upgrade myrelease mychart -f values-prod.yaml

# Rollback
helm rollback myrelease 1

# Uninstall
helm uninstall myrelease

# Package chart
helm package mychart
```

## Quick Environment Deployment

```bash
# Development
helm install myapp ./mychart -f values-dev.yaml -n dev

# Staging
helm install myapp ./mychart -f values-staging.yaml -n staging

# Production (with safety flags)
helm install myapp ./mychart -f values-prod.yaml -n prod --atomic --wait
```

## Library Charts for Organizational Standards

Library charts provide reusable templates that can be shared across all charts in an organization. They enforce standards and reduce duplication.

### Creating a Library Chart

```yaml
# Chart.yaml
apiVersion: v2
name: org-standards
description: "Reusable templates for organization"
type: library  # Cannot be installed directly
version: 1.0.0
```

```yaml
# templates/_labels.tpl
{{- define "org-standards.labels.common" -}}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/instance: {{ .Release.Name }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version }}
{{- end }}
```

### Using Library Charts

```yaml
# Application Chart.yaml
dependencies:
  - name: org-standards
    version: "^1.0.0"
    repository: "oci://registry.company.com/helm-charts"
```

```yaml
# Application templates/deployment.yaml
metadata:
  labels:
    {{- include "org-standards.labels.common" . | nindent 4 }}
```

### Common Library Templates

- **Labels**: Standard Kubernetes labels, cost attribution
- **Annotations**: Monitoring (Prometheus), logging (Fluentd), tracing (Jaeger)
- **Security Contexts**: Pod and container security (SOC2, PCI-DSS compliance)
- **Probes**: HTTP, TCP, exec health checks
- **Resources**: Standardized resource presets (micro, small, medium, large, xlarge)
- **Affinity**: Pod anti-affinity, node affinity, zone spreading
- **Tolerations**: Spot instances, GPU nodes

See [LIBRARY_GUIDE.md](LIBRARY_GUIDE.md) for comprehensive examples and [references/LIBRARY.md](references/LIBRARY.md) for complete reference.
