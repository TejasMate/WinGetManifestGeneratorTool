import polars as pl
import logging
import re
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass
import sys
import os

# Handle imports for direct execution
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

try:
    from utils.token_manager import TokenManager
    from utils.unified_utils import GitHubAPI, GitHubConfig, GitHubURLProcessor, YAMLProcessorBase, BaseConfig
    from config import get_config
except ImportError:
    # Fallback for when run from different directory
    sys.path.insert(0, str(parent_dir.parent))
    from src.utils.token_manager import TokenManager
    from src.utils.unified_utils import GitHubAPI, GitHubConfig, GitHubURLProcessor, YAMLProcessorBase, BaseConfig
    from src.config import get_config

from concurrent.futures import ThreadPoolExecutor
import json
import yaml
from urllib.parse import urlparse

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


@dataclass
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
            logging.debug(f"Error getting package directory for {package_identifier}: {e}")
            return None
    
    def extract_installer_urls_from_manifest(self, manifest_path: Path) -> List[str]:
        """Extract installer URLs from a single manifest file."""
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest_data = yaml.safe_load(f)
                
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
        except Exception as e:
            logging.debug(f"Error extracting URLs from {manifest_path}: {e}")
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
            logging.debug(f"Error getting all URLs for {package_identifier}: {e}")
            return {}


@dataclass
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
    def extract_base_filename(url: str) -> str:
        """Extract base filename without version info."""
        try:
            # Get filename from URL
            filename = Path(urlparse(url).path).name
            
            # Remove version patterns
            filename = re.sub(r'-v?\d+\.\d+[\.\d]*', '', filename)
            filename = re.sub(r'_v?\d+\.\d+[\.\d]*', '', filename)
            
            return filename
        except Exception:
            return ""
    
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
            
            # Normalize URLs for comparison
            github_normalized = [(url, URLComparator.normalize_url_for_comparison(url)) for url in github_urls]
            winget_normalized = [(url, URLComparator.normalize_url_for_comparison(url)) for url in winget_urls]
            
            # Extract base filenames
            github_filenames = [(url, URLComparator.extract_base_filename(url)) for url in github_urls]
            winget_filenames = [(url, URLComparator.extract_base_filename(url)) for url in winget_urls]
            
            # Check for exact matches
            for gh_url in github_urls:
                if gh_url in winget_urls:
                    matches['exact_matches'].append(gh_url)
            
            # Check for normalized matches
            for gh_url, gh_norm in github_normalized:
                for wg_url, wg_norm in winget_normalized:
                    if gh_norm == wg_norm and gh_url not in matches['exact_matches']:
                        matches['normalized_matches'].append({'github': gh_url, 'winget': wg_url})
            
            # Check for filename matches
            for gh_url, gh_filename in github_filenames:
                for wg_url, wg_filename in winget_filenames:
                    if (gh_filename and wg_filename and 
                        gh_filename == wg_filename and 
                        gh_url not in matches['exact_matches'] and
                        not any(m['github'] == gh_url for m in matches['normalized_matches'])):
                        matches['filename_matches'].append({'github': gh_url, 'winget': wg_filename})
            
            # Set overall match flag
            matches['has_any_match'] = bool(
                matches['exact_matches'] or 
                matches['normalized_matches'] or 
                matches['filename_matches']
            )
            
            return matches
        except Exception as e:
            logging.debug(f"Error comparing URLs: {e}")
            return {
                'exact_matches': [],
                'normalized_matches': [],
                'filename_matches': [],
                'github_urls_count': len(github_urls),
                'winget_urls_count': len(winget_urls),
                'has_any_match': False,
                'error': str(e)
            }


@dataclass
class VersionAnalyzer:
    def __init__(self, github_api: GitHubAPI):
        self.github_api = github_api
        self.github_repos = {}
        # Initialize WinGet manifest extractor and URL comparator
        self.winget_extractor = WinGetManifestExtractor()
        self.url_comparator = URLComparator()

    def extract_version_from_url(self, url: str) -> Optional[str]:
        try:
            # For GitHub release URLs, version is after /download/ in the path
            if "github.com" in url and "/download/" in url:
                # Split URL by '/' and find the version component after 'download'
                parts = url.split("/")
                if "download" in parts:
                    download_index = parts.index("download")
                    if len(parts) > download_index + 1:
                        version = parts[download_index + 1]
                        # URL decode the version string, particularly handling %2B
                        version = version.replace("%2B", "+")
                        # Remove 'v' prefix if present
                        return version.lstrip("v")
            return None
        except Exception as e:
            logging.error(f"Error extracting version from URL {url}: {e}")
            return None

    def compare_with_all_winget_versions(self, package_identifier: str, github_urls: List[str]) -> Dict[str, any]:
        """Simple comparison: GitHub latest URLs vs ALL WinGet package version URLs."""
        try:
            # Get all installer URLs from all versions of the package
            all_winget_urls_by_version = self.winget_extractor.get_all_installer_urls_for_package(package_identifier)
            
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
            
            # Simple comparison: check if any GitHub URL matches any WinGet URL
            exact_matches = []
            for github_url in github_urls:
                github_url = github_url.strip()
                if github_url in unique_winget_urls:
                    exact_matches.append(github_url)
            
            has_any_match = len(exact_matches) > 0
            
            return {
                'comparison_performed': True,
                'winget_versions_found': len(all_winget_urls_by_version),
                'winget_versions': list(all_winget_urls_by_version.keys()),
                'unique_winget_urls_count': len(unique_winget_urls),
                'has_any_match': has_any_match,
                'exact_matches': exact_matches,
                'exact_matches_count': len(exact_matches),
                'github_urls_checked': github_urls,
                'winget_urls_total': len(all_winget_urls)
            }
            
        except Exception as e:
            logging.error(f"Error comparing with WinGet versions for {package_identifier}: {e}")
            return {
                'comparison_performed': False,
                'reason': f'Error: {str(e)}',
                'winget_versions_found': 0
            }

    def process_package(self, row: List) -> Dict:
        package_name = row[0]  # PackageIdentifier
        source = row[1]  # Source
        versions = row[2]  # AvailableVersions
        version_pattern = row[3]  # VersionFormatPattern
        latest_version = row[4]  # CurrentLatestVersionInWinGet
        download_urls_count = row[5]  # InstallerURLsCount
        installer_urls = row[6]  # LatestVersionURLsInWinGet
        url_patterns = row[7]  # URLPatterns
        open_prs = row[8]  # LatestVersionPullRequest

        try:
            # Extract GitHub repo from installer URLs
            github_repo = None
            for url in installer_urls.split(","):
                if url.strip() and "github.com" in url:
                    github_info = GitHubURLProcessor.extract_github_info(url)
                    if github_info:
                        github_repo = f"{github_info[0]}/{github_info[1]}"
                        break

            if not github_repo:
                return {
                    "PackageIdentifier": package_name,
                    "Source": source,
                    "GitHubRepo": "",
                    "AvailableVersions": versions,
                    "VersionFormatPattern": version_pattern,
                    "CurrentLatestVersionInWinGet": latest_version,
                    "InstallerURLsCount": download_urls_count,
                    "LatestVersionURLsInWinGet": installer_urls,
                    "URLPatterns": url_patterns,
                    "LatestVersionPullRequest": open_prs,
                    "GitHubLatest": "Not found",
                }

            # Extract username and repo name
            username, repo = github_repo.split("/")

            # Store the primary GitHub repo
            self.github_repos[package_name] = github_repo

            # Get latest version and URLs from GitHub
            latest_release = self.github_api.get_latest_release(username, repo)
            latest_version_github = (
                latest_release.get("tag_name") if latest_release else None
            )
            if latest_version_github:
                latest_version_github = latest_version_github.replace("%2B", "+")

            # Filter URLs based on extensions from url_patterns
            if latest_release and url_patterns:
                all_urls = [
                    url.replace("%2B", "+")
                    for url in latest_release.get("asset_urls", [])
                ]
                filtered_urls = []

                # Extract extensions from url_patterns
                valid_extensions = set()
                for pattern in url_patterns.split(","):
                    if pattern:
                        parts = pattern.split("-")
                        if len(parts) > 0:
                            # Last part should be the extension
                            ext = parts[-1]
                            if ext and not ext.isdigit():
                                valid_extensions.add(ext.lower())

                # Filter URLs based on extensions
                for url in all_urls:
                    url_lower = url.lower()
                    for ext in valid_extensions:
                        if url_lower.endswith(f".{ext}"):
                            filtered_urls.append(url)
                            break

                latest_github_urls = ",".join(filtered_urls)
            else:
                latest_github_urls = ""
            normalized_latest = (
                latest_version_github.lower().lstrip("v")
                if latest_version_github
                else ""
            )

            # Extract versions from installer URLs
            url_versions = set()
            for url in installer_urls.split(","):
                if url.strip():
                    url_version = self.extract_version_from_url(url)
                    if url_version:
                        url_versions.add(url_version.lower())

            # Normalize manifest versions
            normalized_versions = [v.lower().lstrip("v") for v in versions.split(",")]

            # NEW FEATURE: Compare GitHub URLs with all WinGet versions
            winget_comparison = {}
            github_urls_list = []
            if latest_github_urls:
                github_urls_list = [url.strip() for url in latest_github_urls.split(",") if url.strip()]
                winget_comparison = self.compare_with_all_winget_versions(package_name, github_urls_list)

            # Prepare the result with existing fields plus new comparison data
            result = {
                "PackageIdentifier": package_name,
                "Source": source,
                "GitHubRepo": github_repo,
                "AvailableVersions": versions,
                "VersionFormatPattern": version_pattern,
                "CurrentLatestVersionInWinGet": latest_version,
                "InstallerURLsCount": download_urls_count,
                "LatestVersionURLsInWinGet": installer_urls,
                "URLPatterns": url_patterns,
                "LatestVersionPullRequest": open_prs,
                "GitHubLatest": (
                    latest_version_github if latest_version_github else "Not found"
                ),
                "LatestGitHubURLs": latest_github_urls,
            }
            
            # Add WinGet comparison results
            if winget_comparison.get('comparison_performed', False):
                result.update({
                    "WinGetVersionsFound": winget_comparison.get('winget_versions_found', 0),
                    "URLComparisonPerformed": True,
                    "ExactURLMatches": winget_comparison.get('exact_matches_count', 0),
                    "HasAnyURLMatch": winget_comparison.get('has_any_match', False),
                    "WinGetVersionsList": ','.join(winget_comparison.get('winget_versions', [])),
                    "UniqueWinGetURLsCount": winget_comparison.get('unique_winget_urls_count', 0),
                    "ExactMatchDetails": ','.join(winget_comparison.get('exact_matches', [])),
                    "GitHubURLsChecked": ','.join(winget_comparison.get('github_urls_checked', [])),
                    "WinGetURLsTotal": winget_comparison.get('winget_urls_total', 0)
                })
            else:
                # No comparison performed
                result.update({
                    "WinGetVersionsFound": 0,
                    "URLComparisonPerformed": False,
                    "ExactURLMatches": 0,
                    "HasAnyURLMatch": False,
                    "WinGetVersionsList": "",
                    "UniqueWinGetURLsCount": 0,
                    "ExactMatchDetails": "",
                    "GitHubURLsChecked": "",
                    "WinGetURLsTotal": 0,
                    "ComparisonFailureReason": winget_comparison.get('reason', 'Unknown')
                })

            return result

        except Exception as e:
            logging.error(f"Error processing {package_name}: {e}")
            return {
                "PackageIdentifier": package_name,
                "Source": source,
                "GitHubRepo": github_repo if github_repo else "",
                "AvailableVersions": versions,
                "VersionFormatPattern": version_pattern,
                "CurrentLatestVersionInWinGet": latest_version,
                "InstallerURLsCount": download_urls_count,
                "LatestVersionURLsInWinGet": installer_urls,
                "URLPatterns": url_patterns,
                "LatestVersionPullRequest": open_prs,
                "GitHubLatest": (
                    latest_version_github if latest_version_github else "Not found"
                ),
                "LatestGitHubURLs": latest_github_urls,
            }

    def analyze_versions(self, input_path: Path, output_path: Path) -> None:
        """
        Analyze GitHub package versions and create enhanced package information.
        
        This method now uses the Source column for efficient GitHub package filtering,
        which is much faster than parsing URLs for each package.
        
        Performance: Processes ~3,400+ GitHub packages out of ~8,300+ total packages
        """
        try:
            # Read and process package info
            df = pl.read_csv(input_path)

            # Get blocked packages from config
            config = get_config()
            blocked_packages = set(config.get('filtering', {}).get('blocked_packages', []))
            
            # Filter out blocked packages
            if blocked_packages:
                df = df.filter(~pl.col("PackageIdentifier").is_in(blocked_packages))
                logging.info(f"Filtered out {len(blocked_packages)} blocked packages from config")

            # Filter for packages with GitHub source (more efficient than URL parsing)
            # Uses the Source column which directly indicates "github.com" for GitHub packages
            df_filtered = df.filter(
                pl.col("Source") == "github.com"
            )

            logging.info(
                f"Processing {len(df_filtered)} packages with GitHub repositories"
            )

            # Process packages in parallel using ThreadPoolExecutor
            results = []
            with ThreadPoolExecutor(max_workers=10) as executor:
                # Submit all tasks and get futures
                future_to_row = {
                    executor.submit(self.process_package, row): row
                    for row in df_filtered.rows()
                }

                # Collect results as they complete
                for future in future_to_row:
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        row = future_to_row[future]
                        package_name = row[0]
                        logging.error(f"Task failed for {package_name}: {e}")

            # Create new dataframe with results
            df_results = pl.DataFrame(results)

            # Save to CSV
            df_results.write_csv(output_path)
            logging.info(f"Results written to {output_path}")

        except Exception as e:
            logging.error(f"Error analyzing versions: {e}")
            raise


def main():
    try:
        # Initialize GitHub API
        token_manager = TokenManager()
        token = token_manager.get_available_token()
        if not token:
            raise RuntimeError("No available GitHub tokens found")

        config = GitHubConfig(token=token)
        github_api = GitHubAPI(config)

        # Initialize analyzer
        analyzer = VersionAnalyzer(github_api)

        # Set input and output paths
        input_path = Path("../data/AllPackageInfo.csv")
        output_path = Path("../data/GitHubPackageInfo.csv")

        # Run analysis
        analyzer.analyze_versions(input_path, output_path)
        logging.info("Version analysis completed successfully")

    except Exception as e:
        logging.error(f"Main process failed: {e}")
        raise


if __name__ == "__main__":
    main()
