"""Simple Kafka consumer example using confluent-kafka."""

import json
import signal
import sys
from confluent_kafka import Consumer, KafkaError

running = True


def signal_handler(sig, frame):
    global running
    running = False


def main():
    signal.signal(signal.SIGINT, signal_handler)

    conf = {
        "bootstrap.servers": "localhost:9092",
        "group.id": "example-group",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    }

    consumer = Consumer(conf)
    consumer.subscribe(["hello-world"])

    print("Consuming messages (Ctrl+C to stop)...")

    try:
        while running:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    print(f"Reached end of partition {msg.partition()}")
                    continue
                print(f"Error: {msg.error()}")
                break

            data = json.loads(msg.value().decode("utf-8"))
            print(
                f"Key: {msg.key().decode('utf-8')}, "
                f"Value: {data}, "
                f"Partition: {msg.partition()}, "
                f"Offset: {msg.offset()}"
            )

            consumer.commit(asynchronous=False)
    finally:
        consumer.close()
        print("Consumer closed")


if __name__ == "__main__":
    main()
