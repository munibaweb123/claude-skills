# Helm Hooks Reference

## Overview

Helm hooks allow you to intervene at specific points in a release's lifecycle. Hooks are Kubernetes resources (Jobs, Pods, etc.) with special annotations that tell Helm when to execute them.

## Hook Types

Helm provides the following hook types:

### Install Hooks

| Hook | Execution Point |
|------|----------------|
| `pre-install` | Before any resources are installed |
| `post-install` | After all resources are installed |

**Use cases:**
- Pre-install: Database initialization, secret generation
- Post-install: Send notifications, register with external services

### Upgrade Hooks

| Hook | Execution Point |
|------|----------------|
| `pre-upgrade` | Before any resources are upgraded |
| `post-upgrade` | After all resources are upgraded |

**Use cases:**
- Pre-upgrade: **Database migrations**, backup data, validate prerequisites
- Post-upgrade: Health checks, smoke tests, notifications

### Delete Hooks

| Hook | Execution Point |
|------|----------------|
| `pre-delete` | Before any resources are deleted |
| `post-delete` | After all resources are deleted |

**Use cases:**
- Pre-delete: Backup data, notify users, deregister services
- Post-delete: Cleanup external resources, remove DNS entries

### Rollback Hooks

| Hook | Execution Point |
|------|----------------|
| `pre-rollback` | Before any resources are rolled back |
| `post-rollback` | After all resources are rolled back |

**Use cases:**
- Pre-rollback: Prepare for rollback, backup current state
- Post-rollback: Restore data, validate system state

### Test Hook

| Hook | Execution Point |
|------|----------------|
| `test` | When `helm test` command is run |

**Use cases:**
- Integration tests, connectivity tests, validation

## Hook Annotations

Hooks are defined using annotations on Kubernetes resources:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: pre-upgrade-migration
  annotations:
    # Required: Defines when the hook runs
    helm.sh/hook: pre-upgrade

    # Optional: Defines execution order (default: 0)
    helm.sh/hook-weight: "-5"

    # Optional: Defines cleanup behavior
    helm.sh/hook-delete-policy: before-hook-creation,hook-succeeded
```

### 1. helm.sh/hook (Required)

Specifies when the hook should run. Multiple hooks can be comma-separated.

```yaml
annotations:
  # Single hook
  helm.sh/hook: pre-upgrade

  # Multiple hooks
  helm.sh/hook: pre-install,pre-upgrade

  # All install/upgrade hooks
  helm.sh/hook: pre-install,post-install,pre-upgrade,post-upgrade
```

### 2. helm.sh/hook-weight (Optional)

Defines the execution order of hooks. Hooks execute in **ascending weight order**.

- **Range**: Any integer (negative to positive)
- **Default**: 0
- **Lower weights execute first**

```yaml
annotations:
  # Runs first (weight: -10)
  helm.sh/hook-weight: "-10"

  # Runs second (weight: -5)
  helm.sh/hook-weight: "-5"

  # Runs third (weight: 0, default)
  helm.sh/hook-weight: "0"

  # Runs last (weight: 5)
  helm.sh/hook-weight: "5"
```

**Common weight patterns:**

```yaml
# Database migrations (run early)
helm.sh/hook-weight: "-5"

# Default processing
helm.sh/hook-weight: "0"

# Post-processing, notifications (run late)
helm.sh/hook-weight: "5"
```

### 3. helm.sh/hook-delete-policy (Optional)

Controls when Helm deletes hook resources.

| Policy | Behavior |
|--------|----------|
| `before-hook-creation` | Delete previous hook before creating new one (default) |
| `hook-succeeded` | Delete hook after it succeeds |
| `hook-failed` | Delete hook after it fails |

**Multiple policies** can be comma-separated:

```yaml
annotations:
  # Delete before new hook + delete if succeeded
  helm.sh/hook-delete-policy: before-hook-creation,hook-succeeded

  # Delete regardless of outcome
  helm.sh/hook-delete-policy: before-hook-creation,hook-succeeded,hook-failed

  # Never delete (for debugging)
  # (omit annotation or use empty value)
```

**Best Practices:**

```yaml
# Production: Clean up successes, keep failures for debugging
helm.sh/hook-delete-policy: before-hook-creation,hook-succeeded

# Development: Keep all hooks for inspection
# (omit the annotation)

# CI/CD: Clean up everything
helm.sh/hook-delete-policy: before-hook-creation,hook-succeeded,hook-failed
```

## Hook Execution Flow

### Install Flow

```text
1. User runs: helm install myapp ./chart
2. Helm validates chart
3. pre-install hooks execute (in weight order)
4. Wait for pre-install hooks to complete
5. Install chart resources (Deployments, Services, etc.)
6. Wait for resources to be ready
7. post-install hooks execute (in weight order)
8. Wait for post-install hooks to complete
9. Installation complete
```

### Upgrade Flow

```text
1. User runs: helm upgrade myapp ./chart
2. Helm validates chart
3. pre-upgrade hooks execute (in weight order)
4. Wait for pre-upgrade hooks to complete
5. Upgrade chart resources
6. Wait for resources to be ready
7. post-upgrade hooks execute (in weight order)
8. Wait for post-upgrade hooks to complete
9. Upgrade complete
```

### Hook Weight Ordering

```text
Hooks with weight -10: [hook-a, hook-b] (parallel within same weight)
  ↓
Hooks with weight -5: [hook-c]
  ↓
Hooks with weight 0: [hook-d, hook-e] (parallel within same weight)
  ↓
Hooks with weight 5: [hook-f]
  ↓
Resources deployed
```

## Complete Examples

### Example 1: Pre-Upgrade Database Migration

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: {{ include "mychart.fullname" . }}-db-migrate-{{ .Release.Revision }}
  annotations:
    # Run before upgrade, early in sequence
    helm.sh/hook: pre-upgrade,pre-install
    helm.sh/hook-weight: "-5"
    helm.sh/hook-delete-policy: before-hook-creation,hook-succeeded
spec:
  backoffLimit: 0
  ttlSecondsAfterFinished: 300
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: migrate
          image: myapp:{{ .Values.image.tag }}
          command: ["alembic", "upgrade", "head"]
          env:
            - name: DATABASE_URL
              value: {{ include "mychart.postgresql.url" . | quote }}
```

### Example 2: Post-Install Notification

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: {{ include "mychart.fullname" . }}-notify-{{ .Release.Revision }}
  annotations:
    # Run after install completes
    helm.sh/hook: post-install,post-upgrade
    helm.sh/hook-weight: "5"
    helm.sh/hook-delete-policy: before-hook-creation,hook-succeeded
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: notify
          image: curlimages/curl:latest
          command:
            - sh
            - -c
            - |
              curl -X POST https://api.slack.com/webhooks/xxx \
                -d '{"text":"Deployed {{ .Release.Name }} version {{ .Chart.Version }}"}'
```

### Example 3: Pre-Delete Backup

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: {{ include "mychart.fullname" . }}-backup-{{ .Release.Revision }}
  annotations:
    # Run before deletion
    helm.sh/hook: pre-delete
    helm.sh/hook-weight: "-5"
    helm.sh/hook-delete-policy: hook-succeeded
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: backup
          image: postgres:15-alpine
          command:
            - sh
            - -c
            - |
              pg_dump {{ include "mychart.postgresql.url" . }} > /backup/dump-$(date +%Y%m%d).sql
              aws s3 cp /backup/dump-$(date +%Y%m%d).sql s3://backups/
```

### Example 4: Helm Test Hook

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: {{ include "mychart.fullname" . }}-test-connection
  annotations:
    # Run when 'helm test' is executed
    helm.sh/hook: test
    helm.sh/hook-delete-policy: hook-succeeded
spec:
  restartPolicy: Never
  containers:
    - name: test
      image: curlimages/curl:latest
      command:
        - sh
        - -c
        - |
          # Test service is accessible
          curl --fail http://{{ include "mychart.fullname" . }}:{{ .Values.service.port }}/health
```

### Example 5: Multiple Hooks with Weights

```yaml
---
# Hook 1: Wait for database (weight: -10, runs first)
apiVersion: batch/v1
kind: Job
metadata:
  name: wait-for-db
  annotations:
    helm.sh/hook: pre-install,pre-upgrade
    helm.sh/hook-weight: "-10"
    helm.sh/hook-delete-policy: before-hook-creation,hook-succeeded
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: wait
          image: postgres:15-alpine
          command: ["sh", "-c", "until pg_isready -h db; do sleep 2; done"]

---
# Hook 2: Run migrations (weight: -5, runs second)
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migrate
  annotations:
    helm.sh/hook: pre-install,pre-upgrade
    helm.sh/hook-weight: "-5"
    helm.sh/hook-delete-policy: before-hook-creation,hook-succeeded
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: migrate
          image: myapp:latest
          command: ["alembic", "upgrade", "head"]

---
# Hook 3: Seed data (weight: 0, runs third)
apiVersion: batch/v1
kind: Job
metadata:
  name: seed-data
  annotations:
    helm.sh/hook: post-install
    helm.sh/hook-weight: "0"
    helm.sh/hook-delete-policy: before-hook-creation,hook-succeeded
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: seed
          image: myapp:latest
          command: ["python", "seed.py"]

---
# Hook 4: Notify (weight: 5, runs last)
apiVersion: batch/v1
kind: Job
metadata:
  name: notify
  annotations:
    helm.sh/hook: post-install,post-upgrade
    helm.sh/hook-weight: "5"
    helm.sh/hook-delete-policy: before-hook-creation,hook-succeeded
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: notify
          image: curlimages/curl:latest
          command: ["sh", "-c", "curl -X POST https://webhook.site/xxx"]
```

## Hook Resource Types

Hooks can be any Kubernetes resource, but Jobs and Pods are most common:

### Job (Recommended)

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: my-hook
  annotations:
    helm.sh/hook: pre-upgrade
spec:
  backoffLimit: 0  # Don't retry on failure
  ttlSecondsAfterFinished: 300  # Auto-cleanup after 5 minutes
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: hook-container
          image: myimage:latest
```

**Advantages:**
- Automatic retry logic (if backoffLimit > 0)
- Completion tracking
- TTL for auto-cleanup

### Pod

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-hook
  annotations:
    helm.sh/hook: pre-upgrade
spec:
  restartPolicy: Never
  containers:
    - name: hook-container
      image: myimage:latest
```

**Advantages:**
- Simpler than Job
- Faster creation
- Good for tests

### Other Resources

Hooks can also be:
- **ConfigMaps/Secrets**: For configuration setup
- **Services**: For temporary endpoints
- **Custom Resources**: For operator-based tasks

## Common Patterns

### Pattern 1: Database Migration

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migrate-{{ .Release.Revision }}
  annotations:
    helm.sh/hook: pre-upgrade,pre-install
    helm.sh/hook-weight: "-5"
    helm.sh/hook-delete-policy: before-hook-creation,hook-succeeded
```

### Pattern 2: Service Readiness Check

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: readiness-check
  annotations:
    helm.sh/hook: post-install,post-upgrade
    helm.sh/hook-weight: "0"
    helm.sh/hook-delete-policy: hook-succeeded
```

### Pattern 3: Cleanup External Resources

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: cleanup
  annotations:
    helm.sh/hook: pre-delete
    helm.sh/hook-weight: "-5"
    helm.sh/hook-delete-policy: hook-succeeded
```

## Best Practices

### 1. Idempotency

Hooks may run multiple times. Ensure they're idempotent:

```bash
# Bad: Fails if database exists
createdb mydb

# Good: Idempotent
createdb mydb || echo "Database already exists"
```

### 2. Timeouts

Set appropriate timeouts to prevent hanging:

```yaml
spec:
  activeDeadlineSeconds: 300  # Job timeout: 5 minutes
  template:
    spec:
      containers:
        - name: migrate
          command:
            - timeout
            - "300"  # Command timeout: 5 minutes
            - alembic
            - upgrade
            - head
```

### 3. Error Handling

Always handle errors gracefully:

```bash
#!/bin/sh
set -e  # Exit on error

# Run migration
if ! alembic upgrade head; then
    echo "Migration failed!"
    # Optional: Send alert
    curl -X POST https://alerts.example.com/migration-failed
    exit 1
fi

echo "Migration succeeded"
```

### 4. Logging

Provide clear logs for debugging:

```bash
echo "=== Starting Migration ==="
echo "Database: $DATABASE_HOST:$DATABASE_PORT/$DATABASE_NAME"
echo "Release: {{ .Release.Name }}"
echo "Revision: {{ .Release.Revision }}"

alembic upgrade head

echo "=== Migration Complete ==="
```

### 5. Resource Limits

Set resource limits to prevent resource exhaustion:

```yaml
resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 100m
    memory: 128Mi
```

## Troubleshooting

### View Hook Status

```bash
# List all jobs (hooks are Jobs)
kubectl get jobs -n mynamespace

# View hook logs
kubectl logs job/myapp-db-migrate-3 -n mynamespace

# Describe hook for events
kubectl describe job/myapp-db-migrate-3 -n mynamespace
```

### Hook Failures

```bash
# Check why hook failed
kubectl describe job/myapp-db-migrate-3

# View logs
kubectl logs job/myapp-db-migrate-3

# Delete failed hook manually
kubectl delete job/myapp-db-migrate-3
```

### Hook Hanging

```bash
# Check if hook pod is running
kubectl get pods -l job-name=myapp-db-migrate-3

# Force delete hanging hook
kubectl delete job/myapp-db-migrate-3 --grace-period=0 --force
```

### Debugging Hooks

```yaml
# Add for debugging (never auto-delete)
annotations:
  helm.sh/hook: pre-upgrade
  # Omit delete policy to keep hook pods
  # helm.sh/hook-delete-policy: ...

# Or keep failed hooks only
annotations:
  helm.sh/hook: pre-upgrade
  helm.sh/hook-delete-policy: before-hook-creation
```

## Testing Hooks

### Local Testing

```bash
# Render hook template
helm template myapp ./chart --show-only templates/hooks/pre-upgrade.yaml

# Dry-run install
helm install myapp ./chart --dry-run --debug

# Install in test namespace
helm install myapp ./chart -n test-hooks --create-namespace
```

### Running Test Hooks

```bash
# Run helm test
helm test myapp -n production

# View test results
kubectl get pods -l helm.sh/hook=test

# View test logs
kubectl logs myapp-test-connection
```

## Summary

### Hook Types Quick Reference

| Hook | When | Use For |
|------|------|---------|
| pre-install | Before install | Setup, initialization |
| post-install | After install | Validation, notification |
| pre-upgrade | Before upgrade | **Migrations**, backups |
| post-upgrade | After upgrade | Health checks, tests |
| pre-delete | Before delete | Backups, cleanup prep |
| post-delete | After delete | External cleanup |
| pre-rollback | Before rollback | Prepare for rollback |
| post-rollback | After rollback | Validate rollback |
| test | On `helm test` | Integration tests |

### Annotation Quick Reference

```yaml
annotations:
  # Required: When to run
  helm.sh/hook: pre-upgrade

  # Optional: Execution order (lower first)
  helm.sh/hook-weight: "-5"

  # Optional: Cleanup behavior
  helm.sh/hook-delete-policy: before-hook-creation,hook-succeeded
```

### Weight Convention

```
-10: Database readiness checks
 -5: Database migrations
  0: Data seeding, default operations
  5: Notifications, post-processing
 10: External integrations
```
