# Dapr Billing Integration Example

This example demonstrates how to integrate a billing service with a todo-api using Dapr service invocation.

## Architecture

1. **todo-api**: Main application that manages tasks
2. **billing-service**: Service that calculates and processes billing when tasks are completed
3. **Dapr**: Provides service invocation between the two services

## Files Included

### todo-api/
- `main.py`: Updated to invoke billing service when tasks are marked complete
- `models.py`: Updated with billing-related fields
- `requirements.txt`: Updated with Dapr dependencies
- `k8s/todo-api-deployment.yaml`: Kubernetes deployment with Dapr annotations

### billing-service/
- `src/app.py`: Billing service implementation
- `requirements.txt`: Dependencies for billing service
- `components/billing-state.yaml`: Dapr state store component
- `k8s/billing-service-deployment.yaml`: Kubernetes deployment with Dapr annotations

## How It Works

1. When a task is updated to "complete" status in the todo-api, a background task invokes the billing service
2. The todo-api uses Dapr's service invocation to call the billing-service
3. The billing service receives the webhook and calculates billing based on task properties
4. Both services have proper Dapr annotations for service discovery and communication

## Deployment

To deploy both services to Kubernetes with Dapr:

```bash
# Install Dapr to your cluster (if not already installed)
helm repo add dapr https://dapr.github.io/helm-charts/
helm repo update
kubectl create namespace dapr-system
helm install dapr dapr/dapr --namespace dapr-system --wait

# Deploy the billing service
kubectl apply -f billing-service/k8s/billing-service-deployment.yaml

# Deploy the todo-api
kubectl apply -f task-api/k8s/todo-api-deployment.yaml

# Check deployment status
kubectl get pods
dapr status -k
```

## Service Invocation Details

The todo-api uses the following pattern to invoke the billing service:

```python
with DaprClient() as client:
    response = client.invoke_method(
        app_id='billing-service',  # Matches dapr.io/app-id annotation
        method_name='webhook/task-completed',
        data=billing_data,
        http_verb='POST',
        content_type='application/json'
    )
```

## Error Handling

The implementation includes proper error handling for:
- `ERR_DIRECT_INVOKE` - When billing-service is unreachable
- Connection refused errors
- General exceptions during service invocation

## Required Dapr Annotations

Both services use these essential annotations:
- `dapr.io/enabled: "true"` - Enables Dapr sidecar injection
- `dapr.io/app-id: "service-name"` - Unique identifier for service invocation
- `dapr.io/app-port: "port-number"` - Port where the application listens

Additionally, both services use:
- `dapr.io/enable-api-logging: "true"` - For debugging service invocation
- `dapr.io/log-level: "info"` - For detailed logging