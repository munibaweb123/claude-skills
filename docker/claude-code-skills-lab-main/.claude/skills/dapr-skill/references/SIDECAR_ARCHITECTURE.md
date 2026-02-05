# Dapr Sidecar Architecture

## The Translator Analogy

Dapr's sidecar architecture functions like a professional translator who bridges communication between two parties speaking different languages.

In traditional distributed applications, your application code needs to speak the "language" of each infrastructure service:
- To talk to Redis, your code must understand Redis commands and protocols
- To talk to Kafka, your code must understand Kafka producer/consumer patterns
- To talk to AWS services, your code must understand AWS SDKs and APIs

This creates tight coupling where your application becomes dependent on specific infrastructure implementations.

Dapr acts as a translator:
- Your application speaks a standard HTTP/gRPC API to Dapr
- Dapr understands the "language" of all infrastructure services
- Dapr translates your standard requests into the appropriate infrastructure-specific calls
- Your application remains infrastructure-agnostic

This translation layer provides enormous benefits in flexibility, maintainability, and separation of concerns.

## Dapr Sidecar (daprd) Technical Details

### Port Configuration

The Dapr sidecar (`daprd`) exposes multiple ports for different purposes:

| Port | Protocol | Purpose | Example Usage |
|------|----------|---------|---------------|
| **3500** | HTTP | Primary API for all Dapr building blocks | Service invocation, state management, pub/sub |
| **50001** | gRPC | High-performance API for all building blocks | Preferred for high-throughput scenarios |
| **9090** | HTTP | Metrics endpoint | Prometheus scraping |
| **9900** | HTTP | Health check endpoint | Kubernetes liveness/readiness probes |
| **50002** | gRPC | Internal control plane communication | Communication with Dapr operators/placement |

### API Endpoints

Common HTTP API endpoints available at port 3500:

```
# Service Invocation
POST /v1.0/invoke/<destination-app>/method/<method-path>

# State Management
GET /v1.0/state/<store-name>/<key>
POST /v1.0/state/<store-name>
DELETE /v1.0/state/<store-name>/<key>

# Publish & Subscribe
POST /v1.0/publish/<pubsub-name>/<topic>

# Secret Management
GET /v1.0/secrets/<secret-store-name>/<key>

# Actor Methods
POST /v1.0/actors/<actor-type>/<actor-id>/method/<method-name>
```

## Kubernetes Annotations

### Essential Annotations

When deploying Dapr applications to Kubernetes, these three annotations are essential:

1. **dapr.io/enabled: "true"**
   - Enables automatic sidecar injection
   - Tells the Dapr sidecar injector to add a daprd container to the pod
   - Without this, no Dapr sidecar will be injected

2. **dapr.io/app-id: "<unique-app-id>"**
   - Defines the unique identifier for your application
   - Used for service discovery, actor placement, and security
   - Must be unique within the namespace

3. **dapr.io/app-port: "<port-number>"**
   - Specifies the port your application is listening on
   - Dapr uses this to route service invocations to your app
   - Required for service invocation functionality

### Additional Annotations

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  template:
    metadata:
      annotations:
        # Essential annotations
        dapr.io/enabled: "true"
        dapr.io/app-id: "myapp"
        dapr.io/app-port: "8080"

        # Optional but useful annotations
        dapr.io/config: "app-config"                    # Configuration resource to use
        dapr.io/components: "statestore,pubsub"         # Specific components to load
        dapr.io/log-as-json: "true"                     # Format Dapr logs as JSON
        dapr.io/sidecar-cpu-limit: "1.0"               # CPU limit for sidecar
        dapr.io/sidecar-cpu-request: "0.1"             # CPU request for sidecar
        dapr.io/sidecar-memory-limit: "512Mi"          # Memory limit for sidecar
        dapr.io/sidecar-memory-request: "128Mi"        # Memory request for sidecar
        dapr.io/enable-metrics: "true"                  # Enable/disable metrics
        dapr.io/metrics-port: "9090"                   # Metrics port override
        dapr.io/enable-debug: "false"                  # Enable/disable debug mode
        dapr.io/debug-port: "40000"                    # Debug port
        dapr.io/enable-profiling: "false"              # Enable/disable profiling
        dapr.io/image: "daprio/daprd:1.11.0"          # Specific Dapr runtime image
```

## Deployment Modes

### Container Mode (Kubernetes)

In container mode, Dapr runs as a sidecar container within the same pod as your application:

```
Pod: myapp-pod
├── Container: myapp (your application)
│   ├── Port: 8080
│   └── Listens for requests
└── Container: daprd (Dapr sidecar)
    ├── Port: 3500 (HTTP API)
    ├── Port: 50001 (gRPC API)
    ├── Port: 9090 (Metrics)
    └── Communicates with infrastructure
```

Benefits:
- Complete process isolation between app and Dapr
- Independent resource management
- Better security posture
- Standard Kubernetes networking
- Recommended for production

### Process Mode (Self-Hosted)

In process mode, Dapr runs as a process on the same host as your application:

```
Host Machine
├── Process: myapp (your application)
│   └── Listens on port 8080
└── Process: daprd (Dapr sidecar)
    ├── Listens on port 3500 (HTTP API)
    ├── Listens on port 50001 (gRPC API)
    └── Communicates with infrastructure via localhost
```

Benefits:
- Lower resource overhead
- Faster startup times
- Simpler debugging
- Suitable for development/testing

## Sidecar Communication Patterns

### Application to Dapr

Applications communicate with Dapr using:
1. HTTP requests to `http://localhost:3500`
2. gRPC calls to `localhost:50001`
3. Dapr SDKs that abstract the communication details

### Dapr to Application

Dapr communicates with applications by:
1. Forwarding service invocation requests to `http://localhost:<app-port>`
2. Calling webhook endpoints for pub/sub message delivery
3. Making actor method calls to registered actor endpoints

### Dapr to Infrastructure

Dapr connects to infrastructure services through:
1. Component configurations (YAML files)
2. Pluggable component architecture
3. Standard protocols (Redis protocol, Kafka protocol, etc.)