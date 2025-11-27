import json
import os
from io import StringIO

import boto3
import pandas as pd
from dateutil import parser
from kafka import KafkaConsumer
from botocore.exceptions import BotoCoreError, ClientError


TOPIC_NAME = os.getenv("KAFKA_TOPIC", "toronto_bicycle_thefts_project")

BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "54.88.119.54:9092")

S3_BUCKET = os.getenv("S3_BUCKET", "toronto-bicycle-thefts")
S3_CLEAN_KEY = os.getenv("S3_CLEAN_KEY", "clean/Bicycle_Thefts_cleaned.csv")

LOCAL_CLEAN_CSV = os.getenv("LOCAL_CLEAN_CSV", "Bicycle_Thefts_cleaned.csv")

GROUP_ID = os.getenv("KAFKA_GROUP_ID", "bicycle-etl-group-v2")

CONSUMER_TIMEOUT_MS = int(os.getenv("CONSUMER_TIMEOUT_MS", "30000"))



def create_consumer():
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

    if pd.isna(val) or val == "":
        return pd.NaT
    try:
        return parser.parse(str(val), dayfirst=False, yearfirst=False)
    except Exception:
        return pd.NaT


def clean_bike_df(df: pd.DataFrame) -> pd.DataFrame:



    df = df.rename(columns=lambda c: str(c).strip().lower().replace(" ", "_"))


    for col in ["occ_date", "report_date"]:
        if col in df.columns:
            df[col] = df[col].apply(parse_date_safe)


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


    if "occ_date" in df.columns:
        df = df.dropna(subset=["occ_date"])


    for coord_col in ["lat_wgs84", "long_wgs84"]:
        if coord_col in df.columns:
            df = df.dropna(subset=[coord_col])

    if "geometry" in df.columns:
        df = df.drop(columns=["geometry"])

    df = df.drop_duplicates()


    print("Missing values per column AFTER cleaning:")
    print(df.isna().sum())

    return df


def save_to_s3(df: pd.DataFrame):
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
    consumer = create_consumer()
    records = []

    print(f"Consuming messages from topic '{TOPIC_NAME}'...")
    for msg in consumer:
        records.append(msg.value)

    consumer.close()
    print(f"Total messages consumed: {len(records)}")

    if not records:
        print("No messages consumed. Did you run the producer first?")
        return


    df_raw = pd.DataFrame(records)
    print(f"Raw DataFrame shape: {df_raw.shape}")

    df_clean = clean_bike_df(df_raw)
    print(f"Cleaned DataFrame shape: {df_clean.shape}")

    df_clean.to_csv(LOCAL_CLEAN_CSV, index=False)
    print(f"Saved cleaned CSV locally as: {LOCAL_CLEAN_CSV}")

    save_to_s3(df_clean)


if __name__ == "__main__":
    main()
