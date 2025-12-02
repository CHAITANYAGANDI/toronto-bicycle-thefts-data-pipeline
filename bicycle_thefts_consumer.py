import json
import os
from io import StringIO

import boto3
import pandas as pd
from dateutil import parser
from kafka import KafkaConsumer
from botocore.exceptions import BotoCoreError, ClientError

# ------------------ Kafka + S3 + local config ------------------

# Kafka topic where the producer is sending bicycle theft records
TOPIC_NAME = os.getenv("KAFKA_TOPIC", "toronto_bicycle_thefts_project")

# Kafka broker address (your EC2/Kafka server)
BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "54.88.119.54:9092")

# S3 bucket and key (path) where we will upload the cleaned CSV
S3_BUCKET = os.getenv("S3_BUCKET", "toronto-bicycle-thefts")
S3_CLEAN_KEY = os.getenv("S3_CLEAN_KEY", "clean/Bicycle_Thefts_cleaned.csv")

# Local file name for saving the cleaned CSV on EC2
LOCAL_CLEAN_CSV = os.getenv("LOCAL_CLEAN_CSV", "Bicycle_Thefts_cleaned.csv")

# Kafka consumer group id (helps Kafka track offsets per group)
GROUP_ID = os.getenv("KAFKA_GROUP_ID", "bicycle-etl-group-v2")

# How long the consumer should wait (in ms) with no new messages before stopping
CONSUMER_TIMEOUT_MS = int(os.getenv("CONSUMER_TIMEOUT_MS", "30000"))


def create_consumer():
    """
    Create and configure a KafkaConsumer.

    - value_deserializer: convert JSON bytes back to Python dict
    - auto_offset_reset='earliest': start from the beginning if no offset stored
    - enable_auto_commit=True: commit offsets so we don't re-read everything next time
    - group_id: used to track this consumer group in Kafka
    - consumer_timeout_ms: stop iteration after this idle time
    """
    return KafkaConsumer(
        TOPIC_NAME,
        bootstrap_servers=BOOTSTRAP_SERVERS,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id=GROUP_ID,
        consumer_timeout_ms=CONSUMER_TIMEOUT_MS,
    )


def parse_date_safe(val):
    """
    Safely parse a date-like value.
    - If value is empty or NaN → return NaT (Not a Time)
    - If parsing fails → also return NaT
    This prevents the script from crashing on bad date strings.
    """
    if pd.isna(val) or val == "":
        return pd.NaT
    try:
        return parser.parse(str(val), dayfirst=False, yearfirst=False)
    except Exception:
        return pd.NaT


def clean_bike_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and transform the raw bicycle theft DataFrame.

    Steps:
    1. Standardize column names
    2. Parse date columns
    3. Convert numeric columns
    4. Normalize text columns (strip + upper)
    5. Drop rows with missing key fields (dates, coordinates)
    6. Drop geometry column
    7. Drop duplicate rows
    """

    # 1) Standardize column names: lowercase and replace spaces with underscores
    df = df.rename(columns=lambda c: str(c).strip().lower().replace(" ", "_"))

    # 2) Parse date columns into proper datetime objects
    for col in ["occ_date", "report_date"]:
        if col in df.columns:
            df[col] = df[col].apply(parse_date_safe)

    # 3) Convert numeric columns (any non-numeric values become NaN)
    numeric_cols = [
        "_id",
        "occ_year",
        "occ_day",
        "occ_doy",
        "occ_hour",
        "report_year",
        "report_day",
        "report_doy",
        "report_hour",
        "bike_speed",
        "bike_cost",
        "long_wgs84",
        "lat_wgs84",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # 4) Normalize text columns: convert to string, strip spaces, and uppercase
    text_cols = [
        "event_unique_id",
        "primary_offence",
        "occ_month",
        "occ_dow",
        "report_month",
        "report_dow",
        "division",
        "location_type",
        "premises_type",
        "bike_make",
        "bike_model",
        "bike_type",
        "bike_colour",
        "status",
    ]
    for col in text_cols:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.strip()
                .str.upper()
            )

    # 5) Drop rows with missing occurrence date (key field for analysis)
    if "occ_date" in df.columns:
        df = df.dropna(subset=["occ_date"])

    # Also drop rows that are missing coordinates (we want valid points for maps)
    for coord_col in ["lat_wgs84", "long_wgs84"]:
        if coord_col in df.columns:
            df = df.dropna(subset=[coord_col])

    # 6) Drop the geometry column (raw GeoJSON), not needed after we have lat/long
    if "geometry" in df.columns:
        df = df.drop(columns=["geometry"])

    # 7) Remove exact duplicate rows
    df = df.drop_duplicates()

    # Show how many missing values remain per column after cleaning
    print("Missing values per column AFTER cleaning:")
    print(df.isna().sum())

    return df


def save_to_s3(df: pd.DataFrame):
    """
    Save the cleaned DataFrame to S3 as a CSV.
    - Uses an in-memory buffer (StringIO) instead of writing a temp file to disk.
    - Handles and prints any S3-related errors.
    """
    s3 = boto3.client("s3")
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)

    try:
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=S3_CLEAN_KEY,
            Body=csv_buffer.getvalue().encode("utf-8"),
        )
        print(f"Uploaded cleaned CSV to s3://{S3_BUCKET}/{S3_CLEAN_KEY}")
    except (BotoCoreError, ClientError) as e:
        print("Failed to upload to S3!")
        print(e)


def main():
    """
    Main pipeline:
    1. Consume all messages from Kafka topic.
    2. Build a pandas DataFrame from the messages.
    3. Clean and transform the DataFrame.
    4. Save cleaned data locally and to S3.
    """

    # Create Kafka consumer and start reading records
    consumer = create_consumer()
    records = []

    print(f"Consuming messages from topic '{TOPIC_NAME}'...")
    for msg in consumer:
        # msg.value is already a Python dict (thanks to value_deserializer)
        records.append(msg.value)

    # Close the consumer once no more messages are available
    consumer.close()
    print(f"Total messages consumed: {len(records)}")

    if not records:
        # If no data came in, we stop early, nothing to clean
        print("No messages consumed. Did you run the producer first?")
        return

    # Convert the list of dicts into a DataFrame
    df_raw = pd.DataFrame(records)
    print(f"Raw DataFrame shape: {df_raw.shape}")

    # Clean and transform the DataFrame
    df_clean = clean_bike_df(df_raw)
    print(f"Cleaned DataFrame shape: {df_clean.shape}")

    # Save the cleaned data as a local CSV file on the EC2 instance
    df_clean.to_csv(LOCAL_CLEAN_CSV, index=False)
    print(f"Saved cleaned CSV locally as: {LOCAL_CLEAN_CSV}")

    # Upload the cleaned CSV to S3
    save_to_s3(df_clean)


# Only run main() if this file is executed directly
if __name__ == "__main__":
    main()
