# Monitoring and Observability for ArgoCD

This document covers monitoring, logging, and observability best practices for ArgoCD installations.

## Metrics Collection

### ArgoCD Metrics Configuration
Enable metrics collection in ArgoCD:

```yaml
# argocd-cmd-params-cm.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cmd-params-cm
  namespace: argocd
data:
  metrics.application.labels: "destination-server,project"
  metrics.application-resource.labels: "group,kind,destination-server,project"
  metrics.approto.labels: "destination-server,project"
```

### Available Metrics

#### Application Metrics
- `argocd_app_sync_total` - Total sync operations
- `argocd_app_sync_duration_seconds` - Sync operation duration
- `argocd_app_health_status` - Application health status
- `argocd_app_sync_status` - Application sync status
- `argocd_app_reconcile_total` - Reconciliation operations

#### Controller Metrics
- `argocd_app_reconcile_duration_seconds` - Reconciliation duration
- `argocd_kubectl_exec_pending` - Pending kubectl operations
- `argocd_cluster_events_total` - Cluster events

#### Repository Server Metrics
- `argocd_git_request_duration_seconds` - Git request duration
- `argocd_repo_server_git_request_total` - Git request count

## Prometheus Integration

### ServiceMonitor for ArgoCD
```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: argocd-metrics
  namespace: argocd
  labels:
    app: argocd-metrics
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: argocd-server-metrics
  endpoints:
  - port: metrics
    interval: 30s
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: argocd-application-controller
  namespace: argocd
  labels:
    app: argocd-application-controller
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: argocd-application-controller
  endpoints:
  - port: metrics
    interval: 30s
```

## Alerting Rules

### Critical Alerts
```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: argocd-critical-alerts
  namespace: argocd
spec:
  groups:
  - name: argocd-critical
    rules:
    - alert: ArgoCDApplicationOutOfSync
      expr: argocd_app_sync_status{sync_status="OutOfSync"} == 1
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "ArgoCD application {{ $labels.name }} is OutOfSync"
        description: "Application {{ $labels.name }} in namespace {{ $labels.namespace }} has been OutOfSync for more than 5 minutes"

    - alert: ArgoCDApplicationDegraded
      expr: argocd_app_health_status{health_status="Degraded"} == 1
      for: 10m
      labels:
        severity: critical
      annotations:
        summary: "ArgoCD application {{ $labels.name }} is Degraded"
        description: "Application {{ $labels.name }} in namespace {{ $labels.namespace }} has been Degraded for more than 10 minutes"

    - alert: ArgoCDControllerDown
      expr: up{job="argocd-application-controller-metrics"} == 0
      for: 2m
      labels:
        severity: critical
      annotations:
        summary: "ArgoCD Application Controller is down"
        description: "ArgoCD Application Controller has been down for more than 2 minutes"

    - alert: ArgoCDRepoServerDown
      expr: up{job="argocd-repo-server-metrics"} == 0
      for: 2m
      labels:
        severity: critical
      annotations:
        summary: "ArgoCD Repository Server is down"
        description: "ArgoCD Repository Server has been down for more than 2 minutes"
```

### Warning Alerts
```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: argocd-warning-alerts
  namespace: argocd
spec:
  groups:
  - name: argocd-warning
    rules:
    - alert: ArgoCDApplicationSyncSlow
      expr: histogram_quantile(0.95, rate(argocd_app_sync_duration_seconds_bucket[5m])) > 60
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: "ArgoCD application sync is slow"
        description: "95th percentile of application sync operations taking more than 60 seconds"

    - alert: ArgoCDReconciliationSlow
      expr: histogram_quantile(0.95, rate(argocd_app_reconcile_duration_seconds_bucket[5m])) > 30
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: "ArgoCD application reconciliation is slow"
        description: "95th percentile of application reconciliation operations taking more than 30 seconds"

    - alert: ArgoCDGitOperationSlow
      expr: histogram_quantile(0.95, rate(argocd_git_request_duration_seconds_bucket[5m])) > 10
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: "ArgoCD Git operations are slow"
        description: "95th percentile of Git operations taking more than 10 seconds"
```

## Grafana Dashboards

### ArgoCD Overview Dashboard
```json
{
  "dashboard": {
    "id": null,
    "title": "ArgoCD Overview",
    "tags": ["argocd"],
    "style": "dark",
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "Applications by Health",
        "type": "stat",
        "targets": [
          {
            "expr": "count(argocd_app_health_status{health_status=\"Healthy\"})",
            "legendFormat": "Healthy"
          }
        ],
        "colorMode": "background",
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "thresholds"
            },
            "thresholds": {
              "steps": [
                {
                  "color": "red",
                  "value": null
                },
                {
                  "color": "yellow",
                  "value": 1
                },
                {
                  "color": "green",
                  "value": 1
                }
              ]
            }
          }
        }
      },
      {
        "id": 2,
        "title": "Applications by Sync Status",
        "type": "graph",
        "targets": [
          {
            "expr": "count(argocd_app_sync_status{sync_status=\"Synced\"})",
            "legendFormat": "Synced"
          },
          {
            "expr": "count(argocd_app_sync_status{sync_status=\"OutOfSync\"})",
            "legendFormat": "OutOfSync"
          }
        ]
      }
    ]
  }
}
```

## Logging Configuration

### Log Level Configuration
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cmd-params-cm
  namespace: argocd
data:
  server.log.level: "info"
  controller.log.level: "info"
  reposerver.log.level: "info"
```

### Structured Logging
Enable JSON logging for better parsing:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cmd-params-cm
  namespace: argocd
data:
  server.log.format: "json"
  controller.log.format: "json"
  reposerver.log.format: "json"
```

## Health Checks

### Application Health Checks
ArgoCD provides built-in health checks for common Kubernetes resources:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: health-checked-app
spec:
  source:
    repoURL: https://github.com/org/app-manifests
    targetRevision: HEAD
    path: k8s
  destination:
    server: https://kubernetes.default.svc
    namespace: production
  ignoreDifferences:
  - group: apps
    kind: Deployment
    jsonPointers:
    - /status  # Ignore status field differences
```

### Custom Health Checks
Define custom health check logic in resource customizations:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cmd-params-cm
  namespace: argocd
data:
  resource.customizations.health.argoproj.io_Application: |
    hs = {}
    if obj.status ~= nil then
      if obj.status.health ~= nil then
        hs.status = obj.status.health.status
        if obj.status.health.message ~= nil then
          hs.message = obj.status.health.message
        end
      end
    end
    return hs
```

## Tracing Configuration

### Jaeger Integration
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cmd-params-cm
  namespace: argocd
data:
  server.otlp.endpoint: "jaeger-collector.jaeger.svc.cluster.local:4317"
  controller.otlp.endpoint: "jaeger-collector.jaeger.svc.cluster.local:4317"
```

## Audit Trail

### Audit Events
ArgoCD emits audit events for important operations. Monitor these events:

- `ApplicationCreated` - When an application is created
- `ApplicationUpdated` - When an application is updated
- `ApplicationDeleted` - When an application is deleted
- `ApplicationSync` - When an application sync is initiated
- `ApplicationComparison` - When application comparison is performed

## Troubleshooting Commands

### Check Application Health
```bash
# Get detailed application information
argocd app get <APP_NAME> --show-operation --show-resource-tree

# Check application resource health
argocd app resources <APP_NAME>

# Compare application state
argocd app diff <APP_NAME>
```

### Check Controller Logs
```bash
# Check application controller logs
kubectl logs -n argocd deployment/argocd-application-controller

# Check repository server logs
kubectl logs -n argocd deployment/argocd-repo-server

# Check API server logs
kubectl logs -n argocd deployment/argocd-server
```

### Metrics Queries
```bash
# Check sync status across all applications
kubectl exec -n argocd deployment/argocd-application-controller -- curl -s localhost:8082/metrics | grep argocd_app_sync_status

# Check health status across all applications
kubectl exec -n argocd deployment/argocd-application-controller -- curl -s localhost:8082/metrics | grep argocd_app_health_status
```

## Performance Monitoring

### Resource Utilization
Monitor ArgoCD component resource utilization:

```bash
# Check resource usage
kubectl top pods -n argocd

# Check resource limits
kubectl describe pods -n argocd
```

### Performance Tuning Metrics
Track these metrics for performance tuning:

- `argocd_app_reconcile_duration_seconds` - Reconciliation performance
- `argocd_git_request_duration_seconds` - Git operation performance
- `argocd_kubectl_exec_pending` - Pending operations
- `workqueue_depth` - Work queue depth for each controller