import os
import json
import requests
import time
from dotenv import load_dotenv

# -----------------------------
# Load settings (with defaults)
# -----------------------------
load_dotenv()

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_DB = os.getenv("POSTGRES_DB", "banking")
CONNECT_URL = os.getenv("CONNECT_URL", "http://localhost:8083/connectors")

# -----------------------------
# Build connector JSON
# -----------------------------
connector_config = {
    "name": "banking-connector",
    "config": {
        "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
        "database.hostname": POSTGRES_HOST,
        "database.port": POSTGRES_PORT,
        "database.user": POSTGRES_USER,
        "database.password": POSTGRES_PASSWORD,
        "database.dbname": POSTGRES_DB,
        "topic.prefix": "banking_server",
        "table.include.list": "public.customers,public.accounts,public.transactions",
        "plugin.name": "pgoutput",
        "slot.name": "banking_slot",
        "publication.autocreate.mode": "filtered",
        "tombstones.on.delete": "false",
        "decimal.handling.mode": "double",
    },
}

# -----------------------------
# Register Connector
# -----------------------------
headers = {"Content-Type": "application/json"}

print(f"🚀 Registering Debezium connector at {CONNECT_URL}...")

try:
    response = requests.post(CONNECT_URL, headers=headers, data=json.dumps(connector_config))
    
    if response.status_code == 201:
        print("✅ Connector registered successfully!")
    elif response.status_code == 409:
        print("⚠️ Connector already exists. Skipping.")
    else:
        print(f"❌ Error ({response.status_code}): {response.text}")

except Exception as e:
    print(f"❌ Connection error: {e}")
