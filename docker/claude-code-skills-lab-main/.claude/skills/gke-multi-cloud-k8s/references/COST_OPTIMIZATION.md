# GKE Cost Optimization Strategies

## Machine Type Selection

### Compute-Optimized Types
- `c2-*`, `c2d-*`: For compute-intensive workloads
- `n1-highcpu-*`, `n2-highcpu-*`: CPU-optimized for compute-heavy tasks

### Memory-Optimized Types
- `n1-highmem-*`, `n2-highmem-*`: For memory-intensive workloads
- `m1-*`, `m2-*`: Ultra high-memory machines for in-memory databases

### Balanced Types
- `e2-*` (most cost-effective): Good for general-purpose workloads
- `n1-standard-*`, `n2-standard-*`: Balanced compute and memory

### Spot/Preemptible VMs
- Up to 91% cost savings compared to regular instances
- Ideal for fault-tolerant, batch processing, or stateless applications
- Termination notice: 30 seconds advance notice

## Node Pool Strategies

### Sizing Considerations
- Right-size nodes to avoid over-provisioning
- Use Vertical Pod Autoscaler (VPA) to optimize resource requests
- Monitor resource utilization regularly
- Scale down during low-demand periods

### Multi-Tenancy
- Separate node pools for different workloads (dev/staging/prod)
- Dedicated node pools for specific requirements (GPU, high memory)
- Isolate noisy neighbors with dedicated hardware

## Storage Cost Optimization

### Persistent Disk Types
- `pd-standard`: Lower cost, suitable for development
- `pd-ssd`: Higher performance, higher cost, for production workloads
- `pd-balanced`: Good balance of price and performance

### Storage Classes Configuration
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
provisioner: kubernetes.io/gce-pd
parameters:
  type: pd-ssd
  replication-type: none
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
```

## Autoscaling Best Practices

### Cluster Autoscaling
```bash
# Enable cluster autoscaling
gcloud container clusters create my-cluster \
  --zone=us-central1-a \
  --num-nodes=1 \
  --enable-autoscaling \
  --min-nodes=1 \
  --max-nodes=10 \
  --total-min-nodes=1 \
  --total-max-nodes=50
```

### Horizontal Pod Autoscaler (HPA)
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: app-deployment
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

### Vertical Pod Autoscaler (VPA)
```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: app-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: app-deployment
  updatePolicy:
    updateMode: "Auto"
```

## Resource Management

### Resource Requests and Limits
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-pod
spec:
  containers:
  - name: app-container
    image: my-app:latest
    resources:
      requests:
        memory: "64Mi"
        cpu: "250m"
      limits:
        memory: "128Mi"
        cpu: "500m"
```

### Quality of Service (QoS) Classes
- **Guaranteed**: Limits equal to requests for all resources
- **Burstable**: At least one resource has requests different from limits
- **BestEffort**: No resource requests or limits specified

## Billing and Budget Controls

### Set Budget Alerts
```bash
# Create a budget alert for GKE spending
gcloud beta billing budgets create \
  --billing-account YOUR_BILLING_ACCOUNT_ID \
  --display-name="GKE Monthly Budget" \
  --budget-amount=1000 \
  --thresholds="0.5,0.75,0.9,1.0" \
  --monitoring-subscriptions=your-email@example.com
```

### Labels for Cost Allocation
```bash
# Create cluster with labels for cost tracking
gcloud container clusters create my-cluster \
  --zone=us-central1-a \
  --num-nodes=3 \
  --labels=environment=production,team=backend,application=webserver
```

## Reserved Instances and Committed Use Discounts

### Committed Use Contracts
- 1-year or 3-year commitments for sustained usage discounts
- Up to 57% discount for 1-year commitment
- Up to 70% discount for 3-year commitment

### Sustained Use Discounts
- Automatic discount based on monthly usage
- Up to 30% discount for 25%+ monthly usage
- Up to 57% discount for 50%+ monthly usage

## Monitoring Cost Optimization Effectiveness

### Key Metrics to Track
- Average CPU and memory utilization
- Number of autoscaled nodes
- Cost per request/response
- Over-provisioned vs. requested resources

### Sample Monitoring Dashboard Setup
```bash
# Install GKE monitoring tools
kubectl apply -f https://raw.githubusercontent.com/GoogleCloudPlatform/k8s-stackdriver/master/custom-metrics-stackdriver-adapter/deploy/production/adapter.yaml

# Create cost monitoring configmap
kubectl create configmap cost-monitoring \
  --from-literal=cost-optimization-config.yaml
```

## Multi-Zone Deployment Strategies

### Regional Clusters
```bash
# Create regional cluster for high availability
gcloud container clusters create my-regional-cluster \
  --region=us-central1 \
  --node-locations=us-central1-a,us-central1-b,us-central1-c \
  --num-nodes=1 \
  --enable-autoscaling \
  --min-nodes=1 \
  --max-nodes=10
```

### Multi-Zone Node Pools
- Distribute node pools across zones to ensure availability
- Balance cost with latency requirements
- Consider proximity to users for performance

This guide helps achieve optimal cost efficiency while maintaining required performance levels for GKE deployments.