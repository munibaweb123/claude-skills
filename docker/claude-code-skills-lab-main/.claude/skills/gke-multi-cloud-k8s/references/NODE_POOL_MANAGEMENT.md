# GKE Node Pool Management

## Node Pool Fundamentals

A node pool is a collection of nodes within a cluster that all have the same configuration. When you create a cluster, it initially contains a default node pool with preset properties.

### Key Properties
- **Machine type**: Compute resources allocated per node
- **Number of nodes**: Initial cluster size
- **Disk size/type**: Storage capacity per node
- **Image type**: OS image running on nodes
- **Labels and taints**: Node identification and scheduling constraints

## Creating Node Pools

### Basic Node Pool Creation
```bash
gcloud container node-pools create pool-name \
  --cluster=cluster-name \
  --zone=compute-zone \
  --num-nodes=3 \
  --machine-type=e2-medium \
  --disk-type=pd-standard \
  --disk-size=100GB
```

### Advanced Node Pool Configuration
```bash
gcloud container node-pools create gpu-pool \
  --cluster=my-cluster \
  --zone=us-central1-a \
  --num-nodes=1 \
  --machine-type=n1-standard-4 \
  --accelerator=type=nvidia-tesla-k80,count=1 \
  --enable-autoscaling \
  --min-nodes=0 \
  --max-nodes=3 \
  --scopes=cloud-platform
```

## Node Pool Autoscaling

### Enable Autoscaling for Existing Node Pool
```bash
gcloud container node-pools update pool-name \
  --cluster=cluster-name \
  --zone=compute-zone \
  --enable-autoscaling \
  --min-nodes=1 \
  --max-nodes=10
```

### Disable Autoscaling
```bash
gcloud container node-pools update pool-name \
  --cluster=cluster-name \
  --zone=compute-zone \
  --no-enable-autoscaling
```

## Node Pool Maintenance

### Upgrading Node Pools
```bash
# Upgrade to latest stable version
gcloud container node-pools update pool-name \
  --cluster=cluster-name \
  --zone=compute-zone \
  --node-version=latest

# Upgrade to specific version
gcloud container node-pools update pool-name \
  --cluster=cluster-name \
  --zone=compute-zone \
  --node-version=1.24.3-gke.1200
```

### Updating Node Pool Size
```bash
gcloud container node-pools update pool-name \
  --cluster=cluster-name \
  --zone=compute-zone \
  --num-nodes=5
```

## Taints and Tolerations

### Adding Taints to Node Pools
```bash
gcloud container node-pools create dedicated-pool \
  --cluster=cluster-name \
  --zone=compute-zone \
  --num-nodes=3 \
  --machine-type=e2-medium \
  --node-taints=dedicated=experimental:NoSchedule,key=value:NoExecute
```

### Using Taints in Pod Specifications
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: with-toleration
spec:
  containers:
  - name: toleration-container
    image: nginx
  tolerations:
  - key: dedicated
    operator: Equal
    value: experimental
    effect: NoSchedule
```

## Node Pool Labels and Tags

### Creating Node Pools with Labels
```bash
gcloud container node-pools create labeled-pool \
  --cluster=cluster-name \
  --zone=compute-zone \
  --num-nodes=2 \
  --machine-type=e2-medium \
  --labels=env=prod,team=backend,app=webserver
```

### Adding Labels to Existing Node Pools
```bash
gcloud container node-pools update pool-name \
  --cluster=cluster-name \
  --zone=compute-zone \
  --labels=env=prod,team=backend
```

## Pod Affinity and Anti-Affinity

### Node Affinity Example
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: with-node-affinity
spec:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: team
            operator: In
            values:
            - backend
            - frontend
  containers:
  - name: affinity-container
    image: nginx
```

### Pod Anti-Affinity Example
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - nginx
              topologyKey: kubernetes.io/hostname
      containers:
      - name: nginx
        image: nginx:1.15.4
```

## Node Pool Networking

### Creating Private Node Pools
```bash
gcloud container node-pools create private-pool \
  --cluster=cluster-name \
  --zone=compute-zone \
  --num-nodes=2 \
  --machine-type=e2-medium \
  --enable-private-nodes \
  --node-network=projects/PROJECT_ID/global/networks/private-net \
  --node-subnetwork=subnet-name
```

### Secondary Ranges for Pods and Services
```bash
gcloud container clusters create cluster-with-ranges \
  --zone=us-central1-a \
  --num-nodes=3 \
  --enable-ip-alias \
  --create-secondary-range=pods-10.4.0.0/14,services-10.6.0.0/20
```

## Specialized Node Pools

### GPU Node Pools
```bash
gcloud container node-pools create gpu-pool \
  --cluster=cluster-name \
  --zone=compute-zone \
  --num-nodes=1 \
  --machine-type=n1-standard-4 \
  --accelerator=type=nvidia-tesla-t4,count=1 \
  --enable-autoscaling \
  --min-nodes=0 \
  --max-nodes=3
```

### Spot (Preemptible) Node Pools
```bash
gcloud container node-pools create spot-pool \
  --cluster=cluster-name \
  --zone=compute-zone \
  --num-nodes=3 \
  --machine-type=e2-medium \
  --preemptible \
  --node-taints=spot-instance=true:NoSchedule
```

## Managing Node Pools with kubectl

### Listing Node Pools
```bash
kubectl get nodes -L cloud.google.com/gke-nodepool
```

### Checking Node Pool Details
```bash
kubectl describe nodes -l cloud.google.com/gke-nodepool=pool-name
```

## Node Pool Lifecycle Management

### Draining and Deleting Nodes
```bash
# Drain a specific node
kubectl drain NODE_NAME --ignore-daemonsets --delete-emptydir-data

# Delete the node after draining
kubectl delete node NODE_NAME
```

### Deleting Node Pools
```bash
gcloud container node-pools delete pool-name \
  --cluster=cluster-name \
  --zone=compute-zone
```

## Best Practices

1. **Separate Workloads**: Create dedicated node pools for different workload types (stateful, stateless, GPU, etc.)

2. **Right-sizing**: Match machine types to workload requirements to avoid over-provisioning

3. **Labeling Strategy**: Use a consistent labeling strategy for easy management and monitoring

4. **Autoscaling Configuration**: Set appropriate min/max bounds for effective cost management

5. **Maintenance Windows**: Schedule maintenance during low-traffic periods

6. **Monitoring**: Regularly monitor resource utilization and node pool performance

7. **Security**: Apply appropriate security configurations (taints, network policies) to sensitive workloads

8. **Version Alignment**: Keep node pool versions aligned with cluster version for compatibility