#!/bin/bash
#
# Kubernetes Production Readiness Validator
#
# Validates Kubernetes manifests against production readiness criteria.
# Checks security, resource management, availability, and best practices.
#
# Usage:
#   ./production-readiness-validator.sh <manifest-file>
#   ./production-readiness-validator.sh deployment.yaml
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

MANIFEST_FILE="${1:?Usage: $0 <manifest-file>}"

echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}Kubernetes Production Readiness Validator${NC}"
echo -e "${BLUE}==========================================${NC}"
echo ""

# Initialize counters
CRITICAL_ISSUES=0
HIGH_ISSUES=0
MEDIUM_ISSUES=0
LOW_ISSUES=0

# Temporary file for processed manifest
TEMP_MANIFEST=$(mktemp)

# Process multi-document manifests
yq eval-all 'select(tag == "!!map")' "$MANIFEST_FILE" > "$TEMP_MANIFEST"

echo "Analyzing manifest: $MANIFEST_FILE"
echo ""

# Function to report issues
report_issue() {
    local severity=$1
    local message=$2
    
    case $severity in
        "CRITICAL")
            echo -e "${RED}[CRITICAL] $message${NC}"
            ((CRITICAL_ISSUES++))
            ;;
        "HIGH")
            echo -e "${RED}[HIGH] $message${NC}"
            ((HIGH_ISSUES++))
            ;;
        "MEDIUM")
            echo -e "${YELLOW}[MEDIUM] $message${NC}"
            ((MEDIUM_ISSUES++))
            ;;
        "LOW")
            echo -e "${YELLOW}[LOW] $message${NC}"
            ((LOW_ISSUES++))
            ;;
    esac
}

# Check if yq is available
if ! command -v yq &> /dev/null; then
    echo -e "${RED}ERROR: yq is not installed. Please install yq to run this validator.${NC}"
    exit 1
fi

# Security Checks
echo -e "${BLUE}[SECURITY] Running security checks...${NC}"

# Check for runAsNonRoot
if yq eval 'select(.kind == "Deployment" or .kind == "StatefulSet" or .kind == "DaemonSet") | 
           (.spec.template.spec.securityContext.runAsNonRoot // false)' "$TEMP_MANIFEST" | grep -q "false\|null"; then
    report_issue "HIGH" "Container does not run as non-root user (runAsNonRoot: true recommended)"
fi

# Check for readOnlyRootFilesystem
if yq eval 'select(.kind == "Deployment" or .kind == "StatefulSet" or .kind == "DaemonSet") | 
           (.spec.template.spec.containers[] | .securityContext.readOnlyRootFilesystem // false)' "$TEMP_MANIFEST" | grep -q "false\|null"; then
    report_issue "MEDIUM" "Container root filesystem is not read-only (readOnlyRootFilesystem: true recommended)"
fi

# Check for allowPrivilegeEscalation
if yq eval 'select(.kind == "Deployment" or .kind == "StatefulSet" or .kind == "DaemonSet") | 
           (.spec.template.spec.containers[] | .securityContext.allowPrivilegeEscalation // true)' "$TEMP_MANIFEST" | grep -q "true\|null"; then
    report_issue "HIGH" "Container allows privilege escalation (allowPrivilegeEscalation: false required)"
fi

# Check for capabilities drop
caps_check=$(yq eval 'select(.kind == "Deployment" or .kind == "StatefulSet" or .kind == "DaemonSet") | 
                     .spec.template.spec.containers[] | 
                     .securityContext.capabilities.drop // [] | length' "$TEMP_MANIFEST")
if [[ $caps_check -eq 0 ]]; then
    report_issue "MEDIUM" "Container does not drop capabilities (capabilities.drop: ['ALL'] recommended)"
fi

# Resource Management Checks
echo ""
echo -e "${BLUE}[RESOURCES] Running resource management checks...${NC}"

# Check for resource requests
requests_cpu=$(yq eval 'select(.kind == "Deployment" or .kind == "StatefulSet" or .kind == "DaemonSet") | 
                      .spec.template.spec.containers[] | 
                      .resources.requests.cpu // ""' "$TEMP_MANIFEST")
requests_memory=$(yq eval 'select(.kind == "Deployment" or .kind == "StatefulSet" or .kind == "DaemonSet") | 
                         .spec.template.spec.containers[] | 
                         .resources.requests.memory // ""' "$TEMP_MANIFEST")

if [[ -z "$requests_cpu" || "$requests_cpu" == "null" ]]; then
    report_issue "HIGH" "CPU requests not specified (required for scheduling and QoS)"
fi

if [[ -z "$requests_memory" || "$requests_memory" == "null" ]]; then
    report_issue "HIGH" "Memory requests not specified (required for scheduling and QoS)"
fi

# Check for resource limits
limits_cpu=$(yq eval 'select(.kind == "Deployment" or .kind == "StatefulSet" or .kind == "DaemonSet") | 
                     .spec.template.spec.containers[] | 
                     .resources.limits.cpu // ""' "$TEMP_MANIFEST")
limits_memory=$(yq eval 'select(.kind == "Deployment" or .kind == "StatefulSet" or .kind == "DaemonSet") | 
                      .spec.template.spec.containers[] | 
                      .resources.limits.memory // ""' "$TEMP_MANIFEST")

if [[ -z "$limits_cpu" || "$limits_cpu" == "null" ]]; then
    report_issue "HIGH" "CPU limits not specified (prevents resource exhaustion)"
fi

if [[ -z "$limits_memory" || "$limits_memory" == "null" ]]; then
    report_issue "HIGH" "Memory limits not specified (prevents OOM issues)"
fi

# Availability Checks
echo ""
echo -e "${BLUE}[AVAILABILITY] Running availability checks...${NC}"

# Check for replica count
replicas=$(yq eval 'select(.kind == "Deployment" or .kind == "StatefulSet") | .spec.replicas // 1' "$TEMP_MANIFEST")
if [[ "$replicas" -lt 2 ]]; then
    report_issue "MEDIUM" "Single replica deployment (consider 2+ for high availability)"
fi

# Check for health probes
liveness_probe=$(yq eval 'select(.kind == "Deployment" or .kind == "StatefulSet" or .kind == "DaemonSet") | 
                       .spec.template.spec.containers[] | 
                       .livenessProbe // null' "$TEMP_MANIFEST")
readiness_probe=$(yq eval 'select(.kind == "Deployment" or .kind == "StatefulSet" or .kind == "DaemonSet") | 
                        .spec.template.spec.containers[] | 
                        .readinessProbe // null' "$TEMP_MANIFEST")

if [[ -z "$liveness_probe" || "$liveness_probe" == "null" ]]; then
    report_issue "HIGH" "Liveness probe not configured (critical for self-healing)"
fi

if [[ -z "$readiness_probe" || "$readiness_probe" == "null" ]]; then
    report_issue "HIGH" "Readiness probe not configured (critical for traffic routing)"
fi

# Configuration Checks
echo ""
echo -e "${BLUE}[CONFIGURATION] Running configuration checks...${NC}"

# Check for secrets vs configmaps
has_secrets=$(yq eval 'select(.kind == "Secret") | has("data")' "$TEMP_MANIFEST")
has_configmaps=$(yq eval 'select(.kind == "ConfigMap") | has("data")' "$TEMP_MANIFEST")

if [[ "$has_configmaps" == "true" ]] && [[ -z "$has_secrets" || "$has_secrets" == "false" ]]; then
    # Check if ConfigMap contains sensitive-looking data
    sensitive_keys=$(yq eval 'select(.kind == "ConfigMap") | .data | to_entries[] | select(.key | test("(password|token|key|secret|auth|cert)"i)) | .key' "$TEMP_MANIFEST" 2>/dev/null || true)
    if [[ -n "$sensitive_keys" ]]; then
        report_issue "CRITICAL" "ConfigMap contains sensitive data (should use Secret instead): $sensitive_keys"
    fi
fi

# Best Practices Checks
echo ""
echo -e "${BLUE}[BEST PRACTICES] Running best practices checks...${NC}"

# Check for image pull policy
pull_policy=$(yq eval 'select(.kind == "Deployment" or .kind == "StatefulSet" or .kind == "DaemonSet") | 
                     .spec.template.spec.containers[] | 
                     .imagePullPolicy // ""' "$TEMP_MANIFEST")

if [[ -z "$pull_policy" || "$pull_policy" == "null" ]]; then
    report_issue "LOW" "Image pull policy not specified (consider Always, IfNotPresent, or Never)"
elif [[ "$pull_policy" == "Always" ]]; then
    report_issue "LOW" "Using Always pull policy (may cause issues with pinned image tags)"
fi

# Check for image tags (not using 'latest')
images=$(yq eval 'select(.kind == "Deployment" or .kind == "StatefulSet" or .kind == "DaemonSet") | 
                 .spec.template.spec.containers[].image' "$TEMP_MANIFEST")

for image in $images; do
    if [[ "$image" =~ :latest$ ]]; then
        report_issue "MEDIUM" "Using 'latest' tag for image: $image (use specific version tags for reproducibility)"
    fi
done

# Check for node selectors/affinity
has_affinity=$(yq eval 'select(.kind == "Deployment" or .kind == "StatefulSet" or .kind == "DaemonSet") | 
                      has("spec.template.spec.affinity")' "$TEMP_MANIFEST")
has_node_selector=$(yq eval 'select(.kind == "Deployment" or .kind == "StatefulSet" or .kind == "DaemonSet") | 
                           has("spec.template.spec.nodeSelector")' "$TEMP_MANIFEST")

if [[ "$has_affinity" == "false" && "$has_node_selector" == "false" ]]; then
    report_issue "LOW" "No node affinity/selector configured (consider for workload placement)"
fi

# Summary
echo ""
echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}VALIDATION SUMMARY${NC}"
echo -e "${BLUE}==========================================${NC}"

TOTAL_ISSUES=$((CRITICAL_ISSUES + HIGH_ISSUES + MEDIUM_ISSUES + LOW_ISSUES))

echo "Critical Issues: $CRITICAL_ISSUES"
echo "High Issues: $HIGH_ISSUES" 
echo "Medium Issues: $MEDIUM_ISSUES"
echo "Low Issues: $LOW_ISSUES"
echo "Total Issues: $TOTAL_ISSUES"

echo ""
if [[ $TOTAL_ISSUES -eq 0 ]]; then
    echo -e "${GREEN}✓ Manifest appears production-ready!${NC}"
    SCORE=100
elif [[ $CRITICAL_ISSUES -gt 0 ]]; then
    echo -e "${RED}✗ Manifest has critical issues and is NOT production-ready${NC}"
    SCORE=20
elif [[ $HIGH_ISSUES -gt 0 ]]; then
    echo -e "${RED}✗ Manifest has high severity issues and is NOT production-ready${NC}"
    SCORE=40
elif [[ $MEDIUM_ISSUES -gt 0 ]]; then
    echo -e "${YELLOW}⚠ Manifest has medium severity issues - review before production${NC}"
    SCORE=70
else
    echo -e "${GREEN}✓ Manifest has only low severity issues - mostly production-ready${NC}"
    SCORE=90
fi

echo ""
echo "Production Readiness Score: $SCORE/100"

# Cleanup
rm "$TEMP_MANIFEST"

# Exit with error if critical or high issues found
if [[ $CRITICAL_ISSUES -gt 0 || $HIGH_ISSUES -gt 0 ]]; then
    exit 1
fi