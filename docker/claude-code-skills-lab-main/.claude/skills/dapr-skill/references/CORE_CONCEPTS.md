# Dapr Core Concepts

## Sidecar Pattern
Dapr uses a sidecar pattern where a lightweight runtime (`daprd`) runs alongside your application. This pattern provides:
- Loose coupling between application code and distributed system concerns
- Language and framework independence
- Consistent APIs across different infrastructure environments
- Independent scaling of application and Dapr sidecar

## Building Blocks
Dapr provides standardized APIs (building blocks) for common distributed system challenges:

1. **Service Invocation** - Secure, reliable service-to-service communication with service discovery
2. **State Management** - Distributed state with support for various state stores
3. **Publish & Subscribe** - Event-driven messaging with multiple broker support
4. **Bindings** - Input/output bindings to external systems
5. **Actors** - Virtual actor pattern implementation
6. **Secrets Management** - Secure access to secrets from various providers
7. **Workflow** - Long-running business process orchestration
8. **Agentic AI** - Durable AI application patterns

## Component Architecture
Dapr's component model allows pluggable connectivity to external systems:
- Components are configured via YAML files
- Support for various providers (Redis, Azure, AWS, GCP, etc.)
- Component scoping limits which applications can use specific components
- Configuration-driven approach reduces code dependencies

## Application Identity
Each application is identified by an App ID which serves as the primary security boundary in Dapr:
- Used for service discovery and invocation
- Forms the basis for security policies
- Enables mTLS certificate generation
- Determines component access permissions