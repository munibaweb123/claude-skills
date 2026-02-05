# Kubernetes Troubleshooting Reference

## Quick Diagnosis Decision Tree

```
Pod not working?
│
├─ What status does `kubectl get pods` show?
│   │
│   ├─ Pending → See "Pending Pod Debugging"
│   │
│   ├─ CrashLoopBackOff → See "CrashLoopBackOff Debugging"
│   │
│   ├─ ImagePullBackOff → See "Image Pull Errors"
│   │
│   ├─ OOMKilled → See "OOMKilled Debugging"
│   │
│   ├─ CreateContainerConfigError → See "Configuration Errors"
│   │
│   └─ Running but not working → See "Running Pod Issues"
│
└─ Service not accessible? → See "Service Debugging"
```

---

## Universal Debugging Workflow

Always start with these commands:

```bash
# Step 1: Get Pod status
kubectl get pods -o wide

# Step 2: Get detailed info and events
kubectl describe pod <pod-name>

# Step 3: Check logs
kubectl logs <pod-name>
kubectl logs <pod-name> --previous  # If container restarted

# Step 4: Interactive inspection (if running)
kubectl exec -it <pod-name> -- /bin/sh
```

---

## CrashLoopBackOff Debugging

### What It Means

The container starts, crashes, Kubernetes restarts it, it crashes again. The backoff time increases with each restart (10s, 20s, 40s, up to 5 minutes).

### Debugging Workflow

```bash
# 1. Check pod status and restart count
kubectl get pod <pod-name>

# 2. Get events and container state
kubectl describe pod <pod-name>

# 3. Check current logs
kubectl logs <pod-name>

# 4. Check previous container logs (critical!)
kubectl logs <pod-name> --previous

# 5. If multi-container pod, specify container
kubectl logs <pod-name> -c <container-name> --previous
```

### Common Causes and Fixes

| Cause | Symptoms | Fix |
|-------|----------|-----|
| **Missing environment variable** | `KeyError`, `undefined variable` in logs | Add env var via ConfigMap/Secret |
| **Missing ConfigMap/Secret** | `CreateContainerConfigError` or immediate crash | Create the missing resource |
| **Application error** | Stack trace in logs | Fix application code |
| **Wrong command/args** | `executable not found`, `no such file` | Fix command/args in manifest |
| **Permission denied** | `Permission denied` in logs | Fix securityContext or file permissions |
| **Port already in use** | `Address already in use` | Change containerPort or fix conflicts |
| **Health probe failing** | Restarts after initial delay | Fix probe path/port or increase thresholds |
| **Dependency not ready** | Connection refused to database/service | Add init container to wait for dependency |

### Example: Missing Environment Variable

**Error in logs:**
```
KeyError: 'DATABASE_URL'
```

**Fix:**
```yaml
spec:
  containers:
  - name: app
    image: myapp:1.0
    env:
    - name: DATABASE_URL
      valueFrom:
        secretKeyRef:
          name: db-secret
          key: url
```

### Example: Add Dependency Wait

```yaml
spec:
  initContainers:
  - name: wait-for-db
    image: busybox:1.36
    command: ['sh', '-c', 'until nc -z db-service 5432; do sleep 2; done']
  containers:
  - name: app
    image: myapp:1.0
```

---

## OOMKilled Debugging

### What It Means

Container exceeded its memory limit and was terminated by the kernel.

### Debugging Workflow

```bash
# 1. Confirm OOMKilled
kubectl describe pod <pod-name> | grep -A5 "Last State"

# 2. Check current memory usage (requires metrics-server)
kubectl top pod <pod-name>

# 3. Check memory limits
kubectl get pod <pod-name> -o jsonpath='{.spec.containers[*].resources}'
```

### Common Causes and Fixes

| Cause | Fix |
|-------|-----|
| **Memory limit too low** | Increase `resources.limits.memory` |
| **Memory leak in application** | Fix application code, add memory bounds |
| **JVM heap not configured** | Set `-Xmx` to match container limit |
| **Loading too much data** | Implement pagination/streaming |

### Example: Increase Memory Limit

```yaml
resources:
  requests:
    memory: "256Mi"
  limits:
    memory: "512Mi"  # Increase from previous value
```

### Example: JVM Configuration

```yaml
env:
- name: JAVA_OPTS
  value: "-Xms256m -Xmx400m"  # Keep ~20% buffer below limit
resources:
  limits:
    memory: "512Mi"
```

---

## Pending Pod Debugging

### What It Means

Pod accepted but not scheduled to a node.

### Debugging Workflow

```bash
# 1. Check events for scheduling failures
kubectl describe pod <pod-name>

# Look for events like:
# - FailedScheduling
# - Insufficient cpu/memory
# - node(s) had taint

# 2. Check node resources
kubectl describe nodes | grep -A5 "Allocated resources"

# 3. Check node taints
kubectl get nodes -o custom-columns=NAME:.metadata.name,TAINTS:.spec.taints
```

### Common Causes and Fixes

| Cause | Symptoms | Fix |
|-------|----------|-----|
| **Insufficient resources** | `Insufficient cpu` or `Insufficient memory` | Reduce requests or add nodes |
| **Node selector mismatch** | `node(s) didn't match node selector` | Fix nodeSelector or label nodes |
| **Taint/toleration** | `node(s) had taint` | Add toleration or remove taint |
| **PVC not bound** | `persistentvolumeclaim not bound` | Create PV or check storage class |
| **Image pull pending** | Shows Pending then ImagePullBackOff | See Image Pull Errors section |

### Example: Reduce Resource Requests

```yaml
# Before: Too high for available nodes
resources:
  requests:
    cpu: "4"
    memory: "8Gi"

# After: Reasonable for scheduling
resources:
  requests:
    cpu: "500m"
    memory: "512Mi"
```

### Example: Add Toleration

```yaml
spec:
  tolerations:
  - key: "node-role.kubernetes.io/master"
    operator: "Exists"
    effect: "NoSchedule"
```

---

## ImagePullBackOff Debugging

### What It Means

Kubernetes cannot pull the container image.

### Debugging Workflow

```bash
# 1. Check the exact error
kubectl describe pod <pod-name> | grep -A10 "Events"

# 2. Verify image name
kubectl get pod <pod-name> -o jsonpath='{.spec.containers[*].image}'

# 3. Test pull manually (if you have docker)
docker pull <image-name>
```

### Common Causes and Fixes

| Cause | Error Message | Fix |
|-------|--------------|-----|
| **Image doesn't exist** | `repository does not exist` | Fix image name/tag |
| **Private registry no auth** | `unauthorized` | Create and attach imagePullSecret |
| **Wrong tag** | `manifest unknown` | Use existing tag or `latest` |
| **Registry unreachable** | `timeout`, `no such host` | Check network/firewall |

### Example: Add Image Pull Secret

```bash
# Create secret for private registry
kubectl create secret docker-registry my-registry-secret \
  --docker-server=registry.example.com \
  --docker-username=user \
  --docker-password=password
```

```yaml
spec:
  imagePullSecrets:
  - name: my-registry-secret
  containers:
  - name: app
    image: registry.example.com/myapp:1.0
```

---

## CreateContainerConfigError

### What It Means

Container cannot start due to configuration issues.

### Common Causes and Fixes

| Cause | Fix |
|-------|-----|
| **ConfigMap doesn't exist** | Create the ConfigMap |
| **Secret doesn't exist** | Create the Secret |
| **Key not found in ConfigMap/Secret** | Add the key or fix reference |

### Debugging

```bash
# Check which ConfigMap/Secret is missing
kubectl describe pod <pod-name>

# Verify ConfigMap exists
kubectl get configmap <name>

# Verify Secret exists
kubectl get secret <name>

# Check keys in ConfigMap
kubectl get configmap <name> -o yaml
```

---

## Running Pod Issues

### Pod Running But Application Not Working

```bash
# 1. Check if process is running
kubectl exec <pod-name> -- ps aux

# 2. Check application logs
kubectl logs <pod-name> -f

# 3. Test connectivity from inside pod
kubectl exec <pod-name> -- curl localhost:8080/health

# 4. Check environment variables
kubectl exec <pod-name> -- env

# 5. Check mounted files
kubectl exec <pod-name> -- ls -la /etc/config
kubectl exec <pod-name> -- cat /etc/config/app.properties
```

### Health Probe Failures

```bash
# Check probe configuration and failures
kubectl describe pod <pod-name> | grep -A20 "Liveness\|Readiness"
```

**Common fixes:**
- Increase `initialDelaySeconds` for slow-starting apps
- Fix probe `path` or `port`
- Increase `failureThreshold`

---

## Service Debugging

### Service Not Accessible

```bash
# 1. Verify service exists and has endpoints
kubectl get svc <service-name>
kubectl get endpoints <service-name>

# 2. Check if pods match service selector
kubectl get pods -l <selector-from-service>

# 3. Test from another pod
kubectl run debug --rm -it --image=busybox -- wget -qO- http://<service-name>:<port>

# 4. Check if ports match
kubectl get svc <service-name> -o yaml  # Check port and targetPort
kubectl get pod <pod-name> -o yaml      # Check containerPort
```

### Common Causes

| Issue | Fix |
|-------|-----|
| **No endpoints** | Pods don't match selector labels |
| **Port mismatch** | Align service port, targetPort, and containerPort |
| **Pod not ready** | Fix readinessProbe |
| **Wrong service type** | Use LoadBalancer or NodePort for external access |

---

## Quick Reference Commands

```bash
# Get all resources in namespace
kubectl get all -n <namespace>

# Watch pods in real-time
kubectl get pods -w

# Get pod YAML (see full spec)
kubectl get pod <pod-name> -o yaml

# Get events sorted by time
kubectl get events --sort-by='.lastTimestamp'

# Debug with ephemeral container (K8s 1.25+)
kubectl debug <pod-name> -it --image=busybox

# Force delete stuck pod
kubectl delete pod <pod-name> --grace-period=0 --force

# Restart all pods in deployment
kubectl rollout restart deployment/<deployment-name>
```

---

## Troubleshooting Checklist

- [ ] `kubectl get pods` - What's the status?
- [ ] `kubectl describe pod` - Check events section
- [ ] `kubectl logs` - What does the application say?
- [ ] `kubectl logs --previous` - What caused the last crash?
- [ ] `kubectl get events` - Any cluster-level issues?
- [ ] Check resource requests vs node capacity
- [ ] Verify ConfigMaps and Secrets exist
- [ ] Verify image name and tag are correct
- [ ] Check service selector matches pod labels
