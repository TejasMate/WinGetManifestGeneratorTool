"""
Package Sources Module.

This module provides a unified interface for handling different package sources
like GitHub, GitLab, SourceForge, and others.

Usage:
    from src.sources import get_package_source_for_url, PackageSourceManager
    
    # Get appropriate source for a URL
    source = get_package_source_for_url("https://github.com/user/repo")
    
    # Get package metadata
    metadata = source.get_package_metadata("https://github.com/user/repo")
    
    # Use the manager for bulk operations
    manager = PackageSourceManager()
    results = manager.process_urls(["https://github.com/user/repo1", 
                                   "https://gitlab.com/user/repo2"])
"""

import logging
from typing import Any, Dict, List, Optional

from .github_source import GitHubPackageSource
from .gitlab_source import GitLabPackageSource
from .sourceforge_source import SourceForgePackageSource

from ..core.package_sources import (
    PackageSourceType,
    PackageSourceFactory,
    PackageSourceRegistry,
    get_package_source_registry,
    IPackageSource,
    PackageMetadata,
    RepositoryInfo,
    ReleaseInfo
)

logger = logging.getLogger(__name__)


class PackageSourceManager:
    """Manager class for handling multiple package sources."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the package source manager."""
        self.config = config or {}
        self.registry = get_package_source_registry()
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        
        # Initialize and register default sources
        self._initialize_default_sources()
    
    def _initialize_default_sources(self) -> None:
        """Initialize and register default package sources."""
        try:
            # Register GitHub source
            github_config = self.config.get('github', {})
            github_source = GitHubPackageSource(github_config)
            self.registry.register_source(github_source)
            
            # Register GitLab source
            gitlab_config = self.config.get('gitlab', {})
            gitlab_source = GitLabPackageSource(gitlab_config)
            self.registry.register_source(gitlab_source)
            
            # Register SourceForge source
            sourceforge_config = self.config.get('sourceforge', {})
            sourceforge_source = SourceForgePackageSource(sourceforge_config)
            self.registry.register_source(sourceforge_source)
            
            self.logger.info(f"Initialized {len(self.registry.list_sources())} package sources")
            
        except Exception as e:
            self.logger.error(f"Error initializing package sources: {e}")
            raise
    
    def get_source_for_url(self, url: str) -> Optional[IPackageSource]:
        """Get the appropriate package source for a URL."""
        return self.registry.get_source_for_url(url)
    
    def is_supported_url(self, url: str) -> bool:
        """Check if the URL is supported by any registered source."""
        return self.registry.is_supported_url(url)
    
    def get_package_metadata(self, url: str) -> Optional[PackageMetadata]:
        """Get package metadata for a URL."""
        source = self.get_source_for_url(url)
        if not source:
            self.logger.warning(f"No source found for URL: {url}")
            return None
        
        return source.get_package_metadata(url)
    
    def process_urls(self, urls: List[str]) -> Dict[str, Optional[PackageMetadata]]:
        """Process multiple URLs and return metadata for each."""
        results = {}
        
        for url in urls:
            try:
                metadata = self.get_package_metadata(url)
                results[url] = metadata
                
                if metadata:
                    self.logger.info(f"Processed {url} -> {metadata.identifier}")
                else:
                    self.logger.warning(f"No metadata found for {url}")
                    
            except Exception as e:
                self.logger.error(f"Error processing {url}: {e}")
                results[url] = None
        
        return results
    
    def get_supported_source_types(self) -> List[PackageSourceType]:
        """Get list of supported source types."""
        return self.registry.list_sources()
    
    def get_source_by_type(self, source_type: PackageSourceType) -> Optional[IPackageSource]:
        """Get a source by its type."""
        return self.registry.get_source(source_type)


# Global manager instance
_global_manager: Optional[PackageSourceManager] = None


def get_package_source_manager(config: Optional[Dict[str, Any]] = None) -> PackageSourceManager:
    """Get the global package source manager instance."""
    global _global_manager
    
    if _global_manager is None:
        _global_manager = PackageSourceManager(config)
    
    return _global_manager


def get_package_source_for_url(url: str) -> Optional[IPackageSource]:
    """Convenience function to get a package source for a URL."""
    manager = get_package_source_manager()
    return manager.get_source_for_url(url)


def is_supported_package_url(url: str) -> bool:
    """Convenience function to check if a URL is supported."""
    manager = get_package_source_manager()
    return manager.is_supported_url(url)


def get_package_metadata_for_url(url: str) -> Optional[PackageMetadata]:
    """Convenience function to get package metadata for a URL."""
    manager = get_package_source_manager()
    return manager.get_package_metadata(url)


# Export all important classes and functions
__all__ = [
    # Core classes
    'PackageSourceManager',
    'GitHubPackageSource',
    'GitLabPackageSource', 
    'SourceForgePackageSource',
    
    # Data classes
    'PackageMetadata',
    'RepositoryInfo', 
    'ReleaseInfo',
    'PackageSourceType',
    
    # Convenience functions
    'get_package_source_manager',
    'get_package_source_for_url',
    'is_supported_package_url',
    'get_package_metadata_for_url',
    
    # Registry and factory
    'PackageSourceFactory',
    'PackageSourceRegistry',
    'get_package_source_registry'
]
