# Kafka Security Reference

## Security Overview

```
Client ──[SSL/TLS]──> Broker ──[SASL Auth]──> [ACL Check] ──> Topic
```

Three pillars:
1. **Encryption** — SSL/TLS for data in transit
2. **Authentication** — SASL (SCRAM, OAUTHBEARER, GSSAPI/Kerberos, PLAIN)
3. **Authorization** — ACLs (Access Control Lists)

## SSL/TLS Encryption

### Generate Certificates

```bash
# 1. Create CA
openssl req -new -x509 -keyout ca-key -out ca-cert -days 365 \
  -subj "/CN=KafkaCA" -passout pass:ca-password

# 2. Create broker keystore
keytool -keystore broker.keystore.jks -alias broker \
  -genkey -keyalg RSA -validity 365 -storepass keystore-password \
  -dname "CN=broker.example.com"

# 3. Create CSR
keytool -keystore broker.keystore.jks -alias broker \
  -certreq -file broker.csr -storepass keystore-password

# 4. Sign with CA
openssl x509 -req -CA ca-cert -CAkey ca-key -in broker.csr \
  -out broker-signed.cert -days 365 -CAcreateserial -passin pass:ca-password

# 5. Import CA and signed cert into keystore
keytool -keystore broker.keystore.jks -alias CARoot \
  -importcert -file ca-cert -storepass keystore-password -noprompt
keytool -keystore broker.keystore.jks -alias broker \
  -importcert -file broker-signed.cert -storepass keystore-password

# 6. Create truststore with CA cert
keytool -keystore broker.truststore.jks -alias CARoot \
  -importcert -file ca-cert -storepass truststore-password -noprompt
```

### Broker SSL Configuration

```properties
# server.properties
listeners=SSL://0.0.0.0:9093
advertised.listeners=SSL://broker1.example.com:9093

ssl.keystore.location=/var/kafka/ssl/broker.keystore.jks
ssl.keystore.password=keystore-password
ssl.key.password=keystore-password
ssl.truststore.location=/var/kafka/ssl/broker.truststore.jks
ssl.truststore.password=truststore-password

# Inter-broker SSL
security.inter.broker.protocol=SSL

# Require client authentication (mutual TLS)
ssl.client.auth=required

# Protocol and cipher configuration
ssl.enabled.protocols=TLSv1.3,TLSv1.2
ssl.protocol=TLSv1.3
```

### Client SSL Configuration

```properties
# Java client
security.protocol=SSL
ssl.truststore.location=/var/kafka/ssl/client.truststore.jks
ssl.truststore.password=truststore-password
# For mutual TLS:
ssl.keystore.location=/var/kafka/ssl/client.keystore.jks
ssl.keystore.password=keystore-password
ssl.key.password=keystore-password
```

```python
# Python confluent-kafka
conf = {
    'bootstrap.servers': 'broker1:9093',
    'security.protocol': 'SSL',
    'ssl.ca.location': '/var/kafka/ssl/ca-cert.pem',
    'ssl.certificate.location': '/var/kafka/ssl/client-cert.pem',
    'ssl.key.location': '/var/kafka/ssl/client-key.pem',
    'ssl.key.password': 'key-password',
}
```

## SASL Authentication

### SASL/SCRAM (Username/Password)

#### Broker Setup

```properties
# server.properties
listeners=SASL_SSL://0.0.0.0:9094
advertised.listeners=SASL_SSL://broker1.example.com:9094
security.inter.broker.protocol=SASL_SSL

sasl.enabled.mechanisms=SCRAM-SHA-512
sasl.mechanism.inter.broker.protocol=SCRAM-SHA-512

# JAAS config (inline)
listener.name.sasl_ssl.scram-sha-512.sasl.jaas.config=\
  org.apache.kafka.common.security.scram.ScramLoginModule required \
  username="admin" \
  password="admin-secret";
```

```bash
# Create SCRAM credentials
bin/kafka-configs.sh --bootstrap-server localhost:9092 \
  --alter --add-config 'SCRAM-SHA-512=[password=client-secret]' \
  --entity-type users --entity-name my-app
```

#### Client Setup

```properties
security.protocol=SASL_SSL
sasl.mechanism=SCRAM-SHA-512
sasl.jaas.config=org.apache.kafka.common.security.scram.ScramLoginModule required \
  username="my-app" \
  password="client-secret";
```

### SASL/OAUTHBEARER

For OAuth 2.0 / OIDC integration:

```properties
# Broker
sasl.enabled.mechanisms=OAUTHBEARER
sasl.mechanism.inter.broker.protocol=OAUTHBEARER
listener.name.sasl_ssl.oauthbearer.sasl.jaas.config=\
  org.apache.kafka.common.security.oauthbearer.OAuthBearerLoginModule required;
listener.name.sasl_ssl.oauthbearer.sasl.login.callback.handler.class=\
  org.apache.kafka.common.security.oauthbearer.secured.OAuthBearerLoginCallbackHandler
listener.name.sasl_ssl.oauthbearer.sasl.server.callback.handler.class=\
  org.apache.kafka.common.security.oauthbearer.secured.OAuthBearerValidatorCallbackHandler
listener.name.sasl_ssl.oauthbearer.sasl.oauthbearer.jwks.endpoint.url=https://idp.example.com/.well-known/jwks.json
listener.name.sasl_ssl.oauthbearer.sasl.oauthbearer.expected.audience=kafka
```

### SASL/GSSAPI (Kerberos)

```properties
# Broker
sasl.enabled.mechanisms=GSSAPI
sasl.kerberos.service.name=kafka
listener.name.sasl_ssl.gssapi.sasl.jaas.config=\
  com.sun.security.auth.module.Krb5LoginModule required \
  useKeyTab=true \
  storeKey=true \
  keyTab="/etc/security/keytabs/kafka.keytab" \
  principal="kafka/broker1.example.com@EXAMPLE.COM";
```

## ACLs (Authorization)

### Enable ACLs

```properties
# server.properties
authorizer.class.name=org.apache.kafka.metadata.authorizer.StandardAuthorizer
# Allow broker operations
super.users=User:admin
# Deny by default when ACLs exist
allow.everyone.if.no.acl.found=false
```

### Managing ACLs

```bash
# Grant producer access to a topic
bin/kafka-acls.sh --bootstrap-server localhost:9092 \
  --add --allow-principal User:producer-app \
  --operation Write --operation Describe \
  --topic orders

# Grant consumer access to a topic + consumer group
bin/kafka-acls.sh --bootstrap-server localhost:9092 \
  --add --allow-principal User:consumer-app \
  --operation Read --operation Describe \
  --topic orders

bin/kafka-acls.sh --bootstrap-server localhost:9092 \
  --add --allow-principal User:consumer-app \
  --operation Read \
  --group order-processors

# Grant access using prefix (all topics starting with "app-")
bin/kafka-acls.sh --bootstrap-server localhost:9092 \
  --add --allow-principal User:my-app \
  --operation All \
  --topic app- --resource-pattern-type prefixed

# List all ACLs
bin/kafka-acls.sh --bootstrap-server localhost:9092 --list

# Remove ACL
bin/kafka-acls.sh --bootstrap-server localhost:9092 \
  --remove --allow-principal User:old-app \
  --operation Write --topic orders
```

### ACL Operations

| Operation | Applies To |
|-----------|-----------|
| `Read` | Topic (consume), Group (join) |
| `Write` | Topic (produce) |
| `Create` | Topic, Cluster |
| `Delete` | Topic |
| `Alter` | Topic, Cluster |
| `Describe` | Topic, Group, Cluster |
| `ClusterAction` | Cluster (inter-broker) |
| `DescribeConfigs` | Topic, Cluster |
| `AlterConfigs` | Topic, Cluster |
| `All` | All of the above |

## Security Best Practices

1. **Always use SSL/TLS** in production — encrypt all client and inter-broker traffic
2. **Use SCRAM-SHA-512** over PLAIN — passwords are salted and hashed
3. **Enable ACLs** with `allow.everyone.if.no.acl.found=false` — deny by default
4. **Use least-privilege ACLs** — grant only needed operations per application
5. **Rotate credentials** — use short-lived tokens (OAUTHBEARER) when possible
6. **Separate listeners** — use different ports for client vs inter-broker traffic
7. **Audit access** — enable Kafka authorizer logging
8. **Secure ZooKeeper/KRaft** — protect metadata with authentication

## SASL_SSL Client Configuration Reference

When connecting to a Kafka cluster secured with both TLS encryption and SASL authentication (the production standard), clients must configure both layers.

### Python (confluent-kafka)

```python
from confluent_kafka import Producer, Consumer

# Producer — SASL_SSL + SCRAM-SHA-512
producer = Producer({
    "bootstrap.servers": "broker1:9093,broker2:9093,broker3:9093",
    "security.protocol": "SASL_SSL",
    "sasl.mechanism": "SCRAM-SHA-512",
    "sasl.username": "order-api-producer",
    "sasl.password": "secret-from-vault",
    "ssl.ca.location": "/etc/kafka/certs/ca.crt",
    "acks": "all",
    "enable.idempotence": True,
})

# Consumer — same security config
consumer = Consumer({
    "bootstrap.servers": "broker1:9093,broker2:9093,broker3:9093",
    "security.protocol": "SASL_SSL",
    "sasl.mechanism": "SCRAM-SHA-512",
    "sasl.username": "notification-consumer",
    "sasl.password": "secret-from-vault",
    "ssl.ca.location": "/etc/kafka/certs/ca.crt",
    "group.id": "notification-svc",
    "auto.offset.reset": "earliest",
    "enable.auto.commit": False,
})
```

### Java

```java
Properties props = new Properties();
props.put("bootstrap.servers", "broker1:9093,broker2:9093,broker3:9093");
props.put("security.protocol", "SASL_SSL");
props.put("sasl.mechanism", "SCRAM-SHA-512");
props.put("sasl.jaas.config",
    "org.apache.kafka.common.security.scram.ScramLoginModule required " +
    "username=\"order-api-producer\" " +
    "password=\"secret-from-vault\";");

// Option A: PEM file (Strimzi CA cert extracted as PEM)
props.put("ssl.truststore.type", "PEM");
props.put("ssl.truststore.location", "/etc/kafka/certs/ca.crt");

// Option B: JKS truststore (traditional Java)
// props.put("ssl.truststore.location", "/etc/kafka/certs/truststore.jks");
// props.put("ssl.truststore.password", "truststore-password");
```

### Security Protocol Matrix

| Protocol | Encryption | Authentication | Use When |
|----------|-----------|----------------|----------|
| `PLAINTEXT` | None | None | Development only |
| `SSL` | TLS | mTLS (client cert) | Client cert-based auth, no passwords |
| `SASL_PLAINTEXT` | None | SASL (password/token) | **Never in production** — passwords sent in clear text |
| `SASL_SSL` | TLS | SASL (SCRAM/OAUTHBEARER) | **Production standard** — encrypted + authenticated |

### Authentication Mechanism Comparison

| Mechanism | Credential Type | Rotation | Complexity | Best For |
|-----------|----------------|----------|------------|----------|
| `SCRAM-SHA-512` | Username + password | Manual (update KafkaUser Secret) | Low | Most production deployments |
| `OAUTHBEARER` | Short-lived JWT token | Automatic (token refresh) | High (requires OIDC provider) | Enterprise with existing IdP |
| `GSSAPI` (Kerberos) | Kerberos ticket | Automatic (kinit renewal) | Very high | Enterprise with existing Kerberos |
| mTLS (`SSL`) | Client certificate | Strimzi auto-renews via `clientsCa` | Medium | Zero-password environments |

### Strimzi-Specific: How TLS + SCRAM Work Together

```
Strimzi manages three certificate layers:

1. Cluster CA (cluster-ca-cert)
   └─ Signs broker server certificates
   └─ Clients trust this CA to verify broker identity

2. Clients CA (clients-ca-cert)
   └─ Signs KafkaUser certificates (for mTLS auth)
   └─ Only used when authentication.type: tls

3. SCRAM credentials (per KafkaUser Secret)
   └─ Username + password stored in K8s Secret
   └─ Client provides over TLS-encrypted channel

For SCRAM-SHA-512:
  Client → [TLS encrypts channel using cluster CA] → Broker
  Client → [SCRAM handshake over encrypted channel] → Broker verifies password
  = Encryption (TLS) + Authentication (SCRAM) are independent layers
```
