"""
Database utilities for PostgreSQL connection management and common operations.
"""

import psycopg2
import psycopg2.pool
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from typing import Optional, Dict, List, Any
import time

from config import postgres_config
from logger import get_logger

logger = get_logger("database")


class DatabaseConnectionPool:
    """Manages PostgreSQL connection pool."""
    
    _pool: Optional[psycopg2.pool.SimpleConnectionPool] = None
    _lock_attempts = 5
    _lock_delay = 1
    
    @classmethod
    def initialize(cls):
        """Initialize connection pool."""
        if cls._pool is None:
            try:
                logger.info("Initializing database connection pool...")
                cls._pool = psycopg2.pool.SimpleConnectionPool(
                    postgres_config.MIN_POOL_SIZE,
                    postgres_config.MAX_POOL_SIZE,
                    **postgres_config.get_psycopg2_dict()
                )
                logger.info("Database connection pool initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize connection pool: {e}")
                raise
    
    @classmethod
    def get_connection(cls):
        """Get a connection from the pool."""
        if cls._pool is None:
            cls.initialize()
        
        try:
            return cls._pool.getconn()
        except psycopg2.pool.PoolError as e:
            logger.error(f"Connection pool exhausted: {e}")
            raise
    
    @classmethod
    def return_connection(cls, conn):
        """Return a connection to the pool."""
        if cls._pool and conn:
            cls._pool.putconn(conn)
    
    @classmethod
    def close_all(cls):
        """Close all connections in the pool."""
        if cls._pool:
            cls._pool.closeall()
            cls._pool = None
            logger.info("All database connections closed")


@contextmanager
def get_db_connection():
    """Context manager for getting a database connection."""
    conn = None
    try:
        conn = DatabaseConnectionPool.get_connection()
        conn.autocommit = False  # Use explicit transactions
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        if conn:
            DatabaseConnectionPool.return_connection(conn)


@contextmanager
def get_db_cursor(dict_cursor: bool = False):
    """Context manager for getting a database cursor."""
    conn = None
    cursor = None
    try:
        conn = DatabaseConnectionPool.get_connection()
        conn.autocommit = False
        cursor_class = RealDictCursor if dict_cursor else None
        cursor = conn.cursor(cursor_factory=cursor_class)
        yield cursor
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            DatabaseConnectionPool.return_connection(conn)


class DatabaseHealth:
    """Health check utilities for database."""
    
    @staticmethod
    def is_healthy() -> bool:
        """Check if database is healthy."""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    return True
        except Exception as e:
            logger.warning(f"Database health check failed: {e}")
            return False
    
    @staticmethod
    def get_table_counts() -> Dict[str, int]:
        """Get row counts for each table."""
        counts = {}
        try:
            with get_db_cursor(dict_cursor=True) as cursor:
                for table in ["customers", "accounts", "transactions"]:
                    cursor.execute(f"SELECT COUNT(*) as cnt FROM {table}")
                    result = cursor.fetchone()
                    counts[table] = result['cnt'] if result else 0
        except Exception as e:
            logger.error(f"Failed to get table counts: {e}")
        
        return counts
    
    @staticmethod
    def get_database_size() -> str:
        """Get database size."""
        try:
            with get_db_cursor(dict_cursor=True) as cursor:
                cursor.execute(
                    f"SELECT pg_size_pretty(pg_database_size('{postgres_config.DB}')) as size"
                )
                result = cursor.fetchone()
                return result['size'] if result else "Unknown"
        except Exception as e:
            logger.error(f"Failed to get database size: {e}")
            return "Unknown"


class DatabaseInitializer:
    """Initialize and manage database schema."""
    
    @staticmethod
    def wait_for_database(timeout: int = 60):
        """Wait for database to be available."""
        logger.info("Waiting for database to be available...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT 1")
                    logger.info("Database is now available")
                    return True
            except Exception as e:
                logger.debug(f"Database not ready: {e}")
                time.sleep(2)
        
        logger.error(f"Database not available after {timeout} seconds")
        raise TimeoutError("Database connection timeout")
    
    @staticmethod
    def check_schema_exists() -> bool:
        """Check if database schema is initialized."""
        try:
            with get_db_cursor() as cursor:
                cursor.execute(
                    "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='customers')"
                )
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Failed to check schema: {e}")
            return False
    
    @staticmethod
    def initialize_schema(schema_file: str):
        """Initialize database schema from SQL file."""
        try:
            logger.info(f"Initializing schema from {schema_file}")
            with open(schema_file, 'r') as f:
                schema_sql = f.read()
            
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(schema_sql)
            
            logger.info("Schema initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize schema: {e}")
            raise


class DatabaseOperations:
    """Common database operations."""
    
    @staticmethod
    def get_customer_count() -> int:
        """Get total customer count."""
        try:
            with get_db_cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM customers")
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Failed to get customer count: {e}")
            return 0
    
    @staticmethod
    def get_account_count() -> int:
        """Get total account count."""
        try:
            with get_db_cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM accounts")
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Failed to get account count: {e}")
            return 0
    
    @staticmethod
    def get_transaction_count() -> int:
        """Get total transaction count."""
        try:
            with get_db_cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM transactions")
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Failed to get transaction count: {e}")
            return 0
    
    @staticmethod
    def get_total_balance() -> float:
        """Get total account balance."""
        try:
            with get_db_cursor() as cursor:
                cursor.execute("SELECT SUM(balance) FROM accounts")
                result = cursor.fetchone()[0]
                return float(result) if result else 0.0
        except Exception as e:
            logger.error(f"Failed to get total balance: {e}")
            return 0.0
    
    @staticmethod
    def cleanup_old_data(days: int = 30):
        """Clean up old transaction data."""
        try:
            with get_db_cursor() as cursor:
                cursor.execute(
                    "DELETE FROM transactions WHERE created_at < NOW() - INTERVAL %s DAY",
                    (days,)
                )
                logger.info(f"Cleaned up transactions older than {days} days")
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
