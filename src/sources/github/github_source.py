"""
GitHub Package Source Implementation.

This module provides GitHub-specific implementation of the package source interface,
migrated from the legacy GitHub-specific modules.
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

# Import existing GitHub utilities
try:
    from ...utils.unified_utils import GitHubAPI, GitHubConfig
    from ...utils.token_manager import TokenManager
except ImportError:
    # Fallback imports
    pass

logger = logging.getLogger(__name__)


class GitHubURLMatcher(BaseURLMatcher):
    """GitHub-specific URL matcher."""
    
    def __init__(self):
        super().__init__()
        self.github_patterns = [
            r'github\.com/([^/]+)/([^/]+)',
            r'api\.github\.com/repos/([^/]+)/([^/]+)',
        ]
    
    def is_github_url(self, url: str) -> bool:
        """Check if URL is a GitHub URL."""
        if not url:
            return False
        
        for pattern in self.github_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        
        return False
    
    def extract_repo_info(self, url: str) -> Optional[tuple]:
        """Extract owner and repo name from GitHub URL."""
        for pattern in self.github_patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                return match.group(1), match.group(2)
        
        return None


class GitHubPackageFilter(BasePackageFilter):
    """GitHub-specific package filter."""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        
        # GitHub-specific exclusions
        self.default_exclusions = [
            'template', 'boilerplate', 'example', 'demo', 'test',
            'documentation', 'docs', 'tutorial', 'guide'
        ]
    
    def should_include_package(self, package: PackageMetadata) -> bool:
        """GitHub-specific inclusion logic."""
        if not super().should_include_package(package):
            return False
        
        # Skip repositories with low stars (configurable)
        min_stars = self.config.get('min_stars', 0)
        if package.repository and package.repository.stars < min_stars:
            return False
        
        # Skip archived repositories
        if self.config.get('exclude_archived', True):
            # This would require additional API data
            pass
        
        # Skip template repositories
        if self.config.get('exclude_templates', True):
            if package.repository and package.repository.name:
                name_lower = package.repository.name.lower()
                if any(excl in name_lower for excl in self.default_exclusions):
                    return False
        
        return True


class GitHubSource(BasePackageSource):
    """GitHub package source implementation."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.url_matcher = GitHubURLMatcher()
        self.filter = GitHubPackageFilter(config.get('filter', {}))
        
        # Initialize GitHub API if tokens are available
        self.github_api = None
        self.token_manager = None
        
        try:
            if 'github_tokens' in config:
                self.token_manager = TokenManager(config['github_tokens'])
                self.github_api = GitHubAPI(self.token_manager)
        except Exception as e:
            self.logger.warning(f"Failed to initialize GitHub API: {e}")
    
    @property
    def source_type(self) -> SourceType:
        """Get the source type."""
        return SourceType.GITHUB
    
    def is_supported_url(self, url: str) -> bool:
        """Check if the URL is a GitHub URL."""
        return self.url_matcher.is_github_url(url)
    
    def extract_package_info(self, url: str) -> Optional[PackageMetadata]:
        """Extract package information from a GitHub URL."""
        if not self.is_supported_url(url):
            return None
        
        repo_info = self.url_matcher.extract_repo_info(url)
        if not repo_info:
            return None
        
        owner, repo_name = repo_info
        
        try:
            # Create basic repository info
            repository = RepositoryInfo(
                name=repo_name,
                full_name=f"{owner}/{repo_name}",
                url=f"https://github.com/{owner}/{repo_name}",
                clone_url=f"https://github.com/{owner}/{repo_name}.git"
            )
            
            # Get additional info from API if available
            if self.github_api:
                repo_data = self._get_repo_data(owner, repo_name)
                if repo_data:
                    repository = self._enhance_repository_info(repository, repo_data)
            
            # Get latest release
            latest_release = self.get_latest_release(f"{owner}/{repo_name}")
            
            # Extract URL patterns if release has assets
            url_patterns = set()
            installer_urls_count = 0
            
            if latest_release and latest_release.download_urls:
                url_patterns = self.url_matcher.extract_url_patterns(latest_release.download_urls)
                installer_urls_count = len([url for url in latest_release.download_urls 
                                          if self.url_matcher.is_valid_installer_url(url)])
            
            # Create package metadata
            package = PackageMetadata(
                identifier=f"GitHub.{owner}.{repo_name}",
                name=repo_name,
                source_type=SourceType.GITHUB,
                repository=repository,
                latest_release=latest_release,
                url_patterns=url_patterns,
                installer_urls_count=installer_urls_count
            )
            
            return package
            
        except Exception as e:
            self.logger.error(f"Failed to extract package info for {owner}/{repo_name}: {e}")
            return None
    
    def get_latest_release(self, package_id: str) -> Optional[ReleaseInfo]:
        """Get the latest release for a GitHub repository."""
        if not self.github_api:
            return None
        
        try:
            # Extract owner/repo from package_id
            if package_id.startswith("GitHub."):
                parts = package_id.split(".")
                if len(parts) >= 3:
                    owner, repo = parts[1], parts[2]
                else:
                    return None
            else:
                # Assume format is owner/repo
                if "/" in package_id:
                    owner, repo = package_id.split("/", 1)
                else:
                    return None
            
            # Get latest release from API
            release_data = self.github_api.get_latest_release(owner, repo)
            if not release_data:
                return None
            
            # Convert to ReleaseInfo
            return self._convert_release_data(release_data)
            
        except Exception as e:
            self.logger.error(f"Failed to get latest release for {package_id}: {e}")
            return None
    
    def get_all_releases(self, package_id: str) -> List[ReleaseInfo]:
        """Get all releases for a GitHub repository."""
        if not self.github_api:
            latest = self.get_latest_release(package_id)
            return [latest] if latest else []
        
        try:
            # Extract owner/repo from package_id
            if package_id.startswith("GitHub."):
                parts = package_id.split(".")
                if len(parts) >= 3:
                    owner, repo = parts[1], parts[2]
                else:
                    return []
            else:
                if "/" in package_id:
                    owner, repo = package_id.split("/", 1)
                else:
                    return []
            
            # Get all releases from API
            releases_data = self.github_api.get_all_releases(owner, repo)
            if not releases_data:
                return []
            
            # Convert to ReleaseInfo list
            releases = []
            for release_data in releases_data:
                release_info = self._convert_release_data(release_data)
                if release_info:
                    releases.append(release_info)
            
            return releases
            
        except Exception as e:
            self.logger.error(f"Failed to get all releases for {package_id}: {e}")
            return []
    
    def search_packages(self, query: str) -> List[PackageMetadata]:
        """Search for GitHub packages."""
        if not self.github_api:
            return []
        
        try:
            # Use GitHub search API
            search_results = self.github_api.search_repositories(query)
            packages = []
            
            for repo_data in search_results:
                package = self._convert_repo_to_package(repo_data)
                if package and self.filter.should_include_package(package):
                    packages.append(package)
            
            return packages
            
        except Exception as e:
            self.logger.error(f"Failed to search packages with query '{query}': {e}")
            return []
    
    def validate_config(self) -> bool:
        """Validate GitHub source configuration."""
        # Check if tokens are provided
        if 'github_tokens' not in self.config:
            self.logger.warning("No GitHub tokens provided - API functionality will be limited")
            return True  # Still valid, just limited
        
        tokens = self.config['github_tokens']
        if not isinstance(tokens, list) or not tokens:
            self.logger.error("GitHub tokens must be a non-empty list")
            return False
        
        return True
    
    def _get_repo_data(self, owner: str, repo: str) -> Optional[Dict[str, Any]]:
        """Get repository data from GitHub API."""
        if not self.github_api:
            return None
        
        try:
            return self.github_api.get_repository(owner, repo)
        except Exception as e:
            self.logger.debug(f"Failed to get repo data for {owner}/{repo}: {e}")
            return None
    
    def _enhance_repository_info(self, repo_info: RepositoryInfo, repo_data: Dict[str, Any]) -> RepositoryInfo:
        """Enhance repository info with API data."""
        repo_info.description = repo_data.get('description')
        repo_info.homepage = repo_data.get('homepage')
        repo_info.language = repo_data.get('language')
        repo_info.stars = repo_data.get('stargazers_count', 0)
        repo_info.forks = repo_data.get('forks_count', 0)
        
        # Extract license info
        license_info = repo_data.get('license')
        if license_info:
            repo_info.license = license_info.get('name')
        
        # Extract topics
        repo_info.topics = repo_data.get('topics', [])
        
        return repo_info
    
    def _convert_release_data(self, release_data: Dict[str, Any]) -> Optional[ReleaseInfo]:
        """Convert GitHub API release data to ReleaseInfo."""
        try:
            # Extract download URLs from assets
            download_urls = []
            assets = release_data.get('assets', [])
            
            for asset in assets:
                if asset.get('browser_download_url'):
                    download_urls.append(asset['browser_download_url'])
            
            return ReleaseInfo(
                version=release_data.get('tag_name', ''),
                tag_name=release_data.get('tag_name', ''),
                download_urls=download_urls,
                release_date=release_data.get('published_at'),
                release_notes=release_data.get('body'),
                is_prerelease=release_data.get('prerelease', False),
                is_draft=release_data.get('draft', False),
                assets=assets
            )
            
        except Exception as e:
            self.logger.error(f"Failed to convert release data: {e}")
            return None
    
    def _convert_repo_to_package(self, repo_data: Dict[str, Any]) -> Optional[PackageMetadata]:
        """Convert GitHub API repository data to PackageMetadata."""
        try:
            full_name = repo_data.get('full_name', '')
            if not full_name or '/' not in full_name:
                return None
            
            owner, name = full_name.split('/', 1)
            
            repository = RepositoryInfo(
                name=name,
                full_name=full_name,
                url=repo_data.get('html_url', ''),
                clone_url=repo_data.get('clone_url', ''),
                description=repo_data.get('description'),
                homepage=repo_data.get('homepage'),
                language=repo_data.get('language'),
                stars=repo_data.get('stargazers_count', 0),
                forks=repo_data.get('forks_count', 0),
                topics=repo_data.get('topics', [])
            )
            
            # Extract license
            license_info = repo_data.get('license')
            if license_info:
                repository.license = license_info.get('name')
            
            # Get latest release
            latest_release = self.get_latest_release(full_name)
            
            # Calculate metrics
            url_patterns = set()
            installer_urls_count = 0
            
            if latest_release and latest_release.download_urls:
                url_patterns = self.url_matcher.extract_url_patterns(latest_release.download_urls)
                installer_urls_count = len([url for url in latest_release.download_urls 
                                          if self.url_matcher.is_valid_installer_url(url)])
            
            return PackageMetadata(
                identifier=f"GitHub.{owner}.{name}",
                name=name,
                source_type=SourceType.GITHUB,
                repository=repository,
                latest_release=latest_release,
                url_patterns=url_patterns,
                installer_urls_count=installer_urls_count
            )
            
        except Exception as e:
            self.logger.error(f"Failed to convert repo data to package: {e}")
            return None
