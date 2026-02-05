#!/bin/bash
#
# Kubernetes Deployment Validator
#
# Validates that a deployment is ready and healthy.
# Checks pods, services, and optional ingress.
#
# Usage:
#   ./validate-deployment.sh <deployment-name> [namespace]
#   ./validate-deployment.sh myapp production
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Arguments
DEPLOYMENT_NAME="${1:?Usage: $0 <deployment-name> [namespace]}"
NAMESPACE="${2:-default}"

echo "=========================================="
echo "Validating deployment: $DEPLOYMENT_NAME"
echo "Namespace: $NAMESPACE"
echo "=========================================="
echo ""

ERRORS=0

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}ERROR: kubectl is not installed or not in PATH${NC}"
    exit 1
fi

# Check if namespace exists
if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
    echo -e "${RED}ERROR: Namespace '$NAMESPACE' does not exist${NC}"
    exit 1
fi

# Check deployment exists
echo "Checking deployment..."
if kubectl get deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE" &> /dev/null; then
    echo -e "${GREEN}[OK] Deployment exists${NC}"
else
    echo -e "${RED}[FAIL] Deployment '$DEPLOYMENT_NAME' not found${NC}"
    exit 1
fi

# Check deployment status
echo ""
echo "Checking deployment status..."
READY=$(kubectl get deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")
DESIRED=$(kubectl get deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE" -o jsonpath='{.spec.replicas}')
READY=${READY:-0}

if [ "$READY" -eq "$DESIRED" ] && [ "$DESIRED" -gt 0 ]; then
    echo -e "${GREEN}[OK] All replicas ready: $READY/$DESIRED${NC}"
else
    echo -e "${RED}[FAIL] Replicas not ready: $READY/$DESIRED${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Check pods
echo ""
echo "Checking pods..."
PODS=$(kubectl get pods -l "app=$DEPLOYMENT_NAME" -n "$NAMESPACE" -o jsonpath='{.items[*].metadata.name}')
if [ -z "$PODS" ]; then
    echo -e "${YELLOW}[WARN] No pods found with label app=$DEPLOYMENT_NAME${NC}"
    ERRORS=$((ERRORS + 1))
else
    for POD in $PODS; do
        STATUS=$(kubectl get pod "$POD" -n "$NAMESPACE" -o jsonpath='{.status.phase}')
        READY=$(kubectl get pod "$POD" -n "$NAMESPACE" -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}')

        if [ "$STATUS" = "Running" ] && [ "$READY" = "True" ]; then
            echo -e "${GREEN}[OK] Pod $POD: Running and Ready${NC}"
        else
            echo -e "${RED}[FAIL] Pod $POD: Status=$STATUS, Ready=$READY${NC}"
            ERRORS=$((ERRORS + 1))
        fi
    done
fi

# Check service
echo ""
echo "Checking service..."
if kubectl get service "$DEPLOYMENT_NAME" -n "$NAMESPACE" &> /dev/null; then
    ENDPOINTS=$(kubectl get endpoints "$DEPLOYMENT_NAME" -n "$NAMESPACE" -o jsonpath='{.subsets[*].addresses[*].ip}')
    if [ -n "$ENDPOINTS" ]; then
        echo -e "${GREEN}[OK] Service exists with endpoints${NC}"
    else
        echo -e "${YELLOW}[WARN] Service exists but has no endpoints${NC}"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo -e "${YELLOW}[WARN] No service named '$DEPLOYMENT_NAME' found${NC}"
fi

# Check ingress (optional)
echo ""
echo "Checking ingress..."
if kubectl get ingress "$DEPLOYMENT_NAME" -n "$NAMESPACE" &> /dev/null; then
    ADDRESS=$(kubectl get ingress "$DEPLOYMENT_NAME" -n "$NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}{.status.loadBalancer.ingress[0].hostname}')
    if [ -n "$ADDRESS" ]; then
        echo -e "${GREEN}[OK] Ingress exists with address: $ADDRESS${NC}"
    else
        echo -e "${YELLOW}[WARN] Ingress exists but has no address yet${NC}"
    fi
else
    echo -e "${YELLOW}[INFO] No ingress named '$DEPLOYMENT_NAME' found (optional)${NC}"
fi

# Check HPA (optional)
echo ""
echo "Checking HPA..."
if kubectl get hpa "${DEPLOYMENT_NAME}-hpa" -n "$NAMESPACE" &> /dev/null; then
    CURRENT=$(kubectl get hpa "${DEPLOYMENT_NAME}-hpa" -n "$NAMESPACE" -o jsonpath='{.status.currentReplicas}')
    MIN=$(kubectl get hpa "${DEPLOYMENT_NAME}-hpa" -n "$NAMESPACE" -o jsonpath='{.spec.minReplicas}')
    MAX=$(kubectl get hpa "${DEPLOYMENT_NAME}-hpa" -n "$NAMESPACE" -o jsonpath='{.spec.maxReplicas}')
    echo -e "${GREEN}[OK] HPA exists: current=$CURRENT, min=$MIN, max=$MAX${NC}"
elif kubectl get hpa "$DEPLOYMENT_NAME" -n "$NAMESPACE" &> /dev/null; then
    echo -e "${GREEN}[OK] HPA exists${NC}"
else
    echo -e "${YELLOW}[INFO] No HPA found (optional)${NC}"
fi

# Check resource requests/limits
echo ""
echo "Checking resource configuration..."
HAS_REQUESTS=$(kubectl get deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE" -o jsonpath='{.spec.template.spec.containers[0].resources.requests}')
HAS_LIMITS=$(kubectl get deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE" -o jsonpath='{.spec.template.spec.containers[0].resources.limits}')

if [ -n "$HAS_REQUESTS" ]; then
    echo -e "${GREEN}[OK] Resource requests defined${NC}"
else
    echo -e "${YELLOW}[WARN] No resource requests defined (recommended for production)${NC}"
fi

if [ -n "$HAS_LIMITS" ]; then
    echo -e "${GREEN}[OK] Resource limits defined${NC}"
else
    echo -e "${YELLOW}[WARN] No resource limits defined (recommended for production)${NC}"
fi

# Check probes
echo ""
echo "Checking health probes..."
HAS_LIVENESS=$(kubectl get deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE" -o jsonpath='{.spec.template.spec.containers[0].livenessProbe}')
HAS_READINESS=$(kubectl get deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE" -o jsonpath='{.spec.template.spec.containers[0].readinessProbe}')

if [ -n "$HAS_LIVENESS" ]; then
    echo -e "${GREEN}[OK] Liveness probe configured${NC}"
else
    echo -e "${YELLOW}[WARN] No liveness probe configured${NC}"
fi

if [ -n "$HAS_READINESS" ]; then
    echo -e "${GREEN}[OK] Readiness probe configured${NC}"
else
    echo -e "${YELLOW}[WARN] No readiness probe configured${NC}"
fi

# Summary
echo ""
echo "=========================================="
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}Validation PASSED${NC}"
    exit 0
else
    echo -e "${RED}Validation FAILED with $ERRORS error(s)${NC}"
    exit 1
fi
