# Strimzi Kafka on Kubernetes Reference

Strimzi is a CNCF project that runs Apache Kafka on Kubernetes using Custom Resource Definitions (CRDs). It manages the full lifecycle: deployment, scaling, rolling upgrades, security, and monitoring.

## Architecture

```
Strimzi Cluster Operator (watches CRDs)
  │
  ├── Kafka CR              → Deploys broker + controller pods
  ├── KafkaNodePool CR      → Defines node roles, replicas, storage
  ├── KafkaTopic CR         → Manages topics declaratively
  ├── KafkaUser CR          → Manages ACLs and credentials
  ├── KafkaConnect CR       → Deploys Connect workers
  ├── KafkaMirrorMaker2 CR  → Cross-cluster replication
  └── Entity Operator       → Watches KafkaTopic + KafkaUser CRs
        ├── Topic Operator
        └── User Operator
```

## Installation

### Install Strimzi Operator

```bash
# Create namespace
kubectl create namespace kafka

# Install latest Strimzi operator
kubectl create -f 'https://strimzi.io/install/latest?namespace=kafka' -n kafka

# Wait for operator
kubectl wait deployment/strimzi-cluster-operator \
  --for=condition=Available --timeout=300s -n kafka

# Verify CRDs installed
kubectl get crd | grep strimzi
```

### Install via Helm (Alternative)

```bash
helm repo add strimzi https://strimzi.io/charts/
helm repo update

helm install strimzi-operator strimzi/strimzi-kafka-operator \
  --namespace kafka --create-namespace \
  --set watchNamespaces="{kafka}" \
  --set resources.requests.memory=256Mi \
  --set resources.requests.cpu=200m
```

## KRaft vs ZooKeeper

Strimzi supports both modes. **KRaft is recommended** for all new deployments (Kafka 3.3+).

| Aspect | KRaft | ZooKeeper |
|--------|-------|-----------|
| **Metadata management** | Built into Kafka (controller nodes) | External ZooKeeper ensemble |
| **Operational complexity** | One system to manage | Two systems to manage |
| **Recovery time** | Faster leader election | Slower (ZooKeeper round-trip) |
| **Scaling** | Millions of partitions | ~200K partition practical limit |
| **Strimzi config** | `annotations: strimzi.io/kraft: enabled` | Default in older Strimzi versions |
| **Status** | Production-ready (Kafka 3.6+) | Deprecated in Kafka 4.0 |

### KRaft Mode in Strimzi

KRaft requires **KafkaNodePool** resources to define node roles:

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: Kafka
metadata:
  name: my-cluster
  annotations:
    strimzi.io/kraft: enabled
    strimzi.io/node-pools: enabled
```

Node roles are defined via KafkaNodePool CRs (see below), not in the Kafka CR.

## Development Cluster (Docker Desktop / Minikube)

Single-node, combined controller+broker, minimal resources:

```yaml
# kafka-dev.yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaNodePool
metadata:
  name: combined
  namespace: kafka
  labels:
    strimzi.io/cluster: dev-cluster
spec:
  replicas: 1
  roles:
    - controller
    - broker
  storage:
    type: jbod
    volumes:
      - id: 0
        type: persistent-claim
        size: 5Gi
        deleteClaim: true
  resources:
    requests:
      memory: 1Gi
      cpu: 500m
    limits:
      memory: 2Gi
      cpu: 1000m
---
apiVersion: kafka.strimzi.io/v1beta2
kind: Kafka
metadata:
  name: dev-cluster
  namespace: kafka
  annotations:
    strimzi.io/kraft: enabled
    strimzi.io/node-pools: enabled
spec:
  kafka:
    version: 3.9.0
    metadataVersion: "3.9"
    listeners:
      - name: plain
        port: 9092
        type: internal
        tls: false
      - name: external
        port: 9094
        type: nodeport
        tls: false
        configuration:
          bootstrap:
            nodePort: 31092
    config:
      offsets.topic.replication.factor: 1
      transaction.state.log.replication.factor: 1
      transaction.state.log.min.isr: 1
      default.replication.factor: 1
      min.insync.replicas: 1
      auto.create.topics.enable: false
      log.retention.hours: 24
      num.partitions: 3
  entityOperator:
    topicOperator: {}
    userOperator: {}
```

```bash
kubectl apply -f kafka-dev.yaml -n kafka
kubectl wait kafka/dev-cluster --for=condition=Ready --timeout=300s -n kafka
```

## Production Cluster

Separate controller and broker node pools, TLS, persistent storage, resource limits:

```yaml
# kafka-production.yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaNodePool
metadata:
  name: controllers
  namespace: kafka
  labels:
    strimzi.io/cluster: prod-cluster
spec:
  replicas: 3
  roles:
    - controller
  storage:
    type: jbod
    volumes:
      - id: 0
        type: persistent-claim
        size: 10Gi
        class: fast-ssd
        deleteClaim: false
  resources:
    requests:
      memory: 2Gi
      cpu: 500m
    limits:
      memory: 4Gi
      cpu: 1000m
  template:
    pod:
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            - labelSelector:
                matchLabels:
                  strimzi.io/pool-name: controllers
              topologyKey: topology.kubernetes.io/zone
---
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaNodePool
metadata:
  name: brokers
  namespace: kafka
  labels:
    strimzi.io/cluster: prod-cluster
spec:
  replicas: 3
  roles:
    - broker
  storage:
    type: jbod
    volumes:
      - id: 0
        type: persistent-claim
        size: 500Gi
        class: fast-ssd
        deleteClaim: false
  resources:
    requests:
      memory: 8Gi
      cpu: 2000m
    limits:
      memory: 12Gi
      cpu: 4000m
  jvmOptions:
    -Xms: 6144m
    -Xmx: 6144m
    gcLoggingEnabled: true
  template:
    pod:
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            - labelSelector:
                matchLabels:
                  strimzi.io/pool-name: brokers
              topologyKey: topology.kubernetes.io/zone
---
apiVersion: kafka.strimzi.io/v1beta2
kind: Kafka
metadata:
  name: prod-cluster
  namespace: kafka
  annotations:
    strimzi.io/kraft: enabled
    strimzi.io/node-pools: enabled
spec:
  kafka:
    version: 3.9.0
    metadataVersion: "3.9"
    listeners:
      - name: tls
        port: 9093
        type: internal
        tls: true
        authentication:
          type: scram-sha-512
      - name: external
        port: 9094
        type: loadbalancer
        tls: true
        authentication:
          type: scram-sha-512
        configuration:
          bootstrap:
            annotations:
              service.beta.kubernetes.io/aws-load-balancer-type: nlb
    config:
      default.replication.factor: 3
      min.insync.replicas: 2
      offsets.topic.replication.factor: 3
      transaction.state.log.replication.factor: 3
      transaction.state.log.min.isr: 2
      auto.create.topics.enable: false
      unclean.leader.election.enable: false
      log.retention.hours: 168
      num.partitions: 6
      log.message.format.version: "3.9"
    rack:
      topologyKey: topology.kubernetes.io/zone
  entityOperator:
    topicOperator:
      resources:
        requests:
          memory: 256Mi
          cpu: 100m
    userOperator:
      resources:
        requests:
          memory: 256Mi
          cpu: 100m
```

```bash
kubectl apply -f kafka-production.yaml -n kafka
kubectl wait kafka/prod-cluster --for=condition=Ready --timeout=600s -n kafka
```

## KafkaTopic CR

Manage topics declaratively instead of using CLI commands:

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaTopic
metadata:
  name: task-events
  namespace: kafka
  labels:
    strimzi.io/cluster: prod-cluster
spec:
  partitions: 12
  replicas: 3
  config:
    retention.ms: "604800000"
    cleanup.policy: delete
    min.insync.replicas: "2"
    compression.type: lz4
```

## KafkaUser CR

Manage credentials and ACLs declaratively:

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaUser
metadata:
  name: task-api-producer
  namespace: kafka
  labels:
    strimzi.io/cluster: prod-cluster
spec:
  authentication:
    type: scram-sha-512
  authorization:
    type: simple
    acls:
      - resource:
          type: topic
          name: task-events
          patternType: literal
        operations:
          - Write
          - Describe
        host: "*"
---
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaUser
metadata:
  name: notification-consumer
  namespace: kafka
  labels:
    strimzi.io/cluster: prod-cluster
spec:
  authentication:
    type: scram-sha-512
  authorization:
    type: simple
    acls:
      - resource:
          type: topic
          name: task-events
          patternType: literal
        operations:
          - Read
          - Describe
        host: "*"
      - resource:
          type: group
          name: notification-svc
          patternType: literal
        operations:
          - Read
        host: "*"
```

Credentials are stored in a Kubernetes Secret automatically:

```bash
# Get generated password
kubectl get secret task-api-producer -n kafka \
  -o jsonpath='{.data.password}' | base64 -d
```

## Kafka Connect on Strimzi

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaConnect
metadata:
  name: my-connect
  namespace: kafka
  annotations:
    strimzi.io/use-connector-resources: "true"
spec:
  version: 3.9.0
  replicas: 2
  bootstrapServers: prod-cluster-kafka-bootstrap:9093
  tls:
    trustedCertificates:
      - secretName: prod-cluster-cluster-ca-cert
        certificate: ca.crt
  authentication:
    type: scram-sha-512
    username: connect-worker
    passwordSecret:
      secretName: connect-worker
      password: password
  config:
    group.id: connect-cluster
    offset.storage.topic: connect-offsets
    config.storage.topic: connect-configs
    status.storage.topic: connect-status
    config.storage.replication.factor: 3
    offset.storage.replication.factor: 3
    status.storage.replication.factor: 3
  build:
    output:
      type: docker
      image: my-registry.io/kafka-connect:latest
    plugins:
      - name: debezium-postgres
        artifacts:
          - type: tgz
            url: https://repo1.maven.org/maven2/io/debezium/debezium-connector-postgres/2.5.0.Final/debezium-connector-postgres-2.5.0.Final-plugin.tar.gz
```

## Listener Types

| Type | Access | Use Case |
|------|--------|----------|
| `internal` | Within Kubernetes only | Service-to-service within cluster |
| `nodeport` | Via node IP + port | Development, Docker Desktop |
| `loadbalancer` | Via cloud LB | Production external access (AWS NLB, GCP LB) |
| `ingress` | Via Kubernetes Ingress | Shared ingress controller |
| `cluster-ip` | Within Kubernetes only | Default internal access |
| `route` | Via OpenShift Route | OpenShift deployments |

## Operations

### Rolling Upgrade

Update the Kafka version in the CR — Strimzi handles the rolling restart:

```yaml
spec:
  kafka:
    version: 3.10.0          # Updated from 3.9.0
    metadataVersion: "3.9"    # Keep old version during rolling upgrade
```

After all brokers are upgraded:

```yaml
    metadataVersion: "3.10"   # Now safe to update metadata version
```

### Scaling Brokers

```yaml
# Edit the broker node pool
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaNodePool
metadata:
  name: brokers
spec:
  replicas: 5    # Scaled from 3 to 5
```

Strimzi adds new broker pods. Existing partitions stay on old brokers — use `kafka-reassign-partitions.sh` or Cruise Control to rebalance.

### Monitoring with Prometheus

```yaml
spec:
  kafka:
    metricsConfig:
      type: jmxPrometheusExporter
      valueFrom:
        configMapKeyRef:
          name: kafka-metrics
          key: kafka-metrics-config.yml
```

```yaml
# kafka-metrics ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: kafka-metrics
  namespace: kafka
data:
  kafka-metrics-config.yml: |
    lowercaseOutputName: true
    rules:
      - pattern: kafka.server<type=(.+), name=(.+)><>Value
        name: kafka_server_$1_$2
        type: GAUGE
      - pattern: kafka.server<type=(.+), name=(.+)><>Count
        name: kafka_server_$1_$2_total
        type: COUNTER
```

## Useful Commands

```bash
# Check cluster status
kubectl get kafka -n kafka
kubectl get kafkanodepools -n kafka

# Describe cluster (events, conditions)
kubectl describe kafka prod-cluster -n kafka

# List topics managed by operator
kubectl get kafkatopics -n kafka

# List users managed by operator
kubectl get kafkausers -n kafka

# View broker logs
kubectl logs prod-cluster-brokers-0 -n kafka

# Get bootstrap server address
kubectl get kafka prod-cluster -n kafka \
  -o jsonpath='{.status.listeners[*].bootstrapServers}'

# Port-forward for local access (alternative to nodeport)
kubectl port-forward svc/prod-cluster-kafka-bootstrap 9092:9092 -n kafka
```

## Dev vs Production Summary

| Setting | Development | Production |
|---------|-------------|------------|
| **Brokers** | 1 (combined mode) | 3+ brokers, 3 controllers |
| **Replication** | 1 | 3 |
| **min.insync.replicas** | 1 | 2 |
| **Storage** | 5Gi, deleteClaim: true | 500Gi, deleteClaim: false, SSD |
| **TLS** | Disabled | Enabled on all listeners |
| **Authentication** | None | SCRAM-SHA-512 or mTLS |
| **Resources** | 1-2Gi memory | 8-12Gi memory, 6Gi heap |
| **Anti-affinity** | None | Spread across zones |
| **Listener type** | nodeport | loadbalancer or ingress |
| **Retention** | 24 hours | 7+ days |
| **PDB** | None | maxUnavailable: 1 |
| **NetworkPolicy** | None | Restrict to app namespaces |
| **Cert rotation** | Default (30d renewal) | Custom renewal/validity days |
| **Cruise Control** | None | Enabled for auto-rebalance |

## Production Hardening

### Client Deployment: Mounting Strimzi Secrets

When Strimzi creates a `KafkaUser`, it generates a Kubernetes Secret containing the username and password. The cluster CA cert is in a separate Secret. Mount both into your application pod:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-api
  namespace: app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: order-api
  template:
    metadata:
      labels:
        app: order-api
    spec:
      containers:
        - name: order-api
          image: my-registry.io/order-api:latest
          env:
            - name: KAFKA_BOOTSTRAP
              value: "prod-cluster-kafka-bootstrap.kafka.svc:9093"
            - name: KAFKA_USERNAME
              valueFrom:
                secretKeyRef:
                  name: order-api-producer    # KafkaUser-generated Secret
                  key: username
            - name: KAFKA_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: order-api-producer
                  key: password
          volumeMounts:
            - name: kafka-ca
              mountPath: /etc/kafka/certs
              readOnly: true
      volumes:
        - name: kafka-ca
          secret:
            secretName: prod-cluster-cluster-ca-cert   # Strimzi cluster CA
            items:
              - key: ca.crt
                path: ca.crt
```

```python
# Application reads credentials from environment + mounted cert
import os
from confluent_kafka import Producer

producer = Producer({
    "bootstrap.servers": os.environ["KAFKA_BOOTSTRAP"],
    "security.protocol": "SASL_SSL",
    "sasl.mechanism": "SCRAM-SHA-512",
    "sasl.username": os.environ["KAFKA_USERNAME"],
    "sasl.password": os.environ["KAFKA_PASSWORD"],
    "ssl.ca.location": "/etc/kafka/certs/ca.crt",
    "acks": "all",
    "enable.idempotence": True,
})
```

```java
// Java equivalent
Properties props = new Properties();
props.put("bootstrap.servers", System.getenv("KAFKA_BOOTSTRAP"));
props.put("security.protocol", "SASL_SSL");
props.put("sasl.mechanism", "SCRAM-SHA-512");
props.put("sasl.jaas.config",
    "org.apache.kafka.common.security.scram.ScramLoginModule required " +
    "username=\"" + System.getenv("KAFKA_USERNAME") + "\" " +
    "password=\"" + System.getenv("KAFKA_PASSWORD") + "\";");
props.put("ssl.truststore.type", "PEM");
props.put("ssl.truststore.location", "/etc/kafka/certs/ca.crt");
```

#### Extracting Credentials

```bash
# Get cluster CA cert (for TLS trust)
kubectl get secret prod-cluster-cluster-ca-cert -n kafka \
  -o jsonpath='{.data.ca\.crt}' | base64 -d > ca.crt

# Get KafkaUser password
kubectl get secret order-api-producer -n kafka \
  -o jsonpath='{.data.password}' | base64 -d

# Get bootstrap address
kubectl get kafka prod-cluster -n kafka \
  -o jsonpath='{.status.listeners[?(@.name=="tls")].bootstrapServers}'
```

#### Cross-Namespace Access

If your app is in a different namespace than Kafka, copy the secrets:

```bash
# Copy cluster CA cert to app namespace
kubectl get secret prod-cluster-cluster-ca-cert -n kafka \
  -o json | jq 'del(.metadata.namespace,.metadata.resourceVersion,.metadata.uid,.metadata.creationTimestamp)' \
  | kubectl apply -n app -f -

# Copy KafkaUser secret to app namespace
kubectl get secret order-api-producer -n kafka \
  -o json | jq 'del(.metadata.namespace,.metadata.resourceVersion,.metadata.uid,.metadata.creationTimestamp)' \
  | kubectl apply -n app -f -
```

For automated sync, use **Reflector**, **kubernetes-replicator**, or **External Secrets Operator**.

### Pod Disruption Budgets

Prevent Kubernetes from evicting too many broker/controller pods simultaneously during node drains or upgrades:

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: kafka-brokers-pdb
  namespace: kafka
spec:
  maxUnavailable: 1
  selector:
    matchLabels:
      strimzi.io/cluster: prod-cluster
      strimzi.io/pool-name: brokers
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: kafka-controllers-pdb
  namespace: kafka
spec:
  maxUnavailable: 1
  selector:
    matchLabels:
      strimzi.io/cluster: prod-cluster
      strimzi.io/pool-name: controllers
```

**Why `maxUnavailable: 1`?** With `replication.factor=3` and `min.insync.replicas=2`, you can tolerate exactly 1 broker down. The PDB ensures Kubernetes never drains more than 1 at a time.

### Network Policies

Restrict which namespaces/pods can reach the Kafka brokers:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: kafka-broker-access
  namespace: kafka
spec:
  podSelector:
    matchLabels:
      strimzi.io/cluster: prod-cluster
      strimzi.io/kind: Kafka
  policyTypes:
    - Ingress
  ingress:
    # Allow traffic from app namespaces
    - from:
        - namespaceSelector:
            matchLabels:
              kafka-access: "true"
      ports:
        - port: 9093    # TLS listener
          protocol: TCP
    # Allow inter-broker + controller traffic within kafka namespace
    - from:
        - podSelector:
            matchLabels:
              strimzi.io/cluster: prod-cluster
      ports:
        - port: 9091    # Inter-broker
          protocol: TCP
        - port: 9090    # Controller
          protocol: TCP
    # Allow Strimzi operator
    - from:
        - podSelector:
            matchLabels:
              strimzi.io/kind: cluster-operator
      ports:
        - port: 9091
          protocol: TCP
```

```bash
# Label namespaces that need Kafka access
kubectl label namespace app kafka-access=true
kubectl label namespace data-pipeline kafka-access=true
```

### Certificate Rotation

Strimzi auto-manages cluster CA and client certificates. Configure renewal and validity periods:

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: Kafka
metadata:
  name: prod-cluster
  namespace: kafka
  annotations:
    strimzi.io/kraft: enabled
    strimzi.io/node-pools: enabled
spec:
  kafka:
    version: 3.9.0
    # ... listeners, config ...
  # Certificate lifecycle
  clusterCa:
    renewalDays: 30          # Start renewal 30 days before expiry
    validityDays: 365        # CA cert valid for 1 year
    generateCertificateAuthority: true
  clientsCa:
    renewalDays: 30
    validityDays: 365
    generateCertificateAuthority: true
```

**How rotation works:**
1. Strimzi generates new cert `renewalDays` before the old one expires
2. Both old and new certs are trusted during the overlap period
3. Brokers rolling-restart to pick up the new cert
4. After all pods restart, the old cert is removed

**Manual rotation trigger:**

```bash
# Force CA rotation (annotate the Secret)
kubectl annotate secret prod-cluster-cluster-ca -n kafka \
  strimzi.io/force-renew=true

# Force client cert rotation
kubectl annotate secret prod-cluster-clients-ca -n kafka \
  strimzi.io/force-renew=true
```

### Cruise Control (Partition Rebalancing)

When you scale brokers (e.g., 3→5), new brokers have no partitions. Cruise Control automatically rebalances:

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: Kafka
metadata:
  name: prod-cluster
  namespace: kafka
  annotations:
    strimzi.io/kraft: enabled
    strimzi.io/node-pools: enabled
spec:
  kafka:
    version: 3.9.0
    # ... listeners, config ...
  cruiseControl:
    resources:
      requests:
        memory: 512Mi
        cpu: 200m
      limits:
        memory: 1Gi
        cpu: 500m
    config:
      # Goals (ordered by priority)
      default.goals: >
        com.linkedin.kafka.cruisecontrol.analyzer.goals.RackAwareGoal,
        com.linkedin.kafka.cruisecontrol.analyzer.goals.ReplicaCapacityGoal,
        com.linkedin.kafka.cruisecontrol.analyzer.goals.DiskCapacityGoal,
        com.linkedin.kafka.cruisecontrol.analyzer.goals.NetworkInboundCapacityGoal,
        com.linkedin.kafka.cruisecontrol.analyzer.goals.NetworkOutboundCapacityGoal,
        com.linkedin.kafka.cruisecontrol.analyzer.goals.CpuCapacityGoal,
        com.linkedin.kafka.cruisecontrol.analyzer.goals.ReplicaDistributionGoal,
        com.linkedin.kafka.cruisecontrol.analyzer.goals.DiskUsageDistributionGoal
      # Throttle rebalance to avoid impacting production traffic
      execution.progress.check.interval.ms: 10000
  entityOperator:
    topicOperator: {}
    userOperator: {}
```

#### Triggering a Rebalance

```yaml
# KafkaRebalance CR — request a rebalance proposal
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaRebalance
metadata:
  name: rebalance-after-scale
  namespace: kafka
  labels:
    strimzi.io/cluster: prod-cluster
spec:
  goals:
    - DiskUsageDistributionGoal
    - ReplicaDistributionGoal
```

```bash
# Apply and check proposal
kubectl apply -f rebalance.yaml -n kafka
kubectl get kafkarebalance rebalance-after-scale -n kafka

# Approve the proposal
kubectl annotate kafkarebalance rebalance-after-scale -n kafka \
  strimzi.io/rebalance=approve

# Monitor progress
kubectl get kafkarebalance rebalance-after-scale -n kafka -w
```

**Rebalance states:** `New` → `ProposalReady` → `Rebalancing` → `Ready`

### Resource Quotas per User

Strimzi `KafkaUser` supports producer/consumer byte-rate quotas to prevent one client from monopolizing cluster bandwidth:

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaUser
metadata:
  name: batch-importer
  namespace: kafka
  labels:
    strimzi.io/cluster: prod-cluster
spec:
  authentication:
    type: scram-sha-512
  quotas:
    producerByteRate: 10485760     # 10 MB/s max produce rate
    consumerByteRate: 20971520     # 20 MB/s max consume rate
    requestPercentage: 25          # Max 25% of broker request handler capacity
    controllerMutationRate: 10     # Max 10 topic/partition mutations per second
  authorization:
    type: simple
    acls:
      - resource:
          type: topic
          name: bulk-import
          patternType: literal
        operations: [Write, Describe]
        host: "*"
```

**When to use quotas:**

| Quota | Use When |
|-------|----------|
| `producerByteRate` | Batch importers, CDC connectors — prevent flooding brokers |
| `consumerByteRate` | Analytics consumers doing large backfills |
| `requestPercentage` | Any client that shouldn't monopolize broker threads |
| `controllerMutationRate` | Clients that create/delete topics programmatically |

### Multiple Node Pools (Tiered Storage Classes)

Use separate node pools for different workload tiers:

```yaml
# High-throughput brokers for event streams
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaNodePool
metadata:
  name: brokers-hot
  namespace: kafka
  labels:
    strimzi.io/cluster: prod-cluster
spec:
  replicas: 3
  roles:
    - broker
  storage:
    type: jbod
    volumes:
      - id: 0
        type: persistent-claim
        size: 500Gi
        class: fast-ssd           # NVMe or local SSD
        deleteClaim: false
  resources:
    requests:
      memory: 12Gi
      cpu: 4000m
    limits:
      memory: 16Gi
      cpu: 8000m
  jvmOptions:
    -Xms: 8192m
    -Xmx: 8192m
  template:
    pod:
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            - labelSelector:
                matchLabels:
                  strimzi.io/pool-name: brokers-hot
              topologyKey: topology.kubernetes.io/zone
---
# Cost-optimized brokers for audit/log topics with longer retention
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaNodePool
metadata:
  name: brokers-warm
  namespace: kafka
  labels:
    strimzi.io/cluster: prod-cluster
spec:
  replicas: 3
  roles:
    - broker
  storage:
    type: jbod
    volumes:
      - id: 0
        type: persistent-claim
        size: 2Ti
        class: standard-hdd      # Cheaper, higher capacity
        deleteClaim: false
  resources:
    requests:
      memory: 4Gi
      cpu: 1000m
    limits:
      memory: 8Gi
      cpu: 2000m
  jvmOptions:
    -Xms: 4096m
    -Xmx: 4096m
  template:
    pod:
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            - labelSelector:
                matchLabels:
                  strimzi.io/pool-name: brokers-warm
              topologyKey: topology.kubernetes.io/zone
```

Assign topics to specific broker pools using `replica-assignment` or Cruise Control goals that respect rack/pool labels.

### Production Checklist (Strimzi-Specific)

| Category | Item | Status |
|----------|------|--------|
| **Security** | TLS on all listeners | `tls: true` |
| | SCRAM-SHA-512 or mTLS authentication | `authentication.type: scram-sha-512` |
| | Least-privilege ACLs per KafkaUser | `authorization.type: simple` |
| | NetworkPolicy restricting broker access | See NetworkPolicy section |
| | Cert rotation configured | `clusterCa.renewalDays`, `clientsCa.renewalDays` |
| **Availability** | 3+ controllers, 3+ brokers | Separate KafkaNodePools |
| | Anti-affinity across AZs | `topologyKey: topology.kubernetes.io/zone` |
| | PodDisruptionBudget `maxUnavailable: 1` | See PDB section |
| | `unclean.leader.election.enable: false` | In Kafka CR config |
| **Resources** | Broker memory: 8-12Gi, heap: 6Gi | In KafkaNodePool `resources` + `jvmOptions` |
| | Controller memory: 2-4Gi | Separate pool with lighter resources |
| | Resource quotas for batch/bulk clients | `KafkaUser.spec.quotas` |
| | Storage class: SSD for brokers | `class: fast-ssd` |
| **Operations** | Cruise Control enabled | See Cruise Control section |
| | Entity Operator for topics + users | `entityOperator` in Kafka CR |
| | Monitoring via JMX Prometheus exporter | `metricsConfig` in Kafka CR |
| | `deleteClaim: false` for broker storage | Prevents data loss on scale-down |
