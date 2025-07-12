"""Progress tracking system for WinGetManifestGeneratorTool.

This module provides comprehensive progress tracking for long-running operations
including visual progress bars, ETA calculations, and real-time status updates.
"""

import time
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Union
from enum import Enum
import json
import sys
from pathlib import Path

try:
    from ..config import get_config
    from .logging import get_logger
    from .metrics import get_metrics_collector
    from ..exceptions import MonitoringError
except ImportError:
    # Fallback for direct script execution
    import sys
    sys.path.append(str(Path(__file__).parent.parent))
    from config import get_config
    from .logging import get_logger
    from .metrics import get_metrics_collector
    from exceptions import MonitoringError


class ProgressStatus(Enum):
    """Progress tracking status."""
    NOT_STARTED = "not_started"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ProgressStep:
    """Individual step in a progress tracker."""
    
    name: str
    total: int = 0
    current: int = 0
    status: ProgressStatus = ProgressStatus.NOT_STARTED
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def percentage(self) -> float:
        """Calculate percentage completion."""
        if self.total == 0:
            return 0.0
        return min(100.0, (self.current / self.total) * 100)
    
    @property
    def duration(self) -> Optional[timedelta]:
        """Calculate duration."""
        if self.start_time is None:
            return None
        end = self.end_time or datetime.utcnow()
        return end - self.start_time
    
    @property
    def rate(self) -> Optional[float]:
        """Calculate processing rate (items per second)."""
        duration = self.duration
        if duration is None or duration.total_seconds() == 0 or self.current == 0:
            return None
        return self.current / duration.total_seconds()
    
    @property
    def eta(self) -> Optional[timedelta]:
        """Calculate estimated time of arrival."""
        if self.status != ProgressStatus.RUNNING or self.total == 0 or self.current == 0:
            return None
        
        rate = self.rate
        if rate is None or rate == 0:
            return None
        
        remaining = self.total - self.current
        eta_seconds = remaining / rate
        return timedelta(seconds=eta_seconds)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "total": self.total,
            "current": self.current,
            "percentage": round(self.percentage, 2),
            "status": self.status.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": str(self.duration) if self.duration else None,
            "rate": round(self.rate, 2) if self.rate else None,
            "eta": str(self.eta) if self.eta else None,
            "message": self.message,
            "metadata": self.metadata
        }


class ProgressBar:
    """Simple text-based progress bar."""
    
    def __init__(self, width: int = 50, fill_char: str = '█', empty_char: str = '░'):
        self.width = width
        self.fill_char = fill_char
        self.empty_char = empty_char
    
    def render(self, percentage: float, message: str = "") -> str:
        """Render progress bar as string."""
        filled_width = int(self.width * percentage / 100)
        bar = self.fill_char * filled_width + self.empty_char * (self.width - filled_width)
        
        return f"[{bar}] {percentage:6.2f}% {message}"
    
    def print_progress(self, percentage: float, message: str = "", clear_line: bool = True):
        """Print progress bar to stdout."""
        if clear_line:
            print('\r' + ' ' * 100 + '\r', end='')  # Clear line
        
        progress_str = self.render(percentage, message)
        print(f'\r{progress_str}', end='', flush=True)
        
        if percentage >= 100:
            print()  # New line when complete


class ProgressTracker:
    """Multi-step progress tracker with real-time updates."""
    
    def __init__(self, name: str, steps: List[str] = None):
        self.name = name
        self.steps: Dict[str, ProgressStep] = {}
        self.current_step: Optional[str] = None
        self.overall_status = ProgressStatus.NOT_STARTED
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.logger = get_logger(__name__)
        self.metrics = get_metrics_collector()
        self._lock = threading.Lock()
        self._callbacks: List[Callable[[str, ProgressStep], None]] = []
        self._console_output = get_config("monitoring.progress.console_output", True)
        self._log_updates = get_config("monitoring.progress.log_updates", True)
        self._update_interval = get_config("monitoring.progress.update_interval", 1.0)
        self._last_update = 0.0
        
        # Initialize steps
        if steps:
            for step_name in steps:
                self.add_step(step_name)
    
    def add_step(self, name: str, total: int = 0) -> ProgressStep:
        """Add a new progress step."""
        with self._lock:
            step = ProgressStep(name=name, total=total)
            self.steps[name] = step
        
        self.logger.debug(f"Progress step added: {name}", 
                         tracker=self.name, 
                         step=name, 
                         total=total)
        
        return step
    
    def get_step(self, name: str) -> Optional[ProgressStep]:
        """Get a progress step by name."""
        with self._lock:
            return self.steps.get(name)
    
    def start_tracker(self):
        """Start the overall progress tracker."""
        with self._lock:
            self.overall_status = ProgressStatus.RUNNING
            self.start_time = datetime.utcnow()
        
        self.logger.info(f"Progress tracker started: {self.name}",
                        tracker=self.name,
                        steps_count=len(self.steps))
        
        # Record metric
        self.metrics.increment_counter("progress.trackers.started")
    
    def start_step(self, name: str, total: int = None, message: str = "") -> ProgressStep:
        """Start a specific step."""
        step = self.get_step(name)
        if step is None:
            step = self.add_step(name, total or 0)
        
        with self._lock:
            self.current_step = name
            step.status = ProgressStatus.RUNNING
            step.start_time = datetime.utcnow()
            step.message = message
            if total is not None:
                step.total = total
        
        self.logger.info(f"Progress step started: {name}",
                        tracker=self.name,
                        step=name,
                        total=step.total,
                        step_message=message)
        
        self._notify_callbacks(name, step)
        return step
    
    def update_step(self, name: str, current: int = None, increment: int = None,
                   message: str = None, metadata: Dict[str, Any] = None):
        """Update progress for a step."""
        step = self.get_step(name)
        if step is None:
            raise ValueError(f"Progress step '{name}' not found")
        
        with self._lock:
            if current is not None:
                step.current = current
            elif increment is not None:
                step.current += increment
            
            if message is not None:
                step.message = message
            
            if metadata is not None:
                step.metadata.update(metadata)
        
        # Rate-limited logging and callbacks
        current_time = time.time()
        if current_time - self._last_update >= self._update_interval:
            self._last_update = current_time
            
            if self._log_updates:
                self.logger.debug(f"Progress step updated: {name}",
                                tracker=self.name,
                                step=name,
                                current=step.current,
                                total=step.total,
                                percentage=step.percentage,
                                step_message=step.message)
            
            self._notify_callbacks(name, step)
            
            # Console output
            if self._console_output and name == self.current_step:
                self._print_progress(step)
    
    def complete_step(self, name: str, message: str = ""):
        """Mark a step as completed."""
        step = self.get_step(name)
        if step is None:
            raise ValueError(f"Progress step '{name}' not found")
        
        with self._lock:
            step.status = ProgressStatus.COMPLETED
            step.end_time = datetime.utcnow()
            step.current = step.total
            if message:
                step.message = message
        
        self.logger.info(f"Progress step completed: {name}",
                        tracker=self.name,
                        step=name,
                        duration=str(step.duration),
                        rate=step.rate,
                        step_message=step.message)
        
        # Record metrics
        if step.duration:
            self.metrics.observe_histogram("progress.step.duration", 
                                          step.duration.total_seconds(),
                                          tags={"tracker": self.name, "step": name})
        
        if step.rate:
            self.metrics.observe_histogram("progress.step.rate",
                                         step.rate,
                                         tags={"tracker": self.name, "step": name})
        
        self._notify_callbacks(name, step)
        
        if self._console_output and name == self.current_step:
            self._print_progress(step, completed=True)
    
    def fail_step(self, name: str, error: Exception = None, message: str = ""):
        """Mark a step as failed."""
        step = self.get_step(name)
        if step is None:
            raise ValueError(f"Progress step '{name}' not found")
        
        with self._lock:
            step.status = ProgressStatus.FAILED
            step.end_time = datetime.utcnow()
            if message:
                step.message = message
            if error:
                step.metadata["error"] = str(error)
                step.metadata["error_type"] = type(error).__name__
        
        self.logger.error(f"Progress step failed: {name}",
                         tracker=self.name,
                         step=name,
                         error=str(error) if error else None,
                         step_message=step.message)
        
        # Record metric
        self.metrics.increment_counter("progress.steps.failed",
                                     tags={"tracker": self.name, "step": name})
        
        self._notify_callbacks(name, step)
    
    def complete_tracker(self, message: str = ""):
        """Mark the entire tracker as completed."""
        with self._lock:
            self.overall_status = ProgressStatus.COMPLETED
            self.end_time = datetime.utcnow()
        
        duration = self.end_time - (self.start_time or self.end_time)
        
        self.logger.info(f"Progress tracker completed: {self.name}",
                        tracker=self.name,
                        duration=str(duration),
                        steps_completed=sum(1 for s in self.steps.values() 
                                          if s.status == ProgressStatus.COMPLETED),
                        total_steps=len(self.steps),
                        completion_message=message)
        
        # Record metrics
        self.metrics.increment_counter("progress.trackers.completed")
        self.metrics.observe_histogram("progress.tracker.duration",
                                     duration.total_seconds(),
                                     tags={"tracker": self.name})
    
    def fail_tracker(self, error: Exception = None, message: str = ""):
        """Mark the entire tracker as failed."""
        with self._lock:
            self.overall_status = ProgressStatus.FAILED
            self.end_time = datetime.utcnow()
        
        self.logger.error(f"Progress tracker failed: {self.name}",
                         tracker=self.name,
                         error=str(error) if error else None,
                         failure_message=message)
        
        # Record metric
        self.metrics.increment_counter("progress.trackers.failed")
    
    def get_overall_progress(self) -> Dict[str, Any]:
        """Get overall progress information."""
        with self._lock:
            completed_steps = sum(1 for s in self.steps.values() 
                                if s.status == ProgressStatus.COMPLETED)
            failed_steps = sum(1 for s in self.steps.values() 
                             if s.status == ProgressStatus.FAILED)
            running_steps = sum(1 for s in self.steps.values() 
                              if s.status == ProgressStatus.RUNNING)
            
            total_items = sum(s.total for s in self.steps.values())
            completed_items = sum(s.current for s in self.steps.values())
            
            overall_percentage = (completed_items / total_items * 100) if total_items > 0 else 0
            
            duration = None
            if self.start_time:
                end = self.end_time or datetime.utcnow()
                duration = end - self.start_time
            
            return {
                "name": self.name,
                "status": self.overall_status.value,
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "end_time": self.end_time.isoformat() if self.end_time else None,
                "duration": str(duration) if duration else None,
                "current_step": self.current_step,
                "steps": {
                    "total": len(self.steps),
                    "completed": completed_steps,
                    "failed": failed_steps,
                    "running": running_steps
                },
                "items": {
                    "total": total_items,
                    "completed": completed_items,
                    "percentage": round(overall_percentage, 2)
                },
                "step_details": {name: step.to_dict() for name, step in self.steps.items()}
            }
    
    def add_callback(self, callback: Callable[[str, ProgressStep], None]):
        """Add a callback for progress updates."""
        self._callbacks.append(callback)
    
    def remove_callback(self, callback: Callable[[str, ProgressStep], None]):
        """Remove a callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def _notify_callbacks(self, step_name: str, step: ProgressStep):
        """Notify all registered callbacks."""
        for callback in self._callbacks:
            try:
                callback(step_name, step)
            except Exception as e:
                self.logger.warning(f"Progress callback failed: {str(e)}",
                                  tracker=self.name,
                                  step=step_name,
                                  error=str(e))
    
    def _print_progress(self, step: ProgressStep, completed: bool = False):
        """Print progress to console."""
        if not self._console_output:
            return
        
        bar = ProgressBar()
        message = f"{step.name}: {step.message}" if step.message else step.name
        
        if step.eta and not completed:
            message += f" (ETA: {step.eta})"
        
        bar.print_progress(step.percentage, message, clear_line=True)
    
    def export_progress(self, file_path: Union[str, Path]):
        """Export progress data to file."""
        progress_data = self.get_overall_progress()
        
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w') as f:
            json.dump(progress_data, f, indent=2, default=str)
        
        self.logger.info("Progress data exported",
                        tracker=self.name,
                        file_path=str(file_path))


class ProgressManager:
    """Manager for multiple progress trackers."""
    
    def __init__(self):
        self.trackers: Dict[str, ProgressTracker] = {}
        self.logger = get_logger(__name__)
        self._lock = threading.Lock()
    
    def create_tracker(self, name: str, steps: List[str] = None) -> ProgressTracker:
        """Create a new progress tracker."""
        with self._lock:
            if name in self.trackers:
                raise ValueError(f"Progress tracker '{name}' already exists")
            
            tracker = ProgressTracker(name, steps)
            self.trackers[name] = tracker
        
        self.logger.info(f"Progress tracker created: {name}",
                        tracker=name,
                        steps=steps or [])
        
        return tracker
    
    def get_tracker(self, name: str) -> Optional[ProgressTracker]:
        """Get a progress tracker by name."""
        with self._lock:
            return self.trackers.get(name)
    
    def remove_tracker(self, name: str) -> bool:
        """Remove a progress tracker."""
        with self._lock:
            removed = self.trackers.pop(name, None) is not None
        
        if removed:
            self.logger.info(f"Progress tracker removed: {name}", tracker=name)
        
        return removed
    
    def get_all_progress(self) -> Dict[str, Dict[str, Any]]:
        """Get progress information for all trackers."""
        with self._lock:
            return {name: tracker.get_overall_progress() 
                   for name, tracker in self.trackers.items()}
    
    def cleanup_completed(self, max_age_hours: int = 24):
        """Remove completed trackers older than max_age_hours."""
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        removed_count = 0
        
        with self._lock:
            to_remove = []
            for name, tracker in self.trackers.items():
                if (tracker.overall_status in [ProgressStatus.COMPLETED, ProgressStatus.FAILED] and
                    tracker.end_time and tracker.end_time < cutoff_time):
                    to_remove.append(name)
            
            for name in to_remove:
                del self.trackers[name]
                removed_count += 1
        
        if removed_count > 0:
            self.logger.info(f"Cleaned up {removed_count} old progress trackers")
        
        return removed_count


# Global progress manager instance
_progress_manager: Optional[ProgressManager] = None


def get_progress_tracker(name: str, steps: List[str] = None, 
                        create_if_not_exists: bool = True) -> Optional[ProgressTracker]:
    """Get or create a progress tracker."""
    global _progress_manager
    
    if _progress_manager is None:
        _progress_manager = ProgressManager()
    
    tracker = _progress_manager.get_tracker(name)
    if tracker is None and create_if_not_exists:
        tracker = _progress_manager.create_tracker(name, steps)
    
    return tracker


def get_progress_manager() -> ProgressManager:
    """Get the global progress manager instance."""
    global _progress_manager
    
    if _progress_manager is None:
        _progress_manager = ProgressManager()
    
    return _progress_manager


# Context manager for automatic progress tracking
class ProgressContext:
    """Context manager for automatic progress tracking."""
    
    def __init__(self, tracker_name: str, step_name: str, total: int = 0, 
                 message: str = ""):
        self.tracker_name = tracker_name
        self.step_name = step_name
        self.total = total
        self.message = message
        self.tracker: Optional[ProgressTracker] = None
    
    def __enter__(self) -> ProgressTracker:
        self.tracker = get_progress_tracker(self.tracker_name)
        if self.tracker.overall_status == ProgressStatus.NOT_STARTED:
            self.tracker.start_tracker()
        
        self.tracker.start_step(self.step_name, self.total, self.message)
        return self.tracker
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.tracker:
            if exc_type is None:
                self.tracker.complete_step(self.step_name)
            else:
                self.tracker.fail_step(self.step_name, exc_val)


# Decorator for automatic progress tracking
def track_progress(tracker_name: str, step_name: str = None, total: int = 0):
    """Decorator for automatic progress tracking.
    
    Args:
        tracker_name: Name of the progress tracker
        step_name: Name of the step (uses function name if None)
        total: Total items to process
    """
    def decorator(func):
        import functools
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            name = step_name or func.__name__
            with ProgressContext(tracker_name, name, total):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator
