# Kubernetes Deployments Reference

## What is a Deployment?

A **Deployment** manages a set of Pods to run an application workload. It provides declarative updates for Pods and ReplicaSets, allowing you to describe a desired state and have the Deployment Controller change the actual state at a controlled rate.

## Key Use Cases

- Rollout a ReplicaSet and manage Pods
- Declare new Pod state via PodTemplateSpec updates
- Rollback to earlier Deployment revisions
- Scale up/down to handle varying loads
- Pause and resume rollouts for applying multiple fixes

## Basic Deployment YAML

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
  labels:
    app: nginx
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.14.2
        ports:
        - containerPort: 80
```

## Key Fields

| Field | Description |
|-------|-------------|
| `.metadata.name` | Deployment name (basis for ReplicaSets and Pods) |
| `.spec.replicas` | Desired number of Pod replicas |
| `.spec.selector` | How the ReplicaSet finds Pods to manage |
| `.spec.template` | Pod template specification |
| `.spec.template.metadata.labels` | Labels applied to Pods |
| `.spec.template.spec.containers` | Container definitions |

## Essential Commands

```bash
# Create deployment
kubectl apply -f deployment.yaml

# Check status
kubectl get deployments
kubectl rollout status deployment/nginx-deployment

# View ReplicaSets
kubectl get rs

# View Pods with labels
kubectl get pods --show-labels
```

## Updating a Deployment

A rollout is triggered **only** when Pod template (`.spec.template`) changes.

```bash
# Update container image
kubectl set image deployment/nginx-deployment nginx=nginx:1.16.1

# Edit deployment directly
kubectl edit deployment/nginx-deployment

# Monitor rollout
kubectl rollout status deployment/nginx-deployment
```

## Rolling Back

```bash
# View rollout history
kubectl rollout history deployment/nginx-deployment

# Rollback to previous revision
kubectl rollout undo deployment/nginx-deployment

# Rollback to specific revision
kubectl rollout undo deployment/nginx-deployment --to-revision=2
```

## Scaling

```bash
# Manual scaling
kubectl scale deployment nginx-deployment --replicas=10

# Set up autoscaling
kubectl autoscale deployment nginx-deployment --min=3 --max=10
```

## Pausing and Resuming

```bash
# Pause rollout
kubectl rollout pause deployment/nginx-deployment

# Apply multiple changes
kubectl set image deployment/nginx-deployment nginx=nginx:1.16.2
kubectl set resources deployment/nginx-deployment -c=nginx --limits=cpu=200m,memory=512Mi

# Resume rollout
kubectl rollout resume deployment/nginx-deployment
```

## Deployment Strategies

### RollingUpdate (Default)

```yaml
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 25%         # or absolute number like 1
      maxUnavailable: 25%   # or absolute number like 1
```

| Parameter | Description | Default |
|-----------|-------------|---------|
| `maxSurge` | Max pods over desired count during update | 25% |
| `maxUnavailable` | Max pods that can be unavailable | 25% |

**Example with 4 replicas:**
- `maxSurge: 1` → Can have up to 5 pods during update
- `maxUnavailable: 1` → Must have at least 3 available pods

**Rolling Update Visualization:**
```
replicas: 4, maxSurge: 1, maxUnavailable: 1

Initial:  [v1] [v1] [v1] [v1]           (4 pods, all v1)
Step 1:   [v1] [v1] [v1] [--] [v2]      (terminate 1, create 1)
Step 2:   [v1] [v1] [--] [v2] [v2]      (continue rolling)
Step 3:   [v1] [--] [v2] [v2] [v2]      (continue rolling)
Step 4:   [v2] [v2] [v2] [v2]           (complete)
```

### Recreate Strategy

```yaml
spec:
  strategy:
    type: Recreate
```

Terminates all existing Pods before creating new ones.

**Recreate Visualization:**
```
Initial:  [v1] [v1] [v1] [v1]    (4 pods running v1)
Step 1:   [--] [--] [--] [--]    (all terminated - DOWNTIME)
Step 2:   [v2] [v2] [v2] [v2]    (all new pods created)
```

**Use Recreate when:**
- Application cannot run multiple versions simultaneously
- Shared resources require exclusive access
- Database schema migrations
- License restrictions on concurrent instances

### Strategy Comparison

| Aspect | RollingUpdate | Recreate |
|--------|---------------|----------|
| Zero downtime | ✅ Yes | ❌ No |
| Resource usage | Higher (both versions run) | Lower |
| Rollback speed | Fast | Requires full redeploy |
| Version mixing | Brief overlap | Never |
| Use case | Most applications | Stateful, exclusive access |

---

## ReplicaSet Management

### How Deployments Manage ReplicaSets

```
Deployment (nginx-deployment)
    │
    ├── ReplicaSet (nginx-deployment-abc123) ← Current
    │       ├── Pod (nginx-deployment-abc123-xxxxx)
    │       ├── Pod (nginx-deployment-abc123-yyyyy)
    │       └── Pod (nginx-deployment-abc123-zzzzz)
    │
    ├── ReplicaSet (nginx-deployment-def456) ← Previous (scaled to 0)
    │
    └── ReplicaSet (nginx-deployment-ghi789) ← Older (scaled to 0)
```

### ReplicaSet Naming

ReplicaSets are named using: `{deployment-name}-{pod-template-hash}`

The pod-template-hash is generated from the Pod template spec and ensures:
- Each unique Pod template gets its own ReplicaSet
- Rollbacks can reuse existing ReplicaSets

### Revision History

```yaml
spec:
  revisionHistoryLimit: 10  # Default: 10, set to 0 to disable rollback
```

```bash
# View all ReplicaSets (including old ones)
kubectl get rs -l app=nginx

# View revision history
kubectl rollout history deployment/nginx-deployment

# View specific revision
kubectl rollout history deployment/nginx-deployment --revision=2
```

---

## Self-Healing Mechanisms

Kubernetes continuously reconciles actual state with desired state.

### Pod-Level Self-Healing

| Event | Response |
|-------|----------|
| Container crashes | kubelet restarts container (per restartPolicy) |
| Container OOMKilled | kubelet restarts container |
| Liveness probe fails | kubelet kills and restarts container |
| Readiness probe fails | Pod removed from Service endpoints |

### ReplicaSet-Level Self-Healing

| Event | Response |
|-------|----------|
| Pod deleted | ReplicaSet creates replacement |
| Pod fails | ReplicaSet creates replacement |
| Replicas < desired | ReplicaSet scales up |
| Replicas > desired | ReplicaSet scales down |

### Node-Level Self-Healing

| Event | Response |
|-------|----------|
| Node becomes NotReady | Pods marked for eviction after timeout |
| Node unreachable | Pods rescheduled to healthy nodes |
| Node deleted | Pods immediately rescheduled |

### Observing Self-Healing

```bash
# Watch pods recreate after deletion
kubectl get pods -w

# Delete a pod and watch replacement
kubectl delete pod nginx-deployment-abc123-xxxxx

# View events showing self-healing
kubectl describe deployment nginx-deployment
```

---

## Rollout Commands Reference

### Triggering Updates

```bash
# Update container image
kubectl set image deployment/nginx nginx=nginx:1.16.1

# Update environment variable
kubectl set env deployment/nginx ENV=production

# Update resources
kubectl set resources deployment/nginx -c=nginx \
  --requests=cpu=100m,memory=128Mi \
  --limits=cpu=500m,memory=512Mi

# Apply manifest changes
kubectl apply -f deployment.yaml

# Patch deployment
kubectl patch deployment nginx -p \
  '{"spec":{"template":{"spec":{"containers":[{"name":"nginx","image":"nginx:1.16.1"}]}}}}'
```

### Monitoring Rollouts

```bash
# Watch rollout progress (blocks until complete)
kubectl rollout status deployment/nginx

# Check if rollout is complete
kubectl rollout status deployment/nginx --timeout=5m

# View current ReplicaSet and pods
kubectl get rs,pods -l app=nginx
```

### Rolling Back

```bash
# Rollback to previous revision
kubectl rollout undo deployment/nginx

# Rollback to specific revision
kubectl rollout undo deployment/nginx --to-revision=2

# Dry-run rollback (see what would change)
kubectl rollout undo deployment/nginx --dry-run=client -o yaml
```

### Pause and Resume

```bash
# Pause deployment (prevents rollouts)
kubectl rollout pause deployment/nginx

# Make multiple changes
kubectl set image deployment/nginx nginx=nginx:1.17
kubectl set resources deployment/nginx -c=nginx --limits=memory=256Mi
kubectl set env deployment/nginx NEW_VAR=value

# Resume to apply all changes in single rollout
kubectl rollout resume deployment/nginx
```

### Restart Deployment

```bash
# Trigger rolling restart (same image, new pods)
kubectl rollout restart deployment/nginx
```

---

## Complete Production Deployment Example

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: production
  labels:
    app: myapp
    version: v1.0.0
  annotations:
    kubernetes.io/change-cause: "Initial deployment v1.0.0"
spec:
  replicas: 3
  revisionHistoryLimit: 5
  progressDeadlineSeconds: 600
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0  # Zero downtime
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
        version: v1.0.0
    spec:
      containers:
      - name: app
        image: myapp:1.0.0
        ports:
        - containerPort: 8080
          name: http
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi
        livenessProbe:
          httpGet:
            path: /healthz
            port: http
          initialDelaySeconds: 15
          periodSeconds: 10
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: http
          initialDelaySeconds: 5
          periodSeconds: 5
          failureThreshold: 3
        startupProbe:
          httpGet:
            path: /healthz
            port: http
          initialDelaySeconds: 10
          periodSeconds: 10
          failureThreshold: 30
      terminationGracePeriodSeconds: 30
```

---

## Best Practices

1. **Labels**: Use specific, meaningful labels (`app: nginx`)
2. **Selectors**: Don't overlap with other controllers
3. **Image tags**: Always specify image tags (not `latest`)
4. **Declarative**: Use `kubectl apply` for updates
5. **History**: Use `.spec.revisionHistoryLimit` to control retained revisions
6. **Strategy**: Use `maxUnavailable: 0` for true zero-downtime deployments
7. **Health probes**: Always configure liveness and readiness probes
8. **Resources**: Always set requests and limits
9. **Change cause**: Use annotations to document deployment reasons
10. **Progress deadline**: Set `progressDeadlineSeconds` to detect stuck rollouts
