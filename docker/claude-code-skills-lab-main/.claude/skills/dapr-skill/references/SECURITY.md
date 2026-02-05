# Dapr Security

## mTLS (Mutual TLS)

Dapr automatically establishes mTLS between sidecars to encrypt service-to-service communication. The Sentry service acts as a Certificate Authority (CA) that generates and manages certificates.

### Configuration
```yaml
apiVersion: dapr.io/v1alpha1
kind: Configuration
metadata:
  name: dapr-config
spec:
  mtls:
    enabled: true
    workloadCertTTL: 24h
    allowedClockSkew: 15m
```

## Application Identity

Every application in Dapr has a unique App ID that serves as its identity:
- Used for service discovery and invocation
- Forms the basis for security policies
- Enables certificate generation for mTLS
- Determines component access permissions

## API Authentication

Dapr supports token-based authentication to ensure only authenticated applications can call into Dapr:
- API tokens for application-to-Dapr authentication
- OAuth 2.0 middleware for endpoint authorization
- OpenID Connect support for advanced authentication

## Component Security

### Scoping
Limit which applications can use specific components:
```yaml
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: sensitive-store
spec:
  # ... component spec ...
scopes:
- app1
- app2
```

### Secret Scoping
Restrict which applications can access specific secrets:
```yaml
apiVersion: dapr.io/v1alpha1
kind: Configuration
metadata:
  name: secret-config
spec:
  secrets:
    scopes:
    - storeName: "local-secret-store"
      defaultAccess: "deny"
      allowedSecrets: ["db-password", "api-key"]
```

## Namespace Isolation

Applications with the same App ID in different namespaces remain isolated:
- Namespace-aware security controls
- Multi-tenant deployment support
- Resource isolation between environments

## Network Security

### Localhost Binding
By default, Dapr sidecars only accept connections on localhost to minimize attack surface:
- Sidecars listen on 127.0.0.1 by default
- Prevents external access to Dapr APIs
- Additional network policies can be applied

### API Allow Lists
Restrict which Dapr APIs applications can access:
```yaml
apiVersion: dapr.io/v1alpha1
kind: Configuration
metadata:
  name: api-allowlist-config
spec:
  apiAllowlist:
    enabled: true
    verbs:
    - GET
    - POST
    - PUT
    - DELETE
```

## Security Best Practices

1. Always enable mTLS in production
2. Use component scoping to limit access
3. Implement proper secret management
4. Apply network policies for additional protection
5. Regularly rotate certificates and secrets
6. Monitor and audit security events
7. Keep Dapr runtime updated with security patches