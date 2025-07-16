"""
Logging setup for the WinGet Manifest Generator Tool.

This module provides centralized logging configuration.
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Dict, Any, Optional


def setup_logging(config: Optional[Dict[str, Any]] = None):
    """
    Set up logging configuration.
    
    Args:
        config: Logging configuration dictionary
    """
    config = config or {}
    
    # Default configuration
    default_config = {
        'level': 'INFO',
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'date_format': '%Y-%m-%d %H:%M:%S',
        'file_logging': True,
        'console_logging': True,
        'log_file': 'logs/winget_tool.log',
        'max_file_size': 10 * 1024 * 1024,  # 10MB
        'backup_count': 5,
    }
    
    # Merge with provided config
    effective_config = {**default_config, **config}
    
    # Create log directory if needed
    log_file = Path(effective_config['log_file'])
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, effective_config['level'].upper()))
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        effective_config['format'],
        datefmt=effective_config['date_format']
    )
    
    # Console handler
    if effective_config['console_logging']:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # File handler with rotation
    if effective_config['file_logging']:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=effective_config['max_file_size'],
            backupCount=effective_config['backup_count']
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Set specific logger levels
    logger_levels = config.get('logger_levels', {})
    for logger_name, level in logger_levels.items():
        logging.getLogger(logger_name).setLevel(getattr(logging, level.upper()))
    
    logging.info("Logging configuration completed")


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name."""
    return logging.getLogger(name)
