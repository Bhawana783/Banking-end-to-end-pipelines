"""
Startup orchestrator - Manages the entire pipeline lifecycle
Includes health checks, initialization, and graceful shutdown
"""

import time
import sys
import os
import signal
import argparse
from datetime import datetime
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import DatabaseConnectionPool, DatabaseInitializer, DatabaseHealth
from config import postgres_config, kafka_config, debezium_config
from logger import get_logger, LogContext
from kafka_debezium.register_connector import DebeziumConnectorManager

logger = get_logger("orchestrator")


class PipelineOrchestrator:
    """Orchestrates the entire banking data pipeline."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.running = True
        self.start_time = datetime.now()
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, sig, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {sig}. Shutting down gracefully...")
        self.running = False
    
    def startup_database(self) -> bool:
        """Startup and initialize database."""
        with LogContext(logger, "Database Initialization"):
            try:
                # Initialize connection pool
                DatabaseConnectionPool.initialize()
                
                # Check health
                if not DatabaseHealth.is_healthy():
                    raise Exception("Database health check failed")
                
                # Wait for availability
                DatabaseInitializer.wait_for_database()
                
                # Check if schema exists
                if not DatabaseInitializer.check_schema_exists():
                    logger.info("Schema not found. Initializing...")
                    schema_file = os.path.join(os.path.dirname(__file__), "postgres/schema.sql")
                    DatabaseInitializer.initialize_schema(schema_file)
                else:
                    logger.info("✅ Existing schema found")
                
                # Log database info
                counts = DatabaseHealth.get_table_counts()
                size = DatabaseHealth.get_database_size()
                logger.info(f"Database size: {size}")
                logger.info(f"Table counts: {counts}")
                
                return True
            
            except Exception as e:
                logger.error(f"Database initialization failed: {e}")
                return False
    
    def startup_kafka(self) -> bool:
        """Verify Kafka connectivity."""
        with LogContext(logger, "Kafka Verification"):
            try:
                from kafka import KafkaProducer
                from kafka.errors import KafkaError
                
                logger.info(f"Connecting to Kafka at {kafka_config.BOOTSTRAP_SERVERS}...")
                
                producer = KafkaProducer(
                    bootstrap_servers=kafka_config.get_bootstrap_servers_list(),
                    request_timeout_ms=10000,
                )
                
                logger.info("✅ Kafka connectivity verified")
                producer.close()
                return True
            
            except Exception as e:
                logger.error(f"Kafka connectivity failed: {e}")
                return False
    
    def startup_debezium(self) -> bool:
        """Register Debezium connector."""
        with LogContext(logger, "Debezium Connector Setup"):
            try:
                manager = DebeziumConnectorManager()
                
                # Wait for Connect
                if not manager.wait_for_connect(timeout=60):
                    logger.warning("Kafka Connect not available. Skipping connector registration.")
                    return True  # Don't fail if Connect isn't ready
                
                # Register connector
                success = manager.register_connector(force=False)
                
                if success:
                    logger.info("✅ Debezium connector ready")
                    time.sleep(5)  # Wait for connector to start
                    
                    # Check status
                    status = manager.get_connector_status(debezium_config.CONNECTOR_NAME)
                    if status:
                        logger.info(f"Connector state: {status.get('connector', {}).get('state', 'Unknown')}")
                
                return success
            
            except Exception as e:
                logger.error(f"Debezium setup failed: {e}")
                return False
    
    def startup_all(self, skip_debezium: bool = False) -> bool:
        """Startup all components."""
        logger.info("=" * 80)
        logger.info("🚀 BANKING DATA PIPELINE - STARTUP SEQUENCE")
        logger.info("=" * 80)
        
        components = [
            ("Database", self.startup_database),
            ("Kafka", self.startup_kafka),
        ]
        
        if not skip_debezium:
            components.append(("Debezium", self.startup_debezium))
        
        results = {}
        
        for component_name, startup_func in components:
            logger.info(f"\n📦 Starting {component_name}...")
            results[component_name] = startup_func()
            
            if not results[component_name]:
                logger.error(f"❌ {component_name} startup failed")
                return False
            
            logger.info(f"✅ {component_name} startup successful")
            time.sleep(2)
        
        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("✅ PIPELINE STARTUP SUCCESSFUL")
        logger.info("=" * 80)
        logger.info("\nNext steps:")
        logger.info("1. Run data generator: python data-generator/faker_generator.py")
        logger.info("2. Run Kafka consumer: python consumer/kafka_consumer.py")
        logger.info("=" * 80 + "\n")
        
        return True
    
    def health_check(self) -> dict:
        """Perform comprehensive health check."""
        health_status = {
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
            "components": {}
        }
        
        # Database health
        try:
            db_healthy = DatabaseHealth.is_healthy()
            counts = DatabaseHealth.get_table_counts()
            health_status["components"]["database"] = {
                "status": "healthy" if db_healthy else "unhealthy",
                "table_counts": counts
            }
        except Exception as e:
            health_status["components"]["database"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Kafka health
        try:
            from kafka import KafkaProducer
            producer = KafkaProducer(
                bootstrap_servers=kafka_config.get_bootstrap_servers_list(),
                request_timeout_ms=5000,
            )
            producer.close()
            health_status["components"]["kafka"] = {"status": "healthy"}
        except Exception as e:
            health_status["components"]["kafka"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        return health_status
    
    def shutdown(self):
        """Shutdown pipeline."""
        logger.info("Shutting down pipeline...")
        DatabaseConnectionPool.close_all()
        logger.info("Pipeline shutdown complete")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Banking Pipeline Orchestrator")
    parser.add_argument(
        "--startup",
        action="store_true",
        help="Run startup sequence"
    )
    parser.add_argument(
        "--health",
        action="store_true",
        help="Perform health check"
    )
    parser.add_argument(
        "--skip-debezium",
        action="store_true",
        help="Skip Debezium connector setup"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    orchestrator = PipelineOrchestrator(verbose=args.verbose)
    
    try:
        if args.startup:
            success = orchestrator.startup_all(skip_debezium=args.skip_debezium)
            sys.exit(0 if success else 1)
        
        elif args.health:
            health_status = orchestrator.health_check()
            import json
            logger.info(f"Health Status:\n{json.dumps(health_status, indent=2)}")
            
            all_healthy = all(
                comp.get("status") == "healthy"
                for comp in health_status["components"].values()
            )
            sys.exit(0 if all_healthy else 1)
        
        else:
            parser.print_help()
    
    finally:
        orchestrator.shutdown()


if __name__ == "__main__":
    main()
