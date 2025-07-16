"""
SourceForge Package Source Implementation.

This module provides SourceForge-specific implementation of the package source interface.
"""

import re
import logging
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse

try:
    from ..base import BasePackageSource, SourceType, ReleaseInfo, RepositoryInfo, PackageMetadata
    from ..base.url_matcher import BaseURLMatcher
    from ..base.filter_base import BasePackageFilter
except ImportError:
    # Fallback for direct execution
    import sys
    from pathlib import Path
    current_dir = Path(__file__).parent
    parent_dir = current_dir.parent
    sys.path.insert(0, str(parent_dir))
    
    from base import BasePackageSource, SourceType, ReleaseInfo, RepositoryInfo, PackageMetadata
    from base.url_matcher import BaseURLMatcher
    from base.filter_base import BasePackageFilter

logger = logging.getLogger(__name__)


class SourceForgeURLMatcher(BaseURLMatcher):
    """SourceForge-specific URL matcher."""
    
    def __init__(self):
        super().__init__()
        self.sourceforge_patterns = [
            r'sourceforge\.net/projects/([^/]+)',
            r'downloads\.sourceforge\.net/([^/]+)',
            r'([^.]+)\.sourceforge\.net',
        ]
    
    def is_sourceforge_url(self, url: str) -> bool:
        """Check if URL is a SourceForge URL."""
        if not url:
            return False
        
        for pattern in self.sourceforge_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        
        return False
    
    def extract_project_info(self, url: str) -> Optional[str]:
        """Extract project name from SourceForge URL."""
        # Try projects pattern
        match = re.search(r'sourceforge\.net/projects/([^/]+)', url, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Try downloads pattern
        match = re.search(r'downloads\.sourceforge\.net/([^/]+)', url, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Try subdomain pattern
        match = re.search(r'([^.]+)\.sourceforge\.net', url, re.IGNORECASE)
        if match:
            return match.group(1)
        
        return None


class SourceForgePackageFilter(BasePackageFilter):
    """SourceForge-specific package filter."""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        
        # SourceForge-specific exclusions
        self.default_exclusions = [
            'template', 'boilerplate', 'example', 'demo', 'test',
            'documentation', 'docs', 'tutorial', 'guide', 'abandoned'
        ]
    
    def should_include_package(self, package: PackageMetadata) -> bool:
        """SourceForge-specific inclusion logic."""
        if not super().should_include_package(package):
            return False
        
        # SourceForge projects often have different quality metrics
        # We might want to check download counts, activity, etc.
        
        return True


class SourceForgeSource(BasePackageSource):
    """SourceForge package source implementation."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.url_matcher = SourceForgeURLMatcher()
        self.filter = SourceForgePackageFilter(config.get('filter', {}))
    
    @property
    def source_type(self) -> SourceType:
        """Get the source type."""
        return SourceType.SOURCEFORGE
    
    def is_supported_url(self, url: str) -> bool:
        """Check if the URL is a SourceForge URL."""
        return self.url_matcher.is_sourceforge_url(url)
    
    def extract_package_info(self, url: str) -> Optional[PackageMetadata]:
        """Extract package information from a SourceForge URL."""
        if not self.is_supported_url(url):
            return None
        
        project_name = self.url_matcher.extract_project_info(url)
        if not project_name:
            return None
        
        try:
            # Create basic repository info
            repository = RepositoryInfo(
                name=project_name,
                full_name=project_name,
                url=f"https://sourceforge.net/projects/{project_name}/",
                clone_url=f"https://sourceforge.net/p/{project_name}/code/"
            )
            
            # Get additional info if available
            repo_data = self._get_project_data(project_name)
            if repo_data:
                repository = self._enhance_repository_info(repository, repo_data)
            
            # Get latest release
            latest_release = self.get_latest_release(project_name)
            
            # Extract URL patterns if release has assets
            url_patterns = set()
            installer_urls_count = 0
            
            if latest_release and latest_release.download_urls:
                url_patterns = self.url_matcher.extract_url_patterns(latest_release.download_urls)
                installer_urls_count = len([url for url in latest_release.download_urls 
                                          if self.url_matcher.is_valid_installer_url(url)])
            
            # Create package metadata
            package = PackageMetadata(
                identifier=f"SourceForge.{project_name}",
                name=project_name,
                source_type=SourceType.SOURCEFORGE,
                repository=repository,
                latest_release=latest_release,
                url_patterns=url_patterns,
                installer_urls_count=installer_urls_count
            )
            
            return package
            
        except Exception as e:
            self.logger.error(f"Failed to extract package info for {project_name}: {e}")
            return None
    
    def get_latest_release(self, package_id: str) -> Optional[ReleaseInfo]:
        """Get the latest release for a SourceForge project."""
        # SourceForge release fetching would require:
        # 1. RSS feed parsing
        # 2. API calls to SourceForge
        # 3. Web scraping of project pages
        # For now, return None
        self.logger.debug(f"SourceForge release fetching not yet implemented for {package_id}")
        return None
    
    def get_all_releases(self, package_id: str) -> List[ReleaseInfo]:
        """Get all releases for a SourceForge project."""
        latest = self.get_latest_release(package_id)
        return [latest] if latest else []
    
    def search_packages(self, query: str) -> List[PackageMetadata]:
        """Search for SourceForge packages."""
        # SourceForge search implementation would go here
        self.logger.debug(f"SourceForge search not yet implemented for query: {query}")
        return []
    
    def validate_config(self) -> bool:
        """Validate SourceForge source configuration."""
        # SourceForge typically doesn't require authentication for basic operations
        return True
    
    def _get_project_data(self, project_name: str) -> Optional[Dict[str, Any]]:
        """Get project data from SourceForge."""
        # Could implement SourceForge API calls or web scraping here
        return None
    
    def _enhance_repository_info(self, repo_info: RepositoryInfo, project_data: Dict[str, Any]) -> RepositoryInfo:
        """Enhance repository info with SourceForge project data."""
        # Enhance with SourceForge-specific data
        return repo_info
