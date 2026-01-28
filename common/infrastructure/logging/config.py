"""
Logging configuration module.
This module provides a centralized logging configuration for all services.
"""

import json
import logging
import os
import sys
from typing import Any


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter that includes all extra fields."""

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON."""
        log_data: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": getattr(record, "service", "unknown"),
            "environment": getattr(record, "environment", "unknown"),
        }

        # Add all extra fields
        for key, value in record.__dict__.items():
            if key not in [
                "timestamp",
                "level",
                "logger",
                "message",
                "service",
                "environment",
                "args",
                "exc_info",
                "exc_text",
                "msg",
                "created",
                "msecs",
                "relativeCreated",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "funcName",
                "lineno",
                "processName",
                "process",
                "threadName",
                "thread",
            ]:
                log_data[key] = value

        return json.dumps(log_data)


def configure_logging(
    service_name: str,
    log_level: str = "INFO",
    environment: str = "development",
) -> None:
    """
    Configure logging for the application.

    Args:
        service_name (str): Name of the service (e.g., 'customer-support')
        log_level (str): Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        environment (str): Environment name (development, staging, production)
    """
    # Create formatters
    console_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_formatter = JSONFormatter()

    # Create handlers
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)

    logs_dir: str = "/tmp"
    os.makedirs(logs_dir, exist_ok=True)

    file_handler = logging.FileHandler(os.path.join(logs_dir, f"{service_name}.log"))
    file_handler.setFormatter(file_formatter)

    # Configure root logger
    root_logger: logging.Logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Configure API logger
    api_logger: logging.Logger = logging.getLogger("api")
    api_logger.setLevel(getattr(logging, log_level.upper()))

    # Add default context to all loggers
    for handler in root_logger.handlers:
        handler.addFilter(
            lambda record: setattr(record, "service", service_name) or True
        )
        handler.addFilter(
            lambda record: setattr(record, "environment", environment) or True
        )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.

    Args:
        name (str): Logger name (usually __name__)

    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(name)
