#!/usr/bin/env python3
"""
Advanced Helm Chart Generator
Creates production-ready Helm charts with best practices
"""

import os
import yaml
import argparse
from pathlib import Path
import subprocess
from typing import Dict, Any, List

def create_production_deployment_template(chart_name: str) -> str:
    """Create a production-ready deployment template with best practices."""
    return f'''apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{{{ include "{chart_name}.fullname" . }}}}
  labels:
    {{{{- include "{chart_name}.labels" . | nindent 4 }}}}
spec:
  replicas: {{{{ .Values.replicaCount | default 1 }}}}
  selector:
    matchLabels:
      {{{{- include "{chart_name}.selectorLabels" . | nindent 6 }}}}
  template:
    metadata:
      annotations:
        checksum/config: {{{{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}}}
      labels:
        {{{{- include "{chart_name}.selectorLabels" . | nindent 8 }}}}
    spec:
      {{- with .Values.imagePullSecrets }}
      imagePullSecrets:
        {{{{- toYaml . | nindent 8 }}}}
      {{- end }}
      serviceAccountName: {{{{ include "{chart_name}.serviceAccountName" . }}}}
      securityContext:
        {{{{- toYaml .Values.podSecurityContext | nindent 8 }}}}
      containers:
        - name: {{{{ .Chart.Name }}}}
          securityContext:
            {{{{- toYaml .Values.securityContext | nindent 12 }}}}
          image: "{{{{ .Values.image.repository }}}}{{{{ .Values.image.tag | default .Chart.AppVersion }}}}"
          imagePullPolicy: {{{{ .Values.image.pullPolicy }}}}
          ports:
            - name: http
              containerPort: 80
              protocol: TCP
          livenessProbe:
            httpGet:
              path: /
              port: http
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /
              port: http
            initialDelaySeconds: 5
            periodSeconds: 5
          resources:
            {{{{- toYaml .Values.resources | nindent 12 }}}}
          {{- with .Values.volumeMounts }}
          volumeMounts:
            {{{{- toYaml . | nindent 12 }}}}
          {{- end }}
      {{- with .Values.volumes }}
      volumes:
        {{{{- toYaml . | nindent 8 }}}}
      {{- end }}
      {{- with .Values.nodeSelector }}
      nodeSelector:
        {{{{- toYaml . | nindent 8 }}}}
      {{- end }}
      {{- with .Values.affinity }}
      affinity:
        {{{{- toYaml . | nindent 8 }}}}
      {{- end }}
      {{- with .Values.tolerations }}
      tolerations:
        {{{{- toYaml . | nindent 8 }}}}
      {{- end }}
'''

def create_production_service_template() -> str:
    """Create a production-ready service template."""
    return '''apiVersion: v1
kind: Service
metadata:
  name: {{{{ include "{{ .Chart.Name }}.fullname" . }}}}
  labels:
    {{{{- include "{{ .Chart.Name }}.labels" . | nindent 4 }}}}
spec:
  type: {{{{ .Values.service.type }}}}
  ports:
    - port: {{{{ .Values.service.port }}}}
      targetPort: http
      protocol: TCP
      name: http
  selector:
    {{{{- include "{{ .Chart.Name }}.selectorLabels" . | nindent 4 }}}}
'''

def create_horizontal_pod_autoscaler_template(chart_name: str) -> str:
    """Create an HPA template for auto-scaling."""
    return f'''{{{{- if .Values.autoscaling.enabled }}}}
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {{{{ include "{chart_name}.fullname" . }}}}
  labels:
    {{{{- include "{chart_name}.labels" . | nindent 4 }}}}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {{{{ include "{chart_name}.fullname" . }}}}
  minReplicas: {{{{ .Values.autoscaling.minReplicas }}}}
  maxReplicas: {{{{ .Values.autoscaling.maxReplicas }}}}
  metrics:
    {{- if .Values.autoscaling.targetCPUUtilizationPercentage }}
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: {{{{ .Values.autoscaling.targetCPUUtilizationPercentage }}}}
    {{- end }}
    {{- if .Values.autoscaling.targetMemoryUtilizationPercentage }}
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: {{{{ .Values.autoscaling.targetMemoryUtilizationPercentage }}}}
    {{- end }}
{{{{- end }}}}
'''

def create_ingress_template(chart_name: str) -> str:
    """Create a production-ready ingress template."""
    return f'''{{{{- if .Values.ingress.enabled }}}}
{{{{- $fullName := include "{chart_name}.fullname" . }}}}
{{{{- $svcPort := .Values.service.port }}}}
{{{{- if and .Values.ingress.className (not (semverCompare ">=1.18-0" .Capabilities.KubeVersion.GitVersion)) }}}}
  {{- if not (hasKey .Values.ingress.annotations "kubernetes.io/ingress.class") }}}
  {{- $_ := set .Values.ingress.annotations "kubernetes.io/ingress.class" .Values.ingress.className }}
  {{- end }}
{{{{- end }}}}
{{{{- if semverCompare ">=1.19-0" .Capabilities.KubeVersion.GitVersion -}}}
apiVersion: networking.k8s.io/v1
{{{{- else if semverCompare ">=1.14-0" .Capabilities.KubeVersion.GitVersion -}}}
apiVersion: networking.k8s.io/v1beta1
{{{{- else -}}}
apiVersion: extensions/v1beta1
{{{{- end }}}}
kind: Ingress
metadata:
  name: {{{{ $fullName }}}}
  labels:
    {{{{- include "{chart_name}.labels" . | nindent 4 }}}}
  {{- with .Values.ingress.annotations }}
  annotations:
    {{{{- toYaml . | nindent 4 }}}}
  {{- end }}
spec:
  {{- if and .Values.ingress.className (semverCompare ">=1.18-0" .Capabilities.KubeVersion.GitVersion) }}
  ingressClassName: {{{{ .Values.ingress.className }}}}
  {{- end }}
  {{- if .Values.ingress.tls }}
  tls:
    {{- range .Values.ingress.tls }}
    - hosts:
        {{- range .hosts }}
        - {{{{ . }}}}
        {{- end }}
      secretName: {{{{ .secretName }}}}
    {{- end }}
  {{- end }}
  rules:
    {{- range .Values.ingress.hosts }}
    - host: {{{{ .host }}}}
      http:
        paths:
          {{- range .paths }}
          - path: {{{{ .path }}}}
            {{- if and .pathType (semverCompare ">=1.18-0" .Capabilities.KubeVersion.GitVersion) }}
            pathType: {{{{ .pathType }}}}
            {{- end }}
            backend:
              {{- if semverCompare ">=1.19-0" $.Capabilities.KubeVersion.GitVersion }}
              service:
                name: {{{{ $fullName }}}}
                port:
                  number: {{{{ $svcPort }}}}
              {{- else }}
              serviceName: {{{{ $fullName }}}}
              servicePort: {{{{ $svcPort }}}}
              {{- end }}
          {{- end }}
    {{- end }}
{{{{- end }}}}
'''

def create_helpers_template(chart_name: str) -> str:
    """Create helper templates with production best practices."""
    return f'''{{/* vim: set filetype=mustache: */}}
{{/*
Expand the name of the chart.
*/}}
{{- define "{chart_name}.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "{chart_name}.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "{chart_name}.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Common labels
*/}}
{{- define "{chart_name}.labels" -}}
helm.sh/chart: {{{{ include "{chart_name}.chart" . }}}}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{{{ .Chart.AppVersion | quote }}}}
{{- end }}
app.kubernetes.io/managed-by: {{{{ .Release.Service | quote }}}}
{{- end -}}

{{/*
Selector labels
*/}}
{{- define "{chart_name}.selectorLabels" -}}
app.kubernetes.io/name: {{{{ include "{chart_name}.name" . }}}}
app.kubernetes.io/instance: {{{{ .Release.Name }}}}
{{- end -}}

{{/*
Create the name of the service account to use
*/}}
{{- define "{chart_name}.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
    {{{{ default (include "{chart_name}.fullname" .) .Values.serviceAccount.name }}}}
{{- else -}}
    {{{{ default "default" .Values.serviceAccount.name }}}}
{{- end -}}
{{- end -}}
'''

def create_production_values() -> Dict[str, Any]:
    """Return production-ready default values."""
    return {
        'replicaCount': 3,
        'image': {
            'repository': 'nginx',
            'pullPolicy': 'IfNotPresent',
            'tag': ''
        },
        'imagePullSecrets': [],
        'nameOverride': '',
        'fullnameOverride': '',
        'serviceAccount': {
            'create': True,
            'annotations': {},
            'name': ''
        },
        'podAnnotations': {},
        'podSecurityContext': {
            'fsGroup': 2000
        },
        'securityContext': {
            'capabilities': {
                'drop': ['ALL']
            },
            'readOnlyRootFilesystem': False,
            'runAsNonRoot': True,
            'runAsUser': 1000
        },
        'service': {
            'type': 'ClusterIP',
            'port': 80
        },
        'ingress': {
            'enabled': False,
            'className': '',
            'annotations': {},
            'hosts': [
                {
                    'host': 'chart-example.local',
                    'paths': [
                        {
                            'path': '/',
                            'pathType': 'ImplementationSpecific'
                        }
                    ]
                }
            ],
            'tls': []
        },
        'resources': {
            'limits': {
                'cpu': '500m',
                'memory': '512Mi'
            },
            'requests': {
                'cpu': '100m',
                'memory': '128Mi'
            }
        },
        'autoscaling': {
            'enabled': False,
            'minReplicas': 1,
            'maxReplicas': 100,
            'targetCPUUtilizationPercentage': 80
        },
        'nodeSelector': {},
        'tolerations': [],
        'affinity': {}
    }

def create_chart_yaml(name: str, description: str = "A production-ready Helm chart") -> Dict[str, Any]:
    """Create Chart.yaml content."""
    return {
        'apiVersion': 'v2',
        'name': name,
        'description': description,
        'type': 'application',
        'version': '0.1.0',
        'appVersion': '1.0.0',
        'keywords': ['production', 'best-practices'],
        'home': 'https://example.com',
        'sources': ['https://github.com/example/charts'],
        'maintainers': [
            {
                'name': 'Maintainer Name',
                'email': 'maintainer@example.com'
            }
        ]
    }

def create_production_chart(chart_name: str, output_dir: str = "."):
    """Create a complete production-ready Helm chart."""
    chart_path = Path(output_dir) / chart_name

    # Create directory structure
    chart_path.mkdir(exist_ok=True)
    templates_path = chart_path / "templates"
    templates_path.mkdir(exist_ok=True)

    # Create Chart.yaml
    with open(chart_path / "Chart.yaml", "w") as f:
        yaml.dump(create_chart_yaml(chart_name), f, default_flow_style=False)

    # Create values.yaml
    with open(chart_path / "values.yaml", "w") as f:
        yaml.dump(create_production_values(), f, default_flow_style=False)

    # Create templates
    with open(templates_path / "deployment.yaml", "w") as f:
        f.write(create_production_deployment_template(chart_name))

    with open(templates_path / "service.yaml", "w") as f:
        f.write(create_production_service_template())

    with open(templates_path / "hpa.yaml", "w") as f:
        f.write(create_horizontal_pod_autoscaler_template(chart_name))

    with open(templates_path / "ingress.yaml", "w") as f:
        f.write(create_ingress_template(chart_name))

    with open(templates_path / "_helpers.tpl", "w") as f:
        f.write(create_helpers_template(chart_name))

    # Create NOTES.txt
    with open(templates_path / "NOTES.txt", "w") as f:
        f.write('''1. Get the application URL by running these commands:
{{- if .Values.ingress.enabled }}
{{- range $host := .Values.ingress.hosts }}
  http{{ if $.Values.ingress.tls }}s{{ end }}://{{ $host.host }}{{ range $path := $host.paths }}
    {{ $path.path }}
  {{- end }}
{{- else if contains "NodePort" .Values.service.type }}
  export NODE_PORT=$(kubectl get --namespace {{ .Release.Namespace }} -o jsonpath="{.spec.ports[0].nodePort}" services {{ include "'''+chart_name+'''.fullname" . }})
  export NODE_IP=$(kubectl get nodes --namespace {{ .Release.Namespace }} -o jsonpath="{.items[0].status.addresses[0].address}")
  echo http://$NODE_IP:$NODE_PORT
{{- else if contains "LoadBalancer" .Values.service.type }}
     NOTE: It may take a few minutes for the LoadBalancer IP to be available.
           You can watch the status of by running 'kubectl get --namespace {{ .Release.Namespace }} svc -w {{ include "'''+chart_name+'''.fullname" . }}'
  export SERVICE_IP=$(kubectl get svc --namespace {{ .Release.Namespace }} {{ include "'''+chart_name+'''.fullname" . }} --template "{{"{{ range (index .status.loadBalancer.ingress 0) }}{{.}}{{ end }}"}}")
  echo http://$SERVICE_IP:{{ .Values.service.port }}
{{- else if contains "ClusterIP" .Values.service.type }}
  export POD_NAME=$(kubectl get pods --namespace {{ .Release.Namespace }} -l "app.kubernetes.io/name={{ include "'''+chart_name+'''.name" . }},app.kubernetes.io/instance={{ .Release.Name }}" -o jsonpath="{.items[0].metadata.name}")
  export CONTAINER_PORT=$(kubectl get pod --namespace {{ .Release.Namespace }} $POD_NAME -o jsonpath="{.spec.containers[0].ports[0].containerPort}")
  echo "Visit http://127.0.0.1:8080 to use your application"
  kubectl --namespace {{ .Release.Namespace }} port-forward $POD_NAME 8080:$CONTAINER_PORT
{{- end }}
''')

    print(f"Production-ready Helm chart '{chart_name}' created successfully!")
    print(f"Location: {chart_path.absolute()}")

def main():
    parser = argparse.ArgumentParser(description='Advanced Helm Chart Generator')
    parser.add_argument('action', choices=['create-production-chart'], help='Action to perform')
    parser.add_argument('--name', required=True, help='Name of the chart to create')
    parser.add_argument('--output-dir', default='.', help='Output directory for the chart')

    args = parser.parse_args()

    if args.action == 'create-production-chart':
        create_production_chart(args.name, args.output_dir)

if __name__ == "__main__":
    main()