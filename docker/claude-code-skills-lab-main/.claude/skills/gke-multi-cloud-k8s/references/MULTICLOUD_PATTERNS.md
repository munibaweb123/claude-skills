# Multi-Cloud Kubernetes Patterns

## Consistent Provision → Connect → Deploy Pattern

### Pattern Overview
The provision → connect → deploy pattern ensures consistent deployment workflows across different cloud providers (GKE, EKS, AKS) by separating concerns into three distinct phases:

1. **Provision**: Set up the Kubernetes infrastructure
2. **Connect**: Establish kubectl connectivity to the cluster
3. **Deploy**: Deploy applications to the cluster

### Benefits
- Reduces cognitive load when switching between providers
- Ensures consistent deployment processes
- Facilitates multi-cloud strategies
- Simplifies disaster recovery planning

## Provider-Specific Implementation

### Google Kubernetes Engine (GKE)
#### Provision Phase
```bash
gcloud container clusters create CLUSTER_NAME \
  --zone=COMPUTE_ZONE \
  --num-nodes=NODE_COUNT \
  --machine-type=MACHINE_TYPE \
  --enable-autoscaling \
  --min-nodes=MIN_NODE_COUNT \
  --max-nodes=MAX_NODE_COUNT
```

#### Connect Phase
```bash
gcloud container clusters get-credentials CLUSTER_NAME \
  --zone=COMPUTE_ZONE \
  --project=PROJECT_ID
```

#### Deploy Phase
Standard kubectl commands:
```bash
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
```

### Amazon EKS
#### Provision Phase
```bash
eksctl create cluster \
  --name CLUSTER_NAME \
  --region REGION \
  --nodegroup-name standard-workers \
  --node-type MACHINE_TYPE \
  --nodes NODE_COUNT \
  --nodes-min MIN_NODES \
  --nodes-max MAX_NODES
```

#### Connect Phase
```bash
aws eks update-kubeconfig --region REGION --name CLUSTER_NAME
```

#### Deploy Phase
Standard kubectl commands:
```bash
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
```

### Azure AKS
#### Provision Phase
```bash
az aks create \
  --resource-group RESOURCE_GROUP \
  --name CLUSTER_NAME \
  --node-count NODE_COUNT \
  --generate-ssh-keys \
  --enable-cluster-autoscaler \
  --min-count MIN_NODES \
  --max-count MAX_NODES
```

#### Connect Phase
```bash
az aks get-credentials --resource-group RESOURCE_GROUP --name CLUSTER_NAME
```

#### Deploy Phase
Standard kubectl commands:
```bash
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
```

## Configuration Management Patterns

### Environment Configuration
Store cloud-specific parameters in separate configuration files:

#### GKE Configuration (gke-config.yaml)
```yaml
provider: gke
region: us-central1
zone: us-central1-a
node_count: 3
machine_type: e2-medium
min_nodes: 1
max_nodes: 10
disk_size_gb: 100
enable_autoscaling: true
project_id: my-project-id
```

#### EKS Configuration (eks-config.yaml)
```yaml
provider: eks
region: us-west-2
node_count: 3
machine_type: m5.large
min_nodes: 1
max_nodes: 10
disk_size_gb: 100
enable_autoscaling: true
cluster_name: my-cluster
```

#### AKS Configuration (aks-config.yaml)
```yaml
provider: aks
resource_group: my-resource-group
location: eastus
node_count: 3
machine_type: Standard_D2_v2
min_nodes: 1
max_nodes: 10
disk_size_gb: 100
enable_autoscaling: true
cluster_name: my-cluster
```

### Infrastructure as Code (IaC) Templates

#### Terraform Variables (variables.tf)
```hcl
variable "provider" {
  description = "Cloud provider (gke, eks, aks)"
  type        = string
}

variable "region" {
  description = "Cloud region"
  type        = string
}

variable "node_count" {
  description = "Initial number of worker nodes"
  type        = number
  default     = 3
}

variable "machine_type" {
  description = "Machine type for worker nodes"
  type        = string
  default     = "e2-medium"
}
```

#### Cloud-Specific Terraform Files
Create provider-specific files (main-gke.tf, main-eks.tf, main-aks.tf) that use the common variables.

## Deployment Manifest Patterns

### Cloud-Agnostic Manifests
Structure Kubernetes manifests to work across providers:

#### Generic Deployment (deployment.yaml)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-deployment
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
      - name: app
        image: my-app:latest
        ports:
        - containerPort: 8080
        resources:
          requests:
            memory: "64Mi"
            cpu: "250m"
          limits:
            memory: "128Mi"
            cpu: "500m"
```

### Cloud-Specific Additions
Add cloud-specific configurations via patches or overlays:

#### GKE Specific (gke-patch.yaml)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-deployment
spec:
  template:
    spec:
      nodeSelector:
        cloud.google.com/gke-nodepool: default-pool
```

#### EKS Specific (eks-patch.yaml)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-deployment
spec:
  template:
    spec:
      nodeSelector:
        eks.amazonaws.com/nodegroup: standard-workers
```

## CI/CD Pipeline Patterns

### Multi-Provider Pipeline
Create a CI/CD pipeline that can deploy to multiple providers:

```yaml
# .github/workflows/deploy.yaml (GitHub Actions example)
name: Deploy to Multiple Clouds

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        provider: [gke, eks, aks]
    steps:
      - uses: actions/checkout@v3

      - name: Set up cloud CLI
        run: |
          if [ "${{ matrix.provider }}" == "gke" ]; then
            # Install gcloud
            curl https://sdk.cloud.google.com | bash
          elif [ "${{ matrix.provider }}" == "eks" ]; then
            # Install AWS CLI and eksctl
            curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
          elif [ "${{ matrix.provider }}" == "aks" ]; then
            # Install Azure CLI
            curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
          fi

      - name: Deploy to ${{ matrix.provider }}
        run: ./scripts/deploy-${{ matrix.provider }}.sh
```

## Cost Management Across Providers

### Cross-Provider Cost Comparison
Create scripts to estimate and compare costs across providers:

#### Cost Estimation Script (compare_costs.sh)
```bash
#!/bin/bash

echo "Cost estimation for 10 nodes of e2-medium equivalent:"
echo "GKE: $${GKE_COST_PER_HOUR} per hour per node"
echo "EKS: $${EKS_COST_PER_HOUR} per hour per node"
echo "AKS: $${AKS_COST_PER_HOUR} per hour per node"

echo "Total monthly cost comparison:"
echo "GKE: $(( ${GKE_COST_PER_HOUR} * 10 * 24 * 30 ))"
echo "EKS: $(( ${EKS_COST_PER_HOUR} * 10 * 24 * 30 ))"
echo "AKS: $(( ${AKS_COST_PER_HOUR} * 10 * 24 * 30 ))"
```

## Security Patterns

### Consistent Identity Management
Use a consistent approach to identity and access management:

#### Common RBAC Configuration (rbac.yaml)
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: app-service-account
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: default
  name: pod-reader
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "watch", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: read-pods
  namespace: default
subjects:
- kind: ServiceAccount
  name: app-service-account
  namespace: default
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

## Monitoring and Observability

### Consistent Monitoring Stack
Deploy the same monitoring stack regardless of cloud provider:

#### Monitoring Manifest (monitoring.yaml)
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: monitoring
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: prometheus
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: prometheus
  template:
    metadata:
      labels:
        app: prometheus
    spec:
      containers:
      - name: prometheus
        image: prom/prometheus:latest
        ports:
        - containerPort: 9090
---
apiVersion: v1
kind: Service
metadata:
  name: prometheus-service
  namespace: monitoring
spec:
  selector:
    app: prometheus
  ports:
    - protocol: TCP
      port: 9090
      targetPort: 9090
  type: LoadBalancer
```

## Testing Across Providers

### Multi-Provider Test Suite
Create tests that can run on any provider:

#### Integration Test (integration_test.go)
```go
package integration

import (
    "testing"
    "k8s.io/client-go/kubernetes"
    // ... other imports
)

func TestDeploymentAcrossProviders(t *testing.T) {
    clientset := getClientset() // Gets client for current provider

    // Test common functionality
    testBasicDeployment(clientset, t)
    testServiceDiscovery(clientset, t)
    testConfigMapMounting(clientset, t)
    testSecretMounting(clientset, t)
}

func getClientset() *kubernetes.Clientset {
    // Logic to get client based on current provider context
    // Uses standard kubectl config
}
```

## Migration Strategies

### Blue-Green Deployment Across Providers
Use consistent blue-green deployment patterns:

#### Blue-Green Template
```yaml
# blue-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app-blue
  labels:
    version: blue
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-app
      version: blue
  template:
    metadata:
      labels:
        app: my-app
        version: blue
    spec:
      containers:
      - name: app
        image: my-app:v1.0.0
---
# green-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app-green
  labels:
    version: green
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-app
      version: green
  template:
    metadata:
      labels:
        app: my-app
        version: green
    spec:
      containers:
      - name: app
        image: my-app:v2.0.0
```

This approach ensures consistent, portable, and maintainable Kubernetes deployments across different cloud providers while leveraging each provider's strengths.