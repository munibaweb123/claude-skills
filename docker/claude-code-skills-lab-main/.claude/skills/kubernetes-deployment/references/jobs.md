# Kubernetes Jobs and CronJobs Reference

## Quick Reference

| Field | Job | CronJob | Purpose |
|-------|-----|---------|---------|
| `completions` | ✓ | ✓ (in jobTemplate) | Total successful pods needed |
| `parallelism` | ✓ | ✓ (in jobTemplate) | Concurrent pods |
| `backoffLimit` | ✓ | ✓ (in jobTemplate) | Max retries before failure |
| `activeDeadlineSeconds` | ✓ | ✓ (in jobTemplate) | Timeout for entire Job |
| `ttlSecondsAfterFinished` | ✓ | ✓ (in jobTemplate) | Auto-cleanup delay |
| `schedule` | ✗ | ✓ | Cron expression |
| `concurrencyPolicy` | ✗ | ✓ | Handle overlapping runs |

---

## Job vs Deployment

| Aspect | Job | Deployment |
|--------|-----|------------|
| Purpose | Run to completion | Run continuously |
| restartPolicy | `Never` or `OnFailure` | `Always` |
| Completion | Terminates when done | Never terminates |
| Scaling | `completions` + `parallelism` | `replicas` |
| Use case | Batch processing, migrations | Web servers, APIs |

---

## Job Patterns

### Pattern 1: Single Task (Default)

Run one pod to completion:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migration
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: migrate
        image: myapp:1.0
        command: ["python", "manage.py", "migrate"]
        resources:
          requests:
            cpu: "100m"
            memory: "256Mi"
          limits:
            cpu: "500m"
            memory: "512Mi"
```

### Pattern 2: Fixed Completions (Queue Processing)

Process exactly N items:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: process-queue
spec:
  completions: 10        # Need 10 successful completions
  parallelism: 3         # Run 3 pods concurrently
  backoffLimit: 5        # Allow 5 total failures
  template:
    spec:
      restartPolicy: OnFailure
      containers:
      - name: worker
        image: worker:1.0
        resources:
          requests:
            cpu: "200m"
            memory: "256Mi"
          limits:
            cpu: "1"
            memory: "512Mi"
```

**Execution timeline:**
```
Time 0:   [Pod-0] [Pod-1] [Pod-2] running (parallelism=3)
Time 5s:  [Pod-0✓] completes → [Pod-3] starts
Time 8s:  [Pod-1✓] completes → [Pod-4] starts
Time 12s: [Pod-2✓] completes → [Pod-5] starts
...continues until 10 completions
```

### Pattern 3: Indexed Jobs (K8s 1.21+)

Each pod gets a unique index (0, 1, 2, ...):

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: indexed-processor
spec:
  completions: 5
  parallelism: 5
  completionMode: Indexed  # Enable indexed mode
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: worker
        image: python:3.11-slim
        command: ["python", "-c"]
        args:
          - |
            import os
            index = int(os.environ['JOB_COMPLETION_INDEX'])
            print(f"Processing partition {index} of 5")
            # Process data partition based on index
        env:
        - name: JOB_COMPLETION_INDEX
          valueFrom:
            fieldRef:
              fieldPath: metadata.annotations['batch.kubernetes.io/job-completion-index']
        resources:
          requests:
            cpu: "100m"
            memory: "128Mi"
          limits:
            cpu: "500m"
            memory: "256Mi"
```

### Pattern 4: Work Queue (External Queue)

Pods pull work from external queue until empty:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: queue-worker
spec:
  parallelism: 5           # 5 workers
  # No completions set - runs until all pods exit successfully
  template:
    spec:
      restartPolicy: OnFailure
      containers:
      - name: worker
        image: worker:1.0
        env:
        - name: QUEUE_URL
          value: "redis://redis:6379/0"
        command: ["python", "worker.py"]
        # Worker exits 0 when queue is empty
        resources:
          requests:
            cpu: "200m"
            memory: "256Mi"
          limits:
            cpu: "1"
            memory: "512Mi"
```

---

## Job Failure Handling

### backoffLimit

Maximum number of pod failures before marking Job as failed:

```yaml
spec:
  backoffLimit: 6  # Default is 6
```

**Backoff timing:** 10s, 20s, 40s, 80s... (exponential, capped at 6 minutes)

### activeDeadlineSeconds

Timeout for the entire Job:

```yaml
spec:
  activeDeadlineSeconds: 600  # Fail if not done in 10 minutes
```

### Pod Failure Policy (K8s 1.26+)

Fine-grained control over failure handling:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: with-failure-policy
spec:
  backoffLimit: 6
  podFailurePolicy:
    rules:
    # Don't count OOMKilled as failure (increase limit instead)
    - action: Ignore
      onExitCodes:
        containerName: worker
        operator: In
        values: [137]  # OOMKilled
    # Fail immediately on config errors
    - action: FailJob
      onExitCodes:
        containerName: worker
        operator: In
        values: [42]   # Custom "config error" exit code
    # Count other errors toward backoffLimit
    - action: Count
      onExitCodes:
        containerName: worker
        operator: NotIn
        values: [0, 137, 42]
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: worker
        image: worker:1.0
        resources:
          requests:
            cpu: "100m"
            memory: "128Mi"
          limits:
            cpu: "500m"
            memory: "256Mi"
```

---

## Job Cleanup

### ttlSecondsAfterFinished

Auto-delete completed Jobs:

```yaml
spec:
  ttlSecondsAfterFinished: 3600  # Delete 1 hour after completion
```

### Manual Cleanup

```bash
# Delete completed Jobs older than 1 hour
kubectl delete jobs --field-selector status.successful=1 -n batch

# Delete all failed Jobs
kubectl delete jobs --field-selector status.failed=1 -n batch
```

---

## CronJob Configuration

### Schedule Syntax

```
┌───────────── minute (0-59)
│ ┌───────────── hour (0-23)
│ │ ┌───────────── day of month (1-31)
│ │ │ ┌───────────── month (1-12)
│ │ │ │ ┌───────────── day of week (0-6, Sun=0)
│ │ │ │ │
* * * * *
```

| Schedule | Meaning |
|----------|---------|
| `*/15 * * * *` | Every 15 minutes |
| `0 * * * *` | Every hour |
| `0 0 * * *` | Daily at midnight |
| `0 2 * * *` | Daily at 2 AM |
| `0 0 * * 0` | Weekly on Sunday |
| `0 0 1 * *` | Monthly on 1st |
| `0 0 1 1 *` | Yearly on Jan 1st |

### Timezone Support (K8s 1.27+)

```yaml
spec:
  schedule: "0 9 * * 1-5"      # 9 AM weekdays
  timeZone: "America/New_York"  # In Eastern time
```

### Concurrency Policy

| Policy | Behavior |
|--------|----------|
| `Allow` (default) | Multiple Jobs can run simultaneously |
| `Forbid` | Skip new Job if previous still running |
| `Replace` | Cancel running Job and start new one |

```yaml
spec:
  concurrencyPolicy: Forbid  # Recommended for most cases
```

### History Limits

```yaml
spec:
  successfulJobsHistoryLimit: 3  # Keep last 3 successful (default)
  failedJobsHistoryLimit: 1      # Keep last 1 failed (default)
```

### Starting Deadline

Skip scheduled run if it can't start in time:

```yaml
spec:
  startingDeadlineSeconds: 200  # Skip if >200s late
```

---

## Complete CronJob Example

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: daily-report
  namespace: batch
spec:
  schedule: "0 6 * * *"           # Daily at 6 AM
  timeZone: "UTC"
  concurrencyPolicy: Forbid
  successfulJobsHistoryLimit: 7   # Keep 1 week of history
  failedJobsHistoryLimit: 3
  startingDeadlineSeconds: 300
  jobTemplate:
    spec:
      backoffLimit: 2
      activeDeadlineSeconds: 1800  # 30 min timeout
      ttlSecondsAfterFinished: 86400  # Cleanup after 24 hours
      template:
        metadata:
          labels:
            app: daily-report
        spec:
          restartPolicy: OnFailure
          containers:
          - name: reporter
            image: reporter:1.0
            env:
            - name: REPORT_DATE
              value: "yesterday"
            - name: SMTP_SERVER
              valueFrom:
                configMapKeyRef:
                  name: email-config
                  key: smtp_server
            - name: SMTP_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: email-secrets
                  key: password
            resources:
              requests:
                cpu: "200m"
                memory: "256Mi"
              limits:
                cpu: "1"
                memory: "1Gi"
          # Optional: Node selection for batch workloads
          nodeSelector:
            workload-type: batch
          tolerations:
          - key: "batch"
            operator: "Equal"
            value: "true"
            effect: "NoSchedule"
```

---

## AI/ML Batch Job Patterns

### Training Job with GPU

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: model-training
spec:
  backoffLimit: 2
  activeDeadlineSeconds: 86400  # 24 hour timeout
  template:
    spec:
      restartPolicy: OnFailure
      containers:
      - name: trainer
        image: pytorch-trainer:1.0
        command: ["python", "train.py"]
        args:
          - "--epochs=100"
          - "--batch-size=32"
          - "--checkpoint-dir=/checkpoints"
        resources:
          requests:
            cpu: "4"
            memory: "16Gi"
            nvidia.com/gpu: "1"
          limits:
            cpu: "8"
            memory: "32Gi"
            nvidia.com/gpu: "1"
        volumeMounts:
        - name: checkpoints
          mountPath: /checkpoints
        - name: dataset
          mountPath: /data
          readOnly: true
      volumes:
      - name: checkpoints
        persistentVolumeClaim:
          claimName: training-checkpoints
      - name: dataset
        persistentVolumeClaim:
          claimName: training-dataset
      nodeSelector:
        gpu-type: nvidia-a100
```

### Distributed Training with Indexed Jobs

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: distributed-training
spec:
  completions: 4           # 4 workers
  parallelism: 4           # All run simultaneously
  completionMode: Indexed
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: worker
        image: distributed-trainer:1.0
        env:
        - name: WORLD_SIZE
          value: "4"
        - name: RANK
          valueFrom:
            fieldRef:
              fieldPath: metadata.annotations['batch.kubernetes.io/job-completion-index']
        - name: MASTER_ADDR
          value: "distributed-training-0"  # First pod is master
        - name: MASTER_PORT
          value: "29500"
        resources:
          requests:
            nvidia.com/gpu: "1"
          limits:
            nvidia.com/gpu: "1"
```

---

## Essential Commands

```bash
# Create Job
kubectl apply -f job.yaml

# List Jobs
kubectl get jobs -n batch
kubectl get jobs -o wide

# Watch Job progress
kubectl get jobs -w

# View Job details
kubectl describe job data-processor

# View Job pods
kubectl get pods -l job-name=data-processor

# View logs from Job pod
kubectl logs job/data-processor
kubectl logs -l job-name=data-processor --tail=100

# Delete Job (and its pods)
kubectl delete job data-processor

# CronJob commands
kubectl get cronjobs
kubectl describe cronjob daily-report

# Manually trigger CronJob
kubectl create job manual-run --from=cronjob/daily-report

# Suspend CronJob
kubectl patch cronjob daily-report -p '{"spec":{"suspend":true}}'

# Resume CronJob
kubectl patch cronjob daily-report -p '{"spec":{"suspend":false}}'

# View CronJob history
kubectl get jobs -l cronjob-name=daily-report
```

---

## Troubleshooting

| Symptom | Cause | Solution |
|---------|-------|----------|
| Job stuck in `Active` | Pods failing repeatedly | Check `backoffLimit`, view pod logs |
| Job `Failed` immediately | `backoffLimit` reached | Increase limit or fix pod errors |
| CronJob not creating Jobs | Suspended or schedule issue | Check `suspend` field, validate cron syntax |
| Overlapping CronJob runs | Long-running Jobs | Set `concurrencyPolicy: Forbid` |
| Jobs not cleaning up | No TTL set | Add `ttlSecondsAfterFinished` |
| Pods stuck `Pending` | Resource constraints | Reduce requests or add nodes |

### Debugging Workflow

```bash
# 1. Check Job status
kubectl get job data-processor -o yaml

# 2. Check pod status
kubectl get pods -l job-name=data-processor

# 3. View pod events
kubectl describe pod <pod-name>

# 4. Check logs (including failed pods)
kubectl logs <pod-name>
kubectl logs <pod-name> --previous  # If restarted

# 5. Check Job events
kubectl describe job data-processor | grep -A20 Events
```

---

## Best Practices

1. **Always set `backoffLimit`** - Prevent infinite retries
2. **Always set `activeDeadlineSeconds`** - Prevent runaway Jobs
3. **Use `ttlSecondsAfterFinished`** - Automatic cleanup
4. **Use `restartPolicy: OnFailure`** for retryable tasks
5. **Use `restartPolicy: Never`** when you need to debug failed pods
6. **Set resource requests/limits** - Ensure scheduling and prevent OOM
7. **Use `concurrencyPolicy: Forbid`** for CronJobs by default
8. **Use Indexed Jobs** for parallel processing with deterministic work assignment
9. **Add labels** for easy filtering and monitoring
10. **Use PodDisruptionBudget** for long-running batch Jobs
