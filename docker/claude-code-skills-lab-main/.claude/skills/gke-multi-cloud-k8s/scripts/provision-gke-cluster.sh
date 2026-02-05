#!/bin/bash

# GKE Cluster Provisioning Script
# Implements the "provision" phase of the provision → connect → deploy pattern

set -e  # Exit on any error

# Default values
DEFAULT_CLUSTER_NAME="my-gke-cluster"
DEFAULT_ZONE="us-central1-a"
DEFAULT_NODE_COUNT=3
DEFAULT_MACHINE_TYPE="e2-medium"
DEFAULT_MIN_NODES=1
DEFAULT_MAX_NODES=10
DEFAULT_DISK_SIZE="100GB"

# Display usage information
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  -n, --name NAME           Cluster name (default: $DEFAULT_CLUSTER_NAME)"
    echo "  -z, --zone ZONE           Compute zone (default: $DEFAULT_ZONE)"
    echo "  -c, --node-count COUNT    Number of nodes (default: $DEFAULT_NODE_COUNT)"
    echo "  -m, --machine-type TYPE   Machine type (default: $DEFAULT_MACHINE_TYPE)"
    echo "  --min-nodes COUNT         Minimum nodes for autoscaling (default: $DEFAULT_MIN_NODES)"
    echo "  --max-nodes COUNT         Maximum nodes for autoscaling (default: $DEFAULT_MAX_NODES)"
    echo "  --disk-size SIZE          Disk size per node (default: $DEFAULT_DISK_SIZE)"
    echo "  --enable-private          Enable private cluster"
    echo "  --enable-autopilot        Use Autopilot mode"
    echo "  --help                    Show this help message"
    exit 1
}

# Parse command line arguments
CLUSTER_NAME=$DEFAULT_CLUSTER_NAME
ZONE=$DEFAULT_ZONE
NODE_COUNT=$DEFAULT_NODE_COUNT
MACHINE_TYPE=$DEFAULT_MACHINE_TYPE
MIN_NODES=$DEFAULT_MIN_NODES
MAX_NODES=$DEFAULT_MAX_NODES
DISK_SIZE=$DEFAULT_DISK_SIZE
ENABLE_PRIVATE=false
ENABLE_AUTOPILOT=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -n|--name)
            CLUSTER_NAME="$2"
            shift 2
            ;;
        -z|--zone)
            ZONE="$2"
            shift 2
            ;;
        -c|--node-count)
            NODE_COUNT="$2"
            shift 2
            ;;
        -m|--machine-type)
            MACHINE_TYPE="$2"
            shift 2
            ;;
        --min-nodes)
            MIN_NODES="$2"
            shift 2
            ;;
        --max-nodes)
            MAX_NODES="$2"
            shift 2
            ;;
        --disk-size)
            DISK_SIZE="$2"
            shift 2
            ;;
        --enable-private)
            ENABLE_PRIVATE=true
            shift
            ;;
        --enable-autopilot)
            ENABLE_AUTOPILOT=true
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

# Validate inputs
if [[ -z "$CLUSTER_NAME" || -z "$ZONE" ]]; then
    echo "Error: Cluster name and zone are required"
    usage
fi

# Check if gcloud is installed and authenticated
if ! command -v gcloud &> /dev/null; then
    echo "Error: gcloud CLI is not installed"
    exit 1
fi

if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "@"; then
    echo "Error: Not authenticated with gcloud. Please run 'gcloud auth login'"
    exit 1
fi

echo "Starting GKE cluster provisioning..."
echo "Cluster Name: $CLUSTER_NAME"
echo "Zone: $ZONE"
echo "Node Count: $NODE_COUNT"
echo "Machine Type: $MACHINE_TYPE"
echo "Min Nodes: $MIN_NODES"
echo "Max Nodes: $MAX_NODES"
echo "Disk Size: $DISK_SIZE"

# Build the gcloud command with appropriate flags
CMD="gcloud container clusters create $CLUSTER_NAME \
  --zone=$ZONE \
  --num-nodes=$NODE_COUNT \
  --machine-type=$MACHINE_TYPE \
  --disk-size=$DISK_SIZE \
  --enable-autoscaling \
  --min-nodes=$MIN_NODES \
  --max-nodes=$MAX_NODES"

if [[ "$ENABLE_PRIVATE" == true ]]; then
    CMD="$CMD \
      --enable-private-nodes \
      --enable-private-endpoint \
      --master-ipv4-cidr-block=172.16.0.0/28"
fi

if [[ "$ENABLE_AUTOPILOT" == true ]]; then
    # For autopilot, we need different flags
    CMD="gcloud container clusters create $CLUSTER_NAME \
      --zone=$ZONE \
      --enable-autopilot \
      --region=${ZONE%-*}"  # Convert zone to region
fi

echo "Executing command: $CMD"
eval $CMD

echo "Cluster $CLUSTER_NAME has been provisioned successfully!"

# Optionally, get credentials for kubectl
echo "Getting cluster credentials for kubectl..."
gcloud container clusters get-credentials "$CLUSTER_NAME" --zone="$ZONE"

echo "You can now connect to your cluster using kubectl."
echo "Next step: Deploy your applications using 'kubectl apply -f <manifest-file>'"