# Kubernetes Pods Reference

## Pod Anatomy

A Pod is the smallest deployable unit in Kubernetes, representing one or more containers that share storage and network.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: pod-name              # Required: unique name within namespace
  namespace: default          # Optional: defaults to 'default'
  labels:                     # Optional: key-value pairs for selection
    app: myapp
    version: v1
  annotations:                # Optional: non-identifying metadata
    description: "My application pod"
spec:
  containers: []              # Required: at least one container
  initContainers: []          # Optional: run before main containers
  volumes: []                 # Optional: shared storage
  restartPolicy: Always       # Always | OnFailure | Never
  terminationGracePeriodSeconds: 30
```

---

## Container Specification

### Complete Container Example

```yaml
spec:
  containers:
  - name: app                          # Required
    image: myapp:1.0                   # Required
    imagePullPolicy: IfNotPresent      # Always | IfNotPresent | Never

    # Command and arguments
    command: ["python"]                # Overrides ENTRYPOINT
    args: ["-m", "http.server", "8000"] # Overrides CMD

    # Environment variables
    env:
    - name: APP_ENV
      value: "production"
    - name: SECRET_KEY
      valueFrom:
        secretKeyRef:
          name: app-secrets
          key: secret-key
    - name: CONFIG_VALUE
      valueFrom:
        configMapKeyRef:
          name: app-config
          key: config-value

    # Load all keys from ConfigMap/Secret
    envFrom:
    - configMapRef:
        name: app-config
    - secretRef:
        name: app-secrets

    # Ports
    ports:
    - name: http
      containerPort: 8080
      protocol: TCP                    # TCP | UDP | SCTP

    # Resources (always set these!)
    resources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        cpu: 500m
        memory: 512Mi

    # Volume mounts
    volumeMounts:
    - name: data-volume
      mountPath: /data
      readOnly: false
    - name: config-volume
      mountPath: /etc/config
      readOnly: true

    # Health probes
    livenessProbe:
      httpGet:
        path: /healthz
        port: 8080
      initialDelaySeconds: 10
      periodSeconds: 10
    readinessProbe:
      httpGet:
        path: /ready
        port: 8080
      initialDelaySeconds: 5
      periodSeconds: 5
    startupProbe:
      httpGet:
        path: /healthz
        port: 8080
      failureThreshold: 30
      periodSeconds: 10

    # Security context
    securityContext:
      runAsNonRoot: true
      runAsUser: 1000
      readOnlyRootFilesystem: true
      allowPrivilegeEscalation: false
```

---

## Resource Management

### Requests vs Limits

| Type | Purpose | Enforcement |
|------|---------|-------------|
| **requests** | Minimum guaranteed | Used for scheduling decisions |
| **limits** | Maximum allowed | Enforced at runtime |

### CPU Resources

```yaml
resources:
  requests:
    cpu: 100m      # 0.1 CPU cores (100 millicores)
  limits:
    cpu: 500m      # 0.5 CPU cores
```

**CPU Units:**
- `1` = 1 CPU core (1000 millicores)
- `500m` = 0.5 CPU cores
- `100m` = 0.1 CPU cores

**CPU Enforcement:** Throttling (container is slowed, not killed)

### Memory Resources

```yaml
resources:
  requests:
    memory: 128Mi   # 128 mebibytes
  limits:
    memory: 512Mi   # 512 mebibytes
```

**Memory Units:**
- `Ki` = kibibytes (1024 bytes)
- `Mi` = mebibytes (1024 Ki)
- `Gi` = gibibytes (1024 Mi)

**Memory Enforcement:** OOMKilled (container is terminated if exceeded)

### QoS Classes

| Class | Criteria | Eviction Priority |
|-------|----------|-------------------|
| **Guaranteed** | requests = limits for all resources | Lowest (last to evict) |
| **Burstable** | At least one request/limit set | Medium |
| **BestEffort** | No requests or limits | Highest (first to evict) |

**Best Practice:** Always set both requests and limits for production workloads.

---

## Multi-Container Patterns

### Sidecar Pattern

Extends main container functionality (logging, monitoring, proxying).

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: web-with-sidecar
spec:
  containers:
  # Main application
  - name: web
    image: nginx:1.25
    ports:
    - containerPort: 80
    resources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        cpu: 500m
        memory: 256Mi
    volumeMounts:
    - name: logs
      mountPath: /var/log/nginx

  # Sidecar: ships logs to external system
  - name: log-shipper
    image: fluentd:v1.16
    resources:
      requests:
        cpu: 50m
        memory: 64Mi
      limits:
        cpu: 200m
        memory: 128Mi
    volumeMounts:
    - name: logs
      mountPath: /var/log/nginx
      readOnly: true

  volumes:
  - name: logs
    emptyDir: {}
```

### Ambassador Pattern

Proxies network connections for the main container.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-ambassador
spec:
  containers:
  # Main application connects to localhost:6379
  - name: app
    image: myapp:1.0
    env:
    - name: REDIS_HOST
      value: "localhost"
    resources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        cpu: 500m
        memory: 256Mi

  # Ambassador: proxies to actual Redis cluster
  - name: redis-ambassador
    image: redis-proxy:1.0
    ports:
    - containerPort: 6379
    resources:
      requests:
        cpu: 50m
        memory: 32Mi
      limits:
        cpu: 100m
        memory: 64Mi
```

### Adapter Pattern

Transforms output from the main container.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-adapter
spec:
  containers:
  # Legacy app outputs custom metrics format
  - name: legacy-app
    image: legacy-app:1.0
    resources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        cpu: 500m
        memory: 256Mi
    volumeMounts:
    - name: metrics
      mountPath: /metrics

  # Adapter: converts to Prometheus format
  - name: metrics-adapter
    image: prometheus-adapter:1.0
    ports:
    - containerPort: 9090
    resources:
      requests:
        cpu: 50m
        memory: 32Mi
      limits:
        cpu: 100m
        memory: 64Mi
    volumeMounts:
    - name: metrics
      mountPath: /metrics
      readOnly: true

  volumes:
  - name: metrics
    emptyDir: {}
```

---

## Init Containers

Run to completion before main containers start. Use for setup tasks.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-init
spec:
  initContainers:
  # Wait for database to be ready
  - name: wait-for-db
    image: busybox:1.36
    command: ['sh', '-c', 'until nc -z db-service 5432; do echo waiting; sleep 2; done']
    resources:
      requests:
        cpu: 50m
        memory: 32Mi
      limits:
        cpu: 100m
        memory: 64Mi

  # Download configuration
  - name: download-config
    image: busybox:1.36
    command: ['wget', '-O', '/config/app.conf', 'http://config-server/app.conf']
    volumeMounts:
    - name: config
      mountPath: /config
    resources:
      requests:
        cpu: 50m
        memory: 32Mi
      limits:
        cpu: 100m
        memory: 64Mi

  # Set permissions
  - name: set-permissions
    image: busybox:1.36
    command: ['chmod', '644', '/config/app.conf']
    volumeMounts:
    - name: config
      mountPath: /config
    resources:
      requests:
        cpu: 50m
        memory: 32Mi
      limits:
        cpu: 100m
        memory: 64Mi

  containers:
  - name: app
    image: myapp:1.0
    volumeMounts:
    - name: config
      mountPath: /etc/app
    resources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        cpu: 500m
        memory: 512Mi

  volumes:
  - name: config
    emptyDir: {}
```

**Init Container Rules:**
- Run sequentially in order defined
- Each must complete successfully before next starts
- If any fails, Pod restarts (based on restartPolicy)
- Main containers only start after all init containers complete

---

## Pod Networking

### Network Model

```
┌──────────────────────────────────────────────────────────────┐
│ Node                                                          │
│                                                               │
│  ┌─────────────────────────────────┐  ┌────────────────────┐ │
│  │ Pod A (IP: 10.1.0.10)           │  │ Pod B (IP: 10.1.0.11)│ │
│  │                                 │  │                    │ │
│  │  ┌───────────┐ ┌───────────┐   │  │  ┌───────────┐     │ │
│  │  │Container 1│ │Container 2│   │  │  │Container 1│     │ │
│  │  │  :8080    │ │  :9090    │   │  │  │  :3000    │     │ │
│  │  └───────────┘ └───────────┘   │  │  └───────────┘     │ │
│  │                                 │  │                    │ │
│  │  localhost:8080 ←→ localhost:9090│  │                    │ │
│  └─────────────────────────────────┘  └────────────────────┘ │
│                                                               │
│  Pod A can reach Pod B at 10.1.0.11:3000                     │
└──────────────────────────────────────────────────────────────┘
```

### Key Networking Facts

1. **Shared Network Namespace**: All containers in a Pod share the same IP
2. **Localhost Communication**: Containers communicate via `localhost:<port>`
3. **Unique Ports Required**: Each container must use different ports
4. **Pod-to-Pod**: Pods can reach each other directly by IP
5. **Service Discovery**: Use Services for stable DNS names

### DNS Resolution

```yaml
# Within same namespace
curl http://my-service:8080

# Across namespaces
curl http://my-service.other-namespace:8080

# Fully qualified
curl http://my-service.other-namespace.svc.cluster.local:8080
```

### hostNetwork Mode

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: host-network-pod
spec:
  hostNetwork: true    # Uses node's network namespace
  containers:
  - name: app
    image: myapp:1.0
    ports:
    - containerPort: 8080
      hostPort: 8080   # Accessible on node IP
```

**Warning:** Use sparingly; reduces isolation and can cause port conflicts.

---

## Pod Lifecycle

### Pod Phases

| Phase | Description |
|-------|-------------|
| **Pending** | Accepted but not yet running (scheduling, image pulls) |
| **Running** | At least one container running |
| **Succeeded** | All containers completed successfully |
| **Failed** | All containers terminated, at least one failed |
| **Unknown** | Pod state cannot be determined |

### Container States

| State | Description |
|-------|-------------|
| **Waiting** | Not yet running (pulling image, applying secrets) |
| **Running** | Executing without issues |
| **Terminated** | Completed or failed execution |

### Restart Policies

```yaml
spec:
  restartPolicy: Always      # Default for Deployments
  # restartPolicy: OnFailure # Good for Jobs
  # restartPolicy: Never     # Good for debugging
```

---

## Essential Commands

```bash
# Create/update pod
kubectl apply -f pod.yaml

# List pods
kubectl get pods
kubectl get pods -o wide                    # Show node and IP
kubectl get pods -l app=myapp               # Filter by label

# Describe pod (detailed info + events)
kubectl describe pod myapp-pod

# View logs
kubectl logs myapp-pod
kubectl logs myapp-pod -c sidecar           # Specific container
kubectl logs myapp-pod --previous           # Previous instance
kubectl logs -f myapp-pod                   # Follow/stream

# Execute commands
kubectl exec myapp-pod -- ls /app
kubectl exec -it myapp-pod -- /bin/sh       # Interactive shell
kubectl exec -it myapp-pod -c sidecar -- sh # Specific container

# Port forwarding
kubectl port-forward myapp-pod 8080:80

# Copy files
kubectl cp myapp-pod:/app/log.txt ./log.txt
kubectl cp ./config.yaml myapp-pod:/etc/config/

# Resource usage (requires metrics-server)
kubectl top pod myapp-pod

# Delete pod
kubectl delete pod myapp-pod
kubectl delete pod myapp-pod --grace-period=0 --force  # Immediate

# Debug with ephemeral container (K8s 1.25+)
kubectl debug myapp-pod -it --image=busybox
```

---

## Best Practices

1. **Always set resource requests and limits** for predictable scheduling and stability
2. **Use labels consistently** for selection and organization
3. **Prefer Deployments over standalone Pods** for production workloads
4. **Configure health probes** for reliable service discovery
5. **Use init containers** for setup tasks that must complete first
6. **Run as non-root** for security
7. **Use read-only root filesystem** where possible
8. **Set appropriate QoS class** (Guaranteed for critical workloads)
