# GitOps Implementation Patterns

This document outlines various GitOps implementation patterns for different use cases and environments.

## Basic GitOps Pattern

The fundamental GitOps pattern involves storing the entire desired state of your infrastructure in Git:

```
Developer commits -> Git Repository -> ArgoCD Sync -> Kubernetes Cluster
```

### Implementation Steps:
1. Define infrastructure and applications as code in Git
2. Configure ArgoCD to monitor the Git repository
3. ArgoCD continuously compares Git state with cluster state
4. ArgoCD automatically reconciles differences

## Multi-Environment Patterns

### Environment-Specific Branches
```
main ──→ dev
 │       │
 └──→ staging
      │
      └──→ production
```

### Implementation:
```yaml
# dev-application.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app-dev
spec:
  source:
    repoURL: https://github.com/org/repo
    targetRevision: dev  # Track dev branch
    path: k8s/dev
  destination:
    namespace: my-app-dev
```

### Environment-Specific Directories
```
repository/
├── k8s/
│   ├── base/
│   ├── dev/
│   ├── staging/
│   └── prod/
```

## Application Delivery Patterns

### App-of-Apps Pattern
Deploy applications through a parent application:

```yaml
# root-application.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: root-application
spec:
  source:
    repoURL: https://github.com/org/applications
    targetRevision: HEAD
    path: apps
    directory:
      recurse: true
  destination:
    server: https://kubernetes.default.svc
    namespace: argocd
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

### Application Sets Pattern
Use ApplicationSet controller for dynamic application creation:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: guestbook
  namespace: argocd
spec:
  generators:
  - git:
      repoURL: https://github.com/org/environment-configs
      revision: HEAD
      directories:
      - path: "environments/*"
  template:
    metadata:
      name: '{{path.basename}}'
    spec:
      project: default
      source:
        repoURL: https://github.com/org/guestbook
        targetRevision: HEAD
        path: '{{path}}'
      destination:
        server: https://kubernetes.default.svc
        namespace: '{{path.basename}}'
```

## Multi-Cluster Patterns

### Cluster-Specific Applications
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: app-us-east
spec:
  source:
    repoURL: https://github.com/org/app-manifests
    targetRevision: HEAD
    path: k8s/base
  destination:
    server: https://us-east-cluster.k8s.example.com  # Specific cluster
    namespace: production
```

### Cluster Groups
```yaml
# Use ApplicationSet to deploy to multiple clusters
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: multi-cluster-deployment
spec:
  generators:
  - clusters:
      selector:
        matchLabels:
          environment: production
  template:
    metadata:
      name: 'app-{{name}}'
    spec:
      project: default
      source:
        repoURL: https://github.com/org/app-manifests
        targetRevision: HEAD
        path: k8s/production
      destination:
        server: '{{server}}'
        namespace: production
```

## Promotion Patterns

### Manual Promotion
1. Developer commits to dev branch
2. Dev team tests in development environment
3. Manual promotion to staging branch
4. QA team tests in staging environment
5. Manual promotion to main branch
6. Automatic deployment to production

### Automated Promotion with Gates
```yaml
# GitHub Actions workflow
name: Automated Promotion
on:
  workflow_run:
    workflows: ["Integration Tests"]
    types: [completed]
    branches: [dev]

jobs:
  promote-to-staging:
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    runs-on: ubuntu-latest
    steps:
      - name: Promote to staging
        run: |
          # Update staging overlay with latest commit
          sed -i "s|tag:.*|tag: ${{ github.sha }}|" k8s/staging/values.yaml
          git add .
          git commit -m "Promote ${{ github.sha }} to staging"
          git push
```

## Container Build Patterns: BuildKit Cache and Metadata

### BuildKit Cache with GitHub Actions Cache Backend

Use `docker/build-push-action` with BuildKit cache directives to avoid rebuilding unchanged layers. The `gha` cache backend stores layers in the GitHub Actions cache.

```yaml
name: Build with Cache
on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3

    - name: Login to Docker Hub
      uses: docker/login-action@v3
      with:
        username: ${{ secrets.DOCKER_USERNAME }}
        password: ${{ secrets.DOCKER_TOKEN }}

    - name: Build and push with GHA cache
      uses: docker/build-push-action@v5
      with:
        context: .
        push: true
        tags: ${{ secrets.DOCKER_USERNAME }}/myapp:${{ github.sha }}
        cache-from: type=gha
        cache-to: type=gha,mode=max
```

`mode=max` caches all layers (including intermediate), not just the final image layers.

### Registry Cache Backend

Store cache layers in a dedicated registry tag instead of GitHub Actions cache. Useful when the GHA cache size limit (10 GB) is too small.

```yaml
    - name: Build and push with registry cache
      uses: docker/build-push-action@v5
      with:
        context: .
        push: true
        tags: ${{ secrets.DOCKER_USERNAME }}/myapp:${{ github.sha }}
        cache-from: type=registry,ref=${{ secrets.DOCKER_USERNAME }}/myapp:buildcache
        cache-to: type=registry,ref=${{ secrets.DOCKER_USERNAME }}/myapp:buildcache,mode=max
```

### Metadata Action for Automated Tagging

`docker/metadata-action` generates tags and OCI labels from Git context (branch, tag, SHA, semver). This replaces manual tag construction.

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
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
          type=semver,pattern={{major}}.{{minor}}

    - name: Build and push
      uses: docker/build-push-action@v5
      with:
        context: .
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
        cache-from: type=gha
        cache-to: type=gha,mode=max
```

This produces tags like `myapp:sha-abc1234`, `myapp:main`, `myapp:1.2.3`, and `myapp:1.2` from a single config. The `labels` output adds OCI annotations (`org.opencontainers.image.source`, `org.opencontainers.image.revision`, etc.) automatically.

### Multi-Platform Build with Cache

Combine QEMU, Buildx, cache, and metadata for cross-architecture images:

```yaml
    - name: Set up QEMU
      uses: docker/setup-qemu-action@v3

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3

    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v5
      with:
        images: ${{ secrets.DOCKER_USERNAME }}/myapp
        tags: |
          type=sha
          type=semver,pattern={{version}}

    - name: Build and push multi-platform
      uses: docker/build-push-action@v5
      with:
        context: .
        platforms: linux/amd64,linux/arm64
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
        cache-from: type=gha
        cache-to: type=gha,mode=max
```

## CI Patterns: Matrix Builds and Secrets

### Matrix Strategy for Multi-Version Testing

Use `strategy.matrix` to run tests across multiple runtime versions or configurations in parallel. All combinations must pass before downstream jobs execute.

```yaml
name: CI with Matrix Build
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Lint Kubernetes manifests
      run: |
        yamllint k8s/
        kubeval k8s/base/*.yaml

  test:
    needs: lint
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, ubuntu-22.04]
        python-version: ["3.11", "3.12"]
        test-type: [unit, integration]
      fail-fast: true  # Stop all jobs on first failure
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    - name: Run ${{ matrix.test-type }} tests
      run: make test-${{ matrix.test-type }}

  build-and-push:
    needs: test  # All matrix combinations must pass
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Login to Docker Hub
      run: |
        echo "${{ secrets.DOCKER_TOKEN }}" | docker login -u "${{ secrets.DOCKER_USERNAME }}" --password-stdin
    - name: Build and push
      run: |
        IMAGE="${{ secrets.DOCKER_USERNAME }}/myapp:${{ github.sha }}"
        docker build -t $IMAGE .
        docker push $IMAGE
```

### Matrix with Include/Exclude

Fine-tune matrix combinations to skip invalid pairings or add specific configurations:

```yaml
strategy:
  matrix:
    k8s-version: ["1.28", "1.29", "1.30"]
    test-suite: [smoke, e2e]
    exclude:
    - k8s-version: "1.28"
      test-suite: e2e  # e2e not supported on 1.28
    include:
    - k8s-version: "1.30"
      test-suite: e2e
      extra-args: "--enable-feature-gate=NewAPI"
```

### Secrets Reference Patterns

Secrets are stored in GitHub repository or organization settings and referenced via `${{ secrets.NAME }}`. They are masked in logs automatically.

```yaml
# Common secret references for GitOps pipelines
steps:
- name: Login to container registry
  run: |
    echo "${{ secrets.DOCKER_TOKEN }}" | docker login -u "${{ secrets.DOCKER_USERNAME }}" --password-stdin

- name: Login to GitHub Container Registry
  run: |
    echo "${{ secrets.GITHUB_TOKEN }}" | docker login ghcr.io -u ${{ github.actor }} --password-stdin

- name: Configure ArgoCD CLI
  run: |
    argocd login ${{ secrets.ARGOCD_SERVER }} \
      --username ${{ secrets.ARGOCD_USERNAME }} \
      --password ${{ secrets.ARGOCD_PASSWORD }} \
      --grpc-web

- name: Update GitOps repo
  run: |
    git clone https://x-access-token:${{ secrets.GITOPS_PAT }}@github.com/org/gitops-repo.git
    cd gitops-repo
    kustomize edit set image myapp=myapp:${{ github.sha }}
    git add . && git commit -m "deploy ${{ github.sha }}" && git push
```

> **Note:** `secrets.GITHUB_TOKEN` is automatically available in every workflow. All other secrets must be created in repo Settings > Secrets and variables > Actions.

## Service Containers for Integration Tests

### PostgreSQL and Redis Services

GitHub Actions `services` run containers alongside your job. Use them for integration tests that need real databases or caches.

```yaml
name: Integration Tests with Services
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  integration-test:
    runs-on: ubuntu-latest
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
    - name: Wait for services
      run: |
        until pg_isready -h localhost -p 5432; do sleep 1; done
        until redis-cli -h localhost ping; do sleep 1; done
    - name: Run migrations
      run: make db-migrate
    - name: Run integration tests
      run: make test-integration
```

### Services with Matrix Strategy

Combine service containers with a matrix to test against multiple database versions:

```yaml
jobs:
  integration-test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        postgres-version: [15, 16]
      fail-fast: true
    services:
      postgres:
        image: postgres:${{ matrix.postgres-version }}
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
    env:
      DATABASE_URL: postgresql://testuser:testpass@localhost:5432/testdb
    steps:
    - uses: actions/checkout@v3
    - name: Run integration tests against Postgres ${{ matrix.postgres-version }}
      run: make test-integration
```

### Environment Variables Pattern

Pass service connection details to tests through `env` at the job or step level. Keep secrets separate from hardcoded test credentials:

```yaml
env:
  # Hardcoded for CI test containers (not real credentials)
  DATABASE_URL: postgresql://testuser:testpass@localhost:5432/testdb
  REDIS_URL: redis://localhost:6379
  # Real secrets for external services
  API_KEY: ${{ secrets.EXTERNAL_API_KEY }}
```

> **Note:** Service containers only run on `ubuntu-*` runners. They are not available on `macos-*` or `windows-*`. Health checks in `options` ensure the service is ready before tests start.

## Quality Gate Patterns

Quality gates enforce that only tested, validated artifacts progress through environments.

### Test-Gated Promotion Pattern

Each environment promotion is conditional on the previous environment's tests passing:

```
build → test → deploy-dev → smoke-test-dev → deploy-staging → e2e-test-staging → deploy-prod
         ✗ STOP               ✗ STOP                            ✗ STOP
```

```yaml
# GitHub Actions: test gate blocks deployment
name: Quality Gated Pipeline
on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - run: make test-unit && make test-integration
    # If this job fails, no downstream jobs execute

  deploy-dev:
    needs: test  # Gate: tests must pass
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - run: |
        cd gitops-repo
        kustomize edit set image myapp=myapp:${{ github.sha }}
        git add . && git commit -m "deploy ${{ github.sha }} to dev" && git push

  smoke-test-dev:
    needs: deploy-dev
    runs-on: ubuntu-latest
    steps:
    - run: |
        argocd app wait my-app-dev --health --timeout 300
        curl --fail https://dev.example.com/healthz

  deploy-staging:
    needs: smoke-test-dev  # Gate: dev smoke tests must pass
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - run: |
        cd gitops-repo
        kustomize edit set image myapp=myapp:${{ github.sha }}
        git add . && git commit -m "promote ${{ github.sha }} to staging" && git push
```

### Policy Gate with OPA/Kyverno

Block sync if manifests violate policies:

```yaml
# Kyverno policy: reject images without a SHA-pinned tag
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-image-digest
spec:
  validationFailureAction: Enforce
  rules:
  - name: require-digest
    match:
      resources:
        kinds: [Pod]
    validate:
      message: "Images must use a digest or SHA-based tag, not :latest"
      pattern:
        spec:
          containers:
          - image: "!*:latest"
```

## Rollback Patterns

### Git Revert Rollback

The standard GitOps rollback — revert the Git commit to restore the previous versioned artifact:

```bash
# Identify the bad commit
git log --oneline -- k8s/overlays/prod/

# Revert it (creates a forward commit pointing to the old image tag)
git revert <commit-sha> --no-edit
git push
# ArgoCD syncs automatically to the previous image
```

### Kustomize Tag Rollback

Re-pin the image tag to a previous known-good version:

```yaml
# overlays/prod/kustomization.yaml — roll back by changing the tag
images:
- name: myapp
  newTag: abc123-known-good  # Previously: def456-bad
```

### ArgoCD Rollout with Automatic Rollback

Use Argo Rollouts to automatically roll back a canary if metrics degrade:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: my-app
spec:
  strategy:
    canary:
      steps:
      - setWeight: 10
      - pause: {duration: 60s}
      - analysis:
          templates:
          - templateName: error-rate-check
      - setWeight: 50
      - pause: {duration: 120s}
      - analysis:
          templates:
          - templateName: error-rate-check
      autoPromotionEnabled: false
---
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: error-rate-check
spec:
  metrics:
  - name: error-rate
    interval: 30s
    failureLimit: 3
    successCondition: result[0] < 0.05
    provider:
      prometheus:
        address: http://prometheus.monitoring:9090
        query: |
          sum(rate(http_requests_total{status=~"5.*",app="my-app"}[5m]))
          /
          sum(rate(http_requests_total{app="my-app"}[5m]))
```

If the error rate exceeds 5% during the canary, the rollout automatically reverts to the previous version.

## Configuration Management Patterns

### Kustomize Pattern
```yaml
# base/kustomization.yaml
resources:
- deployment.yaml
- service.yaml

images:
- name: myapp
  newTag: latest

# overlays/production/kustomization.yaml
bases:
- ../../base

patchesStrategicMerge:
- production-patch.yaml

images:
- name: myapp
  newTag: v1.2.3
```

### Helm Pattern
```yaml
# Chart.yaml
apiVersion: v2
name: myapp
version: 1.0.0

# values.yaml
replicaCount: 1
image:
  repository: myapp
  tag: latest
  pullPolicy: IfNotPresent

# values-production.yaml
replicaCount: 3
image:
  tag: stable
```

## Drift Detection and Remediation

### Self-Healing Configuration
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: self-healing-app
spec:
  syncPolicy:
    automated:
      prune: true
      selfHeal: true  # Automatically fix drift
    syncOptions:
    - CreateNamespace=true
    - ApplyOutOfSyncOnly=true
```

### Selective Self-Healing
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: selective-healing-app
  annotations:
    argocd.argoproj.io/sync-options: ServerSideApply=true  # Use server-side apply
spec:
  syncPolicy:
    automated:
      prune: false  # Don't auto-prune
      selfHeal: true
```

## Security Patterns

### Git Signing Verification
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: signed-commits-app
spec:
  source:
    repoURL: https://github.com/org/secured-repo
    targetRevision: HEAD
    path: k8s
    directory:
      include: '*.yaml'
      exclude: '*.tmp'
  ignoreDifferences:
  - group: apps
    kind: Deployment
    jsonPointers:
    - /spec/template/metadata/annotations/checksum
```

### Immutable Tags
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: immutable-tags-app
spec:
  source:
    repoURL: https://github.com/org/app-manifests
    targetRevision: v1.2.3  # Immutable tag
    path: k8s/production
```

## Validation Patterns

### Pre-Sync Hooks
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: pre-sync-validation-app
spec:
  source:
    repoURL: https://github.com/org/app-manifests
    targetRevision: HEAD
    path: k8s
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
    - PruneLast=true  # Prune resources last
  ignoreDifferences:
  - group: batch
    kind: Job
    managedFieldsManagers: [argocd-application-controller]
```

### Validation Applications
Deploy validation tools as ArgoCD applications:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: kyverno-policy-engine
spec:
  source:
    repoURL: https://github.com/org/policy-manifests
    targetRevision: HEAD
    path: kyverno
  destination:
    server: https://kubernetes.default.svc
    namespace: kyverno
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

## Disaster Recovery Patterns

### Backup Applications
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: backup-controller
spec:
  source:
    repoURL: https://github.com/org/backup-manifests
    targetRevision: HEAD
    path: velero
  destination:
    server: https://kubernetes.default.svc
    namespace: velero
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

### DR Environment Sync
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: dr-sync-app
spec:
  source:
    repoURL: https://github.com/org/app-manifests
    targetRevision: HEAD
    path: k8s
  destination:
    server: https://dr-cluster.example.com  # Disaster recovery cluster
    namespace: production
  syncPolicy:
    automated:
      prune: false  # Don't prune in DR
      selfHeal: true
```