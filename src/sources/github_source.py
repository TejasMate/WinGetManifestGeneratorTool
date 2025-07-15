"""
GitHub Package Source Implementation.

This module provides GitHub-specific implementation of the package source interface,
handling GitHub repositories, releases, and API interactions.
"""

import re
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

# Handle imports for different execution contexts
try:
    from ..core.package_sources import (
        BasePackageSource, 
        PackageSourceType, 
        ReleaseInfo, 
        RepositoryInfo,
        PackageMetadata
    )
except ImportError:
    # Fallback for direct execution or when run from different paths
    import sys
    from pathlib import Path
    current_dir = Path(__file__).parent
    parent_dir = current_dir.parent
    sys.path.insert(0, str(parent_dir))
    
    from core.package_sources import (
        BasePackageSource, 
        PackageSourceType, 
        ReleaseInfo, 
        RepositoryInfo,
        PackageMetadata
    )

try:
    from ..utils.unified_utils import GitHubAPI, GitHubConfig
    from ..utils.token_manager import TokenManager
    from ..config import get_config
except ImportError:
    # Fallback for direct script execution
    import sys
    from pathlib import Path
    current_dir = Path(__file__).parent
    parent_dir = current_dir.parent
    root_dir = parent_dir.parent
    sys.path.insert(0, str(root_dir))
    
    from src.utils.unified_utils import GitHubAPI, GitHubConfig
    from src.utils.token_manager import TokenManager
    from src.config import get_config


logger = logging.getLogger(__name__)


class GitHubPackageSource(BasePackageSource):
    """GitHub implementation of the package source interface."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize GitHub package source."""
        super().__init__(config)
        
        # Initialize GitHub API
        self._init_github_api()
    
    def _init_github_api(self) -> None:
        """Initialize GitHub API with configuration."""
        try:
            # Get configuration
            app_config = get_config() if hasattr(self, '_use_global_config') else {}
            
            # Get GitHub token
            token_manager = TokenManager(app_config)
            token = token_manager.get_available_token()
            
            if not token:
                raise ValueError("No GitHub token available")
            
            # Create GitHub configuration
            github_config = GitHubConfig.from_config(app_config, token) if app_config else GitHubConfig(token=token)
            
            # Initialize GitHub API
            self.github_api = GitHubAPI(github_config)
            
            self.logger.info("GitHub API initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize GitHub API: {e}")
            raise
    
    @property
    def source_type(self) -> PackageSourceType:
        """Return GitHub as the source type."""
        return PackageSourceType.GITHUB
    
    def can_handle_url(self, url: str) -> bool:
        """Check if this is a GitHub URL."""
        if not url:
            return False
        
        # Check for github.com domain
        if "github.com" in url.lower():
            return True
        
        # Check for GitHub Enterprise patterns (if needed in future)
        # if self._is_github_enterprise_url(url):
        #     return True
        
        return False
    
    def extract_repository_info(self, url: str) -> Optional[RepositoryInfo]:
        """Extract GitHub repository information from URL."""
        if not self.can_handle_url(url):
            return None
        
        try:
            # Parse GitHub repository from URL
            # Examples:
            # https://github.com/microsoft/PowerToys
            # https://github.com/microsoft/PowerToys/releases
            # https://github.com/microsoft/PowerToys/releases/download/v0.70.1/PowerToys-v0.70.1-x64.exe
            
            pattern = r"github\.com/([^/]+)/([^/]+)"
            match = re.search(pattern, url)
            
            if not match:
                return None
            
            username = match.group(1)
            repo_name = match.group(2)
            
            # Clean repository name (remove .git suffix if present)
            if repo_name.endswith('.git'):
                repo_name = repo_name[:-4]
            
            return RepositoryInfo(
                source_type=PackageSourceType.GITHUB,
                username=username,
                repository_name=repo_name,
                base_url=f"https://github.com/{username}/{repo_name}",
                api_url=f"https://api.github.com/repos/{username}/{repo_name}",
                clone_url=f"https://github.com/{username}/{repo_name}.git"
            )
            
        except Exception as e:
            self.logger.error(f"Error extracting GitHub repository info from {url}: {e}")
            return None
    
    def get_latest_release(self, repo_info: RepositoryInfo) -> Optional[ReleaseInfo]:
        """Get the latest release from GitHub."""
        if not self.validate_repository_info(repo_info):
            return None
        
        try:
            # Use existing GitHub API
            release_data = self.github_api.get_latest_release(
                repo_info.username, 
                repo_info.repository_name
            )
            
            if not release_data:
                return None
            
            # Convert to our standard format
            return self._convert_github_release_to_standard(release_data)
            
        except Exception as e:
            self.logger.error(f"Error getting latest release for {repo_info.username}/{repo_info.repository_name}: {e}")
            return None
    
    def get_all_releases(self, repo_info: RepositoryInfo) -> Optional[List[ReleaseInfo]]:
        """Get all releases from GitHub."""
        if not self.validate_repository_info(repo_info):
            return None
        
        try:
            # Use existing GitHub API
            release_tags = self.github_api.get_all_releases(
                repo_info.username,
                repo_info.repository_name
            )
            
            if not release_tags:
                return None
            
            # For now, return simplified release info
            # In the future, we could make individual API calls to get full release data
            releases = []
            for tag in release_tags:
                releases.append(ReleaseInfo(
                    version=self.normalize_version(tag),
                    tag_name=tag,
                    download_urls=[]  # Would need additional API call to get assets
                ))
            
            return releases
            
        except Exception as e:
            self.logger.error(f"Error getting all releases for {repo_info.username}/{repo_info.repository_name}: {e}")
            return None
    
    def get_package_metadata(self, url: str) -> Optional[PackageMetadata]:
        """Get comprehensive GitHub package metadata."""
        try:
            repo_info = self.extract_repository_info(url)
            if not repo_info:
                return None
            
            # Get releases
            latest_release = self.get_latest_release(repo_info)
            all_releases = self.get_all_releases(repo_info)
            
            # Extract metadata specific to GitHub
            source_specific_data = {
                'api_rate_limit_remaining': getattr(self.github_api, 'rate_limit_remaining', None),
                'repository_url': repo_info.base_url,
                'api_url': repo_info.api_url
            }
            
            # Create base metadata
            metadata = super().get_package_metadata(url)
            if metadata:
                metadata.source_specific_data = source_specific_data
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Error getting GitHub package metadata for {url}: {e}")
            return None
    
    def _convert_github_release_to_standard(self, github_release: Dict[str, Any]) -> ReleaseInfo:
        """Convert GitHub API release data to our standard format."""
        tag_name = github_release.get('tag_name', '')
        
        return ReleaseInfo(
            version=self.normalize_version(tag_name),
            tag_name=tag_name,
            download_urls=github_release.get('asset_urls', []),
            release_date=github_release.get('published_at'),
            release_notes=github_release.get('body'),
            is_prerelease=github_release.get('prerelease', False),
            is_draft=github_release.get('draft', False),
            assets=github_release.get('assets', [])
        )
    
    def get_filtered_release_urls(self, repo_info: RepositoryInfo, 
                                 allowed_extensions: List[str]) -> Optional[List[str]]:
        """Get release URLs filtered by allowed file extensions."""
        latest_release = self.get_latest_release(repo_info)
        if not latest_release:
            return None
        
        filtered_urls = []
        for url in latest_release.download_urls:
            for ext in allowed_extensions:
                if url.lower().endswith(f'.{ext.lower()}'):
                    filtered_urls.append(url)
                    break
        
        return filtered_urls if filtered_urls else None
    
    def supports_architecture_filtering(self) -> bool:
        """GitHub supports architecture filtering through filename analysis."""
        return True
    
    def get_architecture_specific_urls(self, repo_info: RepositoryInfo, 
                                     architecture: str) -> Optional[List[str]]:
        """Get URLs specific to an architecture."""
        latest_release = self.get_latest_release(repo_info)
        if not latest_release:
            return None
        
        arch_patterns = {
            'x64': ['x64', 'amd64', 'x86_64'],
            'x86': ['x86', 'i386', 'win32'],
            'arm64': ['arm64', 'aarch64'],
            'arm': ['arm', 'armv7']
        }
        
        patterns = arch_patterns.get(architecture.lower(), [architecture.lower()])
        
        filtered_urls = []
        for url in latest_release.download_urls:
            url_lower = url.lower()
            for pattern in patterns:
                if pattern in url_lower:
                    filtered_urls.append(url)
                    break
        
        return filtered_urls if filtered_urls else None


# Register the GitHub source class with the factory
try:
    from ..core.package_sources import PackageSourceFactory
    PackageSourceFactory.register_source_class(PackageSourceType.GITHUB, GitHubPackageSource)
except ImportError:
    # Will be registered when properly imported through the package
    pass
