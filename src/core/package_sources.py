"""
Package Sources Framework for WinGet Manifest Generator Tool.

This module provides a flexible architecture for handling different package sources
like GitHub, GitLab, SourceForge, and potentially others in the future.

The framework uses the Strategy pattern and Factory pattern to enable:
- Easy addition of new package sources
- Consistent interface across all sources
- Source-specific optimization and configuration
- Unified package metadata handling
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Protocol
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import logging

# Configure logging
logger = logging.getLogger(__name__)


class PackageSourceType(Enum):
    """Enumeration of supported package source types."""
    GITHUB = "github"
    GITLAB = "gitlab"
    SOURCEFORGE = "sourceforge"
    BITBUCKET = "bitbucket"
    CUSTOM = "custom"


@dataclass
class ReleaseInfo:
    """Standard release information across all package sources."""
    version: str
    tag_name: str
    download_urls: List[str]
    release_date: Optional[str] = None
    release_notes: Optional[str] = None
    is_prerelease: bool = False
    is_draft: bool = False
    assets: Optional[List[Dict[str, Any]]] = None
    checksums: Optional[Dict[str, str]] = None


@dataclass
class RepositoryInfo:
    """Standard repository information across all package sources."""
    source_type: PackageSourceType
    username: str
    repository_name: str
    base_url: str
    api_url: Optional[str] = None
    clone_url: Optional[str] = None
    description: Optional[str] = None
    language: Optional[str] = None
    stars: Optional[int] = None
    forks: Optional[int] = None


@dataclass
class PackageMetadata:
    """Comprehensive package metadata from any source."""
    identifier: str
    name: str
    repository_info: RepositoryInfo
    latest_release: Optional[ReleaseInfo] = None
    all_releases: Optional[List[ReleaseInfo]] = None
    architectures: Optional[List[str]] = None
    file_extensions: Optional[List[str]] = None
    install_urls: Optional[List[str]] = None
    source_specific_data: Optional[Dict[str, Any]] = None


class IPackageSource(Protocol):
    """Interface that all package sources must implement."""
    
    @property
    def source_type(self) -> PackageSourceType:
        """Return the type of this package source."""
        ...
    
    def can_handle_url(self, url: str) -> bool:
        """Check if this source can handle the given URL."""
        ...
    
    def extract_repository_info(self, url: str) -> Optional[RepositoryInfo]:
        """Extract repository information from URL."""
        ...
    
    def get_latest_release(self, repo_info: RepositoryInfo) -> Optional[ReleaseInfo]:
        """Get the latest release information."""
        ...
    
    def get_all_releases(self, repo_info: RepositoryInfo) -> Optional[List[ReleaseInfo]]:
        """Get all releases for the repository."""
        ...
    
    def get_package_metadata(self, url: str) -> Optional[PackageMetadata]:
        """Get comprehensive package metadata."""
        ...


class BasePackageSource(ABC):
    """Abstract base class for all package sources."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the package source with configuration."""
        self.config = config or {}
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
    
    @property
    @abstractmethod
    def source_type(self) -> PackageSourceType:
        """Return the type of this package source."""
        pass
    
    @abstractmethod
    def can_handle_url(self, url: str) -> bool:
        """Check if this source can handle the given URL."""
        pass
    
    @abstractmethod
    def extract_repository_info(self, url: str) -> Optional[RepositoryInfo]:
        """Extract repository information from URL."""
        pass
    
    @abstractmethod
    def get_latest_release(self, repo_info: RepositoryInfo) -> Optional[ReleaseInfo]:
        """Get the latest release information."""
        pass
    
    @abstractmethod
    def get_all_releases(self, repo_info: RepositoryInfo) -> Optional[List[ReleaseInfo]]:
        """Get all releases for the repository."""
        pass
    
    def get_package_metadata(self, url: str) -> Optional[PackageMetadata]:
        """Get comprehensive package metadata. Default implementation."""
        try:
            repo_info = self.extract_repository_info(url)
            if not repo_info:
                return None
            
            latest_release = self.get_latest_release(repo_info)
            all_releases = self.get_all_releases(repo_info)
            
            # Extract architectures and extensions from releases
            architectures = set()
            file_extensions = set()
            install_urls = []
            
            if latest_release:
                install_urls.extend(latest_release.download_urls)
                for url in latest_release.download_urls:
                    # Extract file extension
                    path = Path(url)
                    if path.suffix:
                        file_extensions.add(path.suffix.lower().lstrip('.'))
                    
                    # Extract architecture hints from filename
                    filename = path.name.lower()
                    for arch in ['x64', 'x86', 'arm64', 'aarch64', 'arm']:
                        if arch in filename:
                            architectures.add(arch)
            
            return PackageMetadata(
                identifier=f"{repo_info.username}.{repo_info.repository_name}",
                name=repo_info.repository_name,
                repository_info=repo_info,
                latest_release=latest_release,
                all_releases=all_releases,
                architectures=list(architectures) if architectures else None,
                file_extensions=list(file_extensions) if file_extensions else None,
                install_urls=install_urls if install_urls else None
            )
            
        except Exception as e:
            self.logger.error(f"Error getting package metadata for {url}: {e}")
            return None
    
    def validate_repository_info(self, repo_info: RepositoryInfo) -> bool:
        """Validate repository information."""
        if not repo_info.username or not repo_info.repository_name:
            return False
        if not repo_info.base_url:
            return False
        return True
    
    def normalize_version(self, version: str) -> str:
        """Normalize version string for consistent comparison."""
        # Remove common prefixes
        version = version.lstrip('vV')
        # Handle URL encoding
        version = version.replace('%2B', '+')
        return version
    
    def filter_releases_by_criteria(self, releases: List[ReleaseInfo], 
                                  include_prereleases: bool = False,
                                  include_drafts: bool = False) -> List[ReleaseInfo]:
        """Filter releases based on criteria."""
        filtered = []
        for release in releases:
            if not include_prereleases and release.is_prerelease:
                continue
            if not include_drafts and release.is_draft:
                continue
            filtered.append(release)
        return filtered


class PackageSourceRegistry:
    """Registry for managing different package sources."""
    
    def __init__(self):
        """Initialize the package source registry."""
        self._sources: Dict[PackageSourceType, IPackageSource] = {}
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
    
    def register_source(self, source: IPackageSource) -> None:
        """Register a new package source."""
        self._sources[source.source_type] = source
        self.logger.info(f"Registered package source: {source.source_type.value}")
    
    def get_source(self, source_type: PackageSourceType) -> Optional[IPackageSource]:
        """Get a package source by type."""
        return self._sources.get(source_type)
    
    def get_source_for_url(self, url: str) -> Optional[IPackageSource]:
        """Find the appropriate source for a given URL."""
        for source in self._sources.values():
            if source.can_handle_url(url):
                return source
        return None
    
    def list_sources(self) -> List[PackageSourceType]:
        """List all registered source types."""
        return list(self._sources.keys())
    
    def is_supported_url(self, url: str) -> bool:
        """Check if any registered source can handle the URL."""
        return self.get_source_for_url(url) is not None


class PackageSourceFactory:
    """Factory for creating package source instances."""
    
    _source_classes: Dict[PackageSourceType, type] = {}
    
    @classmethod
    def register_source_class(cls, source_type: PackageSourceType, source_class: type) -> None:
        """Register a source class for a given type."""
        cls._source_classes[source_type] = source_class
    
    @classmethod
    def create_source(cls, source_type: PackageSourceType, 
                     config: Optional[Dict[str, Any]] = None) -> Optional[IPackageSource]:
        """Create a source instance of the specified type."""
        source_class = cls._source_classes.get(source_type)
        if not source_class:
            return None
        
        try:
            return source_class(config)
        except Exception as e:
            logger.error(f"Failed to create source {source_type.value}: {e}")
            return None
    
    @classmethod
    def get_available_source_types(cls) -> List[PackageSourceType]:
        """Get all available source types."""
        return list(cls._source_classes.keys())


# Global registry instance
package_source_registry = PackageSourceRegistry()


def get_package_source_registry() -> PackageSourceRegistry:
    """Get the global package source registry."""
    return package_source_registry
