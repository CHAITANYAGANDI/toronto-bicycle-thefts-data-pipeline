import csv
import json
import os
from kafka import KafkaProducer

# Topic name in Kafka where we will send each row of the CSV
# Can be overridden with env var KAFKA_TOPIC
TOPIC_NAME = os.getenv("KAFKA_TOPIC", "toronto_bicycle_thefts_project")

# Path to the CSV file we want to read
# Can be overridden with env var CSV_PATH
CSV_PATH = os.getenv("CSV_PATH", "bicycle-thefts-4326.csv")

# Address of the Kafka broker (host:port)
# Can be overridden with env var KAFKA_BOOTSTRAP_SERVERS
BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "54.88.119.54:9092")


def create_producer():
    """
    Create and return a KafkaProducer object.
    - bootstrap_servers: where Kafka is running
    - value_serializer: convert Python dict to JSON bytes before sending
    - linger_ms: small delay to batch messages slightly
    - retries: how many times to retry if send fails
    """
    return KafkaProducer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        linger_ms=5,
        retries=3,
    )


def main():
    """
    Read the CSV file row by row and send each row as a message to Kafka.
    """

    # Check if the CSV file exists at the given path
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"CSV file not found at {CSV_PATH}")

    # Create a Kafka producer
    producer = create_producer()
    sent_count = 0  # keep track of how many messages we send

    # Open the CSV file
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        # DictReader turns each row into a dictionary: {column_name: value}
        reader = csv.DictReader(f)

        # Loop through every row in the CSV
        for row in reader:
            # Make sure all values are strings and not None
            # Kafka + JSON like clean data types
            safe_row = {k: ("" if v is None else str(v)) for k, v in row.items()}

            # Send one message to Kafka with this row
            producer.send(TOPIC_NAME, safe_row)
            sent_count += 1

    # Make sure all buffered messages are actually sent out
    producer.flush()
    # Close the producer connection
    producer.close()

    print(f"Finished sending {sent_count} messages to topic '{TOPIC_NAME}'")


# Only run main() if this file is executed directly
# (and not imported as a module in some other script)
if __name__ == "__main__":
    main()
