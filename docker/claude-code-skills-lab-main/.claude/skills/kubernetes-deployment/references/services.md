# Kubernetes Services Reference

## What is a Service?

A **Service** exposes a logical set of Pods over a network, providing a stable endpoint for accessing applications. Services decouple frontends from backends, allowing Pods to be created/destroyed dynamically.

## Service Type Selection Guide

### Decision Tree

```
How should the application be accessed?
│
├─ Only from within the cluster?
│   └─ ClusterIP (default)
│
├─ From outside the cluster?
│   │
│   ├─ Local development (Docker Desktop, minikube, kind)?
│   │   └─ NodePort
│   │
│   ├─ Cloud environment with load balancer support?
│   │   └─ LoadBalancer
│   │
│   └─ Need hostname/path-based routing?
│       └─ ClusterIP + Ingress
│
└─ Need to connect to external service?
    └─ ExternalName
```

### Service Type Comparison

| Type | Access Scope | Use Case | Port Range |
|------|--------------|----------|------------|
| **ClusterIP** | Internal only | Microservice communication, databases | Any |
| **NodePort** | External via node IP | Development, testing | 30000-32767 |
| **LoadBalancer** | External via cloud LB | Production external access | Any |
| **ExternalName** | DNS alias | Connect to external services | N/A |

### When to Use Each Type

**ClusterIP** (Default)
- Backend services accessed only by other pods
- Databases, caches, internal APIs
- Services behind an Ingress controller

**NodePort**
- Local Kubernetes (Docker Desktop, minikube, kind)
- Quick external access for testing
- When cloud load balancer is unavailable

**LoadBalancer**
- Production workloads on cloud providers (AWS, GCP, Azure)
- Need automatic external IP provisioning
- High availability requirements

**ExternalName**
- Alias for external databases (RDS, Cloud SQL)
- Gradual migration from external to internal services
- Environment-specific external endpoints

## Service Types

### ClusterIP (Default)

Exposes the Service on a cluster-internal IP only.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: backend-service
  namespace: myapp
spec:
  type: ClusterIP
  selector:
    app: backend
    tier: api
  ports:
  - name: http
    protocol: TCP
    port: 80           # Service port (what clients use)
    targetPort: 8080   # Pod port (where app listens)
```

**Access patterns:**
- From same namespace: `http://backend-service:80`
- From other namespace: `http://backend-service.myapp.svc.cluster.local:80`

### NodePort

Exposes the Service on each Node's IP at a static port. External access via `<NodeIP>:<NodePort>`.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: frontend-service
spec:
  type: NodePort
  selector:
    app: frontend
  ports:
  - name: http
    port: 80           # Internal cluster port
    targetPort: 3000   # Pod port
    nodePort: 30080    # External port (30000-32767)
```

**Access patterns:**
- Internal: `http://frontend-service:80`
- External: `http://localhost:30080` (Docker Desktop)
- External: `http://<node-ip>:30080` (any node in cluster)

### LoadBalancer

Exposes the Service externally using a cloud provider's load balancer.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: api-service
  annotations:
    # AWS-specific annotations
    service.beta.kubernetes.io/aws-load-balancer-type: nlb
    service.beta.kubernetes.io/aws-load-balancer-scheme: internet-facing
spec:
  type: LoadBalancer
  selector:
    app: api
  ports:
  - name: https
    protocol: TCP
    port: 443
    targetPort: 8443
```

**Access patterns:**
- Internal: `http://api-service:443`
- External: `http://<EXTERNAL-IP>:443` (provisioned by cloud)

### ExternalName

Maps a Service to an external DNS name.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: external-db
  namespace: myapp
spec:
  type: ExternalName
  externalName: mydb.us-east-1.rds.amazonaws.com
```

**Access pattern:**
- `external-db.myapp.svc.cluster.local` → `mydb.us-east-1.rds.amazonaws.com`

## Label Selector Configuration

### How Selectors Work

Services use label selectors to find target Pods. The selector must match labels defined in the Pod template.

```
Service                          Deployment
┌─────────────────────┐          ┌─────────────────────────────┐
│ spec:               │          │ spec:                       │
│   selector:         │──MUST───▶│   template:                 │
│     app: myapp      │  MATCH   │     metadata:               │
│     version: v1     │          │       labels:               │
│                     │          │         app: myapp          │
│                     │          │         version: v1         │
└─────────────────────┘          └─────────────────────────────┘
```

### Basic Selector Pattern

```yaml
# Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp        # Pod label
        version: v1       # Additional label
    spec:
      containers:
      - name: app
        image: myapp:1.0
        ports:
        - containerPort: 8080
---
# Service - selector matches Pod labels
apiVersion: v1
kind: Service
metadata:
  name: myapp-service
spec:
  selector:
    app: myapp            # Matches Pod label
  ports:
  - port: 80
    targetPort: 8080
```

### Multiple Label Selectors

Use multiple labels for precise targeting:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: myapp-v1-service
spec:
  selector:
    app: myapp
    version: v1           # Only targets v1 pods
  ports:
  - port: 80
    targetPort: 8080
```

### Common Label Conventions

```yaml
labels:
  app: myapp                    # Application name
  app.kubernetes.io/name: myapp # Recommended label
  app.kubernetes.io/version: "1.0"
  app.kubernetes.io/component: frontend
  app.kubernetes.io/part-of: myapp-stack
  tier: frontend                # Application tier
  environment: production       # Environment
```

### Selector Mismatch Debugging

```bash
# Check Pod labels
kubectl get pods --show-labels

# Check Service selector
kubectl describe svc myapp-service | grep Selector

# Verify endpoints (should list Pod IPs)
kubectl get endpoints myapp-service

# If endpoints show <none>, selectors don't match
```

## DNS Naming Conventions

### DNS Record Format

Kubernetes creates DNS records for Services automatically:

```
<service-name>.<namespace>.svc.<cluster-domain>
```

Default cluster domain is `cluster.local`.

### DNS Resolution Examples

```
Full DNS name:           myapp.production.svc.cluster.local
Same namespace:          myapp
Cross-namespace:         myapp.production
With svc suffix:         myapp.production.svc
```

### DNS Discovery Patterns

```yaml
# Pod accessing services via DNS
apiVersion: v1
kind: Pod
metadata:
  name: client-pod
spec:
  containers:
  - name: app
    image: myapp:1.0
    env:
    # Same namespace - short name
    - name: DATABASE_URL
      value: "postgres://db-service:5432/mydb"

    # Cross-namespace - full name
    - name: AUTH_SERVICE_URL
      value: "http://auth-service.auth-system.svc.cluster.local:8080"

    # Using service DNS with port name
    - name: CACHE_URL
      value: "redis://cache-service:6379"
```

### DNS Resolution Hierarchy

```
From pod in namespace "myapp":

1. db-service                              → db-service.myapp.svc.cluster.local
2. db-service.myapp                        → db-service.myapp.svc.cluster.local
3. db-service.other-ns                     → db-service.other-ns.svc.cluster.local
4. db-service.myapp.svc                    → db-service.myapp.svc.cluster.local
5. db-service.myapp.svc.cluster.local      → Full FQDN
```

### Headless Services (Direct Pod DNS)

For stateful applications needing direct Pod access:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: db-headless
spec:
  clusterIP: None         # Headless service
  selector:
    app: database
  ports:
  - port: 5432
```

DNS records for headless services:
```
# Service DNS returns all Pod IPs
db-headless.default.svc.cluster.local → [10.1.0.1, 10.1.0.2, 10.1.0.3]

# Individual Pod DNS (with StatefulSet)
db-0.db-headless.default.svc.cluster.local → 10.1.0.1
db-1.db-headless.default.svc.cluster.local → 10.1.0.2
```

### Testing DNS Resolution

```bash
# Run a test pod with DNS tools
kubectl run -it dns-test --image=alpine --rm -- sh

# Inside the pod:
apk add bind-tools curl

# Test DNS resolution
nslookup myapp-service
nslookup myapp-service.default.svc.cluster.local

# Test connectivity
curl http://myapp-service:80
```

## Endpoint Troubleshooting

### Common Issues and Solutions

#### Issue 1: Endpoints Show `<none>`

**Symptom:**
```bash
$ kubectl get endpoints myapp-service
NAME            ENDPOINTS   AGE
myapp-service   <none>      5m
```

**Causes and Solutions:**

| Cause | Diagnosis | Solution |
|-------|-----------|----------|
| Selector mismatch | `kubectl describe svc` vs `kubectl get pods --show-labels` | Fix selector to match Pod labels |
| No matching Pods | `kubectl get pods -l app=myapp` returns nothing | Deploy Pods with correct labels |
| Pods not Ready | `kubectl get pods` shows 0/1 Ready | Fix readiness probes or app startup |
| Wrong namespace | Service and Pods in different namespaces | Move to same namespace or use cross-namespace |

**Debug commands:**
```bash
# Compare selector with Pod labels
kubectl describe svc myapp-service | grep Selector
kubectl get pods --show-labels

# Check if Pods exist with the label
kubectl get pods -l app=myapp

# Check Pod readiness
kubectl get pods -l app=myapp -o wide
```

#### Issue 2: Connection Refused

**Symptom:**
```bash
$ curl http://myapp-service:80
curl: (7) Failed to connect: Connection refused
```

**Causes and Solutions:**

| Cause | Diagnosis | Solution |
|-------|-----------|----------|
| Wrong targetPort | App listens on different port | Match targetPort to containerPort |
| App not listening | App crashed or not started | Check `kubectl logs` |
| App binding to localhost | App only accepts 127.0.0.1 | Configure app to bind 0.0.0.0 |

**Debug commands:**
```bash
# Check what port the app is listening on
kubectl exec -it <pod-name> -- netstat -tlnp
kubectl exec -it <pod-name> -- ss -tlnp

# Check Pod logs
kubectl logs -l app=myapp

# Test from inside the Pod
kubectl exec -it <pod-name> -- curl localhost:8080
```

#### Issue 3: Connection Reset / Timeout

**Symptom:**
```bash
$ curl http://myapp-service:80
curl: (56) Recv failure: Connection reset by peer
```

**Causes and Solutions:**

| Cause | Diagnosis | Solution |
|-------|-----------|----------|
| Pod crashing | `kubectl get pods` shows restarts | Fix application errors |
| Resource limits | OOMKilled in events | Increase memory limits |
| Network policy blocking | Check NetworkPolicies | Update or remove policy |
| Readiness probe failing | Endpoints flapping | Fix readiness probe |

**Debug commands:**
```bash
# Check Pod events
kubectl describe pod <pod-name>

# Watch endpoints for flapping
kubectl get endpoints myapp-service -w

# Check for NetworkPolicies
kubectl get networkpolicies

# Check Pod resource usage
kubectl top pod <pod-name>
```

#### Issue 4: DNS Resolution Fails

**Symptom:**
```bash
$ nslookup myapp-service
;; connection timed out; no servers could be reached
```

**Causes and Solutions:**

| Cause | Diagnosis | Solution |
|-------|-----------|----------|
| CoreDNS not running | `kubectl get pods -n kube-system` | Restart CoreDNS |
| Service doesn't exist | `kubectl get svc` | Create the Service |
| Wrong namespace | Service in different namespace | Use FQDN or correct namespace |

**Debug commands:**
```bash
# Check CoreDNS pods
kubectl get pods -n kube-system -l k8s-app=kube-dns

# Check CoreDNS logs
kubectl logs -n kube-system -l k8s-app=kube-dns

# Test DNS from pod
kubectl run -it dns-test --image=busybox --rm -- nslookup myapp-service

# Check /etc/resolv.conf in pod
kubectl exec -it <pod-name> -- cat /etc/resolv.conf
```

### Troubleshooting Flowchart

```
Service not working?
│
├─ Can you resolve the DNS name?
│   │
│   ├─ No → Check CoreDNS pods, check Service exists
│   │
│   └─ Yes → Continue
│
├─ Do endpoints exist?
│   │
│   ├─ No (<none>) → Check selector matches Pod labels
│   │               → Check Pods are Running and Ready
│   │
│   └─ Yes → Continue
│
├─ Can you connect to endpoint IP directly?
│   │
│   ├─ No → Check targetPort matches containerPort
│   │     → Check app is listening on 0.0.0.0
│   │     → Check Pod logs for errors
│   │
│   └─ Yes → Check NetworkPolicies, kube-proxy
│
└─ Still not working?
    → Check kube-proxy logs
    → Check iptables rules
    → Check CNI plugin status
```

### Quick Diagnostic Script

```bash
#!/bin/bash
# diagnose-service.sh <service-name> <namespace>

SERVICE=$1
NAMESPACE=${2:-default}

echo "=== Service Details ==="
kubectl get svc $SERVICE -n $NAMESPACE -o wide

echo -e "\n=== Service Description ==="
kubectl describe svc $SERVICE -n $NAMESPACE

echo -e "\n=== Endpoints ==="
kubectl get endpoints $SERVICE -n $NAMESPACE

echo -e "\n=== Pods matching selector ==="
SELECTOR=$(kubectl get svc $SERVICE -n $NAMESPACE -o jsonpath='{.spec.selector}' | tr -d '{}' | sed 's/:/=/g' | sed 's/,/,/g' | tr -d '"')
kubectl get pods -n $NAMESPACE -l $SELECTOR -o wide

echo -e "\n=== Pod Readiness ==="
kubectl get pods -n $NAMESPACE -l $SELECTOR -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.conditions[?(@.type=="Ready")].status}{"\n"}{end}'
```

## Port Configuration

```yaml
ports:
  - name: http           # Port name (optional but recommended for multi-port)
    protocol: TCP        # TCP (default) or UDP
    port: 80             # Service port (exposed on cluster IP)
    targetPort: 9376     # Pod port (where app listens)
```

### Port Mapping Visualization

```
External Client
      │
      ▼ (NodePort: 30080)
┌─────────────────────────────────────┐
│           Node                       │
│  ┌─────────────────────────────┐    │
│  │     Service (ClusterIP)     │    │
│  │     Port: 80                │    │
│  └──────────────┬──────────────┘    │
│                 │                    │
│         ┌───────┴───────┐           │
│         ▼               ▼           │
│    ┌─────────┐     ┌─────────┐     │
│    │  Pod 1  │     │  Pod 2  │     │
│    │ :8080   │     │ :8080   │     │
│    └─────────┘     └─────────┘     │
│    (targetPort)    (targetPort)     │
└─────────────────────────────────────┘
```

### Named Port References

Reference Pod port names in `targetPort`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: nginx-service
spec:
  selector:
    app: proxy
  ports:
  - port: 80
    targetPort: http-web-svc  # References Pod's named port
---
apiVersion: v1
kind: Pod
metadata:
  name: nginx
  labels:
    app: proxy
spec:
  containers:
  - name: nginx
    image: nginx:stable
    ports:
      - containerPort: 80
        name: http-web-svc  # Named port
```

## Multi-Port Services

```yaml
apiVersion: v1
kind: Service
metadata:
  name: myapp-service
spec:
  selector:
    app: myapp
  ports:
  - name: http          # Required when multiple ports
    protocol: TCP
    port: 80
    targetPort: 8080
  - name: https
    protocol: TCP
    port: 443
    targetPort: 8443
  - name: metrics
    protocol: TCP
    port: 9090
    targetPort: 9090
```

## Essential Commands

```bash
# Create service
kubectl apply -f service.yaml

# List services
kubectl get services
kubectl get svc -o wide

# Describe service (shows endpoints)
kubectl describe service my-service

# Get endpoints directly
kubectl get endpoints my-service

# Expose a deployment quickly
kubectl expose deployment nginx --port=80 --target-port=8080 --type=ClusterIP
kubectl expose deployment nginx --port=80 --target-port=8080 --type=NodePort
kubectl expose deployment nginx --port=80 --target-port=8080 --type=LoadBalancer

# Test service from within cluster
kubectl run -it curl-test --image=curlimages/curl --rm -- curl http://my-service:80

# Port forward for local testing
kubectl port-forward svc/my-service 8080:80

# Delete service
kubectl delete svc my-service
```

## Best Practices

1. **Use ClusterIP** for internal services, NodePort for dev, LoadBalancer for production
2. **Always define selectors** that match your Pod labels exactly
3. **Name your ports** when using multi-port services
4. **Use short DNS names** within same namespace, FQDN for cross-namespace
5. **Set resource requests** on Pods so they become Ready and get endpoints
6. **Test connectivity** from inside the cluster before exposing externally
7. **Monitor endpoints** to detect selector mismatches early
8. **Use readiness probes** to prevent traffic to unhealthy Pods
