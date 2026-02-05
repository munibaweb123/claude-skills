---
name: argocd-gitops
description: Comprehensive GitOps with ArgoCD skill for automating Kubernetes deployments from hello world to professional production pipelines. Use when deploying, managing, and operating applications on Kubernetes using GitOps principles with ArgoCD for declarative, automated, and auditable infrastructure and application management.
---

# GitOps with ArgoCD Skill

This skill provides comprehensive support for implementing GitOps workflows with ArgoCD, from basic hello world deployments to professional production pipelines with advanced features like multi-cluster management, automated sync policies, and security best practices.

## When to Use This Skill

Use this skill when you need to:
- Implement GitOps workflows for Kubernetes applications
- Automate application deployments using ArgoCD
- Manage multiple clusters with ArgoCD
- Set up production-grade CI/CD pipelines with GitOps
- Implement drift detection and reconciliation
- Manage application lifecycles from dev to prod
- Handle secrets management in GitOps workflows
- Configure automated sync policies and rollback strategies

## Prerequisites

- Kubernetes cluster(s) with kubectl access
- Git repository for storing deployment manifests
- ArgoCD installed on the target cluster(s)
- Understanding of Kubernetes manifests and YAML
- Git workflow knowledge

## Pre-Implementation Context Gathering

Before providing specific recommendations, this skill will gather important context about your requirements:

### Team Experience Assessment
- What is your team's current experience with GitOps? (beginner, intermediate, advanced)
- Do you have experience with Kubernetes deployments?
- Have you used other GitOps tools (Flux, Jenkins X) before?

### Infrastructure Requirements
- How many Kubernetes clusters do you need to manage?
- What is your cluster topology? (single, multi-region, multi-cloud)
- Do you need to manage applications across multiple namespaces?

### Scale Requirements
- How many applications will be managed through GitOps?
- What is your expected deployment frequency?
- Do you anticipate rapid growth in application count?

### Security Requirements
- What are your security and compliance requirements?
- Do you need to manage secrets in Git (sealed-secrets, sops)?
- What level of RBAC do you need for ArgoCD?

### Operational Considerations
- What monitoring and observability tools do you currently use?
- Do you have dedicated DevOps/SRE resources for GitOps operations?
- What are your disaster recovery and backup requirements?

## Quick Start: Hello World with ArgoCD

### Install ArgoCD

```bash
# Install ArgoCD on your cluster
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Wait for pods to be ready
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=argocd-server -n argocd --timeout=180s

# Port forward to access ArgoCD UI
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

### Get Initial Admin Password

```bash
# Get the initial admin password
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
```

### Create a Hello World Application

1. Create a Git repository with a simple Kubernetes deployment:

```yaml
# hello-world.yaml
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
      - name: hello-world
        image: nginx:latest
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: hello-world-service
spec:
  selector:
    app: hello-world
  ports:
    - protocol: TCP
      port: 80
      targetPort: 80
  type: ClusterIP
```

2. Create the application in ArgoCD:

```bash
# Login to ArgoCD CLI (use the initial password from above)
argocd login localhost:8080 --username admin --password <initial-password>

# Create the application
argocd app create hello-world \
  --repo https://github.com/your-org/your-gitops-repo \
  --path . \
  --dest-server https://kubernetes.default.svc \
  --dest-namespace default
```

3. Sync the application:

```bash
# Sync the application to deploy it
argocd app sync hello-world
```

## GitOps Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Git Repo      │    │   ArgoCD        │    │ Kubernetes      │
│                 │    │                 │    │ Cluster         │
│  (Source of     │◄──►│  (Controller)   │◄──►│                 │
│   Truth)        │    │                 │    │  (Target)       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                       │                       │
        ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Commits       │    │   Sync Loop     │    │   Desired State │
│                 │    │                 │    │                 │
│  Developers     │    │  Continuous     │    │  Applications   │
│  push changes   │    │  reconciliation │    │  running as     │
└─────────────────┘    └─────────────────┘    │  declared in    │
                                             │  Git            │
                                             └─────────────────┘
```

### GitOps Principles

GitOps follows four core principles:

1. **Declarative**: The entire system state is described declaratively in Git
2. **Version Controlled**: The Git repository is the single source of truth
3. **Automated**: Automated tools ensure the system state matches the Git state
4. **Auditable**: All changes are tracked in Git history with full audit trail

## ArgoCD Internal Components

ArgoCD runs as a set of controllers and servers in the `argocd` namespace. Each component has a distinct role in the reconciliation loop:

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  API Server  │────►│  Repo Server │────►│  Application │────►│  Kubernetes  │
│              │     │              │     │  Controller  │     │  Cluster(s)  │
│ UI, CLI,     │     │ Clones Git,  │     │              │     │              │
│ gRPC/REST,   │     │ renders      │     │ Compares     │     │ Actual state │
│ auth, RBAC   │     │ manifests    │     │ desired vs   │     │ of resources │
└──────────────┘     └──────────────┘     │ actual state │     └──────────────┘
                            ▲              └──────┬───────┘
                            │                     │
                     ┌──────┴───────┐      Sync / Self-Heal
                     │    Redis     │
                     │              │
                     │ Caches repo  │
                     │ state and    │
                     │ manifests    │
                     └──────────────┘
```

### API Server (`argocd-server`)
Exposes the gRPC and REST API that the UI and CLI connect to. Handles authentication (SSO, OIDC, local accounts), enforces RBAC policies, and proxies requests to other components. This is the only component users interact with directly.

### Repo Server (`argocd-repo-server`)
Clones Git repositories and renders Kubernetes manifests from the source (plain YAML, Kustomize, Helm, Jsonnet). Returns the rendered manifests to the Application Controller. Stateless — can be scaled horizontally for repos with heavy rendering workloads.

### Application Controller (`argocd-application-controller`)
The core reconciliation engine. Runs a continuous loop that:
1. Asks the Repo Server for the desired state (rendered manifests from Git)
2. Queries the Kubernetes API for the actual state (live resources)
3. Compares the two using a structured diff
4. If `automated.selfHeal` is enabled, applies changes to make actual match desired
5. Updates the Application status (`Synced`, `OutOfSync`, `Healthy`, `Degraded`)

### Redis
Caches rendered manifests and repository state to reduce load on the Repo Server and Git. Used internally by both the API Server and Application Controller. Not a persistence layer — can be flushed without data loss.

## Reconciliation Loop Mechanics

The Application Controller continuously reconciles desired state (Git) with actual state (cluster):

```
Every 3 minutes (default):
  ┌─────────────────────────────────────────────────────────┐
  │ 1. Controller polls Repo Server for latest manifests    │
  │ 2. Repo Server pulls from Git (or returns cached copy)  │
  │ 3. Controller queries Kubernetes API for live resources  │
  │ 4. Controller diffs desired vs actual                    │
  │    ├── Match → status: Synced                            │
  │    └── Mismatch → status: OutOfSync                      │
  │        ├── selfHeal: true → auto-apply desired state     │
  │        └── selfHeal: false → wait for manual sync        │
  └─────────────────────────────────────────────────────────┘
```

### Configuring the Reconciliation Interval

The default poll interval is 3 minutes. Tune it based on your deployment frequency:

```yaml
# argocd-cmd-params-cm.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cmd-params-cm
  namespace: argocd
data:
  # How often the controller re-checks each application (default: 180s)
  controller.repo.server.timeout.seconds: "60"
  # Timeout for the full reconciliation cycle
  timeout.reconciliation: "180s"
```

For immediate sync on push, use a Git webhook instead of polling:

```bash
# Configure a webhook in your Git provider pointing to:
# https://<argocd-server>/api/webhook
# ArgoCD will immediately refresh the affected application
```

### Sync Phases and Waves

When ArgoCD syncs an application, it executes resources in three phases. Within each phase, sync waves control ordering:

```
Phase 1: PreSync    → Run setup tasks (Jobs, migrations)
Phase 2: Sync       → Apply main resources (Deployments, Services)
Phase 3: PostSync   → Run verification tasks (smoke tests, notifications)
```

```yaml
# PreSync hook: run database migrations before deploying
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migrate
  annotations:
    argocd.argoproj.io/hook: PreSync
    argocd.argoproj.io/hook-delete-policy: HookSucceeded
spec:
  template:
    spec:
      containers:
      - name: migrate
        image: myapp:latest
        command: ["make", "db-migrate"]
      restartPolicy: Never
---
# Sync wave: deploy ConfigMap before Deployment (lower wave = first)
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  annotations:
    argocd.argoproj.io/sync-wave: "-1"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  annotations:
    argocd.argoproj.io/sync-wave: "0"
```

### Resource Hooks

Hooks are Kubernetes resources (typically Jobs) that run at specific points during the sync lifecycle. They are identified by the `argocd.argoproj.io/hook` annotation.

#### Hook Types

| Hook | When it runs |
|------|-------------|
| `PreSync` | Before any Sync-phase resources are applied |
| `Sync` | Alongside normal resources (same as no hook) |
| `PostSync` | After all Sync-phase resources are healthy |
| `SyncFail` | When the sync operation fails |
| `Skip` | Resource is never applied (useful for documentation manifests) |

#### Hook Delete Policies

Control when hook resources are cleaned up:

| Policy | Behavior |
|--------|----------|
| `HookSucceeded` | Delete after hook completes successfully |
| `HookFailed` | Delete after hook fails |
| `BeforeHookCreation` | Delete any existing hook resource before creating a new one (default) |

Combine policies: `argocd.argoproj.io/hook-delete-policy: HookSucceeded,BeforeHookCreation`

#### PreSync Hook: Database Schema Migration

Run migrations before the application deploys. If the migration Job fails, the sync aborts and the Deployment is never updated.

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migrate
  annotations:
    argocd.argoproj.io/hook: PreSync
    argocd.argoproj.io/hook-delete-policy: BeforeHookCreation
    argocd.argoproj.io/sync-wave: "-1"  # Run before other PreSync hooks
spec:
  backoffLimit: 2
  activeDeadlineSeconds: 300
  template:
    metadata:
      labels:
        app: db-migrate
    spec:
      restartPolicy: Never
      containers:
      - name: migrate
        image: myapp:latest
        command: ["python", "manage.py", "migrate", "--noinput"]
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: database-url
```

`BeforeHookCreation` ensures the previous Job is deleted before a new one is created — necessary because Kubernetes doesn't allow re-running a completed Job with the same name.

#### PostSync Hook: Smoke Tests

Run health verification after the deployment is healthy. If the smoke test fails, the Application status becomes `Degraded` and the `SyncFail` hook runs (if defined).

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: smoke-test
  annotations:
    argocd.argoproj.io/hook: PostSync
    argocd.argoproj.io/hook-delete-policy: HookSucceeded,BeforeHookCreation
spec:
  backoffLimit: 1
  activeDeadlineSeconds: 120
  template:
    metadata:
      labels:
        app: smoke-test
    spec:
      restartPolicy: Never
      containers:
      - name: smoke
        image: curlimages/curl:latest
        command:
        - sh
        - -c
        - |
          set -e
          echo "Waiting for service to be ready..."
          sleep 10
          echo "Testing health endpoint..."
          curl --fail --retry 5 --retry-delay 5 http://my-app:8080/healthz
          echo "Testing API endpoint..."
          curl --fail --retry 3 http://my-app:8080/api/v1/status
          echo "Smoke tests passed."
```

#### SyncFail Hook: Notification on Failure

Send an alert when a sync fails (e.g., migration error or failed smoke test):

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: notify-sync-failure
  annotations:
    argocd.argoproj.io/hook: SyncFail
    argocd.argoproj.io/hook-delete-policy: HookSucceeded,BeforeHookCreation
spec:
  backoffLimit: 0
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: notify
        image: curlimages/curl:latest
        command:
        - sh
        - -c
        - |
          curl -X POST "$SLACK_WEBHOOK" \
            -H 'Content-Type: application/json' \
            -d '{"text":"Sync failed for my-app. Check ArgoCD for details."}'
        env:
        - name: SLACK_WEBHOOK
          valueFrom:
            secretKeyRef:
              name: notification-secrets
              key: slack-webhook-url
```

#### Complete Hook Lifecycle Example

A full sync with hooks executes in this order:

```
1. PreSync (wave -1): db-migrate Job → must succeed
2. PreSync (wave 0):  seed-data Job  → must succeed
3. Sync:              Deployment, Service, ConfigMap applied
4. Wait:              ArgoCD waits for Deployment to be Healthy
5. PostSync:          smoke-test Job → runs verification
6. (If any step fails) → SyncFail: notify-sync-failure Job
```

### Ignoring Expected Drift

Some resources are legitimately modified at runtime (e.g., HPA changing replicas). Use `ignoreDifferences` to prevent ArgoCD from flagging these as OutOfSync:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app
spec:
  ignoreDifferences:
  - group: apps
    kind: Deployment
    jsonPointers:
    - /spec/replicas  # HPA manages this
  - group: admissionregistration.k8s.io
    kind: MutatingWebhookConfiguration
    jqPathExpressions:
    - .webhooks[].clientConfig.caBundle  # Cert-manager rotates this
```

## Sync Status vs Health Status

ArgoCD tracks two independent dimensions for every Application:

### Sync Status (Git ↔ Cluster)

Sync status answers: **"Do the manifests in Git match what's on the cluster?"**

| Status | Meaning |
|--------|---------|
| `Synced` | Live cluster state matches the desired state in Git |
| `OutOfSync` | Cluster state has drifted from Git (someone edited a resource directly, or Git was updated but not yet applied) |
| `Unknown` | ArgoCD cannot determine sync status (e.g., repo unreachable) |

### Health Status (Resource Readiness)

Health status answers: **"Are the resources actually working?"**

| Status | Meaning |
|--------|---------|
| `Healthy` | All resources are running and passing health checks |
| `Progressing` | Resources are being updated (rollout in progress, pods starting) |
| `Degraded` | One or more resources have failures (CrashLoopBackOff, failed probes) |
| `Suspended` | Resource is paused (e.g., suspended CronJob or Argo Rollout) |
| `Missing` | Resource defined in Git does not exist on the cluster |
| `Unknown` | Health cannot be assessed (no health check defined for CRD) |

### Why Both Matter

An application can be **Synced but Degraded** — Git matches the cluster, but the deployed code is crashing. Conversely, it can be **OutOfSync but Healthy** — a manual hotfix was applied directly to the cluster and is working fine, but Git hasn't been updated.

```
Sync Status:    Synced ──────── OutOfSync
                  │                  │
Health Status:  Healthy            Healthy       ← hotfix applied directly
                Degraded           Degraded      ← bad config in Git AND cluster
                Progressing        Progressing   ← rollout in progress
```

**Alerting guidance**: Alert on `OutOfSync` for drift detection. Alert on `Degraded` for application failures. Both require different remediation — OutOfSync needs a sync or git revert; Degraded needs debugging the application itself.

## Custom Health Checks with Lua

ArgoCD has built-in health checks for standard Kubernetes resources (Deployment, StatefulSet, Service, Ingress, etc.). For CustomResources (CRDs), ArgoCD reports health as `Unknown` unless you provide a Lua script.

### How Custom Health Checks Work

Health check scripts are configured in the `argocd-cm` ConfigMap. ArgoCD passes the full resource object (`obj`) to the Lua function, which must return a table with:

- `hs.status` — one of: `Healthy`, `Progressing`, `Degraded`, `Suspended`, `Missing`
- `hs.message` — human-readable explanation shown in the UI and CLI

### Configuration in argocd-cm

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
data:
  # Key format: resource.customizations.health.<group_kind>
  # Group and kind are separated by underscore, dots in group replaced with underscores

  resource.customizations.health.argoproj.io_Rollout: |
    hs = {}
    if obj.status == nil then
      hs.status = "Progressing"
      hs.message = "Waiting for status"
      return hs
    end
    if obj.status.phase == "Healthy" then
      hs.status = "Healthy"
      hs.message = "Rollout is healthy"
    elseif obj.status.phase == "Paused" then
      hs.status = "Suspended"
      hs.message = "Rollout is paused: " .. (obj.status.message or "awaiting promotion")
    elseif obj.status.phase == "Degraded" then
      hs.status = "Degraded"
      hs.message = "Rollout is degraded: " .. (obj.status.message or "unknown error")
    else
      hs.status = "Progressing"
      hs.message = "Rollout is " .. (obj.status.phase or "unknown")
    end
    return hs
```

### Example: Certificate (cert-manager)

```yaml
  resource.customizations.health.cert-manager.io_Certificate: |
    hs = {}
    if obj.status == nil or obj.status.conditions == nil then
      hs.status = "Progressing"
      hs.message = "Waiting for certificate status"
      return hs
    end
    for i, condition in ipairs(obj.status.conditions) do
      if condition.type == "Ready" then
        if condition.status == "True" then
          hs.status = "Healthy"
          hs.message = "Certificate is ready"
        elseif condition.status == "False" then
          hs.status = "Degraded"
          hs.message = condition.message or "Certificate not ready"
        else
          hs.status = "Progressing"
          hs.message = "Certificate status unknown"
        end
        return hs
      end
    end
    hs.status = "Progressing"
    hs.message = "No Ready condition found"
    return hs
```

### Example: Custom Application CRD

For a CRD with `.status.state` and `.status.replicas.ready`:

```yaml
  resource.customizations.health.myorg.io_MyApp: |
    hs = {}
    if obj.status == nil then
      hs.status = "Progressing"
      hs.message = "Resource just created"
      return hs
    end

    if obj.status.state == "Running" then
      -- Check if all replicas are ready
      local desired = obj.spec.replicas or 1
      local ready = 0
      if obj.status.replicas ~= nil then
        ready = obj.status.replicas.ready or 0
      end
      if ready >= desired then
        hs.status = "Healthy"
        hs.message = ready .. "/" .. desired .. " replicas ready"
      else
        hs.status = "Progressing"
        hs.message = ready .. "/" .. desired .. " replicas ready"
      end
    elseif obj.status.state == "Failed" then
      hs.status = "Degraded"
      hs.message = obj.status.error or "Application failed"
    elseif obj.status.state == "Suspended" then
      hs.status = "Suspended"
      hs.message = "Application paused by operator"
    else
      hs.status = "Progressing"
      hs.message = "State: " .. (obj.status.state or "unknown")
    end
    return hs
```

### Example: Condition-Based Pattern (Generic)

Many CRDs follow the Kubernetes conditions convention. This generic pattern works for any resource with `.status.conditions[]`:

```yaml
  resource.customizations.health.example.com_MyResource: |
    hs = {}
    if obj.status == nil or obj.status.conditions == nil then
      hs.status = "Progressing"
      hs.message = "Waiting for conditions"
      return hs
    end

    -- Check for a "Ready" or "Available" condition
    for i, condition in ipairs(obj.status.conditions) do
      if condition.type == "Ready" or condition.type == "Available" then
        if condition.status == "True" then
          hs.status = "Healthy"
          hs.message = condition.type .. ": " .. (condition.message or "OK")
          return hs
        end
      end
      if condition.type == "Degraded" and condition.status == "True" then
        hs.status = "Degraded"
        hs.message = condition.message or "Resource degraded"
        return hs
      end
    end

    -- No definitive condition found
    hs.status = "Progressing"
    hs.message = "Waiting for Ready condition"
    return hs
```

### Custom Resource Actions

Beyond health, you can also define custom Lua actions that appear in the ArgoCD UI:

```yaml
  resource.customizations.actions.argoproj.io_Rollout: |
    discovery.lua: |
      actions = {}
      actions["restart"] = {["disabled"] = false}
      actions["promote-full"] = {["disabled"] = false}
      return actions
    definitions:
    - name: restart
      action.lua: |
        obj.spec.restartAt = os.date("!%Y-%m-%dT%H:%M:%SZ")
        return obj
    - name: promote-full
      action.lua: |
        if obj.status.currentPodHash ~= nil then
          obj.status.promoteFull = true
        end
        return obj
```

### Lua Script Reference

| Variable | Type | Description |
|----------|------|-------------|
| `obj` | table | Full Kubernetes resource (spec, status, metadata) |
| `hs` | table | Return value — must have `hs.status` and `hs.message` |
| `obj.status` | table/nil | Resource status — always nil-check before accessing |
| `obj.spec` | table | Resource spec |
| `obj.metadata` | table | Resource metadata (name, namespace, labels, annotations) |

**Key rules**:
- Always nil-check `obj.status` before accessing sub-fields
- Always return `hs` at the end of every code path
- String concatenation uses `..` not `+`
- Use `ipairs` for iterating arrays (conditions), `pairs` for maps (labels)

## Automated Sync: Prune vs Self-Heal

Both `prune` and `selfHeal` are sub-options of `automated` sync, but they address different drift scenarios:

### Prune (`automated.prune: true`)

**What it does**: Deletes cluster resources that no longer exist in Git.

**When it triggers**: You remove a manifest from Git (e.g., delete a ConfigMap YAML). Without prune, the orphaned resource stays on the cluster forever.

**When to enable**: Almost always in non-production environments. In production, enable it but consider `argocd.argoproj.io/sync-options: PruneLast=true` annotation so deletions happen after all other syncs complete.

**Risk**: Accidentally deleting a manifest from Git deletes the live resource. Mitigate with `PrunePropagationPolicy=foreground` and PR reviews.

### Self-Heal (`automated.selfHeal: true`)

**What it does**: Reverts manual changes made directly on the cluster back to the Git-defined state.

**When it triggers**: Someone runs `kubectl edit` or `kubectl scale` directly, causing drift from Git. Self-heal detects this within the poll interval and re-applies the Git state.

**When to enable**: Production environments where you want to enforce Git as the single source of truth. This prevents ad-hoc `kubectl` changes from persisting.

**Risk**: Conflicts with HPA (autoscaler changes replicas, self-heal reverts them). Use `ignoreDifferences` for fields managed by controllers:

```yaml
spec:
  ignoreDifferences:
    - group: apps
      kind: Deployment
      jsonPointers:
        - /spec/replicas
```

### Decision Matrix

| Scenario | `prune` | `selfHeal` |
|----------|---------|------------|
| Dev/staging (fast iteration) | `true` | `true` |
| Production (strict GitOps) | `true` | `true` |
| Production (cautious rollout) | `false` | `true` |
| Shared cluster with manual overrides | `false` | `false` |
| HPA-managed deployments | either | `true` + `ignoreDifferences` on replicas |

## Sync Windows and Emergency Overrides

Sync windows control **when** ArgoCD is allowed to sync applications. This prevents deployments during maintenance periods, business-critical hours, or weekends.

### Sync Window Configuration

Sync windows are defined at the **AppProject** level and use cron syntax:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: production
  namespace: argocd
spec:
  description: Production applications
  sourceRepos:
    - 'https://github.com/your-org/*'
  destinations:
    - namespace: '*'
      server: https://kubernetes.default.svc

  syncWindows:
    # Allow syncs only during business hours on weekdays
    - kind: allow
      schedule: '0 9 * * 1-5'    # Mon-Fri at 9:00 AM
      duration: 8h                 # Until 5:00 PM
      applications:
        - '*'
      manualSync: true             # Allow manual sync even outside window

    # Block all syncs during the weekend
    - kind: deny
      schedule: '0 0 * * 0,6'     # Saturday and Sunday at midnight
      duration: 24h
      applications:
        - '*'

    # Allow syncs for critical-path apps anytime
    - kind: allow
      schedule: '* * * * *'        # Always
      duration: 24h
      applications:
        - 'critical-*'

    # Block syncs during monthly maintenance
    - kind: deny
      schedule: '0 2 1 * *'       # 1st of each month at 2:00 AM
      duration: 4h
      applications:
        - '*'
```

### Window Evaluation Rules

- **Multiple windows**: If both `allow` and `deny` windows overlap, `deny` takes precedence
- **No active window**: If no `allow` window is active and at least one `allow` window is defined, syncs are blocked
- **`manualSync: true`**: Permits manual syncs (via UI/CLI) even when the automated window is closed — useful for emergency fixes
- **Scope**: Windows apply to all applications in the project matching the `applications` glob pattern

### Emergency Override Strategies

When a critical fix must go out outside a sync window:

**Strategy 1: Manual sync with `manualSync: true`**

If the sync window has `manualSync: true`, operators can force a sync:

```bash
# Force sync bypasses automated window restrictions (if manualSync is enabled)
argocd app sync my-app-prod --force
```

**Strategy 2: Temporarily disable the sync window**

Edit the AppProject to remove or modify the blocking window:

```bash
# Edit the project to temporarily allow syncs
kubectl edit appproject production -n argocd
# Remove or comment out the deny window, save, sync, then restore
```

> Restore the window immediately after the emergency sync. Track the override in your incident log.

**Strategy 3: Override annotation on the Application**

Bypass sync windows for a specific application using the override annotation:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app-prod
  annotations:
    # Temporarily allow sync regardless of project sync windows
    argocd.argoproj.io/sync-options: "RespectIgnoreDifferences=true"
spec:
  syncPolicy:
    syncOptions:
      - RespectIgnoreDifferences=true
```

**Strategy 4: Dedicated emergency project**

Create a separate project with no sync window restrictions for break-glass scenarios:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: emergency-override
  namespace: argocd
spec:
  description: Emergency deployments - no sync windows
  sourceRepos:
    - 'https://github.com/your-org/*'
  destinations:
    - namespace: '*'
      server: https://kubernetes.default.svc
  # No syncWindows defined = syncs always allowed
```

```bash
# Move an application to the emergency project temporarily
argocd app set my-app-prod --project emergency-override
argocd app sync my-app-prod

# After the emergency, move it back
argocd app set my-app-prod --project production
```

### Decision Guide

| Scenario | Approach |
|----------|----------|
| Planned deploy during blocked window | Wait for next `allow` window |
| P1 incident, `manualSync: true` set | `argocd app sync --force` |
| P1 incident, `manualSync: false` | Edit AppProject or use emergency project |
| Hotfix that must bypass all gates | Emergency project + post-incident review |
| Recurring maintenance window | `deny` window with cron schedule |

> **Post-emergency**: Always update Git to reflect what was deployed. If you used `kubectl` directly or moved projects, the cluster state may drift from Git until you reconcile.

## Core ArgoCD Concepts

### Applications
An Application in ArgoCD represents a deployed application on a Kubernetes cluster. It defines the relationship between a source (Git repository) and a destination (cluster/namespace).

### Projects
Projects provide a grouping mechanism for applications and allow for fine-grained access control and resource restrictions.

### Repositories
ArgoCD can manage applications from any Git repository containing Kubernetes manifests.

### Clusters
ArgoCD can manage multiple Kubernetes clusters from a single control plane.

## ArgoCD Application Configuration Patterns

### Basic Application Configuration

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/your-org/my-app-manifests
    targetRevision: HEAD
    path: k8s/overlays/prod
  destination:
    server: https://kubernetes.default.svc
    namespace: my-app-prod
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

### Application with Multiple Environments

```yaml
# dev-application.yaml
apiVersion: argocd.io/v1alpha1
kind: Application
metadata:
  name: my-app-dev
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/your-org/my-app-manifests
    targetRevision: HEAD
    path: k8s/overlays/dev
  destination:
    server: https://kubernetes.default.svc
    namespace: my-app-dev
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
---
# staging-application.yaml
apiVersion: argocd.io/v1alpha1
kind: Application
metadata:
  name: my-app-staging
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/your-org/my-app-manifests
    targetRevision: HEAD
    path: k8s/overlays/staging
  destination:
    server: https://kubernetes.default.svc
    namespace: my-app-staging
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
---
# prod-application.yaml
apiVersion: argocd.io/v1alpha1
kind: Application
metadata:
  name: my-app-prod
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/your-org/my-app-manifests
    targetRevision: HEAD
    path: k8s/overlays/prod
  destination:
    server: https://kubernetes.default.svc
    namespace: my-app-prod
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
    - CreateNamespace=true
    - ApplyOutOfSyncOnly=true
```

### Application with Value Substitution

```yaml
apiVersion: argocd.io/v1alpha1
kind: Application
metadata:
  name: my-app-parameterized
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/your-org/my-app-manifests
    targetRevision: HEAD
    path: k8s/base
    helm:
      valueFiles:
      - values-prod.yaml
      parameters:
      - name: "image.tag"
        value: "v1.2.3"
      - name: "replicaCount"
        value: "3"
  destination:
    server: https://kubernetes.default.svc
    namespace: my-app-prod
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

## ArgoCD Project Configuration

Projects restrict which repositories, clusters, namespaces, and resource types an Application can use. The `default` project has no restrictions — production applications should use a dedicated project.

### Restrictive Project: Namespace and Repository Whitelists

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: team-payments
  namespace: argocd
spec:
  description: Payment service team - restricted to their repos and namespaces

  # Only these Git repos can be used as sources
  sourceRepos:
  - 'https://github.com/your-org/payments-manifests'
  - 'https://github.com/your-org/shared-charts'
  # Use glob: 'https://github.com/your-org/payments-*' for pattern matching

  # Only these cluster/namespace combinations are allowed
  destinations:
  - server: https://kubernetes.default.svc
    namespace: payments-dev
  - server: https://kubernetes.default.svc
    namespace: payments-staging
  - server: https://prod-cluster.example.com
    namespace: payments-prod
  # Deny all other namespaces — Applications targeting e.g., 'kube-system' will be rejected

  # Cluster-scoped resources this project can create (empty = none allowed)
  clusterResourceWhitelist: []
  # To allow specific cluster resources:
  # clusterResourceWhitelist:
  # - group: ''
  #   kind: Namespace
  # - group: rbac.authorization.k8s.io
  #   kind: ClusterRole

  # Namespace-scoped resources this project CANNOT create
  namespaceResourceBlacklist:
  - group: ''
    kind: ResourceQuota
  - group: ''
    kind: LimitRange
  - group: ''
    kind: NetworkPolicy   # Managed by platform team, not app teams

  # Warn if resources exist in the destination but aren't tracked by any Application
  orphanedResources:
    warn: true
    ignore:
    - group: ''
      kind: ConfigMap
      name: kube-root-ca.crt  # Auto-generated, not managed by GitOps
```

### Project with Sync Windows and Source Namespaces

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: team-platform
  namespace: argocd
spec:
  description: Platform team - broader access with sync window controls

  sourceRepos:
  - 'https://github.com/your-org/platform-*'
  - 'https://github.com/your-org/shared-charts'

  destinations:
  - server: https://kubernetes.default.svc
    namespace: 'monitoring'
  - server: https://kubernetes.default.svc
    namespace: 'logging'
  - server: https://kubernetes.default.svc
    namespace: 'ingress-nginx'
  - server: '*'
    namespace: 'argocd'  # Manage ArgoCD itself across clusters

  clusterResourceWhitelist:
  - group: ''
    kind: Namespace
  - group: rbac.authorization.k8s.io
    kind: ClusterRole
  - group: rbac.authorization.k8s.io
    kind: ClusterRoleBinding
  - group: networking.k8s.io
    kind: IngressClass

  syncWindows:
  - kind: allow
    schedule: '0 9 * * 1-5'
    duration: 8h
    applications:
    - '*'
    manualSync: true

  # RBAC roles defined below
```

### RBAC: Role Definitions and Group Mappings

ArgoCD RBAC controls who can view, sync, and manage Applications. Policies are defined in the `argocd-rbac-cm` ConfigMap using a Casbin-style syntax.

#### Policy Syntax

```
p, <subject>, <resource>, <action>, <object>, <effect>
g, <user/group>, <role>
```

- **subject**: user email, group name, or role
- **resource**: `applications`, `projects`, `clusters`, `repositories`, `logs`, `exec`
- **action**: `get`, `create`, `update`, `delete`, `sync`, `override`, `action/*`
- **object**: `<project>/<application>` or `*` for all
- **effect**: `allow` or `deny`

#### RBAC ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-rbac-cm
  namespace: argocd
data:
  # Default policy for authenticated users with no matching role
  policy.default: role:readonly

  policy.csv: |
    # ============================================
    # Role: Admin — full access to everything
    # ============================================
    p, role:admin, applications, *, */*, allow
    p, role:admin, clusters, *, *, allow
    p, role:admin, repositories, *, *, allow
    p, role:admin, projects, *, *, allow
    p, role:admin, logs, get, */*, allow
    p, role:admin, exec, create, */*, allow

    # ============================================
    # Role: Developer — sync and view their team's apps
    # ============================================
    p, role:payments-developer, applications, get, team-payments/*, allow
    p, role:payments-developer, applications, sync, team-payments/*, allow
    p, role:payments-developer, applications, action/*, team-payments/*, allow
    p, role:payments-developer, logs, get, team-payments/*, allow
    # Cannot create, delete, or update Application definitions
    # Cannot access other projects

    # ============================================
    # Role: Deployer — sync to production only
    # ============================================
    p, role:payments-deployer, applications, get, team-payments/*, allow
    p, role:payments-deployer, applications, sync, team-payments/*-prod, allow
    p, role:payments-deployer, applications, action/*, team-payments/*-prod, allow

    # ============================================
    # Role: Read-only — view all apps across all projects
    # ============================================
    p, role:readonly, applications, get, */*, allow
    p, role:readonly, projects, get, *, allow
    p, role:readonly, clusters, get, *, allow
    p, role:readonly, repositories, get, *, allow

    # ============================================
    # Group mappings — map SSO/OIDC groups to roles
    # ============================================
    g, platform-admins, role:admin
    g, payments-team, role:payments-developer
    g, payments-leads, role:payments-deployer
    g, engineering, role:readonly

  # Map OIDC groups claim to ArgoCD groups
  scopes: '[groups]'
```

#### Project-Scoped Roles

Roles can also be defined directly in an AppProject for tighter scoping:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: team-payments
  namespace: argocd
spec:
  sourceRepos:
  - 'https://github.com/your-org/payments-manifests'
  destinations:
  - server: https://kubernetes.default.svc
    namespace: payments-dev
  - server: https://kubernetes.default.svc
    namespace: payments-staging
  - server: https://prod-cluster.example.com
    namespace: payments-prod

  roles:
  - name: developer
    description: Can sync non-prod applications
    policies:
    - p, proj:team-payments:developer, applications, get, team-payments/*, allow
    - p, proj:team-payments:developer, applications, sync, team-payments/*-dev, allow
    - p, proj:team-payments:developer, applications, sync, team-payments/*-staging, allow
    groups:
    - payments-team   # OIDC/SSO group

  - name: lead
    description: Can sync all environments including prod
    policies:
    - p, proj:team-payments:lead, applications, *, team-payments/*, allow
    - p, proj:team-payments:lead, logs, get, team-payments/*, allow
    groups:
    - payments-leads  # OIDC/SSO group

  - name: oncall
    description: Emergency sync access for on-call engineers
    policies:
    - p, proj:team-payments:oncall, applications, sync, team-payments/*, allow
    - p, proj:team-payments:oncall, applications, get, team-payments/*, allow
    # Tokens can be generated for CI/CD:
    # argocd proj role create-token team-payments oncall --expires-in 24h
```

#### RBAC Decision Guide

| Team | Role | Can view | Can sync dev/staging | Can sync prod | Can create/delete apps |
|------|------|----------|---------------------|---------------|----------------------|
| Platform | `admin` | All | All | All | Yes |
| App team | `developer` | Own project | Yes | No | No |
| Tech leads | `deployer` | Own project | Yes | Yes | No |
| Everyone | `readonly` | All | No | No | No |
| On-call | `oncall` | Own project | Yes | Yes (emergency) | No |

## Production-Grade GitOps Pipeline

### Multi-Environment Pipeline

```yaml
# ci-pipeline.yaml - Example for GitHub Actions
name: GitOps Deployment

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Validate manifests
      run: |
        # Run kubectl dry-run or conftest validation
        kubectl apply --dry-run=server -f k8s/overlays/prod/

  deploy-dev:
    needs: validate
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
    - uses: actions/checkout@v3
    - name: Deploy to dev
      run: |
        # Update GitOps repo with dev-specific values
        # ArgoCD will auto-sync
        git config user.name github-actions
        git config user.email github-actions@github.com
        # Update dev overlay with new image tag
        sed -i "s|image:.*|image: myapp:${{ github.sha }}|" k8s/overlays/dev/deployment.yaml
        git add .
        git commit -m "Deploy ${{ github.sha }}"
        git push

  promote-staging:
    needs: deploy-dev
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
    - uses: actions/checkout@v3
    - name: Promote to staging
      run: |
        # Update staging overlay with validated image tag
        sed -i "s|image:.*|image: myapp:${{ github.sha }}|" k8s/overlays/staging/deployment.yaml
        git add .
        git commit -m "Promote ${{ github.sha }} to staging"
        git push

  promote-prod:
    needs: promote-staging
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
    - uses: actions/checkout@v3
    - name: Promote to prod (manual approval)
      run: |
        # Manual promotion to prod
        sed -i "s|image:.*|image: myapp:${{ github.sha }}|" k8s/overlays/prod/deployment.yaml
        git add .
        git commit -m "Promote ${{ github.sha }} to prod"
        git push
```

### Automated Promotion with Conditions

```yaml
# automated-promotion.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/your-org/my-app-manifests
    targetRevision: HEAD
    path: k8s/overlays/prod
    kustomize:
      images:
      - myapp=${IMAGE_TAG}
  destination:
    server: https://kubernetes.default.svc
    namespace: my-app-prod
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
      allowEmpty: false
    syncOptions:
    - CreateNamespace=true
    - ApplyOutOfSyncOnly=true
    - SkipDryRunOnMissingResource=true
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m0s
```

## Quality Gates: Blocking Deployment on Test Failures

Quality gates ensure that test failures prevent promotion to the next environment. Each stage acts as a checkpoint — if tests fail, the pipeline halts and the artifact never reaches downstream environments.

### CI Pipeline with Quality Gates

```yaml
# ci-pipeline-with-gates.yaml - GitHub Actions
name: GitOps Deployment with Quality Gates

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      image_tag: ${{ steps.meta.outputs.tags }}
    steps:
    - uses: actions/checkout@v3

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3

    - name: Login to Docker Hub
      uses: docker/login-action@v3
      with:
        username: ${{ secrets.DOCKER_USERNAME }}
        password: ${{ secrets.DOCKER_TOKEN }}

    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v5
      with:
        images: ${{ secrets.DOCKER_USERNAME }}/myapp
        tags: |
          type=sha
          type=ref,event=branch
          type=semver,pattern={{version}}

    - name: Build and push
      uses: docker/build-push-action@v5
      with:
        context: .
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
        cache-from: type=gha
        cache-to: type=gha,mode=max

  test:
    needs: build
    runs-on: ubuntu-latest
    strategy:
      matrix:
        test-type: [unit, integration]
        node-version: [18, 20]
      fail-fast: true  # Cancel all matrix jobs if any fails
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: testuser
          POSTGRES_PASSWORD: testpass
          POSTGRES_DB: testdb
        ports:
        - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7
        ports:
        - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    env:
      DATABASE_URL: postgresql://testuser:testpass@localhost:5432/testdb
      REDIS_URL: redis://localhost:6379
    steps:
    - uses: actions/checkout@v3
    - name: Set up Node ${{ matrix.node-version }}
      uses: actions/setup-node@v3
      with:
        node-version: ${{ matrix.node-version }}
    - name: Run ${{ matrix.test-type }} tests
      run: make test-${{ matrix.test-type }}
      # Services are available for integration tests via DATABASE_URL and REDIS_URL
      # Unit tests ignore the services — no harm in them running
      # If ANY matrix combination fails, no downstream jobs execute

  deploy-dev:
    needs: test  # Only runs if ALL matrix combinations pass
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Update dev overlay with tested image
      run: |
        sed -i "s|image:.*|image: ${{ needs.build.outputs.image_tag }}|" k8s/overlays/dev/deployment.yaml
        git add . && git commit -m "Deploy tested ${{ github.sha }} to dev" && git push

  smoke-tests-dev:
    needs: deploy-dev
    runs-on: ubuntu-latest
    steps:
    - name: Wait for ArgoCD sync
      run: argocd app wait my-app-dev --health --timeout 300
    - name: Run smoke tests against dev
      run: |
        make test-smoke ENV=dev
        # If smoke tests fail, promotion to staging is blocked

  promote-staging:
    needs: smoke-tests-dev  # Blocked until dev smoke tests pass
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Promote to staging
      run: |
        sed -i "s|image:.*|image: ${{ needs.build.outputs.image_tag }}|" k8s/overlays/staging/deployment.yaml
        git add . && git commit -m "Promote ${{ github.sha }} to staging" && git push

  promote-prod:
    needs: promote-staging
    runs-on: ubuntu-latest
    environment: production  # Requires manual approval in GitHub
    steps:
    - uses: actions/checkout@v3
    - name: Promote to production
      run: |
        sed -i "s|image:.*|image: ${{ needs.build.outputs.image_tag }}|" k8s/overlays/prod/deployment.yaml
        git add . && git commit -m "Promote ${{ github.sha }} to prod" && git push
```

### How Quality Gates Block Deployment

```
build → test (matrix: unit×node18, unit×node20, integration×node18, integration×node20)
                    ✗ ANY combination fails → pipeline stops. No image reaches dev.
         ↓ all pass
      deploy-dev → smoke-tests → staging → prod
                      ✗ FAIL
                  Pipeline stops.
               No promotion to staging.
```

Each `needs:` dependency enforces that the previous stage succeeded. The `strategy.matrix` runs all test type / version combinations in parallel — `fail-fast: true` cancels remaining matrix jobs on the first failure. A test failure at any point halts the chain, so the versioned artifact never reaches downstream environments.

## Rollback Strategies Using Versioned Artifacts

Because every deployment is a Git commit pointing to a specific image tag (`myapp:<sha>`), rollback is a Git operation — revert to a previous commit or re-pin the image tag.

### Strategy 1: Git Revert (Recommended)

The simplest rollback. Revert the commit that introduced the bad version:

```bash
# Find the commit that promoted the bad image
git log --oneline k8s/overlays/prod/deployment.yaml

# Revert it — creates a new commit pointing to the previous image tag
git revert <bad-commit-sha>
git push

# ArgoCD auto-syncs to the reverted state
argocd app wait my-app-prod --health --timeout 300
```

### Strategy 2: Re-pin Image Tag

Directly set the image tag back to a known-good version:

```bash
# Pin to the last known-good versioned artifact
sed -i "s|image:.*|image: myapp:abc123-known-good|" k8s/overlays/prod/deployment.yaml
git add . && git commit -m "Rollback prod to abc123" && git push
```

### Strategy 3: ArgoCD History Rollback

ArgoCD tracks sync history and can rollback to a previous sync:

```bash
# List sync history
argocd app history my-app-prod

# Rollback to a specific revision
argocd app rollback my-app-prod <HISTORY_ID>
```

> **Note:** This creates drift between Git and the cluster. Follow up by updating Git to match the rolled-back state.

### Strategy 4: Automated Rollback on Health Check Failure

Configure ArgoCD to automatically rollback when a deployment becomes unhealthy:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app-prod
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/your-org/my-app-manifests
    targetRevision: HEAD
    path: k8s/overlays/prod
  destination:
    server: https://kubernetes.default.svc
    namespace: my-app-prod
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    retry:
      limit: 3
      backoff:
        duration: 10s
        factor: 2
        maxDuration: 3m
---
# Pair with Argo Rollouts for automatic rollback
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: my-app
spec:
  strategy:
    canary:
      steps:
      - setWeight: 20
      - pause: {duration: 60s}
      - analysis:
          templates:
          - templateName: success-rate
      - setWeight: 50
      - pause: {duration: 60s}
      - analysis:
          templates:
          - templateName: success-rate
      autoPromotionEnabled: false
---
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: success-rate
spec:
  metrics:
  - name: success-rate
    interval: 30s
    successCondition: result[0] >= 0.95
    provider:
      prometheus:
        address: http://prometheus.monitoring:9090
        query: |
          sum(rate(http_requests_total{status=~"2.*",app="my-app"}[5m]))
          /
          sum(rate(http_requests_total{app="my-app"}[5m]))
```

If the `success-rate` analysis fails, Argo Rollouts automatically rolls back the canary — no manual intervention needed.

## Argo Rollouts: Progressive Delivery

Argo Rollouts replaces the standard Kubernetes `Deployment` with a `Rollout` CRD that supports canary, blue-green, and metric-based analysis for safe progressive delivery.

### Installation

```bash
kubectl create namespace argo-rollouts
kubectl apply -n argo-rollouts -f https://github.com/argoproj/argo-rollouts/releases/latest/download/install.yaml

# Install kubectl plugin
brew install argoproj/tap/kubectl-argo-rollouts  # macOS
# or: curl -LO https://github.com/argoproj/argo-rollouts/releases/latest/download/kubectl-argo-rollouts-linux-amd64 && chmod +x kubectl-argo-rollouts-linux-amd64 && mv kubectl-argo-rollouts-linux-amd64 /usr/local/bin/kubectl-argo-rollouts
```

### Canary Strategy (Detailed)

Gradually shifts traffic to the new version while running automated analysis:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: my-app
  namespace: my-app
spec:
  replicas: 5
  revisionHistoryLimit: 3
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
      - name: my-app
        image: my-registry/my-app:v2.0.0
        ports:
        - containerPort: 8080
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 256Mi
  strategy:
    canary:
      canaryService: my-app-canary       # Service for canary pods
      stableService: my-app-stable       # Service for stable pods
      trafficRouting:
        nginx:
          stableIngress: my-app-ingress  # or use istio/alb
      steps:
      - setWeight: 10
      - pause: {duration: 5m}
      - analysis:
          templates:
          - templateName: success-rate
          - templateName: latency-check
          args:
          - name: service-name
            value: my-app-canary
      - setWeight: 30
      - pause: {duration: 5m}
      - analysis:
          templates:
          - templateName: success-rate
      - setWeight: 60
      - pause: {duration: 10m}
      - setWeight: 100
      autoPromotionEnabled: false        # require manual final promotion
      maxSurge: 1
      maxUnavailable: 0
      abortScaleDownDelaySeconds: 30
---
# Services for traffic splitting
apiVersion: v1
kind: Service
metadata:
  name: my-app-stable
spec:
  selector:
    app: my-app
  ports:
  - port: 80
    targetPort: 8080
---
apiVersion: v1
kind: Service
metadata:
  name: my-app-canary
spec:
  selector:
    app: my-app
  ports:
  - port: 80
    targetPort: 8080
```

### Blue-Green Strategy

Runs both versions simultaneously, switches traffic atomically:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: my-app
  namespace: my-app
spec:
  replicas: 5
  revisionHistoryLimit: 3
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
      - name: my-app
        image: my-registry/my-app:v2.0.0
        ports:
        - containerPort: 8080
  strategy:
    blueGreen:
      activeService: my-app-active       # points to live version
      previewService: my-app-preview     # points to new version (pre-switch)
      autoPromotionEnabled: false        # manual promotion after verification
      prePromotionAnalysis:
        templates:
        - templateName: smoke-test
        args:
        - name: preview-url
          value: "http://my-app-preview.my-app.svc.cluster.local"
      postPromotionAnalysis:
        templates:
        - templateName: success-rate
      scaleDownDelaySeconds: 300         # keep old version 5m after switch
      scaleDownDelayRevisionLimit: 1     # keep only 1 old ReplicaSet
---
apiVersion: v1
kind: Service
metadata:
  name: my-app-active
spec:
  selector:
    app: my-app
  ports:
  - port: 80
    targetPort: 8080
---
apiVersion: v1
kind: Service
metadata:
  name: my-app-preview
spec:
  selector:
    app: my-app
  ports:
  - port: 80
    targetPort: 8080
```

### AnalysisTemplate Examples

**Prometheus success rate:**
```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: success-rate
spec:
  args:
  - name: service-name
  metrics:
  - name: success-rate
    interval: 60s
    count: 5                            # run 5 measurements
    successCondition: result[0] >= 0.95
    failureLimit: 2                     # tolerate 2 failures
    provider:
      prometheus:
        address: http://prometheus.monitoring:9090
        query: |
          sum(rate(http_requests_total{status=~"2.*",service="{{args.service-name}}"}[5m]))
          /
          sum(rate(http_requests_total{service="{{args.service-name}}"}[5m]))
```

**Latency P99 check:**
```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: latency-check
spec:
  args:
  - name: service-name
  metrics:
  - name: p99-latency
    interval: 60s
    count: 3
    successCondition: result[0] < 500   # < 500ms
    provider:
      prometheus:
        address: http://prometheus.monitoring:9090
        query: |
          histogram_quantile(0.99,
            sum(rate(http_request_duration_seconds_bucket{service="{{args.service-name}}"}[5m])) by (le)
          ) * 1000
```

**Smoke test (HTTP probe):**
```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: smoke-test
spec:
  args:
  - name: preview-url
  metrics:
  - name: smoke-test
    count: 1
    successCondition: result.status == "200"
    provider:
      web:
        url: "{{args.preview-url}}/healthz"
        method: GET
        timeoutSeconds: 10
```

### Canary vs Blue-Green Decision Guide

| Factor | Canary | Blue-Green |
|--------|--------|------------|
| **Traffic shift** | Gradual (10% → 30% → 100%) | Atomic (0% → 100% instant switch) |
| **Rollback speed** | Immediate (shift back to 0%) | Immediate (switch Service back) |
| **Resource cost** | Low — canary pods only (~10-20% extra) | High — full duplicate stack (2×) |
| **Risk exposure** | Small % of users see new version first | All users switch at once |
| **Testing in prod** | Yes, real traffic at low % | Yes, via preview Service before switch |
| **Metric validation** | During gradual rollout (inline analysis) | Pre-promotion and post-promotion |
| **Database migrations** | Needs backward-compatible schema | Same — both versions hit same DB |
| **Stateful services** | Harder — mixed versions serving state | Cleaner — single active version |

### AI/ML Model Deployment Considerations

AI/ML workloads have unique deployment challenges because behavioral changes are subtle and may not manifest as HTTP errors:

| Challenge | Why It's Different | Strategy |
|-----------|-------------------|----------|
| **Output quality regression** | Model returns 200 OK but worse answers | Canary + custom quality metrics |
| **Latency distribution shift** | New model may be slower at P99 | Canary with latency analysis |
| **Bias drift** | New model may behave differently across demographics | Canary at low % + shadow analysis |
| **A/B behavior divergence** | Two versions give different answers simultaneously | Blue-green avoids split-brain |
| **Rollback semantics** | Users may have received bad recommendations | Canary limits blast radius |

**Recommendation for AI agents:**
- **Canary** when you have quality metrics (accuracy, relevance scores, user feedback signals) — the gradual rollout lets you detect subtle degradation before full exposure
- **Blue-green** when behavior must be consistent across all users (e.g., financial models, compliance-sensitive outputs) — avoids two model versions giving different answers simultaneously
- **Both strategies** benefit from custom AnalysisTemplates that query model-specific metrics, not just HTTP status codes

**Example: AI model canary with quality metrics:**
```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: model-quality
spec:
  metrics:
  - name: response-quality-score
    interval: 120s
    count: 10
    successCondition: result[0] >= 0.85   # quality score threshold
    failureLimit: 3
    provider:
      prometheus:
        address: http://prometheus.monitoring:9090
        query: |
          avg(model_response_quality_score{version="canary"}[10m])
  - name: hallucination-rate
    interval: 120s
    count: 10
    successCondition: result[0] <= 0.02   # < 2% hallucination rate
    failureLimit: 2
    provider:
      prometheus:
        address: http://prometheus.monitoring:9090
        query: |
          sum(rate(model_hallucination_detected_total{version="canary"}[10m]))
          /
          sum(rate(model_requests_total{version="canary"}[10m]))
```

### Rollout Operations

```bash
# Watch rollout status
kubectl argo rollouts get rollout my-app -n my-app --watch

# Manually promote (advance to next step or full promotion)
kubectl argo rollouts promote my-app -n my-app

# Full promote (skip remaining steps)
kubectl argo rollouts promote my-app -n my-app --full

# Abort rollout (rollback to stable)
kubectl argo rollouts abort my-app -n my-app

# Retry aborted rollout
kubectl argo rollouts retry rollout my-app -n my-app

# Set image (trigger new rollout)
kubectl argo rollouts set image my-app my-app=my-registry/my-app:v3.0.0 -n my-app
```

## ApplicationSets

ApplicationSets dynamically generate ArgoCD Application resources from templates. Instead of manually creating one Application per environment/cluster, a single ApplicationSet produces all of them.

### List Generator

The simplest generator — explicitly enumerate environments with per-environment parameters:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: my-app
  namespace: argocd
spec:
  generators:
  - list:
      elements:
      - env: dev
        namespace: my-app-dev
        cluster: https://kubernetes.default.svc
        replicas: "1"
        syncPolicy: "automated"
      - env: staging
        namespace: my-app-staging
        cluster: https://kubernetes.default.svc
        replicas: "2"
        syncPolicy: "automated"
      - env: prod
        namespace: my-app-prod
        cluster: https://prod-cluster.example.com
        replicas: "3"
        syncPolicy: "manual"
  template:
    metadata:
      name: 'my-app-{{env}}'
    spec:
      project: default
      source:
        repoURL: https://github.com/your-org/my-app-manifests
        targetRevision: HEAD
        path: 'k8s/overlays/{{env}}'
      destination:
        server: '{{cluster}}'
        namespace: '{{namespace}}'
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
```

Template variables use `{{name}}` syntax and are substituted from each element in the list.

### Git Directory Generator

Automatically create one Application per directory in the repo. Adding a new directory creates a new Application without editing the ApplicationSet:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: my-app-envs
  namespace: argocd
spec:
  generators:
  - git:
      repoURL: https://github.com/your-org/my-app-manifests
      revision: HEAD
      directories:
      - path: 'k8s/overlays/*'
  template:
    metadata:
      name: 'my-app-{{path.basename}}'
    spec:
      project: default
      source:
        repoURL: https://github.com/your-org/my-app-manifests
        targetRevision: HEAD
        path: '{{path}}'
      destination:
        server: https://kubernetes.default.svc
        namespace: 'my-app-{{path.basename}}'
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
```

Built-in variables: `{{path}}` is the full directory path, `{{path.basename}}` is the last segment (e.g., `dev`, `staging`, `prod`).

### Cluster Generator

Generate one Application per registered ArgoCD cluster. Automatically discovers clusters — adding a new cluster to ArgoCD creates an Application for it:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: my-app-all-clusters
  namespace: argocd
spec:
  generators:
  - clusters:
      selector:
        matchLabels:
          env: production
  template:
    metadata:
      name: 'my-app-{{name}}'
    spec:
      project: default
      source:
        repoURL: https://github.com/your-org/my-app-manifests
        targetRevision: HEAD
        path: k8s/overlays/prod
      destination:
        server: '{{server}}'
        namespace: my-app
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
```

Built-in variables: `{{name}}` is the cluster name, `{{server}}` is the API server URL. The `selector.matchLabels` filters which clusters get an Application.

### Cluster Generator with Environment-Specific Value Files

Use cluster labels to select the correct Helm values file per environment. Add custom labels to cluster Secrets:

```yaml
# clusters/staging-cluster-secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: staging-us-east
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: cluster
    env: staging
    region: us-east
    tier: non-prod
type: Opaque
stringData:
  name: staging-us-east
  server: https://staging-us-east.example.com:6443
  config: |
    { "bearerToken": "..." }
---
apiVersion: v1
kind: Secret
metadata:
  name: prod-us-east
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: cluster
    env: production
    region: us-east
    tier: prod
type: Opaque
stringData:
  name: prod-us-east
  server: https://prod-us-east.example.com:6443
  config: |
    { "bearerToken": "..." }
```

**ApplicationSet with per-cluster Helm values:**
```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: my-app-multi-cluster
  namespace: argocd
spec:
  generators:
  - clusters:
      selector:
        matchLabels:
          tier: prod
      # Expose cluster labels as template variables
      values:
        env: '{{metadata.labels.env}}'
        region: '{{metadata.labels.region}}'
  template:
    metadata:
      name: 'my-app-{{name}}'
      labels:
        env: '{{values.env}}'
        region: '{{values.region}}'
    spec:
      project: production
      source:
        repoURL: https://github.com/your-org/my-app-manifests
        targetRevision: HEAD
        path: helm/my-app
        helm:
          valueFiles:
          - values.yaml                          # base values
          - values-{{values.env}}.yaml           # values-production.yaml
          - values-{{values.region}}.yaml        # values-us-east.yaml
          - values-{{name}}.yaml                 # values-prod-us-east.yaml (cluster-specific overrides)
          parameters:
          - name: cluster.name
            value: '{{name}}'
          - name: cluster.region
            value: '{{values.region}}'
      destination:
        server: '{{server}}'
        namespace: my-app
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
        syncOptions:
        - CreateNamespace=true
```

**Corresponding Helm values file structure in Git:**
```
helm/my-app/
├── values.yaml                  # base defaults (replicas: 1, resources, etc.)
├── values-staging.yaml          # staging overrides (replicas: 1, debug: true)
├── values-production.yaml       # prod overrides (replicas: 3, resources.limits.cpu: 2)
├── values-us-east.yaml          # region overrides (ingress.domain: us-east.example.com)
├── values-eu-west.yaml          # region overrides (ingress.domain: eu-west.example.com)
├── values-prod-us-east.yaml     # cluster-specific (optional fine-tuning)
└── Chart.yaml
```

**Kustomize variant (per-cluster overlays via path):**
```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: my-app-kustomize-clusters
  namespace: argocd
spec:
  generators:
  - clusters:
      selector:
        matchExpressions:
        - key: env
          operator: In
          values: [staging, production]
      values:
        env: '{{metadata.labels.env}}'
  template:
    metadata:
      name: 'my-app-{{name}}'
    spec:
      project: default
      source:
        repoURL: https://github.com/your-org/my-app-manifests
        targetRevision: HEAD
        path: 'k8s/overlays/{{values.env}}'  # k8s/overlays/staging or k8s/overlays/production
      destination:
        server: '{{server}}'
        namespace: my-app
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
```

### Matrix Generator

Combine two generators to produce the **cartesian product** of their outputs. Each combination generates one Application:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: my-app-matrix
  namespace: argocd
spec:
  generators:
  - matrix:
      generators:
      # Generator 1: clusters labeled for production
      - clusters:
          selector:
            matchLabels:
              env: production
      # Generator 2: list of application components
      - list:
          elements:
          - component: frontend
            path: k8s/overlays/prod/frontend
            port: "3000"
          - component: backend
            path: k8s/overlays/prod/backend
            port: "8080"
          - component: worker
            path: k8s/overlays/prod/worker
            port: "9090"
  template:
    metadata:
      name: '{{component}}-{{name}}'  # e.g., frontend-us-east, backend-eu-west
    spec:
      project: default
      source:
        repoURL: https://github.com/your-org/my-app-manifests
        targetRevision: HEAD
        path: '{{path}}'
      destination:
        server: '{{server}}'
        namespace: '{{component}}'
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
```

With 3 production clusters and 3 components, this generates 9 Applications. Adding a 4th cluster automatically creates 3 more Applications.

### Matrix: Git Directories × Clusters

Deploy every overlay to every matching cluster:

```yaml
spec:
  generators:
  - matrix:
      generators:
      - git:
          repoURL: https://github.com/your-org/my-app-manifests
          revision: HEAD
          directories:
          - path: 'k8s/overlays/*'
      - clusters:
          selector:
            matchLabels:
              tier: '{{path.basename}}'  # Cluster label matches directory name
```

This maps `k8s/overlays/prod/` to clusters labeled `tier: prod`, and `k8s/overlays/staging/` to clusters labeled `tier: staging`.

### Merge Generator

Override specific fields for particular combinations. Unlike matrix (cartesian product), merge lets you set defaults and then override per-environment:

```yaml
spec:
  generators:
  - merge:
      mergeKeys:
      - env
      generators:
      # Base: all environments with defaults
      - list:
          elements:
          - env: dev
            replicas: "1"
            cluster: https://kubernetes.default.svc
          - env: staging
            replicas: "2"
            cluster: https://kubernetes.default.svc
          - env: prod
            replicas: "5"
            cluster: https://prod-cluster.example.com
      # Override: prod gets extra config
      - list:
          elements:
          - env: prod
            replicas: "10"            # Override default of 5
            resourcePolicy: "strict"  # Additional field only for prod
  template:
    metadata:
      name: 'my-app-{{env}}'
    spec:
      project: default
      source:
        repoURL: https://github.com/your-org/my-app-manifests
        targetRevision: HEAD
        path: 'k8s/overlays/{{env}}'
      destination:
        server: '{{cluster}}'
        namespace: 'my-app-{{env}}'
```

### Generator Comparison

| Generator | Use case | Scales with |
|-----------|----------|-------------|
| List | Fixed set of environments with explicit params | Manual additions |
| Git directory | One app per directory in repo | New directories in Git |
| Git file | One app per config file in repo | New files in Git |
| Cluster | One app per registered cluster | New clusters in ArgoCD |
| Matrix | Cartesian product of two generators | Both dimensions independently |
| Merge | Defaults with per-element overrides | Manual additions to override list |

### ApplicationSet Sync Policy

Control what happens when an ApplicationSet removes an element (e.g., deleting an env from the list):

```yaml
spec:
  syncPolicy:
    preserveResourcesOnDeletion: true  # Don't delete cluster resources when Application is removed
  generators:
    # ...
```

Without `preserveResourcesOnDeletion`, removing an element deletes the Application AND all its cluster resources. Set to `true` for safety — orphaned resources can be cleaned up manually.

## Multi-Cluster Management

### External Cluster Registration

ArgoCD manages the **in-cluster** (where ArgoCD runs) automatically. External clusters must be registered explicitly. The `argocd cluster add` command creates a ServiceAccount, ClusterRole, and ClusterRoleBinding on the target cluster, then stores the credentials as a Secret in the ArgoCD namespace.

**What `argocd cluster add` does under the hood:**
```
Target Cluster                          ArgoCD Cluster
┌──────────────────────────────┐       ┌──────────────────────────────┐
│ 1. Creates ServiceAccount    │       │ 4. Stores credentials as     │
│    "argocd-manager" in       │       │    Secret in argocd namespace│
│    kube-system               │       │                              │
│ 2. Creates ClusterRole with  │  ───→ │ 5. ArgoCD controller uses    │
│    full cluster access       │       │    token to manage resources │
│ 3. Creates ClusterRoleBinding│       │                              │
└──────────────────────────────┘       └──────────────────────────────┘
```

**Method 1: CLI-based registration (imperative)**
```bash
# Prerequisites: kubectl context for the target cluster must exist
kubectl config get-contexts

# Register the cluster (uses the kubeconfig context name)
argocd cluster add staging-cluster-context \
  --name staging \
  --kubeconfig ~/.kube/config

# With specific namespace restrictions (least-privilege)
argocd cluster add staging-cluster-context \
  --name staging \
  --namespace my-app-ns \
  --namespace monitoring-ns

# Verify registration
argocd cluster list
argocd cluster get staging
```

**Method 2: Declarative Secret (GitOps-friendly)**

Instead of imperative CLI commands, define the cluster as a Secret in Git. ArgoCD discovers clusters from Secrets with the label `argocd.argoproj.io/secret-type: cluster`.

```yaml
# clusters/staging-cluster-secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: staging-cluster
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: cluster
type: Opaque
stringData:
  name: staging
  server: https://staging-k8s-api.example.com:6443
  config: |
    {
      "bearerToken": "<service-account-token>",
      "tlsClientConfig": {
        "insecure": false,
        "caData": "<base64-encoded-ca-cert>"
      }
    }
```

**Method 3: EKS with IAM roles (no static tokens)**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: eks-production
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: cluster
type: Opaque
stringData:
  name: eks-production
  server: https://ABCDEF1234.gr7.us-east-1.eks.amazonaws.com
  config: |
    {
      "awsAuthConfig": {
        "clusterName": "production-cluster",
        "roleARN": "arn:aws:iam::123456789012:role/argocd-manager"
      },
      "tlsClientConfig": {
        "insecure": false,
        "caData": "<base64-encoded-ca-cert>"
      }
    }
```

**Method 4: GKE with Google service account**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: gke-production
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: cluster
type: Opaque
stringData:
  name: gke-production
  server: https://gke-api.example.com
  config: |
    {
      "execProviderConfig": {
        "command": "argocd-k8s-auth",
        "args": ["gcp"],
        "apiVersion": "client.authentication.k8s.io/v1beta1"
      },
      "tlsClientConfig": {
        "insecure": false,
        "caData": "<base64-encoded-ca-cert>"
      }
    }
```

**Creating the ServiceAccount manually (for declarative registration):**
```bash
# Run these on the TARGET cluster

# 1. Create ServiceAccount
kubectl create serviceaccount argocd-manager -n kube-system

# 2. Create ClusterRole (full access — restrict for least-privilege)
kubectl create clusterrolebinding argocd-manager-role \
  --clusterrole=cluster-admin \
  --serviceaccount=kube-system:argocd-manager

# 3. Create long-lived token (K8s 1.24+ requires explicit Secret)
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: argocd-manager-token
  namespace: kube-system
  annotations:
    kubernetes.io/service-account.name: argocd-manager
type: kubernetes.io/service-account-token
EOF

# 4. Retrieve the token
kubectl get secret argocd-manager-token -n kube-system \
  -o jsonpath='{.data.token}' | base64 -d

# 5. Retrieve the CA cert
kubectl get secret argocd-manager-token -n kube-system \
  -o jsonpath='{.data.ca\.crt}'
```

**Least-privilege ClusterRole (instead of cluster-admin):**
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: argocd-manager-role
rules:
- apiGroups: ["*"]
  resources: ["*"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps", "extensions"]
  resources: ["deployments", "replicasets", "statefulsets", "daemonsets"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: [""]
  resources: ["services", "configmaps", "secrets", "pods", "serviceaccounts", "namespaces"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["networking.k8s.io"]
  resources: ["ingresses", "networkpolicies"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["batch"]
  resources: ["jobs", "cronjobs"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
```

**Cluster registration decision guide:**

| Method | When to Use | GitOps-Safe? |
|--------|-------------|:------------:|
| `argocd cluster add` (CLI) | Quick setup, dev/test | No (imperative) |
| Declarative Secret + bearer token | Production, token-based auth | Yes |
| Declarative Secret + AWS IAM | EKS clusters | Yes |
| Declarative Secret + GCP auth | GKE clusters | Yes |
| Declarative Secret + exec provider | Custom auth flows | Yes |

**Troubleshooting cluster connectivity:**
```bash
# Check cluster status
argocd cluster list
# Look for CONNECTION STATUS: Successful

# Test connectivity from ArgoCD pod
kubectl exec -n argocd deploy/argocd-application-controller -- \
  curl -sk https://staging-k8s-api.example.com:6443/healthz

# Check ArgoCD controller logs for cluster errors
kubectl logs -n argocd deploy/argocd-application-controller | grep -i "cluster"

# Rotate expired token
kubectl delete secret argocd-manager-token -n kube-system
# Re-create the token Secret (see step 3 above)
# Update the cluster Secret in ArgoCD namespace
```

### Multi-Cluster Application

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: multi-cluster-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/your-org/my-app-manifests
    targetRevision: HEAD
    path: k8s/base
  destinations:
  - server: https://primary-cluster-url
    namespace: my-app-primary
  - server: https://secondary-cluster-url
    namespace: my-app-secondary
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

## Secrets Management in GitOps

### Secrets Strategy Comparison

| Approach | Secrets in Git? | External Dependency | Rotation | Best For |
|----------|----------------|---------------------|----------|----------|
| **SealedSecrets** | Encrypted ciphertext | Controller in-cluster | Re-seal + commit | Simple setups, no vault |
| **External Secrets Operator** | Reference only | External vault (Vault, AWS SM, GCP SM) | Automatic via polling | Production with existing vault |
| **SOPS + age/KMS** | Encrypted in-place | KMS or age key | Re-encrypt + commit | Small teams, no controller |

### SealedSecrets: Complete Workflow

**Architecture**: Plaintext → `kubeseal` encrypts with controller's public cert → encrypted YAML safe for Git → controller decrypts in-cluster → creates native `Secret`.

```
┌─────────────┐    kubeseal     ┌──────────────────┐    git push    ┌─────────┐
│  Plaintext   │ ──────────────→│  SealedSecret     │ ─────────────→│   Git   │
│  Secret YAML │   (asymmetric  │  (encrypted YAML) │               │  Repo   │
└─────────────┘    encryption)  └──────────────────┘               └────┬────┘
                                                                        │
                   ArgoCD sync                                          │
┌─────────────┐    ←──────────── ┌──────────────────┐    ←──────────────┘
│  Native K8s  │   controller    │  SealedSecret     │
│  Secret      │   decrypts      │  in cluster       │
└─────────────┘                  └──────────────────┘
```

**Step 1: Install controller**
```bash
# Install sealed-secrets controller
helm repo add sealed-secrets https://bitnami-labs.github.io/sealed-secrets
helm install sealed-secrets sealed-secrets/sealed-secrets \
  --namespace kube-system \
  --set fullnameOverride=sealed-secrets-controller

# Fetch the public cert (for offline sealing)
kubeseal --fetch-cert \
  --controller-name=sealed-secrets-controller \
  --controller-namespace=kube-system > pub-cert.pem
```

**Step 2: Create and seal a secret**
```bash
# Create plaintext secret (NEVER commit this)
kubectl create secret generic db-credentials \
  --from-literal=username=admin \
  --from-literal=password='S3cureP@ss!' \
  --dry-run=client -o yaml > /tmp/db-secret.yaml

# Seal it — output is safe for Git
kubeseal --format yaml \
  --cert pub-cert.pem \
  < /tmp/db-secret.yaml \
  > k8s/overlays/prod/db-sealed-secret.yaml

# Delete the plaintext immediately
rm /tmp/db-secret.yaml
```

**Step 3: SealedSecret manifest (what goes in Git)**
```yaml
apiVersion: bitnami.com/v1alpha1
kind: SealedSecret
metadata:
  name: db-credentials
  namespace: my-app
  annotations:
    # Scope controls who can decrypt:
    # strict (default) — bound to this name + namespace
    # namespace-wide  — any name in this namespace
    # cluster-wide    — any name in any namespace
    sealedsecrets.bitnami.com/managed: "true"
spec:
  encryptedData:
    username: AgBy3i4OJSWK+PiTySYZZA9rO43... # encrypted
    password: AgCtr8OJSWK+PiTyZZA9rOFg43...  # encrypted
  template:
    type: Opaque
    metadata:
      name: db-credentials
      namespace: my-app
      labels:
        app: my-app
```

**Scoping rules:**
```bash
# Strict scope (default) — name + namespace bound
kubeseal --format yaml --scope strict < secret.yaml > sealed.yaml

# Namespace-wide — any Secret name in the namespace
kubeseal --format yaml --scope namespace-wide < secret.yaml > sealed.yaml

# Cluster-wide — portable across namespaces (least secure)
kubeseal --format yaml --scope cluster-wide < secret.yaml > sealed.yaml
```

**Key rotation:**
```bash
# Controller auto-rotates keys every 30 days
# Existing SealedSecrets still decrypt (old keys kept)
# To re-encrypt with latest key:
kubeseal --re-encrypt < sealed-secret.yaml > sealed-secret-new.yaml
mv sealed-secret-new.yaml sealed-secret.yaml
```

### External Secrets Operator (ESO) with HashiCorp Vault

**Architecture**: ESO polls an external vault → creates/updates native `Secret` in cluster. Only a reference (path, key) is stored in Git — no encrypted data at all.

```
┌──────────────┐              ┌────────────────────┐              ┌──────────────┐
│  HashiCorp   │  ←── poll ── │  External Secrets  │  ── sync ──→│  Native K8s  │
│  Vault       │              │  Operator (ESO)    │              │  Secret      │
└──────────────┘              └────────────────────┘              └──────────────┘
       ↑                              ↑
       │                              │  ArgoCD deploys ExternalSecret + SecretStore
       │                        ┌─────┴──────┐
       │                        │  Git Repo   │
       └── credentials ────────│  (no secret  │
           via SecretStore      │   data)     │
                                └─────────────┘
```

**Step 1: Install ESO**
```bash
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets \
  --namespace external-secrets \
  --create-namespace \
  --set installCRDs=true
```

**Step 2: ClusterSecretStore for Vault**
```yaml
# cluster-secret-store.yaml — one per cluster, references Vault
apiVersion: external-secrets.io/v1beta1
kind: ClusterSecretStore
metadata:
  name: vault-backend
spec:
  provider:
    vault:
      server: "https://vault.example.com"
      path: "secret"           # KV v2 mount path
      version: "v2"
      auth:
        kubernetes:
          mountPath: "kubernetes"
          role: "external-secrets"
          # ESO uses the SA token to auth with Vault
          serviceAccountRef:
            name: external-secrets
            namespace: external-secrets
```

**Step 3: Namespace-scoped SecretStore (alternative)**
```yaml
# secret-store.yaml — per-namespace, more restrictive
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: vault-backend
  namespace: my-app
spec:
  provider:
    vault:
      server: "https://vault.example.com"
      path: "secret"
      version: "v2"
      auth:
        tokenSecretRef:
          name: vault-token
          key: token
```

**Step 4: ExternalSecret (what goes in Git)**
```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: db-credentials
  namespace: my-app
spec:
  refreshInterval: 1h              # polling interval
  secretStoreRef:
    name: vault-backend
    kind: ClusterSecretStore
  target:
    name: db-credentials            # resulting K8s Secret name
    creationPolicy: Owner           # ESO owns the Secret lifecycle
    deletionPolicy: Retain          # keep Secret if ExternalSecret deleted
  data:
  - secretKey: username              # key in the K8s Secret
    remoteRef:
      key: my-app/database           # Vault path
      property: username             # Vault key within path
  - secretKey: password
    remoteRef:
      key: my-app/database
      property: password
```

**Step 5: ExternalSecret with templating**
```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: db-connection-string
  namespace: my-app
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault-backend
    kind: ClusterSecretStore
  target:
    name: db-connection-string
    template:
      type: Opaque
      data:
        DATABASE_URL: "postgresql://{{ .username }}:{{ .password }}@db.example.com:5432/mydb?sslmode=require"
  data:
  - secretKey: username
    remoteRef:
      key: my-app/database
      property: username
  - secretKey: password
    remoteRef:
      key: my-app/database
      property: password
```

**Step 6: Vault Kubernetes auth setup (prerequisite)**
```bash
# Enable Kubernetes auth in Vault
vault auth enable kubernetes

# Configure it with the cluster's API
vault write auth/kubernetes/config \
  kubernetes_host="https://kubernetes.default.svc" \
  token_reviewer_jwt="$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)" \
  kubernetes_ca_cert=@/var/run/secrets/kubernetes.io/serviceaccount/ca.crt

# Create policy for ESO
vault policy write external-secrets - <<EOF
path "secret/data/my-app/*" {
  capabilities = ["read"]
}
EOF

# Bind role to ESO service account
vault write auth/kubernetes/role/external-secrets \
  bound_service_account_names=external-secrets \
  bound_service_account_namespaces=external-secrets \
  policies=external-secrets \
  ttl=1h
```

**ESO with AWS Secrets Manager (alternative provider):**
```yaml
apiVersion: external-secrets.io/v1beta1
kind: ClusterSecretStore
metadata:
  name: aws-secrets-manager
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-east-1
      auth:
        jwt:
          serviceAccountRef:
            name: external-secrets-sa
            namespace: external-secrets
---
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: api-keys
  namespace: my-app
spec:
  refreshInterval: 30m
  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore
  target:
    name: api-keys
  dataFrom:
  - extract:
      key: prod/my-app/api-keys    # AWS SM secret name
```

### Secrets Management Decision Guide

| Scenario | Recommended | Why |
|----------|-------------|-----|
| No external vault, simple secrets | SealedSecrets | Zero external deps, encrypt + commit |
| Existing HashiCorp Vault | ESO + Vault | Automatic rotation, single source of truth |
| AWS-native stack | ESO + AWS Secrets Manager | IAM integration, no extra infra |
| GCP-native stack | ESO + GCP Secret Manager | Workload Identity, native integration |
| Multicloud / multiple vaults | ESO + ClusterSecretStore per provider | Unified CRD, provider-agnostic apps |
| Secrets shared across clusters | ESO + ClusterSecretStore | Central vault, per-cluster ESO |
| Small team, no controller overhead | SOPS + age/KMS | Encrypt files in-place, no CRDs |

## ArgoCD RBAC Configuration

### Example RBAC Policy

```yaml
# argocd-rbac-cm.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-rbac-cm
  namespace: argocd
data:
  policy.csv: |
    p, role:org-admin, applications, *, */*, allow
    p, role:org-admin, clusters, get, *, allow
    p, role:org-admin, repositories, get, *, allow
    p, role:org-admin, projects, get, *, allow
    g, your-org:team-name, role:org-admin
```

## Monitoring and Observability

### ArgoCD Metrics Configuration

```yaml
# argocd-cmd-params-cm.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cmd-params-cm
  namespace: argocd
data:
  metrics.application.labels: "destination-server,project"
  metrics.application-resource.labels: "group,kind,destination-server,project"
```

### Example Prometheus Rules

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: argocd-rules
  namespace: argocd
spec:
  groups:
  - name: argocd.rules
    rules:
    - alert: ArgoCDAppOutOfSync
      expr: argocd_app_sync_status{sync_status="OutOfSync"} == 1
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "ArgoCD Application {{ $labels.name }} is OutOfSync"
```

## Common Commands

```bash
# Install ArgoCD
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Login to ArgoCD CLI
argocd login <ARGOCD_SERVER>

# List applications
argocd app list

# Get application details
argocd app get <APP_NAME>

# Sync an application
argocd app sync <APP_NAME>

# Refresh an application
argocd app refresh <APP_NAME>

# Delete an application
argocd app delete <APP_NAME>

# Create a project
argocd proj create <PROJECT_NAME> -f <PROJECT_FILE>

# Add repository
argocd repo add <REPO_URL> --username <USERNAME> --password <PASSWORD>

# Add cluster
argocd cluster add <CONTEXT_NAME>
```

## ArgoCD Notifications

ArgoCD Notifications sends alerts when Application events occur (sync success, failure, health changes). Configuration lives in two ConfigMaps in the `argocd` namespace.

### Notification Architecture

```
Application Event → Trigger (when to notify) → Template (what to send) → Service (where to send)
```

### Service Configuration: argocd-notifications-cm

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  # ============================================
  # Services: where notifications are sent
  # ============================================

  service.slack: |
    token: $slack-token          # References argocd-notifications-secret
    signingSecret: $slack-signing-secret

  service.webhook.grafana: |
    url: https://grafana.example.com/api/annotations
    headers:
    - name: Authorization
      value: Bearer $grafana-token

  service.email: |
    host: smtp.example.com
    port: 587
    from: argocd@example.com
    username: $email-username
    password: $email-password

  # ============================================
  # Templates: what the notification looks like
  # ============================================

  template.app-sync-succeeded: |
    message: |
      Application {{.app.metadata.name}} sync succeeded.
      Revision: {{.app.status.sync.revision}}
      Environment: {{.app.spec.destination.namespace}}
    slack:
      attachments: |
        [{
          "color": "#18be52",
          "title": "{{.app.metadata.name}} synced successfully",
          "fields": [
            {"title": "Application", "value": "{{.app.metadata.name}}", "short": true},
            {"title": "Namespace", "value": "{{.app.spec.destination.namespace}}", "short": true},
            {"title": "Revision", "value": "{{.app.status.sync.revision | trunc 7}}", "short": true},
            {"title": "Time", "value": "{{.app.status.operationState.finishedAt}}", "short": true}
          ]
        }]

  template.app-sync-failed: |
    message: |
      Application {{.app.metadata.name}} sync FAILED.
      Error: {{.app.status.operationState.message}}
    slack:
      attachments: |
        [{
          "color": "#E96D76",
          "title": "{{.app.metadata.name}} sync failed",
          "fields": [
            {"title": "Application", "value": "{{.app.metadata.name}}", "short": true},
            {"title": "Error", "value": "{{.app.status.operationState.message}}", "short": false}
          ]
        }]

  template.app-health-degraded: |
    message: |
      Application {{.app.metadata.name}} is DEGRADED.
    slack:
      attachments: |
        [{
          "color": "#E96D76",
          "title": "{{.app.metadata.name}} health degraded",
          "fields": [
            {"title": "Application", "value": "{{.app.metadata.name}}", "short": true},
            {"title": "Health", "value": "{{.app.status.health.status}}", "short": true}
          ]
        }]

  # ============================================
  # Triggers: when to send notifications
  # ============================================

  trigger.on-sync-succeeded: |
    - when: app.status.operationState.phase in ['Succeeded']
      send: [app-sync-succeeded]

  trigger.on-sync-failed: |
    - when: app.status.operationState.phase in ['Error', 'Failed']
      send: [app-sync-failed]

  trigger.on-health-degraded: |
    - when: app.status.health.status == 'Degraded'
      send: [app-health-degraded]

  trigger.on-sync-status-unknown: |
    - when: app.status.sync.status == 'Unknown'
      send: [app-sync-failed]
```

### Secrets for Notification Services

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: argocd-notifications-secret
  namespace: argocd
type: Opaque
stringData:
  slack-token: xoxb-your-slack-bot-token
  slack-signing-secret: your-signing-secret
  grafana-token: your-grafana-api-key
  email-username: argocd@example.com
  email-password: smtp-password
```

### Subscribing Applications to Notifications

Add annotations to Applications (or ApplicationSets) to subscribe them to triggers:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app-prod
  annotations:
    # Subscribe to specific triggers on specific services
    notifications.argoproj.io/subscribe.on-sync-succeeded.slack: deployments-channel
    notifications.argoproj.io/subscribe.on-sync-failed.slack: alerts-channel
    notifications.argoproj.io/subscribe.on-health-degraded.slack: alerts-channel

    # Subscribe to all triggers on a service
    # notifications.argoproj.io/subscribe.slack: alerts-channel
```

### Default Triggers for All Applications

Instead of annotating each Application, set defaults in `argocd-notifications-cm`:

```yaml
data:
  defaultTriggers: |
    - on-sync-failed
    - on-health-degraded

  defaultTriggers.slack: alerts-channel
```

### Template Variables Reference

| Variable | Description |
|----------|-------------|
| `{{.app.metadata.name}}` | Application name |
| `{{.app.spec.destination.namespace}}` | Target namespace |
| `{{.app.spec.destination.server}}` | Target cluster |
| `{{.app.status.sync.status}}` | Sync status (Synced/OutOfSync) |
| `{{.app.status.sync.revision}}` | Git commit SHA |
| `{{.app.status.health.status}}` | Health status (Healthy/Degraded) |
| `{{.app.status.operationState.phase}}` | Sync phase (Succeeded/Failed/Error) |
| `{{.app.status.operationState.message}}` | Error message on failure |

## Production Checklist

Before deploying to production:

### Infrastructure
- [ ] ArgoCD installed and configured
- [ ] Multiple clusters registered (if needed)
- [ ] Proper resource allocation for ArgoCD components
- [ ] Network policies configured for ArgoCD communication

### Security
- [ ] RBAC configured appropriately
- [ ] TLS certificates properly configured
- [ ] Secrets management implemented (sealed-secrets, etc.)
- [ ] Audit logging enabled
- [ ] Image scanning integrated

### Configuration
- [ ] Project and application configurations reviewed
- [ ] Sync policies configured appropriately
- [ ] Automated sync with pruning enabled
- [ ] Self-healing enabled
- [ ] Proper retry policies configured

### Monitoring
- [ ] ArgoCD metrics collected and visualized
- [ ] Application health dashboards created
- [ ] Alerting configured for OutOfSync applications
- [ ] Health checks implemented
- [ ] Performance baselines established

### Operations
- [ ] Backup and recovery procedures for ArgoCD
- [ ] Rollback procedures defined
- [ ] Promotion strategies documented
- [ ] Regular security updates planned

## Troubleshooting

### Common Issues

**Application stuck in OutOfSync:**
```bash
# Check for resources that can't be synced
argocd app diff <APP_NAME>

# Force sync (be careful!)
argocd app sync <APP_NAME> --force
```

**Permission errors:**
```bash
# Check cluster RBAC
argocd cluster get <CLUSTER_NAME>

# Verify repository access
argocd repo get <REPO_URL>
```

**Sync failures:**
```bash
# Check application logs
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-application-controller

# Get detailed sync information
argocd app get <APP_NAME> -o yaml
```

## Manifest Validation Pipeline

Validate manifests at every stage: pre-commit, CI, pre-sync, and post-deploy. Catching errors early prevents broken deployments.

```
Developer → pre-commit hooks → PR CI pipeline → ArgoCD PreSync hook → Post-deploy smoke test
  yamllint    kubeconform          conftest/OPA       schema migration      health check
  helm lint   helm template        argocd app diff    data validation       e2e probe
```

### Pre-Commit Hooks

Catch YAML syntax and schema errors before they reach Git:

```yaml
# .pre-commit-config.yaml
repos:
- repo: https://github.com/adrienverge/yamllint
  rev: v1.35.1
  hooks:
  - id: yamllint
    args: [-c, .yamllint.yaml]
    files: \.(yaml|yml)$

- repo: https://github.com/yannh/kubeconform
  rev: v0.6.4
  hooks:
  - id: kubeconform
    args:
    - -strict
    - -ignore-missing-schemas
    - -kubernetes-version=1.29.0
    - -schema-location=default
    - -schema-location=https://raw.githubusercontent.com/datreeio/CRDs-catalog/main/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json
    files: ^k8s/

- repo: https://github.com/gruntwork-io/pre-commit
  rev: v0.1.23
  hooks:
  - id: helmlint
```

```yaml
# .yamllint.yaml
extends: default
rules:
  line-length:
    max: 200
  truthy:
    allowed-values: ['true', 'false', 'yes', 'no']
  comments:
    min-spaces-from-content: 1
  document-start: disable
```

### CI Validation Pipeline

Full validation in CI before ArgoCD ever sees the manifests:

```yaml
name: GitOps Validation
on:
  pull_request:
    paths: ['k8s/**', 'helm/**']

jobs:
  validate-manifests:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4

    - name: Install tools
      run: |
        # kubeconform — schema validation (faster than kubeval, supports CRDs)
        curl -sL https://github.com/yannh/kubeconform/releases/latest/download/kubeconform-linux-amd64.tar.gz | tar xz
        sudo mv kubeconform /usr/local/bin/

        # conftest — OPA policy testing
        curl -sL https://github.com/open-policy-agent/conftest/releases/latest/download/conftest_0.50.0_Linux_x86_64.tar.gz | tar xz
        sudo mv conftest /usr/local/bin/

    # Stage 1: YAML lint
    - name: YAML lint
      run: yamllint -c .yamllint.yaml k8s/ helm/

    # Stage 2: Kubernetes schema validation
    - name: Validate Kustomize output
      run: |
        for env in dev staging prod; do
          echo "=== Validating overlay: $env ==="
          kustomize build k8s/overlays/$env | kubeconform \
            -strict \
            -kubernetes-version 1.29.0 \
            -schema-location default \
            -schema-location 'https://raw.githubusercontent.com/datreeio/CRDs-catalog/main/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json' \
            -summary
        done

    # Stage 3: Helm template validation
    - name: Validate Helm charts
      run: |
        for chart in helm/*/; do
          chart_name=$(basename $chart)
          echo "=== Linting chart: $chart_name ==="
          helm lint $chart

          for env in dev staging production; do
            values_file="$chart/values-${env}.yaml"
            if [ -f "$values_file" ]; then
              echo "--- Validating $chart_name with $env values ---"
              helm template $chart_name $chart \
                -f $chart/values.yaml \
                -f $values_file | kubeconform -strict -summary
            fi
          done
        done

    # Stage 4: OPA/Conftest policy checks
    - name: Policy validation
      run: |
        for env in dev staging prod; do
          echo "=== Policy check: $env ==="
          kustomize build k8s/overlays/$env | conftest test - \
            --policy policy/ \
            --all-namespaces
        done

    # Stage 5: ArgoCD diff preview (shows what would change)
    - name: ArgoCD diff preview
      if: github.event_name == 'pull_request'
      env:
        ARGOCD_AUTH_TOKEN: ${{ secrets.ARGOCD_AUTH_TOKEN }}
        ARGOCD_SERVER: ${{ secrets.ARGOCD_SERVER }}
      run: |
        argocd app diff my-app-staging \
          --local k8s/overlays/staging/ \
          --server-side \
          || true  # diff returns non-zero if changes exist
        # Post diff as PR comment
        argocd app diff my-app-staging \
          --local k8s/overlays/staging/ \
          --server-side 2>&1 | tee /tmp/diff.txt
        if [ -s /tmp/diff.txt ]; then
          gh pr comment ${{ github.event.pull_request.number }} \
            --body "### ArgoCD Diff Preview
        \`\`\`diff
        $(cat /tmp/diff.txt)
        \`\`\`"
        fi
```

### OPA/Conftest Policies

```rego
# policy/deployment.rego
package main

deny[msg] {
  input.kind == "Deployment"
  not input.spec.template.spec.containers[_].resources.limits
  msg := sprintf("Deployment %s must have resource limits", [input.metadata.name])
}

deny[msg] {
  input.kind == "Deployment"
  input.spec.template.spec.containers[_].image
  endswith(input.spec.template.spec.containers[_].image, ":latest")
  msg := sprintf("Deployment %s uses :latest tag — use SHA or semver", [input.metadata.name])
}

deny[msg] {
  input.kind == "Deployment"
  not input.spec.template.spec.securityContext.runAsNonRoot
  msg := sprintf("Deployment %s must set runAsNonRoot: true", [input.metadata.name])
}

deny[msg] {
  input.kind == "Deployment"
  not input.spec.template.spec.containers[_].readinessProbe
  msg := sprintf("Deployment %s must have a readinessProbe", [input.metadata.name])
}

deny[msg] {
  input.kind == "Service"
  input.spec.type == "LoadBalancer"
  not input.metadata.annotations["service.beta.kubernetes.io/aws-load-balancer-internal"]
  msg := sprintf("Service %s: LoadBalancer must be annotated as internal", [input.metadata.name])
}
```

### ApplicationSet Dry-Run

Preview what Applications an ApplicationSet would generate without applying:

```bash
# Render ApplicationSet locally (requires argocd CLI 2.8+)
argocd appset generate my-app-appset -o yaml

# Diff against what's currently in the cluster
argocd appset generate my-app-appset -o yaml | \
  diff <(argocd app list -p my-app -o yaml) -

# Validate the generated Applications
argocd appset generate my-app-appset -o yaml | kubeconform -strict -summary
```

### Post-Deploy Verification

ArgoCD PreSync + PostSync hooks for automated verification (see Resource Hooks section above):

```yaml
# Combine with Argo Rollouts analysis for full verification chain:
# PreSync:  schema migration + data validation
# Sync:     deploy new version (canary or blue-green)
# Analysis: Prometheus metrics (success rate, latency, error rate)
# PostSync: smoke test (HTTP probe to /healthz)
# On fail:  automatic rollback + SyncFail notification to Slack
```

## Production Readiness Checklist

Use this checklist before deploying ArgoCD to production:

### Cluster & Access
- [ ] External clusters registered with least-privilege ClusterRole (not `cluster-admin`)
- [ ] Declarative cluster Secrets in Git (not imperative `argocd cluster add`)
- [ ] Cluster connectivity monitored with alerts for `ClusterNotAccessible`

### AppProjects & RBAC
- [ ] Dedicated AppProject per team (not `default` project)
- [ ] `sourceRepos` restricted to team's repositories
- [ ] `destinations` restricted to team's namespaces
- [ ] `clusterResourceWhitelist` empty unless explicitly needed
- [ ] RBAC policies in `argocd-rbac-cm` with named roles (not wildcards)
- [ ] OIDC/SSO group mappings instead of local accounts

### Sync Policies
- [ ] `selfHeal: true` on production (revert manual drift)
- [ ] `prune: false` on production (or `true` with sync windows)
- [ ] Sync windows restrict prod deploys to business hours
- [ ] Emergency override procedure documented and tested
- [ ] Retry policy configured (`limit: 3` with exponential backoff)

### Secrets
- [ ] No plaintext secrets in Git (SealedSecrets or ExternalSecrets)
- [ ] ExternalSecret `refreshInterval` set appropriately
- [ ] Vault/secret store credentials rotated on schedule
- [ ] `deletionPolicy: Retain` on ExternalSecrets (keep Secret if ESO removed)

### Progressive Delivery
- [ ] Argo Rollouts installed for canary/blue-green deployments
- [ ] AnalysisTemplates configured with Prometheus metrics
- [ ] `autoPromotionEnabled: false` for production Rollouts
- [ ] Rollback tested and verified end-to-end

### Validation
- [ ] Pre-commit hooks: yamllint + kubeconform
- [ ] CI pipeline: schema validation + OPA policy checks + ArgoCD diff
- [ ] PreSync hooks for database migrations
- [ ] PostSync hooks for smoke tests
- [ ] Kyverno/OPA policies enforced in-cluster

### Notifications & Monitoring
- [ ] `argocd-notifications-cm` configured with Slack/webhook/email
- [ ] Triggers for: sync-succeeded, sync-failed, health-degraded
- [ ] Prometheus metrics enabled (`argocd-cmd-params-cm`)
- [ ] Grafana dashboards for sync duration, health status, resource count
- [ ] Alerts for: sync failures, degraded health, OutOfSync > threshold

### Disaster Recovery
- [ ] ArgoCD configuration backed up (AppProjects, Applications, repos, clusters)
- [ ] `preserveResourcesOnDeletion: true` on all ApplicationSets
- [ ] Git repo backup/mirror strategy in place
- [ ] DR runbook tested: restore ArgoCD from backup → re-sync all apps

### ApplicationSets
- [ ] `preserveResourcesOnDeletion: true` set
- [ ] Cluster labels standardized (env, region, tier)
- [ ] Helm value files layered: base → env → region → cluster-specific
- [ ] Matrix generators tested: verify cartesian product matches expected Applications

## Safety: NEVER

- **Deploy directly to clusters without GitOps** - Always use Git as the source of truth to maintain audit trail and consistency.

- **Commit secrets in plain text to Git** - Always use sealed-secrets, SOPS, or other encryption methods to protect sensitive information.

- **Disable automated sync in production** - Production environments should maintain self-healing capabilities to ensure desired state.

- **Use wildcard permissions in ArgoCD RBAC** - Grant minimal required permissions to prevent security risks.

- **Skip validation of Kubernetes manifests** - Always validate manifests before committing to prevent deployment failures.

- **Manually modify resources managed by ArgoCD** - This creates drift and defeats the purpose of GitOps. Always modify through Git.

- **Ignore OutOfSync applications in production** - Investigate and resolve sync issues promptly to maintain system integrity.

## Safety: ALWAYS

- **Verify sync operations before applying** - Always review what changes will be applied before syncing.

- **Use automated testing in your GitOps pipeline** - Implement validation steps to catch issues before deployment.

- **Maintain separate environments** - Use different overlays or repositories for dev/staging/prod environments.

- **Enable pruning and self-healing** - Automatically remove resources that are no longer in Git.

- **Implement proper backup strategies** - Regularly backup ArgoCD configuration and application state.

- **Monitor application health continuously** - Use ArgoCD's built-in health checks and external monitoring.

## Common Errors Reference

| Error | Cause | Fix |
|-------|-------|-----|
| `OutOfSync` | Manifests in Git don't match cluster state | Run `argocd app sync` to reconcile |
| `ComparisonError` | ArgoCD can't access cluster resources | Check cluster RBAC and connection |
| `Unknown` | New application not yet synced | Run initial sync with `argocd app sync` |
| `Degraded` | Application is running but unhealthy | Check application logs and health checks |
| `SyncFailed` | Sync operation failed | Check controller logs and manifest validity |
| `PermissionDenied` | Insufficient RBAC permissions | Update ArgoCD RBAC policies |
| `RepositoryNotAccessible` | Can't access Git repository | Check repository credentials and connectivity |
| `ClusterNotAccessible` | Can't access target cluster | Verify cluster registration and credentials |
| `InvalidSpecError` | Invalid application specification | Fix application YAML configuration |
| `HealthCheckFailed` | Health checks are failing | Investigate application health and dependencies |

## Reference Documentation

| Reference | Description |
|-----------|-------------|
| [ARGOCD_BEST_PRACTICES.md](references/ARGOCD_BEST_PRACTICES.md) | ArgoCD best practices for production deployments, security configurations, and operational excellence |
| [GITOPS_PATTERNS.md](references/GITOPS_PATTERNS.md) | GitOps implementation patterns, multi-environment strategies, and advanced workflows |
| [MONITORING.md](references/MONITORING.md) | ArgoCD monitoring configurations, alerting rules, and dashboard setups |
| [SECURITY.md](references/SECURITY.md) | Security best practices, RBAC configurations, and secrets management in GitOps |