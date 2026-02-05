# Helm Values Hierarchy and Schema Validation

## Values Hierarchy and Merge Order

### Understanding Values Priority

Helm merges values from multiple sources in a specific order. **Later sources override earlier ones**.

```text
Priority Order (lowest to highest):
1. Chart's values.yaml (base defaults)
2. Parent chart's values.yaml (if subchart)
3. User-supplied values file (-f or --values)
4. User-supplied parameters (--set)
```

### Example: Values Merge

**Chart values.yaml:**
```yaml
replicaCount: 3
image:
  repository: myapp
  tag: "1.0.0"
  pullPolicy: IfNotPresent
resources:
  limits:
    cpu: 500m
    memory: 512Mi
```

**values-prod.yaml:**
```yaml
replicaCount: 5
image:
  tag: "2.0.0"
resources:
  limits:
    memory: 1Gi
```

**Command:**
```bash
helm install myapp ./chart -f values-prod.yaml --set replicaCount=10
```

**Result (merged):**
```yaml
replicaCount: 10              # From --set (highest priority)
image:
  repository: myapp          # From values.yaml
  tag: "2.0.0"              # From values-prod.yaml (overrides base)
  pullPolicy: IfNotPresent  # From values.yaml
resources:
  limits:
    cpu: 500m               # From values.yaml
    memory: 1Gi             # From values-prod.yaml (overrides base)
```

### Deep Merge Behavior

Helm performs **deep merge** for maps/objects:

```yaml
# Base values.yaml
database:
  host: localhost
  port: 5432
  ssl: false
  poolSize: 10

# Override with -f values-prod.yaml
database:
  host: prod-db.example.com
  ssl: true

# RESULT: Deep merge keeps unspecified keys
database:
  host: prod-db.example.com  # Overridden
  port: 5432                 # Kept from base
  ssl: true                  # Overridden
  poolSize: 10              # Kept from base
```

### List Override Behavior

**Lists are completely replaced, NOT merged:**

```yaml
# Base values.yaml
env:
  - name: LOG_LEVEL
    value: INFO
  - name: DEBUG
    value: "false"

# Override with -f values-dev.yaml
env:
  - name: LOG_LEVEL
    value: DEBUG

# RESULT: Entire list replaced
env:
  - name: LOG_LEVEL
    value: DEBUG
# Note: DEBUG env var is gone!
```

**Best Practice:** Always specify complete lists in override files.

## Multiple Values Files

You can specify multiple `-f` flags. They are applied in order:

```bash
helm install myapp ./chart \
  -f values.yaml \           # Base
  -f values-prod.yaml \      # Environment overrides
  -f values-region-us.yaml \ # Region-specific overrides
  --set image.tag=v3.0.0     # Runtime override
```

Each file overrides the previous one.

## Schema Validation with values.schema.json

### Why Use Schema Validation?

1. **Catch errors early** - Validate values before deployment
2. **Document requirements** - Self-documenting value constraints
3. **Type safety** - Ensure correct value types
4. **Range validation** - Enforce min/max values
5. **Required fields** - Fail if mandatory values missing

### Basic Schema Structure

Helm uses JSON Schema (Draft 7) for validation.

**values.schema.json:**
```json
{
  "$schema": "https://json-schema.org/draft-07/schema#",
  "title": "Chart Values Schema",
  "type": "object",
  "required": ["image"],
  "properties": {
    "replicaCount": {
      "type": "integer",
      "minimum": 1,
      "maximum": 100,
      "description": "Number of pod replicas"
    },
    "image": {
      "type": "object",
      "required": ["repository"],
      "properties": {
        "repository": {
          "type": "string",
          "description": "Container image repository",
          "minLength": 1
        },
        "tag": {
          "type": "string",
          "description": "Container image tag",
          "pattern": "^[a-zA-Z0-9._-]+$"
        },
        "pullPolicy": {
          "type": "string",
          "enum": ["Always", "IfNotPresent", "Never"],
          "default": "IfNotPresent"
        }
      }
    }
  }
}
```

### Comprehensive Schema Example

**values.schema.json:**
```json
{
  "$schema": "https://json-schema.org/draft-07/schema#",
  "title": "Task API Helm Chart Values",
  "type": "object",
  "required": ["image", "service"],
  "properties": {
    "replicaCount": {
      "type": "integer",
      "minimum": 1,
      "maximum": 100,
      "default": 3,
      "description": "Number of pod replicas (ignored if autoscaling is enabled)"
    },
    "image": {
      "type": "object",
      "required": ["repository"],
      "properties": {
        "registry": {
          "type": "string",
          "description": "Container registry URL",
          "examples": ["docker.io", "gcr.io"]
        },
        "repository": {
          "type": "string",
          "minLength": 1,
          "description": "Container image repository",
          "examples": ["mycompany/task-api"]
        },
        "tag": {
          "type": "string",
          "pattern": "^[a-zA-Z0-9._-]+$",
          "description": "Container image tag. Defaults to Chart.appVersion if not set.",
          "examples": ["1.0.0", "latest", "v2.1.3-beta"]
        },
        "pullPolicy": {
          "type": "string",
          "enum": ["Always", "IfNotPresent", "Never"],
          "default": "IfNotPresent",
          "description": "Image pull policy"
        }
      }
    },
    "imagePullSecrets": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["name"],
        "properties": {
          "name": {
            "type": "string",
            "minLength": 1
          }
        }
      },
      "description": "List of image pull secrets for private registries"
    },
    "serviceAccount": {
      "type": "object",
      "properties": {
        "create": {
          "type": "boolean",
          "default": true,
          "description": "Specifies whether a service account should be created"
        },
        "name": {
          "type": "string",
          "description": "The name of the service account to use"
        },
        "annotations": {
          "type": "object",
          "additionalProperties": {
            "type": "string"
          }
        }
      }
    },
    "service": {
      "type": "object",
      "required": ["type", "port"],
      "properties": {
        "type": {
          "type": "string",
          "enum": ["ClusterIP", "NodePort", "LoadBalancer", "ExternalName"],
          "default": "ClusterIP",
          "description": "Kubernetes service type"
        },
        "port": {
          "type": "integer",
          "minimum": 1,
          "maximum": 65535,
          "description": "Service port"
        },
        "targetPort": {
          "type": ["integer", "string"],
          "description": "Container target port (number or name)"
        },
        "nodePort": {
          "type": "integer",
          "minimum": 30000,
          "maximum": 32767,
          "description": "NodePort (only valid for NodePort service type)"
        }
      }
    },
    "ingress": {
      "type": "object",
      "properties": {
        "enabled": {
          "type": "boolean",
          "default": false,
          "description": "Enable ingress resource"
        },
        "className": {
          "type": "string",
          "description": "IngressClass name"
        },
        "hosts": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["host", "paths"],
            "properties": {
              "host": {
                "type": "string",
                "format": "hostname",
                "description": "Hostname"
              },
              "paths": {
                "type": "array",
                "minItems": 1,
                "items": {
                  "type": "object",
                  "required": ["path", "pathType"],
                  "properties": {
                    "path": {
                      "type": "string",
                      "description": "Path"
                    },
                    "pathType": {
                      "type": "string",
                      "enum": ["Exact", "Prefix", "ImplementationSpecific"]
                    }
                  }
                }
              }
            }
          }
        },
        "tls": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["secretName", "hosts"],
            "properties": {
              "secretName": {
                "type": "string",
                "minLength": 1
              },
              "hosts": {
                "type": "array",
                "items": {
                  "type": "string",
                  "format": "hostname"
                }
              }
            }
          }
        }
      }
    },
    "resources": {
      "type": "object",
      "properties": {
        "limits": {
          "type": "object",
          "properties": {
            "cpu": {
              "type": "string",
              "pattern": "^[0-9]+(m|\\.[0-9]+)?$",
              "description": "CPU limit (e.g., '500m', '1', '2.5')"
            },
            "memory": {
              "type": "string",
              "pattern": "^[0-9]+(Mi|Gi|M|G|Ki|K)?$",
              "description": "Memory limit (e.g., '512Mi', '1Gi')"
            }
          }
        },
        "requests": {
          "type": "object",
          "properties": {
            "cpu": {
              "type": "string",
              "pattern": "^[0-9]+(m|\\.[0-9]+)?$",
              "description": "CPU request"
            },
            "memory": {
              "type": "string",
              "pattern": "^[0-9]+(Mi|Gi|M|G|Ki|K)?$",
              "description": "Memory request"
            }
          }
        }
      }
    },
    "autoscaling": {
      "type": "object",
      "properties": {
        "enabled": {
          "type": "boolean",
          "default": false
        },
        "minReplicas": {
          "type": "integer",
          "minimum": 1,
          "maximum": 100
        },
        "maxReplicas": {
          "type": "integer",
          "minimum": 1,
          "maximum": 1000
        },
        "targetCPUUtilizationPercentage": {
          "type": "integer",
          "minimum": 1,
          "maximum": 100
        },
        "targetMemoryUtilizationPercentage": {
          "type": "integer",
          "minimum": 1,
          "maximum": 100
        }
      }
    },
    "env": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["name"],
        "properties": {
          "name": {
            "type": "string",
            "minLength": 1,
            "pattern": "^[A-Z][A-Z0-9_]*$",
            "description": "Environment variable name (uppercase with underscores)"
          },
          "value": {
            "type": "string",
            "description": "Environment variable value"
          }
        }
      }
    },
    "nodeSelector": {
      "type": "object",
      "additionalProperties": {
        "type": "string"
      }
    },
    "tolerations": {
      "type": "array",
      "items": {
        "type": "object"
      }
    },
    "affinity": {
      "type": "object"
    }
  }
}
```

### Advanced Schema Features

#### Conditional Validation

```json
{
  "properties": {
    "service": {
      "type": "object",
      "properties": {
        "type": {
          "type": "string",
          "enum": ["ClusterIP", "NodePort", "LoadBalancer"]
        },
        "nodePort": {
          "type": "integer"
        }
      },
      "if": {
        "properties": {
          "type": { "const": "NodePort" }
        }
      },
      "then": {
        "required": ["nodePort"],
        "properties": {
          "nodePort": {
            "minimum": 30000,
            "maximum": 32767
          }
        }
      }
    }
  }
}
```

#### Pattern Properties

```json
{
  "properties": {
    "config": {
      "type": "object",
      "patternProperties": {
        "^[A-Z_]+$": {
          "type": "string"
        }
      },
      "additionalProperties": false
    }
  }
}
```

#### Dependencies

```json
{
  "properties": {
    "ingress": {
      "type": "object",
      "properties": {
        "enabled": { "type": "boolean" },
        "tls": { "type": "array" }
      },
      "dependencies": {
        "tls": ["enabled"]
      }
    }
  }
}
```

## Testing Schema Validation

### Automatic Validation

Helm automatically validates values against the schema:

```bash
# Validation happens automatically
helm install myapp ./chart -f values-prod.yaml

# Validation error example:
Error: values don't meet the specifications of the schema(s) in the following chart(s):
task-api:
- replicaCount: Invalid type. Expected: integer, given: string
```

### Manual Validation

```bash
# Validate without installing
helm lint ./chart -f values-prod.yaml

# Template with validation
helm template myapp ./chart -f values-prod.yaml --validate
```

### CI/CD Integration

```yaml
# .github/workflows/helm-validate.yml
name: Validate Helm Charts

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install Helm
        uses: azure/setup-helm@v3

      - name: Validate dev values
        run: helm lint ./chart -f values-dev.yaml

      - name: Validate staging values
        run: helm lint ./chart -f values-staging.yaml

      - name: Validate prod values
        run: helm lint ./chart -f values-prod.yaml
```

## Best Practices

### Values File Organization

1. **Base values.yaml** - Complete, sensible defaults
2. **Environment overrides** - Only override what changes
3. **Clear comments** - Document purpose and valid ranges
4. **Logical grouping** - Group related configuration

### Schema Best Practices

1. **Start simple** - Add constraints incrementally
2. **Required fields** - Mark truly mandatory fields as required
3. **Provide defaults** - Include sensible defaults in schema
4. **Good descriptions** - Help users understand each field
5. **Examples** - Show valid value examples
6. **Pattern validation** - Use regex for formatted strings
7. **Enum constraints** - Limit choices where appropriate

### Environment-Specific Patterns

```yaml
# values.yaml (base)
environment: "development"
replicaCount: 1
resources:
  limits:
    cpu: 250m
    memory: 256Mi

# values-prod.yaml (override)
environment: "production"
replicaCount: 5
resources:
  limits:
    cpu: 1000m
    memory: 1Gi
```

## Common Validation Errors

### Type Mismatch
```yaml
# ERROR: replicaCount should be integer
replicaCount: "3"  # String instead of integer

# CORRECT:
replicaCount: 3
```

### Missing Required Field
```yaml
# ERROR: image.repository is required
image:
  tag: "1.0.0"

# CORRECT:
image:
  repository: "myapp"
  tag: "1.0.0"
```

### Invalid Enum Value
```yaml
# ERROR: pullPolicy must be one of the enum values
image:
  pullPolicy: "AlwaysPull"  # Invalid

# CORRECT:
image:
  pullPolicy: "Always"  # Valid enum value
```

### Out of Range
```yaml
# ERROR: replicaCount maximum is 100
replicaCount: 150  # Out of range

# CORRECT:
replicaCount: 50  # Within range
```

## Debugging Values

### Show Computed Values

```bash
# Show all computed values after merge
helm get values myrelease

# Show all values including defaults
helm get values myrelease --all

# Show values in YAML format
helm get values myrelease -o yaml
```

### Template Debugging

```bash
# Render with debug output
helm template myapp ./chart -f values-prod.yaml --debug

# Check specific values in templates
helm template myapp ./chart --show-only templates/deployment.yaml
```

### Value Inspection in Templates

```yaml
# Add debug output in templates
{{- printf "DEBUG: replicaCount = %v" .Values.replicaCount | nindent 0 }}
{{- printf "DEBUG: image = %v" .Values.image | nindent 0 }}
```

## Schema Validation Tools

### helm-schema (Plugin)

```bash
# Install plugin
helm plugin install https://github.com/losisin/helm-values-schema-json

# Generate schema from values.yaml
helm schema -input values.yaml -output values.schema.json

# Validate values against schema
helm schema -input values.yaml -schema values.schema.json
```

### kubeconform

```bash
# Validate rendered manifests
helm template myapp ./chart | kubeconform -strict
```

## Summary

### Values Priority (Highest to Lowest)
1. `--set` flags
2. `-f values-override.yaml` (last file wins)
3. `-f values-prod.yaml`
4. `values.yaml` (chart defaults)

### Key Concepts
- **Deep merge** for objects/maps
- **Complete replacement** for arrays/lists
- **Schema validation** catches errors early
- **Multiple values files** for layered configuration
- **JSON Schema Draft 7** for validation rules
