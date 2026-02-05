# Kubernetes Resource Management Reference

## Quick Reference: Resource Failures

| Symptom | Cause | Fix |
|---------|-------|-----|
| Pod `Pending` | Insufficient CPU/memory on nodes | Reduce requests or add nodes |
| Container `OOMKilled` | Exceeded memory limit | Increase limit or fix memory leak |
| Container throttled (slow) | Exceeded CPU limit | Increase CPU limit |
| Pod evicted | Node under memory pressure | Use Guaranteed QoS or increase node resources |

---

## Requests vs Limits

| Type | Purpose | Behavior |
|------|---------|----------|
| **Requests** | Minimum guaranteed resources | Used for scheduling; always available |
| **Limits** | Maximum allowed resources | Enforced at runtime |

```
                    Request          Limit
                       │               │
                       ▼               ▼
    ├──────────────────┼───────────────┼──────────────────►
    0                 100m            500m              CPU

    │    Guaranteed   │    Burstable   │   Throttled    │
    │    (always)     │   (if avail)   │   (capped)     │
```

---

## CPU Units

- 1 CPU = 1 physical/virtual core
- Fractional values allowed
- `m` = millicpu (1000m = 1 CPU)

| Value | Meaning |
|-------|---------|
| `1` | 1 full CPU |
| `0.5` or `500m` | Half a CPU |
| `250m` | Quarter CPU |
| `100m` | One-tenth CPU |

**CPU Enforcement**: Throttling (container is slowed, never killed)

---

## Memory Units

Binary suffixes (recommended):
- `Ki` = kibibyte (1024 bytes)
- `Mi` = mebibyte (1024 Ki)
- `Gi` = gibibyte (1024 Mi)

| Value | Meaning |
|-------|---------|
| `128Mi` | 128 mebibytes |
| `1Gi` | 1 gibibyte |
| `512Mi` | 512 mebibytes |

**Warning**: `400m` = 0.4 bytes (wrong!), `400Mi` = 400 mebibytes (correct!)

**Memory Enforcement**: OOMKilled (container is terminated if exceeded)

---

## QoS Classes

Kubernetes assigns Quality of Service classes based on resource configuration. This determines eviction priority when nodes are under pressure.

### QoS Class Comparison

| Class | Criteria | Eviction Priority | Use Case |
|-------|----------|-------------------|----------|
| **Guaranteed** | requests = limits for ALL resources | Lowest (last to evict) | Critical production workloads |
| **Burstable** | At least one request set, requests ≠ limits | Medium | Standard workloads |
| **BestEffort** | No requests or limits | Highest (first to evict) | Non-critical batch jobs |

### Guaranteed QoS Example

Both CPU and memory must have requests = limits for all containers:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: guaranteed-pod
spec:
  containers:
  - name: app
    image: myapp:1.0
    resources:
      requests:
        cpu: "500m"
        memory: "256Mi"
      limits:
        cpu: "500m"       # Same as request
        memory: "256Mi"   # Same as request
```

**Check QoS class:**
```bash
kubectl get pod guaranteed-pod -o jsonpath='{.status.qosClass}'
# Output: Guaranteed
```

### Burstable QoS Example

At least one container has requests set, but requests ≠ limits:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: burstable-pod
spec:
  containers:
  - name: app
    image: myapp:1.0
    resources:
      requests:
        cpu: "100m"
        memory: "128Mi"
      limits:
        cpu: "500m"       # Different from request (can burst)
        memory: "512Mi"   # Different from request (can burst)
```

### BestEffort QoS Example

No resources specified (not recommended for production):

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: besteffort-pod
spec:
  containers:
  - name: app
    image: myapp:1.0
    # No resources block - BestEffort QoS
```

### QoS Selection Guide

```
What's your workload priority?
│
├─ Critical (database, API gateway)
│   └─ Use Guaranteed: requests = limits
│
├─ Standard (web apps, microservices)
│   └─ Use Burstable: set requests, higher limits
│
└─ Non-critical (batch jobs, dev/test)
    └─ BestEffort acceptable (but still set requests)
```

---

## Failure States and Diagnosis

### OOMKilled (Exit Code 137)

Container exceeded memory limit and was terminated.

**Symptoms:**
```bash
kubectl describe pod <pod-name>
# Last State:     Terminated
#   Reason:       OOMKilled
#   Exit Code:    137
```

**Diagnosis:**
```bash
# Check memory limits
kubectl get pod <pod-name> -o jsonpath='{.spec.containers[*].resources.limits.memory}'

# Check actual usage (requires metrics-server)
kubectl top pod <pod-name>

# Check for memory pressure events
kubectl describe pod <pod-name> | grep -i oom
```

**Fixes:**

1. **Increase memory limit** (if app needs more):
```yaml
resources:
  limits:
    memory: "512Mi"  # Increase from 256Mi
```

2. **Fix memory leak** (if app is buggy):
   - Review application code
   - Add memory bounds/cleanup

3. **Configure JVM/runtime** (for Java, Node.js):
```yaml
env:
- name: JAVA_OPTS
  value: "-Xms256m -Xmx400m"  # Set heap ~80% of limit
resources:
  limits:
    memory: "512Mi"
```

### CPU Throttling (Container Slow)

Container hitting CPU limit, being throttled.

**Symptoms:**
- Application is slow/unresponsive
- High latency in responses
- No crashes or restarts

**Diagnosis:**
```bash
# Check CPU usage vs limits
kubectl top pod <pod-name>

# Check container metrics (if prometheus available)
# container_cpu_cfs_throttled_seconds_total
```

**Fixes:**

1. **Increase CPU limit**:
```yaml
resources:
  limits:
    cpu: "1000m"  # Increase from 500m
```

2. **Optimize application** for better CPU efficiency

### Pending Due to Resources

Pod cannot be scheduled due to insufficient resources.

**Symptoms:**
```bash
kubectl get pods
# NAME      READY   STATUS    RESTARTS   AGE
# myapp     0/1     Pending   0          5m
```

**Diagnosis:**
```bash
kubectl describe pod <pod-name>
# Events:
#   Warning  FailedScheduling  Insufficient cpu
#   Warning  FailedScheduling  Insufficient memory
```

**Fixes:**

1. **Reduce requests**:
```yaml
resources:
  requests:
    cpu: "100m"      # Reduce from 500m
    memory: "128Mi"  # Reduce from 512Mi
```

2. **Add more nodes** to the cluster

3. **Check node capacity**:
```bash
kubectl describe nodes | grep -A5 "Allocated resources"
```

### Evicted Pods

Pod removed from node due to resource pressure.

**Symptoms:**
```bash
kubectl get pods
# NAME      READY   STATUS    RESTARTS   AGE
# myapp     0/1     Evicted   0          1h
```

**Diagnosis:**
```bash
kubectl describe pod <pod-name>
# Status:       Failed
# Reason:       Evicted
# Message:      The node was low on resource: memory
```

**Fixes:**

1. **Use Guaranteed QoS** (set requests = limits)
2. **Reduce resource usage** of other pods
3. **Add node resources** or more nodes
4. **Set PriorityClass** for critical pods

---

## Resource Enforcement Behavior

### CPU Limits

```
┌─────────────────────────────────────────────────────────┐
│ CPU Enforcement                                          │
│                                                          │
│  Request: 100m    Limit: 500m                           │
│  ─────────────────────────────────────────────────────  │
│                                                          │
│  Usage: 100m  │ Guaranteed - always available           │
│  Usage: 300m  │ Burstable - using available capacity    │
│  Usage: 500m  │ At limit - throttled if exceeded        │
│  Usage: 600m  │ THROTTLED - capped at 500m              │
│                                                          │
│  ✓ Container is NEVER killed for CPU                    │
└─────────────────────────────────────────────────────────┘
```

### Memory Limits

```
┌─────────────────────────────────────────────────────────┐
│ Memory Enforcement                                       │
│                                                          │
│  Request: 128Mi   Limit: 256Mi                          │
│  ─────────────────────────────────────────────────────  │
│                                                          │
│  Usage: 128Mi │ Within request - safe                   │
│  Usage: 200Mi │ Within limit - ok                       │
│  Usage: 256Mi │ At limit - danger zone                  │
│  Usage: 260Mi │ OOMKilled! Container terminated         │
│                                                          │
│  ✗ Container IS killed if memory exceeded               │
└─────────────────────────────────────────────────────────┘
```

---

## Basic Resource Specification

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: resource-demo
spec:
  containers:
  - name: app
    image: myapp:1.0
    resources:
      requests:
        memory: "64Mi"
        cpu: "250m"
      limits:
        memory: "128Mi"
        cpu: "500m"
```

---

## Multi-Container Pod Resources

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: frontend
spec:
  containers:
  - name: app
    image: myapp:1.0
    resources:
      requests:
        memory: "64Mi"
        cpu: "250m"
      limits:
        memory: "128Mi"
        cpu: "500m"
  - name: log-aggregator
    image: log-aggregator:1.0
    resources:
      requests:
        memory: "64Mi"
        cpu: "250m"
      limits:
        memory: "128Mi"
        cpu: "500m"
```

**Pod Totals**: Request: 0.5 CPU, 128Mi | Limit: 1 CPU, 256Mi

---

## Complete Deployment Example

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      containers:
      - name: app
        image: myapp:1.0
        ports:
        - containerPort: 8080
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi
```

---

## Resource Quotas (Namespace-level)

Limit total resources consumed by all pods in a namespace:

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: compute-quota
  namespace: production
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    pods: "50"
```

---

## LimitRange (Default Resources)

Set default resources for pods that don't specify them:

```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: default-limits
  namespace: production
spec:
  limits:
  - default:          # Default limits
      cpu: 500m
      memory: 256Mi
    defaultRequest:   # Default requests
      cpu: 100m
      memory: 128Mi
    max:              # Maximum allowed
      cpu: 2
      memory: 2Gi
    min:              # Minimum allowed
      cpu: 50m
      memory: 32Mi
    type: Container
```

---

## Priority Classes

Control scheduling and eviction priority:

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 1000000
globalDefault: false
description: "High priority for critical workloads"
---
apiVersion: v1
kind: Pod
metadata:
  name: critical-pod
spec:
  priorityClassName: high-priority
  containers:
  - name: app
    image: myapp:1.0
    resources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        cpu: 100m
        memory: 128Mi
```

---

## Essential Commands

```bash
# View node resources and allocation
kubectl describe nodes
kubectl describe nodes | grep -A10 "Allocated resources"

# View pod resource usage (requires metrics-server)
kubectl top pods
kubectl top pod <pod-name>
kubectl top pods --sort-by=memory

# View node resource usage
kubectl top nodes

# Check pod QoS class
kubectl get pod <pod-name> -o jsonpath='{.status.qosClass}'

# View resource quotas
kubectl get resourcequota -n production
kubectl describe resourcequota compute-quota -n production

# View limit ranges
kubectl get limitrange -n production
kubectl describe limitrange default-limits -n production

# Check why pod is pending
kubectl describe pod <pod-name> | grep -A5 "Events"

# Check for OOMKilled
kubectl describe pod <pod-name> | grep -i "oom\|killed\|exit code"
```

---

## Debugging Workflow for Resource Issues

```bash
# Step 1: Check pod status
kubectl get pods

# Step 2: If Pending, check scheduling issues
kubectl describe pod <pod-name> | grep -A10 "Events"

# Step 3: If OOMKilled, check memory
kubectl describe pod <pod-name> | grep -A5 "Last State"
kubectl top pod <pod-name>

# Step 4: Check node capacity
kubectl describe nodes | grep -A10 "Allocated resources"

# Step 5: Check quotas in namespace
kubectl describe resourcequota -n <namespace>
```

---

## Best Practices

1. **Always set requests** for proper scheduling
2. **Always set limits** for resource safety
3. **Use Guaranteed QoS** for critical workloads (requests = limits)
4. **Use millicpu** (`m`) for CPU values under 1
5. **Use binary notation** (`Mi`, `Gi`) for memory
6. **Set JVM/runtime heap** below container memory limit (~80%)
7. **Use ResourceQuotas** for multi-tenant clusters
8. **Use LimitRanges** to enforce defaults and prevent unbounded resources
9. **Monitor actual usage** with `kubectl top` before right-sizing
10. **Use PriorityClasses** for critical workloads to avoid eviction
