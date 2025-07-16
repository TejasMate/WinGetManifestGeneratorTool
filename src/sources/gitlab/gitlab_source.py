"""
GitLab Package Source Implementation.

This module provides GitLab-specific implementation of the package source interface.
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


class GitLabURLMatcher(BaseURLMatcher):
    """GitLab-specific URL matcher."""
    
    def __init__(self):
        super().__init__()
        self.gitlab_patterns = [
            r'gitlab\.com/([^/]+)/([^/]+)',
            r'gitlab\.([^/]+)/([^/]+)/([^/]+)',  # Self-hosted GitLab
        ]
    
    def is_gitlab_url(self, url: str) -> bool:
        """Check if URL is a GitLab URL."""
        if not url:
            return False
        
        for pattern in self.gitlab_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        
        return False
    
    def extract_repo_info(self, url: str) -> Optional[tuple]:
        """Extract namespace and project name from GitLab URL."""
        # Try main GitLab.com pattern first
        match = re.search(r'gitlab\.com/([^/]+)/([^/]+)', url, re.IGNORECASE)
        if match:
            return match.group(1), match.group(2), "gitlab.com"
        
        # Try self-hosted GitLab pattern
        match = re.search(r'gitlab\.([^/]+)/([^/]+)/([^/]+)', url, re.IGNORECASE)
        if match:
            return match.group(2), match.group(3), f"gitlab.{match.group(1)}"
        
        return None


class GitLabPackageFilter(BasePackageFilter):
    """GitLab-specific package filter."""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        
        # GitLab-specific exclusions
        self.default_exclusions = [
            'template', 'boilerplate', 'example', 'demo', 'test',
            'documentation', 'docs', 'tutorial', 'guide'
        ]
    
    def should_include_package(self, package: PackageMetadata) -> bool:
        """GitLab-specific inclusion logic."""
        if not super().should_include_package(package):
            return False
        
        # Skip repositories with low stars (if available)
        min_stars = self.config.get('min_stars', 0)
        if package.repository and package.repository.stars < min_stars:
            return False
        
        # Skip template repositories
        if self.config.get('exclude_templates', True):
            if package.repository and package.repository.name:
                name_lower = package.repository.name.lower()
                if any(excl in name_lower for excl in self.default_exclusions):
                    return False
        
        return True


class GitLabSource(BasePackageSource):
    """GitLab package source implementation."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.url_matcher = GitLabURLMatcher()
        self.filter = GitLabPackageFilter(config.get('filter', {}))
        
        # GitLab API configuration
        self.gitlab_token = config.get('gitlab_token')
        self.gitlab_instances = config.get('gitlab_instances', ['gitlab.com'])
    
    @property
    def source_type(self) -> SourceType:
        """Get the source type."""
        return SourceType.GITLAB
    
    def is_supported_url(self, url: str) -> bool:
        """Check if the URL is a GitLab URL."""
        return self.url_matcher.is_gitlab_url(url)
    
    def extract_package_info(self, url: str) -> Optional[PackageMetadata]:
        """Extract package information from a GitLab URL."""
        if not self.is_supported_url(url):
            return None
        
        repo_info = self.url_matcher.extract_repo_info(url)
        if not repo_info:
            return None
        
        namespace, project_name, instance = repo_info
        
        try:
            # Create basic repository info
            repository = RepositoryInfo(
                name=project_name,
                full_name=f"{namespace}/{project_name}",
                url=f"https://{instance}/{namespace}/{project_name}",
                clone_url=f"https://{instance}/{namespace}/{project_name}.git"
            )
            
            # Get additional info from API if available
            if self.gitlab_token:
                repo_data = self._get_repo_data(namespace, project_name, instance)
                if repo_data:
                    repository = self._enhance_repository_info(repository, repo_data)
            
            # Get latest release
            latest_release = self.get_latest_release(f"{namespace}/{project_name}")
            
            # Extract URL patterns if release has assets
            url_patterns = set()
            installer_urls_count = 0
            
            if latest_release and latest_release.download_urls:
                url_patterns = self.url_matcher.extract_url_patterns(latest_release.download_urls)
                installer_urls_count = len([url for url in latest_release.download_urls 
                                          if self.url_matcher.is_valid_installer_url(url)])
            
            # Create package metadata
            package = PackageMetadata(
                identifier=f"GitLab.{namespace}.{project_name}",
                name=project_name,
                source_type=SourceType.GITLAB,
                repository=repository,
                latest_release=latest_release,
                url_patterns=url_patterns,
                installer_urls_count=installer_urls_count
            )
            
            return package
            
        except Exception as e:
            self.logger.error(f"Failed to extract package info for {namespace}/{project_name}: {e}")
            return None
    
    def get_latest_release(self, package_id: str) -> Optional[ReleaseInfo]:
        """Get the latest release for a GitLab project."""
        # GitLab releases implementation would go here
        # For now, return None as we'd need GitLab API implementation
        self.logger.debug(f"GitLab release fetching not yet implemented for {package_id}")
        return None
    
    def get_all_releases(self, package_id: str) -> List[ReleaseInfo]:
        """Get all releases for a GitLab project."""
        latest = self.get_latest_release(package_id)
        return [latest] if latest else []
    
    def search_packages(self, query: str) -> List[PackageMetadata]:
        """Search for GitLab packages."""
        # GitLab search implementation would go here
        self.logger.debug(f"GitLab search not yet implemented for query: {query}")
        return []
    
    def validate_config(self) -> bool:
        """Validate GitLab source configuration."""
        # Check if instances are valid
        instances = self.config.get('gitlab_instances', ['gitlab.com'])
        if not isinstance(instances, list) or not instances:
            self.logger.error("GitLab instances must be a non-empty list")
            return False
        
        if self.gitlab_token:
            # Could validate token format here
            pass
        else:
            self.logger.warning("No GitLab token provided - API functionality will be limited")
        
        return True
    
    def _get_repo_data(self, namespace: str, project: str, instance: str) -> Optional[Dict[str, Any]]:
        """Get project data from GitLab API."""
        # GitLab API implementation would go here
        return None
    
    def _enhance_repository_info(self, repo_info: RepositoryInfo, repo_data: Dict[str, Any]) -> RepositoryInfo:
        """Enhance repository info with API data."""
        # Enhance with GitLab-specific data
        return repo_info
