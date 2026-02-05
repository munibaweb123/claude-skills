# Helm Chart Testing Reference

## Overview

Comprehensive testing ensures Helm charts work correctly across different environments and configurations. This guide covers multiple testing strategies and patterns.

## Testing Strategies

### 1. Static Analysis (Pre-Deployment)
### 2. Unit Testing (Template Validation)
### 3. Integration Testing (Runtime Validation)
### 4. End-to-End Testing (Full Deployment)

---

## 1. Static Analysis

### Helm Lint

Basic syntax and structure validation:

```bash
# Lint chart
helm lint ./mychart

# Lint with specific values
helm lint ./mychart -f values-prod.yaml

# Lint all environment configurations
helm lint ./mychart -f values-dev.yaml
helm lint ./mychart -f values-staging.yaml
helm lint ./mychart -f values-prod.yaml
```

**Checks:**
- Chart.yaml validity
- Template syntax errors
- Required fields
- File structure

### Helm Template (Dry-Run)

Render templates without installing:

```bash
# Render all templates
helm template myrelease ./mychart

# Render with specific values
helm template myrelease ./mychart -f values-prod.yaml

# Show only specific template
helm template myrelease ./mychart --show-only templates/deployment.yaml

# Debug mode (verbose output)
helm template myrelease ./mychart --debug

# Validate against Kubernetes API
helm template myrelease ./mychart | kubectl apply --dry-run=client -f -
```

**Best for:**
- Template rendering validation
- Variable interpolation testing
- Conditional logic verification

### Schema Validation

Validate values against values.schema.json:

```bash
# Automatic validation (happens during install/upgrade)
helm install myapp ./mychart -f values.yaml

# Manual validation with lint
helm lint ./mychart -f values-prod.yaml
```

**values.schema.json example:**
```json
{
  "$schema": "https://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["image"],
  "properties": {
    "replicaCount": {
      "type": "integer",
      "minimum": 1,
      "maximum": 100
    },
    "image": {
      "type": "object",
      "required": ["repository"],
      "properties": {
        "repository": {"type": "string", "minLength": 1},
        "tag": {"type": "string"},
        "pullPolicy": {
          "type": "string",
          "enum": ["Always", "IfNotPresent", "Never"]
        }
      }
    }
  }
}
```

---

## 2. Unit Testing

### Helm Unittest Plugin

Install:
```bash
helm plugin install https://github.com/helm-unittest/helm-unittest
```

### Test Structure

```yaml
suite: test deployment
templates:
  - deployment.yaml
tests:
  - it: should create deployment
    asserts:
      - isKind:
          of: Deployment
      - equal:
          path: metadata.name
          value: RELEASE-NAME-myapp
```

### Assertion Types

#### Document Assertions

```yaml
# Check document count
- hasDocuments:
    count: 1

# Check resource kind
- isKind:
    of: Deployment

# Check API version
- isAPIVersion:
    of: apps/v1
```

#### Value Assertions

```yaml
# Exact match
- equal:
    path: spec.replicas
    value: 3

# Pattern matching
- matchRegex:
    path: metadata.name
    pattern: "^.*-deployment$"

# Check if value exists
- isNotNull:
    path: spec.template.spec.containers[0].image

# Check if value is null
- isNull:
    path: spec.replicas  # When autoscaling enabled

# Check if field exists
- exists:
    path: metadata.annotations

# Check if field doesn't exist
- notExists:
    path: spec.minReadySeconds
```

#### List Assertions

```yaml
# Contains item
- contains:
    path: spec.template.spec.containers[0].env
    content:
      name: LOG_LEVEL
      value: DEBUG

# Not contains
- notContains:
    path: spec.template.spec.containers
    content:
      name: sidecar

# Length check
- lengthEqual:
    path: spec.template.spec.containers
    count: 1
```

#### Template Failure Assertions

```yaml
# Should fail with error
- failedTemplate:
    errorMessage: "image.repository is required"
```

### Setting Test Values

```yaml
# Set specific values
- it: should use custom image
  set:
    image.repository: myrepo/myapp
    image.tag: v2.0.0
  asserts:
    - equal:
        path: spec.template.spec.containers[0].image
        value: myrepo/myapp:v2.0.0

# Load values from file
- it: should work with dev values
  values:
    - ../values-dev.yaml
  asserts:
    - equal:
        path: spec.replicas
        value: 1

# Override release/chart metadata
- it: should use release name
  release:
    name: test-release
    revision: 5
  chart:
    version: 1.2.3
    appVersion: 2.0.0
  asserts:
    - equal:
        path: metadata.name
        value: test-release-myapp
```

### Running Tests

```bash
# Run all tests
helm unittest .

# Run specific test file
helm unittest -f tests/deployment_test.yaml .

# Verbose output
helm unittest -v .

# Show test output
helm unittest -o tests-output.xml .

# Update snapshots
helm unittest -u .
```

### Test Organization

```
mychart/
├── templates/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   └── hpa.yaml
└── tests/
    ├── deployment_test.yaml
    ├── service_test.yaml
    ├── ingress_test.yaml
    ├── hpa_test.yaml
    ├── helpers_test.yaml
    ├── hooks_test.yaml
    └── values_test.yaml
```

---

## 3. Integration Testing

### Helm Test Hook

Create test pods using the `test` hook:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: {{ include "mychart.fullname" . }}-test-connection
  annotations:
    helm.sh/hook: test
    helm.sh/hook-delete-policy: hook-succeeded
spec:
  restartPolicy: Never
  containers:
    - name: test
      image: curlimages/curl:latest
      command:
        - sh
        - -c
        - |
          # Test health endpoint
          curl --fail http://{{ include "mychart.fullname" . }}:{{ .Values.service.port }}/health

          # Test readiness endpoint
          curl --fail http://{{ include "mychart.fullname" . }}:{{ .Values.service.port }}/ready
```

**Run tests:**
```bash
# Install chart
helm install myapp ./mychart

# Run tests
helm test myapp

# View test logs
kubectl logs myapp-test-connection

# Run tests with cleanup
helm test myapp --logs
```

### Test Categories

#### Connectivity Tests

```yaml
# Test service is accessible
- name: test-service
  command: ["curl", "--fail", "http://myapp:80/health"]

# Test DNS resolution
- name: test-dns
  command: ["nslookup", "myapp.default.svc.cluster.local"]

# Test port is open
- name: test-port
  command: ["nc", "-zv", "myapp", "80"]
```

#### Database Tests

```yaml
# Test database connection
- name: test-database
  command:
    - sh
    - -c
    - |
      pg_isready -h myapp-postgresql -p 5432 -U postgres
      psql postgresql://user:pass@myapp-postgresql:5432/db -c "SELECT 1"
```

#### Redis Tests

```yaml
# Test Redis connection
- name: test-redis
  command:
    - sh
    - -c
    - |
      redis-cli -h myapp-redis-master ping
```

#### API Tests

```yaml
# Test API endpoints
- name: test-api
  command:
    - sh
    - -c
    - |
      # Test GET endpoint
      curl --fail http://myapp/api/health

      # Test POST endpoint
      curl --fail -X POST http://myapp/api/test -d '{"test": true}'

      # Test authentication
      curl --fail -H "Authorization: Bearer token" http://myapp/api/protected
```

---

## 4. End-to-End Testing

### CI/CD Integration

#### GitHub Actions Example

```yaml
name: Test Helm Chart

on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install Helm
        uses: azure/setup-helm@v3

      - name: Lint chart
        run: helm lint ./mychart

      - name: Lint with all values
        run: |
          helm lint ./mychart -f values-dev.yaml
          helm lint ./mychart -f values-staging.yaml
          helm lint ./mychart -f values-prod.yaml

  unittest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install Helm
        uses: azure/setup-helm@v3

      - name: Install helm-unittest
        run: helm plugin install https://github.com/helm-unittest/helm-unittest

      - name: Run unit tests
        run: helm unittest -o tests-output.xml ./mychart

      - name: Upload test results
        uses: actions/upload-artifact@v3
        with:
          name: test-results
          path: tests-output.xml

  integration:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Create k8s cluster (kind)
        uses: helm/kind-action@v1.5.0

      - name: Install chart
        run: |
          helm install myapp ./mychart -f values-dev.yaml --wait

      - name: Run helm tests
        run: helm test myapp --logs

      - name: Check deployment
        run: |
          kubectl get pods
          kubectl get svc
          kubectl logs -l app.kubernetes.io/name=myapp
```

### Local Testing with Kind

```bash
# Create local cluster
kind create cluster --name test-cluster

# Install chart
helm install myapp ./mychart -f values-dev.yaml --wait

# Run tests
helm test myapp --logs

# Check resources
kubectl get all

# Clean up
helm uninstall myapp
kind delete cluster --name test-cluster
```

---

## Testing Patterns

### Pattern 1: Test Matrix (Multiple Environments)

```yaml
# tests/environments_test.yaml
suite: test environments
templates:
  - deployment.yaml
tests:
  - it: development should use 1 replica
    values:
      - ../values-dev.yaml
    asserts:
      - equal:
          path: spec.replicas
          value: 1

  - it: staging should use 2 replicas
    values:
      - ../values-staging.yaml
    asserts:
      - equal:
          path: spec.replicas
          value: 2

  - it: production should use 5 replicas
    values:
      - ../values-prod.yaml
    asserts:
      - equal:
          path: spec.replicas
          value: 5
```

### Pattern 2: Golden Files (Snapshot Testing)

```yaml
# tests/snapshot_test.yaml
suite: test snapshots
templates:
  - deployment.yaml
tests:
  - it: should match golden file
    values:
      - ../values-prod.yaml
    asserts:
      - matchSnapshot: {}
```

Update snapshots:
```bash
helm unittest -u ./mychart
```

### Pattern 3: Conditional Resource Testing

```yaml
# Test optional resources
suite: test conditional resources
templates:
  - ingress.yaml
tests:
  - it: should not create ingress when disabled
    set:
      ingress.enabled: false
    asserts:
      - hasDocuments:
          count: 0

  - it: should create ingress when enabled
    set:
      ingress.enabled: true
    asserts:
      - hasDocuments:
          count: 1
      - isKind:
          of: Ingress
```

### Pattern 4: Security Testing

```yaml
# Test security contexts
suite: test security
templates:
  - deployment.yaml
tests:
  - it: should not run as root
    values:
      - ../values-prod.yaml
    asserts:
      - equal:
          path: spec.template.spec.securityContext.runAsNonRoot
          value: true

  - it: should drop all capabilities
    values:
      - ../values-prod.yaml
    asserts:
      - contains:
          path: spec.template.spec.containers[0].securityContext.capabilities.drop
          content: ALL

  - it: should use read-only root filesystem
    values:
      - ../values-prod.yaml
    asserts:
      - equal:
          path: spec.template.spec.containers[0].securityContext.readOnlyRootFilesystem
          value: true
```

### Pattern 5: Helper Template Testing

```yaml
# Test helper functions
suite: test helpers
templates:
  - deployment.yaml
tests:
  - it: should generate correct fullname
    release:
      name: myrelease
    asserts:
      - equal:
          path: metadata.name
          value: myrelease-myapp

  - it: should use fullnameOverride
    set:
      fullnameOverride: custom-name
    asserts:
      - equal:
          path: metadata.name
          value: custom-name
```

---

## Best Practices

### 1. Test Organization

```
✅ Good: One test file per template
tests/
├── deployment_test.yaml
├── service_test.yaml
└── ingress_test.yaml

❌ Bad: All tests in one file
tests/
└── all_tests.yaml  # Hard to maintain
```

### 2. Test Naming

```yaml
✅ Good: Descriptive test names
- it: should create deployment with correct replica count
- it: should not set replicas when autoscaling is enabled

❌ Bad: Vague test names
- it: test replicas
- it: check deployment
```

### 3. Test Coverage

Ensure tests cover:
- ✅ Default values
- ✅ Each environment (dev, staging, prod)
- ✅ Conditional resources (ingress, HPA)
- ✅ Required fields validation
- ✅ Security configurations
- ✅ Helper templates
- ✅ Hook annotations
- ✅ Edge cases

### 4. Maintainability

```yaml
# Use variables for common values
- it: should use custom image
  set:
    &image
    repository: myrepo/myapp
    tag: v2.0.0
  asserts:
    - equal:
        path: spec.template.spec.containers[0].image
        value: myrepo/myapp:v2.0.0
```

### 5. CI/CD Integration

```bash
# Fail fast on errors
set -e

# Run all validation steps
helm lint ./mychart || exit 1
helm unittest ./mychart || exit 1
helm template ./mychart | kubectl apply --dry-run=client -f - || exit 1
```

---

## Troubleshooting

### Test Failures

```bash
# Run with verbose output
helm unittest -v ./mychart

# Run specific test file
helm unittest -f tests/deployment_test.yaml ./mychart

# Debug template rendering
helm template myapp ./mychart --debug > /tmp/rendered.yaml
cat /tmp/rendered.yaml
```

### Common Issues

**Issue 1: Path not found**
```yaml
# ❌ Wrong: Incorrect path
- equal:
    path: spec.template.containers[0].image

# ✅ Correct: Full path
- equal:
    path: spec.template.spec.containers[0].image
```

**Issue 2: Type mismatch**
```yaml
# ❌ Wrong: Comparing string to integer
- equal:
    path: spec.replicas
    value: "3"  # String

# ✅ Correct: Use correct type
- equal:
    path: spec.replicas
    value: 3  # Integer
```

**Issue 3: Null vs missing**
```yaml
# Check if null
- isNull:
    path: spec.replicas

# Check if doesn't exist
- notExists:
    path: spec.replicas
```

---

## Quick Reference

### Commands

| Command | Purpose |
|---------|---------|
| `helm lint` | Static analysis |
| `helm template` | Render templates |
| `helm unittest` | Run unit tests |
| `helm test` | Run integration tests |
| `helm install --dry-run` | Simulate install |

### Test Files

| File | Tests |
|------|-------|
| `deployment_test.yaml` | Deployment configuration |
| `service_test.yaml` | Service configuration |
| `ingress_test.yaml` | Ingress rules |
| `hpa_test.yaml` | Autoscaling |
| `helpers_test.yaml` | Helper templates |
| `hooks_test.yaml` | Hook annotations |
| `values_test.yaml` | Values validation |

### Assertion Types

| Assertion | Purpose |
|-----------|---------|
| `isKind` | Check resource kind |
| `equal` | Exact value match |
| `matchRegex` | Pattern match |
| `contains` | List contains item |
| `isNull` | Value is null |
| `exists` | Field exists |
| `hasDocuments` | Document count |
| `failedTemplate` | Template should fail |

---

## Summary

Comprehensive testing strategy:

1. **Static Analysis** - Lint and schema validation
2. **Unit Tests** - Template logic with helm-unittest
3. **Integration Tests** - Runtime validation with helm test
4. **E2E Tests** - Full deployment in CI/CD

All layers combined ensure robust, reliable Helm charts.
