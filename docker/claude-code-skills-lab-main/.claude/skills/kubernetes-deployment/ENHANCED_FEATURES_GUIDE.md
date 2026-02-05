# Enhanced Kubernetes Deployment Skill Guide

This guide provides comprehensive coverage of the enhanced Kubernetes deployment skill with AI-assisted generation and validation patterns.

## Table of Contents
1. [Overview](#overview)
2. [AI-Assisted Manifest Generation](#ai-assisted-manifest-generation)
3. [Iterative Refinement Workflows](#iterative-refinement-workflows)
4. [Critical Evaluation Checklists](#critical-evaluation-checklists)
5. [Production Readiness Validation](#production-readiness-validation)
6. [Complete Workflow Example](#complete-workflow-example)
7. [Best Practices](#best-practices)

## Overview

The enhanced Kubernetes deployment skill incorporates AI-assisted patterns to streamline the process of creating, validating, and deploying production-ready Kubernetes manifests. This includes:

- Natural language to YAML translation
- Iterative refinement workflows
- Critical evaluation checklists
- Production readiness validation

## AI-Assisted Manifest Generation

### Natural Language Processing

The AI-assisted generator parses natural language descriptions to extract configuration parameters:

```python
from scripts.natural-language-generator import KubernetesManifestGenerator

generator = KubernetesManifestGenerator()
manifest = generator.generate_from_natural_language(
    "Deploy a web app called myapi using myapp:1.0 with 3 replicas, expose via LoadBalancer"
)
```

### Supported Patterns

The parser recognizes common patterns in natural language descriptions:

- **Replicas**: "with 3 replicas", "scale to 5 pods", "2 instances"
- **Ports**: "expose on port 8080", "listen on 3000"
- **Images**: "use nginx:1.25", "container image redis:7"
- **Services**: "with LoadBalancer", "expose externally"
- **Features**: "enable HPA", "with ingress", "production hardened"

### Command Line Usage

```bash
# Generate manifest from description
python scripts/natural-language-generator.py --describe "Deploy nginx with 3 replicas" --output deployment.yaml

# Generate with validation
python scripts/natural-language-generator.py --describe "Production API with HPA" --validate

# Refine existing manifest
python scripts/natural-language-generator.py --refine existing.yaml --describe "Add security context"
```

## Iterative Refinement Workflows

### Workflow Process

The iterative refinement follows a cycle of generation, evaluation, and improvement:

1. **Initial Generation**: Create base manifest from requirements
2. **Validation**: Run automated checks and scoring
3. **Feedback Integration**: Apply suggestions and corrections
4. **Verification**: Re-validate improved manifest
5. **Iteration**: Repeat until quality targets met

### Refinement Engine

The refinement engine applies feedback to improve manifests:

```python
from scripts.natural-language-generator import IterativeRefinementEngine

refiner = IterativeRefinementEngine()
refined_manifest = refiner.refine_manifest(
    current_manifest,
    "Add resource limits and security context"
)
```

### Common Refinement Patterns

| Category | Feedback | Applied Change |
|----------|----------|----------------|
| Security | "Add security context" | Add runAsNonRoot, readOnlyRootFilesystem |
| Resources | "Add resource limits" | Add CPU/memory requests and limits |
| Availability | "Increase replicas" | Change replica count |
| Scaling | "Enable HPA" | Add HorizontalPodAutoscaler |
| Networking | "Change service type" | Update service specification |

## Critical Evaluation Checklists

### Security Assessment

- [ ] Images from trusted sources
- [ ] Containers run as non-root
- [ ] Read-only root filesystem
- [ ] Privilege escalation disabled
- [ ] Capabilities dropped
- [ ] Seccomp profile applied
- [ ] Network policies defined

### Resource Management

- [ ] CPU requests and limits specified
- [ ] Memory requests and limits specified
- [ ] Resource ratios appropriate
- [ ] No unlimited resources
- [ ] QoS class understood and appropriate

### Availability and Reliability

- [ ] Sufficient replica count for HA
- [ ] Liveness probes configured
- [ ] Readiness probes configured
- [ ] Startup probes for slow apps
- [ ] Proper deployment strategy
- [ ] Pod disruption budgets

## Production Readiness Validation

### Automated Validation Script

The production readiness validator performs comprehensive checks:

```bash
# Validate a manifest file
./scripts/production-readiness-validator.sh deployment.yaml

# Output includes:
# - Critical, High, Medium, Low issue counts
# - Production readiness score (0-100)
# - Specific recommendations
```

### Validation Categories

#### Security Validation
- Container security (non-root, capabilities, etc.)
- Network security (policies, service exposure)
- RBAC and permissions

#### Resource Validation
- Proper resource requests and limits
- Appropriate QoS class
- Resource ratio validation

#### Availability Validation
- Sufficient replica count
- Proper health check configuration
- Appropriate deployment strategy

#### Best Practices Validation
- Proper labeling and naming
- Immutable image tags
- Appropriate service types

### Scoring System

- **90-100**: Production ready with minor considerations
- **70-89**: Production ready with some improvements needed
- **50-69**: Significant improvements needed before production
- **Below 50**: Major issues, not production ready

## Complete Workflow Example

### Step 1: Natural Language Input
```
Description: "Deploy a production web API called products-api using image mycompany/products-api:v1.2 with 3 replicas, expose via LoadBalancer on port 8080, enable HPA with min 2 and max 10, add security context and resource limits"
```

### Step 2: AI Generation
```bash
python scripts/natural-language-generator.py --describe "Deploy a production web API called products-api using image mycompany/products-api:v1.2 with 3 replicas, expose via LoadBalancer on port 8080, enable HPA with min 2 and max 10, add security context and resource limits" --output products-api.yaml
```

### Step 3: Production Validation
```bash
./scripts/production-readiness-validator.sh products-api.yaml
```

### Step 4: Refinement (if needed)
```bash
python scripts/natural-language-generator.py --refine products-api.yaml --describe "Optimize resource requests for cost efficiency" --output products-api-final.yaml
```

### Step 5: Final Validation
```bash
./scripts/production-readiness-validator.sh products-api-final.yaml
```

### Step 6: Deploy
```bash
kubectl apply -f products-api-final.yaml
./scripts/validate-deployment.sh products-api default
```

## Best Practices

### For Natural Language Descriptions
- Be specific about requirements (replicas, ports, features)
- Mention production requirements explicitly
- Include security and performance needs
- Specify scaling requirements

### For Iterative Refinement
- Address critical issues first
- Validate after each refinement
- Keep iterations focused
- Document changes made

### For Production Validation
- Run validation before deployment
- Address all critical and high severity issues
- Aim for score of 85+ for production
- Review medium severity issues

### For Security
- Always specify security requirements
- Use non-root containers
- Apply principle of least privilege
- Regularly update base images

## Troubleshooting

### Common Issues

**Parser doesn't recognize description**: Use more specific language or common patterns
**Invalid YAML generated**: Check for syntax errors in description
**Validation fails**: Address issues in priority order (critical → high → medium → low)
**Performance problems**: Optimize resource requests/limits based on actual usage

### Getting Help

- Review the critical evaluation checklist for guidance
- Use the iterative refinement process to improve gradually
- Consult the reference documentation for specific configuration options
- Validate frequently to catch issues early