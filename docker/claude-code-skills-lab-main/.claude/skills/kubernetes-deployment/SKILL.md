---
name: kubernetes-deployment
description: Deploy and scale containerized applications on Kubernetes from hello world to production. Use when deploying containers to Kubernetes, creating Deployments/Services/Ingress, scaling applications, configuring health checks, managing configuration with ConfigMaps/Secrets, setting up storage, or preparing production-ready deployments. Covers kubectl operations, YAML manifests, HPA autoscaling, and security best practices. Includes AI-assisted manifest generation, iterative refinement workflows, critical evaluation checklists, and production readiness validation.
---

# Kubernetes Deployment

Deploy containerized applications from development to production on Kubernetes with AI-assisted generation and validation.

## Quick Start Decision Tree

```
What do you need?
│
├─ Understand Pods first? → See "Pod Fundamentals"
│
├─ First deployment? → See "Hello World Deployment"
│
├─ Natural language to YAML? → See "AI-Assisted Generation"
│
├─ Expose application?
│   ├─ Internal only → ClusterIP Service
│   ├─ External (dev) → NodePort Service
│   └─ External (prod) → LoadBalancer + Ingress
│
├─ Handle traffic spikes? → HPA Autoscaling
│
├─ Run batch workloads?
│   ├─ One-time task → Job
│   └─ Scheduled task → CronJob
│
├─ Store configuration?
│   ├─ Non-sensitive → ConfigMap
│   └─ Sensitive → Secret
│
├─ Persist data? → PersistentVolumeClaim
│
├─ Production ready? → See "Production Checklist"
│
├─ Validate manifests? → See "Production Readiness Validation"
│
├─ Refine iteratively? → See "Iterative Refinement"
│
└─ Pod not working? → See "Troubleshooting Reference"
    ├─ CrashLoopBackOff → Check logs --previous
    ├─ Pending → Check resources/node capacity
    ├─ OOMKilled → Increase memory limit
    └─ ImagePullBackOff → Check image name/auth
```

## Pod Fundamentals

Pods are the smallest deployable units in Kubernetes. Understanding Pod structure is essential before working with Deployments.

### Standalone Pod (Basic)

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: myapp-pod
  labels:
    app: myapp
    version: v1
spec:
  containers:
  - name: app
    image: nginx:1.25
    ports:
    - containerPort: 80
```

### Pod with Resource Requests and Limits

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: myapp-pod
  labels:
    app: myapp
spec:
  containers:
  - name: app
    image: python:3.11-alpine
    command: ["python", "-m", "http.server", "8000"]
    ports:
    - containerPort: 8000
    resources:
      requests:
        cpu: 100m        # Minimum guaranteed (scheduling)
        memory: 64Mi     # Minimum guaranteed
      limits:
        cpu: 500m        # Maximum allowed (throttled if exceeded)
        memory: 256Mi    # Maximum allowed (OOMKilled if exceeded)
```

**Resource Units Quick Reference:**
| Type | Unit | Examples |
|------|------|----------|
| CPU | millicores | `100m` = 0.1 CPU, `1000m` = 1 CPU |
| Memory | binary | `64Mi`, `256Mi`, `1Gi` |

### Multi-Container Pod (Sidecar Pattern)

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: web-with-logging
  labels:
    app: web
spec:
  containers:
  # Main application container
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
    - name: shared-logs
      mountPath: /var/log/nginx

  # Sidecar: log collector
  - name: log-collector
    image: busybox:1.36
    command: ["sh", "-c", "tail -F /logs/access.log"]
    resources:
      requests:
        cpu: 50m
        memory: 32Mi
      limits:
        cpu: 100m
        memory: 64Mi
    volumeMounts:
    - name: shared-logs
      mountPath: /logs

  volumes:
  - name: shared-logs
    emptyDir: {}
```

### Init Container Pattern

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-init
spec:
  initContainers:
  - name: init-db-check
    image: busybox:1.36
    command: ['sh', '-c', 'until nc -z db-service 5432; do sleep 2; done']
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

### Pod Networking Basics

```
┌─────────────────────────────────────────────────────┐
│ Pod (shared network namespace)                       │
│ IP: 10.1.0.15                                       │
│                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │ Container A │  │ Container B │  │ Container C │ │
│  │ :8080       │  │ :9090       │  │ :3000       │ │
│  └─────────────┘  └─────────────┘  └─────────────┘ │
│                                                      │
│  Containers communicate via localhost:PORT          │
└─────────────────────────────────────────────────────┘
```

**Key networking facts:**
- All containers in a Pod share the same IP address
- Containers communicate via `localhost:<port>`
- Each container must use a unique port
- Pod IP is accessible from other Pods in the cluster

### Pod Commands

```bash
# Create pod from manifest
kubectl apply -f pod.yaml

# List pods with resource info
kubectl get pods -o wide

# View pod details and events
kubectl describe pod myapp-pod

# View pod logs
kubectl logs myapp-pod
kubectl logs myapp-pod -c log-collector  # specific container

# Execute command in pod
kubectl exec -it myapp-pod -- /bin/sh
kubectl exec -it myapp-pod -c web -- /bin/sh  # specific container

# Check resource usage (requires metrics-server)
kubectl top pod myapp-pod

# Delete pod
kubectl delete pod myapp-pod
```

> **Note**: For production workloads, use Deployments instead of standalone Pods. Deployments provide self-healing, scaling, and rolling updates.

## Hello World Deployment

### Minimal Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hello-world
spec:
  replicas: 1
  selector:
    matchLabels:
      app: hello-world
  template:
    metadata:
      labels:
        app: hello-world
    spec:
      containers:
      - name: app
        image: nginx:latest
        ports:
        - containerPort: 80
```

### Expose with Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: hello-world
spec:
  type: LoadBalancer
  selector:
    app: hello-world
  ports:
  - port: 80
    targetPort: 80
```

### Deploy Commands

```bash
# Apply manifests
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml

# Verify
kubectl get deployments
kubectl get pods
kubectl get services

# Access logs
kubectl logs -l app=hello-world

# Delete
kubectl delete -f deployment.yaml -f service.yaml
```

## Standard Deployment Workflow

### 1. Create Namespace

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: myapp
```

### 2. Create ConfigMap (if needed)

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: myapp-config
  namespace: myapp
data:
  APP_ENV: production
  LOG_LEVEL: info
```

### 3. Create Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: myapp
spec:
  replicas: 2
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
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
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8080
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          periodSeconds: 5
        envFrom:
        - configMapRef:
            name: myapp-config
```

### 4. Create Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: myapp
  namespace: myapp
spec:
  type: ClusterIP
  selector:
    app: myapp
  ports:
  - port: 80
    targetPort: 8080
```

### 5. Create Ingress (for external access)

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: myapp
  namespace: myapp
spec:
  ingressClassName: nginx
  rules:
  - host: myapp.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: myapp
            port:
              number: 80
```

## Scaling

### Manual Scaling

```bash
kubectl scale deployment myapp --replicas=5 -n myapp
```

### Auto Scaling with HPA

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: myapp-hpa
  namespace: myapp
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: myapp
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

**Prerequisite**: Resource requests must be defined. Install Metrics Server:
```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

## Deployment Strategies

### Rolling Update (Default)

Gradually replaces old Pods with new ones, ensuring zero downtime.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1        # Max pods over desired count during update
      maxUnavailable: 1  # Max pods that can be unavailable during update
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: app
        image: myapp:2.0
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

**Rolling Update Behavior:**
```
replicas: 3, maxSurge: 1, maxUnavailable: 1

Step 1: [v1] [v1] [v1]        ← Initial state (3 pods)
Step 2: [v1] [v1] [v2] [v2]   ← Create 1 new, terminate 1 old (maxSurge=1)
Step 3: [v1] [v2] [v2] [v2]   ← Continue rolling
Step 4: [v2] [v2] [v2]        ← Complete (3 pods running v2)
```

### Recreate Strategy

Terminates all existing Pods before creating new ones. Causes downtime but ensures no version mixing.

```yaml
spec:
  strategy:
    type: Recreate
```

**When to use Recreate:**
- Application cannot run multiple versions simultaneously
- Database migrations requiring exclusive access
- Stateful applications with strict consistency requirements

### Strategy Comparison

| Aspect | RollingUpdate | Recreate |
|--------|---------------|----------|
| Downtime | None | Yes |
| Resource usage | Higher (runs both versions) | Lower |
| Rollback speed | Fast | Slow |
| Version mixing | Yes (briefly) | No |

## ReplicaSet Management

Deployments create and manage ReplicaSets automatically.

```
Deployment (myapp)
    │
    ├── ReplicaSet (myapp-7d9f8b6c5) ← Current (3 replicas)
    │       ├── Pod (myapp-7d9f8b6c5-abc12)
    │       ├── Pod (myapp-7d9f8b6c5-def34)
    │       └── Pod (myapp-7d9f8b6c5-ghi56)
    │
    └── ReplicaSet (myapp-5c4d3b2a1) ← Previous (0 replicas, kept for rollback)
```

```bash
# View ReplicaSets
kubectl get rs -n myapp

# View ReplicaSet details
kubectl describe rs myapp-7d9f8b6c5 -n myapp

# Control revision history (in Deployment spec)
spec:
  revisionHistoryLimit: 10  # Number of old ReplicaSets to retain
```

## Self-Healing Mechanisms

Kubernetes automatically maintains the desired state:

| Failure | Response |
|---------|----------|
| Pod crashes | ReplicaSet creates replacement Pod |
| Pod deleted | ReplicaSet creates replacement Pod |
| Node fails | Pods rescheduled to healthy nodes |
| Container OOMKilled | Pod restarts based on restartPolicy |
| Health check fails | Pod restarted or removed from Service |

```bash
# Watch self-healing in action
kubectl get pods -w -n myapp

# Delete a pod (watch it recreate)
kubectl delete pod myapp-7d9f8b6c5-abc12 -n myapp
```

## Updates and Rollbacks

### Update Methods

```bash
# Method 1: Update image directly
kubectl set image deployment/myapp app=myapp:2.0 -n myapp

# Method 2: Edit deployment
kubectl edit deployment myapp -n myapp

# Method 3: Apply updated manifest (recommended)
kubectl apply -f deployment.yaml

# Method 4: Patch specific fields
kubectl patch deployment myapp -n myapp -p '{"spec":{"template":{"spec":{"containers":[{"name":"app","image":"myapp:2.0"}]}}}}'
```

### Monitor Rollout

```bash
# Watch rollout progress
kubectl rollout status deployment/myapp -n myapp

# View rollout history
kubectl rollout history deployment/myapp -n myapp

# View specific revision details
kubectl rollout history deployment/myapp -n myapp --revision=2
```

### Rollback

```bash
# Rollback to previous revision
kubectl rollout undo deployment/myapp -n myapp

# Rollback to specific revision
kubectl rollout undo deployment/myapp -n myapp --to-revision=2

# Verify rollback
kubectl rollout status deployment/myapp -n myapp
```

### Pause and Resume (for batched changes)

```bash
# Pause rollout
kubectl rollout pause deployment/myapp -n myapp

# Apply multiple changes without triggering rollout
kubectl set image deployment/myapp app=myapp:2.0 -n myapp
kubectl set resources deployment/myapp -c app --limits=cpu=500m,memory=512Mi -n myapp
kubectl set env deployment/myapp -c app APP_ENV=production -n myapp

# Resume to trigger single rollout with all changes
kubectl rollout resume deployment/myapp -n myapp
```

## Jobs and CronJobs

For batch processing and scheduled tasks, use Jobs and CronJobs instead of Deployments.

### Job (One-time Task)

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: data-processor
spec:
  completions: 5           # Total successful completions needed
  parallelism: 2           # Run 2 pods concurrently
  backoffLimit: 3          # Max retries before failure
  activeDeadlineSeconds: 600  # Timeout after 10 minutes
  ttlSecondsAfterFinished: 300  # Auto-cleanup after 5 min
  template:
    spec:
      restartPolicy: OnFailure  # Required: Never or OnFailure
      containers:
      - name: processor
        image: myapp:1.0
        command: ["python", "process.py"]
        resources:
          requests:
            cpu: "100m"
            memory: "128Mi"
          limits:
            cpu: "500m"
            memory: "256Mi"
```

### CronJob (Scheduled Task)

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: daily-cleanup
spec:
  schedule: "0 2 * * *"          # Daily at 2 AM
  timeZone: "America/New_York"   # K8s 1.27+
  concurrencyPolicy: Forbid      # Skip if previous still running
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 1
  jobTemplate:
    spec:
      backoffLimit: 2
      activeDeadlineSeconds: 3600
      template:
        spec:
          restartPolicy: OnFailure
          containers:
          - name: cleanup
            image: cleanup:1.0
            resources:
              requests:
                cpu: "100m"
                memory: "128Mi"
              limits:
                cpu: "500m"
                memory: "512Mi"
```

**Cron Schedule Quick Reference:**

| Schedule | Meaning |
|----------|---------|
| `*/15 * * * *` | Every 15 minutes |
| `0 * * * *` | Every hour |
| `0 2 * * *` | Daily at 2 AM |
| `0 0 * * 0` | Weekly on Sunday |

### Job Commands

```bash
# Create and monitor Job
kubectl apply -f job.yaml
kubectl get jobs -w
kubectl logs job/data-processor

# Manually trigger CronJob
kubectl create job manual-run --from=cronjob/daily-cleanup

# Suspend/resume CronJob
kubectl patch cronjob daily-cleanup -p '{"spec":{"suspend":true}}'
```

## Essential Commands

```bash
# Apply/Update resources
kubectl apply -f manifest.yaml

# Get resources
kubectl get pods,deployments,services -n myapp

# Describe (detailed info)
kubectl describe deployment myapp -n myapp

# Logs
kubectl logs -l app=myapp -n myapp --tail=100

# Exec into pod
kubectl exec -it <pod-name> -n myapp -- /bin/sh

# Port forward for local testing
kubectl port-forward svc/myapp 8080:80 -n myapp

# Delete resources
kubectl delete -f manifest.yaml
```

## Reference Documentation

Detailed reference for each topic:

| Topic | Reference File |
|-------|----------------|
| Cluster & Context Management | [references/cluster-management.md](references/cluster-management.md) |
| Architecture & Reconciliation | [references/architecture.md](references/architecture.md) |
| Pods | [references/pods.md](references/pods.md) |
| Deployments | [references/deployments.md](references/deployments.md) |
| Services | [references/services.md](references/services.md) |
| ConfigMaps & Secrets | [references/configuration.md](references/configuration.md) |
| Scaling & HPA | [references/scaling.md](references/scaling.md) |
| Jobs & CronJobs | [references/jobs.md](references/jobs.md) |
| Ingress | [references/ingress.md](references/ingress.md) |
| Health Probes | [references/health-probes.md](references/health-probes.md) |
| Resource Limits | [references/resources.md](references/resources.md) |
| Storage (PV/PVC) | [references/storage.md](references/storage.md) |
| Namespaces | [references/namespaces.md](references/namespaces.md) |
| Security | [references/security.md](references/security.md) |
| Production Checklist | [references/production-checklist.md](references/production-checklist.md) |
| Troubleshooting | [references/troubleshooting.md](references/troubleshooting.md) |

## AI-Assisted Manifest Generation

Generate Kubernetes manifests from natural language descriptions using AI-powered parsing and generation.

### Natural Language to YAML Translation

Convert plain English descriptions directly to valid Kubernetes YAML:

```bash
# Generate deployment from natural language
python scripts/natural-language-generator.py --describe "Deploy nginx web server with 3 replicas, expose on port 80"

# Generate with additional features
python scripts/natural-language-generator.py --describe "Create production API with 5 replicas, enable HPA and ingress" --validate

# Refine existing manifest with feedback
python scripts/natural-language-generator.py --refine existing.yaml --describe "Add security context and resource limits"
```

### Supported Natural Language Patterns

| Pattern | Example |
|---------|---------|
| Replicas | "with 3 replicas", "3 instances", "scale to 5 pods" |
| Ports | "expose on port 8080", "listen on 3000" |
| Images | "use nginx:1.25", "container image redis:7" |
| Services | "with LoadBalancer", "expose externally" |
| HPA | "enable auto-scaling", "with HPA" |
| Production | "production hardened", "secure deployment" |
| Resources | "100m CPU, 256Mi memory" |

### Example Conversions

**Input:** "Deploy a web app called myapi using image myapp:1.0 with 3 replicas, expose via LoadBalancer on port 8080, enable HPA"

**Output:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapi
  namespace: default
  labels:
    app: myapi
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapi
  template:
    metadata:
      labels:
        app: myapi
    spec:
      containers:
      - name: myapi
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
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 15
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
---
apiVersion: v1
kind: Service
metadata:
  name: myapi
  namespace: default
spec:
  type: LoadBalancer
  selector:
    app: myapi
  ports:
  - port: 80
    targetPort: 8080
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: myapi-hpa
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: myapi
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
```

## Iterative Refinement Workflows

Improve Kubernetes manifests through feedback-driven iteration cycles.

### Refinement Process

1. **Generate Initial Manifest** - Create base configuration from requirements
2. **Validate & Evaluate** - Run automated checks and scoring
3. **Gather Feedback** - Collect input from validation tools and humans
4. **Apply Improvements** - Integrate feedback into manifest
5. **Repeat** - Continue until quality targets are met

### Common Refinement Patterns

| Feedback Category | Example Feedback | Applied Change |
|------------------|------------------|----------------|
| Security | "Add security context" | Add runAsNonRoot, readOnlyRootFilesystem |
| Resources | "Add resource limits" | Add CPU/memory requests and limits |
| Availability | "Increase replicas" | Change replica count from 1 to 3 |
| Scaling | "Enable HPA" | Add HorizontalPodAutoscaler resource |
| Networking | "Change service type" | Switch from ClusterIP to LoadBalancer |

### Refinement Commands

```bash
# Refine manifest with specific feedback
python scripts/natural-language-generator.py --refine deployment.yaml --describe "Add production security settings"

# Apply multiple refinements iteratively
python scripts/natural-language-generator.py --refine deployment.yaml --describe "Add resource limits and health checks" --output refined.yaml
```

## Production Readiness Validation

Comprehensive validation to ensure manifests meet production standards.

### Validation Categories

#### Security Validation
- Container runs as non-root
- Privilege escalation disabled
- Capabilities properly restricted
- Images from trusted sources

#### Resource Validation
- CPU and memory requests/limits defined
- Resource ratios appropriate
- No unlimited resources

#### Availability Validation
- Sufficient replica count
- Health checks configured
- Proper deployment strategy

#### Best Practices Validation
- Proper labeling
- Immutable tags used
- Appropriate service types

### Validation Commands

```bash
# Validate single manifest file
./scripts/production-readiness-validator.sh deployment.yaml

# Validate and score manifest
./scripts/production-readiness-validator.sh deployment.yaml
# Output: Production Readiness Score: 92/100

# Traditional validation after deployment
./scripts/validate-deployment.sh myapp production
```

### Critical Evaluation Checklist

Use the comprehensive checklist to evaluate production readiness:

- [ ] Security Assessment (container, network, RBAC)
- [ ] Resource Management (requests, limits, QoS)
- [ ] Availability and Reliability (probes, strategy, scaling)
- [ ] Configuration Management (secrets, naming, labels)
- [ ] Observability (logging, monitoring, tracing)
- [ ] Production Readiness (backup, lifecycle, testing)
- [ ] Performance Optimization (efficiency, network)
- [ ] Documentation and Maintenance

See [references/critical-evaluation-checklist.md](references/critical-evaluation-checklist.md) for the complete checklist.

## Scripts

| Script | Purpose |
|--------|---------|
| [scripts/generate-manifest.py](scripts/generate-manifest.py) | Generate Kubernetes manifests interactively |
| [scripts/validate-deployment.sh](scripts/validate-deployment.sh) | Validate deployment readiness |
| [scripts/natural-language-generator.py](scripts/natural-language-generator.py) | AI-assisted manifest generation from natural language |
| [scripts/production-readiness-validator.sh](scripts/production-readiness-validator.sh) | Production readiness validation and scoring |
