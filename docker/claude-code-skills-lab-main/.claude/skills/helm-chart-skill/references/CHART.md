# Chart.yaml Reference

The `Chart.yaml` file contains metadata about your Helm chart. This is a required file for every chart.

## Complete Chart.yaml Structure

```yaml
# Required Fields
apiVersion: v2                    # Helm 3 uses v2, Helm 2 uses v1
name: my-application              # Chart name (lowercase, hyphen-separated)
version: 1.0.0                    # Chart version (SemVer 2)

# Recommended Fields
description: "A Helm chart for deploying My Application on Kubernetes"
type: application                 # 'application' or 'library'
appVersion: "2.0.0"              # Version of the app being deployed

# Optional Metadata
keywords:
  - web
  - api
  - microservice
home: https://example.com/my-application
sources:
  - https://github.com/myorg/my-application
icon: https://example.com/icon.png

# Maintainers
maintainers:
  - name: "John Doe"
    email: "john.doe@example.com"
    url: "https://johndoe.dev"
  - name: "Jane Smith"
    email: "jane.smith@example.com"

# Annotations (custom metadata)
annotations:
  category: "Web Application"
  artifacthub.io/license: "Apache-2.0"
  artifacthub.io/links: |
    - name: Documentation
      url: https://docs.example.com

# Dependencies (optional)
dependencies:
  - name: postgresql
    version: "12.x.x"
    repository: "https://charts.bitnami.com/bitnami"
    condition: postgresql.enabled
  - name: redis
    version: "17.x.x"
    repository: "https://charts.bitnami.com/bitnami"
    condition: redis.enabled

# Kubernetes Version Constraint (optional)
kubeVersion: ">=1.23.0-0"

# Deprecation (optional)
deprecated: false
```

## Field Reference

### Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `apiVersion` | Chart API version. Use `v2` for Helm 3 | `v2` |
| `name` | Chart name (lowercase, hyphens allowed) | `my-app` |
| `version` | Chart version following SemVer 2 | `1.2.3` |

### Recommended Fields

| Field | Description | Example |
|-------|-------------|---------|
| `description` | Single-sentence description | `"A web application chart"` |
| `type` | Chart type: `application` or `library` | `application` |
| `appVersion` | Version of contained application | `"2.0.0"` |

### Optional Fields

| Field | Description | Example |
|-------|-------------|---------|
| `keywords` | List of keywords for searching | `[web, api]` |
| `home` | Project homepage URL | `https://example.com` |
| `sources` | List of source code URLs | `[https://github.com/...]` |
| `icon` | URL to chart icon (SVG or PNG) | `https://.../icon.png` |
| `maintainers` | List of maintainers | See example above |
| `annotations` | Custom key-value metadata | See example above |
| `kubeVersion` | Kubernetes version constraint | `>=1.23.0-0` |
| `deprecated` | Mark chart as deprecated | `true` or `false` |

## Chart Types

### Application Charts (Default)
```yaml
type: application
```
- Can be deployed to a cluster
- Contains templates that create Kubernetes resources
- Most common chart type

### Library Charts
```yaml
type: library
```
- Cannot be deployed directly
- Provides utilities and helper templates
- Included as dependencies by other charts
- No `templates/` directory (only `_helpers.tpl`)

## Version Fields Explained

### `version` (Chart Version)
- Version of the chart itself
- Must follow [Semantic Versioning 2.0.0](https://semver.org/)
- Increment when chart templates/values change
- Format: `MAJOR.MINOR.PATCH` (e.g., `1.2.3`)
- Pre-release: `1.2.3-alpha.1`, `1.2.3-beta.2`

### `appVersion` (Application Version)
- Version of the application being deployed
- Does NOT need to follow SemVer
- Informational only (not used by Helm)
- Examples: `"2.0.0"`, `"latest"`, `"v2023.01"`

## Examples by Use Case

### Minimal Chart.yaml
```yaml
apiVersion: v2
name: hello-world
version: 0.1.0
```

### Web Application
```yaml
apiVersion: v2
name: web-api
description: "REST API service with database connectivity"
type: application
version: 1.0.0
appVersion: "2.5.0"
keywords:
  - api
  - rest
  - fastapi
maintainers:
  - name: "Platform Team"
    email: "platform@company.com"
```

### Microservice with Dependencies
```yaml
apiVersion: v2
name: order-service
description: "Order processing microservice"
type: application
version: 2.1.0
appVersion: "3.0.0"
kubeVersion: ">=1.25.0-0"

dependencies:
  - name: postgresql
    version: "12.6.x"
    repository: "https://charts.bitnami.com/bitnami"
    condition: postgresql.enabled
  - name: rabbitmq
    version: "11.x.x"
    repository: "https://charts.bitnami.com/bitnami"
    condition: rabbitmq.enabled
```

### Library Chart
```yaml
apiVersion: v2
name: common-templates
description: "Shared template library for organization charts"
type: library
version: 1.0.0
```

## Best Practices

1. **Always use apiVersion v2** for Helm 3 compatibility
2. **Use lowercase names** with hyphens (not underscores)
3. **Follow SemVer strictly** for chart versions
4. **Quote appVersion** to ensure string interpretation
5. **Include maintainers** for production charts
6. **Add keywords** for discoverability
7. **Pin dependency versions** to avoid surprises
8. **Use kubeVersion** to ensure cluster compatibility

## Validation

Validate your Chart.yaml:
```bash
# Lint the chart (includes Chart.yaml validation)
helm lint ./my-chart

# Show chart info
helm show chart ./my-chart
```
