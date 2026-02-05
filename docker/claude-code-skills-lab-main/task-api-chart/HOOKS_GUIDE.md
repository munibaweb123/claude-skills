# Helm Hooks Guide

This chart includes several Helm hooks for lifecycle management.

## Available Hooks

### 1. Pre-Upgrade Migration (pre-upgrade-migration.yaml)

**When**: Before every upgrade and initial install
**Purpose**: Run database schema migrations
**Weight**: -5 (runs early)
**Delete Policy**: before-hook-creation, hook-succeeded

```bash
# Migration runs automatically on:
helm install task-api . -f values.yaml
helm upgrade task-api . -f values.yaml
```

**Customize migration command** in the template:
```yaml
command:
  - sh
  - -c
  - |
    # Change this to your migration tool
    alembic upgrade head
    # Or: python manage.py migrate
    # Or: flyway migrate
```

### 2. Post-Upgrade Health Check (post-upgrade-test.yaml)

**When**: After every upgrade and install completes
**Purpose**: Validate deployment health
**Weight**: 5 (runs late)
**Delete Policy**: before-hook-creation, hook-succeeded

Tests:
- Health endpoint
- Readiness endpoint
- Database connectivity (if enabled)

### 3. Pre-Delete Backup (pre-delete-backup.yaml)

**When**: Before chart deletion
**Purpose**: Create database backup
**Weight**: -5
**Delete Policy**: hook-succeeded

Only runs if `postgresql.enabled=true` (internal database).

```bash
# Backup runs automatically on:
helm uninstall task-api
```

### 4. Test Hook (test-connection.yaml)

**When**: When you run `helm test`
**Purpose**: Validate deployment
**Delete Policy**: hook-succeeded

```bash
# Run tests manually:
helm test task-api -n production

# View test results:
kubectl logs task-api-test-connection -n production
```

## Hook Execution Order

### During Install

```text
1. pre-install hooks (weight order)
   └─ pre-upgrade-migration.yaml (weight: -5)
2. Deploy resources (Deployment, Service, etc.)
3. post-install hooks (weight order)
   └─ post-upgrade-test.yaml (weight: 5)
```

### During Upgrade

```text
1. pre-upgrade hooks (weight order)
   └─ pre-upgrade-migration.yaml (weight: -5)
2. Upgrade resources
3. post-upgrade hooks (weight order)
   └─ post-upgrade-test.yaml (weight: 5)
```

### During Delete

```text
1. pre-delete hooks (weight order)
   └─ pre-delete-backup.yaml (weight: -5)
2. Delete resources
```

## Hook Annotations Explained

### helm.sh/hook

Specifies when the hook runs:

```yaml
helm.sh/hook: pre-upgrade           # Single hook
helm.sh/hook: pre-install,pre-upgrade  # Multiple hooks
```

**All hook types:**
- `pre-install` - Before install
- `post-install` - After install
- `pre-upgrade` - Before upgrade
- `post-upgrade` - After upgrade
- `pre-delete` - Before delete
- `post-delete` - After delete
- `pre-rollback` - Before rollback
- `post-rollback` - After rollback
- `test` - On `helm test` command

### helm.sh/hook-weight

Controls execution order (ascending):

```yaml
helm.sh/hook-weight: "-10"  # Runs first
helm.sh/hook-weight: "-5"   # Runs second
helm.sh/hook-weight: "0"    # Default, runs third
helm.sh/hook-weight: "5"    # Runs fourth
helm.sh/hook-weight: "10"   # Runs last
```

**Our weight convention:**
- `-10`: Database readiness checks
- `-5`: Database migrations
- `0`: Default operations
- `5`: Health checks, notifications
- `10`: External integrations

### helm.sh/hook-delete-policy

Controls cleanup behavior:

```yaml
# Delete before creating new hook (prevents duplicates)
helm.sh/hook-delete-policy: before-hook-creation

# Delete after hook succeeds
helm.sh/hook-delete-policy: hook-succeeded

# Delete after hook fails
helm.sh/hook-delete-policy: hook-failed

# Combine multiple policies
helm.sh/hook-delete-policy: before-hook-creation,hook-succeeded
```

**Recommendations:**
- Production: `before-hook-creation,hook-succeeded` (keep failures for debugging)
- Development: Omit (keep all for inspection)
- CI/CD: `before-hook-creation,hook-succeeded,hook-failed` (always clean up)

## Troubleshooting Hooks

### View Hook Status

```bash
# List hook jobs
kubectl get jobs -n production

# View specific hook
kubectl get job task-api-db-migrate-3 -n production

# View hook logs
kubectl logs job/task-api-db-migrate-3 -n production

# Describe for events
kubectl describe job/task-api-db-migrate-3 -n production
```

### Hook Failed

```bash
# View why it failed
kubectl describe job/task-api-db-migrate-3

# View logs
kubectl logs job/task-api-db-migrate-3

# Delete failed hook to retry
kubectl delete job/task-api-db-migrate-3

# Retry upgrade
helm upgrade task-api . -f values.yaml
```

### Hook Hanging

```bash
# Check pod status
kubectl get pods -l job-name=task-api-db-migrate-3

# Force delete
kubectl delete job/task-api-db-migrate-3 --grace-period=0 --force
```

### Disable Hooks Temporarily

```bash
# Skip hooks during install/upgrade
helm install task-api . --no-hooks

# Skip hooks during upgrade
helm upgrade task-api . --no-hooks
```

### Debug Hooks

To keep hooks for inspection, modify delete policy:

```yaml
# In template:
annotations:
  helm.sh/hook: pre-upgrade
  # Comment out delete policy
  # helm.sh/hook-delete-policy: before-hook-creation,hook-succeeded
```

## Customizing Hooks

### Disable Specific Hooks

Add conditions to templates:

```yaml
{{- if .Values.hooks.migration.enabled }}
apiVersion: batch/v1
kind: Job
# ... migration hook
{{- end }}
```

Then in values.yaml:

```yaml
hooks:
  migration:
    enabled: true
  healthCheck:
    enabled: true
  backup:
    enabled: true
```

### Custom Migration Command

Edit `templates/pre-upgrade-migration.yaml`:

```yaml
command:
  - sh
  - -c
  - |
    # Your custom migration command
    python manage.py migrate
```

### Add Custom Hooks

Create new hook template in `templates/`:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: {{ include "task-api-chart.fullname" . }}-custom-hook
  annotations:
    helm.sh/hook: post-install
    helm.sh/hook-weight: "5"
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

## Testing Hooks Locally

### Render Hook Templates

```bash
# View migration hook
helm template task-api . --show-only templates/pre-upgrade-migration.yaml

# View all hooks
helm template task-api . | grep -A 50 "kind: Job"
```

### Test Migration Script

```bash
# Get the migration job
kubectl get job -l app.kubernetes.io/component=migration

# Run migration manually (for testing)
kubectl create job --from=cronjob/task-api-db-migrate manual-test
```

### Dry Run Install

```bash
# Preview what will happen
helm install task-api . --dry-run --debug

# Shows hook execution order
```

## Best Practices

### 1. Idempotency

Ensure hooks can run multiple times safely:

```bash
# Bad: Fails if table exists
CREATE TABLE users ...;

# Good: Idempotent
CREATE TABLE IF NOT EXISTS users ...;
```

### 2. Timeouts

Set timeouts to prevent hanging:

```yaml
spec:
  activeDeadlineSeconds: 300  # Job timeout: 5 minutes
```

### 3. Resource Limits

Always set resource limits:

```yaml
resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 100m
    memory: 128Mi
```

### 4. Logging

Provide clear logs:

```bash
echo "=== Starting Migration ==="
echo "Release: {{ .Release.Name }}"
echo "Revision: {{ .Release.Revision }}"
# ... run migration ...
echo "=== Migration Complete ==="
```

### 5. Error Handling

Handle errors gracefully:

```bash
set -e  # Exit on error

if ! alembic upgrade head; then
    echo "Migration failed!"
    # Send alert
    curl -X POST https://alerts.example.com/failed
    exit 1
fi
```

## Environment-Specific Behavior

Hooks behave differently based on configuration:

### Development
- Migrations run on basic schema
- Health checks may be relaxed
- Backups optional

### Staging
- Migrations tested before production
- Full health validation
- Backups enabled

### Production
- Critical migrations with extra caution
- Strict health checks
- Mandatory backups before deletion

## Quick Commands Reference

| Action | Command |
|--------|---------|
| View hooks | `kubectl get jobs -n namespace` |
| View logs | `kubectl logs job/name -n namespace` |
| Delete hook | `kubectl delete job/name -n namespace` |
| Run test | `helm test release -n namespace` |
| Skip hooks | `helm upgrade --no-hooks` |
| Dry run | `helm install --dry-run --debug` |

## Further Reading

- [Helm Hooks Documentation](https://helm.sh/docs/topics/charts_hooks/)
- [Kubernetes Jobs](https://kubernetes.io/docs/concepts/workloads/controllers/job/)
- Complete reference: [.claude/skills/helm-chart-skill/references/HOOKS.md](../.claude/skills/helm-chart-skill/references/HOOKS.md)
