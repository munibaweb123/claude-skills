# Kubernetes Health Probes Reference

## Quick Reference: Probe Types

| Probe | Purpose | On Failure | When to Use |
|-------|---------|------------|-------------|
| **Startup** | Wait for app initialization | Block liveness/readiness | Slow-starting apps, AI models |
| **Liveness** | Detect deadlocks/hangs | Restart container | All production pods |
| **Readiness** | Control traffic routing | Remove from Service | Apps with dependencies |

---

## Probe Timing Decision Guide

```
How long does your app take to start?
│
├─ < 30 seconds (standard web app)
│   └─ Use initialDelaySeconds: 10-15
│
├─ 30-120 seconds (app with migrations, cache warm-up)
│   └─ Use startupProbe with failureThreshold: 12-15
│
├─ 2-5 minutes (AI model loading, large datasets)
│   └─ Use startupProbe with failureThreshold: 30-60
│
└─ 5-15 minutes (LLM loading, GPU initialization)
    └─ Use startupProbe with failureThreshold: 90-180
```

---

## Probe Mechanisms

### HTTP Probe (Most Common)

```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: 8080
    httpHeaders:
    - name: Custom-Header
      value: Awesome
  initialDelaySeconds: 3
  periodSeconds: 10
```

**Success**: HTTP status 200-399

### TCP Probe (For Non-HTTP Services)

```yaml
livenessProbe:
  tcpSocket:
    port: 8080
  initialDelaySeconds: 15
  periodSeconds: 20
```

**Success**: TCP connection established

### Command/Exec Probe (Custom Logic)

```yaml
livenessProbe:
  exec:
    command:
    - cat
    - /tmp/healthy
  initialDelaySeconds: 5
  periodSeconds: 5
```

**Success**: Exit code 0

### gRPC Probe (For gRPC Services)

```yaml
livenessProbe:
  grpc:
    port: 50051
    service: myservice  # Optional
  initialDelaySeconds: 10
  periodSeconds: 10
```

**Success**: gRPC health check returns SERVING

---

## Configuration Parameters

| Parameter | Default | Description | Recommendation |
|-----------|---------|-------------|----------------|
| `initialDelaySeconds` | 0 | Wait before first probe | Set based on app startup time |
| `periodSeconds` | 10 | How often to probe | 5-15s for readiness, 10-30s for liveness |
| `timeoutSeconds` | 1 | Max wait for response | 3-10s for slow endpoints |
| `successThreshold` | 1 | Successes to be healthy | Keep at 1 for liveness |
| `failureThreshold` | 3 | Failures before unhealthy | 3-5 for production |

### Calculating Maximum Startup Time

```
maxStartupTime = failureThreshold × periodSeconds

Example: failureThreshold: 30, periodSeconds: 10
maxStartupTime = 30 × 10 = 300 seconds (5 minutes)
```

---

## Startup Probe (For Slow-Starting Apps)

Blocks liveness and readiness probes until the app is initialized.

### Standard Application (30-60s startup)

```yaml
startupProbe:
  httpGet:
    path: /healthz
    port: 8080
  failureThreshold: 12      # 12 × 5s = 60s max
  periodSeconds: 5
```

### Application with Database Migrations (2-3 min startup)

```yaml
startupProbe:
  httpGet:
    path: /healthz
    port: 8080
  failureThreshold: 36      # 36 × 5s = 180s (3 min) max
  periodSeconds: 5
  timeoutSeconds: 5
```

---

## AI Agent / ML Model Probe Patterns

AI workloads often have slow initialization due to model loading, GPU setup, and warm-up.

### Pattern 1: LLM Inference Service (5-10 min startup)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: llm-inference
spec:
  replicas: 2
  selector:
    matchLabels:
      app: llm-inference
  template:
    metadata:
      labels:
        app: llm-inference
    spec:
      containers:
      - name: inference
        image: llm-inference:1.0
        ports:
        - containerPort: 8080
        resources:
          requests:
            cpu: "4"
            memory: "16Gi"
            nvidia.com/gpu: "1"
          limits:
            cpu: "8"
            memory: "32Gi"
            nvidia.com/gpu: "1"

        # Startup: Allow 10 minutes for model loading
        startupProbe:
          httpGet:
            path: /health
            port: 8080
          failureThreshold: 60    # 60 × 10s = 600s (10 min)
          periodSeconds: 10
          timeoutSeconds: 10

        # Liveness: Detect inference engine crashes
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 0  # Startup probe handles delay
          periodSeconds: 30       # Less frequent (GPU workload)
          timeoutSeconds: 10
          failureThreshold: 3

        # Readiness: Check if model is ready for inference
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
          successThreshold: 1
```

### Pattern 2: AI Agent with Tool Loading (3-5 min startup)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ai-agent
  template:
    metadata:
      labels:
        app: ai-agent
    spec:
      containers:
      - name: agent
        image: ai-agent:1.0
        ports:
        - containerPort: 8000
        env:
        - name: MODEL_PATH
          value: "/models/agent-model"
        - name: TOOL_REGISTRY
          value: "http://tool-service:8080"

        # Startup: Allow 5 minutes for model + tool initialization
        startupProbe:
          httpGet:
            path: /health/startup
            port: 8000
          failureThreshold: 30    # 30 × 10s = 300s (5 min)
          periodSeconds: 10
          timeoutSeconds: 15

        # Liveness: Simple health check (no model inference)
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
          periodSeconds: 20
          timeoutSeconds: 5
          failureThreshold: 3

        # Readiness: Verify agent can process requests
        readinessProbe:
          exec:
            command:
            - python
            - -c
            - "import requests; r=requests.get('http://localhost:8000/health/ready'); exit(0 if r.status_code==200 else 1)"
          periodSeconds: 15
          timeoutSeconds: 10
          failureThreshold: 2
```

### Pattern 3: Embedding Service with Model Warm-up (2-3 min startup)

```yaml
startupProbe:
  httpGet:
    path: /health
    port: 8080
  failureThreshold: 36      # 36 × 5s = 180s (3 min)
  periodSeconds: 5
  timeoutSeconds: 10

livenessProbe:
  httpGet:
    path: /health
    port: 8080
  periodSeconds: 30
  timeoutSeconds: 10
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /ready            # Returns 200 only after warm-up complete
    port: 8080
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3
```

### Pattern 4: GPU-Accelerated Training Worker

```yaml
startupProbe:
  exec:
    command:
    - sh
    - -c
    - "nvidia-smi && python -c 'import torch; print(torch.cuda.is_available())'"
  failureThreshold: 30      # 30 × 10s = 300s
  periodSeconds: 10
  timeoutSeconds: 30

livenessProbe:
  exec:
    command:
    - sh
    - -c
    - "nvidia-smi > /dev/null 2>&1"
  periodSeconds: 60         # GPU workloads - check less frequently
  timeoutSeconds: 10
  failureThreshold: 3
```

---

## Liveness Probe Examples

### HTTP Liveness (Standard)

```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 15
  timeoutSeconds: 5
  failureThreshold: 3
```

### Command Liveness (For Non-HTTP)

```yaml
livenessProbe:
  exec:
    command:
    - sh
    - -c
    - "pgrep -f 'python main.py' || exit 1"
  periodSeconds: 30
  timeoutSeconds: 5
  failureThreshold: 3
```

### TCP Liveness (Database/Redis)

```yaml
livenessProbe:
  tcpSocket:
    port: 5432
  initialDelaySeconds: 15
  periodSeconds: 20
  failureThreshold: 3
```

---

## Readiness Probe Examples

### HTTP Readiness with Dependency Check

```yaml
readinessProbe:
  httpGet:
    path: /ready            # Checks DB connection, cache, etc.
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 3
  successThreshold: 1
```

### Command Readiness (Check File Exists)

```yaml
readinessProbe:
  exec:
    command:
    - test
    - -f
    - /app/ready
  periodSeconds: 5
  failureThreshold: 3
```

---

## Complete Production Example

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

        # Startup probe for initialization
        startupProbe:
          httpGet:
            path: /healthz
            port: 8080
          failureThreshold: 30    # 30 × 10s = 300s max
          periodSeconds: 10

        # Liveness probe to detect deadlocks
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8080
          initialDelaySeconds: 0  # Startup probe handles delay
          periodSeconds: 15
          timeoutSeconds: 5
          failureThreshold: 3

        # Readiness probe for traffic control
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 0
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
          successThreshold: 1
```

---

## Probe Failure Diagnosis

### Step 1: Identify the Failing Probe

```bash
# Check pod status and restart count
kubectl get pods

# Look for probe failure events
kubectl describe pod <pod-name> | grep -A5 "Events"

# Example output:
# Warning  Unhealthy  Liveness probe failed: HTTP probe failed with statuscode: 500
# Warning  Unhealthy  Readiness probe failed: connection refused
```

### Step 2: Check Container Logs

```bash
# View current logs
kubectl logs <pod-name>

# View previous container logs (if restarted)
kubectl logs <pod-name> --previous

# Follow logs in real-time
kubectl logs -f <pod-name>
```

### Step 3: Test Probe Endpoint Manually

```bash
# Port-forward to test the endpoint
kubectl port-forward <pod-name> 8080:8080

# In another terminal, test the probe endpoint
curl -v http://localhost:8080/healthz
curl -v http://localhost:8080/ready

# Or exec into the pod
kubectl exec -it <pod-name> -- curl localhost:8080/healthz
kubectl exec -it <pod-name> -- wget -qO- localhost:8080/ready
```

### Step 4: Check Probe Configuration

```bash
# View probe settings
kubectl get pod <pod-name> -o yaml | grep -A20 "livenessProbe\|readinessProbe\|startupProbe"

# Common issues to check:
# - Wrong port number
# - Wrong path
# - Timeout too short
# - failureThreshold too low
```

### Step 5: Analyze Probe Timing

```bash
# Check events for timing patterns
kubectl get events --field-selector involvedObject.name=<pod-name> --sort-by='.lastTimestamp'

# Calculate if startup time exceeds probe limits
# maxStartupTime = failureThreshold × periodSeconds
```

---

## Common Probe Failures and Solutions

| Symptom | Cause | Solution |
|---------|-------|----------|
| **Container keeps restarting** | Liveness probe failing | Increase `failureThreshold` or `timeoutSeconds` |
| **Pod not receiving traffic** | Readiness probe failing | Fix `/ready` endpoint or increase timeout |
| **Pod killed during startup** | No startup probe, liveness failing | Add `startupProbe` |
| **Probe timeout errors** | Endpoint too slow | Increase `timeoutSeconds` |
| **Connection refused** | App not listening on port | Check port number, app binding |
| **HTTP 500 errors** | App error on health endpoint | Check app logs, fix endpoint |
| **Probe passes locally, fails in K8s** | Wrong port or path | Verify containerPort matches probe port |

### Fix: Container Restarts During Startup

**Before (failing):**
```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: 8080
  initialDelaySeconds: 10  # Not enough for slow app
  periodSeconds: 5
  failureThreshold: 3      # Killed after 25 seconds
```

**After (fixed):**
```yaml
startupProbe:
  httpGet:
    path: /healthz
    port: 8080
  failureThreshold: 30     # 300 seconds to start
  periodSeconds: 10

livenessProbe:
  httpGet:
    path: /healthz
    port: 8080
  initialDelaySeconds: 0   # Startup probe handles delay
  periodSeconds: 15
  failureThreshold: 3
```

### Fix: Readiness Probe Too Sensitive

**Before (flapping):**
```yaml
readinessProbe:
  httpGet:
    path: /ready
    port: 8080
  periodSeconds: 1         # Too frequent
  timeoutSeconds: 1        # Too short
  failureThreshold: 1      # Removed on first failure
```

**After (stable):**
```yaml
readinessProbe:
  httpGet:
    path: /ready
    port: 8080
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 3
  successThreshold: 1
```

---

## Best Practices

### Do's

1. **Use startup probes** for apps > 30s initialization
2. **Use separate endpoints** - `/healthz` (liveness), `/ready` (readiness)
3. **Keep liveness checks simple** - should only check if process is alive
4. **Include dependencies in readiness** - database, cache, external services
5. **Set appropriate timeouts** - especially for AI/ML workloads
6. **Use TCP probes** for databases and non-HTTP services

### Don'ts

1. **Don't check external dependencies in liveness** - causes cascading failures
2. **Don't set initialDelaySeconds too low** - use startup probe instead
3. **Don't make probes do heavy work** - should be lightweight
4. **Don't use failureThreshold: 1 for liveness** - too aggressive
5. **Don't forget timeoutSeconds** for slow endpoints

---

## Probe Endpoint Implementation Examples

### Python (FastAPI)

```python
from fastapi import FastAPI
import asyncio

app = FastAPI()
model_loaded = False
db_connected = False

@app.on_event("startup")
async def startup():
    global model_loaded, db_connected
    # Simulate slow model loading
    await asyncio.sleep(60)
    model_loaded = True
    db_connected = True

@app.get("/healthz")
async def liveness():
    """Liveness: Is the process running?"""
    return {"status": "alive"}

@app.get("/ready")
async def readiness():
    """Readiness: Can we serve traffic?"""
    if model_loaded and db_connected:
        return {"status": "ready"}
    return Response(status_code=503)

@app.get("/health/startup")
async def startup_check():
    """Startup: Has initialization completed?"""
    if model_loaded:
        return {"status": "started"}
    return Response(status_code=503)
```

### Node.js (Express)

```javascript
const express = require('express');
const app = express();

let modelLoaded = false;
let dbConnected = false;

// Simulate slow startup
setTimeout(() => {
  modelLoaded = true;
  dbConnected = true;
}, 60000);

// Liveness: Is process alive?
app.get('/healthz', (req, res) => {
  res.status(200).json({ status: 'alive' });
});

// Readiness: Can we serve traffic?
app.get('/ready', (req, res) => {
  if (modelLoaded && dbConnected) {
    res.status(200).json({ status: 'ready' });
  } else {
    res.status(503).json({ status: 'not ready' });
  }
});

// Startup: Has initialization completed?
app.get('/health/startup', (req, res) => {
  if (modelLoaded) {
    res.status(200).json({ status: 'started' });
  } else {
    res.status(503).json({ status: 'starting' });
  }
});
```

---

## Debugging Commands Reference

```bash
# View all probe-related events
kubectl get events --field-selector reason=Unhealthy

# Watch pod status in real-time
kubectl get pods -w

# Describe pod for probe details
kubectl describe pod <pod-name>

# Check container restart count
kubectl get pods -o custom-columns=NAME:.metadata.name,RESTARTS:.status.containerStatuses[0].restartCount

# View probe configuration
kubectl get pod <pod-name> -o jsonpath='{.spec.containers[0].livenessProbe}'

# Test probe from inside cluster
kubectl run debug --rm -it --image=curlimages/curl -- curl http://<service-name>:8080/healthz

# Check endpoint response time
kubectl exec <pod-name> -- time curl -s localhost:8080/healthz
```
