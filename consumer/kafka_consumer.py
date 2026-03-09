import json
import os
from kafka import KafkaConsumer
from datetime import datetime

# -----------------------------
# Kafka configuration
# -----------------------------
BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP", "localhost:29092")
TOPICS = [
    'banking_server.public.customers',
    'banking_server.public.accounts',
    'banking_server.public.transactions'
]

# -----------------------------
# Initialize Consumer
# -----------------------------
consumer = KafkaConsumer(
    *TOPICS,
    bootstrap_servers=BOOTSTRAP_SERVERS,
    auto_offset_reset='earliest',
    enable_auto_commit=True,
    group_id='banking-consumer-group',
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

# Create local data directory
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

print(f"✅ Connected to Kafka at {BOOTSTRAP_SERVERS}. Listening for messages...")

try:
    for message in consumer:
        topic = message.topic
        event = message.value
        payload = event.get("payload", {})
        record = payload.get("after")  # Extract the row after change

        if record:
            table_name = topic.split('.')[-1]
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Save as local JSON file (simulating persistence)
            file_path = os.path.join(DATA_DIR, f"{table_name}_{timestamp}.json")
            with open(file_path, "w") as f:
                json.dump(record, f, indent=4)
            
            print(f"[{topic}] -> Saved to {file_path}")

except KeyboardInterrupt:
    print("\nConsumer stopped by user.")
finally:
    consumer.close()
