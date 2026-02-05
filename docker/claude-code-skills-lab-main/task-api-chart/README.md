# Task API Helm Chart

Helm chart for deploying the Task API application to Kubernetes with environment-specific configurations.

## Features

- ✅ **Environment-specific values** (dev, staging, prod)
- ✅ **Schema validation** via values.schema.json
- ✅ **Helper templates** for consistent naming and labels
- ✅ **Horizontal pod autoscaling** support
- ✅ **Ingress** configuration with TLS
- ✅ **Health checks** (liveness and readiness probes)
- ✅ **Security contexts** and best practices
- ✅ **Resource management** with requests and limits

## Quick Start

### Install Development

```bash
helm install task-api . -f values-dev.yaml -n dev --create-namespace
```

### Install Staging

```bash
helm install task-api . -f values-staging.yaml -n staging --create-namespace --wait
```

### Install Production

```bash
helm install task-api . -f values-prod.yaml -n prod --create-namespace --atomic --wait
```

## Chart Structure

```
task-api-chart/
├── Chart.yaml              # Chart metadata
├── values.yaml             # Default values (base configuration)
├── values.schema.json      # Schema validation
├── values-dev.yaml         # Development overrides
├── values-staging.yaml     # Staging overrides
├── values-prod.yaml        # Production overrides
├── templates/
│   ├── _helpers.tpl        # Helper templates
│   ├── deployment.yaml     # Deployment manifest
│   ├── service.yaml        # Service manifest
│   ├── ingress.yaml        # Ingress manifest
│   ├── serviceaccount.yaml # ServiceAccount
│   ├── hpa.yaml           # HorizontalPodAutoscaler
│   └── NOTES.txt          # Post-install notes
├── HELPERS_USAGE.md       # Helper templates guide
└── VALUES_COMPARISON.md   # Environment comparison
```

## Configuration

### Values Files Hierarchy

Values are merged in this order (later overrides earlier):

1. `values.yaml` - Base defaults
2. `values-{env}.yaml` - Environment-specific overrides (`-f` flag)
3. `--set` command-line overrides - Highest priority

Example:
```bash
helm install task-api . \
  -f values-prod.yaml \        # Override base with prod values
  --set replicaCount=10 \      # Override prod replicaCount
  --set image.tag=v2.0.0       # Override prod image.tag
```

### Environment Comparison

| Setting | Development | Staging | Production |
|---------|------------|---------|------------|
| Replicas | 1 | 2 | 5 (HPA: 3-20) |
| Image Tag | `latest` | `latest` | `v1.0.0` (pinned) |
| CPU Limit | 250m | 500m | 1000m |
| Memory Limit | 256Mi | 512Mi | 1Gi |
| Log Level | DEBUG | INFO | WARN |
| Autoscaling | ❌ | ❌ | ✅ |
| Health Checks | ❌ | ✅ | ✅ Strict |
| Ingress | ❌ | ✅ | ✅ + TLS |
| Security | Minimal | Standard | Strict |

See [VALUES_COMPARISON.md](VALUES_COMPARISON.md) for detailed comparison.

## Common Operations

### Validation

```bash
# Lint the chart
helm lint .

# Lint with specific values
helm lint . -f values-prod.yaml

# Validate schema
helm template task-api . -f values-prod.yaml --validate
```

### Template Rendering

```bash
# Render all templates locally
helm template task-api .

# Render with specific values
helm template task-api . -f values-prod.yaml

# Render specific template
helm template task-api . --show-only templates/deployment.yaml

# Debug rendering
helm template task-api . -f values-prod.yaml --debug
```

### Installation

```bash
# Install with default values
helm install task-api .

# Install with environment-specific values
helm install task-api . -f values-prod.yaml -n prod

# Install with dry-run
helm install task-api . -f values-prod.yaml --dry-run

# Install with atomic rollback on failure
helm install task-api . -f values-prod.yaml --atomic --wait --timeout 10m
```

### Upgrades

```bash
# Upgrade existing release
helm upgrade task-api . -f values-prod.yaml

# Upgrade with specific image version
helm upgrade task-api . -f values-prod.yaml --set image.tag=v2.0.0

# Upgrade with atomic rollback on failure
helm upgrade task-api . -f values-prod.yaml --atomic --wait

# Upgrade with history tracking
helm upgrade task-api . -f values-prod.yaml --description "Release v2.0.0"
```

### Rollback

```bash
# List release history
helm history task-api -n prod

# Rollback to previous version
helm rollback task-api -n prod

# Rollback to specific revision
helm rollback task-api 3 -n prod

# Rollback with wait
helm rollback task-api -n prod --wait
```

### Inspection

```bash
# List all releases
helm list -A

# Show release values
helm get values task-api -n prod

# Show all values (including defaults)
helm get values task-api -n prod --all

# Show rendered manifests
helm get manifest task-api -n prod

# Show release notes
helm get notes task-api -n prod

# Show release status
helm status task-api -n prod
```

### Uninstallation

```bash
# Uninstall release
helm uninstall task-api -n prod

# Uninstall with keeping history
helm uninstall task-api -n prod --keep-history
```

## Customization

### Override Single Values

```bash
# Override replica count
helm install task-api . --set replicaCount=5

# Override image
helm install task-api . \
  --set image.repository=myregistry/task-api \
  --set image.tag=v2.0.0

# Override multiple values
helm install task-api . \
  --set replicaCount=10 \
  --set resources.limits.cpu=2000m \
  --set resources.limits.memory=2Gi
```

### Using Custom Values Files

```bash
# Create custom values file
cat > my-values.yaml <<EOF
replicaCount: 7
image:
  tag: "v1.5.0"
ingress:
  enabled: true
  hosts:
    - host: my-custom-domain.com
      paths:
        - path: /
          pathType: Prefix
EOF

# Use custom values
helm install task-api . -f my-values.yaml

# Combine multiple values files
helm install task-api . \
  -f values.yaml \
  -f values-prod.yaml \
  -f my-values.yaml
```

## Helper Templates

The chart includes reusable helper templates in `templates/_helpers.tpl`:

- `task-api-chart.name` - Chart name
- `task-api-chart.fullname` - Full resource name
- `task-api-chart.labels` - Common labels
- `task-api-chart.selectorLabels` - Selector labels
- `task-api-chart.image` - Full image string
- `task-api-chart.resourceName` - Resource name with suffix
- `task-api-chart.replicas` - Environment-based replicas

See [HELPERS_USAGE.md](HELPERS_USAGE.md) for detailed usage.

## Schema Validation

The chart includes `values.schema.json` that automatically validates:

- ✅ Required fields (image.repository, service)
- ✅ Value types (strings, integers, booleans)
- ✅ Valid ranges (ports 1-65535, replicas 1-100)
- ✅ Enum constraints (pullPolicy, service.type, etc.)
- ✅ Pattern validation (image tags, env var names)

Validation happens automatically during:
- `helm lint`
- `helm install`
- `helm upgrade`
- `helm template --validate`

## Best Practices

### Development
- ✅ Use `latest` tag for rapid iteration
- ✅ Disable health checks for faster startup
- ✅ Minimal resources for cost efficiency
- ✅ Verbose logging (DEBUG) for troubleshooting

### Staging
- ✅ Mirror production configuration
- ✅ Test with production-like scale
- ✅ Enable monitoring and observability
- ✅ Validate upgrade procedures

### Production
- ✅ **Always pin image versions** (never use `latest`)
- ✅ Use `--atomic` flag for safe rollbacks
- ✅ Enable autoscaling for variable load
- ✅ Strict security contexts
- ✅ Enable health checks with appropriate timeouts
- ✅ Use anti-affinity for high availability
- ✅ Monitor deployments closely

## Troubleshooting

### Chart Issues

```bash
# Check chart syntax
helm lint .

# Debug template rendering
helm template task-api . --debug

# Validate against Kubernetes API
helm template task-api . | kubectl apply --dry-run=client -f -
```

### Deployment Issues

```bash
# Check pod status
kubectl get pods -n prod -l app.kubernetes.io/name=task-api

# View pod logs
kubectl logs -n prod -l app.kubernetes.io/name=task-api

# Describe deployment
kubectl describe deployment -n prod task-api

# Check events
kubectl get events -n prod --sort-by='.lastTimestamp'
```

### Values Issues

```bash
# Show actual values used
helm get values task-api -n prod

# Show all values including defaults
helm get values task-api -n prod --all

# Compare environments
diff <(helm get values task-api -n staging) <(helm get values task-api -n prod)
```

## Documentation

- [HELPERS_USAGE.md](HELPERS_USAGE.md) - Helper template patterns and usage
- [VALUES_COMPARISON.md](VALUES_COMPARISON.md) - Environment configuration comparison
- [Helm Chart Skill](../.claude/skills/helm-chart-skill/SKILL.md) - Complete Helm chart guide

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Deploy to Kubernetes

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install Helm
        uses: azure/setup-helm@v3

      - name: Lint Chart
        run: helm lint ./task-api-chart -f values-prod.yaml

      - name: Deploy to Production
        run: |
          helm upgrade --install task-api ./task-api-chart \
            -f values-prod.yaml \
            --set image.tag=${{ github.sha }} \
            --namespace prod \
            --atomic --wait --timeout 10m
```

## Support

For issues or questions:
1. Validate your values with `helm lint`
2. Check schema validation errors
3. Review template rendering with `helm template --debug`
4. Consult the documentation in this repository

## Version

- **Chart Version**: 0.1.0
- **App Version**: 1.0.0

## License

See parent repository for license information.
