"""Simple Kafka producer example using confluent-kafka."""

import json
import time
from confluent_kafka import Producer


def delivery_report(err, msg):
    """Callback for message delivery reports."""
    if err is not None:
        print(f"Delivery failed for {msg.key()}: {err}")
    else:
        print(f"Delivered to {msg.topic()} [{msg.partition()}] @ offset {msg.offset()}")


def main():
    conf = {
        "bootstrap.servers": "localhost:9092",
        "client.id": "example-producer",
        "acks": "all",
        "enable.idempotence": True,
    }

    producer = Producer(conf)
    topic = "hello-world"

    for i in range(10):
        message = {"id": i, "message": f"Hello Kafka #{i}", "timestamp": time.time()}
        producer.produce(
            topic=topic,
            key=str(i),
            value=json.dumps(message).encode("utf-8"),
            callback=delivery_report,
        )
        producer.poll(0)

    # Wait for all messages to be delivered
    remaining = producer.flush(timeout=10)
    if remaining > 0:
        print(f"Warning: {remaining} messages still in queue")
    else:
        print("All messages delivered successfully")


if __name__ == "__main__":
    main()
