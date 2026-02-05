# Kubernetes Manifest Critical Evaluation Checklist

This checklist provides a systematic way to evaluate Kubernetes manifests for production readiness, security, and best practices.

## Security Assessment

### Container Security
- [ ] Images are from trusted sources (official registries, verified publishers)
- [ ] Images are regularly updated and scanned for vulnerabilities
- [ ] Images use minimal base (distroless/alpine preferred over ubuntu/debian)
- [ ] Containers run as non-root user (`runAsNonRoot: true`)
- [ ] User ID is explicitly specified (`runAsUser: 1000`)
- [ ] File system is read-only when possible (`readOnlyRootFilesystem: true`)
- [ ] Privilege escalation is disabled (`allowPrivilegeEscalation: false`)
- [ ] Capabilities are dropped (`capabilities.drop: ['ALL']`)
- [ ] Seccomp profile is applied (`seccompProfile.type: RuntimeDefault`)

### Network Security
- [ ] Network policies are defined to restrict traffic
- [ ] Services are exposed only as needed (prefer ClusterIP over LoadBalancer)
- [ ] TLS is enforced for external connections
- [ ] Ingress controllers have WAF or rate limiting configured

### RBAC and Permissions
- [ ] Service accounts are specified and minimal
- [ ] Role-based access is properly configured
- [ ] Pods don't have excessive permissions
- [ ] Secrets are used instead of ConfigMaps for sensitive data

## Resource Management

### Resource Requests and Limits
- [ ] CPU and memory requests are specified for all containers
- [ ] CPU and memory limits are specified for all containers
- [ ] Resource ratios are appropriate (limits >= requests)
- [ ] Resource values are based on actual application requirements
- [ ] No containers have unlimited resources (limit = 0)

### Quality of Service (QoS)
- [ ] QoS class is understood and appropriate (Guaranteed/Burstable/BestEffort)
- [ ] Critical applications use Guaranteed QoS (requests = limits)
- [ ] Resource limits prevent resource exhaustion

## Availability and Reliability

### Health Checks
- [ ] Liveness probes are configured to detect stuck applications
- [ ] Readiness probes are configured to detect when app is ready for traffic
- [ ] Startup probes are configured for slow-starting applications
- [ ] Probe timeouts and thresholds are appropriate
- [ ] Health check endpoints are reliable and lightweight

### Deployment Strategy
- [ ] Rolling update strategy is configured appropriately
- [ ] Max surge and max unavailable values are set correctly
- [ ] Revision history limit is configured (typically 10)
- [ ] Pod disruption budgets are configured for HA workloads

### Replication and Scaling
- [ ] Sufficient replicas for high availability (typically >= 3 for critical apps)
- [ ] Horizontal Pod Autoscaler is configured for variable load
- [ ] Cluster autoscaler integration is considered
- [ ] Anti-affinity rules are configured if needed

## Configuration Management

### Environment Configuration
- [ ] Configuration is externalized using ConfigMaps/Secrets
- [ ] Sensitive data is stored in Secrets, not ConfigMaps
- [ ] Secrets are mounted as files or environment variables securely
- [ ] Configuration is validated before deployment

### Naming and Labels
- [ ] Resource names follow consistent naming conventions
- [ ] Labels are applied consistently across related resources
- [ ] Labels include `app`, `version`, `environment` selectors
- [ ] Annotations are used for operational metadata

## Observability

### Logging
- [ ] Applications log to stdout/stderr
- [ ] Structured logging is used (JSON format preferred)
- [ ] Log levels are configurable
- [ ] Log retention and rotation are configured

### Monitoring
- [ ] Metrics endpoints are exposed (Prometheus format preferred)
- [ ] Key application metrics are collected
- [ ] Resource utilization is monitored
- [ ] Custom business metrics are available

### Tracing
- [ ] Distributed tracing is implemented if needed
- [ ] Trace sampling rates are configured appropriately

## Production Readiness

### Backup and Recovery
- [ ] Data persistence strategies are defined
- [ ] Backup schedules are configured for stateful applications
- [ ] Disaster recovery procedures are documented
- [ ] Data retention policies are implemented

### Lifecycle Management
- [ ] Graceful shutdown is implemented (SIGTERM handling)
- [ ] PreStop hooks are configured if needed
- [ ] Init containers are used for setup tasks
- [ ] Sidecar containers are used for auxiliary functions

### Testing and Validation
- [ ] Manifests are validated with kubeval or similar tools
- [ ] Security scanning is performed (trivy, kubesec, etc.)
- [ ] Integration tests cover deployment scenarios
- [ ] Chaos engineering is implemented for resilience testing

## Performance Optimization

### Resource Efficiency
- [ ] Resource requests are based on actual usage data
- [ ] Over-provisioning is minimized
- [ ] Container images are optimized (multi-stage builds)
- [ ] Unused packages and dependencies are removed

### Network Optimization
- [ ] Services are properly load balanced
- [ ] CDN is used for static assets when appropriate
- [ ] Connection pooling is configured
- [ ] Compression is enabled where beneficial

## Documentation and Maintenance

### Documentation
- [ ] Deployment procedures are documented
- [ ] Rollback procedures are documented
- [ ] Configuration parameters are documented
- [ ] Troubleshooting guide is available

### Maintenance
- [ ] Update and patching procedures are defined
- [ ] Deprecation warnings are monitored
- [ ] Version compatibility is tested
- [ ] Automated testing pipeline is in place

## Scoring System

Rate each section from 0-10 based on completeness:

- 9-10: Excellent - All items addressed with best practices
- 7-8: Good - Most items addressed, minor improvements needed
- 5-6: Adequate - Basic requirements met, significant improvements needed
- 3-4: Poor - Many requirements missing, major overhaul needed
- 0-2: Critical - Fundamental issues present, not production-ready

**Overall Score: [__/100]**

## Action Items

Based on the evaluation, list specific improvements needed:

1. 
2. 
3. 
4. 
5. 

## Final Assessment

**Production Ready:** [Yes/No/Conditional]

**Risk Level:** [Low/Medium/High/Critical]

**Recommended Actions Before Production:**