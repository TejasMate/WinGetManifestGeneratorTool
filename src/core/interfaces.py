"""Interface definitions for WinGet Manifest Generator Tool components."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol
from pathlib import Path


class IPackageProcessor(Protocol):
    """Interface for package processors."""
    
    def process_package(self, package_info: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single package."""
        ...
    
    def process_batch(self, packages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process multiple packages."""
        ...


class IManifestGenerator(Protocol):
    """Interface for manifest generators."""
    
    def generate_manifest(self, package_info: Dict[str, Any]) -> str:
        """Generate manifest content for a package."""
        ...
    
    def validate_manifest(self, manifest_content: str) -> bool:
        """Validate manifest content."""
        ...
    
    def save_manifest(self, manifest_content: str, output_path: Path) -> bool:
        """Save manifest to file."""
        ...


class IConfigProvider(Protocol):
    """Interface for configuration providers."""
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        ...
    
    def set_config(self, key: str, value: Any) -> None:
        """Set configuration value."""
        ...
    
    def load_config(self, config_path: Path) -> Dict[str, Any]:
        """Load configuration from file."""
        ...
    
    def save_config(self, config_path: Path) -> bool:
        """Save current configuration to file."""
        ...


class IGitHubIntegration(Protocol):
    """Interface for GitHub integration."""
    
    def get_repository_info(self, repo_url: str) -> Dict[str, Any]:
        """Get repository information."""
        ...
    
    def get_latest_release(self, repo_url: str) -> Optional[Dict[str, Any]]:
        """Get latest release information."""
        ...
    
    def create_pull_request(self, title: str, body: str, branch: str) -> str:
        """Create a pull request."""
        ...


class IMonitoringProvider(Protocol):
    """Interface for monitoring and observability."""
    
    def log_event(self, event: str, data: Dict[str, Any]) -> None:
        """Log an event."""
        ...
    
    def record_metric(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a metric."""
        ...
    
    def start_span(self, operation_name: str) -> Any:
        """Start a new span for tracing."""
        ...
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        ...
