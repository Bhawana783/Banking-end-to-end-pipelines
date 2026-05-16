"""
Debezium Connector Registration - Registers CDC connector with Kafka Connect
Includes health checks, retry logic, and connector management
"""

import os
import json
import requests
import time
import sys
import argparse

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import debezium_config, postgres_config, kafka_config
from logger import get_logger, LogContext

logger = get_logger("debezium_connector")


class DebeziumConnectorManager:
    """Manages Debezium connector lifecycle."""
    
    def __init__(self):
        self.connect_url = debezium_config.CONNECT_URL
        self.max_retries = debezium_config.RETRIABLE_RETRIES
        self.retry_delay = debezium_config.RETRY_DELAY_MS / 1000  # Convert to seconds
    
    def wait_for_connect(self, timeout: int = 120) -> bool:
        """Wait for Kafka Connect to be available."""
        logger.info(f"Waiting for Kafka Connect at {self.connect_url}...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(
                    f"{self.connect_url.rsplit('/connectors', 1)[0]}",
                    timeout=5
                )
                if response.status_code == 200:
                    logger.info("✅ Kafka Connect is available")
                    return True
            except requests.RequestException as e:
                logger.debug(f"Connect not ready: {e}")
            
            time.sleep(5)
        
        logger.error(f"Kafka Connect not available after {timeout} seconds")
        return False
    
    def check_connector_exists(self, connector_name: str) -> bool:
        """Check if connector already exists."""
        try:
            response = requests.get(
                f"{self.connect_url}/{connector_name}",
                timeout=10
            )
            return response.status_code == 200
        except requests.RequestException as e:
            logger.debug(f"Error checking connector: {e}")
            return False
    
    def get_connector_status(self, connector_name: str) -> dict:
        """Get connector status."""
        try:
            response = requests.get(
                f"{self.connect_url}/{connector_name}/status",
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
        except requests.RequestException as e:
            logger.warning(f"Error getting connector status: {e}")
        
        return {}
    
    def delete_connector(self, connector_name: str) -> bool:
        """Delete existing connector."""
        try:
            logger.info(f"Deleting existing connector: {connector_name}")
            response = requests.delete(
                f"{self.connect_url}/{connector_name}",
                timeout=10
            )
            if response.status_code in [200, 204]:
                logger.info("✅ Connector deleted successfully")
                time.sleep(5)  # Wait for cleanup
                return True
            else:
                logger.error(f"Error deleting connector: {response.status_code} - {response.text}")
                return False
        except requests.RequestException as e:
            logger.error(f"Error deleting connector: {e}")
            return False
    
    def register_connector(self, force: bool = False) -> bool:
        """Register Debezium connector."""
        try:
            connector_config = self._build_connector_config()
            headers = {"Content-Type": "application/json"}
            
            with LogContext(logger, "Register Connector", 
                          connector=debezium_config.CONNECTOR_NAME):
                
                # Check if connector exists
                if self.check_connector_exists(debezium_config.CONNECTOR_NAME):
                    if force:
                        logger.info("⚠️  Connector already exists. Deleting due to --force flag...")
                        self.delete_connector(debezium_config.CONNECTOR_NAME)
                    else:
                        logger.info("⚠️  Connector already exists. Skipping.")
                        return True
                
                # Register connector with retries
                for attempt in range(1, self.max_retries + 1):
                    try:
                        logger.info(f"Registering connector (attempt {attempt}/{self.max_retries})...")
                        response = requests.post(
                            self.connect_url,
                            headers=headers,
                            data=json.dumps(connector_config),
                            timeout=30
                        )
                        
                        if response.status_code == 201:
                            logger.info("✅ Connector registered successfully!")
                            self._log_connector_details()
                            return True
                        elif response.status_code == 409:
                            logger.warning("⚠️  Connector already exists")
                            return True
                        else:
                            logger.error(f"❌ Error ({response.status_code}): {response.text}")
                            
                            if attempt < self.max_retries:
                                logger.info(f"Retrying in {self.retry_delay} seconds...")
                                time.sleep(self.retry_delay)
                            else:
                                return False
                    
                    except requests.RequestException as e:
                        logger.error(f"❌ Request failed: {e}")
                        
                        if attempt < self.max_retries:
                            logger.info(f"Retrying in {self.retry_delay} seconds...")
                            time.sleep(self.retry_delay)
                        else:
                            return False
        
        except Exception as e:
            logger.error(f"❌ Error registering connector: {e}")
            return False
    
    def _build_connector_config(self) -> dict:
        """Build Debezium connector configuration."""
        # Use Docker network hostnames for connector running in Docker
        db_host = postgres_config.get_docker_host()
        db_port = postgres_config.get_docker_port()
        
        return {
            "name": debezium_config.CONNECTOR_NAME,
            "config": {
                "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
                "database.hostname": db_host,
                "database.port": str(db_port),
                "database.user": postgres_config.USER,
                "database.password": postgres_config.PASSWORD,
                "database.dbname": postgres_config.DB,
                "topic.prefix": kafka_config.TOPIC_PREFIX,
                "table.include.list": "public.customers,public.accounts,public.transactions",
                "plugin.name": debezium_config.PLUGIN_NAME,
                "slot.name": debezium_config.SLOT_NAME,
                "publication.autocreate.mode": "filtered",
                "tombstones.on.delete": debezium_config.TOMBSTONES_ON_DELETE,
                "decimal.handling.mode": debezium_config.DECIMAL_HANDLING,
                # Performance tuning
                "batch.size": "2048",
                "poll.interval.ms": "1000",
                "connect.timeout.ms": "30000",
                # Heartbeat to prevent timeouts
                "heartbeat.interval.ms": "10000",
                "heartbeat.action.query": "SELECT 1",
            },
        }
    
    def _log_connector_details(self):
        """Log connector configuration details."""
        logger.info("Connector Configuration:")
        logger.info(f"  - Database: {postgres_config.HOST}:{postgres_config.PORT}/{postgres_config.DB}")
        logger.info(f"  - Topic Prefix: {kafka_config.TOPIC_PREFIX}")
        logger.info(f"  - Tables: customers, accounts, transactions")
        logger.info(f"  - Plugin: {debezium_config.PLUGIN_NAME}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Register Debezium Connector")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-registration by deleting existing connector"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check connector status without registering"
    )
    args = parser.parse_args()
    
    manager = DebeziumConnectorManager()
    
    # Wait for Connect to be available
    if not manager.wait_for_connect():
        logger.error("Failed to connect to Kafka Connect")
        sys.exit(1)
    
    # Check status if requested
    if args.check:
        status = manager.get_connector_status(debezium_config.CONNECTOR_NAME)
        if status:
            logger.info(f"Connector Status: {json.dumps(status, indent=2)}")
        else:
            logger.info("Connector not found or not running")
        return
    
    # Register connector
    success = manager.register_connector(force=args.force)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
