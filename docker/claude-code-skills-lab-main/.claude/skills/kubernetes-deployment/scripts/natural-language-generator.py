#!/usr/bin/env python3
"""
AI-Assisted Kubernetes Manifest Generator

Converts natural language descriptions to Kubernetes YAML manifests.
Supports iterative refinement and validation patterns.

Usage:
    python natural-language-generator.py --describe "Create a web app deployment with 3 replicas"
    python natural-language-generator.py --describe "Deploy nginx with 2 replicas, expose on port 80, enable HPA" --validate
"""

import argparse
import json
import re
import yaml
from typing import Dict, List, Optional, Tuple
import sys


class NaturalLanguageParser:
    """Parses natural language descriptions into Kubernetes configuration parameters."""
    
    def __init__(self):
        self.patterns = {
            'replicas': r'(\d+)\s*(?:replica|instance|copy|pod)',
            'port': r'(?:port|expose|listen)\s*(?:on|=|:)?\s*(\d+)',
            'image': r'(?:image|container)\s+(?:is|=|:)?\s*([^\s,]+)',
            'name': r'(?:name|app|application)\s+(?:is|=|:)?\s*([^\s,]+)',
            'namespace': r'(?:namespace|ns)\s+(?:is|=|:)?\s*([^\s,]+)',
            'service_type': r'(?:service|svc)\s+(?:type|is)\s+(ClusterIP|NodePort|LoadBalancer)',
            'enable_hpa': r'(?:enable|with|add)\s+(?:HPA|autoscaling|auto[-\s]?scale)',
            'enable_ingress': r'(?:enable|with|add)\s+(?:ingress|route|external)',
            'production': r'(?:production|prod|secure|hardened)',
            'resources': r'(?:resource|cpu|memory)\s+(?:request|limit)\s+(?:is|=|:)?\s*([^\s,]+)',
            'host': r'(?:host|domain|hostname)\s+(?:is|=|:)?\s*([^\s,]+)',
            'env_vars': r'(?:environment|env|variable)\s+(?:is|=|:)?\s*([^\s,]+)',
        }
        
        self.image_patterns = [
            r'(nginx|apache|redis|postgres|mysql|mongo|elasticsearch):?([\d\.]+)?',
            r'([a-z0-9\-]+)/([a-z0-9\-]+):?([\d\.]+)?',
        ]

    def parse(self, description: str) -> Dict[str, any]:
        """Parse natural language description into configuration parameters."""
        description_lower = description.lower()
        params = {}
        
        # Extract numeric values
        for param_name, pattern in self.patterns.items():
            match = re.search(pattern, description_lower, re.IGNORECASE)
            if match:
                if param_name in ['replicas', 'port']:
                    params[param_name] = int(match.group(1))
                elif param_name in ['enable_hpa', 'enable_ingress', 'production']:
                    params[param_name] = True
                elif param_name == 'resources':
                    # Parse resource specifications like "100m CPU, 256Mi memory"
                    resource_text = match.group(1)
                    cpu_match = re.search(r'(\d+m?)\s*(?:cpu|core)', resource_text)
                    mem_match = re.search(r'(\d+[MG]i?)\s*(?:memory|ram)', resource_text)
                    if cpu_match:
                        params['cpu_request'] = cpu_match.group(1)
                    if mem_match:
                        params['memory_request'] = mem_match.group(1)
                else:
                    params[param_name] = match.group(1)
        
        # Extract image if not explicitly mentioned
        if 'image' not in params:
            for img_pattern in self.image_patterns:
                match = re.search(img_pattern, description_lower)
                if match:
                    if len(match.groups()) >= 2:
                        image = f"{match.group(1)}:{match.group(2) or 'latest'}"
                    else:
                        image = f"{match.group(1)}:latest"
                    params['image'] = image
                    break
        
        # Extract name from common app names if not specified
        if 'name' not in params:
            app_names = ['web', 'api', 'app', 'service', 'backend', 'frontend']
            for app_name in app_names:
                if app_name in description_lower:
                    params['name'] = app_name
                    break
        
        # Set defaults if not provided
        if 'name' not in params:
            params['name'] = 'app'
        if 'image' not in params:
            params['image'] = 'nginx:latest'
        if 'port' not in params:
            params['port'] = 80
        if 'replicas' not in params:
            params['replicas'] = 1
        if 'namespace' not in params:
            params['namespace'] = 'default'
            
        return params


class KubernetesManifestGenerator:
    """Generates Kubernetes manifests from parsed parameters."""
    
    def __init__(self):
        self.parser = NaturalLanguageParser()
    
    def generate_from_natural_language(self, description: str) -> str:
        """Generate Kubernetes manifests from natural language description."""
        params = self.parser.parse(description)
        return self.generate_manifests(params)
    
    def generate_manifests(self, params: Dict[str, any]) -> str:
        """Generate Kubernetes manifests based on parameters."""
        manifests = []
        
        # Generate namespace if not default
        if params.get('namespace') != 'default':
            manifests.append(self._generate_namespace(params['namespace']))
        
        # Generate deployment
        manifests.append(self._generate_deployment(params))
        
        # Generate service
        manifests.append(self._generate_service(params))
        
        # Generate HPA if enabled
        if params.get('enable_hpa'):
            manifests.append(self._generate_hpa(params))
        
        # Generate Ingress if enabled and host provided
        if params.get('enable_ingress') and params.get('host'):
            manifests.append(self._generate_ingress(params))
        
        return "---\n".join(manifests)
    
    def _generate_namespace(self, namespace: str) -> str:
        """Generate Namespace manifest."""
        return f"""apiVersion: v1
kind: Namespace
metadata:
  name: {namespace}
"""
    
    def _generate_deployment(self, params: Dict[str, any]) -> str:
        """Generate Deployment manifest."""
        name = params['name']
        image = params['image']
        port = params['port']
        replicas = params['replicas']
        namespace = params['namespace']
        production = params.get('production', False)
        
        # Set resource defaults based on production flag
        cpu_request = params.get('cpu_request', '100m' if production else '50m')
        memory_request = params.get('memory_request', '128Mi' if production else '64Mi')
        cpu_limit = params.get('cpu_limit', '500m' if production else '200m')
        memory_limit = params.get('memory_limit', '512Mi' if production else '256Mi')
        
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
        
        # Add environment variables if specified
        if params.get('env_vars'):
            manifest += f"""
        env:
        - name: {params['env_vars'].split('=')[0]}
          value: "{params['env_vars'].split('=', 1)[1] if '=' in params['env_vars'] else 'default'}"""
        
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
    
    def _generate_service(self, params: Dict[str, any]) -> str:
        """Generate Service manifest."""
        name = params['name']
        port = params.get('service_port', 80)
        target_port = params['port']
        namespace = params['namespace']
        service_type = params.get('service_type', 'ClusterIP')
        
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
    
    def _generate_hpa(self, params: Dict[str, any]) -> str:
        """Generate HorizontalPodAutoscaler manifest."""
        name = params['name']
        namespace = params['namespace']
        min_replicas = params.get('min_replicas', 2)
        max_replicas = params.get('max_replicas', 10)
        cpu_target = params.get('cpu_target', 70)
        
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
    
    def _generate_ingress(self, params: Dict[str, any]) -> str:
        """Generate Ingress manifest."""
        name = params['name']
        host = params['host']
        namespace = params['namespace']
        service_port = params.get('service_port', 80)
        tls = params.get('tls', False)
        
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


class IterativeRefinementEngine:
    """Handles iterative refinement of Kubernetes manifests."""
    
    def __init__(self):
        self.generator = KubernetesManifestGenerator()
    
    def refine_manifest(self, current_manifest: str, feedback: str) -> str:
        """Apply feedback to refine the current manifest."""
        # Parse the current manifest to understand its structure
        try:
            docs = list(yaml.safe_load_all(current_manifest))
        except yaml.YAMLError:
            return current_manifest  # Return original if parsing fails
        
        # Apply feedback transformations
        refined_docs = []
        for doc in docs:
            if isinstance(doc, dict) and 'kind' in doc:
                refined_doc = self._apply_feedback_to_resource(doc, feedback)
                refined_docs.append(refined_doc)
            else:
                refined_docs.append(doc)
        
        # Convert back to YAML string
        return "---\n".join([yaml.dump(doc, default_flow_style=False) for doc in refined_docs])
    
    def _apply_feedback_to_resource(self, resource: Dict, feedback: str) -> Dict:
        """Apply specific feedback to a Kubernetes resource."""
        feedback_lower = feedback.lower()
        resource_copy = resource.copy()
        
        # Handle common feedback patterns
        if 'increase replicas' in feedback_lower:
            if resource_copy.get('kind') == 'Deployment':
                current_replicas = resource_copy.get('spec', {}).get('replicas', 1)
                resource_copy['spec']['replicas'] = current_replicas + 1
        
        elif 'decrease replicas' in feedback_lower:
            if resource_copy.get('kind') == 'Deployment':
                current_replicas = resource_copy.get('spec', {}).get('replicas', 1)
                resource_copy['spec']['replicas'] = max(1, current_replicas - 1)
        
        elif 'add resource limits' in feedback_lower or 'add resources' in feedback_lower:
            if resource_copy.get('kind') == 'Deployment':
                containers = resource_copy.get('spec', {}).get('template', {}).get('spec', {}).get('containers', [])
                for container in containers:
                    if 'resources' not in container:
                        container['resources'] = {
                            'requests': {'cpu': '100m', 'memory': '128Mi'},
                            'limits': {'cpu': '500m', 'memory': '512Mi'}
                        }
        
        elif 'add security' in feedback_lower or 'production' in feedback_lower:
            if resource_copy.get('kind') == 'Deployment':
                # Add security context
                if 'securityContext' not in resource_copy.get('spec', {}).get('template', {}).get('spec', {}):
                    resource_copy['spec']['template']['spec']['securityContext'] = {
                        'runAsNonRoot': True,
                        'runAsUser': 1000,
                        'fsGroup': 1000,
                        'seccompProfile': {'type': 'RuntimeDefault'}
                    }
                
                # Add container security context
                containers = resource_copy.get('spec', {}).get('template', {}).get('spec', {}).get('containers', [])
                for container in containers:
                    if 'securityContext' not in container:
                        container['securityContext'] = {
                            'allowPrivilegeEscalation': False,
                            'readOnlyRootFilesystem': True,
                            'capabilities': {'drop': ['ALL']}
                        }
        
        elif 'change service type' in feedback_lower:
            if resource_copy.get('kind') == 'Service':
                if 'loadbalancer' in feedback_lower:
                    resource_copy['spec']['type'] = 'LoadBalancer'
                elif 'nodeport' in feedback_lower:
                    resource_copy['spec']['type'] = 'NodePort'
                elif 'clusterip' in feedback_lower:
                    resource_copy['spec']['type'] = 'ClusterIP'
        
        return resource_copy


def main():
    parser = argparse.ArgumentParser(
        description="AI-Assisted Kubernetes Manifest Generator - Convert natural language to YAML"
    )
    
    parser.add_argument(
        "--describe", 
        required=True, 
        help="Natural language description of the deployment"
    )
    parser.add_argument(
        "--refine", 
        help="Feedback to refine an existing manifest"
    )
    parser.add_argument(
        "--validate", 
        action="store_true", 
        help="Run validation after generation"
    )
    parser.add_argument(
        "--output", 
        help="Output file path (default: stdout)"
    )
    
    args = parser.parse_args()
    
    generator = KubernetesManifestGenerator()
    refiner = IterativeRefinementEngine()
    
    if args.refine:
        # Refine an existing manifest
        with open(args.refine, 'r') as f:
            current_manifest = f.read()
        refined_manifest = refiner.refine_manifest(current_manifest, args.describe)
        output = refined_manifest
    else:
        # Generate new manifest from natural language
        output = generator.generate_from_natural_language(args.describe)
    
    # Output the result
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"Manifest written to {args.output}")
    else:
        print(output)
    
    # Run validation if requested
    if args.validate:
        print("\n" + "="*50)
        print("VALIDATION SUMMARY")
        print("="*50)
        print("To validate this deployment, run:")
        print("kubectl apply -f <manifest-file>")
        print("./validate-deployment.sh <deployment-name> <namespace>")


if __name__ == "__main__":
    main()