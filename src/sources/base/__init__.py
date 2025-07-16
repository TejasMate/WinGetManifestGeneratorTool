"""
Base classes and interfaces for package sources.

This module provides the foundational interfaces and abstract base classes
for implementing different package sources (GitHub, GitLab, SourceForge, etc.).
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol, Tuple, Set
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class SourceType(Enum):
    """Enumeration of supported package source types."""
    GITHUB = "github"
    GITLAB = "gitlab"
    SOURCEFORGE = "sourceforge"
    BITBUCKET = "bitbucket"
    CUSTOM = "custom"


@dataclass
class ReleaseInfo:
    """Standardized release information across all package sources."""
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
    """Standardized repository information across all package sources."""
    name: str
    full_name: str
    url: str
    clone_url: str
    description: Optional[str] = None
    homepage: Optional[str] = None
    language: Optional[str] = None
    topics: List[str] = None
    license: Optional[str] = None
    stars: int = 0
    forks: int = 0


@dataclass
class PackageMetadata:
    """Complete package metadata from a source."""
    identifier: str
    name: str
    source_type: SourceType
    repository: RepositoryInfo
    latest_release: Optional[ReleaseInfo] = None
    all_releases: List[ReleaseInfo] = None
    url_patterns: Set[str] = None
    installer_urls_count: int = 0
    

class IPackageSource(Protocol):
    """Interface for package source implementations."""
    
    @property
    def source_type(self) -> SourceType:
        """Get the source type."""
        ...
    
    def extract_package_info(self, url: str) -> Optional[PackageMetadata]:
        """Extract package information from a URL."""
        ...
    
    def get_latest_release(self, package_id: str) -> Optional[ReleaseInfo]:
        """Get the latest release for a package."""
        ...
    
    def get_all_releases(self, package_id: str) -> List[ReleaseInfo]:
        """Get all releases for a package."""
        ...
    
    def search_packages(self, query: str) -> List[PackageMetadata]:
        """Search for packages by query."""
        ...


class BasePackageSource(ABC):
    """Abstract base class for package source implementations."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the package source with configuration."""
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @property
    @abstractmethod
    def source_type(self) -> SourceType:
        """Get the source type."""
        pass
    
    @abstractmethod
    def is_supported_url(self, url: str) -> bool:
        """Check if the URL is supported by this source."""
        pass
    
    @abstractmethod
    def extract_package_info(self, url: str) -> Optional[PackageMetadata]:
        """Extract package information from a URL."""
        pass
    
    @abstractmethod
    def get_latest_release(self, package_id: str) -> Optional[ReleaseInfo]:
        """Get the latest release for a package."""
        pass
    
    def get_all_releases(self, package_id: str) -> List[ReleaseInfo]:
        """Get all releases for a package. Default implementation returns latest only."""
        latest = self.get_latest_release(package_id)
        return [latest] if latest else []
    
    def search_packages(self, query: str) -> List[PackageMetadata]:
        """Search for packages by query. Default implementation returns empty list."""
        return []
    
    def validate_config(self) -> bool:
        """Validate the source configuration."""
        return True


class IURLMatcher(Protocol):
    """Interface for URL matching and pattern extraction."""
    
    def extract_url_patterns(self, urls: List[str]) -> Set[str]:
        """Extract URL patterns from a list of URLs."""
        ...
    
    def filter_urls_by_patterns(self, urls: List[str], patterns: Set[str]) -> List[str]:
        """Filter URLs based on patterns."""
        ...
    
    def extract_extensions(self, urls: List[str]) -> Set[str]:
        """Extract file extensions from URLs."""
        ...


class IPackageFilter(Protocol):
    """Interface for package filtering logic."""
    
    def filter_packages(self, packages: List[PackageMetadata]) -> List[PackageMetadata]:
        """Filter packages based on criteria."""
        ...
    
    def should_include_package(self, package: PackageMetadata) -> bool:
        """Determine if a package should be included."""
        ...


class IPackageProcessor(Protocol):
    """Interface for package processors."""
    
    def process_package(self, package: PackageMetadata) -> Dict[str, Any]:
        """Process a single package."""
        ...
    
    def process_batch(self, packages: List[PackageMetadata]) -> List[Dict[str, Any]]:
        """Process multiple packages."""
        ...
