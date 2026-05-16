"""
Banking Data Consumer - Consumes CDC events from Kafka and persists to storage
Supports JSON and Parquet formats with batching
"""

import json
import os
import sys
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kafka import KafkaConsumer, TopicPartition
from kafka.errors import KafkaError

from config import kafka_config, consumer_config
from validation import quality_checker, DataValidator
from logger import get_logger, LogContext

logger = get_logger("kafka_consumer")


class BankingDataConsumer:
    """Consumes Kafka CDC events and persists to storage."""
    
    def __init__(self):
        self.bootstrap_servers = kafka_config.get_bootstrap_servers_list()
        self.consumer = None
        self.data_batches: Dict[str, List[Dict]] = defaultdict(list)
        self.batch_counts: Dict[str, int] = defaultdict(int)
        self.last_flush_time = datetime.now()
        self.record_count = 0
        self.error_count = 0
        
        # Create output directory
        os.makedirs(consumer_config.OUTPUT_DIR, exist_ok=True)
    
    def initialize_consumer(self):
        """Initialize Kafka consumer."""
        try:
            logger.info(f"Initializing Kafka consumer...")
            logger.info(f"Bootstrap servers: {self.bootstrap_servers}")
            logger.info(f"Topics: {kafka_config.TOPICS}")
            
            self.consumer = KafkaConsumer(
                *kafka_config.TOPICS,
                bootstrap_servers=self.bootstrap_servers,
                auto_offset_reset=kafka_config.AUTO_OFFSET_RESET,
                enable_auto_commit=kafka_config.ENABLE_AUTO_COMMIT,
                group_id=kafka_config.GROUP_ID,
                value_deserializer=lambda x: json.loads(x.decode('utf-8')) if x else None,
                session_timeout_ms=kafka_config.SESSION_TIMEOUT_MS,
                max_poll_records=100,
                connections_max_idle_ms=540000,  # 9 minutes
            )
            
            logger.info("Kafka consumer initialized successfully")
        except KafkaError as e:
            logger.error(f"Failed to initialize Kafka consumer: {e}")
            raise
    
    def extract_payload(self, message: dict) -> Dict[str, Any]:
        """Extract payload from Kafka message."""
        try:
            # Debezium message structure
            payload = message.get("payload", {})
            record = payload.get("after")  # Extract the row after change
            
            if not record:
                return None
            
            return record
        except Exception as e:
            logger.error(f"Error extracting payload: {e}")
            return None
    
    def process_message(self, topic: str, message: dict) -> bool:
        """Process a single Kafka message."""
        try:
            # Extract payload
            record = self.extract_payload(message)
            if not record:
                return False
            
            # Determine table and validate
            table_name = topic.split('.')[-1]
            
            is_valid, errors = self._validate_by_table(table_name, record)
            if not is_valid:
                logger.warning(f"Invalid record from {table_name}: {errors}")
                quality_checker.invalid_records += 1
                return False
            
            # Add metadata
            record['_table'] = table_name
            record['_timestamp'] = datetime.now().isoformat()
            record['_topic'] = topic
            
            # Batch the record
            self.data_batches[table_name].append(record)
            self.batch_counts[table_name] += 1
            self.record_count += 1
            quality_checker.valid_records += 1
            
            return True
        
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            self.error_count += 1
            return False
    
    @staticmethod
    def _validate_by_table(table_name: str, record: dict) -> tuple:
        """Validate record by table type."""
        if table_name == "customers":
            return DataValidator.validate_customer(record)
        elif table_name == "accounts":
            return DataValidator.validate_account(record)
        elif table_name == "transactions":
            return DataValidator.validate_transaction(record)
        else:
            return False, [f"Unknown table: {table_name}"]
    
    def flush_batches(self, force: bool = False):
        """Flush data batches to storage."""
        should_flush = force or (
            sum(len(batch) for batch in self.data_batches.values()) >= consumer_config.BATCH_SIZE or
            (datetime.now() - self.last_flush_time).total_seconds() >= consumer_config.FLUSH_INTERVAL_SECONDS
        )
        
        if not should_flush or not any(self.data_batches.values()):
            return
        
        with LogContext(logger, "Flush Data Batches", record_count=sum(len(b) for b in self.data_batches.values())):
            try:
                for table_name, records in self.data_batches.items():
                    if not records:
                        continue
                    
                    if consumer_config.USE_PARQUET:
                        self._save_parquet(table_name, records)
                    else:
                        self._save_json(table_name, records)
                
                self.data_batches.clear()
                self.batch_counts.clear()
                self.last_flush_time = datetime.now()
                
                logger.info(f"✅ Flushed {self.record_count} total records")
            
            except Exception as e:
                logger.error(f"Error flushing batches: {e}")
                self.error_count += 1
    
    def _save_parquet(self, table_name: str, records: list):
        """Save records to Parquet format."""
        try:
            df = pd.DataFrame(records)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Partition by date
            date_dir = os.path.join(
                consumer_config.OUTPUT_DIR,
                table_name,
                datetime.now().strftime('%Y/%m/%d')
            )
            os.makedirs(date_dir, exist_ok=True)
            
            file_path = os.path.join(date_dir, f"{table_name}_{timestamp}.parquet")
            
            compression = "snappy" if consumer_config.COMPRESS_PARQUET else None
            df.to_parquet(
                file_path,
                compression=compression,
                index=False,
                engine='fastparquet'
            )
            
            logger.info(f"Saved {len(records)} {table_name} records to {file_path}")
        
        except Exception as e:
            logger.error(f"Error saving Parquet file: {e}")
            raise
    
    def _save_json(self, table_name: str, records: list):
        """Save records to JSON format."""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Partition by date
            date_dir = os.path.join(
                consumer_config.OUTPUT_DIR,
                table_name,
                datetime.now().strftime('%Y/%m/%d')
            )
            os.makedirs(date_dir, exist_ok=True)
            
            file_path = os.path.join(date_dir, f"{table_name}_{timestamp}.json")
            
            with open(file_path, 'w') as f:
                json.dump(records, f, indent=2, default=str)
            
            logger.info(f"Saved {len(records)} {table_name} records to {file_path}")
        
        except Exception as e:
            logger.error(f"Error saving JSON file: {e}")
            raise
    
    def run(self):
        """Run the consumer."""
        try:
            self.initialize_consumer()
            logger.info("✅ Connected to Kafka. Listening for messages...")
            
            message_count = 0
            
            for message in self.consumer:
                try:
                    topic = message.topic
                    
                    if message.value:
                        self.process_message(topic, message.value)
                        message_count += 1
                        
                        if message_count % 100 == 0:
                            logger.info(f"Processed {message_count} messages. "
                                      f"Batch sizes: {dict(self.batch_counts)}")
                            self.flush_batches()
                
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    self.error_count += 1
        
        except KeyboardInterrupt:
            logger.info("Consumer interrupted by user")
        except Exception as e:
            logger.error(f"Fatal error in consumer: {e}")
            raise
        finally:
            # Final flush
            self.flush_batches(force=True)
            
            # Quality report
            report = quality_checker.get_quality_report()
            logger.info(f"Quality Report: {report}")
            logger.info(f"Total errors: {self.error_count}")
            
            if self.consumer:
                self.consumer.close()


def main():
    """Main entry point."""
    consumer = BankingDataConsumer()
    consumer.run()


if __name__ == "__main__":
    main()
