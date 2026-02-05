# Helm Dependencies Management

## Chart Dependencies Overview

Helm charts can depend on other charts, which are called subcharts. Dependencies can be managed in two ways:
1. Through the `dependencies` field in `Chart.yaml`
2. By placing dependency charts in the `charts/` directory

## Declaring Dependencies in Chart.yaml

```yaml
apiVersion: v2
name: myapp
description: A Helm chart for my application
type: application
version: 0.1.0
appVersion: "1.0.0"

dependencies:
  - name: postgresql
    version: "12.x.x"
    repository: "https://charts.bitnami.com/bitnami"
    condition: postgresql.enabled
    tags:
      - database
  - name: redis
    version: "17.x.x"
    repository: "https://charts.bitnami.com/bitnami"
    condition: redis.enabled
    tags:
      - cache
  - name: common
    version: "1.x.x"
    repository: "https://charts.bitnami.com/bitnami"
    import-values:
      - default
```

## Dependency Fields Explained

- `name`: The name of the chart (without version)
- `version`: The chart version (supports semver ranges)
- `repository`: The repository URL (prefix with @ for alias)
- `condition`: A template expression that determines if the dependency should be loaded
- `tags`: Tags to group dependencies for enabling/disabling
- `import-values`: Specifies values to import from the dependency
- `alias`: Alternative name for the dependency

## Semantic Versioning Constraints

Helm supports various version constraint formats:

### Exact Version
```yaml
dependencies:
  - name: postgresql
    version: "12.12.10"  # Exact version only
```

### Caret (^) - Compatible Updates (Minor and Patch)
Allows updates that do not change the leftmost non-zero digit.

```yaml
dependencies:
  - name: postgresql
    version: "^12.12.10"  # >=12.12.10 <13.0.0
    # Allows: 12.12.11, 12.13.0, 12.99.0
    # Blocks: 13.0.0, 11.x.x

  - name: redis
    version: "^18.4.0"   # >=18.4.0 <19.0.0
    # Allows: 18.4.1, 18.5.0, 18.99.0
    # Blocks: 19.0.0, 17.x.x
```

**When to use `^`:**
- For production: Allows non-breaking updates (bug fixes and new features)
- Recommended for most use cases
- Gets security patches and minor improvements

### Tilde (~) - Patch-Level Updates Only
Allows only patch-level updates.

```yaml
dependencies:
  - name: postgresql
    version: "~12.12.10"  # >=12.12.10 <12.13.0
    # Allows: 12.12.11, 12.12.99
    # Blocks: 12.13.0, 13.0.0

  - name: redis
    version: "~18.4.0"    # >=18.4.0 <18.5.0
    # Allows: 18.4.1, 18.4.99
    # Blocks: 18.5.0, 19.0.0
```

**When to use `~`:**
- For critical production systems
- When you want only bug fixes, no new features
- Maximum stability required

### Wildcard (x or *)
```yaml
dependencies:
  - name: postgresql
    version: "12.12.x"  # >=12.12.0 <12.13.0
    version: "12.x.x"   # >=12.0.0 <13.0.0
    version: "12.*"     # Same as 12.x.x
```

### Range Operators
```yaml
dependencies:
  # Greater than or equal
  - name: postgresql
    version: ">=12.12.10"

  # Less than
  - name: postgresql
    version: "<13.0.0"

  # Combined range
  - name: postgresql
    version: ">=12.12.10 <13.0.0"

  # OR conditions (space-separated)
  - name: postgresql
    version: "^12.12.0 || ^13.0.0"  # Either v12 or v13
```

### Best Practices by Environment

**Development:**
```yaml
dependencies:
  - name: postgresql
    version: "^12.0.0"  # Wide range for flexibility
```

**Staging:**
```yaml
dependencies:
  - name: postgresql
    version: "^12.12.0"  # Specific minor, flexible patch
```

**Production:**
```yaml
dependencies:
  - name: postgresql
    version: "12.12.10"  # Exact version for stability
    # OR
    version: "~12.12.10"  # Patch updates only
```

## Managing Dependencies

### Complete Workflow

#### 1. Add Repository
```bash
# Add the Bitnami repository
helm repo add bitnami https://charts.bitnami.com/bitnami

# Update repository index
helm repo update

# List available repositories
helm repo list
```

#### 2. Declare Dependencies in Chart.yaml
Edit your `Chart.yaml`:
```yaml
dependencies:
  - name: postgresql
    version: "^12.12.0"
    repository: "https://charts.bitnami.com/bitnami"
    condition: postgresql.enabled
  - name: redis
    version: "^18.4.0"
    repository: "https://charts.bitnami.com/bitnami"
    condition: redis.enabled
```

#### 3. Download Dependencies
```bash
# Update dependencies (downloads to charts/ directory)
helm dependency update

# Alternative: Build dependencies (same as update)
helm dependency build

# View dependency status
helm dependency list
```

**Output:**
```
NAME        VERSION    REPOSITORY                              STATUS
postgresql  12.12.10   https://charts.bitnami.com/bitnami     ok
redis       18.4.0     https://charts.bitnami.com/bitnami     ok
```

#### 4. Verify Downloaded Dependencies
```bash
# Check charts/ directory
ls -la charts/
# Output:
# postgresql-12.12.10.tgz
# redis-18.4.0.tgz

# Check Chart.lock file
cat Chart.lock
```

**Chart.lock example:**
```yaml
dependencies:
- name: postgresql
  repository: https://charts.bitnami.com/bitnami
  version: 12.12.10  # Locked to exact version
- name: redis
  repository: https://charts.bitnami.com/bitnami
  version: 18.4.0    # Locked to exact version
digest: sha256:abc123...
generated: "2024-01-15T10:30:00Z"
```

#### 5. Install with Dependencies
```bash
# Install chart with dependencies
helm install myapp ./mychart -f values.yaml

# Dependencies are automatically deployed based on conditions
```

### Updating Dependencies

When you update Chart.yaml with new versions:

```bash
# 1. Update Chart.yaml
vim Chart.yaml  # Change version: "^12.12.0" to "^13.0.0"

# 2. Update dependencies
helm dependency update

# 3. Check what changed
helm dependency list
git diff Chart.lock  # See version changes

# 4. Upgrade release
helm upgrade myapp ./mychart -f values.yaml
```

### Cleaning Dependencies

```bash
# Remove downloaded dependencies
rm -rf charts/*.tgz

# Remove lock file
rm Chart.lock

# Re-download fresh
helm dependency update
```

## Dependency Aliases

Use aliases to include the same chart multiple times:

```yaml
dependencies:
  - name: apache
    version: "8.x.x"
    repository: "https://charts.bitnami.com/bitnami"
    alias: apache-first
  - name: apache
    version: "8.x.x"
    repository: "https://charts.bitnami.com/bitnami"
    alias: apache-second
```

With aliases, you can then access the charts as:
- `apache-first` for the first instance
- `apache-second` for the second instance

## Conditional Dependencies

Dependencies can be conditionally included:

```yaml
dependencies:
  - name: mysql
    version: "8.x.x"
    repository: "https://charts.bitnami.com/bitnami"
    condition: mysql.enabled
```

Then in your values.yaml:
```yaml
mysql:
  enabled: true  # Set to false to disable the dependency
```

## Tags-Based Dependencies

Group dependencies with tags:

```yaml
dependencies:
  - name: nginx
    version: "11.x.x"
    repository: "https://charts.bitnami.com/bitnami"
    tags:
      - web
      - frontend
  - name: memcached
    version: "6.x.x"
    repository: "https://charts.bitnami.com/bitnami"
    tags:
      - cache
      - backend
```

Enable/disable groups:
```bash
# Enable only frontend components
helm install myapp . --set tags.frontend=true

# Enable only backend components
helm install myapp . --set tags.backend=true
```

## Importing Values from Dependencies

Import values to simplify access:

```yaml
dependencies:
  - name: nginx
    version: "11.x.x"
    repository: "https://charts.bitnami.com/bitnami"
    import-values:
      - child: service
        parent: nginx-service
      - child: serverBlock
        parent: nginx-server-block
```

## Subcharts

Subcharts are stored in the `charts/` directory and are treated as completely independent. They cannot access the parent chart's values, and the parent chart cannot access their values without explicit value passing.

### Structure of Subcharts
```
mychart/
├── Chart.yaml
├── values.yaml
├── charts/
│   ├── helper/
│   │   ├── Chart.yaml
│   │   ├── values.yaml
│   │   └── templates/
│   └── util/
│       ├── Chart.yaml
│       ├── values.yaml
│       └── templates/
└── templates/
```

## Dependency Best Practices

### 1. Pin Specific Versions
Always pin to specific version ranges to avoid unexpected updates:
```yaml
dependencies:
  - name: postgresql
    version: "12.6.x"  # Pinned to patch versions
    repository: "https://charts.bitnami.com/bitnami"
```

### 2. Use Conditions Wisely
Provide clear conditions to allow disabling dependencies:
```yaml
postgresql:
  enabled: true

redis:
  enabled: true
```

### 3. Override Subchart Values
Pass values to subcharts through the parent's values.yaml using nested configuration:

**Parent chart's values.yaml:**
```yaml
# Configure PostgreSQL subchart
postgresql:
  enabled: true  # Control via condition
  auth:
    username: "myuser"
    password: "mypassword"
    database: "mydb"
  primary:
    persistence:
      enabled: true
      size: 10Gi
    resources:
      limits:
        cpu: 500m
        memory: 512Mi

# Configure Redis subchart
redis:
  enabled: true  # Control via condition
  auth:
    enabled: true
    password: "redispass"
  master:
    persistence:
      enabled: false
    resources:
      limits:
        cpu: 250m
        memory: 256Mi

# Access in parent templates
# Database URL: {{ .Values.postgresql.auth.username }}@postgresql:5432/{{ .Values.postgresql.auth.database }}
# Redis URL: redis://:{{ .Values.redis.auth.password }}@redis-master:6379
```

**How Subchart Values Work:**
1. **Nested under subchart name** - Values for a subchart are nested under its name
2. **Complete isolation** - Each subchart has its own values namespace
3. **Parent override** - Parent values override subchart defaults
4. **Deep merge** - Values are deeply merged (maps), not replaced (lists replaced)

**Example: Overriding Subchart Values at Install Time:**
```bash
# Override via --set
helm install myapp ./mychart \
  --set postgresql.auth.password="newpass" \
  --set redis.master.persistence.enabled=true

# Override via values file
helm install myapp ./mychart \
  -f values-prod.yaml \
  --set postgresql.primary.resources.limits.memory=2Gi
```

### 4. Document Dependencies
Include dependency information in your chart's documentation:
```yaml
dependencies:
  - name: redis
    version: "17.x.x"
    repository: "https://charts.bitnami.com/bitnami"
    description: "Provides caching layer for the application"
```

## Updating Dependencies

When you update Chart.yaml, run:
```bash
helm dependency update
```

This downloads the new versions to the charts/ directory and creates a Chart.lock file that locks the versions used.

## Vendor Dependencies

To vendor dependencies (download them locally):
```bash
helm dependency build
```

This downloads all dependencies to the charts/ directory and creates a lock file.

## Troubleshooting Dependencies

### Missing Dependencies
```bash
# Ensure dependencies are downloaded
helm dependency update
```

### Repository Issues
```bash
# Add repository if missing
helm repo add <name> <url>
helm repo update
```

### Version Conflicts
Check Chart.lock for locked versions and update Chart.yaml accordingly, then run `helm dependency update`.