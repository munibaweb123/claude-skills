#!/usr/bin/env python3
"""
Docker Deployment helper script

Validates Docker Desktop setup and configures appropriate memory/CPU allocation
for AI services with Docker Desktop prerequisite checks and resource configuration.
"""

import argparse
import subprocess
import sys
import os
import platform
from pathlib import Path


def check_docker_installed():
    """Check if Docker is installed and accessible"""
    try:
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"✓ Docker is installed: {result.stdout.strip()}")
            return True
        else:
            print(f"✗ Docker is not accessible: {result.stderr.strip()}")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("✗ Docker is not installed or not in PATH")
        return False


def check_docker_daemon_running():
    """Check if Docker daemon is running"""
    try:
        result = subprocess.run(['docker', 'info'], capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            print("✓ Docker daemon is running")
            return True
        else:
            print(f"✗ Docker daemon is not running: {result.stderr.strip()}")
            return False
    except subprocess.TimeoutExpired:
        print("✗ Docker daemon check timed out - Docker daemon may not be running")
        return False


def check_docker_desktop_resources():
    """Check Docker Desktop resource allocation"""
    print("Checking Docker Desktop resource allocation...")

    success = True

    # Try to get memory and CPU info from Docker
    try:
        # Get Docker system info
        result = subprocess.run(['docker', 'info', '--format', '{{json .}}'],
                               capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            # For AI services, we recommend at least 4GB memory and 2 CPUs
            # This is a basic check - in a real implementation, we'd parse the JSON
            print("✓ Docker system information accessible")

            # Check memory limits by running a simple container
            test_result = subprocess.run(['docker', 'run', '--rm', '--memory=2g', 'hello-world'],
                                       capture_output=True, text=True, timeout=30)
            if test_result.returncode == 0:
                print("✓ Docker can allocate memory (tested with 2GB limit)")
            else:
                print(f"⚠ Memory allocation test failed: {test_result.stderr.strip()[:100]}...")
                success = False
        else:
            print("⚠ Could not retrieve Docker system information")
            success = False
    except subprocess.TimeoutExpired:
        print("⚠ Docker info check timed out")
        success = False
    except Exception as e:
        print(f"⚠ Error checking Docker resources: {str(e)}")
        success = False

    return success


def validate_docker_desktop_prerequisites():
    """Validate Docker Desktop prerequisites for AI services"""
    print("Validating Docker Desktop prerequisites for AI services...")

    validations = {
        "Docker Installed": check_docker_installed(),
        "Docker Daemon Running": check_docker_daemon_running(),
        "Docker Resources": check_docker_desktop_resources()
    }

    # Check OS compatibility
    os_name = platform.system().lower()
    if os_name in ['windows', 'darwin']:  # Windows or macOS
        print("✓ Running on Windows/macOS - Docker Desktop is appropriate")
        validations["OS Compatible"] = True
    else:
        print("⚠ Running on Linux - Docker Engine is typically used instead of Docker Desktop")
        validations["OS Compatible"] = True  # Still valid, just informational

    # Check WSL2 if on Windows (important for Docker Desktop)
    if os_name == 'windows':
        try:
            result = subprocess.run(['wsl', '--list', '--quiet'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                wsl_dists = result.stdout.strip().split('\n')
                wsl_dists = [dist.strip() for dist in wsl_dists if dist.strip()]
                if wsl_dists:
                    print(f"✓ WSL2 is available with {len(wsl_dists)} distribution(s)")
                    validations["WSL2 Available"] = True
                else:
                    print("⚠ WSL2 is not configured (may be needed for Docker Desktop on Windows)")
                    validations["WSL2 Available"] = False
            else:
                print("⚠ Could not check WSL2 status")
                validations["WSL2 Available"] = False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            print("⚠ WSL2 is not available or not in PATH (may be needed for Docker Desktop on Windows)")
            validations["WSL2 Available"] = False

    return validations


def recommend_ai_resources():
    """Recommend appropriate resource allocation for AI services"""
    print("\nRecommended resource allocation for AI services:")
    print("- Memory: Minimum 8GB (16GB+ recommended for large models)")
    print("- CPU: Minimum 4 cores (8+ cores recommended for parallel processing)")
    print("- Disk: At least 20GB free space for models and containers")
    print("- Swap: Consider increasing if running memory-intensive AI models")

    # Try to get current Docker Desktop settings if possible
    try:
        # This is a simplified check - actual Docker Desktop settings would require
        # platform-specific methods to access
        result = subprocess.run(['docker', 'system', 'info'],
                               capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            print("\nCurrent Docker system info:")
            # Extract relevant information about resources
            lines = result.stdout.split('\n')
            for line in lines:
                if any(keyword in line.lower() for keyword in ['memory', 'cpu', 'total memory', 'nproc']):
                    print(f"  {line.strip()}")
    except subprocess.TimeoutExpired:
        print("\nCould not retrieve current Docker system info")


def configure_docker_resources():
    """Provide guidance for configuring Docker Desktop resources for AI services"""
    print("\nTo configure Docker Desktop resources for AI services:")
    print("1. Open Docker Desktop settings")
    print("2. Go to Resources section")
    print("3. Adjust the following settings:")
    print("   - Memory: Set to at least 8GB (or 50% of system RAM, max 16GB)")
    print("   - CPUs: Set to at least 4 cores (or half of your CPU cores)")
    print("   - Swap: Set to at least 2GB for memory-intensive operations")
    print("   - Disk image size: Ensure at least 20GB available")
    print("\nNote: Changes require Docker Desktop restart to take effect")


def diagnose_container(container_name):
    """Diagnose a failed or problematic container"""
    print(f"\n{'='*80}")
    print(f"DIAGNOSING CONTAINER: {container_name}")
    print(f"{'='*80}\n")

    # Step 1: Check if container exists
    print("1. Checking container status...")
    try:
        result = subprocess.run(['docker', 'ps', '-a', '--filter', f'name={container_name}', '--format', '{{.Names}}\t{{.Status}}\t{{.State}}'],
                               capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and result.stdout.strip():
            print(f"   ✓ Container found: {result.stdout.strip()}")
        else:
            print(f"   ✗ Container '{container_name}' not found")
            return
    except subprocess.TimeoutExpired:
        print("   ✗ Command timed out")
        return

    # Step 2: Get container state details
    print("\n2. Inspecting container state...")
    try:
        status = subprocess.run(['docker', 'inspect', '--format', '{{.State.Status}}', container_name],
                               capture_output=True, text=True, timeout=10)
        error = subprocess.run(['docker', 'inspect', '--format', '{{.State.Error}}', container_name],
                              capture_output=True, text=True, timeout=10)
        exit_code = subprocess.run(['docker', 'inspect', '--format', '{{.State.ExitCode}}', container_name],
                                  capture_output=True, text=True, timeout=10)
        oom_killed = subprocess.run(['docker', 'inspect', '--format', '{{.State.OOMKilled}}', container_name],
                                   capture_output=True, text=True, timeout=10)
        restart_count = subprocess.run(['docker', 'inspect', '--format', '{{.RestartCount}}', container_name],
                                      capture_output=True, text=True, timeout=10)

        print(f"   Status: {status.stdout.strip()}")
        print(f"   Exit Code: {exit_code.stdout.strip()}")
        print(f"   OOM Killed: {oom_killed.stdout.strip()}")
        print(f"   Restart Count: {restart_count.stdout.strip()}")
        if error.stdout.strip():
            print(f"   Error: {error.stdout.strip()}")
    except subprocess.TimeoutExpired:
        print("   ✗ Inspection timed out")

    # Step 3: Show recent logs
    print("\n3. Recent container logs (last 20 lines)...")
    try:
        logs = subprocess.run(['docker', 'logs', '--tail', '20', container_name],
                             capture_output=True, text=True, timeout=15)
        if logs.stdout or logs.stderr:
            print("   " + "-"*76)
            output = logs.stdout + logs.stderr
            for line in output.split('\n')[-20:]:
                if line.strip():
                    print(f"   {line}")
            print("   " + "-"*76)
        else:
            print("   (No logs available)")
    except subprocess.TimeoutExpired:
        print("   ✗ Log retrieval timed out")

    # Step 4: Show restart policy
    print("\n4. Restart policy...")
    try:
        restart_policy = subprocess.run(['docker', 'inspect', '--format', '{{.HostConfig.RestartPolicy.Name}}', container_name],
                                       capture_output=True, text=True, timeout=10)
        max_retry = subprocess.run(['docker', 'inspect', '--format', '{{.HostConfig.RestartPolicy.MaximumRetryCount}}', container_name],
                                   capture_output=True, text=True, timeout=10)
        print(f"   Policy: {restart_policy.stdout.strip()}")
        if max_retry.stdout.strip() != '0':
            print(f"   Max Retries: {max_retry.stdout.strip()}")
    except subprocess.TimeoutExpired:
        print("   ✗ Could not retrieve restart policy")

    # Step 5: Recommendations
    print("\n5. Diagnostic recommendations...")
    print("   • Run 'docker logs -f {}' to follow logs in real-time".format(container_name))
    print("   • Run 'docker inspect {}' for full configuration".format(container_name))
    if status.stdout.strip() == 'running':
        print("   • Run 'docker exec -it {} /bin/bash' to inspect inside container".format(container_name))
    print("   • Check restart policy with 'docker update --restart unless-stopped {}'".format(container_name))
    print(f"\n{'='*80}\n")


def show_container_logs(container_name, tail=50, follow=False):
    """Display container logs"""
    print(f"Viewing logs for container: {container_name}")
    print("="*80)

    cmd = ['docker', 'logs']
    if tail:
        cmd.extend(['--tail', str(tail)])
    if follow:
        cmd.append('-f')
    cmd.append(container_name)

    try:
        if follow:
            # For follow mode, stream output directly
            subprocess.run(cmd)
        else:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                print(result.stdout)
                if result.stderr:
                    print(result.stderr)
            else:
                print(f"Error retrieving logs: {result.stderr}")
    except subprocess.TimeoutExpired:
        print("Log retrieval timed out")
    except KeyboardInterrupt:
        print("\nStopped following logs")


def inspect_container(container_name, format_string=None):
    """Inspect container configuration"""
    print(f"Inspecting container: {container_name}")
    print("="*80)

    cmd = ['docker', 'inspect']
    if format_string:
        cmd.extend(['--format', format_string])
    cmd.append(container_name)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            print(result.stdout)
        else:
            print(f"Error inspecting container: {result.stderr}")
    except subprocess.TimeoutExpired:
        print("Inspection timed out")


def exec_in_container(container_name, command):
    """Execute command in running container"""
    print(f"Executing command in container: {container_name}")
    print(f"Command: {command}")
    print("="*80)

    # Check if container is running
    try:
        status = subprocess.run(['docker', 'inspect', '--format', '{{.State.Status}}', container_name],
                               capture_output=True, text=True, timeout=10)
        if status.stdout.strip() != 'running':
            print(f"Error: Container is not running (status: {status.stdout.strip()})")
            return
    except subprocess.TimeoutExpired:
        print("Could not check container status")
        return

    # Execute command
    cmd = ['docker', 'exec', '-it', container_name] + command.split()
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\nCommand interrupted")


def explain_restart_policies():
    """Explain Docker restart policies"""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                           DOCKER RESTART POLICIES                             ║
╚══════════════════════════════════════════════════════════════════════════════╝

Restart policies control whether containers automatically restart when they exit
or when Docker daemon restarts.

┌──────────────────┬────────────────────────────────────────────────────────────┐
│ POLICY           │ BEHAVIOR                                                   │
├──────────────────┼────────────────────────────────────────────────────────────┤
│ no               │ Do not restart (default)                                   │
│                  │ Use for: Development, debugging                            │
├──────────────────┼────────────────────────────────────────────────────────────┤
│ always           │ Always restart, even after daemon restart                 │
│                  │ Use for: Critical production services                     │
├──────────────────┼────────────────────────────────────────────────────────────┤
│ unless-stopped   │ Restart unless manually stopped                            │
│                  │ Use for: Most production services (RECOMMENDED)            │
├──────────────────┼────────────────────────────────────────────────────────────┤
│ on-failure[:n]   │ Restart only on non-zero exit (max n times)              │
│                  │ Use for: Services that may fail temporarily                │
└──────────────────┴────────────────────────────────────────────────────────────┘

CONFIGURATION EXAMPLES:

  Docker Run:
    docker run -d --restart unless-stopped my-service
    docker run -d --restart on-failure:5 my-service

  Docker Compose:
    services:
      my-service:
        restart: unless-stopped

  Update Existing Container:
    docker update --restart unless-stopped <container-name>

MONITORING:
    docker inspect --format='{{.RestartCount}}' <container>  # Restart count
    docker inspect --format='{{.HostConfig.RestartPolicy.Name}}' <container>
    docker events --filter container=<container>  # Watch restart events

BEST PRACTICES:
  ✓ Use 'unless-stopped' for production services
  ✓ Use 'on-failure' with retry limit to prevent restart loops
  ✓ Use 'no' during development to catch failures immediately
  ✓ Monitor restart counts to detect flapping containers
  ⚠  Avoid 'always' unless container must survive manual stops
""")


def show_debug_guide():
    """Show comprehensive debugging guide"""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    DOCKER CONTAINER DEBUGGING GUIDE                           ║
╚══════════════════════════════════════════════════════════════════════════════╝

WORKFLOW FOR FAILED CONTAINER STARTUP:

1. LIST ALL CONTAINERS (including stopped)
   $ docker ps -a

2. VIEW CONTAINER LOGS
   $ docker logs <container>              # All logs
   $ docker logs --tail 50 <container>    # Last 50 lines
   $ docker logs -f <container>           # Follow in real-time
   $ docker logs --since 5m <container>   # Last 5 minutes

3. INSPECT CONTAINER STATE
   $ docker inspect <container>                              # Full config
   $ docker inspect --format='{{.State.Status}}' <container> # Status
   $ docker inspect --format='{{.State.Error}}' <container>  # Error msg
   $ docker inspect --format='{{.State.ExitCode}}' <container>
   $ docker inspect --format='{{.State.OOMKilled}}' <container>

4. EXECUTE COMMANDS (if running)
   $ docker exec -it <container> /bin/bash   # Interactive shell
   $ docker exec <container> ls -la /app     # List files
   $ docker exec <container> env             # Check env vars
   $ docker exec <container> ps aux          # Running processes

5. CHECK RESOURCES
   $ docker stats <container>                # Real-time resource usage
   $ docker inspect --format='{{.HostConfig.Memory}}' <container>

6. NETWORK DIAGNOSTICS
   $ docker exec <container> ping google.com
   $ docker exec <container> curl localhost:8000
   $ docker port <container>                 # Port mappings

COMMON ISSUES:

┌─────────────────────────┬──────────────────────────────────────────────────┐
│ SYMPTOM                 │ DIAGNOSIS & FIX                                  │
├─────────────────────────┼──────────────────────────────────────────────────┤
│ Port binding error      │ docker logs → "address already in use"           │
│                         │ Fix: Change port or stop conflicting service    │
├─────────────────────────┼──────────────────────────────────────────────────┤
│ OOMKilled              │ docker inspect → OOMKilled: true                 │
│                         │ Fix: Increase memory limit in compose/run       │
├─────────────────────────┼──────────────────────────────────────────────────┤
│ Missing env vars       │ docker exec <c> env                              │
│                         │ Fix: Add to docker-compose.yml or Dockerfile    │
├─────────────────────────┼──────────────────────────────────────────────────┤
│ Volume mount issues    │ docker inspect --format='{{.Mounts}}'            │
│                         │ Fix: Check paths and permissions                │
├─────────────────────────┼──────────────────────────────────────────────────┤
│ App crashes on startup │ docker logs --tail 100                           │
│                         │ Fix: Check stack trace and application config   │
├─────────────────────────┼──────────────────────────────────────────────────┤
│ Network connectivity   │ docker exec <c> ping <host>                      │
│                         │ Fix: Check network config and DNS               │
└─────────────────────────┴──────────────────────────────────────────────────┘

QUICK COMMANDS:
  docker ps -a                                    # All containers
  docker logs -f --tail 100 <container>          # Live logs
  docker exec -it <container> /bin/bash          # Shell access
  docker inspect <container> | grep -i error     # Find errors
  docker stats                                    # Resource usage
  docker events --filter container=<name>        # Monitor events
""")


def explain_docker_concepts(topic=None):
    """Explain core Docker concepts: images, containers, layers, and copy-on-write"""

    concepts = {
        'images-vs-containers': """
╔══════════════════════════════════════════════════════════════════════════════╗
║                         IMAGES VS CONTAINERS                                  ║
╚══════════════════════════════════════════════════════════════════════════════╝

  ┌─────────────────────────┐         ┌─────────────────────────┐
  │      DOCKER IMAGE       │         │    DOCKER CONTAINER     │
  ├─────────────────────────┤         ├─────────────────────────┤
  │ • Immutable template    │ ──────► │ • Running instance      │
  │ • Read-only layers      │         │ • Writable layer on top │
  │ • Built from Dockerfile │         │ • Created via 'run'     │
  │ • Stored in registry    │         │ • Lives on host         │
  │ • Versioned & tagged    │         │ • Isolated process      │
  └─────────────────────────┘         └─────────────────────────┘
         (Blueprint)                        (Living Instance)

ANALOGY: Image is a recipe, Container is the dish cooked from that recipe.
         One recipe → Many dishes. One image → Many containers.

COMMANDS:
  docker images          # List all images
  docker ps              # List running containers
  docker ps -a           # List all containers (including stopped)
  docker run <image>     # Create container from image
  docker build -t <tag>  # Build image from Dockerfile
""",
        'layer-architecture': """
╔══════════════════════════════════════════════════════════════════════════════╗
║                           LAYER ARCHITECTURE                                  ║
╚══════════════════════════════════════════════════════════════════════════════╝

Docker images are built as a stack of read-only layers:

  ┌─────────────────────────────────────────────────────────────┐
  │  Layer 5: COPY . /app                   (Application code) │ ← Changes often
  ├─────────────────────────────────────────────────────────────┤
  │  Layer 4: RUN pip install -r requirements.txt (Python deps)│
  ├─────────────────────────────────────────────────────────────┤
  │  Layer 3: WORKDIR /app                                      │
  ├─────────────────────────────────────────────────────────────┤
  │  Layer 2: RUN apt-get update && apt-get install -y curl    │
  ├─────────────────────────────────────────────────────────────┤
  │  Layer 1: FROM python:3.11-slim          (Base image)      │ ← Changes rarely
  └─────────────────────────────────────────────────────────────┘

KEY PROPERTIES:
  ✓ Each Dockerfile instruction = New layer
  ✓ Layers are immutable (read-only) once created
  ✓ Layers are cached and reused across builds
  ✓ Layers are shared between images (deduplication)
  ✓ Identified by SHA256 content hash

OPTIMIZATION TIP:
  Order instructions from LEAST changed → MOST changed
  to maximize cache hits during rebuilds.

COMMANDS:
  docker history <image>           # Show layers of an image
  docker inspect <image>           # Detailed layer information
  docker system df -v              # Show layer storage usage
""",
        'copy-on-write': """
╔══════════════════════════════════════════════════════════════════════════════╗
║                        COPY-ON-WRITE (CoW) MECHANISM                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

When a container runs, it gets a thin WRITABLE layer on top of image layers:

  ┌─────────────────────────────────────────────────────────────┐
  │  CONTAINER LAYER (Read/Write)        ← Thin, ephemeral     │
  │  • New files created here                                   │
  │  • Modified files copied here first                         │
  │  • Deleted files marked with "whiteout"                     │
  ╞═════════════════════════════════════════════════════════════╡
  │  IMAGE LAYERS (Read-Only)            ← Shared by all       │
  │  Layer 4: Application                  containers from      │
  │  Layer 3: Dependencies                 the same image       │
  │  Layer 2: System packages                                   │
  │  Layer 1: Base OS                                           │
  └─────────────────────────────────────────────────────────────┘

HOW IT WORKS:
  READ:   File read directly from image layer (fast, no copy)
  WRITE:  File copied to container layer, then modified (CoW)
  DELETE: Whiteout marker placed in container layer

BENEFITS:
  ⚡ Fast startup     - No need to copy entire image
  💾 Storage efficient - Containers share image layers
  🧠 Memory efficient  - Same files shared in page cache
  📸 Quick commits     - Only writable layer is saved

⚠️  WARNING: Container layer data is LOST when container is removed!
    Use VOLUMES for persistent data: docker run -v /host:/container

COMMANDS:
  docker diff <container>          # Show filesystem changes
  docker commit <container> <img>  # Save container layer as new image
"""
    }

    if topic and topic in concepts:
        print(concepts[topic])
    else:
        print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                         DOCKER CORE CONCEPTS                                  ║
╚══════════════════════════════════════════════════════════════════════════════╝

Available topics:
  1. images-vs-containers  - Understand the image/container relationship
  2. layer-architecture    - How Docker builds images in layers
  3. copy-on-write        - How containers efficiently share image data

Usage:
  python docker_deployment_helper.py explain                    # Show this menu
  python docker_deployment_helper.py explain images-vs-containers
  python docker_deployment_helper.py explain layer-architecture
  python docker_deployment_helper.py explain copy-on-write
  python docker_deployment_helper.py explain all               # Show all topics
""")
        if topic == 'all':
            for name, content in concepts.items():
                print(content)


def generate_dockerignore():
    """Generate a comprehensive .dockerignore file for build context optimization"""
    dockerignore_content = """# .dockerignore - Optimize Docker build context by excluding unnecessary files
# This file significantly speeds up builds and reduces the build context sent to Docker daemon

# Python cache and compiled files
__pycache__/
*.py[cod]
*$py.class
*.so
.Python

# Virtual environments
venv/
env/
ENV/
.venv/
.ENV/

# Distribution / packaging
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/
.nox/
coverage.xml
*.cover
.hypothesis/
.mypy_cache/
.dmypy.json
dmypy.json

# IDEs
.idea/
.vscode/
*.swp
*.swo
*~
.DS_Store

# Git
.git/
.gitignore
.gitattributes

# Docker
Dockerfile*
docker-compose*.yml
.dockerignore

# Documentation
*.md
docs/
README*
LICENSE
CHANGELOG*

# CI/CD
.github/
.gitlab-ci.yml
.travis.yml
Jenkinsfile
azure-pipelines.yml

# Environment files (should be passed at runtime, not baked in)
.env
.env.*
*.env

# Logs
*.log
logs/

# Temporary files
tmp/
temp/
*.tmp
*.bak

# OS files
Thumbs.db
.DS_Store

# Model files (should be mounted as volumes, not copied)
models/
*.pt
*.pth
*.h5
*.onnx
*.pkl
*.joblib

# Data files (should be mounted as volumes)
data/
*.csv
*.json
*.parquet

# Scripts not needed in container
scripts/
tools/
notebooks/
*.ipynb

# Configuration files for local development
local_settings.py
settings_local.py
"""

    # Write to current directory
    with open('.dockerignore', 'w') as f:
        f.write(dockerignore_content)

    print("✓ Generated .dockerignore file in current directory")
    print("\nThis file will:")
    print("  • Speed up Docker builds by reducing build context size")
    print("  • Prevent accidental inclusion of secrets and data files")
    print("  • Reduce cache invalidation from irrelevant file changes")
    print("\nReview and customize it based on your project needs.")


def copy_optimized_dockerfile(variant='alpine'):
    """Copy an optimized Dockerfile template to the current directory"""
    script_dir = Path(__file__).parent
    assets_dir = script_dir / 'assets'

    template_map = {
        'alpine': 'Dockerfile.optimized-alpine',
        'slim': 'Dockerfile.optimized-slim',
        'gunicorn': 'Dockerfile.production-gunicorn',
        'basic': 'Dockerfile.ai'
    }

    if variant not in template_map:
        print(f"✗ Unknown variant: {variant}")
        print(f"Available variants: {', '.join(template_map.keys())}")
        return False

    template_file = assets_dir / template_map[variant]

    if not template_file.exists():
        print(f"✗ Template file not found: {template_file}")
        return False

    # Copy to current directory as Dockerfile
    target_file = Path('Dockerfile')

    # Check if Dockerfile already exists
    if target_file.exists():
        response = input(f"Dockerfile already exists. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Aborted.")
            return False

    # Copy the file
    import shutil
    shutil.copy(template_file, target_file)

    print(f"✓ Copied {template_map[variant]} to Dockerfile")
    print(f"\nVariant: {variant}")

    if variant == 'alpine':
        print("  • Minimal image size (~50-150MB)")
        print("  • Best for lightweight applications")
        print("  • May have compatibility issues with some packages")
    elif variant == 'slim':
        print("  • Good balance of size and compatibility (~150-300MB)")
        print("  • Better package compatibility than Alpine")
        print("  • Recommended for AI/ML workloads")
    elif variant == 'gunicorn':
        print("  • Production-ready with Gunicorn workers")
        print("  • Includes health checks and logging")
        print("  • Environment variable configuration")
    elif variant == 'basic':
        print("  • Single-stage build (simpler but larger)")
        print("  • Good for development and getting started")

    print("\nNext steps:")
    print("  1. Review and customize the Dockerfile")
    print("  2. Build: docker build -t myapp .")
    print("  3. Run: docker run -p 8000:8000 myapp")

    return True


def show_optimization_guide():
    """Display comprehensive Docker image optimization guide"""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                   DOCKER IMAGE OPTIMIZATION GUIDE                            ║
╚══════════════════════════════════════════════════════════════════════════════╝

1. MULTI-STAGE BUILDS
   Separate build and runtime environments for smaller images

   Benefits:
   ✓ 50-80% smaller final images
   ✓ No build tools in production
   ✓ Better security posture
   ✓ Faster deployments

   Example:
   FROM python:3.12-alpine AS builder
   # Install dependencies...

   FROM python:3.12-alpine
   COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

2. BASE IMAGE SELECTION

   ┌─────────────────────┬─────────┬─────────────────────────────────────┐
   │ Base Image          │ Size    │ Use Case                            │
   ├─────────────────────┼─────────┼─────────────────────────────────────┤
   │ python:3.12         │ ~900MB  │ Development, full tooling           │
   │ python:3.12-slim    │ ~150MB  │ Production, good compatibility      │
   │ python:3.12-alpine  │ ~50MB   │ Production, minimal dependencies    │
   │ Multi-stage (slim)  │ 200-400 │ Production AI/ML                    │
   │ Multi-stage (alpine)│ 80-200  │ Production lightweight apps         │
   └─────────────────────┴─────────┴─────────────────────────────────────┘

3. UV PACKAGE MANAGER
   10-100x faster than pip for dependency installation

   Installation:
   RUN pip install --no-cache-dir uv && pip cache purge

   Usage:
   RUN uv pip install --system --no-cache -r requirements.txt

4. LAYER CACHING OPTIMIZATION
   Order instructions from least-changed to most-changed

   ✓ Good order:
   FROM python:3.12-alpine          # Base (never changes)
   RUN apk add --no-cache gcc       # System deps (rarely changes)
   COPY requirements.txt .          # Dependencies (occasionally changes)
   RUN uv pip install -r ...        # Install deps
   COPY . .                         # App code (frequently changes)

   ✗ Bad order:
   FROM python:3.12-alpine
   COPY . .                         # App code copied first
   COPY requirements.txt .          # Every code change invalidates deps
   RUN pip install -r ...

5. BUILD CONTEXT OPTIMIZATION
   Use .dockerignore to exclude unnecessary files

   Generate template:
   python docker_deployment_helper.py generate-dockerignore

   Common excludes:
   • __pycache__/, *.pyc
   • .git/, .github/
   • venv/, env/
   • *.md, docs/
   • tests/, notebooks/

6. CLEANUP STRATEGIES
   Remove unnecessary files in builder stage

   RUN find /usr/local -type d -name '__pycache__' -exec rm -rf {} + && \\
       find /usr/local -type f -name '*.pyc' -delete && \\
       find /usr/local -name 'tests' -type d -exec rm -rf {} +

7. SECURITY BEST PRACTICES
   ✓ Use non-root user
   ✓ Use minimal base images
   ✓ Don't include secrets in image
   ✓ Scan images for vulnerabilities
   ✓ Use specific version tags

QUICK START:
  1. Generate .dockerignore:
     python docker_deployment_helper.py generate-dockerignore

  2. Copy optimized Dockerfile:
     python docker_deployment_helper.py copy-dockerfile --variant alpine

  3. Build with BuildKit:
     DOCKER_BUILDKIT=1 docker build -t myapp .

  4. Analyze image:
     docker history myapp
     docker images | grep myapp
""")


def generate_ai_optimized_docker_compose():
    """Generate a docker-compose file optimized for AI services"""
    return """version: '3.8'

services:
  ai-service:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./models:/app/models
    environment:
      - PYTHONUNBUFFERED=1
      - TRANSFORMERS_CACHE=/app/models
    deploy:
      resources:
        limits:
          memory: 8G
          cpus: '4.0'
        reservations:
          memory: 4G
          cpus: '2.0'
    restart: unless-stopped
    shm_size: 8G  # Shared memory for AI operations

  # Optional: Add GPU support if available
  # ai-service-gpu:
  #   build:
  #     context: .
  #     dockerfile: Dockerfile.gpu
  #   ports:
  #     - "8001:8000"
  #   volumes:
  #     - ./data:/app/data
  #     - ./models:/app/models
  #   environment:
  #     - PYTHONUNBUFFERED=1
  #     - TRANSFORMERS_CACHE=/app/models
  #   deploy:
  #     resources:
  #       limits:
  #         memory: 12G
  #         cpus: '6.0'
  #         devices:
  #           - driver: nvidia
  #             count: 1
  #             capabilities: [gpu]
  #   restart: unless-stopped
  #   shm_size: 16G
"""


def main():
    parser = argparse.ArgumentParser(description='Docker Deployment Validation and Configuration for AI Services')
    parser.add_argument('action',
                        choices=['validate', 'recommend', 'configure', 'generate-compose', 'explain',
                                'diagnose', 'logs', 'inspect', 'exec', 'debug-guide',
                                'generate-dockerignore', 'copy-dockerfile', 'optimize-guide'],
                        help='Action to perform')
    parser.add_argument('container', nargs='?', default=None,
                        help='Container name or ID (for diagnose, logs, inspect, exec)')
    parser.add_argument('--topic', default=None,
                        choices=['images-vs-containers', 'layer-architecture', 'copy-on-write', 'restart-policies', 'all'],
                        help='Topic to explain (for explain action)')
    parser.add_argument('--tail', type=int, default=50,
                        help='Number of log lines to show (for logs action)')
    parser.add_argument('--follow', '-f', action='store_true',
                        help='Follow log output (for logs action)')
    parser.add_argument('--format', default=None,
                        help='Format string for inspect (for inspect action)')
    parser.add_argument('--command', default='/bin/bash',
                        help='Command to execute (for exec action)')
    parser.add_argument('--variant', default='alpine',
                        choices=['alpine', 'slim', 'gunicorn', 'basic'],
                        help='Dockerfile variant to copy (for copy-dockerfile action)')

    args = parser.parse_args()

    if args.action == 'validate':
        print("Validating Docker Desktop setup for AI services...")
        print("="*50)
        validations = validate_docker_desktop_prerequisites()

        print("\nValidation Summary:")
        print("="*20)
        all_passed = True
        for check, result in validations.items():
            status = "✓ PASS" if result else "✗ FAIL"
            print(f"{check}: {status}")
            if not result:
                all_passed = False

        if all_passed:
            print("\n✓ All Docker Desktop prerequisites validated successfully!")
        else:
            print("\n⚠ Some prerequisites failed. Please address the issues above.")
            sys.exit(1)

    elif args.action == 'recommend':
        recommend_ai_resources()

    elif args.action == 'configure':
        configure_docker_resources()

    elif args.action == 'generate-compose':
        content = generate_ai_optimized_docker_compose()
        print(content)

    elif args.action == 'explain':
        if args.topic == 'restart-policies':
            explain_restart_policies()
        else:
            explain_docker_concepts(args.topic)

    elif args.action == 'diagnose':
        if not args.container:
            print("Error: Container name or ID required for diagnose action")
            print("Usage: python docker_deployment_helper.py diagnose <container-name>")
            sys.exit(1)
        diagnose_container(args.container)

    elif args.action == 'logs':
        if not args.container:
            print("Error: Container name or ID required for logs action")
            print("Usage: python docker_deployment_helper.py logs <container-name> [--tail N] [--follow]")
            sys.exit(1)
        show_container_logs(args.container, tail=args.tail, follow=args.follow)

    elif args.action == 'inspect':
        if not args.container:
            print("Error: Container name or ID required for inspect action")
            print("Usage: python docker_deployment_helper.py inspect <container-name> [--format 'FORMAT']")
            sys.exit(1)
        inspect_container(args.container, format_string=args.format)

    elif args.action == 'exec':
        if not args.container:
            print("Error: Container name or ID required for exec action")
            print("Usage: python docker_deployment_helper.py exec <container-name> --command '<command>'")
            sys.exit(1)
        exec_in_container(args.container, args.command)

    elif args.action == 'debug-guide':
        show_debug_guide()

    elif args.action == 'generate-dockerignore':
        generate_dockerignore()

    elif args.action == 'copy-dockerfile':
        copy_optimized_dockerfile(variant=args.variant)

    elif args.action == 'optimize-guide':
        show_optimization_guide()


if __name__ == "__main__":
    main()