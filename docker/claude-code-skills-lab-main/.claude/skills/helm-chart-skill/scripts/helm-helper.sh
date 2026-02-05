#!/bin/bash
# Helm Chart Helper Script
# Provides common Helm operations for chart development and management

set -euo pipefail

show_help() {
    echo "Helm Chart Helper Script"
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  create-chart <name>     Create a new Helm chart with best practices"
    echo "  lint-chart            Lint the current chart directory"
    echo "  template-local        Render templates locally for inspection"
    echo "  package-chart         Package the chart for distribution"
    echo "  test-install          Test install chart to current namespace"
    echo "  production-ready      Apply production best practices to chart"
    echo "  help                  Show this help message"
    echo ""
}

create_chart() {
    local chart_name="$1"

    if [[ -z "$chart_name" ]]; then
        echo "Error: Chart name is required"
        echo "Usage: $0 create-chart <name>"
        exit 1
    fi

    echo "Creating Helm chart: $chart_name"
    helm create "$chart_name"

    echo "Applying best practices to chart..."
    cd "$chart_name"

    # Update Chart.yaml with better defaults
    cat > Chart.yaml << 'EOF'
apiVersion: v2
name: CHART_NAME_PLACEHOLDER
description: A Helm chart for Kubernetes
type: application
version: 0.1.0
appVersion: "1.0.0"
keywords:
  - application
home: https://example.com
sources:
  - https://github.com/example/charts
maintainers:
  - name: Maintainer Name
    email: maintainer@example.com
icon: https://example.com/icon.png
EOF

    # Replace placeholder with actual chart name
    sed -i "s/CHART_NAME_PLACEHOLDER/$chart_name/g" Chart.yaml

    # Create production values
    cat > values-prod.yaml << 'EOF'
# Production values
replicaCount: 3

image:
  repository: nginx
  pullPolicy: IfNotPresent
  tag: "latest"

imagePullSecrets: []
nameOverride: ""
fullnameOverride: ""

serviceAccount:
  create: true
  annotations: {}
  name: ""

podAnnotations: {}

podSecurityContext: {}
  # fsGroup: 2000

securityContext: {}
  # capabilities:
  #   drop:
  #   - ALL
  # readOnlyRootFilesystem: true
  # runAsNonRoot: true
  # runAsUser: 1000

service:
  type: ClusterIP
  port: 80

ingress:
  enabled: false
  className: ""
  annotations: {}
    # kubernetes.io/ingress.class: nginx
    # kubernetes.io/tls-acme: "true"
  hosts:
    - host: chart-example.local
      paths:
        - path: /
          pathType: ImplementationSpecific
  tls: []
  #  - secretName: chart-example-tls
  #    hosts:
  #      - chart-example.local

resources:
  limits:
    cpu: 100m
    memory: 128Mi
  requests:
    cpu: 100m
    memory: 128Mi

autoscaling:
  enabled: false
  minReplicas: 1
  maxReplicas: 100
  targetCPUUtilizationPercentage: 80
  # targetMemoryUtilizationPercentage: 80

nodeSelector: {}

tolerations: []

affinity: {}
EOF

    echo "Created chart '$chart_name' with production-ready defaults"
}

lint_chart() {
    echo "Linting chart in current directory..."
    helm lint
    echo "Linting completed successfully"
}

template_local() {
    echo "Rendering templates locally..."
    helm template . --debug
}

package_chart() {
    echo "Packaging chart..."
    helm package .
    echo "Chart packaged successfully"
}

test_install() {
    local release_name="test-${RANDOM}"
    echo "Testing chart installation as release: $release_name"
    helm install "$release_name" . --dry-run --debug
    echo "Test installation completed (dry-run only)"
}

production_ready() {
    echo "Applying production best practices..."

    # Check if Chart.yaml exists
    if [[ ! -f Chart.yaml ]]; then
        echo "Error: Chart.yaml not found in current directory"
        exit 1
    fi

    # Add security contexts and production defaults to values.yaml
    cat >> values.yaml << 'EOF'

# Production defaults
resources:
  limits:
    cpu: 200m
    memory: 256Mi
  requests:
    cpu: 100m
    memory: 128Mi

autoscaling:
  enabled: false
  minReplicas: 1
  maxReplicas: 10
  targetCPUUtilizationPercentage: 80

podSecurityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 2000

securityContext:
  capabilities:
    drop:
      - ALL
  readOnlyRootFilesystem: false
  runAsNonRoot: true
  runAsUser: 1000

nodeSelector: {}

tolerations: []

affinity: {}
EOF

    # Create NOTES.txt for better user experience
    mkdir -p templates
    cat > templates/NOTES.txt << 'EOF'
1. Get the application URL by running these commands:
{{- if .Values.ingress.enabled }}
{{- range $host := .Values.ingress.hosts }}
  http{{ if $.Values.ingress.tls }}s{{ end }}://{{ $host.host }}{{ range $path := $host.paths }}
    {{ $path.path }}
  {{- end }}
{{- else if contains "NodePort" .Values.service.type }}
  export NODE_PORT=$(kubectl get --namespace {{ .Release.Namespace }} -o jsonpath="{.spec.ports[0].nodePort}" services {{ include "mychart.fullname" . }})
  export NODE_IP=$(kubectl get nodes --namespace {{ .Release.Namespace }} -o jsonpath="{.items[0].status.addresses[0].address}")
  echo http://$NODE_IP:$NODE_PORT
{{- else if contains "LoadBalancer" .Values.service.type }}
     NOTE: It may take a few minutes for the LoadBalancer IP to be available.
           You can watch the status of by running 'kubectl get --namespace {{ .Release.Namespace }} svc -w {{ include "mychart.fullname" . }}'
  export SERVICE_IP=$(kubectl get svc --namespace {{ .Release.Namespace }} {{ include "mychart.fullname" . }} --template "{{"{{ range (index .status.loadBalancer.ingress 0) }}{{.}}{{ end }}"}}")
  echo http://$SERVICE_IP:{{ .Values.service.port }}
{{- else if contains "ClusterIP" .Values.service.type }}
  export POD_NAME=$(kubectl get pods --namespace {{ .Release.Namespace }} -l "app.kubernetes.io/name={{ include "mychart.name" . }},app.kubernetes.io/instance={{ .Release.Name }}" -o jsonpath="{.items[0].metadata.name}")
  export CONTAINER_PORT=$(kubectl get pod --namespace {{ .Release.Namespace }} $POD_NAME -o jsonpath="{.spec.containers[0].ports[0].containerPort}")
  echo "Visit http://127.0.0.1:8080 to use your application"
  kubectl --namespace {{ .Release.Namespace }} port-forward $POD_NAME 8080:$CONTAINER_PORT
{{- end }}
EOF

    echo "Applied production best practices to chart"
}

case "${1:-help}" in
    create-chart)
        create_chart "${2:-}"
        ;;
    lint-chart)
        lint_chart
        ;;
    template-local)
        template_local
        ;;
    package-chart)
        package_chart
        ;;
    test-install)
        test_install
        ;;
    production-ready)
        production_ready
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "Unknown command: $1"
        show_help
        exit 1
        ;;
esac