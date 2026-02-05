# Kubernetes Architecture & Reconciliation Loop

## Control Plane Components

| Component | Responsibility |
|-----------|----------------|
| **kube-apiserver** | Central hub; exposes Kubernetes API; all components communicate through it |
| **etcd** | Distributed key-value store; persists all cluster state |
| **kube-scheduler** | Watches unscheduled Pods; assigns them to suitable nodes |
| **kube-controller-manager** | Runs controller loops that reconcile desired vs actual state |

## Node Components

| Component | Responsibility |
|-----------|----------------|
| **kubelet** | Node agent; ensures Pods run on the node; reports status |
| **kube-proxy** | Maintains network rules; implements Service networking |
| **Container Runtime** | Runs containers (containerd, CRI-O, etc.) |

---

## The Reconciliation Loop

Controllers implement a **control loop** that continuously reconciles desired state with actual state:

```
┌─────────────────────────────────────────────────────────┐
│                  RECONCILIATION LOOP                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│   1. WATCH                                               │
│      └─ Observe current state via API server            │
│                                                          │
│   2. COMPARE                                             │
│      └─ Diff current state vs desired state (spec)      │
│                                                          │
│   3. ACT                                                 │
│      └─ Make changes to converge toward desired state   │
│                                                          │
│   4. REPEAT                                              │
│      └─ Loop continuously (non-terminating)             │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Key Principle**: Controllers don't execute actions directly. They send requests to the API server, which persists state to etcd. Other components watch for changes and act accordingly.

---

## Controller Hierarchy for Deployments

```
┌──────────────────────────────────────────────────────────────────┐
│                    DEPLOYMENT LIFECYCLE                           │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  User creates Deployment                                          │
│         │                                                         │
│         ▼                                                         │
│  ┌─────────────────┐                                             │
│  │  API Server     │ ◄─── Validates and stores in etcd           │
│  └────────┬────────┘                                             │
│           │                                                       │
│           ▼                                                       │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  DEPLOYMENT CONTROLLER                                       │ │
│  │  • Watches: Deployments                                      │ │
│  │  • Creates/Updates: ReplicaSets                              │ │
│  │  • Manages: Rollouts, rollbacks, scaling                     │ │
│  └────────┬────────────────────────────────────────────────────┘ │
│           │                                                       │
│           ▼                                                       │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  REPLICASET CONTROLLER                                       │ │
│  │  • Watches: ReplicaSets, Pods                                │ │
│  │  • Creates/Deletes: Pods to match replica count              │ │
│  │  • Ensures: Desired number of Pods always running            │ │
│  └────────┬────────────────────────────────────────────────────┘ │
│           │                                                       │
│           ▼                                                       │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  SCHEDULER                                                    │ │
│  │  • Watches: Pods with no assigned node                       │ │
│  │  • Evaluates: Resource requirements, constraints, affinity   │ │
│  │  • Assigns: Pod to optimal node                              │ │
│  └────────┬────────────────────────────────────────────────────┘ │
│           │                                                       │
│           ▼                                                       │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  KUBELET (on assigned node)                                   │ │
│  │  • Watches: Pods assigned to its node                        │ │
│  │  • Pulls: Container images                                   │ │
│  │  • Runs: Containers via container runtime                    │ │
│  │  • Reports: Pod status back to API server                    │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## Component Interactions

### 1. API Server (Central Hub)

All communication flows through the API server:

```
                    ┌─────────────┐
                    │  API Server │
                    └──────┬──────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
   ┌──────────┐     ┌──────────┐     ┌──────────┐
   │  etcd    │     │Controllers│     │ Kubelet  │
   └──────────┘     └──────────┘     └──────────┘
```

- **Validates** all requests
- **Persists** state to etcd
- **Notifies** watchers of changes
- **Authenticates/Authorizes** all operations

### 2. etcd (Source of Truth)

```
┌────────────────────────────────────────┐
│                 etcd                    │
├────────────────────────────────────────┤
│  /registry/deployments/default/myapp   │
│  /registry/replicasets/default/myapp-x │
│  /registry/pods/default/myapp-x-abc    │
│  /registry/services/default/myapp      │
│  /registry/nodes/node-1                │
└────────────────────────────────────────┘
```

- Stores **all cluster state**
- Provides **watch** capability for changes
- Ensures **consistency** across control plane
- Only API server communicates with etcd directly

### 3. Scheduler Decision Flow

```
New Pod (nodeName: null)
         │
         ▼
┌─────────────────────────────────────┐
│         SCHEDULER                    │
├─────────────────────────────────────┤
│ 1. Filter nodes (predicates)        │
│    • Sufficient CPU/memory?         │
│    • Matches nodeSelector?          │
│    • Tolerates taints?              │
│                                      │
│ 2. Score nodes (priorities)         │
│    • Resource balance               │
│    • Affinity/anti-affinity         │
│    • Spread across zones            │
│                                      │
│ 3. Bind Pod to highest-scoring node │
└─────────────────────────────────────┘
         │
         ▼
Pod updated (nodeName: node-1)
```

### 4. Controller Manager

Runs multiple controllers in a single process:

| Controller | Watches | Creates/Manages |
|------------|---------|-----------------|
| Deployment | Deployments | ReplicaSets |
| ReplicaSet | ReplicaSets, Pods | Pods |
| StatefulSet | StatefulSets | Pods, PVCs |
| DaemonSet | DaemonSets, Nodes | Pods |
| Job | Jobs | Pods |
| Service | Services, Pods | Endpoints |
| Node | Nodes | Node status |

---

## Example: Creating a Deployment

```
Step 1: User runs kubectl apply -f deployment.yaml
        └─ kubectl sends POST to API server

Step 2: API Server
        └─ Validates the Deployment spec
        └─ Persists to etcd
        └─ Returns success to kubectl

Step 3: Deployment Controller (watching Deployments)
        └─ Sees new Deployment
        └─ Creates ReplicaSet with matching spec
        └─ Sends POST to API server

Step 4: API Server
        └─ Persists ReplicaSet to etcd

Step 5: ReplicaSet Controller (watching ReplicaSets)
        └─ Sees new ReplicaSet with replicas: 3
        └─ Current Pods: 0, Desired: 3
        └─ Creates 3 Pod objects (nodeName: null)

Step 6: Scheduler (watching Pods with no node)
        └─ Sees 3 unscheduled Pods
        └─ Evaluates each Pod against available nodes
        └─ Binds each Pod to a node

Step 7: Kubelet on each node (watching Pods for its node)
        └─ Sees new Pod assigned to it
        └─ Pulls container image
        └─ Creates and starts container
        └─ Reports Pod status: Running

Step 8: All controllers continue watching
        └─ If a Pod dies, ReplicaSet creates replacement
        └─ If Deployment updated, new ReplicaSet created
        └─ System self-heals continuously
```

---

## Self-Healing in Action

```
┌─────────────────────────────────────────────────────────┐
│  Desired: 3 replicas    Current: 3 Pods running         │
│                         ✓ State matches                 │
└─────────────────────────────────────────────────────────┘
                              │
                    Node failure kills 1 Pod
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│  Desired: 3 replicas    Current: 2 Pods running         │
│                         ✗ State mismatch!               │
└─────────────────────────────────────────────────────────┘
                              │
              ReplicaSet Controller detects mismatch
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│  Action: Create 1 new Pod                               │
│  Scheduler: Assign to healthy node                      │
│  Kubelet: Start container                               │
└─────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│  Desired: 3 replicas    Current: 3 Pods running         │
│                         ✓ State restored                │
└─────────────────────────────────────────────────────────┘
```

---

## Key Takeaways

1. **Declarative Model**: You declare desired state; controllers make it happen
2. **Loose Coupling**: Components communicate only through API server
3. **Watch-based**: Controllers watch for changes, not poll
4. **Level-triggered**: Controllers reconcile entire state, not just react to events
5. **Self-healing**: Continuous loops automatically fix drift from desired state
6. **Single Source of Truth**: etcd stores all state; API server is the only accessor
