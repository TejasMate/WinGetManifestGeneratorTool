"""
Multi-Source Package Processing Framework.

This package provides a unified interface for processing packages from multiple
sources including GitHub, GitLab, SourceForge, and others.
"""

from .base import (
    BasePackageSource, SourceType, ReleaseInfo, RepositoryInfo, PackageMetadata,
    IPackageSource, IURLMatcher, IPackageFilter, IPackageProcessor
)
from .registry import (
    SourceRegistry, SourceFactory, get_registry, get_factory,
    register_source, create_source, auto_detect_and_process
)
from .github import GitHubSource
from .gitlab import GitLabSource
from .sourceforge import SourceForgeSource

# Auto-register all available sources
def _register_default_sources():
    """Register all default source implementations."""
    register_source(SourceType.GITHUB, GitHubSource)
    register_source(SourceType.GITLAB, GitLabSource)
    register_source(SourceType.SOURCEFORGE, SourceForgeSource)

# Register sources on import
_register_default_sources()

__all__ = [
    # Base classes and interfaces
    'BasePackageSource', 'SourceType', 'ReleaseInfo', 'RepositoryInfo', 'PackageMetadata',
    'IPackageSource', 'IURLMatcher', 'IPackageFilter', 'IPackageProcessor',
    
    # Registry and factory
    'SourceRegistry', 'SourceFactory', 'get_registry', 'get_factory',
    'register_source', 'create_source', 'auto_detect_and_process',
    
    # Source implementations
    'GitHubSource', 'GitLabSource', 'SourceForgeSource',
]
