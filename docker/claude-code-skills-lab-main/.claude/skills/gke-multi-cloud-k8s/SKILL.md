---
name: gke-multi-cloud-k8s
description: Multi-cloud Kubernetes deployment skill focused on Google Kubernetes Engine (GKE) for provisioning, managing, and optimizing GKE clusters on Google Cloud Platform. Enables consistent provision → connect → deploy pattern across clouds (GKE, EKS, AKS) with cost optimization strategies and node pool management.
---

# GKE Multi-Cloud Kubernetes Deployment Skill

## Overview

This skill enables the provisioning, management, and optimization of Google Kubernetes Engine (GKE) clusters with a consistent multi-cloud pattern. It follows the provision → connect → deploy pattern that can be extended to other providers (AWS EKS, Azure AKS).

## Prerequisites

- Google Cloud SDK (`gcloud`) installed and authenticated
- `kubectl` installed
- Proper GCP authentication configured (`gcloud auth login` and `gcloud auth application-default login`)

## When to Use This Skill

Use this skill when you need to:
- Provision GKE clusters on Google Cloud Platform
- Configure node pools and autoscaling for GKE clusters
- Connect kubectl to GKE clusters
- Apply cost optimization strategies to GKE deployments
- Deploy applications consistently across multiple cloud providers using a standardized pattern

## Provision → Connect → Deploy Pattern

### 1. Provision Phase
- Create GKE clusters with appropriate configuration
- Set up node pools with desired specifications
- Configure autoscaling and network settings

### 2. Connect Phase
- Authenticate kubectl with the target cluster
- Verify cluster connectivity and readiness

### 3. Deploy Phase
- Deploy applications to the connected cluster
- Verify deployment status and health

## GKE Cluster Provisioning

### Basic Cluster Creation

```bash
gcloud container clusters create CLUSTER_NAME \
  --zone=COMPUTE_ZONE \
  --num-nodes=NODE_COUNT \
  --machine-type=MACHINE_TYPE \
  --enable-autoscaling \
  --min-nodes=MIN_NODE_COUNT \
  --max-nodes=MAX_NODE_COUNT
```

Example:
```bash
gcloud container clusters create my-cluster \
  --zone=us-central1-a \
  --num-nodes=3 \
  --machine-type=e2-medium \
  --enable-autoscaling \
  --min-nodes=1 \
  --max-nodes=10
```

### Node Pool Management

Create additional node pools for specific workloads:
```bash
gcloud container node-pools create POOL_NAME \
  --cluster=CLUSTER_NAME \
  --zone=COMPUTE_ZONE \
  --num-nodes=NODE_COUNT \
  --machine-type=MACHINE_TYPE \
  --enable-autoscaling \
  --min-nodes=MIN_NODE_COUNT \
  --max-nodes=MAX_NODE_COUNT
```

Example for GPU workloads:
```bash
gcloud container node-pools create gpu-pool \
  --cluster=my-cluster \
  --zone=us-central1-a \
  --num-nodes=1 \
  --machine-type=n1-standard-4 \
  --accelerator=type=nvidia-tesla-k80,count=1 \
  --enable-autoscaling \
  --min-nodes=0 \
  --max-nodes=3
```

## Connecting to the Cluster

After cluster creation, configure kubectl to connect to the cluster:

```bash
gcloud container clusters get-credentials CLUSTER_NAME \
  --zone=COMPUTE_ZONE \
  --project=PROJECT_ID
```

Example:
```bash
gcloud container clusters get-credentials my-cluster \
  --zone=us-central1-a \
  --project=my-project-id
```

Verify connection:
```bash
kubectl cluster-info
kubectl get nodes
```

## Cost Optimization Strategies

### Machine Type Selection

Choose appropriate machine types based on workload requirements:
- `e2-*` series: General-purpose, cost-effective for most workloads
- `n1-*` series: Standard virtual machines for compute-intensive workloads
- `n2-*` and `n2d-*` series: Higher performance for compute-intensive workloads
- `t2d-*` and `t2a-*` series: Arm-based instances for cost-effective performance

### Autoscaling Configuration

Configure cluster autoscaling:
```bash
--enable-autoscaling \
--min-nodes=MIN_NODE_COUNT \
--max-nodes=MAX_NODE_COUNT \
--node-labels=workload-type=general-purpose
```

Configure vertical pod autoscaling:
```bash
--enable-vertical-pod-autoscaling
```

### Rightsizing Practices

- Monitor resource usage and adjust node pools accordingly
- Use preemptible nodes for fault-tolerant workloads
- Configure resource quotas and limits appropriately

### Preemptible Nodes

For fault-tolerant workloads, use preemptible nodes for cost savings:
```bash
gcloud container clusters create my-cluster \
  --zone=us-central1-a \
  --num-nodes=3 \
  --enable-autoscaling \
  --min-nodes=1 \
  --max-nodes=10 \
  --preemptible
```

## Multi-Cloud Portability Patterns

The provision → connect → deploy pattern applies consistently across cloud providers:

### GKE Pattern
1. Provision: `gcloud container clusters create ...`
2. Connect: `gcloud container clusters get-credentials ...`
3. Deploy: Standard `kubectl` commands

### Common Configuration Template

Store cloud-specific parameters in configuration files:

```yaml
# gke-config.yaml
provider: gke
region: us-central1
zone: us-central1-a
node_count: 3
machine_type: e2-medium
min_nodes: 1
max_nodes: 10
disk_size_gb: 100
enable_autoscaling: true
```

## Security Best Practices

### Authentication
- Use Workload Identity for secure pod-to-GCP service communication
- Enable private clusters to restrict public access
- Configure master authorized networks for API server access

### Example Secure Cluster
```bash
gcloud container clusters create secure-cluster \
  --zone=us-central1-a \
  --num-nodes=1 \
  --machine-type=e2-medium \
  --enable-private-nodes \
  --master-ipv4-cidr-block=172.16.0.0/28 \
  --enable-master-authorized-networks \
  --master-authorized-networks=YOUR_IP/32
```

## Monitoring and Maintenance

### Health Checks
- Regularly check cluster status: `gcloud container clusters describe CLUSTER_NAME`
- Monitor node conditions: `kubectl get nodes -o wide`
- Review cluster events: `kubectl get events`

### Updates
- Enable automatic node updates: `--enable-autoupgrade`
- Schedule maintenance windows appropriately

## Troubleshooting Common Issues

### Connection Issues
- Verify `gcloud` authentication: `gcloud auth list`
- Ensure kubectl is properly configured: `kubectl config current-context`
- Check if the cluster exists and is running: `gcloud container clusters list`

### Resource Limitations
- Increase node pool sizes if pods are stuck in Pending state
- Adjust resource requests and limits appropriately
- Verify that quota is sufficient for the desired configuration

## Extending to Other Providers

### AWS EKS Pattern
1. Provision: `aws eks create-cluster ...`
2. Connect: `aws eks update-kubeconfig ...`
3. Deploy: Standard `kubectl` commands

### Azure AKS Pattern
1. Provision: `az aks create ...`
2. Connect: `az aks get-credentials ...`
3. Deploy: Standard `kubectl` commands

This consistent pattern enables seamless multi-cloud Kubernetes deployments.