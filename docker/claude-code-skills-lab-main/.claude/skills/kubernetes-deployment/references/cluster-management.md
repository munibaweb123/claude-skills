# Cluster Verification & Context Management

## Cluster Health Verification

### Check Cluster Connectivity

```bash
# Display control plane and cluster services
kubectl cluster-info

# Example output:
# Kubernetes control plane is running at https://kubernetes.docker.internal:6443
# CoreDNS is running at https://kubernetes.docker.internal:6443/api/v1/namespaces/kube-system/services/kube-dns:dns/proxy
```

### Check Node Status

```bash
# List all nodes and their status
kubectl get nodes

# Example output:
# NAME             STATUS   ROLES           AGE   VERSION
# docker-desktop   Ready    control-plane   1d    v1.34.1

# Detailed node information
kubectl get nodes -o wide

# Describe a specific node
kubectl describe node <node-name>
```

### Check System Pods

```bash
# View all system pods
kubectl get pods -n kube-system

# Check if core components are running
kubectl get pods -n kube-system -o wide
```

### Check API Server Health

```bash
# Simple API connectivity test
kubectl get --raw='/healthz'

# Detailed health check
kubectl get --raw='/healthz?verbose'

# Check API versions available
kubectl api-versions
```

---

## Kubeconfig Management

### Kubeconfig File Location

Default location: `~/.kube/config`

```bash
# View kubeconfig file path
echo $KUBECONFIG

# If empty, default is used:
# Linux/Mac: ~/.kube/config
# Windows: %USERPROFILE%\.kube\config
```

### Kubeconfig Structure

```yaml
apiVersion: v1
kind: Config
preferences: {}

clusters:
- cluster:
    server: https://cluster-api-endpoint:6443
    certificate-authority-data: <base64-encoded-ca>
  name: my-cluster

users:
- name: my-user
  user:
    client-certificate-data: <base64-encoded-cert>
    client-key-data: <base64-encoded-key>

contexts:
- context:
    cluster: my-cluster
    namespace: default
    user: my-user
  name: my-context

current-context: my-context
```

---

## Context Management

A **context** combines a cluster, user, and namespace into a named configuration.

### View Contexts

```bash
# List all available contexts
kubectl config get-contexts

# Example output:
# CURRENT   NAME             CLUSTER          AUTHINFO         NAMESPACE
# *         docker-desktop   docker-desktop   docker-desktop
#           minikube         minikube         minikube         default

# Show current context only
kubectl config current-context
```

### Switch Contexts

```bash
# Switch to a different context
kubectl config use-context docker-desktop

# Switch to minikube
kubectl config use-context minikube
```

### Set Default Namespace for Context

```bash
# Set default namespace for current context
kubectl config set-context --current --namespace=production

# Verify the change
kubectl config view --minify | grep namespace
```

### Create a New Context

```bash
# Create context combining existing cluster and user
kubectl config set-context my-new-context \
  --cluster=my-cluster \
  --user=my-user \
  --namespace=my-namespace
```

---

## Cluster Configuration

### View Current Configuration

```bash
# View full kubeconfig
kubectl config view

# View current context only (minimal output)
kubectl config view --minify

# View raw config (including secrets)
kubectl config view --raw
```

### Add a New Cluster

```bash
# Add cluster with certificate authority
kubectl config set-cluster my-cluster \
  --server=https://1.2.3.4:6443 \
  --certificate-authority=/path/to/ca.crt

# Add cluster with embedded CA data
kubectl config set-cluster my-cluster \
  --server=https://1.2.3.4:6443 \
  --certificate-authority-data=<base64-ca-data>

# Add cluster (skip TLS verification - not recommended for production)
kubectl config set-cluster my-cluster \
  --server=https://1.2.3.4:6443 \
  --insecure-skip-tls-verify=true
```

### Add User Credentials

```bash
# Add user with client certificate
kubectl config set-credentials my-user \
  --client-certificate=/path/to/client.crt \
  --client-key=/path/to/client.key

# Add user with token
kubectl config set-credentials my-user \
  --token=<bearer-token>
```

### Delete Configuration

```bash
# Delete a context
kubectl config delete-context my-context

# Delete a cluster
kubectl config delete-cluster my-cluster

# Delete a user
kubectl config delete-user my-user

# Unset specific values
kubectl config unset users.my-user
kubectl config unset clusters.my-cluster
kubectl config unset contexts.my-context
```

---

## Multiple Kubeconfig Files

### Merge Multiple Files

```bash
# Linux/Mac (colon-separated)
export KUBECONFIG=~/.kube/config:~/.kube/config-dev:~/.kube/config-prod

# Windows PowerShell (semicolon-separated)
$Env:KUBECONFIG="$HOME\.kube\config;$HOME\.kube\config-dev"

# View merged configuration
kubectl config view
```

### Use Specific Kubeconfig

```bash
# Use specific kubeconfig for a command
kubectl --kubeconfig=/path/to/config get pods

# Or set environment variable
export KUBECONFIG=/path/to/config
kubectl get pods
```

---

## Troubleshooting Connectivity

### Common Issues

| Error | Cause | Solution |
|-------|-------|----------|
| `connection refused` | Cluster not running | Start your cluster (minikube start, etc.) |
| `certificate signed by unknown authority` | CA mismatch | Check certificate-authority in kubeconfig |
| `Unauthorized` | Invalid credentials | Check user credentials, token expiry |
| `no such host` | DNS/network issue | Check server URL, network connectivity |

### Diagnostic Commands

```bash
# Test API server connectivity
kubectl cluster-info

# Check if kubectl can reach the cluster
kubectl get --raw='/healthz'

# Verbose output for debugging
kubectl get nodes -v=6

# Very verbose (shows HTTP requests)
kubectl get nodes -v=9

# Dump cluster info for debugging
kubectl cluster-info dump

# Check current context
kubectl config current-context

# Verify kubeconfig is valid
kubectl config view
```

### Reset Kubeconfig

```bash
# Backup current config
cp ~/.kube/config ~/.kube/config.backup

# Start fresh (will need to reconfigure)
rm ~/.kube/config
```

---

## Quick Reference

| Command | Purpose |
|---------|---------|
| `kubectl cluster-info` | Show cluster endpoint and services |
| `kubectl get nodes` | List nodes and status |
| `kubectl config get-contexts` | List all contexts |
| `kubectl config current-context` | Show current context |
| `kubectl config use-context <name>` | Switch context |
| `kubectl config view` | View kubeconfig |
| `kubectl config view --minify` | View current context config |
| `kubectl config set-context --current --namespace=<ns>` | Set default namespace |
