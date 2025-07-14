"""Structured logging implementation for WinGetManifestGeneratorTool.

This module provides structured JSON logging with contextual information,
correlation IDs, and standardized log formats for better observability.
"""

import json
import logging
import logging.handlers
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union
from contextvars import ContextVar

try:
    from ..config import get_config
    from ..exceptions import MonitoringError
except ImportError:
    # Fallback for direct script execution
    import sys
    sys.path.append(str(Path(__file__).parent.parent))
    from config import get_config
    from exceptions import MonitoringError


# Context variables for correlation tracking
correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)
user_id: ContextVar[Optional[str]] = ContextVar('user_id', default=None)


class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs."""
    
    def __init__(self, service_name: str = "winget-automation", 
                 service_version: str = "1.0.0"):
        super().__init__()
        self.service_name = service_name
        self.service_version = service_version
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        # Base log structure
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "service": {
                "name": self.service_name,
                "version": self.service_version
            },
            "process": {
                "pid": record.process,
                "thread": record.thread,
                "thread_name": record.threadName
            },
            "source": {
                "file": record.filename,
                "line": record.lineno,
                "function": record.funcName,
                "module": record.module
            }
        }
        
        # Add correlation ID if available
        corr_id = correlation_id.get()
        if corr_id:
            log_entry["correlation_id"] = corr_id
        
        # Add user ID if available
        uid = user_id.get()
        if uid:
            log_entry["user_id"] = uid
        
        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
        
        # Add extra fields from the log record
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in {
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                'filename', 'module', 'lineno', 'funcName', 'created',
                'msecs', 'relativeCreated', 'thread', 'threadName',
                'processName', 'process', 'getMessage', 'exc_info',
                'exc_text', 'stack_info', 'message'
            }:
                extra_fields[key] = self._serialize_value(value)
        
        if extra_fields:
            log_entry["extra"] = extra_fields
        
        # Add stack info if available
        if record.stack_info:
            log_entry["stack_trace"] = record.stack_info
        
        return json.dumps(log_entry, default=str, ensure_ascii=False)
    
    def _serialize_value(self, value: Any) -> Any:
        """Serialize a value for JSON output."""
        if isinstance(value, (str, int, float, bool, type(None))):
            return value
        elif isinstance(value, (list, tuple)):
            return [self._serialize_value(item) for item in value]
        elif isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}
        elif hasattr(value, '__dict__'):
            return {k: self._serialize_value(v) for k, v in value.__dict__.items()}
        else:
            return str(value)


class ContextFilter(logging.Filter):
    """Filter to add contextual information to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add context information to log record."""
        # Add correlation ID
        corr_id = correlation_id.get()
        if corr_id:
            record.correlation_id = corr_id
        
        # Add user ID
        uid = user_id.get()
        if uid:
            record.user_id = uid
        
        return True


class StructuredLogger:
    """Enhanced logger with structured logging capabilities."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._setup_done = False
    
    def _ensure_setup(self):
        """Ensure logger is properly configured."""
        if not self._setup_done:
            setup_structured_logging()
            self._setup_done = True
    
    def debug(self, message: str, **kwargs):
        """Log debug message with structured data."""
        self._ensure_setup()
        self.logger.debug(message, extra=kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message with structured data."""
        self._ensure_setup()
        self.logger.info(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with structured data."""
        self._ensure_setup()
        self.logger.warning(message, extra=kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with structured data."""
        self._ensure_setup()
        self.logger.error(message, extra=kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message with structured data."""
        self._ensure_setup()
        self.logger.critical(message, extra=kwargs)
    
    def exception(self, message: str, **kwargs):
        """Log exception with structured data."""
        self._ensure_setup()
        self.logger.exception(message, extra=kwargs)
    
    def log_operation_start(self, operation: str, **context):
        """Log the start of an operation."""
        self.info(f"Operation started: {operation}", 
                 operation=operation, 
                 operation_status="started",
                 **context)
    
    def log_operation_success(self, operation: str, duration: float = None, **context):
        """Log successful completion of an operation."""
        extra = {
            "operation": operation,
            "operation_status": "success",
            **context
        }
        if duration is not None:
            extra["duration_seconds"] = duration
        
        self.info(f"Operation completed successfully: {operation}", **extra)
    
    def log_operation_failure(self, operation: str, error: Exception = None, 
                            duration: float = None, **context):
        """Log failure of an operation."""
        extra = {
            "operation": operation,
            "operation_status": "failure",
            **context
        }
        if duration is not None:
            extra["duration_seconds"] = duration
        if error:
            extra["error_type"] = type(error).__name__
            extra["error_message"] = str(error)
        
        self.error(f"Operation failed: {operation}", **extra)
    
    def log_api_request(self, method: str, url: str, status_code: int = None,
                       duration: float = None, **context):
        """Log API request with structured data."""
        extra = {
            "api_method": method,
            "api_url": url,
            "request_type": "api_request",
            **context
        }
        
        if status_code is not None:
            extra["api_status_code"] = status_code
        if duration is not None:
            extra["api_duration_seconds"] = duration
        
        message = f"API request: {method} {url}"
        if status_code:
            message += f" -> {status_code}"
        
        if status_code and status_code >= 400:
            self.warning(message, **extra)
        else:
            self.info(message, **extra)
    
    def log_performance_metric(self, metric_name: str, value: float, unit: str = None, **context):
        """Log performance metric."""
        extra = {
            "metric_name": metric_name,
            "metric_value": value,
            "metric_type": "performance",
            **context
        }
        
        if unit:
            extra["metric_unit"] = unit
        
        self.info(f"Performance metric: {metric_name} = {value}" + 
                 (f" {unit}" if unit else ""), **extra)


def setup_structured_logging(force_setup: bool = False) -> None:
    """Set up structured logging for the application.
    
    Args:
        force_setup: Force setup even if already configured
    """
    root_logger = logging.getLogger()
    
    # Check if already configured
    if root_logger.handlers and not force_setup:
        return
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Get logging configuration
    log_level = get_config("logging.level", "INFO")
    log_format = get_config("logging.format", "structured")
    log_file = get_config("logging.file", None)
    max_size = get_config("logging.max_size", 10) * 1024 * 1024  # Convert MB to bytes
    backup_count = get_config("logging.backup_count", 5)
    service_name = get_config("service.name", "winget-automation")
    service_version = get_config("service.version", "1.0.0")
    
    # Set logging level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger.setLevel(numeric_level)
    
    # Create formatters
    if log_format.lower() == "structured":
        formatter = StructuredFormatter(service_name, service_version)
    else:
        # Fallback to standard formatter
        formatter = logging.Formatter(
            fmt=get_config("logging.format", 
                          "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
            datefmt=get_config("logging.date_format", "%Y-%m-%d %H:%M:%S")
        )
    
    # Create context filter
    context_filter = ContextFilter()
    
    # Console handler (always present)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(context_filter)
    root_logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_path,
            maxBytes=max_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.addFilter(context_filter)
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured StructuredLogger instance
    """
    return StructuredLogger(name)


def set_correlation_id(corr_id: str = None) -> str:
    """Set correlation ID for current context.
    
    Args:
        corr_id: Correlation ID to set (generates UUID if None)
        
    Returns:
        The correlation ID that was set
    """
    if corr_id is None:
        corr_id = str(uuid.uuid4())
    
    correlation_id.set(corr_id)
    return corr_id


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID.
    
    Returns:
        Current correlation ID or None if not set
    """
    return correlation_id.get()


def set_user_id(uid: str) -> None:
    """Set user ID for current context.
    
    Args:
        uid: User ID to set
    """
    user_id.set(uid)


def get_user_id() -> Optional[str]:
    """Get current user ID.
    
    Returns:
        Current user ID or None if not set
    """
    return user_id.get()


def clear_context() -> None:
    """Clear all context variables."""
    correlation_id.set(None)
    user_id.set(None)


# Context manager for correlation tracking
class CorrelationContext:
    """Context manager for setting correlation ID."""
    
    def __init__(self, corr_id: str = None):
        self.corr_id = corr_id
        self.previous_corr_id = None
    
    def __enter__(self) -> str:
        self.previous_corr_id = correlation_id.get()
        self.corr_id = set_correlation_id(self.corr_id)
        return self.corr_id
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        correlation_id.set(self.previous_corr_id)


# Decorator for automatic operation logging
def log_operation(operation_name: str = None, logger_name: str = None):
    """Decorator for automatic operation logging.
    
    Args:
        operation_name: Name of the operation (uses function name if None)
        logger_name: Logger name (uses function module if None)
    """
    def decorator(func):
        import functools
        import time
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            op_name = operation_name or func.__name__
            log_name = logger_name or func.__module__
            logger = get_logger(log_name)
            
            start_time = time.time()
            logger.log_operation_start(op_name, function=func.__name__)
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                logger.log_operation_success(op_name, duration=duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.log_operation_failure(op_name, error=e, duration=duration)
                raise
        
        return wrapper
    return decorator
