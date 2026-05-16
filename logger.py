"""
Centralized logging utility for the Banking Data Pipeline.
Provides structured logging with file and console handlers.
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from typing import Optional

from config import logging_config


class BankingPipelineLogger:
    """Centralized logger for the banking pipeline."""
    
    _loggers = {}
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """Get or create a logger instance."""
        if name in cls._loggers:
            return cls._loggers[name]
        
        logger = cls._create_logger(name)
        cls._loggers[name] = logger
        return logger
    
    @classmethod
    def _create_logger(cls, name: str) -> logging.Logger:
        """Create a new logger instance with handlers."""
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, logging_config.LEVEL))
        
        # Remove existing handlers
        logger.handlers = []
        
        # Create formatters
        formatter = logging.Formatter(
            logging_config.LOG_FORMAT,
            datefmt=logging_config.DATE_FORMAT
        )
        
        # Console handler (always INFO level or higher)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File handler (all levels)
        log_dir = logging_config.LOG_DIR
        os.makedirs(log_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d")
        log_file = os.path.join(
            log_dir,
            f"{logging_config.LOG_FILE_PREFIX}_{name}_{timestamp}.log"
        )
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=logging_config.MAX_BYTES,
            backupCount=logging_config.BACKUP_COUNT
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        return logger


def get_logger(name: str) -> logging.Logger:
    """Convenience function to get a logger."""
    return BankingPipelineLogger.get_logger(name)


class LogContext:
    """Context manager for structured logging."""
    
    def __init__(self, logger: logging.Logger, operation: str, **context):
        self.logger = logger
        self.operation = operation
        self.context = context
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
        self.logger.info(f"Starting: {self.operation} ({context_str})")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds()
        
        if exc_type is None:
            self.logger.info(f"Completed: {self.operation} in {duration:.2f}s")
        else:
            self.logger.error(
                f"Failed: {self.operation} after {duration:.2f}s - {exc_type.__name__}: {exc_val}"
            )
        
        return False  # Propagate exceptions
