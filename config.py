"""
Centralized configuration management for the Banking Data Pipeline.
Supports environment-based configuration with type safety.
"""

import os
from typing import Optional
from dotenv import load_dotenv
from dataclasses import dataclass, field

# Load environment variables
load_dotenv()


@dataclass
class PostgresConfig:
    """PostgreSQL database configuration."""
    
    HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    PORT: int = int(os.getenv("POSTGRES_PORT", "5433"))
    DB: str = os.getenv("POSTGRES_DB", "banking")
    USER: str = os.getenv("POSTGRES_USER", "postgres")
    PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    
    # Connection pool settings
    MIN_POOL_SIZE: int = int(os.getenv("POSTGRES_MIN_POOL_SIZE", "2"))
    MAX_POOL_SIZE: int = int(os.getenv("POSTGRES_MAX_POOL_SIZE", "10"))
    POOL_TIMEOUT: int = int(os.getenv("POSTGRES_POOL_TIMEOUT", "30"))
    
    # WAL settings for CDC
    WAL_LEVEL: str = "logical"
    MAX_WAL_SENDERS: int = 10
    MAX_REPLICATION_SLOTS: int = 10
    
    def get_dsn(self) -> str:
        """Generate PostgreSQL connection string."""
        return f"postgresql://{self.USER}:{self.PASSWORD}@{self.HOST}:{self.PORT}/{self.DB}"
    
    def get_psycopg2_dict(self) -> dict:
        """Get psycopg2 connection parameters."""
        return {
            "host": self.HOST,
            "port": self.PORT,
            "database": self.DB,
            "user": self.USER,
            "password": self.PASSWORD,
        }
    
    def get_docker_host(self) -> str:
        """Get Docker internal hostname for services in banking-network."""
        # If running from host machine, use localhost
        # If running from Docker, use service name
        if self.HOST in ("localhost", "127.0.0.1"):
            return "postgres"  # Docker service name for internal network
        return self.HOST
    
    def get_docker_port(self) -> int:
        """Get Docker internal port for services in banking-network."""
        # Docker internal services use container port 5432, not mapped port
        if self.HOST in ("localhost", "127.0.0.1"):
            return 5432  # Container port
        return self.PORT


@dataclass
class KafkaConfig:
    """Kafka broker configuration."""
    
    BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP", "localhost:29092")
    BROKER_HOST: str = os.getenv("KAFKA_BROKER_HOST", "kafka")
    BROKER_PORT: int = int(os.getenv("KAFKA_BROKER_PORT", "9092"))
    
    # Consumer settings
    GROUP_ID: str = os.getenv("KAFKA_GROUP", "banking-consumer-group")
    AUTO_OFFSET_RESET: str = "earliest"
    ENABLE_AUTO_COMMIT: bool = True
    SESSION_TIMEOUT_MS: int = 30000
    
    # Producer settings
    ACKS: str = "all"
    RETRIES: int = 3
    
    # Topic configuration
    TOPICS: list = field(default_factory=lambda: [
        "banking_server.public.customers",
        "banking_server.public.accounts",
        "banking_server.public.transactions"
    ])
    
    TOPIC_PREFIX: str = "banking_server"
    
    def get_bootstrap_servers_list(self) -> list:
        """Parse bootstrap servers string into list."""
        return self.BOOTSTRAP_SERVERS.split(",")


@dataclass
class DebeziumConfig:
    """Debezium connector configuration."""
    
    CONNECT_URL: str = os.getenv("CONNECT_URL", "http://localhost:8083/connectors")
    CONNECTOR_NAME: str = "banking-connector"
    
    # Plugin configuration
    PLUGIN_NAME: str = "pgoutput"
    SLOT_NAME: str = "banking_slot"
    PUBLICATION_NAME: str = "banking_publication"
    
    # Event configuration
    TOMBSTONES_ON_DELETE: str = "false"
    DECIMAL_HANDLING: str = "double"
    RETRIABLE_RETRIES: int = 3
    RETRY_DELAY_MS: int = 5000


@dataclass
class DataGeneratorConfig:
    """Data generator configuration."""
    
    # Data volume
    NUM_CUSTOMERS: int = int(os.getenv("NUM_CUSTOMERS", "50"))
    ACCOUNTS_PER_CUSTOMER: int = int(os.getenv("ACCOUNTS_PER_CUSTOMER", "3"))
    TRANSACTIONS_PER_ITERATION: int = int(os.getenv("NUM_TRANSACTIONS", "100"))
    
    # Transaction configuration
    MIN_TRANSACTION_AMOUNT: float = 10.0
    MAX_TRANSACTION_AMOUNT: float = 5000.0
    
    # Timing
    LOOP_ENABLED: bool = os.getenv("GENERATOR_LOOP", "true").lower() == "true"
    SLEEP_SECONDS: int = int(os.getenv("GENERATOR_SLEEP_SECONDS", "5"))
    
    # Account balance configuration
    MIN_INITIAL_BALANCE: float = 100.0
    MAX_INITIAL_BALANCE: float = 50000.0
    CURRENCY: str = "USD"


@dataclass
class ConsumerConfig:
    """Data consumer configuration."""
    
    OUTPUT_DIR: str = os.getenv("CONSUMER_OUTPUT_DIR", "data")
    BATCH_SIZE: int = int(os.getenv("CONSUMER_BATCH_SIZE", "100"))
    FLUSH_INTERVAL_SECONDS: int = int(os.getenv("CONSUMER_FLUSH_INTERVAL", "60"))
    
    # Storage format
    USE_PARQUET: bool = os.getenv("CONSUMER_USE_PARQUET", "true").lower() == "true"
    COMPRESS_PARQUET: bool = True
    
    # Data retention
    ARCHIVE_ENABLED: bool = False
    RETENTION_DAYS: int = 90


@dataclass
class LoggingConfig:
    """Logging configuration."""
    
    LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR: str = os.getenv("LOG_DIR", "logs")
    LOG_FILE_PREFIX: str = "banking_pipeline"
    
    # Format
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"
    
    # Rotation
    MAX_BYTES: int = 10 * 1024 * 1024  # 10MB
    BACKUP_COUNT: int = 5


@dataclass
class MonitoringConfig:
    """Monitoring and health check configuration."""
    
    HEALTH_CHECK_ENABLED: bool = True
    HEALTH_CHECK_INTERVAL_SECONDS: int = 30
    METRICS_PORT: int = int(os.getenv("METRICS_PORT", "8000"))
    
    # Thresholds
    LAG_WARNING_THRESHOLD: int = 1000
    LAG_CRITICAL_THRESHOLD: int = 5000


# Global configuration instances
postgres_config = PostgresConfig()
kafka_config = KafkaConfig()
debezium_config = DebeziumConfig()
data_generator_config = DataGeneratorConfig()
consumer_config = ConsumerConfig()
logging_config = LoggingConfig()
monitoring_config = MonitoringConfig()


def get_all_config() -> dict:
    """Get all configuration as a dictionary."""
    return {
        "postgres": postgres_config,
        "kafka": kafka_config,
        "debezium": debezium_config,
        "generator": data_generator_config,
        "consumer": consumer_config,
        "logging": logging_config,
        "monitoring": monitoring_config,
    }
