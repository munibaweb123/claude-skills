# Security Best Practices for ArgoCD and GitOps

This document outlines security best practices for implementing and operating ArgoCD in production environments.

## Authentication and Authorization

### RBAC Configuration
Implement proper Role-Based Access Control (RBAC) for ArgoCD:

```yaml
# argocd-rbac-cm.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-rbac-cm
  namespace: argocd
data:
  policy.default: role:readonly  # Default to readonly access
  policy.csv: |
    # Roles
    role:org-admin,policy:eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
    p, role:org-admin, applications, *, */*, allow
    p, role:org-admin, clusters, get, *, allow
    p, role:org-admin, repositories, get, *, allow
    p, role:org-admin, projects, get, *, allow

    role:app-developer,policy:eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
    p, role:app-developer, applications, get, */*, allow
    p, role:app-developer, applications, create, my-project/*, allow
    p, role:app-developer, applications, update, my-project/*, allow
    p, role:app-developer, applications, sync, my-project/*, allow
    p, role:app-developer, applications, delete, my-project/*, allow

    role:readonly,policy:eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
    p, role:readonly, applications, get, */*, allow
    p, role:readonly, projects, get, *, allow

    # Group mappings
    g, "your-org:admin-team", role:org-admin
    g, "your-org:app-developers", role:app-developer
```

### OIDC Integration
Configure OpenID Connect for enterprise authentication:

```yaml
# argocd-cmd-params-cm.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cmd-params-cm
  namespace: argocd
data:
  server.rbac.log.enforce.enable: "true"
  server.disable.auth: "false"
```

```yaml
# argocd-cmd-params-cm.yaml - OIDC Configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cmd-params-cm
  namespace: argocd
data:
  oidc.config: |
    name: Okta
    issuer: https://your-domain.okta.com
    clientID: your-client-id
    clientSecret: $oidc.okta.clientSecret
    requestedScopes: ["openid", "profile", "email"]
```

## Secrets Management

### Git Secrets Protection
Never commit secrets in plain text to Git. Use one of these approaches:

#### Option 1: Sealed Secrets
```yaml
# Install sealed-secrets controller
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.20.5/controller.yaml

# Create a secret locally
kubectl create secret generic my-secret \
  --from-literal=api-key=supersecret \
  --dry-run=client -o json > secret.json

# Seal the secret
kubeseal --format yaml < secret.json > sealed-secret.yaml

# Add to GitOps repository
cat <<EOF > sealed-secret.yaml
apiVersion: bitnami.com/v1alpha1
kind: SealedSecret
metadata:
  name: my-secret
  namespace: my-app
spec:
  encryptedData:
    api-key: AgByWC4uVnJlZGVuY3lQcm90ZWN0ZWQtLS0tCg==
  template:
    metadata:
      name: my-secret
      namespace: my-app
EOF
```

#### Option 2: SOPS (Secrets OPerationS)
```yaml
# Install SOPS and configure with KMS
# .sops.yaml
creation_rules:
  - path_regex: \\.secrets\\.yaml$
    kms: "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"
  - path_regex: .*\\.secrets\\.json$
    kms: "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"
```

```bash
# Encrypt secrets file
sops --encrypt my-secrets.yaml > encrypted-my-secrets.yaml

# In your GitOps repo, use a decryption init container
```

## Network Security

### Network Policies
Implement network policies to restrict traffic to ArgoCD components:

```yaml
# argocd-network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: argocd-server-netpol
  namespace: argocd
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: argocd-server
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-controllers
    ports:
    - protocol: TCP
      port: 8080
    - protocol: TCP
      port: 443
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: kube-system
    ports:
    - protocol: UDP
      port: 53  # DNS
    - protocol: TCP
      port: 53
  - to:
    - podSelector:
        matchLabels:
          app.kubernetes.io/name: argocd-repo-server
    ports:
    - protocol: TCP
      port: 8081
```

### TLS Configuration
Ensure proper TLS configuration for all ArgoCD components:

```yaml
# argocd-tls-certs-cm.yaml
apiVersion: v1
kind: Secret
metadata:
  name: argocd-tls-certs-cm
  namespace: argocd
type: kubernetes.io/tls
data:
  tls.crt: LS0tLS1CRUdJTi...
  tls.key: LS0tLS1CRUdJTi...
```

```yaml
# argocd-cmd-params-cm.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cmd-params-cm
  namespace: argocd
data:
  server.insecure: "false"
  server.rootpath: ""
  server.basehref: "/"
```

## Repository Security

### Private Repository Access
Secure access to private Git repositories:

```yaml
# Create secret for private repo access
kubectl create secret generic argocd-repo-creds \
  --from-literal=sshPrivateKey="$(cat ~/.ssh/id_rsa)" \
  --from-literal=ca.crt="$(cat ca.crt)" \
  --from-literal=config="{"url":"https://github.com/your-org/your-private-repo","sshPrivateKey":"$(cat ~/.ssh/id_rsa)"}"
```

```bash
# Register repository with ArgoCD
argocd repo add git@github.com:your-org/your-private-repo.git \
  --ssh-private-key-path ~/.ssh/id_rsa
```

### Repository Validation
Validate repository content before deployment:

```yaml
# Use admission controllers or pre-sync hooks
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: validated-app
spec:
  source:
    repoURL: https://github.com/org/app-manifests
    targetRevision: HEAD
    path: k8s
    directory:
      include: '*.yaml'
      exclude: '*.tmp'
      jsonnet: {}
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
    - CreateNamespace=true
    - Validate=false  # Disable client-side validation
```

## Cluster Registration Security

### Secure Cluster Access
When registering clusters, use secure authentication methods:

```bash
# Use service accounts instead of personal tokens
argocd cluster add <CONTEXT_NAME> \
  --service-account argocd-manager \
  --namespace default
```

```yaml
# Cluster registration with proper RBAC
apiVersion: v1
kind: ServiceAccount
metadata:
  name: argocd-manager
  namespace: kube-system
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: argocd-manager-role-binding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
- kind: ServiceAccount
  name: argocd-manager
  namespace: kube-system
```

## Image Security

### Image Scanning Integration
Integrate image scanning into your GitOps pipeline:

```yaml
# Trivy integration in CI/CD pipeline
name: Security Scan
on:
  push:
    branches: [main]

jobs:
  security-scan:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Run Trivy vulnerability scanner
      uses: aquasecurity/trivy-action@master
      with:
        scan-type: 'fs'
        format: 'sarif'
        output: 'trivy-results.sarif'
        exit-code: '1'
        ignore-unfixed: true
        vuln-type: 'os,library'
        severity: 'CRITICAL,HIGH'
```

### Image Policy Enforcement
Use Kyverno or OPA Gatekeeper to enforce image policies:

```yaml
# Kyverno policy to enforce signed images
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-signed-images
spec:
  validationFailureAction: Enforce
  background: false
  rules:
  - name: require-signed-images
    match:
      resources:
        kinds:
        - Pod
    validate:
      message: "Images must be from trusted registries and properly tagged"
      pattern:
        spec:
          containers:
          - image: "registry.company.com/*:*"
```

## Audit and Compliance

### Audit Logging
Enable comprehensive audit logging:

```yaml
# argocd-cmd-params-cm.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cmd-params-cm
  namespace: argocd
data:
  server.log.level: "info"
  controller.log.level: "info"
  reposerver.log.level: "info"
  server.audit.enabled: "true"
  server.audit.policy: "log"
```

### Compliance Reporting
Generate compliance reports for regulatory requirements:

```bash
# Generate application compliance report
argocd app list --output yaml > compliance-report.yaml

# Export application history
kubectl get events -n argocd --output wide > argocd-events.log
```

## Security Monitoring

### Security Posture Monitoring
Monitor for security misconfigurations:

```yaml
# Prometheus rule for monitoring security violations
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: argocd-security-violations
  namespace: argocd
spec:
  groups:
  - name: argocd-security
    rules:
    - alert: ArgoCDPrivilegedContainers
      expr: count(kube_pod_container_resource_limits{resource="security_context_privileged", unit="bool"} == 1) > 0
      for: 1m
      labels:
        severity: critical
      annotations:
        summary: "Privileged containers detected in ArgoCD namespace"
```

## Emergency Procedures

### Compromised Credential Response
Steps to take if ArgoCD credentials are compromised:

1. Rotate all ArgoCD secrets immediately
2. Revoke and regenerate API tokens
3. Audit all recent operations
4. Check for unauthorized changes in Git repositories
5. Review and update RBAC policies

### Incident Response
```bash
# Emergency lockdown - disable automated sync
kubectl patch application <APP_NAME> -n argocd \
  --type='merge' -p='{"spec":{"syncPolicy":{"automated":null}}}'

# Check for unauthorized applications
argocd app list --selector '!internal=true'

# Review recent events
kubectl get events -n argocd --sort-by='.lastTimestamp'
```

## Security Hardening

### Minimal Privileges
Run ArgoCD components with minimal required privileges:

```yaml
# ArgoCD server with restricted security context
apiVersion: apps/v1
kind: Deployment
metadata:
  name: argocd-server
  namespace: argocd
spec:
  template:
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 999
        fsGroup: 999
      containers:
      - name: argocd-server
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          runAsNonRoot: true
          runAsUser: 999
          capabilities:
            drop:
            - ALL
```

### Pod Security Standards
Apply Pod Security Standards to ArgoCD namespace:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: argocd
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

## Security Checklist

Before deploying to production:

### Authentication
- [ ] RBAC policies configured with least-privilege access
- [ ] OIDC/LDAP integration set up (if applicable)
- [ ] Default admin password changed
- [ ] Multi-factor authentication enabled (if available)

### Secrets Management
- [ ] No plain text secrets in Git repository
- [ ] Sealed Secrets or SOPS configured
- [ ] Secret encryption keys stored securely
- [ ] Regular secret rotation policies established

### Network Security
- [ ] Network policies applied to restrict traffic
- [ ] TLS certificates properly configured
- [ ] Firewall rules configured appropriately
- [ ] Private repository access secured

### Monitoring
- [ ] Security event monitoring configured
- [ ] Audit logging enabled
- [ ] Alerting for security violations set up
- [ ] Regular security scans scheduled