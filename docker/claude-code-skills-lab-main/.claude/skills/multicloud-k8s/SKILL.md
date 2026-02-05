---
name: multicloud-k8s
description: |
  Provision and manage budget-friendly Kubernetes clusters on DigitalOcean (DOKS via doctl) and Hetzner Cloud (K3s via hetzner-k3s CLI). This skill should be used when users need to create K8s clusters on affordable cloud providers, manage multi-cloud Kubernetes environments, connect clusters to kubectl, compare provider costs, optimize cloud spending, or implement the provision-connect-deploy pattern across DigitalOcean and Hetzner.
---

# Multi-Cloud Kubernetes Deployment

Provision, connect, and manage Kubernetes clusters on budget-friendly providers — DigitalOcean DOKS and Hetzner Cloud K3s — with a unified workflow.

## What This Skill Does

- Provisions DOKS clusters via `doctl` CLI
- Provisions Hetzner K3s clusters via `hetzner-k3s` CLI
- Manages multi-cluster kubeconfig (merge, switch, verify)
- Compares costs and recommends optimal configurations
- Guides the provision → connect → deploy pattern across clouds

## What This Skill Does NOT Do

- Manage AWS EKS, GKE, or AKS clusters
- Handle application-level deployment (use `argocd-gitops` or `kubernetes-deployment` skills)
- Configure service mesh or multi-cluster networking (Istio, Linkerd)
- Manage DNS or domain routing between clusters

---

## Before Implementation

Gather context to ensure successful implementation:

| Source | Gather |
|--------|--------|
| **Conversation** | User's provider preference, cluster purpose, budget, region needs |
| **Skill References** | Provider-specific CLI reference from `references/` |
| **Environment** | Existing kubeconfig, installed CLIs (`doctl`, `hetzner-k3s`, `kubectl`) |
| **User Guidelines** | Naming conventions, network policies, security requirements |

Only ask user for THEIR specific requirements (provider docs are in this skill).

---

## Required Clarifications

Ask about USER'S context (not provider knowledge):

1. **Provider**: "Which provider — DigitalOcean, Hetzner, or both?"
2. **Purpose**: "Dev/staging/production? What workloads?"
3. **Budget**: "Monthly budget target?"
4. **Region**: "Geographic requirements for your clusters?"

---

## Workflow: Provision → Connect → Deploy

```
1. PROVISION          2. CONNECT              3. DEPLOY
   DigitalOcean          Merge kubeconfig        kubectl apply
   doctl k8s create      Set context             or GitOps sync
       ─── or ───        Verify access
   Hetzner               Label contexts
   hetzner-k3s create
```

### Step 1: Provision

Choose provider based on requirements:

| Factor | DigitalOcean DOKS | Hetzner K3s |
|--------|-------------------|-------------|
| **Control plane** | Managed (free) | Self-managed (K3s on your VMs) |
| **Minimum cost** | ~$24/mo (2-node basic) | ~$6/mo (1 CX22 node) |
| **HA control plane** | $40/mo add-on | Free (3 masters across locations) |
| **Regions** | NYC, SFO, AMS, LON, SGP, BLR, SYD, TOR, FRA | FSN, NBG, HEL, ASH, HIL, SIN |
| **Autoscaling** | Built-in node pool autoscaling | Cluster Autoscaler add-on |
| **Setup complexity** | Low (single CLI command) | Low (YAML config + single command) |
| **K8s conformance** | Full CNCF certified | K3s (lightweight, CNCF certified) |
| **Best for** | Managed simplicity, US/Asia presence | Lowest cost, EU presence, ARM64 nodes |

### Step 2: Connect

After provisioning, merge kubeconfigs so `kubectl` can reach all clusters:

```bash
# DigitalOcean — auto-adds to kubeconfig
doctl kubernetes cluster kubeconfig save <cluster-name>

# Hetzner — kubeconfig written to path specified in config
export KUBECONFIG=~/.kube/config:./kubeconfig
kubectl config view --merge --flatten > ~/.kube/merged-config
mv ~/.kube/merged-config ~/.kube/config

# List all contexts
kubectl config get-contexts

# Switch between clusters
kubectl config use-context do-nyc1-my-doks-cluster
kubectl config use-context my-hetzner-cluster

# Verify connectivity
kubectl --context=do-nyc1-my-doks-cluster get nodes
kubectl --context=my-hetzner-cluster get nodes
```

### Step 3: Deploy

Deploy workloads to any connected cluster:

```bash
# Deploy to specific cluster
kubectl --context=do-nyc1-my-doks-cluster apply -f k8s/

# Or set default context and deploy
kubectl config use-context my-hetzner-cluster
kubectl apply -f k8s/
```

---

## DigitalOcean DOKS Quick Reference

### Prerequisites

```bash
# Install doctl
brew install doctl                    # macOS
snap install doctl                    # Linux

# Authenticate
doctl auth init                       # interactive token prompt
# or: doctl auth init --access-token <token>

# Verify
doctl account get
```

### Provision Cluster

```bash
# Minimal dev cluster
doctl kubernetes cluster create my-dev \
  --region nyc1 \
  --size s-2vcpu-4gb \
  --count 2

# Production HA cluster with custom node pool
doctl kubernetes cluster create my-prod \
  --region nyc1 \
  --version latest \
  --ha \
  --auto-upgrade \
  --maintenance-window saturday=02:00 \
  --node-pool "name=app-pool;size=s-4vcpu-8gb;count=3;auto-scale=true;min-nodes=3;max-nodes=10;label=workload=app" \
  --node-pool "name=worker-pool;size=s-2vcpu-4gb;count=2;auto-scale=true;min-nodes=1;max-nodes=5;label=workload=worker;taint=dedicated=worker:NoSchedule"
```

### Manage Cluster

```bash
doctl kubernetes cluster list                              # list clusters
doctl kubernetes cluster get <name>                        # cluster details
doctl kubernetes cluster delete <name>                     # delete cluster
doctl kubernetes cluster kubeconfig save <name>            # save kubeconfig
doctl kubernetes cluster node-pool list <cluster>          # list node pools
doctl kubernetes cluster node-pool create <cluster> \      # add node pool
  --name new-pool --size s-4vcpu-8gb --count 3
doctl kubernetes cluster node-pool update <cluster> <pool> \  # resize
  --count 5
doctl kubernetes cluster node-pool delete <cluster> <pool> # remove pool
doctl kubernetes options versions                          # available K8s versions
doctl kubernetes options sizes                             # available node sizes
doctl kubernetes options regions                           # available regions
```

> Full CLI reference: `references/digitalocean-doks.md`

---

## Hetzner K3s Quick Reference

### Prerequisites

```bash
# Install hetzner-k3s
brew install vitobotta/tap/hetzner_k3s        # macOS/Linux

# Or download binary
wget https://github.com/vitobotta/hetzner-k3s/releases/latest/download/hetzner-k3s-linux-amd64
chmod +x hetzner-k3s-linux-amd64 && sudo mv hetzner-k3s-linux-amd64 /usr/local/bin/hetzner-k3s

# Generate SSH key (if needed)
ssh-keygen -t ed25519 -f ~/.ssh/hetzner_k3s -N ""

# Get Hetzner API token: https://console.hetzner.cloud → Project → Security → API Tokens
```

### Provision Cluster

Create a YAML config file, then run one command:

```yaml
# cluster-dev.yaml — minimal dev cluster
hetzner_token: <your-token>
cluster_name: my-dev
kubeconfig_path: "./kubeconfig"
k3s_version: v1.32.0+k3s1

networking:
  ssh:
    port: 22
    use_agent: false
    public_key_path: "~/.ssh/hetzner_k3s.pub"
    private_key_path: "~/.ssh/hetzner_k3s"
  allowed_networks:
    ssh:
      - 0.0.0.0/0
    api:
      - 0.0.0.0/0

masters_pool:
  instance_type: cx22
  instance_count: 1
  location: fsn1

worker_node_pools:
  - name: workers
    instance_type: cx22
    instance_count: 2
    location: fsn1
```

```yaml
# cluster-prod.yaml — HA production cluster
hetzner_token: <your-token>
cluster_name: my-prod
kubeconfig_path: "./kubeconfig-prod"
k3s_version: v1.32.0+k3s1
schedule_workloads_on_masters: false
protect_against_deletion: true

networking:
  ssh:
    port: 22
    use_agent: false
    public_key_path: "~/.ssh/hetzner_k3s.pub"
    private_key_path: "~/.ssh/hetzner_k3s"
  allowed_networks:
    ssh:
      - <your-ip>/32
    api:
      - <your-ip>/32
  private_network:
    enabled: true
    subnet: 10.0.0.0/16
  cni:
    enabled: true
    mode: cilium

masters_pool:
  instance_type: cpx22
  instance_count: 3
  locations:
    - fsn1
    - nbg1
    - hel1

worker_node_pools:
  - name: app
    instance_type: cpx32
    instance_count: 3
    location: fsn1
    labels:
      - key: workload
        value: app
  - name: worker
    instance_type: cax21
    instance_count: 2
    location: fsn1
    labels:
      - key: workload
        value: background
    autoscaling:
      enabled: true
      min_instances: 1
      max_instances: 10
```

```bash
# Create cluster
hetzner-k3s create --config cluster-dev.yaml

# Delete cluster
hetzner-k3s delete --config cluster-dev.yaml

# Upgrade K3s version (edit k3s_version in config, then)
hetzner-k3s upgrade --config cluster-dev.yaml
```

> Full configuration reference: `references/hetzner-k3s.md`

---

## Multi-Cloud Kubeconfig Management

### Naming Convention

Use a consistent pattern: `<provider>-<region>-<cluster-name>`

```bash
# Rename contexts for clarity
kubectl config rename-context do-nyc1-my-prod do-nyc1-prod
kubectl config rename-context my-hetzner-cluster hetzner-fsn1-prod
```

### Merge Multiple Kubeconfigs

```bash
# Temporary merge (session only)
export KUBECONFIG=~/.kube/config:./kubeconfig-hetzner:./kubeconfig-do

# Permanent merge
KUBECONFIG=~/.kube/config:./kubeconfig-hetzner kubectl config view \
  --merge --flatten > ~/.kube/merged && mv ~/.kube/merged ~/.kube/config
```

### Cross-Cluster Commands

```bash
# Run against specific cluster without switching context
kubectl --context=do-nyc1-prod get pods -A
kubectl --context=hetzner-fsn1-prod get nodes

# Compare node status across clusters
for ctx in do-nyc1-prod hetzner-fsn1-prod; do
  echo "=== $ctx ==="
  kubectl --context=$ctx get nodes -o wide
done
```

> Full reference: `references/multi-cluster-kubectl.md`

---

## Cost-Optimized Cluster Configurations

### Tier 1: Hobby/Learning (~$6-12/mo)

| Provider | Config | Monthly Cost |
|----------|--------|:------------:|
| **Hetzner** | 1x CX22 (2vCPU/4GB) single-node | ~$3-4 |
| **Hetzner** | 1x CX22 master + 2x CX22 workers | ~$9-12 |
| **DigitalOcean** | Free CP + 1x s-1vcpu-2gb | ~$12 |

### Tier 2: Startup/Staging (~$24-60/mo)

| Provider | Config | Monthly Cost |
|----------|--------|:------------:|
| **Hetzner** | 3x CPX22 masters (HA) + 3x CPX32 workers | ~$58 |
| **DigitalOcean** | Free CP + 3x s-2vcpu-4gb | ~$72 |
| **DigitalOcean** | HA CP + 3x s-2vcpu-4gb | ~$112 |

### Tier 3: Production (~$60-200/mo)

| Provider | Config | Monthly Cost |
|----------|--------|:------------:|
| **Hetzner** | 3x CPX22 HA + 10x CPX32 + autoscaling | ~$135 |
| **Hetzner** | 3x CPX22 HA + 10x CAX21 ARM64 + autoscaling | ~$100 |
| **DigitalOcean** | HA CP + 5x s-4vcpu-8gb + autoscaling | ~$280 |

> Full cost analysis and optimization strategies: `references/cost-optimization.md`

---

## Provider Decision Guide

```
What's your priority?
│
├── Lowest possible cost?
│   └── Hetzner (2-4x cheaper than DO at equivalent specs)
│
├── Managed control plane (zero K8s ops)?
│   └── DigitalOcean DOKS (free managed CP)
│
├── EU data residency?
│   └── Hetzner (Germany, Finland datacenters)
│
├── US/Asia presence?
│   └── DigitalOcean (NYC, SFO, SGP, BLR, SYD)
│       Note: Hetzner has ASH (US) and SIN (Singapore) too
│
├── ARM64 cost savings?
│   └── Hetzner CAX series (Ampere ARM, cheapest compute)
│
├── Simplest setup (single command)?
│   └── DigitalOcean (`doctl k8s cluster create` — one line)
│
├── Full infrastructure control?
│   └── Hetzner (you own the VMs, SSH access, custom networking)
│
└── Both? Multi-cloud resilience?
    └── Use both — provision each, merge kubeconfigs, deploy via GitOps
```

---

## Output Checklist

Before delivering, verify:

- [ ] Correct CLI installed and authenticated (`doctl auth init` / Hetzner token set)
- [ ] SSH key exists for Hetzner clusters
- [ ] Cluster provisioned successfully (nodes in `Ready` state)
- [ ] Kubeconfig saved and merged into `~/.kube/config`
- [ ] Context named with `<provider>-<region>-<name>` convention
- [ ] `kubectl get nodes` returns expected nodes on correct context
- [ ] Node pool sizing matches budget target
- [ ] Autoscaling configured if production workload
- [ ] Network access restricted (`allowed_networks` for Hetzner, VPC for DO)

---

## Safety: NEVER

- Store Hetzner API tokens or DO access tokens in Git — use environment variables or secret managers
- Provision production clusters without HA (single master = single point of failure)
- Use `0.0.0.0/0` for SSH/API `allowed_networks` in production — restrict to your IP
- Delete clusters without verifying persistent volumes and load balancers are cleaned up
- Mix cluster CIDRs when connecting multiple clusters (default `10.244.0.0/16` conflicts)

## Safety: ALWAYS

- Use `protect_against_deletion: true` for Hetzner production clusters
- Set `--maintenance-window` for DOKS clusters to control upgrade timing
- Restrict `allowed_networks` to your IP/VPN CIDR in production
- Back up kubeconfig files before merging
- Verify node count and sizes before applying — cloud bills are real

---

## Reference Files

| File | When to Read |
|------|--------------|
| `references/digitalocean-doks.md` | Full doctl CLI reference, all flags, node pool management |
| `references/hetzner-k3s.md` | Complete hetzner-k3s config spec, all fields, add-ons |
| `references/multi-cluster-kubectl.md` | Kubeconfig merge, context management, cross-cluster patterns |
| `references/cost-optimization.md` | Detailed pricing, comparison tables, optimization strategies |
