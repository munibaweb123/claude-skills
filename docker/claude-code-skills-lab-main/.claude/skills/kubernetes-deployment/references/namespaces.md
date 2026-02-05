# Kubernetes Namespaces Reference

## What are Namespaces?

Namespaces isolate groups of resources within a cluster. They:
- Partition resources between users/teams
- Scope resource names (unique within namespace)
- Enable resource quotas per namespace
- Provide security boundaries with RBAC

---

## Initial Namespaces

| Namespace | Purpose |
|-----------|---------|
| `default` | Default for resources without namespace |
| `kube-system` | Kubernetes system components |
| `kube-public` | Publicly readable resources |
| `kube-node-lease` | Node heartbeat leases |

---

## Creating Namespaces

### YAML

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: production
  labels:
    environment: production
    team: backend
```

### Command

```bash
kubectl create namespace production
```

---

## Namespace Isolation Pattern

A complete namespace setup includes three components:

```
┌─────────────────────────────────────────────────────────────┐
│                      Namespace                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │  ResourceQuota  │  │   LimitRange    │  │   Network   │ │
│  │                 │  │                 │  │   Policy    │ │
│  │ Total limits    │  │ Per-container   │  │             │ │
│  │ for namespace   │  │ defaults/limits │  │ Traffic     │ │
│  │                 │  │                 │  │ isolation   │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Complete Namespace Setup Example

```yaml
# 1. Namespace
apiVersion: v1
kind: Namespace
metadata:
  name: dev
  labels:
    environment: development
---
# 2. ResourceQuota - Total namespace limits
apiVersion: v1
kind: ResourceQuota
metadata:
  name: dev-quota
  namespace: dev
spec:
  hard:
    requests.cpu: "4"
    requests.memory: 8Gi
    limits.cpu: "8"
    limits.memory: 16Gi
    pods: "20"
    services: "10"
    configmaps: "20"
    secrets: "20"
    persistentvolumeclaims: "5"
---
# 3. LimitRange - Per-container defaults and constraints
apiVersion: v1
kind: LimitRange
metadata:
  name: dev-limits
  namespace: dev
spec:
  limits:
  - type: Container
    default:
      cpu: 500m
      memory: 256Mi
    defaultRequest:
      cpu: 100m
      memory: 128Mi
    min:
      cpu: 50m
      memory: 64Mi
    max:
      cpu: 2
      memory: 2Gi
  - type: Pod
    max:
      cpu: 4
      memory: 4Gi
  - type: PersistentVolumeClaim
    min:
      storage: 1Gi
    max:
      storage: 10Gi
```

---

## ResourceQuota Configuration

### Compute Resource Quotas

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: compute-quota
  namespace: production
spec:
  hard:
    # CPU quotas
    requests.cpu: "20"        # Total CPU requests
    limits.cpu: "40"          # Total CPU limits

    # Memory quotas
    requests.memory: 40Gi     # Total memory requests
    limits.memory: 80Gi       # Total memory limits
```

### Object Count Quotas

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: object-quota
  namespace: production
spec:
  hard:
    # Core objects
    pods: "100"
    services: "20"
    configmaps: "50"
    secrets: "50"
    replicationcontrollers: "20"

    # Workload objects
    count/deployments.apps: "20"
    count/replicasets.apps: "40"
    count/statefulsets.apps: "10"
    count/jobs.batch: "20"
    count/cronjobs.batch: "10"

    # Service types
    services.nodeports: "5"
    services.loadbalancers: "2"
```

### Storage Quotas

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: storage-quota
  namespace: production
spec:
  hard:
    # Total storage
    requests.storage: 100Gi
    persistentvolumeclaims: "20"

    # Per storage class (if using storage classes)
    requests.storage.standard: 50Gi
    requests.storage.fast-ssd: 20Gi
```

### Scoped Quotas (by Priority Class)

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: high-priority-quota
  namespace: production
spec:
  hard:
    pods: "10"
    requests.cpu: "10"
    requests.memory: 20Gi
  scopeSelector:
    matchExpressions:
    - operator: In
      scopeName: PriorityClass
      values:
      - high-priority
```

---

## LimitRange Configuration

### Container Limits

```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: container-limits
  namespace: production
spec:
  limits:
  - type: Container
    # Default limits (applied if not specified)
    default:
      cpu: 500m
      memory: 512Mi
    # Default requests (applied if not specified)
    defaultRequest:
      cpu: 100m
      memory: 128Mi
    # Minimum allowed
    min:
      cpu: 50m
      memory: 64Mi
    # Maximum allowed
    max:
      cpu: 4
      memory: 8Gi
    # Max ratio of limit/request
    maxLimitRequestRatio:
      cpu: 10
      memory: 4
```

### Pod Limits

```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: pod-limits
  namespace: production
spec:
  limits:
  - type: Pod
    max:
      cpu: 8
      memory: 16Gi
    min:
      cpu: 100m
      memory: 128Mi
```

### PVC Limits

```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: pvc-limits
  namespace: production
spec:
  limits:
  - type: PersistentVolumeClaim
    min:
      storage: 1Gi
    max:
      storage: 50Gi
```

### How LimitRange Works

```
Pod Creation Request
        │
        ▼
┌───────────────────────────────────────┐
│         LimitRange Admission          │
├───────────────────────────────────────┤
│ 1. No resources specified?            │
│    → Apply defaultRequest & default   │
│                                       │
│ 2. Below minimum?                     │
│    → REJECT pod creation              │
│                                       │
│ 3. Above maximum?                     │
│    → REJECT pod creation              │
│                                       │
│ 4. Limit/Request ratio exceeded?      │
│    → REJECT pod creation              │
└───────────────────────────────────────┘
        │
        ▼
   Pod Created (or Rejected)
```

---

## Cross-Namespace DNS

### DNS Record Format

```
<service-name>.<namespace>.svc.cluster.local
```

### DNS Resolution Patterns

```yaml
# From a pod in namespace "frontend"
# accessing services in different namespaces

apiVersion: v1
kind: Pod
metadata:
  name: frontend-app
  namespace: frontend
spec:
  containers:
  - name: app
    image: frontend:1.0
    env:
    # Same namespace - short name works
    - name: CACHE_URL
      value: "redis://redis-cache:6379"

    # Different namespace - use full DNS
    - name: API_URL
      value: "http://api-service.backend.svc.cluster.local:8080"

    - name: DATABASE_URL
      value: "postgres://db-service.database.svc.cluster.local:5432/mydb"

    - name: AUTH_URL
      value: "http://auth-service.auth.svc.cluster.local:8000"
```

### DNS Shortcuts

| From namespace | Target | DNS name |
|----------------|--------|----------|
| Same | `my-svc` | `my-svc` |
| Same | `my-svc` | `my-svc.my-ns` |
| Different | `my-svc` in `other-ns` | `my-svc.other-ns` |
| Any | Full FQDN | `my-svc.other-ns.svc.cluster.local` |

### Cross-Namespace Service Access Example

```yaml
# Database in 'database' namespace
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: database
spec:
  selector:
    app: postgres
  ports:
  - port: 5432
---
# Application in 'backend' namespace accessing the database
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-server
  namespace: backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api-server
  template:
    metadata:
      labels:
        app: api-server
    spec:
      containers:
      - name: api
        image: api-server:1.0
        env:
        - name: DATABASE_HOST
          value: "postgres.database.svc.cluster.local"
        - name: DATABASE_PORT
          value: "5432"
```

### ExternalName for Cross-Namespace Aliases

Create a local alias to a service in another namespace:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: database        # Local name in this namespace
  namespace: backend
spec:
  type: ExternalName
  externalName: postgres.database.svc.cluster.local
```

Now pods in `backend` can use `database:5432` instead of the full DNS name.

---

## Multi-Environment Namespace Strategies

### Strategy 1: Environment-Based Namespaces

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│     dev     │  │   staging   │  │    prod     │
├─────────────┤  ├─────────────┤  ├─────────────┤
│ Low quotas  │  │ Medium      │  │ High quotas │
│ Relaxed     │  │ quotas      │  │ Strict      │
│ limits      │  │             │  │ limits      │
└─────────────┘  └─────────────┘  └─────────────┘
```

```yaml
# dev-namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: dev
  labels:
    environment: development
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: dev-quota
  namespace: dev
spec:
  hard:
    requests.cpu: "4"
    requests.memory: 8Gi
    limits.cpu: "8"
    limits.memory: 16Gi
    pods: "30"
---
apiVersion: v1
kind: LimitRange
metadata:
  name: dev-limits
  namespace: dev
spec:
  limits:
  - type: Container
    default:
      cpu: 200m
      memory: 256Mi
    defaultRequest:
      cpu: 50m
      memory: 64Mi
    max:
      cpu: 1
      memory: 1Gi
```

```yaml
# staging-namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: staging
  labels:
    environment: staging
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: staging-quota
  namespace: staging
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    pods: "50"
---
apiVersion: v1
kind: LimitRange
metadata:
  name: staging-limits
  namespace: staging
spec:
  limits:
  - type: Container
    default:
      cpu: 500m
      memory: 512Mi
    defaultRequest:
      cpu: 100m
      memory: 128Mi
    max:
      cpu: 2
      memory: 2Gi
```

```yaml
# prod-namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: prod
  labels:
    environment: production
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: prod-quota
  namespace: prod
spec:
  hard:
    requests.cpu: "50"
    requests.memory: 100Gi
    limits.cpu: "100"
    limits.memory: 200Gi
    pods: "200"
    services.loadbalancers: "5"
---
apiVersion: v1
kind: LimitRange
metadata:
  name: prod-limits
  namespace: prod
spec:
  limits:
  - type: Container
    default:
      cpu: 500m
      memory: 512Mi
    defaultRequest:
      cpu: 200m
      memory: 256Mi
    min:
      cpu: 100m
      memory: 128Mi
    max:
      cpu: 4
      memory: 8Gi
```

### Strategy 2: Team-Based Namespaces

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  team-alpha │  │  team-beta  │  │  team-gamma │
├─────────────┤  ├─────────────┤  ├─────────────┤
│ team: alpha │  │ team: beta  │  │ team: gamma │
│ 10 CPU      │  │ 20 CPU      │  │ 15 CPU      │
│ 20Gi mem    │  │ 40Gi mem    │  │ 30Gi mem    │
└─────────────┘  └─────────────┘  └─────────────┘
```

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: team-alpha
  labels:
    team: alpha
    cost-center: "12345"
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: team-alpha-quota
  namespace: team-alpha
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    pods: "50"
```

### Strategy 3: Application-Based Namespaces

```
┌──────────────────────────────────────────────┐
│                 Application                   │
├──────────────┬──────────────┬───────────────┤
│  app-api     │  app-worker  │  app-database │
│  (stateless) │  (jobs)      │  (stateful)   │
└──────────────┴──────────────┴───────────────┘
```

```yaml
# Shared infrastructure namespace
apiVersion: v1
kind: Namespace
metadata:
  name: shared-services
  labels:
    type: infrastructure
---
# Application-specific namespaces
apiVersion: v1
kind: Namespace
metadata:
  name: ecommerce-api
  labels:
    app: ecommerce
    component: api
---
apiVersion: v1
kind: Namespace
metadata:
  name: ecommerce-workers
  labels:
    app: ecommerce
    component: workers
```

### Environment Quotas Comparison

| Resource | Dev | Staging | Prod |
|----------|-----|---------|------|
| CPU Requests | 4 | 10 | 50 |
| CPU Limits | 8 | 20 | 100 |
| Memory Requests | 8Gi | 20Gi | 100Gi |
| Memory Limits | 16Gi | 40Gi | 200Gi |
| Pods | 30 | 50 | 200 |
| Default CPU | 200m | 500m | 500m |
| Default Memory | 256Mi | 512Mi | 512Mi |
| Max CPU/container | 1 | 2 | 4 |
| Max Memory/container | 1Gi | 2Gi | 8Gi |

---

## Quota Enforcement and Troubleshooting

### How Quota Enforcement Works

```
Pod Creation Request
        │
        ▼
┌───────────────────────────────────────┐
│      ResourceQuota Admission          │
├───────────────────────────────────────┤
│ 1. Calculate new total usage          │
│    (current + requested)              │
│                                       │
│ 2. Compare against quota limits       │
│                                       │
│ 3. If exceeded → REJECT               │
│    If within → ALLOW                  │
└───────────────────────────────────────┘
```

### Common Quota Errors

#### Error: Exceeded CPU quota

```
Error from server (Forbidden): pods "my-pod" is forbidden:
exceeded quota: compute-quota, requested: requests.cpu=500m,
used: requests.cpu=3500m, limited: requests.cpu=4
```

**Solution:**
```bash
# Check current usage
kubectl describe quota -n dev

# Either reduce pod requests or increase quota
kubectl edit resourcequota compute-quota -n dev
```

#### Error: Exceeded pod count

```
Error from server (Forbidden): pods "my-pod" is forbidden:
exceeded quota: object-quota, requested: pods=1,
used: pods=30, limited: pods=30
```

**Solution:**
```bash
# Delete unused pods
kubectl delete pod <unused-pod> -n dev

# Or increase pod limit
kubectl patch resourcequota object-quota -n dev \
  --type='json' -p='[{"op": "replace", "path": "/spec/hard/pods", "value": "50"}]'
```

#### Error: No resources specified (with quota)

```
Error from server (Forbidden): pods "my-pod" is forbidden:
failed quota: compute-quota: must specify requests.cpu, requests.memory
```

**Solution:** When ResourceQuota is set, pods must specify resource requests.

```yaml
# Add LimitRange to provide defaults
apiVersion: v1
kind: LimitRange
metadata:
  name: default-limits
  namespace: dev
spec:
  limits:
  - type: Container
    defaultRequest:
      cpu: 100m
      memory: 128Mi
    default:
      cpu: 500m
      memory: 256Mi
```

### Troubleshooting Commands

```bash
# View all quotas in namespace
kubectl get resourcequota -n production

# Detailed quota usage
kubectl describe resourcequota -n production

# View limit ranges
kubectl get limitrange -n production
kubectl describe limitrange -n production

# Check why pod failed
kubectl describe pod <pod-name> -n production

# View events for quota issues
kubectl get events -n production --field-selector reason=FailedCreate

# Check namespace resource usage
kubectl top pods -n production
kubectl top pods -n production --sum
```

### Quota Status Check Script

```bash
#!/bin/bash
# check-quota.sh <namespace>

NAMESPACE=${1:-default}

echo "=== ResourceQuotas in $NAMESPACE ==="
kubectl get resourcequota -n $NAMESPACE -o custom-columns=\
NAME:.metadata.name,\
CPU_REQ:.status.used.requests\\.cpu,\
CPU_REQ_LIMIT:.status.hard.requests\\.cpu,\
MEM_REQ:.status.used.requests\\.memory,\
MEM_REQ_LIMIT:.status.hard.requests\\.memory,\
PODS:.status.used.pods,\
PODS_LIMIT:.status.hard.pods

echo -e "\n=== LimitRanges in $NAMESPACE ==="
kubectl describe limitrange -n $NAMESPACE

echo -e "\n=== Current Pod Resource Usage ==="
kubectl top pods -n $NAMESPACE --no-headers 2>/dev/null || echo "Metrics server not available"
```

---

## Working with Namespaces

```bash
# List namespaces
kubectl get namespaces

# Set default namespace
kubectl config set-context --current --namespace=production

# Run command in specific namespace
kubectl get pods -n production
kubectl get pods --namespace=production

# View resources across all namespaces
kubectl get pods --all-namespaces
kubectl get pods -A

# Apply manifests to namespace
kubectl apply -f manifest.yaml -n production
```

---

## Namespaced vs Cluster-Scoped

```bash
# Namespaced resources
kubectl api-resources --namespaced=true

# Cluster-scoped resources
kubectl api-resources --namespaced=false
```

| Namespaced | Cluster-Scoped |
|------------|----------------|
| Pods | Nodes |
| Services | PersistentVolumes |
| Deployments | StorageClasses |
| ConfigMaps | ClusterRoles |
| Secrets | Namespaces |
| ResourceQuotas | ClusterRoleBindings |
| LimitRanges | |

---

## Essential Commands

```bash
# Create namespace
kubectl create namespace my-namespace

# Delete namespace (deletes all resources in it!)
kubectl delete namespace my-namespace

# Set default namespace
kubectl config set-context --current --namespace=my-namespace

# View current namespace
kubectl config view --minify | grep namespace

# Apply to namespace
kubectl apply -f manifest.yaml -n production

# Create quota
kubectl create quota my-quota --hard=pods=10,requests.cpu=4 -n dev

# View quota usage
kubectl describe quota -n dev
```

---

## Best Practices

1. **Avoid `default` namespace** in production
2. **Use namespaces** for environment separation (dev/staging/prod)
3. **Don't prefix with `kube-`** (reserved for system)
4. **Always set ResourceQuotas** for multi-tenant clusters
5. **Always set LimitRanges** to provide defaults and prevent resource abuse
6. **Use labels** for fine-grained organization within namespace
7. **Document cross-namespace dependencies** for service discovery
8. **Set appropriate quotas per environment** (lower for dev, higher for prod)
9. **Monitor quota usage** to prevent deployment failures
10. **Use RBAC** to restrict namespace access per team
