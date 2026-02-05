# Testing Guide for Task API Helm Chart

This guide covers all testing strategies for the task-api Helm chart.

## Quick Start

```bash
# 1. Install helm-unittest plugin
helm plugin install https://github.com/helm-unittest/helm-unittest

# 2. Run all tests
cd task-api-chart
helm unittest .

# 3. Install chart for integration tests
helm install task-api . -f values-dev.yaml -n dev --create-namespace

# 4. Run integration tests
helm test task-api -n dev
```

## Testing Layers

### 1. Static Analysis ✅

#### Helm Lint

Validates chart structure and syntax:

```bash
# Lint chart
helm lint .

# Lint with specific values
helm lint . -f values-dev.yaml
helm lint . -f values-staging.yaml
helm lint . -f values-prod.yaml

# Expected output:
# ==> Linting .
# [INFO] Chart.yaml: icon is recommended
# 1 chart(s) linted, 0 chart(s) failed
```

#### Template Rendering

Inspect rendered templates:

```bash
# Render all templates
helm template task-api .

# Render with specific values
helm template task-api . -f values-prod.yaml

# Show only specific template
helm template task-api . --show-only templates/deployment.yaml

# Debug mode (verbose)
helm template task-api . --debug

# Validate against K8s API
helm template task-api . | kubectl apply --dry-run=client -f -
```

#### Schema Validation

Automatically validates against `values.schema.json`:

```bash
# Validation happens during lint
helm lint .

# Also during install/upgrade
helm install task-api . -f values-prod.yaml --dry-run
```

### 2. Unit Testing ✅

#### Run Unit Tests

```bash
# Run all tests
helm unittest .

# Run with verbose output
helm unittest -v .

# Run specific test file
helm unittest -f tests/deployment_test.yaml .

# Output to file
helm unittest -o test-results.xml .
```

#### Test Files

| File | Coverage |
|------|----------|
| [deployment_test.yaml](tests/deployment_test.yaml) | Deployment configuration (15 tests) |
| [service_test.yaml](tests/service_test.yaml) | Service types and ports (7 tests) |
| [ingress_test.yaml](tests/ingress_test.yaml) | Ingress rules and TLS (9 tests) |
| [hpa_test.yaml](tests/hpa_test.yaml) | Autoscaling configuration (8 tests) |
| [helpers_test.yaml](tests/helpers_test.yaml) | Helper templates (7 tests) |
| [hooks_test.yaml](tests/hooks_test.yaml) | Hook annotations and config (14 tests) |
| [values_test.yaml](tests/values_test.yaml) | Values validation (12 tests) |

**Total: 72 unit tests**

#### Test Coverage

```bash
# Test default values
helm unittest -f tests/deployment_test.yaml .

# Test dev environment
helm unittest --set-file values-dev.yaml .

# Test prod environment
helm unittest --set-file values-prod.yaml .

# Test security configurations
helm unittest -f tests/values_test.yaml .
```

### 3. Integration Testing ✅

#### Install Chart

```bash
# Development
helm install task-api . -f values-dev.yaml -n dev --create-namespace --wait

# Staging
helm install task-api . -f values-staging.yaml -n staging --create-namespace --wait

# Production (dry-run first)
helm install task-api . -f values-prod.yaml -n prod --dry-run
helm install task-api . -f values-prod.yaml -n prod --create-namespace --atomic --wait
```

#### Run Helm Tests

```bash
# Run integration tests
helm test task-api -n dev

# View test logs
kubectl logs task-api-test-connection -n dev

# Run tests with cleanup
helm test task-api -n dev --logs

# Expected output:
# NAME: task-api
# TEST SUITE:     task-api-test-connection
# Last Started:   Mon Jan 27 18:00:00 2024
# Last Completed: Mon Jan 27 18:00:10 2024
# Phase:          Succeeded
```

#### Manual Testing

```bash
# Check deployment status
kubectl get pods -n dev -l app.kubernetes.io/name=task-api
kubectl get svc -n dev -l app.kubernetes.io/name=task-api

# Test service connectivity
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -- \
  curl http://task-api:8000/health

# Test database connectivity
kubectl run -it --rm debug --image=postgres:15 --restart=Never -- \
  psql postgresql://taskapi_dev:devpass123@task-api-postgresql:5432/tasks_dev -c "SELECT 1"

# Test Redis connectivity
kubectl run -it --rm debug --image=redis:7 --restart=Never -- \
  redis-cli -h task-api-redis-master ping

# Check logs
kubectl logs -f -l app.kubernetes.io/name=task-api -n dev

# Port-forward for local testing
kubectl port-forward svc/task-api 8000:8000 -n dev
curl http://localhost:8000/health
```

### 4. End-to-End Testing ✅

#### Full Deployment Flow

```bash
# 1. Create test namespace
kubectl create namespace test-e2e

# 2. Install with all dependencies
helm install task-api . -f values-dev.yaml -n test-e2e --wait --timeout 10m

# 3. Verify all resources
kubectl get all -n test-e2e

# 4. Run integration tests
helm test task-api -n test-e2e --logs

# 5. Test upgrades
helm upgrade task-api . -f values-dev.yaml --set replicaCount=2 -n test-e2e --wait

# 6. Verify upgrade
kubectl get pods -n test-e2e

# 7. Test rollback
helm rollback task-api -n test-e2e --wait

# 8. Clean up
helm uninstall task-api -n test-e2e
kubectl delete namespace test-e2e
```

## Test Decision Framework

### When to Use Unit Tests

✅ **Use helm-unittest for:**
- Template rendering logic
- Conditional resource creation
- Helper template functions
- Values validation
- Default value checks
- Multiple environment configurations

**Example:**
```yaml
# Test: Deployment should not set replicas when autoscaling is enabled
- it: should not set replicas when autoscaling is enabled
  set:
    autoscaling.enabled: true
  asserts:
    - isNull:
        path: spec.replicas
```

### When to Use Integration Tests

✅ **Use helm test for:**
- Service connectivity
- API endpoint availability
- Database connections
- External dependencies
- SSL/TLS validation
- Authentication flows

**Example:**
```yaml
# Test: API health endpoint is accessible
apiVersion: v1
kind: Pod
metadata:
  name: test-connection
  annotations:
    helm.sh/hook: test
spec:
  containers:
    - name: test
      command: ["curl", "--fail", "http://service/health"]
```

### Decision Matrix

| Test Type | Speed | Coverage | When to Use |
|-----------|-------|----------|-------------|
| **Lint** | Fast | Syntax | Every commit |
| **Unit** | Fast | Logic | Every commit |
| **Integration** | Medium | Runtime | PR merge |
| **E2E** | Slow | Full stack | Release |

## Testing Workflow

### Development Workflow

```bash
# 1. Make changes to templates
vim templates/deployment.yaml

# 2. Lint changes
helm lint .

# 3. Run unit tests
helm unittest .

# 4. Render template to verify
helm template task-api . --show-only templates/deployment.yaml

# 5. Test in dev environment
helm upgrade task-api . -f values-dev.yaml -n dev

# 6. Run integration tests
helm test task-api -n dev
```

### CI/CD Workflow

```yaml
# .github/workflows/test.yml
name: Test Helm Chart

on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: azure/setup-helm@v3
      - run: helm lint .
      - run: helm lint . -f values-dev.yaml
      - run: helm lint . -f values-prod.yaml

  unittest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: azure/setup-helm@v3
      - run: helm plugin install https://github.com/helm-unittest/helm-unittest
      - run: helm unittest .

  integration:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: helm/kind-action@v1.5.0
      - run: helm install task-api . -f values-dev.yaml --wait
      - run: helm test task-api --logs
```

## Validation Patterns

### Pattern 1: Multi-Environment Validation

```bash
# Test all environments
for env in dev staging prod; do
  echo "Testing ${env} environment..."
  helm lint . -f values-${env}.yaml || exit 1
  helm template task-api . -f values-${env}.yaml > /dev/null || exit 1
done
```

### Pattern 2: Security Validation

```bash
# Check security contexts in prod
helm template task-api . -f values-prod.yaml | \
  grep -A 10 "securityContext:" | \
  grep "runAsNonRoot: true"

# Verify no privileged containers
helm template task-api . -f values-prod.yaml | \
  grep "privileged: true" && exit 1 || echo "✓ No privileged containers"
```

### Pattern 3: Resource Validation

```bash
# Check resource limits are set
helm template task-api . -f values-prod.yaml | \
  grep -A 5 "resources:" | \
  grep "limits:"

# Verify autoscaling in prod
helm template task-api . -f values-prod.yaml | \
  grep "kind: HorizontalPodAutoscaler"
```

### Pattern 4: Dependency Validation

```bash
# Check PostgreSQL is configured
helm template task-api . -f values-dev.yaml | \
  grep "postgresql.enabled"

# Verify Redis connection
helm template task-api . -f values-dev.yaml | \
  grep "redis-master"
```

## Troubleshooting Tests

### Unit Test Failures

```bash
# Run with verbose output
helm unittest -v .

# Debug specific test
helm unittest -f tests/deployment_test.yaml -v .

# Check rendered output
helm template task-api . --debug 2>&1 | grep -A 20 "deployment.yaml"
```

### Integration Test Failures

```bash
# Check test pod status
kubectl get pods -l helm.sh/hook=test

# View test logs
kubectl logs task-api-test-connection

# Describe test pod
kubectl describe pod task-api-test-connection

# Debug in test pod
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -- sh
# Inside pod:
curl http://task-api:8000/health
```

### Common Issues

**Issue 1: Test pod fails immediately**
```bash
# Check test pod events
kubectl describe pod task-api-test-connection

# Common causes:
# - Wrong service name
# - Service not ready
# - Wrong port
```

**Issue 2: Unit test assertion fails**
```bash
# Check expected vs actual
helm template task-api . --show-only templates/deployment.yaml | \
  yq '.spec.replicas'

# Update test assertion to match
```

**Issue 3: Schema validation fails**
```bash
# Check schema errors
helm lint . -f values-prod.yaml

# Common causes:
# - Wrong value type (string vs integer)
# - Missing required field
# - Value out of range
```

## Quick Commands

| Command | Purpose |
|---------|---------|
| `helm lint .` | Validate syntax |
| `helm template task-api .` | Render templates |
| `helm unittest .` | Run unit tests |
| `helm install --dry-run` | Simulate install |
| `helm test task-api` | Run integration tests |
| `kubectl get pods` | Check deployment |
| `kubectl logs -l app=task-api` | View logs |

## Test Coverage Summary

- ✅ **72 unit tests** covering all templates
- ✅ **Schema validation** for values
- ✅ **Integration tests** for runtime validation
- ✅ **Hook tests** for lifecycle management
- ✅ **Security tests** for production hardening
- ✅ **Multi-environment tests** for dev/staging/prod

## Best Practices

1. **Run tests locally** before pushing
2. **Test all environments** (dev, staging, prod)
3. **Use descriptive test names** for clarity
4. **Keep tests maintainable** - one file per template
5. **Test edge cases** - not just happy paths
6. **Integrate into CI/CD** for automated validation
7. **Document test failures** for debugging
8. **Update tests** when changing templates

## Further Reading

- Complete reference: [.claude/skills/helm-chart-skill/references/TESTING.md](../.claude/skills/helm-chart-skill/references/TESTING.md)
- Helm-unittest docs: https://github.com/helm-unittest/helm-unittest
- Helm testing: https://helm.sh/docs/topics/chart_tests/
