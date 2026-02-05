#!/bin/bash

# GKE Cost Analysis and Optimization Script
# Analyzes current cluster configuration and suggests cost optimizations

set -e

# Default values
DEFAULT_CLUSTER_NAME=""
DEFAULT_PROJECT_ID=$(gcloud config get-value project 2>/dev/null || echo "")

# Display usage information
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  -n, --name NAME         Cluster name (default: first available cluster)"
    echo "  -p, --project PROJECT   Project ID (default: current gcloud project)"
    echo "  --analyze-only          Only analyze without applying changes"
    echo "  --suggest-optimizations Suggest optimizations only"
    echo "  --apply-cost-savings    Apply cost-saving changes (use with caution)"
    echo "  --help                  Show this help message"
    exit 1
}

# Parse command line arguments
CLUSTER_NAME=$DEFAULT_CLUSTER_NAME
PROJECT_ID=$DEFAULT_PROJECT_ID
ANALYZE_ONLY=true
SUGGEST_OPTIMIZATIONS=false
APPLY_SAVINGS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -n|--name)
            CLUSTER_NAME="$2"
            shift 2
            ;;
        -p|--project)
            PROJECT_ID="$2"
            shift 2
            ;;
        --analyze-only)
            ANALYZE_ONLY=true
            shift
            ;;
        --suggest-optimizations)
            SUGGEST_OPTIMIZATIONS=true
            ANALYZE_ONLY=true
            shift
            ;;
        --apply-cost-savings)
            APPLY_SAVINGS=true
            ANALYZE_ONLY=false
            shift
            ;;
        --help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Check if gcloud is installed and authenticated
if ! command -v gcloud &> /dev/null; then
    echo "Error: gcloud CLI is not installed"
    exit 1
fi

if [[ -z "$PROJECT_ID" ]]; then
    echo "Error: Project ID is required"
    usage
fi

# If cluster name not specified, get the first available cluster
if [[ -z "$CLUSTER_NAME" ]]; then
    CLUSTER_NAME=$(gcloud container clusters list --project="$PROJECT_ID" --format="value(name)" | head -n1)
    if [[ -z "$CLUSTER_NAME" ]]; then
        echo "Error: No clusters found in project $PROJECT_ID"
        exit 1
    fi
    echo "Using cluster: $CLUSTER_NAME (automatically detected)"
fi

echo "Analyzing cluster: $CLUSTER_NAME in project: $PROJECT_ID"

# Get cluster details
echo "Fetching cluster details..."
CLUSTER_INFO=$(gcloud container clusters describe "$CLUSTER_NAME" --project="$PROJECT_ID" --format="json")

# Extract relevant information
ZONE=$(echo "$CLUSTER_INFO" | jq -r '.zone')
REGION=$(echo "$CLUSTER_INFO" | jq -r '.location')
CURRENT_NODE_COUNT=$(echo "$CLUSTER_INFO" | jq -r '.currentNodeCount')
NODE_CONFIG=$(echo "$CLUSTER_INFO" | jq -r '.nodeConfig')
MACHINE_TYPE=$(echo "$CLUSTER_INFO" | jq -r '.nodeConfig.machineType')
PREEMPTIBLE=$(echo "$CLUSTER_INFO" | jq -r '.nodeConfig.preemptible')
AUTO_UPGRADE=$(echo "$CLUSTER_INFO" | jq -r '.nodePools[0].management.autoUpgrade')

echo "Zone: $ZONE"
echo "Region: $REGION"
echo "Current Node Count: $CURRENT_NODE_COUNT"
echo "Machine Type: $MACHINE_TYPE"
echo "Preemptible: $PREEMPTIBLE"
echo "Auto Upgrade: $AUTO_UPGRADE"

# Analyze resource usage (this would normally come from metrics)
echo ""
echo "=== Current Configuration Analysis ==="

# Check for non-preemptible nodes (potential cost saving)
if [[ "$PREEMPTIBLE" == "false" ]]; then
    echo "⚠️  Potential savings: Consider using preemptible nodes for non-critical workloads (up to 91% savings)"
    if [[ "$APPLY_SAVINGS" == true ]]; then
        echo "Applying: Adding a preemptible node pool for non-critical workloads..."
        NEW_POOL_NAME="${CLUSTER_NAME}-spot-pool"
        gcloud container node-pools create "$NEW_POOL_NAME" \
          --cluster="$CLUSTER_NAME" \
          --zone="$ZONE" \
          --num-nodes=1 \
          --machine-type="$MACHINE_TYPE" \
          --preemptible \
          --node-taints=spot-instance=true:NoSchedule
        echo "Created preemptible node pool: $NEW_POOL_NAME"
    fi
fi

# Check machine type for optimization opportunities
case $MACHINE_TYPE in
    n1-*)
        echo "💡 Recommendation: Consider migrating to newer machine types (n2, n2d) for better price/performance"
        ;;
    e2-*)
        echo "✅ Good choice: e2 machine types offer excellent price/performance ratio"
        ;;
    c2-*|c2d-*)
        echo "✅ Good choice: Optimized for compute-intensive workloads"
        ;;
    m1-*|m2-*)
        echo "✅ Good choice: Optimized for memory-intensive workloads"
        ;;
    *)
        echo "💡 Consideration: Evaluate if e2 series would meet your requirements at lower cost"
        ;;
esac

# Get node pool information
echo ""
echo "=== Node Pool Analysis ==="
NODE_POOLS=$(gcloud container node-pools list --cluster="$CLUSTER_NAME" --zone="$ZONE" --project="$PROJECT_ID" --format="json")

NUM_POOLS=$(echo "$NODE_POOLS" | jq -r 'length')
echo "Number of node pools: $NUM_POOLS"

for i in $(seq 0 $((NUM_POOLS - 1))); do
    POOL_NAME=$(echo "$NODE_POOLS" | jq -r ".[$i].name")
    POOL_MACHINE_TYPE=$(echo "$NODE_POOLS" | jq -r ".[$i].config.machineType")
    POOL_NODE_COUNT=$(echo "$NODE_POOLS" | jq -r ".[$i].initialNodeCount")
    POOL_PREEMPTIBLE=$(echo "$NODE_POOLS" | jq -r ".[$i].config.preemptible")
    POOL_AUTOSCALING=$(echo "$NODE_POOLS" | jq -r ".[$i].autoscaling.enabled")
    POOL_MIN_NODES=$(echo "$NODE_POOLS" | jq -r ".[$i].autoscaling.minNodeCount // 0")
    POOL_MAX_NODES=$(echo "$NODE_POOLS" | jq -r ".[$i].autoscaling.maxNodeCount // 0")

    echo "Pool: $POOL_NAME"
    echo "  Machine Type: $POOL_MACHINE_TYPE"
    echo "  Initial Node Count: $POOL_NODE_COUNT"
    echo "  Preemptible: $POOL_PREEMPTIBLE"
    echo "  Autoscaling: $POOL_AUTOSCALING"
    if [[ "$POOL_AUTOSCALING" == "true" ]]; then
        echo "  Min Nodes: $POOL_MIN_NODES"
        echo "  Max Nodes: $POOL_MAX_NODES"
    fi

    # Check autoscaling configuration
    if [[ "$POOL_AUTOSCALING" == "false" ]]; then
        echo "  ⚠️  Potential savings: Enable autoscaling to dynamically adjust node count"
    fi
    echo ""
done

# Check for regional vs zonal cluster cost implications
if [[ "$CLUSTER_NAME" == *"regional"* || $(echo "$CLUSTER_INFO" | jq -r '.location') == *"-*"-* ]]; then
    echo "💡 Note: This appears to be a regional cluster (higher availability, higher cost)"
else
    echo "💡 Consideration: Regional clusters provide higher availability but cost more"
fi

# Provide cost estimation
echo "=== Cost Optimization Recommendations ==="
echo "1. Enable cluster autoscaling for efficient resource utilization"
echo "2. Use preemptible nodes for fault-tolerant workloads"
echo "3. Consider right-sizing machine types based on actual resource usage"
echo "4. Implement resource quotas and requests/limits to prevent overconsumption"
echo "5. Use VPA (Vertical Pod Autoscaler) to optimize resource allocation"

# Check if we should suggest using kubectl for resource analysis
echo ""
echo "To further analyze resource usage, consider running:"
echo "kubectl top nodes"
echo "kubectl top pods"
echo "kubectl describe nodes"
echo ""
echo "This will help identify potential over-provisioning."

if [[ "$ANALYZE_ONLY" == true ]]; then
    echo "Analysis complete. Run with --apply-cost-savings to implement recommendations."
fi