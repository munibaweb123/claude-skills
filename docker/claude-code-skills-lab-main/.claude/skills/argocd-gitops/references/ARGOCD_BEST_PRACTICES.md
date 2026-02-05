# ArgoCD Best Practices

This document outlines best practices for deploying and operating ArgoCD in production environments.

## Installation Best Practices

### Namespace Isolation
Always install ArgoCD in its own namespace to isolate it from other applications:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: argocd
```

### Resource Limits
Set appropriate resource limits to prevent resource exhaustion:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: argocd-server
  namespace: argocd
spec:
  template:
    spec:
      containers:
      - name: argocd-server
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi
```

## Security Best Practices

### TLS Configuration
Always use TLS for ArgoCD server:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: argocd-tls-certs
  namespace: argocd
type: kubernetes.io/tls
data:
  tls.crt: <base64-cert>
  tls.key: <base64-key>
```

### RBAC Configuration
Implement least-privilege RBAC:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-rbac-cm
  namespace: argocd
data:
  policy.csv: |
    p, role:readonly, applications, get, */*, allow
    p, role:developer, applications, *, my-project/*, allow
    g, developers-group, role:developer
```

## Performance Best Practices

### Repository Caching
Enable repository caching for improved performance:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cmd-params-cm
  namespace: argocd
data:
  reposerver.parallelism.limit: "10"
```

### Application Controller Settings
Optimize application controller for your environment:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cmd-params-cm
  namespace: argocd
data:
  controller.parallelism: "20"
  status.processors: "20"
  operation.processors: "10"
```

## Disaster Recovery

### Backup Strategy
Backup ArgoCD configuration regularly:

```bash
# Backup ArgoCD applications and projects
kubectl get applications -n argocd -o yaml > applications-backup.yaml
kubectl get appprojects -n argocd -o yaml > projects-backup.yaml
```

### Recovery Process
Restore ArgoCD from backups:

```bash
# Restore applications and projects
kubectl apply -f applications-backup.yaml
kubectl apply -f projects-backup.yaml
```

## Monitoring Best Practices

### Metrics Collection
Enable and configure metrics collection:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cmd-params-cm
  namespace: argocd
data:
  metrics.application.labels: "destination-server,project"
```

### Alerting Rules
Implement appropriate alerting:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: argocd-alerts
  namespace: argocd
spec:
  groups:
  - name: argocd
    rules:
    - alert: ArgoCDApplicationOutOfSync
      expr: sum(argocd_app_sync_status{sync_status="OutOfSync"}) > 0
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "ArgoCD application is out of sync"
```

## Multi-Tenancy Best Practices

### Project Isolation
Use projects to isolate applications:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: team-a-project
  namespace: argocd
spec:
  description: Team A project
  sourceRepos:
  - https://github.com/team-a/*
  destinations:
  - namespace: team-a-*
    server: https://kubernetes.default.svc
```

### Resource Quotas
Apply resource quotas per namespace:

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: team-a-quota
  namespace: team-a-prod
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 10Gi
    limits.cpu: "20"
    limits.memory: 20Gi
```

## Troubleshooting Best Practices

### Debugging OutOfSync Applications
```bash
# Get detailed application information
argocd app get <APP_NAME> -o yaml

# Compare local vs live state
argocd app diff <APP_NAME>

# Check controller logs
kubectl logs -n argocd deployment/argocd-application-controller
```

### Performance Issues
Monitor for performance issues:

```bash
# Check for slow repository access
kubectl logs -n argocd deployment/argocd-repo-server

# Monitor resource usage
kubectl top pods -n argocd
```