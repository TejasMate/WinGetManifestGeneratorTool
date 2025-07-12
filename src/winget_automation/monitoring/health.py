"""Health monitoring system for WinGetManifestGeneratorTool.

This module provides comprehensive health checking capabilities including:
- System resource monitoring
- External service connectivity checks
- Application component status
- Configuration validation
- Performance health indicators
"""

import os
import sys
import time
import psutil
import requests
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Union
import threading
import json

try:
    from ..config import get_config, get_config_manager
    from .logging import get_logger
    from .metrics import get_metrics_collector
    from ..exceptions import MonitoringError
except ImportError:
    # Fallback for direct script execution
    import sys
    sys.path.append(str(Path(__file__).parent.parent))
    from config import get_config, get_config_manager
    from .logging import get_logger
    from .metrics import get_metrics_collector
    from exceptions import MonitoringError


class HealthStatus(Enum):
    """Health check status levels."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    
    name: str
    status: HealthStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    duration: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "duration": self.duration
        }


class HealthCheck:
    """Base class for health checks."""
    
    def __init__(self, name: str, timeout: float = 30.0):
        self.name = name
        self.timeout = timeout
        self.logger = get_logger(__name__)
    
    def check(self) -> HealthCheckResult:
        """Perform the health check."""
        start_time = time.time()
        
        try:
            result = self._check_impl()
            result.duration = time.time() - start_time
            return result
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"Health check failed: {self.name}", 
                            error=str(e), 
                            error_type=type(e).__name__,
                            duration=duration)
            
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.CRITICAL,
                message=f"Health check failed: {str(e)}",
                details={"error_type": type(e).__name__, "error": str(e)},
                duration=duration
            )
    
    def _check_impl(self) -> HealthCheckResult:
        """Implementation of the health check. Override in subclasses."""
        raise NotImplementedError


class SystemResourcesCheck(HealthCheck):
    """Check system resource usage."""
    
    def __init__(self, cpu_threshold: float = 80.0, memory_threshold: float = 80.0,
                 disk_threshold: float = 90.0):
        super().__init__("system_resources")
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.disk_threshold = disk_threshold
    
    def _check_impl(self) -> HealthCheckResult:
        """Check system resource usage."""
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # Disk usage (current working directory)
        disk = psutil.disk_usage('.')
        disk_percent = (disk.used / disk.total) * 100
        
        details = {
            "cpu_percent": cpu_percent,
            "memory_percent": memory_percent,
            "memory_available_gb": round(memory.available / (1024**3), 2),
            "memory_total_gb": round(memory.total / (1024**3), 2),
            "disk_percent": round(disk_percent, 2),
            "disk_free_gb": round(disk.free / (1024**3), 2),
            "disk_total_gb": round(disk.total / (1024**3), 2)
        }
        
        # Determine status
        status = HealthStatus.HEALTHY
        issues = []
        
        if cpu_percent > self.cpu_threshold:
            status = HealthStatus.WARNING if cpu_percent < 95 else HealthStatus.CRITICAL
            issues.append(f"High CPU usage: {cpu_percent}%")
        
        if memory_percent > self.memory_threshold:
            status = max(status, HealthStatus.WARNING if memory_percent < 95 else HealthStatus.CRITICAL)
            issues.append(f"High memory usage: {memory_percent}%")
        
        if disk_percent > self.disk_threshold:
            status = max(status, HealthStatus.WARNING if disk_percent < 98 else HealthStatus.CRITICAL)
            issues.append(f"High disk usage: {disk_percent}%")
        
        message = "System resources are healthy"
        if issues:
            message = f"Resource issues detected: {'; '.join(issues)}"
        
        return HealthCheckResult(
            name=self.name,
            status=status,
            message=message,
            details=details
        )


class ConfigurationCheck(HealthCheck):
    """Check application configuration."""
    
    def __init__(self):
        super().__init__("configuration")
    
    def _check_impl(self) -> HealthCheckResult:
        """Check configuration validity."""
        try:
            config_manager = get_config_manager()
            
            # Validate configuration
            is_valid, errors = config_manager.validate_config()
            
            if is_valid:
                # Additional checks
                details = {
                    "environment": config_manager.environment,
                    "config_path": str(config_manager.config_path),
                    "github_tokens_configured": len(get_config("github.tokens", [])),
                    "log_level": get_config("logging.level", "INFO"),
                    "max_workers": get_config("package_processing.max_workers", 4)
                }
                
                # Check for GitHub tokens
                tokens = get_config("github.tokens", [])
                if not tokens:
                    return HealthCheckResult(
                        name=self.name,
                        status=HealthStatus.WARNING,
                        message="No GitHub tokens configured - API rate limiting may occur",
                        details=details
                    )
                
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.HEALTHY,
                    message="Configuration is valid and complete",
                    details=details
                )
            else:
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.CRITICAL,
                    message="Configuration validation failed",
                    details={"errors": errors}
                )
        
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.CRITICAL,
                message=f"Configuration check failed: {str(e)}",
                details={"error": str(e)}
            )


class GitHubAPICheck(HealthCheck):
    """Check GitHub API connectivity and rate limits."""
    
    def __init__(self, timeout: float = 10.0):
        super().__init__("github_api", timeout)
    
    def _check_impl(self) -> HealthCheckResult:
        """Check GitHub API status."""
        tokens = get_config("github.tokens", [])
        api_url = get_config("github.api_url", "https://api.github.com")
        
        if not tokens:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.WARNING,
                message="No GitHub tokens configured",
                details={"tokens_count": 0}
            )
        
        # Test first token
        token = tokens[0]
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        try:
            # Check rate limit endpoint
            response = requests.get(
                f"{api_url}/rate_limit",
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                rate_limit_data = response.json()
                core_limit = rate_limit_data.get("resources", {}).get("core", {})
                
                remaining = core_limit.get("remaining", 0)
                limit = core_limit.get("limit", 5000)
                reset_time = datetime.fromtimestamp(core_limit.get("reset", 0))
                
                details = {
                    "tokens_count": len(tokens),
                    "rate_limit_remaining": remaining,
                    "rate_limit_total": limit,
                    "rate_limit_reset": reset_time.isoformat(),
                    "rate_limit_percentage": round((remaining / limit) * 100, 2) if limit > 0 else 0
                }
                
                # Determine status based on remaining rate limit
                if remaining < 100:
                    status = HealthStatus.CRITICAL
                    message = f"GitHub API rate limit critically low: {remaining}/{limit}"
                elif remaining < 500:
                    status = HealthStatus.WARNING
                    message = f"GitHub API rate limit low: {remaining}/{limit}"
                else:
                    status = HealthStatus.HEALTHY
                    message = f"GitHub API is accessible: {remaining}/{limit} requests remaining"
                
                return HealthCheckResult(
                    name=self.name,
                    status=status,
                    message=message,
                    details=details
                )
            else:
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.CRITICAL,
                    message=f"GitHub API returned status {response.status_code}",
                    details={"status_code": response.status_code, "response": response.text[:500]}
                )
        
        except requests.RequestException as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.CRITICAL,
                message=f"GitHub API connectivity failed: {str(e)}",
                details={"error": str(e)}
            )


class WinGetRepositoryCheck(HealthCheck):
    """Check WinGet repository availability."""
    
    def __init__(self):
        super().__init__("winget_repository")
    
    def _check_impl(self) -> HealthCheckResult:
        """Check WinGet repository status."""
        repo_path = Path(get_config("package_processing.winget_repo_path", "winget-pkgs"))
        
        if not repo_path.exists():
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.CRITICAL,
                message=f"WinGet repository not found at {repo_path}",
                details={"repo_path": str(repo_path), "exists": False}
            )
        
        # Check if it's a git repository
        git_dir = repo_path / ".git"
        is_git_repo = git_dir.exists()
        
        # Count manifest files
        manifest_patterns = get_config("package_processing.file_patterns", ["*.installer.yaml"])
        manifest_count = 0
        
        for pattern in manifest_patterns:
            manifest_count += len(list(repo_path.rglob(pattern)))
        
        details = {
            "repo_path": str(repo_path),
            "exists": True,
            "is_git_repository": is_git_repo,
            "manifest_count": manifest_count,
            "size_gb": round(sum(f.stat().st_size for f in repo_path.rglob('*') if f.is_file()) / (1024**3), 2)
        }
        
        if manifest_count == 0:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.WARNING,
                message="No manifest files found in repository",
                details=details
            )
        
        return HealthCheckResult(
            name=self.name,
            status=HealthStatus.HEALTHY,
            message=f"WinGet repository is accessible with {manifest_count} manifest files",
            details=details
        )


class ApplicationMetricsCheck(HealthCheck):
    """Check application metrics and performance."""
    
    def __init__(self):
        super().__init__("application_metrics")
    
    def _check_impl(self) -> HealthCheckResult:
        """Check application metrics health."""
        metrics_collector = get_metrics_collector()
        summary = metrics_collector.get_summary_stats()
        
        details = summary.copy()
        
        # Check for error rates
        package_success_rate = summary["summary"]["package_success_rate"]
        api_success_rate = summary["summary"]["api_success_rate"]
        
        issues = []
        status = HealthStatus.HEALTHY
        
        if package_success_rate < 95 and summary["summary"]["packages_processed"] > 10:
            issues.append(f"Low package success rate: {package_success_rate}%")
            status = HealthStatus.WARNING if package_success_rate > 80 else HealthStatus.CRITICAL
        
        if api_success_rate < 95 and summary["summary"]["api_requests"] > 10:
            issues.append(f"Low API success rate: {api_success_rate}%")
            status = max(status, HealthStatus.WARNING if api_success_rate > 80 else HealthStatus.CRITICAL)
        
        # Check response times
        avg_processing_time = summary["performance"]["avg_processing_time"]
        if avg_processing_time > 10:  # More than 10 seconds average
            issues.append(f"High processing time: {avg_processing_time:.2f}s")
            status = max(status, HealthStatus.WARNING)
        
        message = "Application metrics are healthy"
        if issues:
            message = f"Performance issues detected: {'; '.join(issues)}"
        
        return HealthCheckResult(
            name=self.name,
            status=status,
            message=message,
            details=details
        )


class HealthChecker:
    """Main health checking coordinator."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.checks: List[HealthCheck] = []
        self._last_check_time = None
        self._last_results: Dict[str, HealthCheckResult] = {}
        self._lock = threading.Lock()
        
        # Register default checks
        self._register_default_checks()
    
    def _register_default_checks(self):
        """Register default health checks."""
        self.checks = [
            SystemResourcesCheck(),
            ConfigurationCheck(),
            GitHubAPICheck(),
            WinGetRepositoryCheck(),
            ApplicationMetricsCheck()
        ]
    
    def add_check(self, check: HealthCheck):
        """Add a custom health check."""
        with self._lock:
            self.checks.append(check)
        
        self.logger.info("Health check added", check_name=check.name)
    
    def remove_check(self, check_name: str) -> bool:
        """Remove a health check by name."""
        with self._lock:
            initial_count = len(self.checks)
            self.checks = [check for check in self.checks if check.name != check_name]
            removed = len(self.checks) < initial_count
        
        if removed:
            self.logger.info("Health check removed", check_name=check_name)
        
        return removed
    
    def check_health(self, check_names: List[str] = None) -> Dict[str, HealthCheckResult]:
        """Perform health checks.
        
        Args:
            check_names: Specific checks to run (all if None)
            
        Returns:
            Dictionary of check results
        """
        start_time = time.time()
        results = {}
        
        checks_to_run = self.checks
        if check_names:
            checks_to_run = [check for check in self.checks if check.name in check_names]
        
        self.logger.info("Starting health checks", 
                        check_count=len(checks_to_run),
                        check_names=[check.name for check in checks_to_run])
        
        for check in checks_to_run:
            try:
                result = check.check()
                results[check.name] = result
                
                self.logger.info(f"Health check completed: {check.name}",
                               check_name=check.name,
                               status=result.status.value,
                               duration=result.duration,
                               check_message=result.message)
            
            except Exception as e:
                self.logger.error(f"Health check error: {check.name}",
                                error=str(e),
                                error_type=type(e).__name__)
                
                results[check.name] = HealthCheckResult(
                    name=check.name,
                    status=HealthStatus.CRITICAL,
                    message=f"Health check failed: {str(e)}",
                    details={"error": str(e)}
                )
        
        total_duration = time.time() - start_time
        
        # Update cache
        with self._lock:
            self._last_check_time = datetime.utcnow()
            self._last_results.update(results)
        
        self.logger.info("Health checks completed",
                        total_duration=total_duration,
                        checks_run=len(results),
                        healthy_count=sum(1 for r in results.values() if r.status == HealthStatus.HEALTHY),
                        warning_count=sum(1 for r in results.values() if r.status == HealthStatus.WARNING),
                        critical_count=sum(1 for r in results.values() if r.status == HealthStatus.CRITICAL))
        
        return results
    
    def check_all(self) -> Dict[str, Any]:
        """Perform all health checks and return summary."""
        results = self.check_health()
        
        # Calculate overall status
        statuses = [result.status for result in results.values()]
        if HealthStatus.CRITICAL in statuses:
            overall_status = HealthStatus.CRITICAL
        elif HealthStatus.WARNING in statuses:
            overall_status = HealthStatus.WARNING
        else:
            overall_status = HealthStatus.HEALTHY
        
        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": overall_status.value,
            "checks": {name: result.to_dict() for name, result in results.items()},
            "summary": {
                "total_checks": len(results),
                "healthy": sum(1 for r in results.values() if r.status == HealthStatus.HEALTHY),
                "warning": sum(1 for r in results.values() if r.status == HealthStatus.WARNING),
                "critical": sum(1 for r in results.values() if r.status == HealthStatus.CRITICAL),
                "unknown": sum(1 for r in results.values() if r.status == HealthStatus.UNKNOWN)
            }
        }
        
        return summary
    
    def get_last_results(self) -> Dict[str, HealthCheckResult]:
        """Get the last health check results."""
        with self._lock:
            return self._last_results.copy()
    
    def export_health_report(self, file_path: Union[str, Path]) -> None:
        """Export health report to file."""
        report = self.check_all()
        
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        self.logger.info("Health report exported", 
                        file_path=str(file_path),
                        overall_status=report["overall_status"])


# Global health checker instance
_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """Get the global health checker instance."""
    global _health_checker
    
    if _health_checker is None:
        _health_checker = HealthChecker()
    
    return _health_checker


# Convenience functions
def check_health(check_names: List[str] = None) -> Dict[str, HealthCheckResult]:
    """Perform health checks."""
    return get_health_checker().check_health(check_names)


def check_all_health() -> Dict[str, Any]:
    """Perform all health checks and return summary."""
    return get_health_checker().check_all()
