# Kubernetes Ingress Reference

## What is Ingress?

**Ingress** manages external HTTP/HTTPS access to services in a cluster. It provides:

- Load balancing
- SSL/TLS termination
- Name-based virtual hosting
- Path-based routing

**Note**: An **Ingress controller** is required (e.g., NGINX, Traefik, HAProxy).

---

## Basic Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: minimal-ingress
spec:
  ingressClassName: nginx
  rules:
  - http:
      paths:
      - path: /testpath
        pathType: Prefix
        backend:
          service:
            name: test
            port:
              number: 80
```

---

## Path Types

| Type | Behavior |
|------|----------|
| `Exact` | Matches URL path exactly, case-sensitive |
| `Prefix` | Matches based on URL path prefix split by `/` |
| `ImplementationSpecific` | Matching depends on IngressClass |

### Path Matching Examples

| Path Type | Path | Request | Matches? |
|-----------|------|---------|----------|
| Prefix | `/` | all paths | Yes |
| Exact | `/foo` | `/foo` | Yes |
| Exact | `/foo` | `/foo/` | No |
| Prefix | `/foo` | `/foo`, `/foo/` | Yes |
| Prefix | `/foo` | `/foobar` | No |

---

## Host-Based Routing

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: host-based-ingress
spec:
  ingressClassName: nginx
  rules:
  - host: foo.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: foo-service
            port:
              number: 80
  - host: bar.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: bar-service
            port:
              number: 80
```

---

## TLS Configuration

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: tls-ingress
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - myapp.example.com
    secretName: myapp-tls-secret
  rules:
  - host: myapp.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: myapp
            port:
              number: 80
```

Create TLS secret:
```bash
kubectl create secret tls myapp-tls-secret \
  --cert=path/to/tls.crt \
  --key=path/to/tls.key
```

---

## Default Backend

Handles requests that don't match any rules:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ingress-with-default
spec:
  ingressClassName: nginx
  defaultBackend:
    service:
      name: default-backend
      port:
        number: 80
  rules:
  - host: myapp.example.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: api-service
            port:
              number: 80
```

---

## Complete Multi-Service Example

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: multi-service-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - myapp.example.com
    secretName: myapp-tls
  rules:
  - host: myapp.example.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: api-service
            port:
              number: 8080
      - path: /admin
        pathType: Prefix
        backend:
          service:
            name: admin-service
            port:
              number: 8080
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-service
            port:
              number: 80
```

---

## Common Ingress Controllers

| Controller | Provider |
|------------|----------|
| NGINX Ingress | Community/NGINX Inc |
| Traefik | Traefik Labs |
| HAProxy | HAProxy Technologies |
| AWS ALB Controller | AWS |
| GCE Ingress | Google Cloud |

Install NGINX Ingress Controller:
```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.0/deploy/static/provider/cloud/deploy.yaml
```

---

## Essential Commands

```bash
# List ingresses
kubectl get ingress

# Describe ingress
kubectl describe ingress my-ingress

# Get ingress controller pods
kubectl get pods -n ingress-nginx

# Check ingress address
kubectl get ingress my-ingress -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
```
