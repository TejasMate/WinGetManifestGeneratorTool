"""
GitHub Source Implementation - Consolidated

This file consolidates all GitHub-related functionality into a single module
for processing GitHub repositories, releases, and package information.
"""

import sys
import os
import logging
import asyncio
import aiohttp
import time
import re
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse
import pandas as pd

# Import core dependencies
# Add parent directory to path for imports  
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

try:
    from utils.token_manager import TokenManager
    from utils.unified_utils import GitHubAPI, GitHubConfig
    from config import get_config_manager, get_config
    print("Successfully imported all dependencies")
except ImportError as e:
    print(f"Warning: Could not import dependencies: {e}")
    # Create dummy classes to avoid import errors
    class TokenManager:
        def __init__(self, config): pass
        def get_available_token(self): return None
    
    class GitHubConfig:
        def __init__(self, **kwargs): pass
    
    class GitHubAPI:
        def __init__(self, config): pass
        def get_latest_release(self, owner, repo): return None
    
    def get_config(): return {}
    def get_config_manager(): return None

logger = logging.getLogger(__name__)


class WinGetManifestExtractor:
    """Extract installer URLs from all versions of a package in WinGet repository."""
    
    def __init__(self, winget_repo_path: str = "winget-pkgs"):
        self.winget_repo_path = Path(winget_repo_path)
        self.manifests_dir = self.winget_repo_path / "manifests"
        
    def get_package_directory(self, package_identifier: str) -> Optional[Path]:
        """Get the directory path for a package in WinGet repository."""
        try:
            # Parse package identifier (e.g., "Microsoft.VisualStudioCode")
            parts = package_identifier.split('.')
            if not parts:
                return None
                
            # Get first character for directory structure
            first_char = parts[0][0].lower()
            
            # Construct path: manifests/m/Microsoft/VisualStudioCode/
            package_path = self.manifests_dir / first_char / parts[0]
            if len(parts) > 1:
                for part in parts[1:]:
                    package_path = package_path / part
                    
            return package_path if package_path.exists() else None
        except Exception as e:
            logger.debug(f"Error getting package directory for {package_identifier}: {e}")
            return None
    
    def extract_installer_urls_from_manifest(self, manifest_path: Path) -> List[str]:
        """Extract installer URLs from a single manifest file."""
        try:
            # Skip very large files that might cause issues
            file_size = manifest_path.stat().st_size
            if file_size > 1024 * 1024:  # Skip files larger than 1MB
                logger.debug(f"Skipping large manifest file: {manifest_path} ({file_size} bytes)")
                return []
            
            with open(manifest_path, 'r', encoding='utf-8') as f:
                # Read only first 50KB to avoid huge files
                content = f.read(50000)
                if len(content) == 50000:  # File was truncated
                    logger.debug(f"Truncated large manifest file: {manifest_path}")
                
                manifest_data = yaml.safe_load(content)
                
            urls = []
            if isinstance(manifest_data, dict):
                # Look for Installers section
                installers = manifest_data.get('Installers', [])
                if isinstance(installers, list):
                    for installer in installers:
                        if isinstance(installer, dict):
                            url = installer.get('InstallerUrl')
                            if url and isinstance(url, str):
                                urls.append(url)
                                
                # Also check for single InstallerUrl (older format)
                single_url = manifest_data.get('InstallerUrl')
                if single_url and isinstance(single_url, str):
                    urls.append(single_url)
                    
            return urls
        except (yaml.YAMLError, UnicodeDecodeError, FileNotFoundError, OSError) as e:
            logger.debug(f"YAML/encoding/file error in {manifest_path}: {e}")
            return []
        except Exception as e:
            logger.debug(f"Error extracting URLs from {manifest_path}: {e}")
            return []
    
    def get_all_installer_urls_for_package(self, package_identifier: str) -> Dict[str, List[str]]:
        """Get all installer URLs from all versions of a package."""
        try:
            package_dir = self.get_package_directory(package_identifier)
            if not package_dir:
                return {}
                
            all_urls = {}
            
            # Look for version directories
            for version_dir in package_dir.iterdir():
                if version_dir.is_dir():
                    version = version_dir.name
                    version_urls = []
                    
                    # Look for installer manifests in version directory
                    for manifest_file in version_dir.glob("*.installer.yaml"):
                        urls = self.extract_installer_urls_from_manifest(manifest_file)
                        version_urls.extend(urls)
                    
                    # Also check for single manifest files (older format)
                    for manifest_file in version_dir.glob("*.yaml"):
                        if not manifest_file.name.endswith('.installer.yaml'):
                            urls = self.extract_installer_urls_from_manifest(manifest_file)
                            version_urls.extend(urls)
                    
                    if version_urls:
                        all_urls[version] = list(set(version_urls))  # Remove duplicates
                        
            return all_urls
        except Exception as e:
            logger.debug(f"Error getting all URLs for {package_identifier}: {e}")
            return {}


class URLComparator:
    """Compare URLs to find similarities even with different versioning."""
    
    @staticmethod
    def normalize_url_for_comparison(url: str) -> str:
        """Normalize URL for comparison by removing version-specific parts."""
        try:
            # Remove common version patterns
            # Example: https://github.com/user/repo/releases/download/v1.2.3/file-1.2.3.exe
            # Becomes: https://github.com/user/repo/releases/download/file.exe
            
            # Parse URL
            parsed = urlparse(url)
            path = parsed.path
            
            # Remove version patterns from path
            # Pattern 1: /v1.2.3/ or /1.2.3/
            path = re.sub(r'/v?\d+\.\d+[\.\d]*/', '/VERSION/', path)
            
            # Pattern 2: -v1.2.3 or -1.2.3 in filename
            path = re.sub(r'-v?\d+\.\d+[\.\d]*(?=[\.-])', '-VERSION', path)
            
            # Pattern 3: _v1.2.3 or _1.2.3 in filename  
            path = re.sub(r'_v?\d+\.\d+[\.\d]*(?=[\._])', '_VERSION', path)
            
            # Reconstruct URL
            normalized = f"{parsed.scheme}://{parsed.netloc}{path}"
            return normalized
        except Exception:
            return url
    
    @staticmethod
    def compare_urls(github_urls: List[str], winget_urls: List[str]) -> Dict[str, any]:
        """Compare GitHub URLs with WinGet URLs to find matches."""
        try:
            matches = {
                'exact_matches': [],
                'normalized_matches': [],
                'filename_matches': [],
                'github_urls_count': len(github_urls),
                'winget_urls_count': len(winget_urls),
                'has_any_match': False
            }
            
            if not github_urls or not winget_urls:
                return matches
            
            # Check for exact matches
            for gh_url in github_urls:
                if gh_url in winget_urls:
                    matches['exact_matches'].append(gh_url)
            
            # Check for normalized matches
            github_normalized = [(url, URLComparator.normalize_url_for_comparison(url)) for url in github_urls]
            winget_normalized = [(url, URLComparator.normalize_url_for_comparison(url)) for url in winget_urls]
            
            for gh_url, gh_norm in github_normalized:
                for wg_url, wg_norm in winget_normalized:
                    if gh_norm == wg_norm and gh_url not in matches['exact_matches']:
                        matches['normalized_matches'].append({'github': gh_url, 'winget': wg_url})
            
            # Set overall match flag
            matches['has_any_match'] = bool(
                matches['exact_matches'] or 
                matches['normalized_matches']
            )
            
            return matches
        except Exception as e:
            logger.debug(f"Error comparing URLs: {e}")
            return {
                'exact_matches': [],
                'normalized_matches': [],
                'filename_matches': [],
                'github_urls_count': len(github_urls),
                'winget_urls_count': len(winget_urls),
                'has_any_match': False,
                'error': str(e)
            }


class GitHubURLMatcher:
    """GitHub URL matching and pattern extraction."""
    
    def extract_extensions_from_url_patterns(self, url_patterns_str):
        """Extract file extensions from URL patterns (e.g., 'NA-exe,x64-msi' -> {'exe', 'msi'})"""
        if pd.isna(url_patterns_str) or url_patterns_str == "":
            return set()

        extensions = set()
        patterns = url_patterns_str.split(",")

        for pattern in patterns:
            pattern = pattern.strip()
            if pattern:
                # Handle NA- patterns (e.g., "NA-exe")
                if pattern.startswith("NA-"):
                    ext = pattern.split("-", 1)[1] if len(pattern.split("-")) > 1 else ""
                    if ext:
                        extensions.add(ext)
                else:
                    # Handle arch-ext patterns (e.g., "x64-exe", "setup-msi")
                    parts = pattern.split("-")
                    if len(parts) >= 2:
                        ext = parts[-1]  # Last part should be the extension
                        if ext and not ext.isdigit():  # Skip if it's just a number
                            extensions.add(ext)

        return extensions

    def filter_github_urls(self, row):
        """Filter GitHub URLs based on URL patterns."""
        # Use the correct column name from the actual CSV
        url_column = "LatestVersionURLsInWinGet"
        
        if pd.isna(row[url_column]) or pd.isna(row["URLPatterns"]):
            return row[url_column]

        github_urls = row[url_column].split(",")
        valid_extensions = self.extract_extensions_from_url_patterns(row["URLPatterns"])

        if not valid_extensions:
            return row[url_column]

        # Filter URLs that match the extensions
        filtered_urls = []
        for url in github_urls:
            url = url.strip()
            # Extract extension from URL (assuming it's at the end of the URL)
            url_ext_match = re.search(r"\.([^.]+)$", url)
            if url_ext_match:
                url_ext = url_ext_match.group(1)
                if url_ext in valid_extensions:
                    filtered_urls.append(url)

        return ",".join(filtered_urls) if filtered_urls else row[url_column]

    def process_urls(self, input_path: str, output_path: str) -> None:
        """Process GitHub URLs from input CSV and save filtered results to output CSV."""
        try:
            # Ensure input file exists
            if not Path(input_path).exists():
                raise FileNotFoundError(f"Input file not found: {input_path}")

            # Read the CSV file
            df = pd.read_csv(input_path)

            # Filter for GitHub packages only
            github_mask = (
                (df['Source'].str.contains('github.com', case=False, na=False)) |
                (df['PackageIdentifier'].str.startswith('GitHub.', na=False)) |
                (df['LatestVersionURLsInWinGet'].str.contains('github.com', case=False, na=False))
            )
            df_github = df[github_mask].copy()

            # Use the correct column name and apply the filtering
            url_column = "LatestVersionURLsInWinGet"
            if url_column in df_github.columns:
                df_github[url_column] = df_github.apply(self.filter_github_urls, axis=1)
            else:
                logger.warning(f"Column '{url_column}' not found in input file. Available columns: {list(df_github.columns)}")

            # Create output directory if it doesn't exist
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            # Save the updated data
            df_github.to_csv(output_path, index=False)
            
            logger.info(f"Processed {len(df_github)} GitHub packages from {len(df)} total packages")

        except Exception as e:
            raise Exception(f"Error processing URLs: {str(e)}")


class GitHubVersionAnalyzer:
    """GitHub version analysis and release processing with WinGet comparison."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.token_manager = None
        self.github_api = None
        
        # Initialize WinGet manifest extractor and URL comparator
        self.winget_extractor = WinGetManifestExtractor()
        self.url_comparator = URLComparator()
        
        # Initialize GitHub API if tokens are available  
        try:
            # Get tokens from config first
            github_tokens = self.config.get('github_tokens', [])
            
            if github_tokens and isinstance(github_tokens, list):
                # Use first available token to create GitHub API (like old code)
                token = github_tokens[0]
                github_config = GitHubConfig(token=token)
                self.github_api = GitHubAPI(github_config)
                logger.info(f"GitHub API initialized successfully with config token")
            else:
                # Try token manager as fallback (like your old code)
                try:
                    self.token_manager = TokenManager(self.config)
                    token = self.token_manager.get_available_token()
                    if token:
                        github_config = GitHubConfig(token=token)
                        self.github_api = GitHubAPI(github_config)
                        logger.info("GitHub API initialized successfully via token manager")
                except Exception as e:
                    logger.warning(f"Could not initialize GitHub API via token manager: {e}")
                    
        except Exception as e:
            logger.warning(f"Failed to initialize GitHub API: {e}")

    def compare_with_all_winget_versions(self, package_identifier: str, github_urls: List[str], github_version: str = None) -> Dict[str, any]:
        """Compare GitHub latest URLs vs ALL WinGet package version URLs and check version presence."""
        try:
            # Get all installer URLs from all versions of the package
            all_winget_urls_by_version = self.winget_extractor.get_all_installer_urls_for_package(package_identifier)
            
            if not all_winget_urls_by_version:
                return {
                    'comparison_performed': False,
                    'reason': 'No WinGet manifests found',
                    'winget_versions_found': 0,
                    'is_version_present': False
                }
            
            # Create flat list of ALL URLs from ALL versions
            all_winget_urls = []
            for version, urls in all_winget_urls_by_version.items():
                all_winget_urls.extend(urls)
            
            # Remove duplicates
            unique_winget_urls = list(set(all_winget_urls))
            
            # Use URLComparator for comprehensive comparison
            comparison_result = self.url_comparator.compare_urls(github_urls, unique_winget_urls)
            
            # Check if version is present in WinGet versions
            is_version_present = False
            
            if github_version and github_version != "Not found":
                # Normalize GitHub version for comparison
                normalized_github_version = github_version.lower().lstrip('v').strip()
                
                # Check if GitHub version is present in WinGet versions
                winget_versions = list(all_winget_urls_by_version.keys())
                normalized_winget_versions = [v.lower().lstrip('v').strip() for v in winget_versions]
                
                if normalized_github_version in normalized_winget_versions:
                    is_version_present = True
                    logger.debug(f"Version {github_version} found in WinGet versions for {package_identifier}")
            
            # If version not found, check URL pattern matching
            if not is_version_present and comparison_result['has_any_match']:
                is_version_present = True
                logger.debug(f"URL patterns match for {package_identifier}")
            
            return {
                'comparison_performed': True,
                'winget_versions_found': len(all_winget_urls_by_version),
                'winget_versions': list(all_winget_urls_by_version.keys()),
                'unique_winget_urls_count': len(unique_winget_urls),
                'is_version_present': is_version_present,
                'exact_matches': comparison_result['exact_matches'],
                'exact_matches_count': len(comparison_result['exact_matches']),
                'normalized_matches': comparison_result['normalized_matches'],
                'normalized_matches_count': len(comparison_result['normalized_matches']),
                'github_urls_checked': github_urls,
                'winget_urls_total': len(all_winget_urls),
                'github_version_checked': github_version
            }
            
        except Exception as e:
            logger.error(f"Error comparing with WinGet versions for {package_identifier}: {e}")
            return {
                'comparison_performed': False,
                'reason': f'Error: {str(e)}',
                'winget_versions_found': 0,
                'is_version_present': False
            }

    def analyze_versions(self, package_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze versions for a GitHub package with comprehensive WinGet comparison."""
        try:
            # Get package info from the row data
            package_name = package_data.get('PackageIdentifier', '')
            versions = package_data.get('AvailableVersions', '')
            version_pattern = package_data.get('VersionFormatPattern', '')
            latest_version = package_data.get('CurrentLatestVersionInWinGet', '')
            download_urls_count = package_data.get('InstallerURLsCount', 0)
            installer_urls = package_data.get('LatestVersionURLsInWinGet', '')
            url_patterns = package_data.get('URLPatterns', '')  # Changed from ArchExtPairs
            open_prs = package_data.get('HasOpenPullRequests', 'unknown')
            source = package_data.get('Source', '')  # New column you added

            # Extract GitHub repo from installer URLs
            github_repo = None
            for url in installer_urls.split(","):
                if url.strip() and "github.com" in url:
                    # Extract owner/repo from GitHub URL
                    match = re.search(r'github\.com/([^/]+)/([^/]+)', url.strip())
                    if match:
                        github_repo = f"{match.group(1)}/{match.group(2)}"
                        break

            if not github_repo:
                # Get all WinGet URLs even if no GitHub repo found
                all_winget_urls_dict = {}
                all_winget_urls_flat = []
                if package_name:
                    try:
                        winget_extractor = WinGetManifestExtractor()
                        all_winget_urls_dict = winget_extractor.get_all_installer_urls_for_package(package_name)
                        for version_urls in all_winget_urls_dict.values():
                            all_winget_urls_flat.extend(version_urls)
                    except Exception as e:
                        logger.debug(f"Error extracting WinGet URLs for {package_name}: {e}")

                # Return basic data without GitHub info
                result = {
                    "PackageIdentifier": package_name,
                    "Source": source,
                    "GitHubRepo": "",
                    "VersionFormatPattern": version_pattern,
                    "URLPatterns": url_patterns,
                    "InstallerURLsCount": download_urls_count,
                    "AvailableVersions": versions,
                    "CurrentLatestVersionInWinGet": latest_version,
                    "AllVersionInstallerURLsInWinGet": ",".join(list(set(all_winget_urls_flat))),
                    "LatestVersionURLsInWinGet": installer_urls,
                    "GitHubLatest": "Not found",
                    "LatestGitHubURLs": "",
                    "LatestReleaseInstallerURLsOfGitHub": "",
                    "HasOpenPullRequests": open_prs,
                    # WinGet comparison fields
                "WinGetVersionsFound": 0,
                "URLComparisonPerformed": False,
                "ExactURLMatches": 0,
                "IsVersionPresent": False,
                "WinGetVersionsList": "",
                "UniqueWinGetURLsCount": 0,
                "ExactMatchDetails": "",
                "NormalizedMatches": 0,
                "GitHubURLsChecked": "",
                "WinGetURLsTotal": 0,
                "GitHubVersionChecked": "",
                "ComparisonFailureReason": "No GitHub repo found"
                }
                return result

            # Extract username and repo name
            username, repo = github_repo.split("/")

            # Get latest version and URLs from GitHub API (like your old code)
            latest_version_github = "Not found"
            latest_github_urls = ""
            
            if self.github_api:
                try:
                    latest_release = self.github_api.get_latest_release(username, repo)
                    if latest_release:
                        latest_version_github = latest_release.get("tag_name", "Not found")
                        if latest_version_github and latest_version_github != "Not found":
                            latest_version_github = latest_version_github.replace("%2B", "+")

                        # Filter URLs based on extensions from url_patterns (was arch_ext_pairs)
                        if url_patterns:
                            all_urls = latest_release.get("asset_urls", [])
                            filtered_urls = []

                            # Extract extensions from url_patterns
                            valid_extensions = set()
                            for pattern in url_patterns.split(","):
                                if pattern.strip():
                                    # Handle patterns like "x64-exe", "setup-msi", "NA-exe"
                                    parts = pattern.strip().rsplit("-", 1)
                                    if len(parts) == 2:
                                        _, ext = parts
                                        valid_extensions.add(ext.lower())

                            # Filter URLs based on extensions
                            for url in all_urls:
                                url = url.replace("%2B", "+")
                                url_lower = url.lower()
                                for ext in valid_extensions:
                                    if url_lower.endswith(f".{ext}"):
                                        filtered_urls.append(url)
                                        break

                            latest_github_urls = ",".join(filtered_urls)
                        else:
                            # No URL patterns, use all asset URLs
                            all_urls = latest_release.get("asset_urls", [])
                            latest_github_urls = ",".join([url.replace("%2B", "+") for url in all_urls])
                except Exception as e:
                    logger.debug(f"Error getting GitHub release for {github_repo}: {e}")

            # Get all WinGet URLs for the new column
            all_winget_urls_dict = {}
            all_winget_urls_flat = []
            if package_name:
                try:
                    winget_extractor = WinGetManifestExtractor()
                    all_winget_urls_dict = winget_extractor.get_all_installer_urls_for_package(package_name)
                    for version_urls in all_winget_urls_dict.values():
                        all_winget_urls_flat.extend(version_urls)
                except Exception as e:
                    logger.debug(f"Error extracting WinGet URLs for {package_name}: {e}")

            # Get filtered GitHub URLs that match URL patterns
            filtered_github_urls = []
            if latest_github_urls and url_patterns:
                github_urls_list = [url.strip() for url in latest_github_urls.split(",") if url.strip()]
                filtered_github_urls = self._filter_urls_by_patterns(github_urls_list, url_patterns)

            # Perform WinGet comparison if we have GitHub URLs
            winget_comparison = {}
            if latest_github_urls:
                github_urls_list = [url.strip() for url in latest_github_urls.split(",") if url.strip()]
                # Pass the GitHub version for version checking
                winget_comparison = self.compare_with_all_winget_versions(
                    package_name, 
                    github_urls_list, 
                    latest_version_github
                )

            # Prepare the result with all fields (matching your old code structure)
            result = {
                "PackageIdentifier": package_name,
                "Source": source,
                "GitHubRepo": github_repo,
                "VersionFormatPattern": version_pattern,
                "URLPatterns": url_patterns,
                "InstallerURLsCount": download_urls_count,
                "AvailableVersions": versions,
                "CurrentLatestVersionInWinGet": latest_version,
                "AllVersionInstallerURLsInWinGet": ",".join(list(set(all_winget_urls_flat))),  # All URLs from all versions
                "LatestVersionURLsInWinGet": installer_urls,
                "GitHubLatest": latest_version_github,
                "LatestGitHubURLs": latest_github_urls,
                "LatestReleaseInstallerURLsOfGitHub": ",".join(filtered_github_urls),  # Filtered GitHub URLs
                "HasOpenPullRequests": open_prs,
            }
            
            # Add WinGet comparison results
            if winget_comparison.get('comparison_performed', False):
                result.update({
                    "WinGetVersionsFound": winget_comparison.get('winget_versions_found', 0),
                    "URLComparisonPerformed": True,
                    "ExactURLMatches": winget_comparison.get('exact_matches_count', 0),
                    "IsVersionPresent": winget_comparison.get('is_version_present', False),
                    "WinGetVersionsList": ','.join(winget_comparison.get('winget_versions', [])),
                    "UniqueWinGetURLsCount": winget_comparison.get('unique_winget_urls_count', 0),
                    "ExactMatchDetails": ','.join(winget_comparison.get('exact_matches', [])),
                    "NormalizedMatches": len(winget_comparison.get('normalized_matches', [])),
                    "GitHubURLsChecked": ','.join(winget_comparison.get('github_urls_checked', [])),
                    "WinGetURLsTotal": winget_comparison.get('winget_urls_total', 0),
                    "GitHubVersionChecked": winget_comparison.get('github_version_checked', '')
                })
            else:
                # No comparison performed
                result.update({
                    "WinGetVersionsFound": 0,
                    "URLComparisonPerformed": False,
                    "ExactURLMatches": 0,
                    "IsVersionPresent": False,
                    "WinGetVersionsList": "",
                    "UniqueWinGetURLsCount": 0,
                    "ExactMatchDetails": "",
                    "NormalizedMatches": 0,
                    "GitHubURLsChecked": "",
                    "WinGetURLsTotal": 0,
                    "GitHubVersionChecked": "",
                    "ComparisonFailureReason": winget_comparison.get('reason', 'Unknown')
                })

            return result

        except Exception as e:
            logger.error(f"Error analyzing versions for {package_data.get('PackageIdentifier', '')}: {e}")
            return package_data

    def _filter_urls_by_patterns(self, urls: List[str], url_patterns: str) -> List[str]:
        """Filter URLs based on URL patterns like 'x64-exe', 'setup-msi'."""
        try:
            if not url_patterns or not urls:
                return urls
            
            # Extract extensions from url_patterns
            valid_extensions = set()
            for pattern in url_patterns.split(","):
                if pattern.strip():
                    # Handle patterns like "x64-exe", "setup-msi", "NA-exe"
                    parts = pattern.strip().rsplit("-", 1)
                    if len(parts) == 2:
                        _, ext = parts
                        valid_extensions.add(ext.lower())
            
            if not valid_extensions:
                return urls
            
            # Filter URLs based on extensions
            filtered_urls = []
            for url in urls:
                url_lower = url.lower()
                for ext in valid_extensions:
                    if url_lower.endswith(f".{ext}"):
                        filtered_urls.append(url)
                        break
            
            return filtered_urls
        except Exception as e:
            logger.debug(f"Error filtering URLs by patterns: {e}")
            return urls

    def _extract_owner_repo(self, package_data: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
        """Extract owner and repo from package data."""
        # Try to get from PackageIdentifier (format: GitHub.owner.repo)
        identifier = package_data.get('PackageIdentifier', '')
        if identifier.startswith('GitHub.'):
            parts = identifier.split('.')
            if len(parts) >= 3:
                return parts[1], parts[2]

        # Try to get from URL columns
        url_fields = ['LatestVersionURLsInWinGet', 'URL', 'RepositoryURL']
        for field in url_fields:
            url = package_data.get(field, '')
            if url and 'github.com' in url:
                match = re.search(r'github\.com/([^/]+)/([^/]+)', url)
                if match:
                    return match.group(1), match.group(2)

        return None, None

    def _process_release_data(self, release_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process GitHub release data into package format."""
        result = {}
        
        # Extract version information (use existing column names)
        result['CurrentLatestVersionInWinGet'] = release_data.get('tag_name', '')
        result['AvailableVersions'] = release_data.get('tag_name', '')
        
        # Extract download URLs from assets
        assets = release_data.get('assets', [])
        download_urls = [asset.get('browser_download_url') for asset in assets if asset.get('browser_download_url')]
        result['LatestVersionURLsInWinGet'] = ','.join(download_urls)
        result['InstallerURLsCount'] = len(download_urls)
        
        # Extract URL patterns
        if download_urls:
            url_patterns = self._extract_url_patterns(download_urls)
            result['URLPatterns'] = ','.join(url_patterns)
        
        # Additional metadata
        result['ReleaseDate'] = release_data.get('published_at', '')
        result['IsPrerelease'] = release_data.get('prerelease', False)
        result['ReleaseNotes'] = release_data.get('body', '')

        return result

    def _extract_url_patterns(self, urls: List[str]) -> Set[str]:
        """Extract URL patterns from download URLs."""
        patterns = set()
        
        for url in urls:
            # Extract architecture
            arch = self._extract_architecture(url)
            # Extract extension
            ext = self._extract_extension(url)
            
            if arch and ext:
                patterns.add(f"{arch}-{ext}")
            elif ext:
                patterns.add(ext)
        
        return patterns

    def _extract_architecture(self, url: str) -> Optional[str]:
        """Extract architecture from URL."""
        url_lower = url.lower()
        
        # Architecture patterns (order matters - more specific first)
        arch_patterns = [
            (r'\b(x86_64|amd64)\b', 'x64'),
            (r'\b(x64)\b', 'x64'),
            (r'\b(x86|i386|i686)\b', 'x86'),
            (r'\b(arm64|aarch64)\b', 'arm64'),
            (r'\b(arm)\b', 'arm'),
        ]
        
        for pattern, normalized_arch in arch_patterns:
            if re.search(pattern, url_lower):
                return normalized_arch
        
        return None

    def _extract_extension(self, url: str) -> Optional[str]:
        """Extract file extension from URL."""
        # Handle URLs ending with /download
        if url.endswith('/download'):
            # Look for extension in the path before /download
            match = re.search(r'/([^/]+)\.([^./]+)/download$', url)
            if match:
                ext = match.group(2)
                if ext and not ext.isdigit():
                    return ext.lower()
        
        # Standard extension extraction
        match = re.search(r'\.([^./?#]+)(?:[?#]|$)', url)
        if match:
            ext = match.group(1)
            if ext and not ext.isdigit() and len(ext) <= 5:
                return ext.lower()
        
        return None


class GitHubFilter:
    """GitHub package filtering functionality with comprehensive filter pipeline."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}

    def has_matching_urls(self, row):
        """Check if current version URLs match between WinGet and GitHub."""
        winget_urls_col = "LatestVersionURLsInWinGet"
        github_urls_col = "LatestGitHubURLs"
        
        if winget_urls_col not in row or github_urls_col not in row:
            return False
            
        if pd.isna(row[winget_urls_col]) or pd.isna(row[github_urls_col]):
            return False
            
        winget_urls = str(row[winget_urls_col]).split(",")
        github_urls = str(row[github_urls_col]).split(",")
        return any(
            url.strip() in [gh_url.strip() for gh_url in github_urls] for url in winget_urls
        )

    def normalize_version(self, version):
        """Normalize version strings for comparison."""
        if pd.isna(version):
            return ""
        version = str(version).lower()
        # Remove common version prefixes
        prefixes = ["v", "ver", "version"]
        for prefix in prefixes:
            if version.startswith(prefix):
                version = version[len(prefix):].lstrip()
        # Standardize separators
        version = version.replace("+", "_")
        return version.strip()

    def versions_match(self, ver1, ver2):
        """Check if two versions match after normalization."""
        return self.normalize_version(ver1) == self.normalize_version(ver2)

    def count_github_urls(self, urls):
        """Count GitHub URLs in a comma-separated string."""
        if pd.isna(urls) or urls == "":
            return 0
        return len(str(urls).split(","))

    def filter_packages(self, packages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply comprehensive filtering pipeline to packages."""
        if not packages:
            return packages
            
        # Convert to DataFrame for easier filtering
        df = pd.DataFrame(packages)
        initial_count = len(df)
        logger.info(f"Starting filter process with {initial_count} packages")
        
        # Filter 1: Remove rows with "Not Found" in GitHubLatest
        if 'GitHubLatest' in df.columns:
            df = df[df["GitHubLatest"] != "Not Found"]
            logger.info(f"Filter 1: {len(df)} packages remaining after removing 'Not Found' GitHub releases")

        # Filter 2: Remove rows where LatestGitHubURLs is empty
        if 'LatestGitHubURLs' in df.columns:
            df = df[~(df["LatestGitHubURLs"].isna() | (df["LatestGitHubURLs"] == ""))]
            logger.info(f"Filter 2: {len(df)} packages remaining after removing empty GitHub URLs")

        # Filter 3: Remove rows where LatestVersionPullRequest is open
        if 'LatestVersionPullRequest' in df.columns:
            df = df[df["LatestVersionPullRequest"] != "open"]
            logger.info(f"Filter 3: {len(df)} packages remaining after removing packages with open PRs")

        # Filter 4: Remove rows where URLPatterns is empty
        if 'URLPatterns' in df.columns:
            df = df[~(df["URLPatterns"].isna() | (df["URLPatterns"] == ""))]
            logger.info(f"Filter 4: {len(df)} packages remaining after removing packages without URL patterns")

        # Filter 5: Remove rows where URLs match (current version)
        if 'LatestVersionURLsInWinGet' in df.columns and 'LatestGitHubURLs' in df.columns:
            df = df[~df.apply(self.has_matching_urls, axis=1)]
            logger.info(f"Filter 5: {len(df)} packages remaining after removing packages with matching current URLs")

        # Filter 5.5: Remove rows where GitHub version/URLs are already present in WinGet
        if 'IsVersionPresent' in df.columns:
            df = df[df["IsVersionPresent"] != True]
            logger.info(f"Filter 5.5: {len(df)} packages remaining after removing packages where version is already present")

        # Filter 6: Remove rows where versions match exactly
        if 'CurrentLatestVersionInWinGet' in df.columns and 'GitHubLatest' in df.columns:
            df = df[df["CurrentLatestVersionInWinGet"] != df["GitHubLatest"]]
            logger.info(f"Filter 6: {len(df)} packages remaining after removing packages with exact version matches")

        # Filter 7: Remove rows where versions match after normalization
        if 'CurrentLatestVersionInWinGet' in df.columns and 'GitHubLatest' in df.columns:
            df = df[~df.apply(
                lambda row: self.versions_match(
                    row["CurrentLatestVersionInWinGet"], 
                    row["GitHubLatest"]
                ), axis=1
            )]
            logger.info(f"Filter 7: {len(df)} packages remaining after removing packages with normalized version matches")

        # Filter 8: Remove rows where URL counts don't match
        if 'InstallerURLsCount' in df.columns and 'LatestGitHubURLs' in df.columns:
            df = df[~df.apply(
                lambda row: self.count_github_urls(row["LatestGitHubURLs"]) != row["InstallerURLsCount"],
                axis=1
            )]
            logger.info(f"Filter 8: {len(df)} packages remaining after removing packages with URL count mismatches")

        # Convert back to list of dictionaries
        filtered_packages = df.to_dict('records')
        
        logger.info(f"Filtering complete: {len(filtered_packages)} packages remaining from {initial_count} original packages")
        return filtered_packages

    def should_include_package(self, package: Dict[str, Any]) -> bool:
        """Determine if a single package should be included (legacy method)."""
        # Basic validation
        if not package.get('PackageIdentifier'):
            return False
        
        # Check if it's a GitHub package
        if not package.get('PackageIdentifier', '').startswith('GitHub.'):
            return False
        
        # Check for minimum requirements
        if self.config.get('require_installer_urls', True):
            if package.get('InstallerURLsCount', 0) == 0:
                return False
        
        # Check star count if available
        min_stars = self.config.get('min_stars', 0)
        if package.get('Stars', 0) < min_stars:
            return False
        
        return True

    def process_filters(self, input_path: str, output_path: str) -> None:
        """Process filters on a CSV file."""
        try:
            df = pd.read_csv(input_path)
            
            # Convert to list of dictionaries for filtering
            packages = df.to_dict('records')
            
            # Apply filters
            filtered_packages = self.filter_packages(packages)
            
            # Convert back to DataFrame and save
            if filtered_packages:
                filtered_df = pd.DataFrame(filtered_packages)
                filtered_df.to_csv(output_path, index=False)
            else:
                # Create empty DataFrame with same columns
                empty_df = pd.DataFrame(columns=df.columns)
                empty_df.to_csv(output_path, index=False)
                
        except Exception as e:
            logger.error(f"Error processing filters: {e}")
            raise


class AsyncWinGetPRSearcher:
    """Async GitHub GraphQL API client for searching Pull Requests in the microsoft/winget-pkgs repository."""
    
    def __init__(self, tokens: List[str], max_concurrent_requests: int = 10):
        if not tokens:
            raise ValueError("At least one GitHub token is required for GraphQL API")
        
        self.tokens = tokens
        self.current_token_index = 0
        self.graphql_url = "https://api.github.com/graphql"
        self.repo_owner = "microsoft"
        self.repo_name = "winget-pkgs"
        self.max_concurrent_requests = max_concurrent_requests
        
        # Rate limiting per token
        self.request_counts = {token: 0 for token in tokens}
        self.last_request_times = {token: 0 for token in tokens}
        self.min_request_interval = 0.1  # 100ms between requests per token
        
        # Semaphore to control concurrent requests
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        
        logger.info(f"Async PR Searcher initialized with {len(tokens)} tokens, max {max_concurrent_requests} concurrent requests")
    
    def get_next_token(self) -> str:
        """Get the next token in round-robin fashion for load balancing."""
        token = self.tokens[self.current_token_index]
        self.current_token_index = (self.current_token_index + 1) % len(self.tokens)
        return token
    
    async def execute_query_async(self, session, query: str, variables: Dict = None) -> Dict:
        """Execute a GraphQL query asynchronously with rate limiting."""
        async with self.semaphore:
            token = self.get_next_token()
            
            # Rate limiting per token
            current_time = time.time()
            last_request_time = self.last_request_times.get(token, 0)
            time_since_last = current_time - last_request_time
            
            if time_since_last < self.min_request_interval:
                await asyncio.sleep(self.min_request_interval - time_since_last)
            
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'query': query,
                'variables': variables or {}
            }
            
            try:
                async with session.post(self.graphql_url, headers=headers, json=payload) as response:
                    self.last_request_times[token] = time.time()
                    self.request_counts[token] += 1
                    
                    if response.status == 200:
                        result = await response.json()
                        
                        if 'errors' in result:
                            logger.error(f"GraphQL errors: {result['errors']}")
                            raise Exception(f"GraphQL errors: {result['errors']}")
                        
                        return result.get('data', {})
                    else:
                        error_text = await response.text()
                        logger.error(f"HTTP error {response.status}: {error_text}")
                        raise Exception(f"HTTP error {response.status}: {error_text}")
                        
            except Exception as e:
                logger.error(f"Request error: {e}")
                raise
    
    async def search_package_prs_async(self, session, package_name: str, max_results: int = 20) -> List[Dict]:
        """Search for Pull Requests related to a specific package asynchronously."""
        # Escape the package name for GraphQL search
        escaped_package_name = package_name.replace('"', '\\"')
        
        # Build search query - search in PR titles
        search_query = f'repo:{self.repo_owner}/{self.repo_name} is:pr "{escaped_package_name}" in:title'
        
        query = """
        query SearchPackagePRs($query: String!, $first: Int!) {
            search(query: $query, type: ISSUE, first: $first) {
                issueCount
                nodes {
                    ... on PullRequest {
                        number
                        title
                        state
                        createdAt
                        updatedAt
                        closedAt
                        mergedAt
                        url
                        body
                        author {
                            login
                        }
                        baseRefName
                        headRefName
                        commits(first: 1) {
                            nodes {
                                commit {
                                    message
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        
        variables = {
            'query': search_query,
            'first': min(max_results, 20)  # Limit to avoid large responses
        }
        
        try:
            data = await self.execute_query_async(session, query, variables)
            
            if "search" not in data:
                logger.debug(f"No search results found for package: {package_name}")
                return []
            
            prs = []
            for pr in data["search"]["nodes"]:
                # Extract commit message if available
                commit_message = None
                if pr["commits"]["nodes"]:
                    commit_message = pr["commits"]["nodes"][0]["commit"]["message"]
                
                enhanced_pr = {
                    "number": pr["number"],
                    "title": pr["title"],
                    "state": pr["state"],
                    "created_at": pr["createdAt"],
                    "updated_at": pr["updatedAt"],
                    "closed_at": pr["closedAt"],
                    "merged_at": pr["mergedAt"],
                    "author": pr["author"]["login"] if pr["author"] else None,
                    "base_ref": pr["baseRefName"],
                    "head_ref": pr["headRefName"],
                    "url": pr["url"],
                    "body": pr["body"],
                    "commit_message": commit_message
                }
                
                prs.append(enhanced_pr)
            
            logger.debug(f"Found {len(prs)} PRs for package: {package_name}")
            return prs
            
        except Exception as e:
            logger.error(f"Error searching PRs for {package_name}: {e}")
            return []
    
    def search_in_pr_content(self, package_name: str, pr_data: dict) -> bool:
        """Search for package name in PR content (title, body, commit messages)."""
        search_terms = [
            package_name.lower(),
            package_name.replace(".", "").lower(),
            package_name.replace("-", "").lower(),
            package_name.replace("_", "").lower()
        ]
        
        # Search in title
        title = pr_data.get("title", "").lower()
        if any(term in title for term in search_terms):
            return True
        
        # Search in body
        body = pr_data.get("body", "") or ""
        if any(term in body.lower() for term in search_terms):
            return True
        
        # Search in commit message
        commit_message = pr_data.get("commit_message", "") or ""
        if any(term in commit_message.lower() for term in search_terms):
            return True
        
        return False
    
    async def get_latest_version_pr_status_async(self, session, package_name: str) -> str:
        """Get the status of the most recent PR for a package asynchronously."""
        try:
            # Search for PRs with expanded search
            prs = await self.search_package_prs_async(session, package_name, max_results=20)
            
            if not prs:
                logger.debug(f"No PRs found for package: {package_name}")
                return "not_found"
            
            # Filter PRs that actually contain the package name in content
            relevant_prs = []
            for pr in prs:
                if self.search_in_pr_content(package_name, pr):
                    relevant_prs.append(pr)
            
            if not relevant_prs:
                logger.debug(f"No relevant PRs found for package: {package_name}")
                return "not_found"
            
            # Sort by creation date (most recent first) 
            sorted_prs = sorted(relevant_prs, key=lambda x: x['created_at'], reverse=True)
            most_recent_pr = sorted_prs[0]
            
            # Log the found PR for debugging
            logger.debug(f"Found recent PR for {package_name}: #{most_recent_pr['number']} - {most_recent_pr['title']} ({most_recent_pr['state']})")
            
            # Return the state of the most recent relevant PR
            state = most_recent_pr['state'].lower()
            if state == 'open':
                return "open"
            elif state == 'merged':
                return "merged"
            elif state == 'closed':
                return "closed"
            else:
                return "unknown"
                
        except Exception as e:
            logger.error(f"Error getting PR status for {package_name}: {e}")
            return "error"


class AsyncPRStatusProcessor:
    """Async processor for adding PR status information to packages."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.github_api = None
        self.pr_searcher = None
        
        try:
            # Get tokens from config first
            github_tokens = self.config.get('github_tokens', [])
            
            # If no tokens in config, try token manager with proper import
            if not github_tokens:
                try:
                    # Create TokenManager instance using the working approach from your old code
                    token_manager = TokenManager(self.config)
                    
                    # Try to get multiple tokens if available
                    tokens = []
                    for _ in range(5):
                        token = token_manager.get_available_token()
                        if token and token not in tokens:
                            tokens.append(token)
                    
                    if tokens:
                        github_tokens = tokens
                        logger.info(f"Retrieved {len(tokens)} GitHub tokens from token manager")
                    
                except Exception as e:
                    logger.warning(f"Could not get tokens from token manager: {e}")
            
            if github_tokens:
                self.pr_searcher = AsyncWinGetPRSearcher(github_tokens, 
                                                       max_concurrent_requests=self.config.get('concurrent_requests', 10))
                logger.info(f"Initialized async PR searcher with {len(github_tokens)} tokens")
            else:
                logger.warning("No GitHub tokens available for PR processing")
                
        except Exception as e:
            logger.warning(f"Failed to initialize GitHub API for PR processing: {e}")

    async def process_pr_status(self, packages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process PR status for GitHub packages asynchronously."""
        if not self.pr_searcher:
            logger.warning("GitHub API not available for PR status processing - no valid tokens")
            # Return packages with 'unknown' status
            for package in packages:
                package['LatestVersionPullRequest'] = 'unknown'
            return packages
        
        # Check if we have dummy/invalid tokens
        sample_token = self.pr_searcher.tokens[0] if self.pr_searcher.tokens else ""
        if sample_token == "dummy_token_for_testing" or not sample_token:
            logger.warning("Invalid GitHub tokens detected - skipping PR status processing")
            for package in packages:
                package['LatestVersionPullRequest'] = 'unknown'
            return packages
        
        logger.info(f"Processing PR status for {len(packages)} packages with {len(self.pr_searcher.tokens)} tokens")
        
        # Process packages in batches to avoid rate limiting
        batch_size = self.config.get('batch_size', 50)
        
        results = []
        
        # Use aiohttp session
        import aiohttp
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for i in range(0, len(packages), batch_size):
                batch = packages[i:i + batch_size]
                batch_tasks = [self._check_pr_status(session, pkg) for pkg in batch]
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                for result in batch_results:
                    if isinstance(result, dict):
                        results.append(result)
                    else:
                        logger.error(f"Error processing package: {result}")
                
                # Small delay between batches
                if i + batch_size < len(packages):
                    await asyncio.sleep(1)
        
        return results

    async def _check_pr_status(self, session, package: Dict[str, Any]) -> Dict[str, Any]:
        """Check PR status for a single package."""
        try:
            package_name = package.get('PackageIdentifier', '')
            
            # Check if this is a GitHub package
            if not (package_name.startswith('GitHub.') or 
                    'github.com' in package.get('Source', '').lower() or
                    'github.com' in package.get('LatestVersionURLsInWinGet', '').lower()):
                package['LatestVersionPullRequest'] = 'not_applicable'
                return package
            
            # Get PR status using the async searcher
            pr_status = await self.pr_searcher.get_latest_version_pr_status_async(session, package_name)
            package['LatestVersionPullRequest'] = pr_status
            
            return package
            
        except Exception as e:
            logger.error(f"Error checking PR status for {package.get('PackageIdentifier', '')}: {e}")
            package['LatestVersionPullRequest'] = 'error'
            return package


class GitHubOrchestrator:
    """Main GitHub processing orchestrator."""
    
    def __init__(self, config: Dict[str, Any] = None):
        # Initialize logger first
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Load config
        self.config = config or self._load_config()
        
        # Initialize components
        self.url_matcher = GitHubURLMatcher()
        self.version_analyzer = GitHubVersionAnalyzer(self.config)
        self.filter = GitHubFilter(self.config.get('filter', {}))
        self.pr_processor = AsyncPRStatusProcessor(self.config)

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration with fallback options."""
        try:
            # Try to get from config system first
            config = get_config()
            
            # Ensure config is a dictionary
            if not isinstance(config, dict):
                self.logger.warning(f"Config is not a dictionary, got {type(config)}: {config}")
                config = {}
                
        except Exception as e:
            self.logger.warning(f"Error loading config system: {e}, using fallback")
            config = {}
        
        # Always try to get tokens from environment (like your original working code)
        github_tokens = []
        
        # Try environment variables (primary method)
        env_token = os.environ.get('GITHUB_TOKEN')
        if env_token:
            github_tokens.append(env_token)
        
        # Try multiple token environment variables
        for i in range(1, 6):  # Check GITHUB_TOKEN_1 through GITHUB_TOKEN_5
            env_token = os.environ.get(f'GITHUB_TOKEN_{i}')
            if env_token and env_token not in github_tokens:
                github_tokens.append(env_token)
        
        if github_tokens:
            config['github_tokens'] = github_tokens
            self.logger.info(f"Loaded {len(github_tokens)} GitHub tokens from environment")
        else:
            # Try to get from token manager as backup
            try:
                token_manager = TokenManager(config)
                token = token_manager.get_available_token()
                if token:
                    github_tokens = [token]
                    config['github_tokens'] = github_tokens
                    self.logger.info("Loaded 1 GitHub token from token manager")
            except Exception as e:
                self.logger.warning(f"Could not get tokens from token manager: {e}")
        
        # Set other default config values
        config.setdefault('batch_size', 50)
        config.setdefault('concurrent_requests', 10)
        config.setdefault('paths', {
            'github_output_dir': 'data/github',
            'input_csv': 'data/AllPackageInfo.csv'
        })
        
        return config

    def setup_logging(self):
        """Configure logging for the package analysis process."""
        try:
            logging_config = self.config.get('logging', {})
            
            logging.basicConfig(
                level=getattr(logging, logging_config.get('level', 'INFO')),
                format=logging_config.get('format', "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
            )
        except Exception:
            # Fallback to default logging if config fails
            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            )

    def setup_directories(self):
        """Setup required directories for processing."""
        try:
            output_dir = Path(self.config.get('paths', {}).get('github_output_dir', 'data/github'))
            output_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Output directory ready: {output_dir}")
        except Exception as e:
            self.logger.error(f"Error setting up directories: {e}")
            raise

    def run_complete_workflow(self, input_file: str = None):
        """Run the complete GitHub analysis workflow."""
        try:
            self.setup_logging()
            self.setup_directories()
            
            self.logger.info("Starting GitHub package analysis workflow")
            
            # Step 1: URL Processing
            if input_file:
                input_path = input_file
            else:
                input_path = self.config.get('paths', {}).get('input_csv', 'data/AllPackageInfo.csv')
            
            url_output_path = "data/github/GitHubPackageInfo_CleanedURLs.csv"
            self.logger.info(f"Processing URLs: {input_path} -> {url_output_path}")
            self.url_matcher.process_urls(input_path, url_output_path)
            
            # Step 2: Version Analysis
            version_output_path = "data/github/GitHubPackageInfo_Analyzed.csv"
            self.logger.info(f"Analyzing versions: {url_output_path} -> {version_output_path}")
            self._run_version_analysis(url_output_path, version_output_path)
            
            # Step 3: Filtering
            filter_output_path = "data/github/GitHubPackageInfo_Filtered.csv"
            self.logger.info(f"Applying filters: {version_output_path} -> {filter_output_path}")
            self.filter.process_filters(version_output_path, filter_output_path)
            
            # Step 4: PR Status (async)
            final_output_path = "data/github/GitHubPackageInfo_Final.csv"
            self.logger.info(f"Processing PR status: {filter_output_path} -> {final_output_path}")
            asyncio.run(self._run_pr_status_processing(filter_output_path, final_output_path))
            
            self.logger.info(f"GitHub workflow completed successfully. Final output: {final_output_path}")
            return final_output_path
            
        except Exception as e:
            self.logger.error(f"Error in GitHub workflow: {e}")
            raise
            self.logger.info(f"Copying to final output: {filter_output_path} -> {final_output_path}")
            import shutil
            shutil.copy2(filter_output_path, final_output_path)
            
            self.logger.info("GitHub package analysis workflow completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error in GitHub workflow: {e}")
            return False
            self.logger.info(f"Processing PR status: {filter_output_path} -> {final_output_path}")
            asyncio.run(self._run_pr_status_processing(filter_output_path, final_output_path))
            
            self.logger.info(f"GitHub workflow completed successfully. Final output: {final_output_path}")
            return final_output_path
            
        except Exception as e:
            self.logger.error(f"Error in GitHub workflow: {e}")
            raise

    def _run_version_analysis(self, input_path: str, output_path: str):
        """Run version analysis on packages."""
        try:
            df = pd.read_csv(input_path)
            packages = df.to_dict('records')
            
            analyzed_packages = []
            winget_extractor = WinGetManifestExtractor()
            url_comparator = URLComparator()
            
            for package in packages:
                analyzed_package = self.version_analyzer.analyze_versions(package)
                
                # Perform WinGet comparison even without GitHub API
                package_id = package.get('PackageIdentifier', '')
                current_urls = package.get('LatestVersionURLsInWinGet', '')
                
                if package_id and current_urls:
                    github_urls_list = [url.strip() for url in current_urls.split(",") if url.strip() and 'github.com' in url]
                    
                    if github_urls_list:
                        winget_comparison = self._compare_with_winget_versions(package_id, github_urls_list, winget_extractor, url_comparator)
                        
                        # Add WinGet comparison results
                        if winget_comparison.get('comparison_performed', False):
                            analyzed_package.update({
                                "WinGetVersionsFound": winget_comparison.get('winget_versions_found', 0),
                                "URLComparisonPerformed": True,
                                "ExactURLMatches": winget_comparison.get('exact_matches_count', 0),
                                "IsVersionPresent": winget_comparison.get('is_version_present', False),
                                "WinGetVersionsList": ','.join(winget_comparison.get('winget_versions', [])),
                                "UniqueWinGetURLsCount": winget_comparison.get('unique_winget_urls_count', 0),
                                "ExactMatchDetails": ','.join(winget_comparison.get('exact_matches', [])),
                                "NormalizedMatches": len(winget_comparison.get('normalized_matches', [])),
                                "GitHubURLsChecked": ','.join(winget_comparison.get('github_urls_checked', [])),
                                "WinGetURLsTotal": winget_comparison.get('winget_urls_total', 0),
                                # Add new columns if not already present
                                "AllVersionInstallerURLsInWinGet": analyzed_package.get('AllVersionInstallerURLsInWinGet', ''),
                                "LatestReleaseInstallerURLsOfGitHub": analyzed_package.get('LatestReleaseInstallerURLsOfGitHub', '')
                            })
                        else:
                            # No comparison performed
                            analyzed_package.update({
                                "WinGetVersionsFound": 0,
                                "URLComparisonPerformed": False,
                                "ExactURLMatches": 0,
                                "IsVersionPresent": False,
                                "WinGetVersionsList": "",
                                "UniqueWinGetURLsCount": 0,
                                "ExactMatchDetails": "",
                                "NormalizedMatches": 0,
                                "GitHubURLsChecked": "",
                                "WinGetURLsTotal": 0,
                                "ComparisonFailureReason": winget_comparison.get('reason', 'Unknown'),
                                # Add new columns if not already present
                                "AllVersionInstallerURLsInWinGet": analyzed_package.get('AllVersionInstallerURLsInWinGet', ''),
                                "LatestReleaseInstallerURLsOfGitHub": analyzed_package.get('LatestReleaseInstallerURLsOfGitHub', '')
                            })
                    else:
                        # No GitHub URLs found
                        analyzed_package.update({
                            "WinGetVersionsFound": 0,
                            "URLComparisonPerformed": False,
                            "ExactURLMatches": 0,
                            "IsVersionPresent": False,
                            "WinGetVersionsList": "",
                            "UniqueWinGetURLsCount": 0,
                            "ExactMatchDetails": "",
                            "NormalizedMatches": 0,
                            "GitHubURLsChecked": "",
                            "WinGetURLsTotal": 0,
                            "ComparisonFailureReason": "No GitHub URLs found",
                            # Add new columns if not already present
                            "AllVersionInstallerURLsInWinGet": analyzed_package.get('AllVersionInstallerURLsInWinGet', ''),
                            "LatestReleaseInstallerURLsOfGitHub": analyzed_package.get('LatestReleaseInstallerURLsOfGitHub', '')
                        })
                else:
                    # No package ID or URLs
                    analyzed_package.update({
                        "WinGetVersionsFound": 0,
                        "URLComparisonPerformed": False,
                        "ExactURLMatches": 0,
                        "IsVersionPresent": False,
                        "WinGetVersionsList": "",
                        "UniqueWinGetURLsCount": 0,
                        "ExactMatchDetails": "",
                        "NormalizedMatches": 0,
                        "GitHubURLsChecked": "",
                        "WinGetURLsTotal": 0,
                        "ComparisonFailureReason": "Missing package identifier or URLs",
                        # Add new columns if not already present
                        "AllVersionInstallerURLsInWinGet": analyzed_package.get('AllVersionInstallerURLsInWinGet', ''),
                        "LatestReleaseInstallerURLsOfGitHub": analyzed_package.get('LatestReleaseInstallerURLsOfGitHub', '')
                    })
                
                analyzed_packages.append(analyzed_package)
            
            if analyzed_packages:
                result_df = pd.DataFrame(analyzed_packages)
                result_df.to_csv(output_path, index=False)
                self.logger.info(f"Version analysis completed with WinGet comparison for {len(analyzed_packages)} packages")
            
        except Exception as e:
            self.logger.error(f"Error in version analysis: {e}")
            raise

    async def _run_pr_status_processing(self, input_path: str, output_path: str):
        """Run async PR status processing."""
        try:
            df = pd.read_csv(input_path)
            packages = df.to_dict('records')
            
            processed_packages = await self.pr_processor.process_pr_status(packages)
            
            if processed_packages:
                result_df = pd.DataFrame(processed_packages)
                result_df.to_csv(output_path, index=False)
            
        except Exception as e:
            self.logger.error(f"Error in PR status processing: {e}")
            raise

    def _compare_with_winget_versions(self, package_identifier: str, github_urls: List[str], winget_extractor, url_comparator) -> Dict[str, any]:
        """Compare GitHub URLs with all WinGet versions (standalone method)."""
        try:
            # Get all installer URLs from all versions of the package
            all_winget_urls_by_version = winget_extractor.get_all_installer_urls_for_package(package_identifier)
            
            if not all_winget_urls_by_version:
                return {
                    'comparison_performed': False,
                    'reason': 'No WinGet manifests found',
                    'winget_versions_found': 0,
                    'has_any_match': False
                }
            
            # Create flat list of ALL URLs from ALL versions
            all_winget_urls = []
            for version, urls in all_winget_urls_by_version.items():
                all_winget_urls.extend(urls)
            
            # Remove duplicates
            unique_winget_urls = list(set(all_winget_urls))
            
            # Use URLComparator for comprehensive comparison
            comparison_result = url_comparator.compare_urls(github_urls, unique_winget_urls)
            
            return {
                'comparison_performed': True,
                'winget_versions_found': len(all_winget_urls_by_version),
                'winget_versions': list(all_winget_urls_by_version.keys()),
                'unique_winget_urls_count': len(unique_winget_urls),
                'has_any_match': comparison_result['has_any_match'],
                'exact_matches': comparison_result['exact_matches'],
                'exact_matches_count': len(comparison_result['exact_matches']),
                'normalized_matches': comparison_result['normalized_matches'],
                'normalized_matches_count': len(comparison_result['normalized_matches']),
                'github_urls_checked': github_urls,
                'winget_urls_total': len(all_winget_urls)
            }
            
        except Exception as e:
            self.logger.error(f"Error comparing with WinGet versions for {package_identifier}: {e}")
            return {
                'comparison_performed': False,
                'reason': f'Error: {str(e)}',
                'winget_versions_found': 0,
                'has_any_match': False
            }


# Main functions for backward compatibility
def setup_logging():
    """Setup logging (backward compatibility)."""
    orchestrator = GitHubOrchestrator()
    orchestrator.setup_logging()

def setup_directories():
    """Setup directories (backward compatibility)."""
    orchestrator = GitHubOrchestrator()
    orchestrator.setup_directories()

def main():
    """Main entry point for GitHub processing."""
    orchestrator = GitHubOrchestrator()
    return orchestrator.run_complete_workflow()

async def run_async_pr_status_processing():
    """Run async PR status processing (backward compatibility)."""
    orchestrator = GitHubOrchestrator()
    return await orchestrator._run_pr_status_processing(
        "data/github/GitHubPackageInfo_Filtered.csv",
        "data/github/GitHubPackageInfo_Final.csv"
    )

def process_urls(input_path: str, output_path: str):
    """Process URLs (backward compatibility)."""
    matcher = GitHubURLMatcher()
    return matcher.process_urls(input_path, output_path)

def process_filters(input_path: str, output_path: str):
    """Process filters (backward compatibility)."""
    filter_processor = GitHubFilter()
    return filter_processor.process_filters(input_path, output_path)

if __name__ == "__main__":
    main()
