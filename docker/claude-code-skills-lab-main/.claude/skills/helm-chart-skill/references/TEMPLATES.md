# Helm Template Functions Reference

## Complete Template Examples

### deployment.yaml (Production-Ready)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "mychart.fullname" . }}
  labels:
    {{- include "mychart.labels" . | nindent 4 }}
spec:
  {{- if not .Values.autoscaling.enabled }}
  replicas: {{ .Values.replicaCount }}
  {{- end }}
  selector:
    matchLabels:
      {{- include "mychart.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      {{- with .Values.podAnnotations }}
      annotations:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      labels:
        {{- include "mychart.labels" . | nindent 8 }}
        {{- with .Values.podLabels }}
        {{- toYaml . | nindent 8 }}
        {{- end }}
    spec:
      {{- with .Values.imagePullSecrets }}
      imagePullSecrets:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      serviceAccountName: {{ include "mychart.serviceAccountName" . }}
      securityContext:
        {{- toYaml .Values.podSecurityContext | nindent 8 }}
      containers:
        - name: {{ .Chart.Name }}
          securityContext:
            {{- toYaml .Values.securityContext | nindent 12 }}
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag | default .Chart.AppVersion }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          ports:
            - name: http
              containerPort: {{ .Values.service.targetPort | default .Values.service.port }}
              protocol: TCP
          {{- if .Values.livenessProbe }}
          livenessProbe:
            {{- toYaml .Values.livenessProbe | nindent 12 }}
          {{- end }}
          {{- if .Values.readinessProbe }}
          readinessProbe:
            {{- toYaml .Values.readinessProbe | nindent 12 }}
          {{- end }}
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
          {{- with .Values.env }}
          env:
            {{- toYaml . | nindent 12 }}
          {{- end }}
          {{- if .Values.envFrom }}
          envFrom:
            {{- if .Values.configMapRef }}
            - configMapRef:
                name: {{ include "mychart.fullname" . }}-config
            {{- end }}
            {{- if .Values.secretRef }}
            - secretRef:
                name: {{ include "mychart.fullname" . }}-secret
            {{- end }}
          {{- end }}
          {{- with .Values.volumeMounts }}
          volumeMounts:
            {{- toYaml . | nindent 12 }}
          {{- end }}
      {{- with .Values.volumes }}
      volumes:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      {{- with .Values.nodeSelector }}
      nodeSelector:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      {{- with .Values.affinity }}
      affinity:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      {{- with .Values.tolerations }}
      tolerations:
        {{- toYaml . | nindent 8 }}
      {{- end }}
```

### service.yaml (Production-Ready)

```yaml
apiVersion: v1
kind: Service
metadata:
  name: {{ include "mychart.fullname" . }}
  labels:
    {{- include "mychart.labels" . | nindent 4 }}
  {{- with .Values.service.annotations }}
  annotations:
    {{- toYaml . | nindent 4 }}
  {{- end }}
spec:
  type: {{ .Values.service.type }}
  {{- if and .Values.service.clusterIP (eq .Values.service.type "ClusterIP") }}
  clusterIP: {{ .Values.service.clusterIP }}
  {{- end }}
  {{- if and .Values.service.loadBalancerIP (eq .Values.service.type "LoadBalancer") }}
  loadBalancerIP: {{ .Values.service.loadBalancerIP }}
  {{- end }}
  ports:
    - port: {{ .Values.service.port }}
      targetPort: {{ .Values.service.targetPort | default "http" }}
      protocol: TCP
      name: http
      {{- if and (eq .Values.service.type "NodePort") .Values.service.nodePort }}
      nodePort: {{ .Values.service.nodePort }}
      {{- end }}
  selector:
    {{- include "mychart.selectorLabels" . | nindent 4 }}
```

### configmap.yaml

```yaml
{{- if .Values.config }}
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ include "mychart.fullname" . }}-config
  labels:
    {{- include "mychart.labels" . | nindent 4 }}
data:
  {{- range $key, $value := .Values.config }}
  {{ $key }}: {{ $value | quote }}
  {{- end }}
{{- end }}
```

### secret.yaml

```yaml
{{- if .Values.secrets }}
apiVersion: v1
kind: Secret
metadata:
  name: {{ include "mychart.fullname" . }}-secret
  labels:
    {{- include "mychart.labels" . | nindent 4 }}
type: Opaque
data:
  {{- range $key, $value := .Values.secrets }}
  {{ $key }}: {{ $value | b64enc | quote }}
  {{- end }}
{{- end }}
```

### ingress.yaml

```yaml
{{- if .Values.ingress.enabled -}}
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ include "mychart.fullname" . }}
  labels:
    {{- include "mychart.labels" . | nindent 4 }}
  {{- with .Values.ingress.annotations }}
  annotations:
    {{- toYaml . | nindent 4 }}
  {{- end }}
spec:
  {{- if .Values.ingress.className }}
  ingressClassName: {{ .Values.ingress.className }}
  {{- end }}
  {{- if .Values.ingress.tls }}
  tls:
    {{- range .Values.ingress.tls }}
    - hosts:
        {{- range .hosts }}
        - {{ . | quote }}
        {{- end }}
      secretName: {{ .secretName }}
    {{- end }}
  {{- end }}
  rules:
    {{- range .Values.ingress.hosts }}
    - host: {{ .host | quote }}
      http:
        paths:
          {{- range .paths }}
          - path: {{ .path }}
            pathType: {{ .pathType }}
            backend:
              service:
                name: {{ include "mychart.fullname" $ }}
                port:
                  number: {{ $.Values.service.port }}
          {{- end }}
    {{- end }}
{{- end }}
```

### hpa.yaml (Horizontal Pod Autoscaler)

```yaml
{{- if .Values.autoscaling.enabled }}
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {{ include "mychart.fullname" . }}
  labels:
    {{- include "mychart.labels" . | nindent 4 }}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {{ include "mychart.fullname" . }}
  minReplicas: {{ .Values.autoscaling.minReplicas }}
  maxReplicas: {{ .Values.autoscaling.maxReplicas }}
  metrics:
    {{- if .Values.autoscaling.targetCPUUtilizationPercentage }}
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: {{ .Values.autoscaling.targetCPUUtilizationPercentage }}
    {{- end }}
    {{- if .Values.autoscaling.targetMemoryUtilizationPercentage }}
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: {{ .Values.autoscaling.targetMemoryUtilizationPercentage }}
    {{- end }}
{{- end }}
```

### _helpers.tpl (Template Helpers)

```yaml
{{/*
Expand the name of the chart.
*/}}
{{- define "mychart.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this.
*/}}
{{- define "mychart.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "mychart.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "mychart.labels" -}}
helm.sh/chart: {{ include "mychart.chart" . }}
{{ include "mychart.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "mychart.selectorLabels" -}}
app.kubernetes.io/name: {{ include "mychart.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "mychart.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "mychart.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}
```

---

## Go Template Syntax Reference

### If/Else Conditionals

```yaml
# Basic if
{{- if .Values.enabled }}
enabled: true
{{- end }}

# If/else
{{- if .Values.production }}
replicas: 5
{{- else }}
replicas: 1
{{- end }}

# If/else if/else
{{- if eq .Values.environment "production" }}
replicas: 5
logLevel: "WARN"
{{- else if eq .Values.environment "staging" }}
replicas: 2
logLevel: "INFO"
{{- else }}
replicas: 1
logLevel: "DEBUG"
{{- end }}

# Compound conditions with 'and'
{{- if and .Values.ingress.enabled .Values.ingress.tls }}
  # TLS is configured
{{- end }}

# Compound conditions with 'or'
{{- if or .Values.serviceAccount.create .Values.serviceAccount.name }}
  # Service account exists
{{- end }}

# Negation with 'not'
{{- if not .Values.autoscaling.enabled }}
replicas: {{ .Values.replicaCount }}
{{- end }}

# Check if value exists (not empty)
{{- if .Values.annotations }}
annotations:
  {{- toYaml .Values.annotations | nindent 2 }}
{{- end }}
```

### Comparison Operators

```yaml
# Equal
{{- if eq .Values.service.type "LoadBalancer" }}

# Not equal
{{- if ne .Values.environment "production" }}

# Less than / Greater than
{{- if lt .Values.replicaCount 3 }}
{{- if gt .Values.replicaCount 1 }}

# Less/greater than or equal
{{- if le .Values.replicaCount 5 }}
{{- if ge .Values.replicaCount 2 }}
```

### Range Loops

```yaml
# Range over a list
env:
{{- range .Values.env }}
  - name: {{ .name }}
    value: {{ .value | quote }}
{{- end }}

# Range over a map/dict with key-value
data:
{{- range $key, $value := .Values.config }}
  {{ $key }}: {{ $value | quote }}
{{- end }}

# Range with index
{{- range $index, $host := .Values.ingress.hosts }}
  - host: {{ $host }}
    # index is {{ $index }}
{{- end }}

# Nested range (e.g., ingress hosts and paths)
rules:
{{- range .Values.ingress.hosts }}
  - host: {{ .host | quote }}
    http:
      paths:
      {{- range .paths }}
        - path: {{ .path }}
          pathType: {{ .pathType }}
      {{- end }}
{{- end }}

# Range with else (empty list handling)
{{- range .Values.tolerations }}
  - {{ . | toYaml | nindent 4 }}
{{- else }}
  # No tolerations defined
{{- end }}
```

### Pipelines

```yaml
# Basic pipeline
image: {{ .Values.image.repository | quote }}

# Chained pipelines
name: {{ .Chart.Name | lower | trunc 63 | trimSuffix "-" }}

# Pipeline with default
tag: {{ .Values.image.tag | default .Chart.AppVersion }}

# Pipeline with conditional default
memory: {{ .Values.resources.limits.memory | default "512Mi" | quote }}

# Complex pipeline
{{ include "mychart.fullname" . | upper | replace "-" "_" }}

# Pipeline to YAML with indentation
annotations:
  {{- .Values.podAnnotations | toYaml | nindent 2 }}
```

### Variables

```yaml
# Define a variable
{{- $fullname := include "mychart.fullname" . -}}
{{- $serviceName := printf "%s-svc" $fullname -}}

# Use the variable
name: {{ $fullname }}
serviceName: {{ $serviceName }}

# Variable in range (preserves outer scope)
{{- $root := . -}}
{{- range .Values.services }}
  name: {{ include "mychart.fullname" $root }}-{{ .name }}
{{- end }}

# Multiple variables
{{- $namespace := .Release.Namespace -}}
{{- $releaseName := .Release.Name -}}
```

### With (Scope Change)

```yaml
# 'with' changes the scope to the specified object
{{- with .Values.nodeSelector }}
nodeSelector:
  {{- toYaml . | nindent 2 }}
{{- end }}

# 'with' with else
{{- with .Values.affinity }}
affinity:
  {{- toYaml . | nindent 2 }}
{{- else }}
affinity: {}
{{- end }}

# Access parent scope with $ inside 'with'
{{- with .Values.service }}
  name: {{ $.Release.Name }}-service
  port: {{ .port }}
{{- end }}
```

### Named Templates (define/include)

```yaml
# Define a named template in _helpers.tpl
{{- define "mychart.labels" -}}
app.kubernetes.io/name: {{ include "mychart.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

# Include the template
metadata:
  labels:
    {{- include "mychart.labels" . | nindent 4 }}

# Include with modified context
{{- include "mychart.labels" (dict "Release" .Release "Chart" .Chart "customKey" "customValue") | nindent 4 }}
```

### Whitespace Control

```yaml
# {{- removes whitespace before
# -}} removes whitespace after

# No whitespace control (adds blank lines)
{{ if .Values.enabled }}
enabled: true
{{ end }}

# With whitespace control (clean output)
{{- if .Values.enabled }}
enabled: true
{{- end }}

# Mixed for specific formatting
{{- if .Values.annotations }}
annotations:
  {{- toYaml .Values.annotations | nindent 2 }}
{{- end }}
```

### Practical Examples

#### Dynamic Environment Variables
```yaml
env:
{{- range $key, $value := .Values.env }}
  - name: {{ $key }}
    value: {{ $value | quote }}
{{- end }}
{{- if .Values.secretEnv }}
{{- range $key, $secret := .Values.secretEnv }}
  - name: {{ $key }}
    valueFrom:
      secretKeyRef:
        name: {{ $secret.name }}
        key: {{ $secret.key }}
{{- end }}
{{- end }}
```

#### Conditional Resource Creation
```yaml
{{- if .Values.persistence.enabled }}
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: {{ include "mychart.fullname" . }}-data
spec:
  accessModes:
    {{- range .Values.persistence.accessModes }}
    - {{ . | quote }}
    {{- end }}
  resources:
    requests:
      storage: {{ .Values.persistence.size | quote }}
  {{- if .Values.persistence.storageClass }}
  {{- if eq .Values.persistence.storageClass "-" }}
  storageClassName: ""
  {{- else }}
  storageClassName: {{ .Values.persistence.storageClass | quote }}
  {{- end }}
  {{- end }}
{{- end }}
```

#### Multi-Container Pod
```yaml
containers:
{{- range .Values.containers }}
  - name: {{ .name }}
    image: "{{ .image.repository }}:{{ .image.tag }}"
    {{- if .ports }}
    ports:
      {{- range .ports }}
      - containerPort: {{ .containerPort }}
        {{- if .name }}
        name: {{ .name }}
        {{- end }}
      {{- end }}
    {{- end }}
    {{- if .resources }}
    resources:
      {{- toYaml .resources | nindent 6 }}
    {{- end }}
{{- end }}
```

---

## Built-in Functions

### String Functions
- `upper`, `lower`: Convert to uppercase/lowercase
- `title`: Capitalize first letter of each word
- `trim`, `trimAll`: Remove whitespace
- `split`: Split string into a list
- `join`: Join list into string
- `replace`: Replace substrings
- `quote`: Wrap in double quotes
- `regexReplaceAll`, `regexReplaceAllLiteral`: Regex replacements

### List Functions
- `list`: Create a list
- `first`, `last`, `initial`, `rest`: Access list elements
- `append`, `prepend`: Add items to lists
- `reverse`: Reverse a list
- `uniq`: Remove duplicates
- `has`: Check if item exists in list

### Dict Functions
- `dict`: Create a dictionary
- `get`: Get value from dict
- `set`: Set value in dict
- `unset`: Remove key from dict
- `hasKey`: Check if key exists
- `keys`: Get all keys
- `values`: Get all values

### Encoding Functions
- `b64enc`, `b64dec`: Base64 encode/decode
- `b32enc`, `b32dec`: Base32 encode/decode
- `sha1sum`, `sha256sum`: Hash functions

### Flow Control
- `if`, `else`, `else if`: Conditionals
- `with`: Scope changes
- `range`: Loops
- `define`, `template`, `include`: Named templates

## Template Best Practices

1. **Use helper templates** for labels to ensure consistency
2. **Quote string values** to prevent YAML parsing issues
3. **Use `toYaml`** function for complex nested structures
4. **Use `nindent`** for proper indentation
5. **Validate inputs** with conditional checks
6. **Use `required`** function to enforce required values
7. **Use `default`** for optional values with sensible defaults
