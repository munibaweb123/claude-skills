# Dependency Quick Start Guide

Quick commands and examples for managing PostgreSQL and Redis dependencies.

## Initial Setup

```bash
# 1. Add Bitnami repository
helm repo add bitnami https://charts.bitnami.com/bitnami

# 2. Update repository index
helm repo update

# 3. Download dependencies from Chart.yaml
cd task-api-chart
helm dependency update

# 4. Verify dependencies
helm dependency list
```

## Deployment Commands

### Development (Internal PostgreSQL + Redis)

```bash
# Install with internal dependencies
helm install task-api . -f values-dev.yaml -n dev --create-namespace

# Connect to PostgreSQL
kubectl exec -it -n dev task-api-postgresql-0 -- \
  psql -U taskapi_dev -d tasks_dev

# Connect to Redis
kubectl exec -it -n dev task-api-redis-master-0 -- redis-cli
```

### Staging (Internal with Persistence)

```bash
# Install with persistent storage
helm install task-api . -f values-staging.yaml -n staging --create-namespace

# Check PVCs
kubectl get pvc -n staging

# Backup database
kubectl exec -n staging task-api-postgresql-0 -- \
  pg_dump -U taskapi_staging tasks_staging > backup.sql
```

### Production (External Services)

```bash
# Install with external services (no internal PostgreSQL/Redis)
helm install task-api . -f values-prod.yaml \
  --set externalDatabase.password="$DB_PASSWORD" \
  --set externalRedis.password="$REDIS_PASSWORD" \
  -n prod --create-namespace --atomic --wait

# Verify no internal databases deployed
kubectl get pods -n prod
# Should only see task-api pods, no postgresql/redis
```

## Configuration Examples

### Enable/Disable Dependencies

**Enable Both (Development):**
```yaml
postgresql:
  enabled: true
redis:
  enabled: true
```

**PostgreSQL Only:**
```yaml
postgresql:
  enabled: true
redis:
  enabled: false
externalRedis:
  host: "external-redis.example.com"
  port: 6379
```

**External Services (Production):**
```yaml
postgresql:
  enabled: false
redis:
  enabled: false
externalDatabase:
  host: "prod-db.example.com"
  username: "taskapi"
  database: "tasks_prod"
externalRedis:
  host: "prod-redis.example.com"
```

### Custom Resources

**Development (Minimal):**
```yaml
postgresql:
  primary:
    resources:
      limits: { cpu: 250m, memory: 256Mi }
      requests: { cpu: 100m, memory: 128Mi }
```

**Production (Generous):**
```yaml
postgresql:
  primary:
    resources:
      limits: { cpu: 2000m, memory: 4Gi }
      requests: { cpu: 1000m, memory: 2Gi }
    persistence:
      enabled: true
      size: 50Gi
      storageClass: "fast-ssd"
```

## Connection Helpers Usage

### In Deployment Template

```yaml
env:
  # PostgreSQL - Individual components
  - name: DB_HOST
    value: {{ include "task-api-chart.postgresql.host" . | quote }}
  - name: DB_PORT
    value: {{ include "task-api-chart.postgresql.port" . | quote }}
  - name: DB_NAME
    value: {{ include "task-api-chart.postgresql.database" . | quote }}
  - name: DB_PASSWORD
    valueFrom:
      secretKeyRef:
        name: {{ include "task-api-chart.postgresql.secretName" . }}
        key: {{ include "task-api-chart.postgresql.secretKey" . }}

  # PostgreSQL - Full connection URL
  - name: DATABASE_URL
    value: {{ include "task-api-chart.postgresql.url" . | quote }}

  # Redis - Individual components
  - name: REDIS_HOST
    value: {{ include "task-api-chart.redis.host" . | quote }}
  - name: REDIS_PORT
    value: {{ include "task-api-chart.redis.port" . | quote }}

  # Redis - Full connection URL
  - name: REDIS_URL
    value: {{ include "task-api-chart.redis.url" . | quote }}
```

## Version Constraints

### Current Versions (Chart.yaml)

```yaml
dependencies:
  - name: postgresql
    version: "12.12.10"  # Exact version
  - name: redis
    version: "18.4.0"    # Exact version
```

### Alternative Constraints

```yaml
# Patch updates only (recommended for production)
version: "~12.12.10"  # Allows 12.12.x

# Minor updates allowed (for staging)
version: "^12.12.10"  # Allows 12.x.x

# Major version range
version: ">=12.0.0 <13.0.0"
```

## Troubleshooting

### Dependency Update Issues

```bash
# Clean and rebuild
rm -rf charts/ Chart.lock
helm dependency update

# Check repository connectivity
helm repo list
helm search repo bitnami/postgresql
helm search repo bitnami/redis
```

### Connection Issues

```bash
# DNS resolution test
kubectl run -it --rm debug --image=busybox -- \
  nslookup task-api-postgresql

# PostgreSQL connection test
kubectl run -it --rm debug --image=postgres:15 -- \
  psql postgresql://user:pass@task-api-postgresql:5432/db -c "SELECT 1"

# Redis connection test
kubectl run -it --rm debug --image=redis:7 -- \
  redis-cli -h task-api-redis-master ping
```

### Password Issues

```bash
# Get PostgreSQL password
kubectl get secret task-api-postgresql -o jsonpath='{.data.password}' | base64 -d

# Get Redis password
kubectl get secret task-api-redis -o jsonpath='{.data.redis-password}' | base64 -d

# Reset password
helm upgrade task-api . \
  --set postgresql.auth.password="newpass" \
  --set redis.auth.password="newpass"
```

## Maintenance

### Upgrade Dependencies

```bash
# 1. Update version in Chart.yaml
vim Chart.yaml

# 2. Update dependencies
helm dependency update

# 3. Check changes
helm dependency list
git diff Chart.lock

# 4. Upgrade release
helm upgrade task-api . -f values.yaml
```

### Backup Database

```bash
# Create backup
kubectl exec -n prod task-api-postgresql-0 -- \
  pg_dump -U taskapi tasks > backup-$(date +%Y%m%d).sql

# Restore backup
kubectl exec -i -n prod task-api-postgresql-0 -- \
  psql -U taskapi tasks < backup-20240115.sql
```

### Monitor Resources

```bash
# PostgreSQL resources
kubectl top pod -n prod -l app.kubernetes.io/name=postgresql

# Redis resources
kubectl top pod -n prod -l app.kubernetes.io/name=redis

# Check PVC usage
kubectl get pvc -n prod
kubectl describe pvc -n prod task-api-postgresql
```

## Quick Reference

| Action | Command |
|--------|---------|
| Add repo | `helm repo add bitnami https://charts.bitnami.com/bitnami` |
| Update deps | `helm dependency update` |
| List deps | `helm dependency list` |
| Clean deps | `rm -rf charts/ Chart.lock` |
| Install dev | `helm install task-api . -f values-dev.yaml` |
| Install prod | `helm install task-api . -f values-prod.yaml` |
| Check pods | `kubectl get pods -l app.kubernetes.io/name=postgresql` |
| Connect pg | `kubectl exec -it postgresql-0 -- psql` |
| Connect redis | `kubectl exec -it redis-master-0 -- redis-cli` |
| Get password | `kubectl get secret <name> -o jsonpath='{.data.password}' \| base64 -d` |

## Environment Comparison

| Feature | Development | Staging | Production |
|---------|------------|---------|------------|
| PostgreSQL | Internal | Internal | External |
| Redis | Internal | Internal | External |
| Persistence | No | Yes | Managed |
| Resources | Minimal | Moderate | High |
| Auth | Basic | Standard | Strong |
| Backups | No | Manual | Automatic |

## Next Steps

1. ✅ Add repository and download dependencies
2. ✅ Configure values for your environment
3. ✅ Test with dev environment
4. ✅ Validate connections work
5. ✅ Set up staging with persistence
6. ✅ Configure external services for production
7. ✅ Implement backup strategy
8. ✅ Monitor and optimize

For detailed documentation, see:
- [DEPENDENCIES.md](DEPENDENCIES.md) - Complete guide
- [VALUES_COMPARISON.md](VALUES_COMPARISON.md) - Environment comparison
- [README.md](README.md) - Chart overview
