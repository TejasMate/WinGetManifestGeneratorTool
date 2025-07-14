"""Metrics collection system for WinGetManifestGeneratorTool.

This module provides comprehensive metrics collection including:
- Processing time measurements
- Success/failure rate tracking  
- API usage statistics
- Resource utilization monitoring
- Custom business metrics
"""

import time
import threading
from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, Callable
import statistics
import json
from pathlib import Path

try:
    from ..config import get_config
    from .logging import get_logger
    from ..exceptions import MonitoringError
except ImportError:
    # Fallback for direct script execution
    import sys
    sys.path.append(str(Path(__file__).parent.parent))
    from config import get_config
    from .logging import get_logger
    from exceptions import MonitoringError


@dataclass
class MetricValue:
    """Container for a single metric value with metadata."""
    
    name: str
    value: Union[int, float]
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    unit: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags,
            "unit": self.unit
        }


@dataclass
class TimerResult:
    """Result of a timer measurement."""
    
    name: str
    duration: float
    start_time: datetime
    end_time: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "duration": self.duration,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "tags": self.tags
        }


class Timer:
    """Context manager for timing operations."""
    
    def __init__(self, name: str, collector: 'MetricsCollector', 
                 tags: Dict[str, str] = None):
        self.name = name
        self.collector = collector
        self.tags = tags or {}
        self.start_time = None
        self.end_time = None
        self.duration = None
    
    def __enter__(self) -> 'Timer':
        self.start_time = datetime.utcnow()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = datetime.utcnow()
        self.duration = (self.end_time - self.start_time).total_seconds()
        
        # Add error tag if exception occurred
        if exc_type is not None:
            self.tags["error"] = True
            self.tags["error_type"] = exc_type.__name__
        else:
            self.tags["error"] = False
        
        # Record the timing
        self.collector.record_timer(
            TimerResult(
                name=self.name,
                duration=self.duration,
                start_time=self.start_time,
                end_time=self.end_time,
                tags=self.tags
            )
        )


class Counter:
    """Thread-safe counter for metrics."""
    
    def __init__(self, name: str):
        self.name = name
        self._value = 0
        self._lock = threading.Lock()
    
    def increment(self, delta: int = 1) -> int:
        """Increment counter by delta."""
        with self._lock:
            self._value += delta
            return self._value
    
    def decrement(self, delta: int = 1) -> int:
        """Decrement counter by delta."""
        with self._lock:
            self._value -= delta
            return self._value
    
    def reset(self) -> int:
        """Reset counter to zero."""
        with self._lock:
            old_value = self._value
            self._value = 0
            return old_value
    
    @property
    def value(self) -> int:
        """Get current counter value."""
        with self._lock:
            return self._value


class Gauge:
    """Thread-safe gauge for metrics."""
    
    def __init__(self, name: str):
        self.name = name
        self._value = 0.0
        self._lock = threading.Lock()
    
    def set(self, value: Union[int, float]) -> None:
        """Set gauge value."""
        with self._lock:
            self._value = float(value)
    
    def increment(self, delta: Union[int, float] = 1.0) -> float:
        """Increment gauge by delta."""
        with self._lock:
            self._value += delta
            return self._value
    
    def decrement(self, delta: Union[int, float] = 1.0) -> float:
        """Decrement gauge by delta."""
        with self._lock:
            self._value -= delta
            return self._value
    
    @property
    def value(self) -> float:
        """Get current gauge value."""
        with self._lock:
            return self._value


class Histogram:
    """Histogram for tracking distributions of values."""
    
    def __init__(self, name: str, max_samples: int = 1000):
        self.name = name
        self.max_samples = max_samples
        self._samples = deque(maxlen=max_samples)
        self._lock = threading.Lock()
    
    def observe(self, value: Union[int, float]) -> None:
        """Observe a value."""
        with self._lock:
            self._samples.append(float(value))
    
    def get_statistics(self) -> Dict[str, float]:
        """Get histogram statistics."""
        with self._lock:
            if not self._samples:
                return {
                    "count": 0,
                    "min": 0.0,
                    "max": 0.0,
                    "mean": 0.0,
                    "median": 0.0,
                    "p95": 0.0,
                    "p99": 0.0
                }
            
            samples = list(self._samples)
            sorted_samples = sorted(samples)
            count = len(samples)
            
            return {
                "count": count,
                "min": min(samples),
                "max": max(samples),
                "mean": statistics.mean(samples),
                "median": statistics.median(samples),
                "p95": sorted_samples[int(count * 0.95)] if count > 0 else 0.0,
                "p99": sorted_samples[int(count * 0.99)] if count > 0 else 0.0
            }


class MetricsCollector:
    """Central metrics collection system."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self._counters: Dict[str, Counter] = {}
        self._gauges: Dict[str, Gauge] = {}
        self._histograms: Dict[str, Histogram] = {}
        self._timers: List[TimerResult] = []
        self._metrics: List[MetricValue] = []
        self._lock = threading.Lock()
        
        # Configuration
        self.max_timer_history = get_config("monitoring.max_timer_history", 1000)
        self.max_metric_history = get_config("monitoring.max_metric_history", 10000)
        
        # Built-in metrics
        self._init_builtin_metrics()
    
    def _init_builtin_metrics(self):
        """Initialize built-in application metrics."""
        # Processing metrics
        self.get_counter("packages.processed.total")
        self.get_counter("packages.processed.success")
        self.get_counter("packages.processed.failure")
        self.get_counter("packages.skipped")
        
        # API metrics
        self.get_counter("api.requests.total")
        self.get_counter("api.requests.success")
        self.get_counter("api.requests.failure")
        self.get_counter("api.rate_limit_hits")
        
        # GitHub specific metrics
        self.get_counter("github.repositories.processed")
        self.get_counter("github.releases.found")
        self.get_counter("github.api.calls")
        
        # Processing time histograms
        self.get_histogram("processing.duration")
        self.get_histogram("api.response_time")
        self.get_histogram("github.processing_time")
        
        # System metrics
        self.get_gauge("system.memory_usage_mb")
        self.get_gauge("system.active_workers")
        self.get_gauge("system.queue_size")
    
    def get_counter(self, name: str) -> Counter:
        """Get or create a counter."""
        with self._lock:
            if name not in self._counters:
                self._counters[name] = Counter(name)
            return self._counters[name]
    
    def get_gauge(self, name: str) -> Gauge:
        """Get or create a gauge."""
        with self._lock:
            if name not in self._gauges:
                self._gauges[name] = Gauge(name)
            return self._gauges[name]
    
    def get_histogram(self, name: str, max_samples: int = 1000) -> Histogram:
        """Get or create a histogram."""
        with self._lock:
            if name not in self._histograms:
                self._histograms[name] = Histogram(name, max_samples)
            return self._histograms[name]
    
    def timer(self, name: str, tags: Dict[str, str] = None) -> Timer:
        """Create a timer context manager."""
        return Timer(name, self, tags)
    
    def record_timer(self, timer_result: TimerResult) -> None:
        """Record a timer result."""
        with self._lock:
            self._timers.append(timer_result)
            # Keep only recent timers
            if len(self._timers) > self.max_timer_history:
                self._timers = self._timers[-self.max_timer_history:]
        
        # Also record in histogram
        self.get_histogram(f"{timer_result.name}.duration").observe(timer_result.duration)
        
        # Log the timing
        self.logger.log_performance_metric(
            f"{timer_result.name}.duration",
            timer_result.duration,
            "seconds",
            **timer_result.tags
        )
    
    def record_metric(self, name: str, value: Union[int, float], 
                     tags: Dict[str, str] = None, unit: str = None) -> None:
        """Record a custom metric."""
        metric = MetricValue(
            name=name,
            value=value,
            timestamp=datetime.utcnow(),
            tags=tags or {},
            unit=unit
        )
        
        with self._lock:
            self._metrics.append(metric)
            # Keep only recent metrics
            if len(self._metrics) > self.max_metric_history:
                self._metrics = self._metrics[-self.max_metric_history:]
        
        # Log the metric
        self.logger.log_performance_metric(name, value, unit, **metric.tags)
    
    def increment_counter(self, name: str, delta: int = 1, 
                         tags: Dict[str, str] = None) -> int:
        """Increment a counter and optionally record with tags."""
        counter = self.get_counter(name)
        value = counter.increment(delta)
        
        if tags:
            self.record_metric(name, value, tags)
        
        return value
    
    def set_gauge(self, name: str, value: Union[int, float], 
                  tags: Dict[str, str] = None) -> None:
        """Set a gauge value and optionally record with tags."""
        gauge = self.get_gauge(name)
        gauge.set(value)
        
        if tags:
            self.record_metric(name, value, tags)
    
    def observe_histogram(self, name: str, value: Union[int, float],
                         tags: Dict[str, str] = None) -> None:
        """Observe a value in a histogram."""
        histogram = self.get_histogram(name)
        histogram.observe(value)
        
        if tags:
            self.record_metric(name, value, tags)
    
    def record_api_call(self, method: str, endpoint: str, status_code: int,
                       duration: float, success: bool = None) -> None:
        """Record an API call metric."""
        if success is None:
            success = 200 <= status_code < 400
        
        tags = {
            "method": method,
            "endpoint": endpoint,
            "status_code": str(status_code),
            "success": str(success)
        }
        
        # Increment counters
        self.increment_counter("api.requests.total", tags=tags)
        if success:
            self.increment_counter("api.requests.success", tags=tags)
        else:
            self.increment_counter("api.requests.failure", tags=tags)
        
        # Record response time
        self.observe_histogram("api.response_time", duration, tags)
    
    def record_package_processing(self, package_id: str, success: bool,
                                 duration: float, error_type: str = None) -> None:
        """Record package processing metrics."""
        tags = {
            "package_id": package_id,
            "success": str(success)
        }
        
        if error_type:
            tags["error_type"] = error_type
        
        # Increment counters
        self.increment_counter("packages.processed.total", tags=tags)
        if success:
            self.increment_counter("packages.processed.success", tags=tags)
        else:
            self.increment_counter("packages.processed.failure", tags=tags)
        
        # Record processing time
        self.observe_histogram("processing.duration", duration, tags)
    
    def record_github_metrics(self, repo_name: str, releases_found: int,
                             api_calls: int, duration: float) -> None:
        """Record GitHub processing metrics."""
        tags = {"repository": repo_name}
        
        self.increment_counter("github.repositories.processed", tags=tags)
        self.increment_counter("github.releases.found", releases_found, tags)
        self.increment_counter("github.api.calls", api_calls, tags)
        self.observe_histogram("github.processing_time", duration, tags)
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all current metrics."""
        with self._lock:
            metrics = {
                "timestamp": datetime.utcnow().isoformat(),
                "counters": {name: counter.value for name, counter in self._counters.items()},
                "gauges": {name: gauge.value for name, gauge in self._gauges.items()},
                "histograms": {name: histogram.get_statistics() 
                             for name, histogram in self._histograms.items()},
                "recent_timers": [timer.to_dict() for timer in self._timers[-10:]],
                "recent_metrics": [metric.to_dict() for metric in self._metrics[-50:]]
            }
        
        return metrics
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics."""
        metrics = self.get_all_metrics()
        
        # Calculate success rates
        total_packages = metrics["counters"].get("packages.processed.total", 0)
        success_packages = metrics["counters"].get("packages.processed.success", 0)
        package_success_rate = (success_packages / total_packages * 100) if total_packages > 0 else 0
        
        total_api = metrics["counters"].get("api.requests.total", 0)
        success_api = metrics["counters"].get("api.requests.success", 0)
        api_success_rate = (success_api / total_api * 100) if total_api > 0 else 0
        
        return {
            "summary": {
                "packages_processed": total_packages,
                "package_success_rate": round(package_success_rate, 2),
                "api_requests": total_api,
                "api_success_rate": round(api_success_rate, 2),
                "github_repositories": metrics["counters"].get("github.repositories.processed", 0),
                "active_workers": metrics["gauges"].get("system.active_workers", 0)
            },
            "performance": {
                "avg_processing_time": metrics["histograms"].get("processing.duration", {}).get("mean", 0),
                "avg_api_response_time": metrics["histograms"].get("api.response_time", {}).get("mean", 0),
                "p95_processing_time": metrics["histograms"].get("processing.duration", {}).get("p95", 0),
                "p95_api_response_time": metrics["histograms"].get("api.response_time", {}).get("p95", 0)
            }
        }
    
    def export_metrics(self, file_path: Union[str, Path], format: str = "json") -> None:
        """Export metrics to file."""
        metrics = self.get_all_metrics()
        
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format.lower() == "json":
            with open(file_path, 'w') as f:
                json.dump(metrics, f, indent=2, default=str)
        else:
            raise ValueError(f"Unsupported export format: {format}")
        
        self.logger.info("Metrics exported", 
                        file_path=str(file_path), 
                        format=format,
                        metric_count=len(metrics))
    
    def reset_all_metrics(self) -> None:
        """Reset all metrics (useful for testing)."""
        with self._lock:
            for counter in self._counters.values():
                counter.reset()
            for gauge in self._gauges.values():
                gauge.set(0)
            self._histograms.clear()
            self._timers.clear()
            self._metrics.clear()
        
        self.logger.info("All metrics reset")


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    global _metrics_collector
    
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    
    return _metrics_collector


# Convenience functions for common metrics operations
def timer(name: str, tags: Dict[str, str] = None) -> Timer:
    """Create a timer context manager."""
    return get_metrics_collector().timer(name, tags)


def increment_counter(name: str, delta: int = 1, tags: Dict[str, str] = None) -> int:
    """Increment a counter."""
    return get_metrics_collector().increment_counter(name, delta, tags)


def set_gauge(name: str, value: Union[int, float], tags: Dict[str, str] = None) -> None:
    """Set a gauge value."""
    get_metrics_collector().set_gauge(name, value, tags)


def observe_histogram(name: str, value: Union[int, float], tags: Dict[str, str] = None) -> None:
    """Observe a value in a histogram."""
    get_metrics_collector().observe_histogram(name, value, tags)


def record_metric(name: str, value: Union[int, float], 
                 tags: Dict[str, str] = None, unit: str = None) -> None:
    """Record a custom metric."""
    get_metrics_collector().record_metric(name, value, tags, unit)


# Decorator for automatic timing
def timed(metric_name: str = None, tags: Dict[str, str] = None):
    """Decorator for automatic timing of functions.
    
    Args:
        metric_name: Name of the metric (uses function name if None)
        tags: Additional tags for the metric
    """
    def decorator(func):
        import functools
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            name = metric_name or f"{func.__module__}.{func.__name__}"
            with timer(name, tags):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator
