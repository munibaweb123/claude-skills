# Helm Hooks Implementation Summary

## Overview

The task-api chart now includes comprehensive Helm hooks for lifecycle management, migrations, health checks, backups, and testing.

## Implemented Hooks

### 1. Pre-Upgrade Migration Hook
**File**: [templates/pre-upgrade-migration.yaml](templates/pre-upgrade-migration.yaml)

```yaml
annotations:
  helm.sh/hook: pre-upgrade,pre-install
  helm.sh/hook-weight: "-5"
  helm.sh/hook-delete-policy: before-hook-creation,hook-succeeded
```

**Purpose**: Run database schema migrations before upgrades
**When**: Before every `helm install` and `helm upgrade`
**Weight**: -5 (runs early, after database readiness checks)
**Cleanup**: Deletes previous hook and successful completions

**Features**:
- Init container waits for PostgreSQL to be ready
- Uses connection helpers for database access
- Customizable migration command (Alembic, Django, Flyway, etc.)
- Proper error handling and logging
- Resource limits configured

**Usage**:
```bash
# Migrations run automatically
helm install task-api . -f values.yaml
helm upgrade task-api . -f values.yaml

# Skip migrations if needed
helm upgrade task-api . --no-hooks
```

### 2. Post-Upgrade Health Check Hook
**File**: [templates/post-upgrade-test.yaml](templates/post-upgrade-test.yaml)

```yaml
annotations:
  helm.sh/hook: post-upgrade,post-install
  helm.sh/hook-weight: "5"
  helm.sh/hook-delete-policy: before-hook-creation,hook-succeeded
```

**Purpose**: Validate deployment after upgrade completes
**When**: After every `helm install` and `helm upgrade`
**Weight**: 5 (runs late, after all resources deployed)
**Cleanup**: Deletes previous hook and successful completions

**Tests**:
- Health endpoint accessibility
- Readiness endpoint validation
- Database connectivity (if enabled)
- API root endpoint

**Features**:
- Retries on failure (backoffLimit: 3)
- 5-minute timeout
- Clear test output
- Fails deployment if health checks fail

### 3. Pre-Delete Backup Hook
**File**: [templates/pre-delete-backup.yaml](templates/pre-delete-backup.yaml)

```yaml
annotations:
  helm.sh/hook: pre-delete
  helm.sh/hook-weight: "-5"
  helm.sh/hook-delete-policy: hook-succeeded
```

**Purpose**: Create database backup before deletion
**When**: Before `helm uninstall`
**Weight**: -5 (runs early in deletion)
**Cleanup**: Deletes only on success (keeps failures for recovery)
**Condition**: Only runs if `postgresql.enabled=true`

**Features**:
- Creates timestamped backup
- Uses `pg_dump` for PostgreSQL
- Optional S3/cloud upload (commented out)
- 30-minute timeout for large databases
- Backup stored in emptyDir volume

**Usage**:
```bash
# Backup runs automatically
helm uninstall task-api

# View backup job
kubectl get job -l app.kubernetes.io/component=backup

# Get backup logs
kubectl logs job/task-api-backup-20240127-182400
```

### 4. Helm Test Hook
**File**: [templates/test-connection.yaml](templates/test-connection.yaml)

```yaml
annotations:
  helm.sh/hook: test
  helm.sh/hook-delete-policy: hook-succeeded
```

**Purpose**: On-demand validation of deployment
**When**: Manually with `helm test` command
**Cleanup**: Deletes after success

**Tests**:
- Health endpoint
- Readiness endpoint
- API root endpoint
- Database connectivity (if enabled)
- Redis connectivity (if enabled)

**Usage**:
```bash
# Run tests
helm test task-api -n production

# View test output
kubectl logs task-api-test-connection -n production

# Clean up test pod
kubectl delete pod task-api-test-connection
```

## Hook Execution Flow

### Install Flow

```text
helm install task-api . -f values.yaml
  ↓
1. pre-install hooks execute (weight order)
   ├─ pre-upgrade-migration.yaml (weight: -5)
   │  ├─ Init: Wait for database
   │  └─ Run: alembic upgrade head
   ↓
2. Deploy resources
   ├─ Deployment (replicas, pods)
   ├─ Service
   ├─ ServiceAccount
   └─ (PostgreSQL, Redis if enabled)
   ↓
3. post-install hooks execute (weight order)
   └─ post-upgrade-test.yaml (weight: 5)
      ├─ Test: Health endpoint
      ├─ Test: Readiness endpoint
      └─ Test: Database connection
   ↓
4. Installation complete
```

### Upgrade Flow

```text
helm upgrade task-api . -f values.yaml
  ↓
1. pre-upgrade hooks execute
   └─ pre-upgrade-migration.yaml (weight: -5)
      └─ Apply database migrations
   ↓
2. Upgrade resources (rolling update)
   ↓
3. post-upgrade hooks execute
   └─ post-upgrade-test.yaml (weight: 5)
      └─ Validate deployment health
   ↓
4. Upgrade complete
```

### Delete Flow

```text
helm uninstall task-api
  ↓
1. pre-delete hooks execute
   └─ pre-delete-backup.yaml (weight: -5)
      └─ Create database backup
   ↓
2. Delete all resources
   ├─ Deployment
   ├─ Service
   ├─ PostgreSQL (if internal)
   └─ Redis (if internal)
   ↓
3. Deletion complete
```

## Hook Annotations Explained

### helm.sh/hook

Defines when the hook runs:

```yaml
# Single phase
helm.sh/hook: pre-upgrade

# Multiple phases
helm.sh/hook: pre-install,pre-upgrade

# All available phases:
# - pre-install
# - post-install
# - pre-upgrade
# - post-upgrade
# - pre-delete
# - post-delete
# - pre-rollback
# - post-rollback
# - test
```

### helm.sh/hook-weight

Controls execution order (ascending):

```yaml
helm.sh/hook-weight: "-10"  # Database readiness
helm.sh/hook-weight: "-5"   # Migrations, backups
helm.sh/hook-weight: "0"    # Default operations
helm.sh/hook-weight: "5"    # Health checks, notifications
helm.sh/hook-weight: "10"   # External integrations
```

**Our convention**:
- `-10`: Prerequisites (database ready, external services)
- `-5`: Critical operations (migrations, backups)
- `0`: Standard operations
- `5`: Validation and testing
- `10`: Notifications and cleanup

### helm.sh/hook-delete-policy

Controls cleanup behavior:

```yaml
# Clean up options:
before-hook-creation  # Delete previous hook first
hook-succeeded       # Delete after success
hook-failed          # Delete after failure

# Common patterns:
# Production: Keep failures for debugging
helm.sh/hook-delete-policy: before-hook-creation,hook-succeeded

# CI/CD: Always clean up
helm.sh/hook-delete-policy: before-hook-creation,hook-succeeded,hook-failed

# Development: Keep all (omit annotation)
```

## Troubleshooting

### View Hook Status

```bash
# List all jobs (hooks are Jobs)
kubectl get jobs -n production

# Filter by component
kubectl get jobs -l app.kubernetes.io/component=migration
kubectl get jobs -l app.kubernetes.io/component=health-check
kubectl get jobs -l app.kubernetes.io/component=backup

# View specific hook
kubectl describe job task-api-db-migrate-3
```

### View Hook Logs

```bash
# Migration logs
kubectl logs job/task-api-db-migrate-3

# Health check logs
kubectl logs job/task-api-health-check-3

# Test logs
kubectl logs task-api-test-connection

# Follow logs in real-time
kubectl logs -f job/task-api-db-migrate-3
```

### Hook Failed - Debugging

```bash
# 1. Check why it failed
kubectl describe job/task-api-db-migrate-3

# 2. View error logs
kubectl logs job/task-api-db-migrate-3

# 3. Check pod events
kubectl get events --field-selector involvedObject.name=task-api-db-migrate-3

# 4. Delete failed hook
kubectl delete job/task-api-db-migrate-3

# 5. Retry upgrade
helm upgrade task-api . -f values.yaml
```

### Skip Hooks Temporarily

```bash
# Skip all hooks
helm upgrade task-api . --no-hooks

# Useful for:
# - Emergency rollback
# - Testing without migrations
# - Skipping long-running operations
```

## Best Practices

### 1. Idempotency ✅

All hooks are idempotent (safe to run multiple times):

```bash
# Migrations: Use framework's built-in idempotency
alembic upgrade head  # Only applies new migrations

# Backups: Timestamped filenames prevent overwrites
backup-20240127-120000.sql

# Health checks: Read-only operations
```

### 2. Timeouts ✅

Appropriate timeouts prevent hanging:

```yaml
# Job-level timeout
activeDeadlineSeconds: 300  # 5 minutes

# Command-level timeout
command: ["timeout", "300", "alembic", "upgrade", "head"]
```

### 3. Resource Limits ✅

All hooks have resource limits:

```yaml
resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 100m
    memory: 128Mi
```

### 4. Error Handling ✅

Clear error messages and proper exit codes:

```bash
set -e  # Exit on error

if ! alembic upgrade head; then
    echo "✗ Migration failed"
    exit 1
fi

echo "✓ Migration succeeded"
```

### 5. Logging ✅

Comprehensive logging for debugging:

```bash
echo "=== Starting Migration ==="
echo "Release: {{ .Release.Name }}"
echo "Revision: {{ .Release.Revision }}"
# ... operation ...
echo "=== Migration Complete ==="
```

## Customization

### Change Migration Tool

Edit `templates/pre-upgrade-migration.yaml`:

```yaml
# Alembic (default)
command: ["alembic", "upgrade", "head"]

# Django
command: ["python", "manage.py", "migrate"]

# Flyway
command: ["flyway", "migrate"]

# Liquibase
command: ["liquibase", "update"]

# Custom script
command: ["sh", "/scripts/migrate.sh"]
```

### Disable Specific Hooks

Add to values.yaml and modify templates:

```yaml
# values.yaml
hooks:
  migration:
    enabled: true
  healthCheck:
    enabled: false
  backup:
    enabled: true
```

### Add Custom Hooks

Create new file in `templates/`:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: {{ include "task-api-chart.fullname" . }}-custom
  annotations:
    helm.sh/hook: post-install
    helm.sh/hook-weight: "10"
    helm.sh/hook-delete-policy: before-hook-creation,hook-succeeded
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: custom
          image: myimage:latest
          command: ["my-command"]
```

## Testing

### Test Locally

```bash
# Render hook templates
helm template task-api . --show-only templates/pre-upgrade-migration.yaml

# Dry-run install
helm install task-api . --dry-run --debug

# Check hook annotations
helm template task-api . | grep -A 3 "helm.sh/hook"
```

### Test in Development

```bash
# Install with hooks
helm install task-api . -f values-dev.yaml -n dev --create-namespace

# Watch hooks execute
watch kubectl get jobs -n dev

# View hook logs
kubectl logs -f job/task-api-db-migrate-1 -n dev
```

### Run Tests

```bash
# Run Helm tests
helm test task-api -n dev

# View test results
kubectl get pods -l helm.sh/hook=test -n dev
kubectl logs task-api-test-connection -n dev
```

## Documentation

- **Complete Reference**: [.claude/skills/helm-chart-skill/references/HOOKS.md](../.claude/skills/helm-chart-skill/references/HOOKS.md)
- **User Guide**: [HOOKS_GUIDE.md](HOOKS_GUIDE.md)
- **Official Docs**: [Helm Hooks](https://helm.sh/docs/topics/charts_hooks/)

## Quick Commands

| Action | Command |
|--------|---------|
| List hooks | `kubectl get jobs -n namespace` |
| View logs | `kubectl logs job/name -n namespace` |
| Delete hook | `kubectl delete job/name -n namespace` |
| Run test | `helm test release -n namespace` |
| Skip hooks | `helm upgrade --no-hooks` |
| Dry run | `helm install --dry-run --debug` |

## Summary

✅ **4 Hooks Implemented**:
1. Pre-Upgrade Migration (weight: -5)
2. Post-Upgrade Health Check (weight: 5)
3. Pre-Delete Backup (weight: -5)
4. Helm Test (on-demand)

✅ **All 9 Hook Types Documented**:
pre-install, post-install, pre-upgrade, post-upgrade, pre-delete, post-delete, pre-rollback, post-rollback, test

✅ **Weight Ordering**: -10 (readiness) → -5 (migrations) → 0 (default) → 5 (validation) → 10 (notifications)

✅ **Delete Policies**: before-hook-creation, hook-succeeded, hook-failed

✅ **Best Practices**: Idempotent, timeouts, resource limits, error handling, logging

✅ **Connection Helpers**: Smart internal/external database and Redis detection
