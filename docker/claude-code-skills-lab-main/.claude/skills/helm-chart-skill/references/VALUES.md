# Helm Values Configuration Best Practices

## Complete values.yaml Structure

A well-structured `values.yaml` should organize configuration logically:

```yaml
# =============================================================================
# APPLICATION SETTINGS
# =============================================================================

# Replica count (ignored if autoscaling is enabled)
replicaCount: 3

# Container image configuration
image:
  repository: your-registry/your-app
  pullPolicy: IfNotPresent
  tag: ""  # Defaults to Chart.appVersion

# Image pull secrets for private registries
imagePullSecrets: []
  # - name: regcred

# Override chart name
nameOverride: ""
fullnameOverride: ""

# =============================================================================
# SERVICE ACCOUNT
# =============================================================================

serviceAccount:
  create: true
  automount: true
  annotations: {}
  name: ""

# =============================================================================
# POD CONFIGURATION
# =============================================================================

podAnnotations: {}
podLabels: {}

podSecurityContext: {}
  # fsGroup: 2000

securityContext: {}
  # capabilities:
  #   drop:
  #     - ALL
  # readOnlyRootFilesystem: true
  # runAsNonRoot: true
  # runAsUser: 1000

# =============================================================================
# SERVICE CONFIGURATION
# =============================================================================

service:
  type: ClusterIP
  port: 80
  targetPort: 8080
  # nodePort: 30080  # Only for NodePort type
  annotations: {}

# =============================================================================
# INGRESS CONFIGURATION
# =============================================================================

ingress:
  enabled: false
  className: ""
  annotations: {}
    # kubernetes.io/ingress.class: nginx
    # cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: chart-example.local
      paths:
        - path: /
          pathType: ImplementationSpecific
  tls: []
    # - secretName: chart-example-tls
    #   hosts:
    #     - chart-example.local

# =============================================================================
# RESOURCE MANAGEMENT
# =============================================================================

resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 100m
    memory: 128Mi

# =============================================================================
# HEALTH CHECKS
# =============================================================================

livenessProbe:
  httpGet:
    path: /health
    port: http
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /ready
    port: http
  initialDelaySeconds: 5
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 3

# =============================================================================
# AUTOSCALING
# =============================================================================

autoscaling:
  enabled: false
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 80
  targetMemoryUtilizationPercentage: 80

# =============================================================================
# ENVIRONMENT VARIABLES
# =============================================================================

# Direct environment variables
env:
  - name: LOG_LEVEL
    value: "INFO"
  - name: APP_ENV
    value: "production"

# Environment from ConfigMap/Secret references
envFrom: []
  # - configMapRef:
  #     name: app-config
  # - secretRef:
  #     name: app-secrets

# ConfigMap data (creates ConfigMap if defined)
config: {}
  # DATABASE_HOST: "localhost"
  # DATABASE_PORT: "5432"

# Secret data (creates Secret if defined)
secrets: {}
  # DATABASE_PASSWORD: "secret123"

# =============================================================================
# STORAGE
# =============================================================================

volumes: []
  # - name: data
  #   persistentVolumeClaim:
  #     claimName: my-pvc

volumeMounts: []
  # - name: data
  #   mountPath: /data

# =============================================================================
# SCHEDULING
# =============================================================================

nodeSelector: {}

tolerations: []

affinity: {}
```

---

## Environment-Specific Values Files

### values-dev.yaml (Development)

```yaml
# Development Environment
# Usage: helm install myapp . -f values-dev.yaml

replicaCount: 1

image:
  tag: "latest"
  pullPolicy: Always

resources:
  limits:
    cpu: 250m
    memory: 256Mi
  requests:
    cpu: 50m
    memory: 64Mi

# Disable health checks for faster iteration
livenessProbe: {}
readinessProbe: {}

autoscaling:
  enabled: false

env:
  - name: LOG_LEVEL
    value: "DEBUG"
  - name: APP_ENV
    value: "development"

config:
  DATABASE_HOST: "localhost"
  DATABASE_PORT: "5432"
  DATABASE_NAME: "myapp_dev"
  CACHE_ENABLED: "false"
```

### values-staging.yaml (Staging)

```yaml
# Staging Environment
# Usage: helm install myapp . -f values-staging.yaml

replicaCount: 2

image:
  tag: "latest"
  pullPolicy: Always

resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 100m
    memory: 128Mi

livenessProbe:
  httpGet:
    path: /health
    port: http
  initialDelaySeconds: 15
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /ready
    port: http
  initialDelaySeconds: 5
  periodSeconds: 5

autoscaling:
  enabled: false

env:
  - name: LOG_LEVEL
    value: "INFO"
  - name: APP_ENV
    value: "staging"

config:
  DATABASE_HOST: "staging-db.internal"
  DATABASE_PORT: "5432"
  DATABASE_NAME: "myapp_staging"
  CACHE_ENABLED: "true"
```

### values-prod.yaml (Production)

```yaml
# Production Environment
# Usage: helm install myapp . -f values-prod.yaml

replicaCount: 5

image:
  tag: "v1.0.0"  # Always pin to specific version in production
  pullPolicy: IfNotPresent

resources:
  limits:
    cpu: 1000m
    memory: 1Gi
  requests:
    cpu: 500m
    memory: 512Mi

livenessProbe:
  httpGet:
    path: /health
    port: http
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /ready
    port: http
  initialDelaySeconds: 10
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 3

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 20
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80

env:
  - name: LOG_LEVEL
    value: "WARN"
  - name: APP_ENV
    value: "production"

config:
  DATABASE_HOST: "prod-db.internal"
  DATABASE_PORT: "5432"
  DATABASE_NAME: "myapp_prod"
  CACHE_ENABLED: "true"
  CACHE_TTL: "3600"

# Pod disruption budget
podDisruptionBudget:
  enabled: true
  minAvailable: 2

# Affinity for high availability
affinity:
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        podAffinityTerm:
          labelSelector:
            matchExpressions:
              - key: app.kubernetes.io/name
                operator: In
                values:
                  - myapp
          topologyKey: kubernetes.io/hostname
```

---

## Environment Comparison Table

| Setting | Dev | Staging | Prod |
|---------|-----|---------|------|
| `replicaCount` | 1 | 2 | 5 |
| `image.tag` | latest | latest | v1.0.0 (pinned) |
| `resources.limits.cpu` | 250m | 500m | 1000m |
| `resources.limits.memory` | 256Mi | 512Mi | 1Gi |
| `LOG_LEVEL` | DEBUG | INFO | WARN |
| `autoscaling.enabled` | false | false | true |
| Health checks | disabled | enabled | enabled (strict) |

---

## Deployment Commands

```bash
# Development
helm install myapp ./mychart -f values-dev.yaml --namespace dev

# Staging
helm install myapp ./mychart -f values-staging.yaml --namespace staging

# Production (with atomic for safety)
helm install myapp ./mychart -f values-prod.yaml --namespace prod --atomic --wait

# Override specific values at deploy time
helm install myapp ./mychart \
  -f values-prod.yaml \
  --set image.tag="v1.2.3" \
  --set replicaCount=10
```

---

## Naming Conventions

- Use lowercase with hyphens for compound names (e.g., `my-service`)
- Group related values under common prefixes (e.g., `database.host`, `database.port`)
- Use consistent naming patterns across charts

## Value Types

### Strings
Always quote string values that might contain special characters:
```yaml
config:
  connectionString: "server=localhost;port=5432"
```

### Numbers
```yaml
port: 8080
replicaCount: 3
```

### Booleans
```yaml
enabled: true
debug: false
```

### Lists
```yaml
allowedHosts:
  - "example.com"
  - "www.example.com"
```

## Validation Tips

1. Always provide sensible defaults
2. Use `required` function in templates for mandatory values
3. Validate ranges for numeric values
4. Use consistent structure across environments
5. Document values with comments
6. Test with various combinations of values
