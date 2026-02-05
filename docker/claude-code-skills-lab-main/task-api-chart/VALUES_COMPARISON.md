# Environment Values Comparison

Quick reference comparing configuration across development, staging, and production environments.

## Environment Characteristics

### Development
- **Purpose**: Local development and testing
- **Priority**: Fast iteration, debugging, ease of use
- **Scale**: Minimal (cost-efficient)
- **Security**: Relaxed for development ease

### Staging
- **Purpose**: Pre-production testing and validation
- **Priority**: Production-like behavior, cost-effective
- **Scale**: Medium (representative workload)
- **Security**: Production-like policies

### Production
- **Purpose**: Live user traffic
- **Priority**: Reliability, performance, security
- **Scale**: High availability, autoscaling
- **Security**: Strict hardening, compliance

## Configuration Comparison

| Setting | Development | Staging | Production |
|---------|------------|---------|------------|
| **Environment Identifier** | `development` | `staging` | `production` |
| **Replicas** | 1 | 2 | 5 (with HPA) |
| **Image Tag** | `latest` | `latest` | `v1.0.0` (pinned) |
| **Image Pull Policy** | Always | Always | IfNotPresent |
| **CPU Limit** | 250m | 500m | 1000m |
| **Memory Limit** | 256Mi | 512Mi | 1Gi |
| **CPU Request** | 100m | 250m | 500m |
| **Memory Request** | 128Mi | 256Mi | 512Mi |
| **LOG_LEVEL** | DEBUG | INFO | WARN |
| **API_TIMEOUT** | 60s | 30s | 30s |
| **Autoscaling** | Disabled | Disabled | Enabled (3-20) |
| **Health Checks** | Disabled | Enabled | Strict |
| **Ingress** | Disabled | Enabled | Enabled + TLS |
| **Security Context** | Minimal | Standard | Strict |
| **Read-Only Filesystem** | No | No | Yes |
| **CORS** | Enabled | Enabled | Configured |
| **Metrics** | Disabled | Enabled | Enabled |
| **Tracing** | Disabled | Enabled | Enabled |
| **Cache** | Disabled | Enabled (5min) | Enabled (10min) |
| **Pod Annotations** | Basic | + Prometheus | + Full observability |
| **Affinity Rules** | None | Basic | Strong anti-affinity |
| **Node Selector** | None | Optional | Production nodes |
| **TLS/SSL** | No | Staging cert | Production cert |

## Resource Progression

```text
Development:
  - Cost: $
  - CPU: ████ (250m)
  - Mem: ████ (256Mi)
  - Replicas: 1

Staging:
  - Cost: $$
  - CPU: ████████ (500m)
  - Mem: ████████ (512Mi)
  - Replicas: 2

Production:
  - Cost: $$$$
  - CPU: ████████████████ (1000m)
  - Mem: ████████████████ (1Gi)
  - Replicas: 5-20 (autoscaled)
```

## Deployment Commands

```bash
# Development - Fast and simple
helm install task-api ./task-api-chart \
  -f values-dev.yaml \
  --namespace dev \
  --create-namespace

# Staging - Production-like testing
helm install task-api ./task-api-chart \
  -f values-staging.yaml \
  --namespace staging \
  --create-namespace \
  --wait --timeout 5m

# Production - Safe and atomic
helm install task-api ./task-api-chart \
  -f values-prod.yaml \
  --namespace prod \
  --create-namespace \
  --atomic --wait --timeout 10m
```

## Upgrade Commands

```bash
# Development - Quick upgrade
helm upgrade task-api ./task-api-chart \
  -f values-dev.yaml \
  --namespace dev

# Staging - Validation before prod
helm upgrade task-api ./task-api-chart \
  -f values-staging.yaml \
  --namespace staging \
  --wait

# Production - Safe upgrade with rollback
helm upgrade task-api ./task-api-chart \
  -f values-prod.yaml \
  --namespace prod \
  --atomic --wait --timeout 10m \
  --description "Release v1.2.3"
```

## Override Examples

### Development with Local Image

```bash
helm upgrade task-api ./task-api-chart \
  -f values-dev.yaml \
  --set image.repository=localhost:5000/task-api \
  --set image.tag=dev-$(git rev-parse --short HEAD) \
  --namespace dev
```

### Staging with Specific Version

```bash
helm upgrade task-api ./task-api-chart \
  -f values-staging.yaml \
  --set image.tag=v1.2.3-rc1 \
  --namespace staging
```

### Production with Scaled Replicas

```bash
helm upgrade task-api ./task-api-chart \
  -f values-prod.yaml \
  --set replicaCount=10 \
  --set autoscaling.maxReplicas=30 \
  --namespace prod --atomic
```

## Values Merge Example

Given these files, here's how values merge:

**Base (values.yaml):**
```yaml
replicaCount: 3
image:
  repository: task-api
  tag: "1.0.0"
  pullPolicy: IfNotPresent
resources:
  limits:
    cpu: 500m
    memory: 512Mi
```

**Override (values-prod.yaml):**
```yaml
replicaCount: 5
image:
  tag: "v1.0.0"
resources:
  limits:
    memory: 1Gi
```

**Command:**
```bash
helm install task-api ./task-api-chart \
  -f values-prod.yaml \
  --set replicaCount=10
```

**Final Result (merged):**
```yaml
replicaCount: 10              # From --set (highest priority)
image:
  repository: task-api        # From values.yaml
  tag: "v1.0.0"              # From values-prod.yaml
  pullPolicy: IfNotPresent   # From values.yaml
resources:
  limits:
    cpu: 500m               # From values.yaml
    memory: 1Gi             # From values-prod.yaml
```

## Validation

Validate each environment before deployment:

```bash
# Validate development values
helm lint ./task-api-chart -f values-dev.yaml

# Validate staging values
helm lint ./task-api-chart -f values-staging.yaml

# Validate production values
helm lint ./task-api-chart -f values-prod.yaml

# Test rendering without installation
helm template task-api ./task-api-chart -f values-prod.yaml --debug
```

## Schema Validation

The `values.schema.json` automatically validates:

### ✅ Valid Configuration

```yaml
replicaCount: 5  # Integer between 1-100
image:
  repository: "myapp"  # Required, non-empty string
  pullPolicy: "Always"  # Valid enum value
service:
  type: "ClusterIP"  # Valid enum
  port: 8000  # Valid port range
```

### ❌ Invalid Configuration

```yaml
replicaCount: "5"  # ERROR: Should be integer, not string
image:
  # ERROR: Missing required 'repository' field
  pullPolicy: "AlwaysPull"  # ERROR: Invalid enum value
service:
  type: "LoadBalanced"  # ERROR: Invalid enum value
  port: 70000  # ERROR: Port out of range (1-65535)
```

## Best Practices

1. **Development**
   - Use for rapid iteration
   - Don't mirror production complexity
   - Keep it simple and fast

2. **Staging**
   - Mirror production configuration
   - Test with production-like data volumes
   - Validate upgrade procedures
   - Run integration tests

3. **Production**
   - Always pin image versions
   - Use `--atomic` flag for safe rollbacks
   - Monitor deployments closely
   - Have rollback plan ready

4. **All Environments**
   - Validate before deploying
   - Use descriptive release notes
   - Tag deployments in Git
   - Document any manual overrides

## Troubleshooting

### Check Actual Values

```bash
# Show values used by a release
helm get values task-api -n prod

# Show all values (including defaults)
helm get values task-api -n prod --all

# Compare against original
diff <(helm get values task-api -n prod) values-prod.yaml
```

### Debug Rendering

```bash
# Show rendered manifests
helm get manifest task-api -n prod

# Template with debug
helm template task-api ./task-api-chart -f values-prod.yaml --debug
```

### Validation Errors

```bash
# Check schema validation
helm lint ./task-api-chart -f values-prod.yaml

# Detailed validation output
helm template task-api ./task-api-chart \
  -f values-prod.yaml \
  --validate \
  --debug
```
