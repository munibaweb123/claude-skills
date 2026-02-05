# Helm Template Helpers (_helpers.tpl)

## Overview

The `_helpers.tpl` file contains reusable named templates that promote consistency and reduce duplication across your Helm chart templates. This file follows special Helm conventions for defining and using helper functions.

## Naming Conventions

### Standard Pattern: `chartname.component`

Helper templates should follow the naming pattern: `{{ chartname }}.{{ component }}`

```yaml
{{- define "mychart.name" -}}          # Chart name
{{- define "mychart.fullname" -}}      # Full resource name
{{- define "mychart.labels" -}}        # Common labels
{{- define "mychart.selectorLabels" -}}  # Pod selector labels
{{- define "myapp.serviceAccountName" -}}  # Service account name
{{- define "myapp.databaseUrl" -}}     # Database URL helper
```

**Why this pattern?**
- Prevents naming collisions across charts
- Makes it clear which chart a helper belongs to
- Follows Helm community conventions
- Enables safe chart composition with subcharts

### Bad Examples (Avoid)

```yaml
{{- define "labels" -}}              # Too generic, collision risk
{{- define "get-name" -}}            # Unclear ownership
{{- define "MyChart.Name" -}}        # Wrong case (use lowercase)
{{- define "my_chart.name" -}}       # Use hyphens, not underscores
```

## Template vs Include

### Use `include` (Recommended)

`include` allows you to pipe the output to other functions and provides better composability.

```yaml
# GOOD: include allows piping to nindent
metadata:
  labels:
    {{- include "mychart.labels" . | nindent 4 }}
```

### Avoid `template` (Legacy)

`template` cannot be piped to other functions, limiting its utility.

```yaml
# BAD: template cannot be piped
metadata:
  labels:
{{ template "mychart.labels" . }}  # No control over indentation
```

**When to use each:**
- **`include`**: 99% of the time - default choice
- **`template`**: Only for NOTES.txt or when output doesn't need processing

## Indentation with nindent

### The nindent Function

`nindent N` adds N spaces of indentation **and** a newline before the content.

```yaml
# Without nindent (manual, error-prone)
metadata:
  labels:
{{ include "mychart.labels" . | indent 4 }}

# With nindent (correct, recommended)
metadata:
  labels:
    {{- include "mychart.labels" . | nindent 4 }}
```

### Common Indentation Levels

```yaml
# 2 spaces - YAML maps at first level
annotations:
  {{- toYaml .Values.annotations | nindent 2 }}

# 4 spaces - Nested under metadata
metadata:
  labels:
    {{- include "mychart.labels" . | nindent 4 }}

# 6 spaces - Nested selector labels
selector:
  matchLabels:
    {{- include "mychart.selectorLabels" . | nindent 6 }}

# 8 spaces - Pod template labels
spec:
  template:
    metadata:
      labels:
        {{- include "mychart.labels" . | nindent 8 }}

# 12 spaces - Container-level configurations
containers:
  - name: {{ .Chart.Name }}
    resources:
      {{- toYaml .Values.resources | nindent 12 }}
```

### indent vs nindent

```yaml
# indent N - Just adds spaces, no newline
{{ include "mychart.labels" . | indent 4 }}

# nindent N - Adds newline + spaces (preferred)
{{- include "mychart.labels" . | nindent 4 }}
```

**Rule of thumb:** Almost always use `nindent` with `include` or `toYaml`.

## Context Passing

### The Dot (.) - Current Context

The `.` (dot) represents the current scope/context.

```yaml
# At root level, . contains everything
{{- define "mychart.fullname" -}}
{{ .Release.Name }}  # Access Release info from root context
{{ .Chart.Name }}    # Access Chart info from root context
{{ .Values.image }}  # Access Values from root context
{{- end }}
```

### Passing Context to Helpers

Always pass context when calling helpers:

```yaml
# CORRECT: Pass the dot
{{- include "mychart.labels" . }}

# WRONG: No context passed
{{- include "mychart.labels" }}  # Will fail, template can't access .Release, .Chart, etc.
```

### The Dollar ($) - Root Context

Inside `range` or `with` blocks, `.` changes. Use `$` to access root.

```yaml
# Problem: Inside range, . is the current item
{{- range .Values.ingress.hosts }}
  host: {{ .host }}  # . is the current host object
  serviceName: {{ .Release.Name }}-service  # ERROR! . doesn't have .Release
{{- end }}

# Solution: Use $ to access root context
{{- range .Values.ingress.hosts }}
  host: {{ .host }}  # . is the current host object
  serviceName: {{ $.Release.Name }}-service  # $ is root context
{{- end }}
```

### Advanced Context Passing

```yaml
# Pass modified context with dict
{{- include "mychart.labels" (dict "Release" .Release "Chart" .Chart "extraLabel" "value") }}

# Store root in variable for clarity
{{- $root := . -}}
{{- range .Values.services }}
  name: {{ include "mychart.fullname" $root }}-{{ .name }}
{{- end }}
```

## Common Helper Patterns

### Complete _helpers.tpl Template

```yaml
{{/*
Expand the name of the chart.
*/}}
{{- define "mychart.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
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
{{- with .Values.commonLabels }}
{{ toYaml . }}
{{- end }}
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

{{/*
Return the appropriate apiVersion for ingress
*/}}
{{- define "mychart.ingress.apiVersion" -}}
{{- if semverCompare ">=1.19-0" .Capabilities.KubeVersion.GitVersion }}
{{- print "networking.k8s.io/v1" }}
{{- else if semverCompare ">=1.14-0" .Capabilities.KubeVersion.GitVersion }}
{{- print "networking.k8s.io/v1beta1" }}
{{- else }}
{{- print "extensions/v1beta1" }}
{{- end }}
{{- end }}

{{/*
Return the appropriate apiVersion for HPA
*/}}
{{- define "mychart.hpa.apiVersion" -}}
{{- if semverCompare ">=1.23-0" .Capabilities.KubeVersion.GitVersion }}
{{- print "autoscaling/v2" }}
{{- else }}
{{- print "autoscaling/v2beta2" }}
{{- end }}
{{- end }}

{{/*
Create a default image pull secret name
*/}}
{{- define "mychart.imagePullSecretName" -}}
{{- printf "%s-registry" (include "mychart.fullname" .) }}
{{- end }}

{{/*
Generate container image string
*/}}
{{- define "mychart.image" -}}
{{- $registry := .Values.image.registry | default "docker.io" }}
{{- $repository := .Values.image.repository | required "image.repository is required" }}
{{- $tag := .Values.image.tag | default .Chart.AppVersion }}
{{- printf "%s/%s:%s" $registry $repository $tag }}
{{- end }}

{{/*
Generate database URL from components
*/}}
{{- define "mychart.databaseUrl" -}}
{{- $host := .Values.database.host | required "database.host is required" }}
{{- $port := .Values.database.port | default 5432 }}
{{- $name := .Values.database.name | required "database.name is required" }}
{{- $user := .Values.database.user | required "database.user is required" }}
{{- printf "postgresql://%s@%s:%d/%s" $user $host (int $port) $name }}
{{- end }}
```

### Advanced Patterns

#### Conditional Labels

```yaml
{{/*
Add extra labels from values with validation
*/}}
{{- define "mychart.extraLabels" -}}
{{- if .Values.extraLabels }}
{{- range $key, $value := .Values.extraLabels }}
{{ $key }}: {{ $value | quote }}
{{- end }}
{{- end }}
{{- end }}
```

#### Annotations with Defaults

```yaml
{{/*
Service annotations with ingress-specific defaults
*/}}
{{- define "mychart.serviceAnnotations" -}}
{{- if eq .Values.service.type "LoadBalancer" }}
service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
{{- end }}
{{- with .Values.service.annotations }}
{{ toYaml . }}
{{- end }}
{{- end }}
```

#### Resource Name with Suffix

```yaml
{{/*
Create resource name with custom suffix
Usage: {{ include "mychart.resourceName" (dict "context" . "suffix" "cache") }}
*/}}
{{- define "mychart.resourceName" -}}
{{- $fullname := include "mychart.fullname" .context -}}
{{- printf "%s-%s" $fullname .suffix | trunc 63 | trimSuffix "-" -}}
{{- end }}
```

#### Environment-Specific Configuration

```yaml
{{/*
Get configuration based on environment
*/}}
{{- define "mychart.environmentConfig" -}}
{{- if eq .Values.environment "production" }}
replicas: 5
logLevel: "ERROR"
{{- else if eq .Values.environment "staging" }}
replicas: 2
logLevel: "WARN"
{{- else }}
replicas: 1
logLevel: "DEBUG"
{{- end }}
{{- end }}
```

## Usage in Templates

### Deployment Example

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "mychart.fullname" . }}
  labels:
    {{- include "mychart.labels" . | nindent 4 }}
spec:
  selector:
    matchLabels:
      {{- include "mychart.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      labels:
        {{- include "mychart.labels" . | nindent 8 }}
    spec:
      serviceAccountName: {{ include "mychart.serviceAccountName" . }}
      containers:
        - name: {{ .Chart.Name }}
          image: {{ include "mychart.image" . }}
```

### Service Example

```yaml
apiVersion: v1
kind: Service
metadata:
  name: {{ include "mychart.fullname" . }}
  labels:
    {{- include "mychart.labels" . | nindent 4 }}
  annotations:
    {{- include "mychart.serviceAnnotations" . | nindent 4 }}
spec:
  selector:
    {{- include "mychart.selectorLabels" . | nindent 4 }}
```

## Best Practices

1. **Always use chartname prefix**: Prevents collisions in subchart scenarios
2. **Prefer include over template**: Better composability with pipes
3. **Always use nindent**: Consistent, correct indentation
4. **Pass context explicitly**: Always pass `.` to helpers
5. **Use $ in loops**: Access root context inside range/with blocks
6. **Document helpers**: Add comments explaining complex helpers
7. **Keep helpers focused**: One responsibility per helper
8. **Validate inputs**: Use `required` for mandatory values
9. **Provide defaults**: Use `default` for optional values
10. **Test thoroughly**: Use `helm template` to verify output

## Common Mistakes to Avoid

### ❌ Missing Context

```yaml
# WRONG
{{- include "mychart.labels" }}

# CORRECT
{{- include "mychart.labels" . }}
```

### ❌ Wrong Indentation Function

```yaml
# WRONG (no newline)
labels:
  {{- include "mychart.labels" . | indent 2 }}

# CORRECT (newline + indent)
labels:
  {{- include "mychart.labels" . | nindent 2 }}
```

### ❌ Losing Root Context in Loops

```yaml
# WRONG
{{- range .Values.hosts }}
  name: {{ .Release.Name }}  # .Release doesn't exist here
{{- end }}

# CORRECT
{{- range .Values.hosts }}
  name: {{ $.Release.Name }}  # $ accesses root
{{- end }}
```

### ❌ Not Truncating Names

```yaml
# WRONG (can exceed 63 char limit)
{{- define "mychart.fullname" -}}
{{ .Release.Name }}-{{ .Chart.Name }}
{{- end }}

# CORRECT (truncates to DNS safe length)
{{- define "mychart.fullname" -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" }}
{{- end }}
```

## Testing Helpers

```bash
# Render templates locally to test helpers
helm template myrelease ./mychart --debug

# Test specific values
helm template myrelease ./mychart \
  --set fullnameOverride="custom-name" \
  --debug

# Test with different environments
helm template myrelease ./mychart \
  -f values-prod.yaml \
  --debug
```

## Quick Reference

| Concept | Syntax | Purpose |
|---------|--------|---------|
| Define helper | `{{- define "name" -}}...{{- end }}` | Create reusable template |
| Include helper | `{{- include "name" . }}` | Use template with context |
| Root context | `.` (dot) | Current scope |
| Parent context | `$` (dollar) | Original root scope |
| Indent | `\| nindent 4` | Add newline + 4 spaces |
| Context passing | `include "name" .` | Pass scope to template |
| Naming | `chartname.component` | Standard naming convention |
