# org-standards Library Chart

A Helm library chart providing reusable templates and organizational standards for Kubernetes deployments.

## Overview

This library chart provides standardized templates for:
- **Labels**: Common, selector, cost attribution labels
- **Annotations**: Monitoring, logging, tracing, security annotations
- **Security**: Pod and container security contexts (restricted, baseline, compliance)
- **Probes**: HTTP, TCP, exec, gRPC health checks
- **Resources**: Standardized resource presets (micro to xxlarge)
- **Affinity**: Pod anti-affinity, node affinity, zone spreading
- **Tolerations**: Spot instances, GPU nodes

## Installation

This is a **library chart** and cannot be installed directly. Include it as a dependency in your application chart.

### Add as Dependency

In your application chart's `Chart.yaml`:

```yaml
dependencies:
  - name: org-standards
    version: "^1.0.0"
    repository: "oci://registry.company.com/helm-charts"
```

Then update dependencies:

```bash
helm dependency update ./my-app
```

## Usage Examples

### Labels

```yaml
# templates/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Release.Name }}
  labels:
    {{- include "org-standards.labels.common" . | nindent 4 }}
    {{- include "org-standards.labels.cost" . | nindent 4 }}
```

### Security Context

```yaml
# templates/deployment.yaml
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

### Health Probes

```yaml
# templates/deployment.yaml
containers:
  - name: app
    livenessProbe:
      {{- include "org-standards.probes.http" (dict "path" "/health" "port" 8080 "context" .) | nindent 12 }}
    readinessProbe:
      {{- include "org-standards.probes.http" (dict "path" "/ready" "port" 8080 "context" .) | nindent 12 }}
```

### Resources

```yaml
# templates/deployment.yaml
containers:
  - name: app
    resources:
      {{- include "org-standards.resources" (dict "size" "medium" "context" .) | nindent 12 }}
```

## Available Templates

### Labels (_labels.tpl)
- `org-standards.labels.common` - Common Kubernetes labels
- `org-standards.labels.selector` - Selector labels (immutable)
- `org-standards.labels.cost` - Cost attribution labels
- `org-standards.labels.recommended` - All recommended labels
- `org-standards.labels.full` - Complete label set

### Annotations (_annotations.tpl)
- `org-standards.annotations.monitoring` - Prometheus configuration
- `org-standards.annotations.logging` - Fluentd/logging configuration
- `org-standards.annotations.tracing` - Jaeger tracing configuration
- `org-standards.annotations.datadog` - Datadog APM configuration
- `org-standards.annotations.observability` - Complete observability stack
- `org-standards.annotations.security` - Security scanning annotations
- `org-standards.annotations.full` - All standard annotations

### Security (_security.tpl)
- `org-standards.securityContext.pod` - Pod-level security context
- `org-standards.securityContext.container` - Container-level security context
- `org-standards.securityContext.restricted` - Kubernetes restricted standard
- `org-standards.securityContext.baseline` - Kubernetes baseline standard
- `org-standards.securityContext.pciDSS` - PCI-DSS compliant context
- `org-standards.securityContext.soc2` - SOC2 compliant context
- `org-standards.securityContext.readOnlyRoot` - Read-only root filesystem

### Probes (_probes.tpl)
- `org-standards.probes.http` - HTTP GET probe
- `org-standards.probes.tcp` - TCP socket probe
- `org-standards.probes.exec` - Exec command probe
- `org-standards.probes.grpc` - gRPC probe (K8s 1.24+)
- `org-standards.probes.startup` - Startup probe for slow apps
- `org-standards.probes.default` - Default HTTP liveness + readiness

### Resources (_resources.tpl)
- `org-standards.resources` - Standard resource presets (micro to xxlarge)
- `org-standards.resources.burstable` - Burstable QoS (requests < limits)
- `org-standards.resources.guaranteed` - Guaranteed QoS (requests == limits)
- `org-standards.resources.minimal` - Minimal resources for sidecars
- `org-standards.resources.gpu` - GPU-enabled resources
- `org-standards.resources.spot` - Optimized for spot instances

### Affinity (_affinity.tpl)
- `org-standards.affinity.podAntiAffinity` - Spread pods across nodes
- `org-standards.affinity.nodeAffinity` - Schedule to specific node pools
- `org-standards.affinity.zoneSpread` - Spread across availability zones
- `org-standards.tolerations.spot` - Tolerate spot instances
- `org-standards.tolerations.gpu` - Tolerate GPU nodes
- `org-standards.tolerations.custom` - Custom tolerations from values

## Configuration

Configure library templates through your application's `values.yaml`:

```yaml
# Cost attribution (required for production)
cost:
  center: "engineering"
  businessUnit: "product"
  spotEligible: false

# Security configuration
security:
  runAsUser: 1000
  runAsGroup: 1000
  fsGroup: 1000
  capabilities: []

# Resource configuration
resources:
  size: medium  # micro, small, medium, large, xlarge, xxlarge

# Probe configuration
probes:
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3

# Observability
metrics:
  enabled: true
  port: 8080
  path: /metrics

tracing:
  enabled: true
  jaeger: true

# Environment
environment: production  # dev, staging, production

# Common labels and annotations
commonLabels:
  team: backend
  project: api-gateway

commonAnnotations:
  description: "My application"
```

## Compliance

This library includes templates for compliance standards:

- **SOC2**: `org-standards.securityContext.soc2`
- **PCI-DSS**: `org-standards.securityContext.pciDSS`
- **CIS Kubernetes Benchmark**: Implemented in security contexts
- **Kubernetes Pod Security Standards**: `restricted` and `baseline` profiles

## Versioning

This library follows [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes to template names or parameters
- **MINOR**: New templates or parameters (backward compatible)
- **PATCH**: Bug fixes or documentation updates

## Examples

See [example-app-chart](../example-app-chart/) for a complete application chart using this library.

## Support

For issues or questions:
- GitHub: https://github.com/company/helm-charts/issues
- Email: platform@company.com
- Slack: #platform-engineering

## License

Copyright (c) 2024 Company Name. All rights reserved.
