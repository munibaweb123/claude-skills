# Kubernetes Security Reference

## Quick Reference: RBAC Components

| Component | Scope | Purpose |
|-----------|-------|---------|
| ServiceAccount | Namespace | Identity for Pods |
| Role | Namespace | Define permissions within namespace |
| ClusterRole | Cluster | Define permissions cluster-wide |
| RoleBinding | Namespace | Grant Role to users/ServiceAccounts |
| ClusterRoleBinding | Cluster | Grant ClusterRole cluster-wide |

---

## Pod Security Standards

Three policy levels from permissive to restrictive:

| Level | Description |
|-------|-------------|
| **Privileged** | Unrestricted; trusted workloads only |
| **Baseline** | Prevents known privilege escalations |
| **Restricted** | Hardened best practices |

---

## Enforcing Pod Security

Apply via namespace labels:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: production
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

Modes:
- `enforce`: Block non-compliant pods
- `audit`: Log audit events
- `warn`: Display warnings

---

## Baseline Policy Requirements

Must NOT use:
- `hostNetwork: true`
- `hostPID: true`
- `hostIPC: true`
- `privileged: true`
- `hostPath` volumes
- Unconfined seccomp profiles

---

## Restricted Policy Requirements

All Baseline requirements PLUS:

```yaml
spec:
  securityContext:
    runAsNonRoot: true
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: app
    securityContext:
      allowPrivilegeEscalation: false
      runAsNonRoot: true
      capabilities:
        drop:
          - ALL
```

---

## Restricted-Compliant Pod

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: secure-pod
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: app
    image: myapp:latest
    securityContext:
      allowPrivilegeEscalation: false
      runAsNonRoot: true
      runAsUser: 1000
      readOnlyRootFilesystem: true
      seccompProfile:
        type: RuntimeDefault
      capabilities:
        drop:
          - ALL
    volumeMounts:
    - name: tmp
      mountPath: /tmp
  volumes:
  - name: tmp
    emptyDir: {}
```

---

## Restricted-Compliant Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: secure-app
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: secure-app
  template:
    metadata:
      labels:
        app: secure-app
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: app
        image: myapp:1.0
        ports:
        - containerPort: 8080
        securityContext:
          allowPrivilegeEscalation: false
          runAsNonRoot: true
          readOnlyRootFilesystem: true
          capabilities:
            drop:
              - ALL
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi
```

---

## Network Policies

Restrict pod-to-pod traffic:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
```

---

## RBAC (Role-Based Access Control)

### RBAC Workflow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ ServiceAccount  │────►│   RoleBinding   │◄────│      Role       │
│ (Identity)      │     │ (Grants access) │     │ (Permissions)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │
        ▼
┌─────────────────┐
│      Pod        │
│ (Uses identity) │
└─────────────────┘
```

### Verbs Reference

| Verb | Description | Example Use |
|------|-------------|-------------|
| `get` | Read single resource | View pod details |
| `list` | List resources | View all pods |
| `watch` | Stream changes | Monitor pod status |
| `create` | Create new resource | Deploy new pod |
| `update` | Modify entire resource | Update deployment |
| `patch` | Partial modification | Scale replicas |
| `delete` | Remove resource | Delete pod |
| `deletecollection` | Delete multiple | Bulk delete |

### Minimal Permissions Principle

**Always grant the minimum permissions required:**

```
Read-only:     ["get", "list", "watch"]
Read-write:    ["get", "list", "watch", "create", "update", "patch", "delete"]
Admin:         ["*"]  # Avoid in production
```

---

## ServiceAccount

ServiceAccounts provide identities for Pods to interact with the Kubernetes API.

### Create ServiceAccount

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: app-service-account
  namespace: production
automountServiceAccountToken: true  # Set false if Pod doesn't need API access
```

### ServiceAccount with Image Pull Secret

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: app-service-account
  namespace: production
imagePullSecrets:
- name: registry-credentials
```

### Pod Using ServiceAccount

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: myapp
  namespace: production
spec:
  serviceAccountName: app-service-account
  containers:
  - name: app
    image: myapp:1.0
```

### Disable Auto-mounted Token (Security Best Practice)

If your Pod doesn't need Kubernetes API access:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: myapp
spec:
  serviceAccountName: app-service-account
  automountServiceAccountToken: false  # Don't mount token
  containers:
  - name: app
    image: myapp:1.0
```

---

## Role (Namespace-scoped Permissions)

### Read-Only Role (Minimal Permissions)

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pod-reader
  namespace: production
rules:
- apiGroups: [""]           # Core API group
  resources: ["pods"]
  verbs: ["get", "list", "watch"]
```

### Role for Specific Resources

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: configmap-manager
  namespace: production
rules:
- apiGroups: [""]
  resources: ["configmaps"]
  resourceNames: ["app-config", "feature-flags"]  # Only specific ConfigMaps
  verbs: ["get", "update", "patch"]
```

### Role for Deployments and Pods

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: deployment-manager
  namespace: production
rules:
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "watch", "create", "update", "patch"]
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch"]
- apiGroups: [""]
  resources: ["pods/log"]
  verbs: ["get"]
```

### Role for Secrets (Minimal)

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: secret-reader
  namespace: production
rules:
- apiGroups: [""]
  resources: ["secrets"]
  resourceNames: ["db-credentials"]  # ONLY specific secret
  verbs: ["get"]                     # ONLY read, not list
```

---

## RoleBinding (Grant Role to Identity)

### Bind Role to ServiceAccount

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: app-pod-reader
  namespace: production
subjects:
- kind: ServiceAccount
  name: app-service-account
  namespace: production
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

### Bind Role to User

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: developer-deployment-access
  namespace: production
subjects:
- kind: User
  name: jane@example.com
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: deployment-manager
  apiGroup: rbac.authorization.k8s.io
```

### Bind Role to Group

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: dev-team-access
  namespace: production
subjects:
- kind: Group
  name: developers
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: deployment-manager
  apiGroup: rbac.authorization.k8s.io
```

---

## ClusterRole (Cluster-wide Permissions)

### Read-Only ClusterRole

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: cluster-pod-reader
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch"]
- apiGroups: [""]
  resources: ["namespaces"]
  verbs: ["get", "list"]
```

### ClusterRole for Node Access

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: node-reader
rules:
- apiGroups: [""]
  resources: ["nodes"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["metrics.k8s.io"]
  resources: ["nodes"]
  verbs: ["get", "list"]
```

---

## ClusterRoleBinding

### Bind ClusterRole to ServiceAccount

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: monitoring-pod-reader
subjects:
- kind: ServiceAccount
  name: monitoring-sa
  namespace: monitoring
roleRef:
  kind: ClusterRole
  name: cluster-pod-reader
  apiGroup: rbac.authorization.k8s.io
```

---

## Complete RBAC Example

Full workflow: ServiceAccount → Role → RoleBinding → Deployment

```yaml
# 1. ServiceAccount
apiVersion: v1
kind: ServiceAccount
metadata:
  name: myapp-sa
  namespace: production
---
# 2. Role with minimal permissions
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: myapp-role
  namespace: production
rules:
- apiGroups: [""]
  resources: ["configmaps"]
  resourceNames: ["myapp-config"]
  verbs: ["get", "watch"]
- apiGroups: [""]
  resources: ["secrets"]
  resourceNames: ["myapp-secrets"]
  verbs: ["get"]
---
# 3. RoleBinding
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: myapp-rolebinding
  namespace: production
subjects:
- kind: ServiceAccount
  name: myapp-sa
  namespace: production
roleRef:
  kind: Role
  name: myapp-role
  apiGroup: rbac.authorization.k8s.io
---
# 4. Deployment using ServiceAccount
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: production
spec:
  replicas: 2
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      serviceAccountName: myapp-sa
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
      containers:
      - name: app
        image: myapp:1.0
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
              - ALL
```

---

## Permission Verification with kubectl auth can-i

### Check Your Own Permissions

```bash
# Can I create deployments?
kubectl auth can-i create deployments

# Can I delete pods in production namespace?
kubectl auth can-i delete pods -n production

# Can I get secrets?
kubectl auth can-i get secrets

# List all permissions in a namespace
kubectl auth can-i --list -n production
```

### Check ServiceAccount Permissions

```bash
# Check what a ServiceAccount can do
kubectl auth can-i get pods --as=system:serviceaccount:production:myapp-sa -n production

# Check if ServiceAccount can access secrets
kubectl auth can-i get secrets --as=system:serviceaccount:production:myapp-sa -n production

# List all permissions for ServiceAccount
kubectl auth can-i --list --as=system:serviceaccount:production:myapp-sa -n production
```

### Check User Permissions

```bash
# Check what a user can do
kubectl auth can-i create deployments --as=jane@example.com -n production

# List all permissions for user
kubectl auth can-i --list --as=jane@example.com -n production
```

### Verify RBAC Configuration

```bash
# Get all roles in namespace
kubectl get roles -n production

# Get all rolebindings in namespace
kubectl get rolebindings -n production

# Describe role to see permissions
kubectl describe role myapp-role -n production

# Describe rolebinding to see subjects
kubectl describe rolebinding myapp-rolebinding -n production

# Get ServiceAccount details
kubectl get serviceaccount myapp-sa -n production -o yaml
```

### Debug RBAC Issues

```bash
# Check if ServiceAccount exists
kubectl get sa myapp-sa -n production

# Check if Role exists and has correct rules
kubectl get role myapp-role -n production -o yaml

# Check if RoleBinding exists and references correct role/subject
kubectl get rolebinding myapp-rolebinding -n production -o yaml

# Test from inside a Pod
kubectl exec -it myapp-pod -n production -- \
  cat /var/run/secrets/kubernetes.io/serviceaccount/token
```

---

## Common RBAC Patterns

### Pattern 1: Read-Only Monitoring

```yaml
# ServiceAccount for monitoring tools
apiVersion: v1
kind: ServiceAccount
metadata:
  name: monitoring-sa
  namespace: monitoring
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: monitoring-reader
rules:
- apiGroups: [""]
  resources: ["pods", "services", "endpoints", "nodes"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments", "replicasets"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: monitoring-reader-binding
subjects:
- kind: ServiceAccount
  name: monitoring-sa
  namespace: monitoring
roleRef:
  kind: ClusterRole
  name: monitoring-reader
  apiGroup: rbac.authorization.k8s.io
```

### Pattern 2: CI/CD Deployment

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: cicd-deployer
  namespace: production
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: deployment-role
  namespace: production
rules:
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "watch", "create", "update", "patch"]
- apiGroups: [""]
  resources: ["services", "configmaps"]
  verbs: ["get", "list", "watch", "create", "update", "patch"]
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: cicd-deployer-binding
  namespace: production
subjects:
- kind: ServiceAccount
  name: cicd-deployer
  namespace: production
roleRef:
  kind: Role
  name: deployment-role
  apiGroup: rbac.authorization.k8s.io
```

### Pattern 3: Secret Reader (Minimal)

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: secret-reader-sa
  namespace: production
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: specific-secret-reader
  namespace: production
rules:
- apiGroups: [""]
  resources: ["secrets"]
  resourceNames: ["db-password", "api-key"]  # ONLY these secrets
  verbs: ["get"]                              # ONLY get, not list
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: secret-reader-binding
  namespace: production
subjects:
- kind: ServiceAccount
  name: secret-reader-sa
  namespace: production
roleRef:
  kind: Role
  name: specific-secret-reader
  apiGroup: rbac.authorization.k8s.io
```

---

## Secret Security Best Practices

1. **Enable encryption at rest** in etcd
2. **Use RBAC** for least-privilege access
3. **Use external secret stores** (Vault, AWS Secrets Manager)
4. **Avoid committing secrets** to version control
5. **Use `resourceNames`** to limit access to specific secrets
6. **Avoid `list` verb** for secrets when possible

---

## Security Checklist

- [ ] Enforce Pod Security Standards
- [ ] Run as non-root user
- [ ] Drop all capabilities
- [ ] Use read-only root filesystem
- [ ] Set resource limits
- [ ] Use Network Policies
- [ ] Create dedicated ServiceAccounts (don't use default)
- [ ] Apply minimal RBAC permissions
- [ ] Use `resourceNames` to limit access
- [ ] Verify permissions with `kubectl auth can-i`
- [ ] Disable automountServiceAccountToken when not needed
- [ ] Encrypt secrets at rest
- [ ] Scan images for vulnerabilities
- [ ] Use private registries
