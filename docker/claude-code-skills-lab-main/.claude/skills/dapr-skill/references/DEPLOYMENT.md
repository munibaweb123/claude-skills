# Dapr Deployment Patterns

## Self-Hosted Mode
Self-hosted mode runs Dapr locally on your development machine using Docker or standalone binaries.

### Quick Setup
```bash
# Install Dapr CLI
curl -fsSL https://raw.githubusercontent.com/dapr/cli/master/install/install.sh | /bin/bash

# Initialize Dapr with Docker
dapr init

# Run applications with Dapr
dapr run --app-id myapp --app-port 8080 python app.py
```

### Production Self-Hosted
For production self-hosted deployments:
- Run control plane services separately
- Use production-grade state stores and pub/sub brokers
- Configure security and monitoring
- Set up proper resource limits

```bash
# Initialize with specific runtime version
dapr init --runtime-version 1.11.0

# Run with specific configurations
dapr run \
  --app-id myapp \
  --app-port 8080 \
  --dapr-http-port 3500 \
  --dapr-grpc-port 50001 \
  --config ./config/config.yaml \
  --components-path ./components \
  --log-level warn \
  -- python app.py
```

## Kubernetes Mode
Kubernetes mode leverages native Kubernetes features for deployment and management.

### Installation
```bash
# Install Dapr to Kubernetes cluster
helm repo add dapr https://dapr.github.io/helm-charts/
helm repo update
kubectl create namespace dapr-system

# Install Dapr with --wait flag for verification
helm install dapr dapr/dapr \
  --namespace dapr-system \
  --set-string global.tag=1.11.0 \
  --wait \
  --timeout 10m

# Verify installation
helm status dapr --namespace dapr-system
kubectl get pods --namespace dapr-system
dapr status -k

# Or use the CLI
dapr init -k
```

### Advanced Helm Deployment with Verification

For production deployments, use these enhanced Helm commands with comprehensive verification:

```bash
# Add and update the Dapr Helm repository
helm repo add dapr https://dapr.github.io/helm-charts/
helm repo update

# Create dedicated namespace for Dapr
kubectl create namespace dapr-system --dry-run=client -o yaml | kubectl apply -f -

# Install Dapr with custom configuration and verification
helm install dapr dapr/dapr \
  --namespace dapr-system \
  --set global.ha.enabled=true \
  --set global.mtls.enabled=true \
  --set dapr_placement.affinity="{}" \
  --set dapr_operator.affinity="{}" \
  --set dapr_sidecar_injector.affinity="{}" \
  --set dapr_sentry.affinity="{}" \
  --set dapr_placement.resources.requests.cpu=100m \
  --set dapr_placement.resources.requests.memory=128Mi \
  --set dapr_placement.resources.limits.cpu=200m \
  --set dapr_placement.resources.limits.memory=256Mi \
  --wait \
  --timeout 15m \
  --atomic

# Verify successful installation
helm status dapr --namespace dapr-system
kubectl get pods --namespace dapr-system -o wide
kubectl rollout status deployment/dapr-operator --namespace dapr-system
kubectl rollout status deployment/dapr-placement --namespace dapr-system
kubectl rollout status deployment/dapr-sentry --namespace dapr-system
kubectl rollout status deployment/dapr-sidecar-injector --namespace dapr-system

# Validate Dapr control plane services
dapr status -k

# Check for any pending or problematic pods
kubectl get events --namespace dapr-system --sort-by='.lastTimestamp'
```

### Helm Upgrade with Verification

```bash
# Upgrade Dapr with comprehensive verification
helm upgrade dapr dapr/dapr \
  --namespace dapr-system \
  --set-string global.tag=1.12.0 \
  --wait \
  --timeout 10m \
  --atomic \
  --reuse-values

# Verify upgrade success
kubectl rollout status deployment/dapr-operator --namespace dapr-system
kubectl rollout status deployment/dapr-placement --namespace dapr-system
kubectl rollout status deployment/dapr-sentry --namespace dapr-system
kubectl rollout status deployment/dapr-sidecar-injector --namespace dapr-system

# Confirm all services are running correctly
dapr status -k
kubectl get pods --namespace dapr-system
```

### Helm Uninstall with Cleanup Verification

```bash
# Uninstall Dapr with verification
helm uninstall dapr --namespace dapr-system

# Verify removal of Dapr pods
kubectl get pods --namespace dapr-system

# Clean up CRDs if needed (WARNING: This will remove all Dapr components)
kubectl get crd -o name | grep dapr | xargs kubectl delete crd

# Delete namespace after confirming all resources are removed
kubectl delete namespace dapr-system
```
```

### Application Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nodeapp
  labels:
    app: nodeapp
spec:
  replicas: 1
  selector:
    matchLabels:
      app: nodeapp
  template:
    metadata:
      labels:
        app: nodeapp
      annotations:
        dapr.io/enabled: "true"
        dapr.io/app-id: "nodeapp"
        dapr.io/app-port: "3000"
        dapr.io/config: "appconfig"
        dapr.io/log-as-json: "true"
    spec:
      containers:
      - name: app
        image: "dapriosamples/hello-k8s-node:latest"
        ports:
        - containerPort: 3000
```

### Dapr System Services
Dapr deploys several control plane services in the `dapr-system` namespace:
- **dapr-operator**: Manages component and configuration lifecycle
- **dapr-placement**: Handles actor placement and load balancing
- **dapr-sentry**: Handles mTLS certificate management
- **dapr-sidecar-injector**: Automatically injects Dapr sidecars

## Component Deployment

### Component Definitions
Components are defined as Kubernetes Custom Resource Definitions (CRDs) or files:

```yaml
# Kubernetes CRD component
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: statestore
  namespace: production
spec:
  type: state.redis
  version: v1
  metadata:
  - name: redisHost
    value: "redis-master:6379"
  - name: redisPassword
    secretKeyRef:
      name: redis-secret
      key: password
auth:
  secretStore: kubernetes
```

### Component Scoping
Limit component access to specific applications:
```yaml
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: restricted-store
spec:
  # ... component spec ...
scopes:
- app1
- app2
```

## Configuration Management

### Application Configuration
Configure individual applications:
```yaml
apiVersion: dapr.io/v1alpha1
kind: Configuration
metadata:
  name: appconfig
spec:
  tracing:
    samplingRate: "1"
    zipkin:
      endpointAddress: "http://zipkin.default.svc.cluster.local:9411/api/v2/spans"
  metric:
    enabled: true
  httpPipeline:
    handlers:
    - name: uppercase
      type: middleware.http.uppercase
```

### Global Configuration
Global configuration affects all applications:
```yaml
apiVersion: dapr.io/v1alpha1
kind: Configuration
metadata:
  name: global-config
spec:
  features:
  - name: FeatureName
    enabled: true
  mtls:
    enabled: true
    workloadCertTTL: 24h
    allowedClockSkew: 15m
```

## Deployment Strategies

### Blue-Green Deployment
Deploy new versions alongside existing ones:
1. Deploy new version with different app-id or version tag
2. Update traffic routing
3. Verify new version is healthy
4. Decommission old version

### Canary Deployment
Gradually shift traffic to new versions:
1. Deploy new version with small replica count
2. Route limited traffic to new version
3. Monitor and gradually increase traffic
4. Full cutover when verified

### Rolling Updates
Standard Kubernetes rolling updates work with Dapr:
```yaml
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0  # Maintain service availability
      maxSurge: 1
```

## Production Best Practices

### Resource Management
- Set appropriate CPU and memory limits
- Monitor sidecar resource usage
- Configure resource requests for predictable scheduling

### Security
- Enable mTLS for all communication
- Use component scoping to limit access
- Implement proper secret management
- Apply network policies

### Monitoring
- Enable distributed tracing
- Collect and visualize metrics
- Set up health checks
- Monitor Dapr system services

### Resilience
- Configure appropriate retry policies
- Implement circuit breakers
- Set timeout values appropriately
- Plan for graceful degradation

### Backup and Recovery
- Backup component configurations
- Plan for state store backup and recovery
- Document disaster recovery procedures
- Test backup and recovery processes regularly