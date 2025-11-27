import csv
import json
import os
from kafka import KafkaProducer


TOPIC_NAME = os.getenv("KAFKA_TOPIC", "toronto_bicycle_thefts_project")

CSV_PATH = os.getenv("CSV_PATH", "bicycle-thefts-4326.csv")

BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "54.88.119.54:9092")


def create_producer():
    return KafkaProducer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        linger_ms=5,
        retries=3,
    )

def main():
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"CSV file not found at {CSV_PATH}")

    producer = create_producer()
    sent_count = 0

    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:

            safe_row = {k: ("" if v is None else str(v)) for k, v in row.items()}
            producer.send(TOPIC_NAME, safe_row)
            sent_count += 1

    producer.flush()
    producer.close()
    print(f"Finished sending {sent_count} messages to topic '{TOPIC_NAME}'")

if __name__ == "__main__":
    main()
