"""Monitoring and observability package for WinGetManifestGeneratorTool.

This package provides comprehensive monitoring capabilities including:
- Structured logging with JSON formatting
- Metrics collection for performance monitoring
- Health checks for system status monitoring
- Progress tracking for long-running operations

Usage:
    from src.monitoring import get_logger, MetricsCollector, HealthChecker
    
    # Get structured logger
    logger = get_logger(__name__)
    logger.info("Processing started", extra={"package_count": 100})
    
    # Collect metrics
    metrics = MetricsCollector()
    with metrics.timer("processing_time"):
        # Your processing code here
        pass
    
    # Health checks
    health = HealthChecker()
    status = health.check_all()
"""

from .logging import get_logger, setup_structured_logging
from .metrics import (
    MetricsCollector, get_metrics_collector, timer, increment_counter, 
    set_gauge, observe_histogram, record_metric, timed
)
from .health import HealthChecker, get_health_checker, check_health, check_all_health
from .progress import (
    ProgressTracker, get_progress_tracker, get_progress_manager,
    ProgressContext, track_progress
)

__all__ = [
    'get_logger',
    'setup_structured_logging',
    'MetricsCollector',
    'get_metrics_collector',
    'timer',
    'increment_counter',
    'set_gauge', 
    'observe_histogram',
    'record_metric',
    'timed',
    'HealthChecker',
    'get_health_checker',
    'check_health',
    'check_all_health',
    'ProgressTracker',
    'get_progress_tracker',
    'get_progress_manager',
    'ProgressContext',
    'track_progress'
]
