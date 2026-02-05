# Kubernetes Storage Reference

## Core Concepts

| Resource | Description | Scope |
|----------|-------------|-------|
| **PersistentVolume (PV)** | Cluster storage resource | Cluster-wide |
| **PersistentVolumeClaim (PVC)** | User request for storage | Namespace |
| **StorageClass** | Storage provisioner template | Cluster-wide |

---

## Access Modes

| Mode | Short | Description |
|------|-------|-------------|
| `ReadWriteOnce` | RWO | Single node read-write |
| `ReadOnlyMany` | ROX | Multiple nodes read-only |
| `ReadWriteMany` | RWX | Multiple nodes read-write |
| `ReadWriteOncePod` | RWOP | Single pod read-write |

---

## Static Provisioning

### Create PersistentVolume

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: my-pv
spec:
  capacity:
    storage: 10Gi
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  hostPath:
    path: /data/my-pv
```

### Create PersistentVolumeClaim

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: my-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
```

---

## Dynamic Provisioning

### StorageClass

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
provisioner: kubernetes.io/gce-pd
reclaimPolicy: Delete
allowVolumeExpansion: true
parameters:
  type: pd-ssd
```

### PVC with StorageClass

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: dynamic-pvc
spec:
  storageClassName: fast-ssd
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 20Gi
```

---

## Using PVC in Pod

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: storage-pod
spec:
  containers:
  - name: app
    image: nginx
    volumeMounts:
    - name: data
      mountPath: /usr/share/nginx/html
  volumes:
  - name: data
    persistentVolumeClaim:
      claimName: my-pvc
```

---

## Using PVC in Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      containers:
      - name: app
        image: nginx
        volumeMounts:
        - name: data
          mountPath: /data
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: my-pvc
```

---

## Reclaim Policies

| Policy | Behavior |
|--------|----------|
| `Retain` | PV kept after PVC deleted; manual cleanup required |
| `Delete` | PV and backing storage deleted automatically |
| `Recycle` | **Deprecated** - Use dynamic provisioning |

---

## Complete Example

```yaml
# StorageClass
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: standard
provisioner: kubernetes.io/gce-pd
reclaimPolicy: Delete
---
# PVC
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: app-data
spec:
  storageClassName: standard
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
---
# Deployment using PVC
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: app
  template:
    metadata:
      labels:
        app: app
    spec:
      containers:
      - name: app
        image: myapp:1.0
        volumeMounts:
        - name: data
          mountPath: /app/data
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: app-data
```

---

## Essential Commands

```bash
# View storage classes
kubectl get storageclass

# View PVs
kubectl get pv

# View PVCs
kubectl get pvc

# Describe PVC
kubectl describe pvc my-pvc

# Delete PVC
kubectl delete pvc my-pvc
```

---

## Best Practices

1. **Use dynamic provisioning** for easier management
2. **Set appropriate reclaim policy** (`Retain` for important data)
3. **Use StorageClasses** for consistent provisioning
4. **Match access modes** to application requirements
5. **Request only needed storage** to avoid waste
