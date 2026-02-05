# Kubernetes Configuration Reference

## Quick Reference: Injection Patterns

| Pattern | Use Case | Updates Automatically |
|---------|----------|----------------------|
| `envFrom.configMapRef` | Inject all ConfigMap keys as env vars | No |
| `envFrom.secretRef` | Inject all Secret keys as env vars | No |
| `valueFrom.configMapKeyRef` | Inject single ConfigMap key | No |
| `valueFrom.secretKeyRef` | Inject single Secret key | No |
| Volume mount (ConfigMap) | Mount as files | Yes |
| Volume mount (Secret) | Mount as files | Yes |

---

## ConfigMaps

ConfigMaps store non-confidential configuration data as key-value pairs.

### Creating a ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: myapp
data:
  # Simple key-value pairs
  APP_ENV: "production"
  LOG_LEVEL: "info"
  MAX_CONNECTIONS: "100"

  # Multi-line/file-like values
  nginx.conf: |
    server {
      listen 80;
      server_name localhost;
      location / {
        proxy_pass http://backend:8080;
      }
    }
  application.properties: |
    spring.datasource.url=jdbc:postgresql://db:5432/mydb
    spring.jpa.hibernate.ddl-auto=validate
```

### envFrom: Bulk Environment Variable Injection

Inject **all** keys from a ConfigMap as environment variables:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 2
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: app
        image: myapp:1.0
        envFrom:
        # Inject all keys from ConfigMap
        - configMapRef:
            name: app-config
        # Optional: add prefix to all injected vars
        - configMapRef:
            name: feature-flags
          prefix: FF_
```

**Result**: Each key in `app-config` becomes an environment variable with the same name.

### valueFrom: Single Environment Variable Injection

Inject **specific** keys with custom variable names:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 2
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: app
        image: myapp:1.0
        env:
        # Rename key when injecting
        - name: ENVIRONMENT
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: APP_ENV
        # Mark as optional (won't fail if missing)
        - name: DEBUG_MODE
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: DEBUG_ENABLED
              optional: true
```

### Volume Mount: File-Based Configuration

Mount ConfigMap data as files in the container:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx
spec:
  replicas: 2
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.25
        volumeMounts:
        # Mount entire ConfigMap as directory
        - name: config-volume
          mountPath: /etc/nginx/conf.d
          readOnly: true
        # Mount single key to specific file path
        - name: app-props
          mountPath: /app/config/application.properties
          subPath: application.properties
          readOnly: true
      volumes:
      - name: config-volume
        configMap:
          name: nginx-config
      - name: app-props
        configMap:
          name: app-config
          items:
          - key: application.properties
            path: application.properties
            mode: 0644  # Optional: set file permissions
```

### ConfigMap with Specific File Permissions

```yaml
volumes:
- name: config-volume
  configMap:
    name: app-config
    defaultMode: 0644  # rwxr--r-- for all files
    items:
    - key: script.sh
      path: script.sh
      mode: 0755  # rwxr-xr-x (executable)
    - key: config.json
      path: config.json
      mode: 0600  # rw------- (owner only)
```

### ConfigMap Constraints

- Maximum size: **1 MiB**
- Must be in same namespace as Pod
- Volume-mounted ConfigMaps update automatically (with delay)
- Environment variables do **NOT** update automatically
- Pod restart required for env var changes

---

## Secrets

Secrets store sensitive data like passwords, tokens, or keys.

### Secret Types

| Type | Usage |
|------|-------|
| `Opaque` | Default; arbitrary data |
| `kubernetes.io/dockerconfigjson` | Docker registry credentials |
| `kubernetes.io/basic-auth` | Basic authentication |
| `kubernetes.io/ssh-auth` | SSH credentials |
| `kubernetes.io/tls` | TLS certificates |
| `kubernetes.io/service-account-token` | Service account tokens |

### Creating Secrets

**Command line (recommended for avoiding version control):**
```bash
# From literal values
kubectl create secret generic db-credentials \
  --from-literal=username=admin \
  --from-literal=password='S3cr3tP@ssw0rd!'

# From file
kubectl create secret generic tls-certs \
  --from-file=tls.crt=./server.crt \
  --from-file=tls.key=./server.key

# From .env file
kubectl create secret generic app-secrets --from-env-file=.env
```

**YAML manifest (values must be base64 encoded):**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-credentials
  namespace: myapp
type: Opaque
data:
  username: YWRtaW4=          # echo -n 'admin' | base64
  password: UzNjcjN0UEBzc3cwcmQh  # echo -n 'S3cr3tP@ssw0rd!' | base64
```

**Using stringData (auto-encodes to base64):**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-credentials
  namespace: myapp
type: Opaque
stringData:
  username: admin
  password: S3cr3tP@ssw0rd!
```

### envFrom: Bulk Secret Injection

Inject **all** keys from a Secret as environment variables:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 2
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: app
        image: myapp:1.0
        envFrom:
        # Inject all keys from Secret
        - secretRef:
            name: db-credentials
        # Optional: add prefix to all injected vars
        - secretRef:
            name: api-keys
          prefix: API_
```

### valueFrom: Single Secret Value Injection

Inject **specific** secret keys:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 2
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: app
        image: myapp:1.0
        env:
        # Database credentials
        - name: DB_USERNAME
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: username
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: password
        # Optional secret (won't fail if missing)
        - name: OPTIONAL_API_KEY
          valueFrom:
            secretKeyRef:
              name: external-api
              key: api-key
              optional: true
```

### Volume Mount: File-Based Secrets

Mount secrets as files (preferred for TLS certs, SSH keys):

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 2
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: app
        image: myapp:1.0
        volumeMounts:
        # Mount entire Secret as directory
        - name: tls-certs
          mountPath: /etc/tls
          readOnly: true
        # Mount single key to specific path
        - name: ssh-key
          mountPath: /root/.ssh/id_rsa
          subPath: id_rsa
          readOnly: true
      volumes:
      - name: tls-certs
        secret:
          secretName: tls-secret
          defaultMode: 0400  # r-------- (secure permissions)
      - name: ssh-key
        secret:
          secretName: ssh-credentials
          items:
          - key: private-key
            path: id_rsa
            mode: 0400
```

### Combined ConfigMap and Secret Injection

Complete example showing all patterns together:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: app
        image: myapp:2.0
        ports:
        - containerPort: 8080

        # Bulk injection
        envFrom:
        - configMapRef:
            name: app-config
        - secretRef:
            name: app-secrets
          prefix: SECRET_

        # Individual injection
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: connection-string
        - name: CACHE_HOST
          valueFrom:
            configMapKeyRef:
              name: infrastructure
              key: redis-host

        # File mounts
        volumeMounts:
        - name: config-files
          mountPath: /app/config
          readOnly: true
        - name: tls-certs
          mountPath: /etc/tls
          readOnly: true

      volumes:
      - name: config-files
        configMap:
          name: app-config-files
      - name: tls-certs
        secret:
          secretName: tls-secret
          defaultMode: 0400
```

---

## Security Best Practices for Secrets

### 1. Enable Encryption at Rest

Configure etcd encryption in your cluster:

```yaml
# /etc/kubernetes/encryption-config.yaml
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources:
      - secrets
    providers:
      - aescbc:
          keys:
            - name: key1
              secret: <base64-encoded-32-byte-key>
      - identity: {}
```

### 2. Use RBAC for Least-Privilege Access

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: secret-reader
  namespace: myapp
rules:
- apiGroups: [""]
  resources: ["secrets"]
  resourceNames: ["db-credentials"]  # Limit to specific secrets
  verbs: ["get"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: read-db-credentials
  namespace: myapp
subjects:
- kind: ServiceAccount
  name: myapp-sa
  namespace: myapp
roleRef:
  kind: Role
  name: secret-reader
  apiGroup: rbac.authorization.k8s.io
```

### 3. Use External Secret Managers (Production)

**External Secrets Operator** integrates with cloud providers:

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: db-credentials
  namespace: myapp
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore
  target:
    name: db-credentials
    creationPolicy: Owner
  data:
  - secretKey: username
    remoteRef:
      key: prod/myapp/database
      property: username
  - secretKey: password
    remoteRef:
      key: prod/myapp/database
      property: password
```

### 4. Avoid Secrets in Version Control

```bash
# .gitignore
*-secret.yaml
secrets/
*.key
*.pem
.env
```

**Use sealed-secrets for GitOps:**
```bash
# Encrypt secret for safe storage in Git
kubeseal --format yaml < secret.yaml > sealed-secret.yaml
```

### 5. Set Appropriate File Permissions

```yaml
volumes:
- name: secret-volume
  secret:
    secretName: my-secret
    defaultMode: 0400  # Read-only for owner
```

### 6. Use Immutable Secrets (Kubernetes 1.21+)

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-credentials
type: Opaque
immutable: true  # Cannot be modified after creation
data:
  password: cGFzc3dvcmQ=
```

### 7. Audit Secret Access

```bash
# Enable audit logging for secrets
# In kube-apiserver audit policy:
- level: Metadata
  resources:
  - group: ""
    resources: ["secrets"]
```

### 8. Rotate Secrets Regularly

```bash
# Update secret
kubectl create secret generic db-credentials \
  --from-literal=password='NewP@ssw0rd!' \
  --dry-run=client -o yaml | kubectl apply -f -

# Trigger rolling restart to pick up changes
kubectl rollout restart deployment/myapp -n myapp
```

---

## Essential Commands

```bash
# ConfigMaps
kubectl create configmap my-config --from-literal=key=value
kubectl create configmap my-config --from-file=config.properties
kubectl create configmap my-config --from-env-file=.env
kubectl get configmaps
kubectl describe configmap my-config
kubectl get configmap my-config -o yaml

# Secrets
kubectl create secret generic my-secret --from-literal=password=secret
kubectl create secret generic my-secret --from-file=tls.crt
kubectl create secret tls my-tls --cert=tls.crt --key=tls.key
kubectl get secrets
kubectl describe secret my-secret

# View secret values (base64 decoded)
kubectl get secret my-secret -o jsonpath='{.data.password}' | base64 --decode

# Edit ConfigMap/Secret
kubectl edit configmap my-config
kubectl edit secret my-secret

# Trigger update after ConfigMap/Secret change
kubectl rollout restart deployment/myapp

# Check if pod has correct env vars
kubectl exec -it <pod-name> -- env | grep MY_VAR

# Check mounted files
kubectl exec -it <pod-name> -- ls -la /etc/config
kubectl exec -it <pod-name> -- cat /etc/config/app.properties
```

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Pod stuck in `CreateContainerConfigError` | ConfigMap/Secret doesn't exist | Create the missing ConfigMap/Secret |
| Env var not updating | Env vars don't auto-update | Restart pod: `kubectl rollout restart` |
| Permission denied on mounted file | Incorrect `defaultMode` | Set appropriate mode (e.g., `0644`) |
| Secret value garbled | Double base64 encoding | Use `stringData` instead of `data` |
| ConfigMap too large | Exceeds 1 MiB limit | Split into multiple ConfigMaps |
