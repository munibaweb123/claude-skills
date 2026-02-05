# Kubernetes Scaling Reference

## Quick Reference: HPA Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| HPA shows `<unknown>` | Metrics Server not working | Install/fix Metrics Server |
| HPA shows `<unknown>` | No resource requests defined | Add CPU/memory requests |
| No scaling occurs | Target not reached | Lower target percentage |
| Rapid up/down (thrashing) | Stabilization too short | Increase stabilization window |
| Won't scale past N | maxReplicas too low | Increase maxReplicas |

---

## Manual Scaling

```bash
# Scale deployment
kubectl scale deployment my-app --replicas=5

# Scale statefulset
kubectl scale statefulset my-db --replicas=3

# Scale to zero (for cost savings)
kubectl scale deployment my-app --replicas=0
```

---

## Metrics Server Setup and Verification

HPA requires Metrics Server to collect resource metrics from kubelets.

### Install Metrics Server

```bash
# Standard installation
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# For Minikube
minikube addons enable metrics-server

# For kind/Docker Desktop (requires insecure TLS)
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
kubectl patch deployment metrics-server -n kube-system --type='json' \
  -p='[{"op": "add", "path": "/spec/template/spec/containers/0/args/-", "value": "--kubelet-insecure-tls"}]'
```

### Verify Metrics Server

```bash
# Step 1: Check deployment status
kubectl get deployment metrics-server -n kube-system
# Expected: READY 1/1

# Step 2: Check pod is running
kubectl get pods -n kube-system -l k8s-app=metrics-server
# Expected: STATUS Running

# Step 3: Check API availability
kubectl get --raw /apis/metrics.k8s.io/v1beta1/nodes
# Expected: JSON response with node metrics

# Step 4: Test with kubectl top
kubectl top nodes
kubectl top pods
# Expected: CPU and memory values (not "error: Metrics API not available")
```

### Troubleshoot Metrics Server

```bash
# Check logs for errors
kubectl logs -n kube-system -l k8s-app=metrics-server

# Common error: "x509: cannot validate certificate"
# Fix: Add --kubelet-insecure-tls flag (see above)

# Common error: "no metrics known for pod"
# Fix: Wait 60 seconds after pod starts for metrics collection

# Check if metrics API is registered
kubectl get apiservices | grep metrics
# Expected: v1beta1.metrics.k8s.io ... True
```

### Metrics Server Health Check Script

```bash
#!/bin/bash
# verify-metrics-server.sh

echo "Checking Metrics Server..."

# Check deployment
if kubectl get deployment metrics-server -n kube-system &>/dev/null; then
    READY=$(kubectl get deployment metrics-server -n kube-system -o jsonpath='{.status.readyReplicas}')
    if [ "$READY" == "1" ]; then
        echo "✓ Metrics Server deployment ready"
    else
        echo "✗ Metrics Server not ready"
        exit 1
    fi
else
    echo "✗ Metrics Server not installed"
    exit 1
fi

# Check API
if kubectl get --raw /apis/metrics.k8s.io/v1beta1/nodes &>/dev/null; then
    echo "✓ Metrics API available"
else
    echo "✗ Metrics API not available"
    exit 1
fi

# Test kubectl top
if kubectl top nodes &>/dev/null; then
    echo "✓ kubectl top working"
    kubectl top nodes
else
    echo "✗ kubectl top failed"
    exit 1
fi

echo "Metrics Server is fully operational!"
```

---

## Horizontal Pod Autoscaler (HPA)

HPA automatically scales workloads based on observed metrics.

### Prerequisites

1. **Metrics Server** must be installed and verified (see above)
2. **Resource requests** must be defined on containers:
   ```yaml
   resources:
     requests:
       cpu: 100m      # REQUIRED for CPU-based HPA
       memory: 128Mi  # REQUIRED for memory-based HPA
   ```

### Core Formula

```
desiredReplicas = ceil(currentReplicas * (currentMetricValue / desiredMetricValue))
```

**Example**: If current CPU is 80% and target is 50%, with 3 replicas:
```
desiredReplicas = ceil(3 * (80/50)) = ceil(4.8) = 5
```

---

## Basic HPA (CPU-based)

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-app-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-app
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

---

## Advanced HPA (Multiple Metrics)

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: myapp
  minReplicas: 2
  maxReplicas: 20
  metrics:
  # CPU-based scaling
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  # Memory-based scaling
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  # Requests per second (custom metric)
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: "1000"
```

---

## Stabilization Window Configuration

Stabilization windows prevent rapid scaling fluctuations (thrashing) by requiring metrics to remain stable before taking action.

### Understanding Stabilization

```
                    Stabilization Window (300s)
                    ◄─────────────────────────────►

CPU: 80% ──┐        ┌── 75% ──┐        ┌── 60% ──► Scale Down!
           │        │         │        │
           └── 70% ─┘         └── 65% ─┘

    t=0    t=60    t=120    t=180    t=240    t=300

    Without stabilization: Would scale down at t=120 (60%)
    With stabilization: Waits until t=300 to confirm trend
```

### Default Behavior

| Direction | Default Stabilization | Reason |
|-----------|----------------------|--------|
| Scale Up | 0 seconds | React quickly to load |
| Scale Down | 300 seconds (5 min) | Prevent premature scale-down |

### Stabilization Configuration

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: stable-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: myapp
  minReplicas: 2
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 0       # Scale up immediately (default)
      policies:
      - type: Percent
        value: 100                         # Can double replicas
        periodSeconds: 15
      - type: Pods
        value: 4                           # Or add up to 4 pods
        periodSeconds: 15
      selectPolicy: Max                    # Use whichever adds more
    scaleDown:
      stabilizationWindowSeconds: 300     # Wait 5 min before scaling down
      policies:
      - type: Percent
        value: 10                          # Remove max 10% of pods
        periodSeconds: 60
      selectPolicy: Min                    # Use most conservative option
```

### Stabilization Presets

#### Aggressive Scaling (Low Latency Requirements)
```yaml
behavior:
  scaleUp:
    stabilizationWindowSeconds: 0
    policies:
    - type: Percent
      value: 200
      periodSeconds: 10
  scaleDown:
    stabilizationWindowSeconds: 60
    policies:
    - type: Percent
      value: 50
      periodSeconds: 30
```

#### Conservative Scaling (Cost Optimization)
```yaml
behavior:
  scaleUp:
    stabilizationWindowSeconds: 60
    policies:
    - type: Pods
      value: 2
      periodSeconds: 60
  scaleDown:
    stabilizationWindowSeconds: 600      # 10 minutes
    policies:
    - type: Pods
      value: 1
      periodSeconds: 120
```

#### Prevent Scale-Down (Peak Hours)
```yaml
behavior:
  scaleDown:
    selectPolicy: Disabled               # Never scale down
```

---

## Custom Metrics for AI/ML Workloads

AI workloads often need custom metrics beyond CPU/memory for intelligent scaling.

### Prerequisites for Custom Metrics

1. **Prometheus Adapter** or **KEDA** for custom metrics
2. **Application exposing metrics** (via /metrics endpoint)

### Install Prometheus Adapter

```bash
# Add Prometheus community Helm repo
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install Prometheus Adapter
helm install prometheus-adapter prometheus-community/prometheus-adapter \
  --namespace monitoring \
  --set prometheus.url=http://prometheus.monitoring.svc
```

### AI Workload Metrics Patterns

#### Pattern 1: GPU Utilization Scaling

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: inference-gpu-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: model-inference
  minReplicas: 1
  maxReplicas: 8
  metrics:
  # Scale on GPU utilization (requires DCGM exporter)
  - type: Pods
    pods:
      metric:
        name: DCGM_FI_DEV_GPU_UTIL
      target:
        type: AverageValue
        averageValue: "70"
  # Also consider GPU memory
  - type: Pods
    pods:
      metric:
        name: DCGM_FI_DEV_FB_USED_PERCENT
      target:
        type: AverageValue
        averageValue: "80"
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 30     # GPUs are expensive, scale fast
    scaleDown:
      stabilizationWindowSeconds: 300    # But don't release too quickly
```

#### Pattern 2: Inference Queue Depth

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: inference-queue-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: model-inference
  minReplicas: 2
  maxReplicas: 20
  metrics:
  # Scale based on pending inference requests
  - type: External
    external:
      metric:
        name: inference_queue_depth
        selector:
          matchLabels:
            model: "llm-7b"
      target:
        type: Value
        value: "100"                      # Scale when queue > 100
  # Also track request latency
  - type: Pods
    pods:
      metric:
        name: inference_latency_p99_seconds
      target:
        type: AverageValue
        averageValue: "2"                 # Scale if p99 > 2s
```

#### Pattern 3: Batch Processing / Training Jobs

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: training-worker-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: training-worker
  minReplicas: 0                          # Scale to zero when idle
  maxReplicas: 50
  metrics:
  # Scale based on pending training jobs
  - type: External
    external:
      metric:
        name: training_jobs_pending
        selector:
          matchLabels:
            queue: "training"
      target:
        type: AverageValue
        averageValue: "1"                 # 1 worker per pending job
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Pods
        value: 10                         # Add up to 10 workers at once
        periodSeconds: 30
    scaleDown:
      stabilizationWindowSeconds: 600    # Keep workers for 10 min
      policies:
      - type: Percent
        value: 100                        # Can scale to zero
        periodSeconds: 60
```

#### Pattern 4: LLM Inference with Token Throughput

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: llm-inference-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: llm-inference
  minReplicas: 1
  maxReplicas: 10
  metrics:
  # Primary: tokens per second throughput
  - type: Pods
    pods:
      metric:
        name: tokens_per_second
      target:
        type: AverageValue
        averageValue: "500"               # Target 500 tokens/sec per pod
  # Secondary: request queue
  - type: Pods
    pods:
      metric:
        name: pending_requests
      target:
        type: AverageValue
        averageValue: "5"                 # Max 5 pending per pod
  # Tertiary: GPU memory (prevent OOM)
  - type: Pods
    pods:
      metric:
        name: gpu_memory_used_percent
      target:
        type: AverageValue
        averageValue: "85"
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 15
      policies:
      - type: Pods
        value: 2
        periodSeconds: 30
    scaleDown:
      stabilizationWindowSeconds: 180
```

### KEDA for Event-Driven Scaling

KEDA (Kubernetes Event-Driven Autoscaling) provides advanced scaling triggers.

```bash
# Install KEDA
helm repo add kedacore https://kedacore.github.io/charts
helm repo update
helm install keda kedacore/keda --namespace keda --create-namespace
```

#### KEDA ScaledObject for AI Queue

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: inference-scaledobject
spec:
  scaleTargetRef:
    name: model-inference
  minReplicaCount: 0
  maxReplicaCount: 20
  triggers:
  # Scale based on RabbitMQ queue
  - type: rabbitmq
    metadata:
      queueName: inference-requests
      hostFromEnv: RABBITMQ_HOST
      mode: QueueLength
      value: "10"                         # 1 pod per 10 messages
  # Scale based on Redis list
  - type: redis
    metadata:
      listName: inference-queue
      listLength: "5"
  # Scale based on Prometheus metric
  - type: prometheus
    metadata:
      serverAddress: http://prometheus:9090
      metricName: inference_requests_pending
      threshold: "100"
      query: sum(inference_requests_pending{model="llm"})
```

---

## Complete Deployment with HPA

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
spec:
  replicas: 2
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
        resources:
          requests:
            cpu: 100m        # REQUIRED for HPA
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi
        ports:
        - containerPort: 8080
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-app-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-app
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 75
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
```

---

## Essential Commands

```bash
# Create HPA imperatively
kubectl autoscale deployment my-app --cpu-percent=50 --min=1 --max=10

# View HPA status
kubectl get hpa

# Watch real-time scaling
kubectl get hpa --watch

# Detailed HPA info (shows events and conditions)
kubectl describe hpa my-app-hpa

# Check current vs desired replicas
kubectl get hpa -o custom-columns=NAME:.metadata.name,MIN:.spec.minReplicas,MAX:.spec.maxReplicas,CURRENT:.status.currentReplicas,DESIRED:.status.desiredReplicas

# Check metrics
kubectl top pods
kubectl top nodes

# Debug HPA decisions
kubectl describe hpa my-app-hpa | grep -A10 "Conditions"

# View HPA events
kubectl get events --field-selector involvedObject.kind=HorizontalPodAutoscaler
```

---

## Key Configuration Reference

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `minReplicas` | 1 | Minimum pods (never scale below) |
| `maxReplicas` | required | Maximum pods (hard limit) |
| `averageUtilization` | - | Target % of resource request |
| `averageValue` | - | Target absolute value |
| `stabilizationWindowSeconds` (up) | 0 | Seconds to wait before scale up |
| `stabilizationWindowSeconds` (down) | 300 | Seconds to wait before scale down |
| `selectPolicy` | Max (up) / Min (down) | Policy selection strategy |

---

## Common Issues and Solutions

| Issue | Symptom | Solution |
|-------|---------|----------|
| HPA shows `<unknown>` for CPU | No metrics available | Verify Metrics Server is running |
| HPA shows `<unknown>` | No resource requests | Add `resources.requests.cpu` |
| No scaling occurs | Metrics below/above target | Check `kubectl describe hpa` |
| Rapid scale up/down | Thrashing | Increase `stabilizationWindowSeconds` |
| Won't scale to zero | minReplicas > 0 | Set `minReplicas: 0` (requires KEDA for some cases) |
| Custom metrics not working | Adapter not configured | Install and configure Prometheus Adapter |
| Slow reaction | Default stabilization | Reduce stabilization window |
