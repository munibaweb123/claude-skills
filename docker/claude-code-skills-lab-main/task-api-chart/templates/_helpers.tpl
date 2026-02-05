{{/*
Expand the name of the chart.
*/}}
{{- define "task-api-chart.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "task-api-chart.fullname" -}}
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
{{- define "task-api-chart.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "task-api-chart.labels" -}}
helm.sh/chart: {{ include "task-api-chart.chart" . }}
{{ include "task-api-chart.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "task-api-chart.selectorLabels" -}}
app.kubernetes.io/name: {{ include "task-api-chart.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "task-api-chart.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "task-api-chart.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Generate the full container image string
Usage: {{ include "task-api-chart.image" . }}
*/}}
{{- define "task-api-chart.image" -}}
{{- $registry := .Values.image.registry | default "" }}
{{- $repository := .Values.image.repository | required "image.repository is required" }}
{{- $tag := .Values.image.tag | default .Chart.AppVersion }}
{{- if $registry }}
{{- printf "%s/%s:%s" $registry $repository $tag }}
{{- else }}
{{- printf "%s:%s" $repository $tag }}
{{- end }}
{{- end }}

{{/*
Create resource name with custom suffix
Usage: {{ include "task-api-chart.resourceName" (dict "context" . "suffix" "cache") }}
Example output: myrelease-task-api-cache
*/}}
{{- define "task-api-chart.resourceName" -}}
{{- $fullname := include "task-api-chart.fullname" .context -}}
{{- printf "%s-%s" $fullname .suffix | trunc 63 | trimSuffix "-" -}}
{{- end }}

{{/*
Return the appropriate apiVersion for Ingress
Handles Kubernetes version compatibility
*/}}
{{- define "task-api-chart.ingress.apiVersion" -}}
{{- if semverCompare ">=1.19-0" .Capabilities.KubeVersion.GitVersion }}
{{- print "networking.k8s.io/v1" }}
{{- else if semverCompare ">=1.14-0" .Capabilities.KubeVersion.GitVersion }}
{{- print "networking.k8s.io/v1beta1" }}
{{- else }}
{{- print "extensions/v1beta1" }}
{{- end }}
{{- end }}

{{/*
Return the appropriate apiVersion for HorizontalPodAutoscaler
*/}}
{{- define "task-api-chart.hpa.apiVersion" -}}
{{- if semverCompare ">=1.23-0" .Capabilities.KubeVersion.GitVersion }}
{{- print "autoscaling/v2" }}
{{- else }}
{{- print "autoscaling/v2beta2" }}
{{- end }}
{{- end }}

{{/*
Common annotations for all resources
Merges default annotations with custom ones from values
*/}}
{{- define "task-api-chart.commonAnnotations" -}}
{{- if .Values.commonAnnotations }}
{{- range $key, $value := .Values.commonAnnotations }}
{{ $key }}: {{ $value | quote }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Environment-specific replicas
Returns replica count based on environment
*/}}
{{- define "task-api-chart.replicas" -}}
{{- if .Values.environment }}
{{- if eq .Values.environment "production" }}
{{- .Values.replicaCount | default 3 }}
{{- else if eq .Values.environment "staging" }}
{{- .Values.replicaCount | default 2 }}
{{- else }}
{{- .Values.replicaCount | default 1 }}
{{- end }}
{{- else }}
{{- .Values.replicaCount | default 1 }}
{{- end }}
{{- end }}

{{/*
=========================================================================
POSTGRESQL DEPENDENCY HELPERS
=========================================================================
*/}}

{{/*
PostgreSQL hostname
Returns the PostgreSQL service hostname (internal or external)
*/}}
{{- define "task-api-chart.postgresql.host" -}}
{{- if .Values.postgresql.enabled }}
{{- printf "%s-postgresql" .Release.Name }}
{{- else }}
{{- required "externalDatabase.host is required when postgresql.enabled=false" .Values.externalDatabase.host }}
{{- end }}
{{- end }}

{{/*
PostgreSQL port
Returns the PostgreSQL service port
*/}}
{{- define "task-api-chart.postgresql.port" -}}
{{- if .Values.postgresql.enabled }}
{{- .Values.postgresql.service.ports.postgresql | default 5432 }}
{{- else }}
{{- .Values.externalDatabase.port | default 5432 }}
{{- end }}
{{- end }}

{{/*
PostgreSQL username
Returns the PostgreSQL username
*/}}
{{- define "task-api-chart.postgresql.username" -}}
{{- if .Values.postgresql.enabled }}
{{- .Values.postgresql.auth.username | default "postgres" }}
{{- else }}
{{- required "externalDatabase.username is required when postgresql.enabled=false" .Values.externalDatabase.username }}
{{- end }}
{{- end }}

{{/*
PostgreSQL database name
Returns the PostgreSQL database name
*/}}
{{- define "task-api-chart.postgresql.database" -}}
{{- if .Values.postgresql.enabled }}
{{- .Values.postgresql.auth.database | default "tasks" }}
{{- else }}
{{- required "externalDatabase.database is required when postgresql.enabled=false" .Values.externalDatabase.database }}
{{- end }}
{{- end }}

{{/*
PostgreSQL secret name
Returns the name of the secret containing PostgreSQL password
*/}}
{{- define "task-api-chart.postgresql.secretName" -}}
{{- if .Values.postgresql.enabled }}
{{- printf "%s-postgresql" .Release.Name }}
{{- else }}
{{- include "task-api-chart.fullname" . }}-external-db
{{- end }}
{{- end }}

{{/*
PostgreSQL secret key
Returns the key name in the secret for PostgreSQL password
*/}}
{{- define "task-api-chart.postgresql.secretKey" -}}
{{- if .Values.postgresql.enabled }}
{{- "password" }}
{{- else }}
{{- "password" }}
{{- end }}
{{- end }}

{{/*
PostgreSQL connection URL
Generates the full PostgreSQL connection string
Usage: {{ include "task-api-chart.postgresql.url" . }}
*/}}
{{- define "task-api-chart.postgresql.url" -}}
{{- $host := include "task-api-chart.postgresql.host" . }}
{{- $port := include "task-api-chart.postgresql.port" . }}
{{- $user := include "task-api-chart.postgresql.username" . }}
{{- $db := include "task-api-chart.postgresql.database" . }}
{{- printf "postgresql://%s@%s:%v/%s" $user $host $port $db }}
{{- end }}

{{/*
=========================================================================
REDIS DEPENDENCY HELPERS
=========================================================================
*/}}

{{/*
Redis hostname
Returns the Redis service hostname (internal or external)
*/}}
{{- define "task-api-chart.redis.host" -}}
{{- if .Values.redis.enabled }}
{{- printf "%s-redis-master" .Release.Name }}
{{- else }}
{{- required "externalRedis.host is required when redis.enabled=false" .Values.externalRedis.host }}
{{- end }}
{{- end }}

{{/*
Redis port
Returns the Redis service port
*/}}
{{- define "task-api-chart.redis.port" -}}
{{- if .Values.redis.enabled }}
{{- .Values.redis.service.ports.redis | default 6379 }}
{{- else }}
{{- .Values.externalRedis.port | default 6379 }}
{{- end }}
{{- end }}

{{/*
Redis secret name
Returns the name of the secret containing Redis password
*/}}
{{- define "task-api-chart.redis.secretName" -}}
{{- if .Values.redis.enabled }}
{{- printf "%s-redis" .Release.Name }}
{{- else }}
{{- include "task-api-chart.fullname" . }}-external-redis
{{- end }}
{{- end }}

{{/*
Redis secret key
Returns the key name in the secret for Redis password
*/}}
{{- define "task-api-chart.redis.secretKey" -}}
{{- if .Values.redis.enabled }}
{{- "redis-password" }}
{{- else }}
{{- "password" }}
{{- end }}
{{- end }}

{{/*
Redis connection URL
Generates the full Redis connection string
Usage: {{ include "task-api-chart.redis.url" . }}
*/}}
{{- define "task-api-chart.redis.url" -}}
{{- $host := include "task-api-chart.redis.host" . }}
{{- $port := include "task-api-chart.redis.port" . }}
{{- if .Values.redis.auth.enabled }}
{{- printf "redis://:%s@%s:%v/0" "$(REDIS_PASSWORD)" $host $port }}
{{- else }}
{{- printf "redis://%s:%v/0" $host $port }}
{{- end }}
{{- end }}
