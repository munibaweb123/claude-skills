# Production Kubernetes Checklist

## Application Configuration

- [ ] **Resource requests and limits** defined for all containers
- [ ] **Health probes** configured (liveness, readiness, startup if needed)
- [ ] **Replicas** set to at least 2 for high availability
- [ ] **Update strategy** configured (RollingUpdate with maxSurge/maxUnavailable)
- [ ] **Pod Disruption Budget** defined

## Security

- [ ] **Non-root user** (`runAsNonRoot: true`)
- [ ] **Read-only filesystem** where possible
- [ ] **Capabilities dropped** (`drop: [ALL]`)
- [ ] **Privilege escalation disabled** (`allowPrivilegeEscalation: false`)
- [ ] **Seccomp profile** set (`RuntimeDefault`)
- [ ] **Network Policies** restricting traffic
- [ ] **RBAC** configured with least-privilege
- [ ] **Secrets** stored securely (not in git, encrypted at rest)
- [ ] **Pod Security Standards** enforced at namespace level

## Reliability

- [ ] **HPA** configured for auto-scaling
- [ ] **PodDisruptionBudget** prevents too many pods down
- [ ] **Anti-affinity rules** spread pods across nodes
- [ ] **Graceful shutdown** with preStop hooks
- [ ] **terminationGracePeriodSeconds** set appropriately

## Observability

- [ ] **Logging** configured (stdout/stderr)
- [ ] **Metrics** exposed (Prometheus format)
- [ ] **Tracing** integrated if needed
- [ ] **Alerts** configured for critical conditions

## Networking

- [ ] **Service** exposes deployment correctly
- [ ] **Ingress** with TLS configured
- [ ] **DNS** names configured
- [ ] **Load balancer** health checks configured

## Storage

- [ ] **PersistentVolumeClaims** with appropriate StorageClass
- [ ] **Backup strategy** for persistent data
- [ ] **Reclaim policy** set appropriately

---

## Production-Ready Deployment Template

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: production-app
  namespace: production
  labels:
    app: production-app
    version: v1.0.0
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: production-app
  template:
    metadata:
      labels:
        app: production-app
        version: v1.0.0
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault

      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchLabels:
                  app: production-app
              topologyKey: kubernetes.io/hostname

      containers:
      - name: app
        image: myapp:1.0.0
        imagePullPolicy: Always
        ports:
        - name: http
          containerPort: 8080

        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
              - ALL

        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi

        startupProbe:
          httpGet:
            path: /healthz
            port: 8080
          failureThreshold: 30
          periodSeconds: 10

        livenessProbe:
          httpGet:
            path: /healthz
            port: 8080
          periodSeconds: 15
          timeoutSeconds: 5
          failureThreshold: 3

        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3

        env:
        - name: POD_NAME
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        - name: POD_NAMESPACE
          valueFrom:
            fieldRef:
              fieldPath: metadata.namespace

        volumeMounts:
        - name: tmp
          mountPath: /tmp
        - name: config
          mountPath: /etc/app/config
          readOnly: true

      volumes:
      - name: tmp
        emptyDir: {}
      - name: config
        configMap:
          name: app-config

      terminationGracePeriodSeconds: 30
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: production-app-pdb
  namespace: production
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: production-app
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: production-app-hpa
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: production-app
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
---
apiVersion: v1
kind: Service
metadata:
  name: production-app
  namespace: production
spec:
  type: ClusterIP
  selector:
    app: production-app
  ports:
  - name: http
    port: 80
    targetPort: 8080
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: production-app
  namespace: production
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - app.example.com
    secretName: app-tls
  rules:
  - host: app.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: production-app
            port:
              number: 80
```
