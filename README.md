# 💳 Minimal Banking Data Engineering Pipeline (Kafka + CDC)

This project is a streamlined, real-time banking data engineering pipeline designed to demonstrate core concepts of Change Data Capture (CDC) and event streaming. It mirrors how enterprise systems capture database changes and process them asynchronously.

## 📌 Architecture Overview

The pipeline follows a modern, decoupled architecture:

1.  **PostgreSQL (OLTP)**: Acts as the source system containing `customers`, `accounts`, and `transactions` tables.
2.  **Kafka & Debezium (CDC)**: Debezium monitors the PostgreSQL WAL (Write-Ahead Log) and streams every row-level change (Insert/Update/Delete) into Kafka topics in real-time.
3.  **Python Data Generator**: A script that uses the `Faker` library to simulate continuous banking activity (new customers, deposits, transfers).
4.  **Python Consumer**: A robust script that listens to Kafka topics and persists the streaming data into structured local storage (JSON/Parquet), simulating a landing zone for further analysis.

## 🛠 Tech Stack

- **Database**: PostgreSQL (Source)
- **Streaming**: Apache Kafka
- **CDC Layer**: Debezium
- **Language**: Python (Generating & Consuming data)
- **Containerization**: Docker & Docker Compose

## 🚀 Getting Started

### 1. Prerequisites
- Docker & Docker Compose installed.
- Python 3.10+ installed.

### 2. Setup & Run
1.  **Clone the Repository** (this folder).
2.  **Start the Infrastructure**:
    ```bash
    docker-compose up -d
    ```
3.  **Install Python Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
4.  **Register the Debezium Connector**:
    ```bash
    python kafka-debezium/register_connector.py
    ```
5.  **Run the Data Generator**:
    ```bash
    python data-generator/faker_generator.py
    ```
6.  **Run the Kafka Consumer**:
    ```bash
    python consumer/kafka_consumer.py
    ```

## 🧠 Key Skills Demonstrated

- **Real-Time Data Ingestion**: Handling live streams from relational databases.
- **Change Data Capture (CDC)**: Implementing Debezium to track database fluctuations without overhead.
- **Event-Driven Architecture**: Using Kafka as a central nervous system for data flow.
- **Database Design**: Managing normalized schemas for financial operations.
- **Python for Data Engineering**: Building scalable generators and consumer services.

---
*Note: This project is designed for portfolio demonstration, focusing on foundational Data Engineering principles.*
