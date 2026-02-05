# Helm Chart Deployment Workflows

## Standard Development Workflow

### 1. Create New Chart
```bash
helm create mychart
cd mychart
```

### 2. Customize Templates
- Edit templates in the `templates/` directory
- Update `values.yaml` with configurable parameters
- Verify syntax: `helm lint`

### 3. Test Locally
```bash
# Template locally to verify
helm template . --debug

# Install to local cluster for testing
helm install mytest . --dry-run --debug
```

### 4. Package and Distribute
```bash
# Package the chart
helm package .

# Upload to registry/repository
helm push mychart-0.1.0.tgz oci://myregistry/myrepo
```

## Production Deployment Workflow

### 1. Pre-deployment Checks
```bash
# Lint the chart
helm lint

# Test with various values files
helm template . -f values-dev.yaml
helm template . -f values-staging.yaml
helm template . -f values-prod.yaml

# Check for security issues
helm template . | kubeval
```

### 2. Deployment Steps
```bash
# Add repository if using remote charts
helm repo add myrepo https://myrepo.example.com

# Update repository cache
helm repo update

# Install with production values
helm install myapp myrepo/mychart -f values-prod.yaml --namespace production --create-namespace
```

### 3. Post-deployment Validation
```bash
# Check release status
helm status myapp

# Monitor resources
kubectl get pods,svc,ingress -n production

# Check logs
kubectl logs -l app.kubernetes.io/name=myapp -n production
```

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Helm Release
on:
  push:
    branches: [main]

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v3

      - name: Configure Git
        run: |
          git config user.name "$GITHUB_ACTOR"
          git config user.email "$GITHUB_ACTOR@users.noreply.github.com"

      - name: Install Helm
        uses: azure/setup-helm@v3
        with:
          version: v3.10.0

      - name: Run Chart Releaser
        uses: helm/chart-releaser-action@v1.5.0
        env:
          CR_TOKEN: "${{ secrets.GITHUB_TOKEN }}"
```

### Jenkins Pipeline Example
```groovy
pipeline {
    agent any
    stages {
        stage('Lint') {
            steps {
                sh 'helm lint'
            }
        }
        stage('Test') {
            steps {
                sh 'helm template . --debug'
            }
        }
        stage('Package') {
            steps {
                sh 'helm package .'
            }
        }
        stage('Deploy') {
            steps {
                sh 'helm upgrade --install myapp . --namespace production'
            }
        }
    }
}
```

## Multi-Environment Deployment

### Environment-Specific Values
```bash
# Deploy to different environments with different values
helm install myapp . -f values-dev.yaml --namespace dev
helm install myapp . -f values-staging.yaml --namespace staging
helm install myapp . -f values-prod.yaml --namespace prod --atomic
```

### Using Helmfile
Create a `helmfile.yaml`:
```yaml
environments:
  dev:
    values:
      - env/dev.yaml
  prod:
    values:
      - env/prod.yaml

releases:
  - name: myapp
    namespace: {{ .Environment.Name }}
    chart: .
    values:
      - global.yaml
      - "env/{{ .Environment.Name }}.yaml"
```

Deploy with:
```bash
helmfile -e dev sync
helmfile -e prod sync
```

## Rolling Updates and Rollbacks

### Performing Updates
```bash
# Upgrade with new values
helm upgrade myapp . -f new-values.yaml

# Upgrade with specific chart version
helm upgrade myapp myrepo/mychart --version 1.2.0

# Perform dry run first
helm upgrade myapp . --dry-run
```

### Rollback Strategies
```bash
# Check revision history
helm history myapp

# Rollback to previous version
helm rollback myapp

# Rollback to specific revision
helm rollback myapp 2
```

## Best Practices for Production

### 1. Use Atomic Deployments
```bash
helm install myapp . --atomic
helm upgrade myapp . --atomic
```

### 2. Wait for Resources
```bash
helm install myapp . --wait --timeout=10m
```

### 3. Verify Signatures
```bash
helm install myapp . --verify --keyring ./pubkey.gpg
```

### 4. Use Namespaces
```bash
helm install myapp . --namespace mynamespace --create-namespace
```

## Common Commands

### Debugging
```bash
# Render templates locally
helm template . --debug

# Dry run installation
helm install myapp . --dry-run --debug

# Get manifest of deployed release
helm get manifest myapp

# Show differences before upgrade
helm diff upgrade myapp .  # requires helm-diff plugin
```

## Iterative Refinement Workflow

### AI-Assisted Chart Development
The iterative refinement approach enables progressive improvement of Helm charts through cycles of generation, evaluation, and enhancement.

### Iteration Cycle
```bash
# 1. Initial generation based on requirements
helm create mychart

# 2. Evaluation and validation
helm lint mychart
helm template mychart --debug

# 3. Refinement based on feedback
# Update templates/values based on evaluation results

# 4. Re-validation
helm lint mychart -f values-prod.yaml
helm unittest mychart  # if using helm-unittest plugin

# 5. Repeat until requirements are met
```

### AI Collaboration Commands
```bash
# Validate against schema
helm lint mychart -f values-prod.yaml

# Test with multiple configurations
for env in dev staging prod; do
  helm template mychart -f values-$env.yaml --debug
done

# Security validation
helm template mychart | conftest test -
```

### Quality Gates in CI/CD
```yaml
# Example quality gates for iterative refinement
stages:
  - validate
  - test
  - security-check
  - deploy

validate:
  script:
    - helm lint mychart
    - helm template mychart | kubeval --strict

security-check:
  script:
    - helm template mychart | kubesec scan
    - trivy config --severity HIGH,CRITICAL .  # if using Trivy
```

### Management
```bash
# List releases
helm list --all-namespaces

# Uninstall release
helm uninstall myapp

# Clean up old revisions
helm history myapp  # check revisions
# Manually delete old revisions if needed
```

## Security Considerations

### RBAC Setup
```yaml
# Example RBAC for Tiller (for older Helm versions)
apiVersion: v1
kind: ServiceAccount
metadata:
  name: tiller
  namespace: kube-system
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: tiller
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
  - kind: ServiceAccount
    name: tiller
    namespace: kube-system
```

### Chart Signing
```bash
# Generate key pair
helm generate key mykey

# Sign chart
helm sign mychart --keyring ./mykey.secret

# Verify signature
helm verify mychart --keyring ./pubkey.public
```

## Performance Optimization

### Chart Testing
```bash
# Use minimal resource requests for testing
# Use resource quotas in testing namespaces
# Implement proper health checks
# Use initContainers for prerequisites
```

### Monitoring Integration
```yaml
# Include monitoring in chart
{{- if .Values.monitoring.enabled }}
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: {{ include "mychart.fullname" . }}
spec:
  selector:
    matchLabels:
      {{- include "mychart.selectorLabels" . | nindent 6 }}
  endpoints:
  - port: http
{{- end }}
```