#!/usr/bin/env python3
"""
Kubernetes Manifest Generator

Generates Kubernetes deployment manifests based on user input.
Outputs properly formatted YAML for Deployment, Service, and optional components.

Usage:
    python generate-manifest.py --name myapp --image myapp:1.0 --port 8080
    python generate-manifest.py --name myapp --image myapp:1.0 --port 8080 --replicas 3 --namespace production
    python generate-manifest.py --name myapp --image myapp:1.0 --port 8080 --production
"""

import argparse
import sys


def generate_namespace(namespace: str) -> str:
    """Generate Namespace manifest."""
    return f"""apiVersion: v1
kind: Namespace
metadata:
  name: {namespace}
"""


def generate_deployment(
    name: str,
    image: str,
    port: int,
    replicas: int = 1,
    namespace: str = "default",
    production: bool = False,
    cpu_request: str = "100m",
    memory_request: str = "128Mi",
    cpu_limit: str = "500m",
    memory_limit: str = "512Mi",
) -> str:
    """Generate Deployment manifest."""

    # Base deployment
    manifest = f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: {name}
  namespace: {namespace}
  labels:
    app: {name}
spec:
  replicas: {replicas}
  selector:
    matchLabels:
      app: {name}
  template:
    metadata:
      labels:
        app: {name}
    spec:"""

    # Add security context for production
    if production:
        manifest += f"""
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault"""

    manifest += f"""
      containers:
      - name: {name}
        image: {image}
        ports:
        - containerPort: {port}"""

    # Add security context for production containers
    if production:
        manifest += """
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
              - ALL"""

    # Add resources
    manifest += f"""
        resources:
          requests:
            cpu: {cpu_request}
            memory: {memory_request}
          limits:
            cpu: {cpu_limit}
            memory: {memory_limit}"""

    # Add probes
    manifest += f"""
        livenessProbe:
          httpGet:
            path: /healthz
            port: {port}
          initialDelaySeconds: 10
          periodSeconds: 15
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: {port}
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3"""

    # Add startup probe for production
    if production:
        manifest += f"""
        startupProbe:
          httpGet:
            path: /healthz
            port: {port}
          failureThreshold: 30
          periodSeconds: 10"""

    # Add tmp volume for read-only filesystem
    if production:
        manifest += """
        volumeMounts:
        - name: tmp
          mountPath: /tmp
      volumes:
      - name: tmp
        emptyDir: {}"""

    return manifest


def generate_service(
    name: str,
    port: int,
    target_port: int,
    namespace: str = "default",
    service_type: str = "ClusterIP",
) -> str:
    """Generate Service manifest."""
    return f"""apiVersion: v1
kind: Service
metadata:
  name: {name}
  namespace: {namespace}
spec:
  type: {service_type}
  selector:
    app: {name}
  ports:
  - port: {port}
    targetPort: {target_port}
"""


def generate_hpa(
    name: str,
    namespace: str = "default",
    min_replicas: int = 2,
    max_replicas: int = 10,
    cpu_target: int = 70,
) -> str:
    """Generate HorizontalPodAutoscaler manifest."""
    return f"""apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {name}-hpa
  namespace: {namespace}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {name}
  minReplicas: {min_replicas}
  maxReplicas: {max_replicas}
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: {cpu_target}
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
"""


def generate_ingress(
    name: str,
    host: str,
    namespace: str = "default",
    service_port: int = 80,
    tls: bool = False,
) -> str:
    """Generate Ingress manifest."""
    manifest = f"""apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {name}
  namespace: {namespace}
spec:
  ingressClassName: nginx"""

    if tls:
        manifest += f"""
  tls:
  - hosts:
    - {host}
    secretName: {name}-tls"""

    manifest += f"""
  rules:
  - host: {host}
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: {name}
            port:
              number: {service_port}
"""
    return manifest


def main():
    parser = argparse.ArgumentParser(
        description="Generate Kubernetes deployment manifests"
    )

    # Required arguments
    parser.add_argument("--name", required=True, help="Application name")
    parser.add_argument("--image", required=True, help="Container image")
    parser.add_argument("--port", type=int, required=True, help="Container port")

    # Optional arguments
    parser.add_argument("--namespace", default="default", help="Kubernetes namespace")
    parser.add_argument("--replicas", type=int, default=1, help="Number of replicas")
    parser.add_argument("--service-type", default="ClusterIP",
                        choices=["ClusterIP", "NodePort", "LoadBalancer"],
                        help="Service type")
    parser.add_argument("--service-port", type=int, default=80, help="Service port")

    # Production flags
    parser.add_argument("--production", action="store_true",
                        help="Enable production settings (security, HPA)")
    parser.add_argument("--host", help="Ingress hostname")
    parser.add_argument("--tls", action="store_true", help="Enable TLS for Ingress")

    # Resource settings
    parser.add_argument("--cpu-request", default="100m", help="CPU request")
    parser.add_argument("--memory-request", default="128Mi", help="Memory request")
    parser.add_argument("--cpu-limit", default="500m", help="CPU limit")
    parser.add_argument("--memory-limit", default="512Mi", help="Memory limit")

    # HPA settings
    parser.add_argument("--min-replicas", type=int, default=2, help="HPA min replicas")
    parser.add_argument("--max-replicas", type=int, default=10, help="HPA max replicas")

    args = parser.parse_args()

    manifests = []

    # Generate namespace if not default
    if args.namespace != "default":
        manifests.append(generate_namespace(args.namespace))

    # Generate deployment
    manifests.append(generate_deployment(
        name=args.name,
        image=args.image,
        port=args.port,
        replicas=args.replicas if not args.production else max(2, args.replicas),
        namespace=args.namespace,
        production=args.production,
        cpu_request=args.cpu_request,
        memory_request=args.memory_request,
        cpu_limit=args.cpu_limit,
        memory_limit=args.memory_limit,
    ))

    # Generate service
    manifests.append(generate_service(
        name=args.name,
        port=args.service_port,
        target_port=args.port,
        namespace=args.namespace,
        service_type=args.service_type,
    ))

    # Generate HPA for production
    if args.production:
        manifests.append(generate_hpa(
            name=args.name,
            namespace=args.namespace,
            min_replicas=args.min_replicas,
            max_replicas=args.max_replicas,
        ))

    # Generate Ingress if host provided
    if args.host:
        manifests.append(generate_ingress(
            name=args.name,
            host=args.host,
            namespace=args.namespace,
            service_port=args.service_port,
            tls=args.tls,
        ))

    # Output all manifests separated by ---
    print("---\n".join(manifests))


if __name__ == "__main__":
    main()
