# Chart Dependencies Guide

This guide explains how to use PostgreSQL and Redis dependencies in the Task API Helm chart.

## Overview

The chart includes optional PostgreSQL and Redis dependencies that can be:
- **Enabled** - Deploy PostgreSQL/Redis as part of the Helm release
- **Disabled** - Use external managed services (AWS RDS, ElastiCache, etc.)

## Dependencies Declaration

See [Chart.yaml](Chart.yaml):

```yaml
dependencies:
  - name: postgresql
    version: "12.12.10"
    repository: "https://charts.bitnami.com/bitnami"
    condition: postgresql.enabled
    tags:
      - database
  - name: redis
    version: "18.4.0"
    repository: "https://charts.bitnami.com/bitnami"
    condition: redis.enabled
    tags:
      - cache
```

## Installation

### Step 1: Add Bitnami Repository

```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
```

### Step 2: Download Dependencies

```bash
# From the chart directory
cd task-api-chart

# Download all dependencies
helm dependency update

# Verify dependencies
helm dependency list
```

Output:
```
NAME        VERSION     REPOSITORY                              STATUS
postgresql  12.12.10    https://charts.bitnami.com/bitnami     ok
redis       18.4.0      https://charts.bitnami.com/bitnami     ok
```

### Step 3: Install with Dependencies

```bash
# Development (with internal PostgreSQL and Redis)
helm install task-api . -f values-dev.yaml -n dev --create-namespace

# Staging (with internal PostgreSQL and Redis)
helm install task-api . -f values-staging.yaml -n staging --create-namespace

# Production (with external services)
helm install task-api . -f values-prod.yaml -n prod --create-namespace
```

## Configuration Patterns

### Pattern 1: Internal Dependencies (Dev/Staging)

Use bundled PostgreSQL and Redis for non-production environments.

**values-dev.yaml:**
```yaml
postgresql:
  enabled: true  # Deploy PostgreSQL
  auth:
    username: taskapi_dev
    password: devpass123
    database: tasks_dev
  primary:
    persistence:
      enabled: false  # No persistence for faster teardown
    resources:
      limits:
        cpu: 250m
        memory: 256Mi

redis:
  enabled: true  # Deploy Redis
  auth:
    enabled: false  # No auth in dev
  master:
    persistence:
      enabled: false
    resources:
      limits:
        cpu: 100m
        memory: 128Mi
```

### Pattern 2: External Services (Production)

Use managed services for production reliability and scaling.

**values-prod.yaml:**
```yaml
postgresql:
  enabled: false  # Don't deploy PostgreSQL

# Configure external database
externalDatabase:
  host: "prod-postgres.cluster-xyz.us-east-1.rds.amazonaws.com"
  port: 5432
  username: "taskapi_prod"
  password: ""  # Set via --set or secret
  database: "tasks_prod"

redis:
  enabled: false  # Don't deploy Redis

# Configure external Redis
externalRedis:
  host: "prod-redis.cluster-xyz.cache.amazonaws.com"
  port: 6379
  password: ""  # Set via --set or secret
```

**Install with credentials:**
```bash
helm install task-api . -f values-prod.yaml \
  --set externalDatabase.password="$DB_PASSWORD" \
  --set externalRedis.password="$REDIS_PASSWORD" \
  --namespace prod
```

## Connection Helpers

The chart provides helper templates that automatically use the correct connection details:

### PostgreSQL Helpers

```yaml
# Get PostgreSQL hostname
{{ include "task-api-chart.postgresql.host" . }}
# Output: myrelease-postgresql (internal) or prod-db.example.com (external)

# Get PostgreSQL port
{{ include "task-api-chart.postgresql.port" . }}
# Output: 5432

# Get PostgreSQL username
{{ include "task-api-chart.postgresql.username" . }}
# Output: taskapi (from values)

# Get PostgreSQL database name
{{ include "task-api-chart.postgresql.database" . }}
# Output: tasks (from values)

# Get full connection URL
{{ include "task-api-chart.postgresql.url" . }}
# Output: postgresql://taskapi@myrelease-postgresql:5432/tasks
```

### Redis Helpers

```yaml
# Get Redis hostname
{{ include "task-api-chart.redis.host" . }}
# Output: myrelease-redis-master (internal) or prod-redis.example.com (external)

# Get Redis port
{{ include "task-api-chart.redis.port" . }}
# Output: 6379

# Get full connection URL
{{ include "task-api-chart.redis.url" . }}
# Output: redis://:$(REDIS_PASSWORD)@myrelease-redis-master:6379/0
```

## Using Connection Helpers in Deployment

Example deployment with environment variables:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "task-api-chart.fullname" . }}
spec:
  template:
    spec:
      containers:
        - name: {{ .Chart.Name }}
          env:
            # PostgreSQL connection
            - name: DATABASE_HOST
              value: {{ include "task-api-chart.postgresql.host" . | quote }}
            - name: DATABASE_PORT
              value: {{ include "task-api-chart.postgresql.port" . | quote }}
            - name: DATABASE_USER
              value: {{ include "task-api-chart.postgresql.username" . | quote }}
            - name: DATABASE_NAME
              value: {{ include "task-api-chart.postgresql.database" . | quote }}
            - name: DATABASE_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: {{ include "task-api-chart.postgresql.secretName" . }}
                  key: {{ include "task-api-chart.postgresql.secretKey" . }}

            # Or use full connection URL
            - name: DATABASE_URL
              value: {{ include "task-api-chart.postgresql.url" . | quote }}

            # Redis connection
            - name: REDIS_HOST
              value: {{ include "task-api-chart.redis.host" . | quote }}
            - name: REDIS_PORT
              value: {{ include "task-api-chart.redis.port" . | quote }}
            {{- if .Values.redis.auth.enabled }}
            - name: REDIS_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: {{ include "task-api-chart.redis.secretName" . }}
                  key: {{ include "task-api-chart.redis.secretKey" . }}
            {{- end }}

            # Or use full connection URL
            - name: REDIS_URL
              value: {{ include "task-api-chart.redis.url" . | quote }}
```

## Environment-Specific Configuration

### Development
- **PostgreSQL**: Internal, no persistence, minimal resources
- **Redis**: Internal, no auth, no persistence, minimal resources
- **Use case**: Fast iteration, easy teardown

### Staging
- **PostgreSQL**: Internal, with persistence, moderate resources
- **Redis**: Internal, with auth, no persistence
- **Use case**: Production-like testing, cost-effective

### Production
- **PostgreSQL**: External managed service (RDS, Cloud SQL, etc.)
- **Redis**: External managed service (ElastiCache, Memorystore, etc.)
- **Use case**: High availability, managed backups, automatic failover

## Advanced Configuration

### Custom PostgreSQL Configuration

```yaml
postgresql:
  enabled: true
  auth:
    username: myapp
    password: mypass
    database: mydb
    postgresPassword: adminpass
  primary:
    persistence:
      enabled: true
      size: 20Gi
      storageClass: "fast-ssd"
    resources:
      limits:
        cpu: 2000m
        memory: 2Gi
      requests:
        cpu: 1000m
        memory: 1Gi
    initdb:
      scripts:
        init.sql: |
          CREATE EXTENSION IF NOT EXISTS pg_trgm;
          CREATE EXTENSION IF NOT EXISTS btree_gist;
  metrics:
    enabled: true
    serviceMonitor:
      enabled: true
```

### Custom Redis Configuration

```yaml
redis:
  enabled: true
  auth:
    enabled: true
    password: myredispass
  master:
    persistence:
      enabled: true
      size: 8Gi
    resources:
      limits:
        cpu: 1000m
        memory: 1Gi
  replica:
    replicaCount: 3
    persistence:
      enabled: true
      size: 8Gi
  metrics:
    enabled: true
    serviceMonitor:
      enabled: true
```

## Disabling Dependencies

### Disable PostgreSQL Only

```bash
helm install task-api . \
  --set postgresql.enabled=false \
  --set externalDatabase.host=my-db.example.com \
  --set externalDatabase.username=myuser \
  --set externalDatabase.password=mypass \
  --set externalDatabase.database=mydb
```

### Disable Redis Only

```bash
helm install task-api . \
  --set redis.enabled=false \
  --set externalRedis.host=my-redis.example.com \
  --set externalRedis.password=mypass
```

### Disable Both (Use All External Services)

```bash
helm install task-api . -f values-prod.yaml \
  --set postgresql.enabled=false \
  --set redis.enabled=false \
  --set externalDatabase.host=my-db.example.com \
  --set externalDatabase.password=$DB_PASS \
  --set externalRedis.host=my-redis.example.com \
  --set externalRedis.password=$REDIS_PASS
```

## Testing Connections

### Test PostgreSQL Connection

```bash
# Get PostgreSQL pod
kubectl get pods -n dev -l app.kubernetes.io/name=postgresql

# Connect to PostgreSQL
kubectl exec -it -n dev myrelease-postgresql-0 -- psql -U taskapi_dev -d tasks_dev

# Test from application pod
kubectl exec -it -n dev myrelease-task-api-xxx -- \
  psql postgresql://taskapi_dev:devpass123@myrelease-postgresql:5432/tasks_dev -c "SELECT 1"
```

### Test Redis Connection

```bash
# Get Redis pod
kubectl get pods -n dev -l app.kubernetes.io/name=redis

# Connect to Redis
kubectl exec -it -n dev myrelease-redis-master-0 -- redis-cli

# Test from application pod
kubectl exec -it -n dev myrelease-task-api-xxx -- \
  redis-cli -h myrelease-redis-master ping
```

## Troubleshooting

### Dependencies Not Downloaded

```bash
# Check dependency status
helm dependency list

# Update dependencies
helm dependency update

# Clean and rebuild
rm -rf charts/ Chart.lock
helm dependency build
```

### Connection Issues

```bash
# Check service DNS resolution
kubectl run -it --rm debug --image=busybox --restart=Never -- \
  nslookup myrelease-postgresql

# Check if service is accessible
kubectl run -it --rm debug --image=postgres:15 --restart=Never -- \
  psql postgresql://taskapi_dev:devpass123@myrelease-postgresql:5432/tasks_dev -c "SELECT 1"
```

### Password Issues

```bash
# Check secret exists
kubectl get secret myrelease-postgresql -n dev

# View secret (base64 encoded)
kubectl get secret myrelease-postgresql -n dev -o yaml

# Decode password
kubectl get secret myrelease-postgresql -n dev \
  -o jsonpath='{.data.password}' | base64 -d
```

## Migration Strategies

### From Internal to External PostgreSQL

1. **Backup internal database**
```bash
kubectl exec -n staging myrelease-postgresql-0 -- \
  pg_dump -U taskapi_staging tasks_staging > backup.sql
```

2. **Restore to external database**
```bash
psql -h external-db.example.com -U taskapi_staging tasks_staging < backup.sql
```

3. **Update values and upgrade**
```bash
helm upgrade task-api . -f values-prod.yaml \
  --set postgresql.enabled=false \
  --set externalDatabase.host=external-db.example.com
```

### From External to Internal (Rollback)

1. **Backup external database**
2. **Enable internal PostgreSQL**
3. **Restore data to internal instance**

## Best Practices

1. **Development**
   - Use internal dependencies for simplicity
   - Disable persistence for faster iteration
   - Use minimal resources

2. **Staging**
   - Use internal dependencies with persistence
   - Production-like configuration
   - Enable monitoring

3. **Production**
   - Use external managed services
   - Enable automatic backups
   - Configure high availability
   - Use strong passwords (not in values files)
   - Enable TLS/SSL connections

4. **Security**
   - Never commit passwords to values files
   - Use Kubernetes secrets or external secret managers
   - Rotate credentials regularly
   - Use network policies to restrict access

5. **Monitoring**
   - Enable metrics exporters
   - Set up alerting for connection issues
   - Monitor resource usage
   - Track query performance

## Reference

- [PostgreSQL Bitnami Chart](https://github.com/bitnami/charts/tree/main/bitnami/postgresql)
- [Redis Bitnami Chart](https://github.com/bitnami/charts/tree/main/bitnami/redis)
- [Helm Dependencies Documentation](https://helm.sh/docs/helm/helm_dependency/)
