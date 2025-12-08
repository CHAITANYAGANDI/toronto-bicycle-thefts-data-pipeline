# Toronto Bicycle Thefts – Kafka & AWS Data Pipeline 🚲

An end-to-end data pipeline and analytics stack for analyzing [Toronto Bicycle Thefts](https://open.toronto.ca/dataset/bicycle-thefts/) using Apache Kafka, AWS services, and interactive dashboards.

## Problem Statement

Bike theft is a recurring problem in urban areas. While the Toronto Police Service publishes open data on bicycle thefts, the raw data isn't directly usable for analysis by non-technical users. This project transforms that raw data into actionable insights.

## Objectives

- Build a cloud-based pipeline that ingests, cleans, and stores bicycle theft data
- Enable analysis of theft patterns by location, time, bike characteristics, and recovery status
- Deliver interactive dashboards for cyclists, city planners, and law enforcement

## Key Questions Answered

- Which areas and police divisions have the most thefts?
- What are the peak times, days, and months for theft?
- Which bike types, colours, and price ranges are most targeted?
- How do recovery patterns vary across the city?

---

## Architecture

```
![Architecture](./Data%20Architecture%20Diagram/Toronto_Bicycle_Thefts_Data_Architecture.jpg)
```



---

## Dataset

| Field | Description |
|-------|-------------|
| **Source** | City of Toronto Open Data |
| **Records** | ~39,000+ reported bicycle thefts |
| **Link** | [Toronto Bicycle Thefts](https://open.toronto.ca/dataset/bicycle-thefts/) |

### Data Fields

- **Event Info:** Event ID, primary offence, occurrence/report dates, year, month, day, hour
- **Location:** Police division, location type, premises type
- **Bike Details:** Make, model, type, speed, colour, cost, status (STOLEN/RECOVERED)
- **Geospatial:** Longitude, latitude (WGS84)

---

## Tech Stack

| Category | Technologies |
|----------|--------------|
| **Languages** | Python 3.9+ |
| **Libraries** | kafka-python, pandas, boto3, python-dateutil |
| **Messaging** | Apache Kafka, ZooKeeper |
| **Compute** | Amazon EC2 |
| **Storage** | Amazon S3 |
| **Database** | Amazon RDS (MySQL) |
| **BI Tool** | Amazon QuickSight |
| **Security** | AWS IAM |

---

## Repository Structure

```
.
├── producer/
│   └── bicycle_thefts_producer.py    # Kafka producer script
├── consumer/
│   └── bicycle_thefts_consumer.py    # Kafka consumer + ETL script
├── data/
│   └── bicycle-thefts-4326.csv       # Raw sample for local testing
├── sql/
│   ├── schema.sql                    # Table definitions
│   └── views.sql                     # Analytical views for QuickSight
├── dashboards/
│   └── quicksight_design.md          # Dashboard notes and screenshots
├── docs/
│   └── architecture.md               # Detailed architecture documentation
└── README.md
```

---

## Getting Started

### Prerequisites

- AWS account with permissions for EC2, S3, RDS, IAM, and QuickSight
- Python 3.9+
- SSH access configured for EC2
- MySQL client (e.g., MySQL Workbench)

### 1. Clone the Repository

```bash
git clone https://github.com/<your-username>/toronto-bicycle-thefts-pipeline.git
cd toronto-bicycle-thefts-pipeline
```

### 2. EC2 Setup

Launch an EC2 instance (t3.xlarge recommended) and install dependencies:

```bash
# Install Java (required for Kafka)
sudo yum install java-1.8.0-openjdk -y

# Download and extract Kafka
wget https://archive.apache.org/dist/kafka/3.6.0/kafka_2.13-3.6.0.tgz
tar -xzf kafka_2.13-3.6.0.tgz
cd kafka_2.13-3.6.0

# Set JVM heap options
export KAFKA_HEAP_OPTS="-Xms1G -Xmx1G"
```

Update `config/server.properties`:

```properties
advertised.listeners=PLAINTEXT://<your-ec2-public-ip>:9092
```

Start ZooKeeper and Kafka:

```bash
bin/zookeeper-server-start.sh -daemon config/zookeeper.properties
bin/kafka-server-start.sh -daemon config/server.properties
```

### 3. Deploy Scripts to EC2

```bash
scp -i "bicycle-theft-ec2-key.pem" \
  producer/bicycle_thefts_producer.py \
  consumer/bicycle_thefts_consumer.py \
  data/bicycle-thefts-4326.csv \
  ec2-user@<your-ec2-public-ip>:/home/ec2-user/
```

---

## Running the Pipeline

### Set Environment Variables

```bash
export KAFKA_TOPIC="toronto_bicycle_thefts_project"
export KAFKA_BOOTSTRAP_SERVERS="<your-ec2-public-ip>:9092"
export S3_BUCKET="toronto-bicycle-thefts"
export S3_CLEAN_KEY="clean/Bicycle_Thefts_cleaned.csv"
export LOCAL_CLEAN_CSV="Bicycle_Thefts_cleaned.csv"
export KAFKA_GROUP_ID="bicycle-etl-group-v2"
```

### Run the Producer

```bash
python3 bicycle_thefts_producer.py
# Output: Finished sending 39473 messages to topic 'toronto_bicycle_thefts_project'
```

### Run the Consumer/ETL

```bash
python3 bicycle_thefts_consumer.py
# Consumes messages, cleans data, saves locally and uploads to S3
```

---

## RDS & QuickSight Setup

### RDS (MySQL)

1. Create an RDS MySQL instance in the same region as EC2
2. Configure security groups to allow MySQL access (port 3306)
3. Connect via MySQL Workbench and run:

```sql
-- Create database
CREATE DATABASE bicycle_thefts_db;

-- Load schema and views
SOURCE sql/schema.sql;
SOURCE sql/views.sql;
```

4. Load the cleaned CSV from S3 into the database

### QuickSight

1. Set up QuickSight in the same AWS region
2. Create a data source connected to RDS
3. Import SQL views as datasets
4. Build dashboards with:
   - Geospatial maps (lat/long theft locations)
   - Time-series trends (yearly/monthly patterns)
   - Bar charts (by division, premises type, bike type)
   - Filters for year, division, bike type, and status

---

## Team

| Member | Role | Responsibilities |
|--------|------|------------------|
| **Chaitanya** | Cloud Infrastructure & ETL | EC2/Kafka setup, Python producer/consumer, data cleaning, S3 integration |
| **Mudra** | Data Modeling & SQL | MySQL schema design, data loading, analytical queries and views |
| **Qi Han** | BI & Dashboards | QuickSight configuration, dashboard design, insights storytelling |

---
