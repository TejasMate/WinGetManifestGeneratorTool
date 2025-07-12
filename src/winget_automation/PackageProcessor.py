import concurrent.futures
import polars as pl
import logging
import yaml
import re
import time
import requests
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union
from dataclasses import dataclass

# Handle both relative and absolute imports
try:
    from .utils.unified_utils import BaseConfig, YAMLProcessorBase, GitHubURLProcessor
    from .utils.version_pattern_utils import VersionPatternDetector
    from .utils.token_manager import TokenManager
    from .exceptions import (
        PackageProcessingError,
        ManifestParsingError,
        FileOperationError,
        GitHubAPIError,
        ConfigurationError,
    )
except ImportError:
    # Fallback for direct script execution
    import sys
    import os
    from pathlib import Path
    
    # Add parent directory to path
    current_dir = Path(__file__).parent if '__file__' in globals() else Path.cwd() / 'src' / 'winget_automation'
    parent_dir = current_dir.parent
    sys.path.insert(0, str(parent_dir))
    
    from winget_automation.utils.unified_utils import BaseConfig, YAMLProcessorBase, GitHubURLProcessor
    from winget_automation.utils.version_pattern_utils import VersionPatternDetector
    from winget_automation.utils.token_manager import TokenManager
    from winget_automation.exceptions import (
        PackageProcessingError,
        ManifestParsingError,
        FileOperationError,
        GitHubAPIError,
        ConfigurationError,
    )

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


@dataclass
class GitHubConfig:
    """Configuration for GitHub API interactions.

    Attributes:
        token: GitHub API token for authentication
        base_url: Base URL for GitHub API (default: https://api.github.com)
        per_page: Number of items per page for paginated requests
    """

    token: str
    base_url: str = "https://api.github.com"
    per_page: int = 100


@dataclass
class ProcessingConfig(BaseConfig):
    """Configuration for package processing operations.

    Attributes:
        output_manifest_file: Name of the output file for package manifests
        output_analysis_file: Name of the output file for package analysis
        open_prs_file: Name of the output file for open pull requests
    """

    output_manifest_file: str = "PackageNames.csv"
    output_analysis_file: str = "AllPackageInfo.csv"
    open_prs_file: str = "OpenPRs.csv"


class PackageProcessor(YAMLProcessorBase):
    """Processes WinGet package manifests and analyzes package information.

    This class is responsible for:
    - Scanning and parsing WinGet package manifest files
    - Extracting package information and version patterns
    - Analyzing GitHub URLs and repository information
    - Generating structured data outputs for further processing

    Attributes:
        token_manager: Manages GitHub API tokens
        github_config: Configuration for GitHub API interactions
        unique_rows: Set of unique package identifier rows
        max_dots: Maximum number of dots in package identifiers
        package_versions: Map of package IDs to their versions
        package_downloads: Map of package IDs to download counts
        version_patterns: Map of package IDs to version patterns
        latest_urls: Map of package IDs to latest release URLs
        latest_extensions: Map of package IDs to file extensions
        latest_version_map: Map of package IDs to latest versions
        arch_ext_pairs: Map of package IDs to architecture-extension pairs
        architectures: List of supported architectures
        extensions: List of supported file extensions
    """

    def __init__(self, config: ProcessingConfig):
        """Initialize the PackageProcessor.

        Args:
            config: Processing configuration

        Raises:
            ConfigurationError: If configuration is invalid
            TokenManagerError: If GitHub tokens cannot be loaded
        """
        try:
            super().__init__(config)
            self.token_manager = TokenManager()
            self.github_config = None
            self._init_github_config()

            # Manifest processing attributes
            self.unique_rows: Set[Tuple[str, ...]] = set()
            self.max_dots = 0

            # Version analysis attributes
            self.package_versions: Dict[str, Set[str]] = {}
            self.package_downloads: Dict[str, int] = {}
            self.version_patterns: Dict[str, Set[str]] = (
                {}
            )  # Changed to Set to store multiple patterns
            self.latest_urls: Dict[str, List[str]] = {}
            self.latest_extensions: Dict[str, List[str]] = {}
            self.latest_version_map: Dict[str, str] = {}
            self.arch_ext_pairs: Dict[str, str] = {}
            self.architectures = [
                "x86-64",
                "aarch64",
                "x86_64",
                "arm64",
                "arm",
                "win64",
                "amd64",
                "x86",
                "i386",
                "ia32",
                "386",
                "win32",
                "32bit",
                "win-arm64",
                "win-x64",
                "win-x86",
                "win-ia32",
                "windows-arm64",
                "windows-x64",
                "windows-x86",
                "windows-ia32",
                "armv6",
                "armv7",
                "arm8",
                "arm9",
                "x64",
                "x32",
                "i686",
                "64bit",
                "x86_x64",
                "x86only",
                "shared-32",
                "shared-64",
                "installer32",
                "installer64",
                "32",
                "64",
            ]
            self.extensions = [
                "msixbundle",
                "appxbundle",
                "msix",
                "appx",
                "zip",
                "msi",
                "exe",
            ]

        except Exception as e:
            raise ConfigurationError(f"Failed to initialize PackageProcessor: {str(e)}")

    def _init_github_config(self) -> None:
        """Initialize GitHub configuration with an available token.

        Raises:
            GitHubAPIError: If no GitHub tokens are available
        """
        try:
            token = self.token_manager.get_available_token()
            if not token:
                raise GitHubAPIError("No GitHub tokens available for configuration")
            self.github_config = GitHubConfig(token=token)
        except Exception as e:
            raise GitHubAPIError(f"Failed to initialize GitHub configuration: {str(e)}")

    def process_manifest_file(self, file_path: Path) -> None:
        """Process a single manifest file and extract package information.

        Args:
            file_path: Path to the manifest file

        Raises:
            ManifestParsingError: If the manifest file cannot be processed
        """
        try:
            name = file_path.stem.replace(".installer", "")
            parts = name.split(".")

            if len(set(parts)) == 1:
                return

            padded_parts = parts[: self.max_dots + 1] + [""] * (
                self.max_dots + 1 - len(parts)
            )
            row = tuple(padded_parts[: self.max_dots + 1])
            self.unique_rows.add(row)

        except Exception as e:
            raise ManifestParsingError(
                f"Failed to process manifest file: {str(e)}", file_path=str(file_path)
            )

    def calculate_max_dots(self, files: List[Path]) -> None:
        """Calculate the maximum number of dots in package identifiers.

        Args:
            files: List of manifest file paths

        Raises:
            PackageProcessingError: If calculation fails
        """
        try:
            self.max_dots = (
                max(
                    file_path.stem.replace(".installer", "").count(".")
                    for file_path in files
                )
                if files
                else 0
            )
        except Exception as e:
            raise PackageProcessingError(f"Error calculating max dots: {str(e)}")

    def create_manifest_dataframe(self) -> pl.DataFrame:
        """Create a DataFrame from processed manifest data.

        Returns:
            Polars DataFrame containing manifest data

        Raises:
            PackageProcessingError: If DataFrame creation fails
        """
        try:
            if not self.unique_rows:
                return pl.DataFrame()

            column_names = [f"column_{i}" for i in range(self.max_dots + 1)]
            data_dict = {name: [] for name in column_names}

            for row in self.unique_rows:
                for i, value in enumerate(row):
                    data_dict[column_names[i]].append(value)

            return pl.DataFrame(data_dict)
        except Exception as e:
            raise PackageProcessingError(f"Error creating manifest dataframe: {str(e)}")

    def extract_arch_ext_pairs(self, urls: List[str]) -> str:
        """Extract architecture-extension pairs from installer URLs.

        Args:
            urls: List of installer URLs

        Returns:
            String representation of architecture-extension pairs

        Raises:
            PackageProcessingError: If extraction fails
        """
        try:
            pairs = []
            logging.info(
                f"Processing {len(urls)} URLs for architecture-extension pairs"
            )
            for url in urls:
                url_lower = url.lower().strip()
                logging.info(f"\nProcessing URL: {url_lower}")

                # Find extension
                ext_match = None
                for ext in self.extensions:
                    if url_lower.endswith(f".{ext}"):
                        ext_match = ext
                        logging.info(f"Found extension: {ext_match}")
                        break

                if not ext_match:
                    logging.info(f"No valid extension found in URL: {url_lower}")
                    continue

                # Find architecture
                arch_match = None
                logging.info(f"Searching for architecture patterns in: {url_lower}")
                for arch in self.architectures:
                    logging.info(f"Checking architecture pattern: {arch}")
                    pattern = None
                    if arch in ["aarch64", "x86_64", "x86-64"]:
                        pattern = f"[^a-z0-9]({arch})[^a-z0-9]|[_.-]({arch})[_.-]|[_.-]({arch})$"
                    elif arch == "x86_x64":
                        pattern = f"(x86_x64|x86[_.-]x64|x86[-_.]64)"
                    elif arch == "x86only":
                        pattern = "(x86only|x86[_.-]only)"
                    elif arch in ["32", "64"]:
                        pattern = f"(installer[-]?{arch}|{arch}[-]?bit|x{arch}|[_.-]{arch})[_.-]|[_.-](installer[-]?{arch}|{arch}[-]?bit|x{arch}|{arch})$|[^a-z0-9]x{arch}[^a-z0-9]"
                    elif arch in [
                        "installer32",
                        "installer64",
                        "shared-32",
                        "shared-64",
                    ]:
                        base = arch.split("-")[0] if "-" in arch else arch[:-2]
                        num = arch[-2:]
                        pattern = f"({base}[-]?{num}|{base}[_.-]{num})"
                    else:
                        pattern = f"[^a-z0-9]({arch})[^a-z0-9]|[_.-]({arch})[_.-]|[_.-]({arch})$|[^a-z0-9]{arch}[^a-z0-9]"

                    if re.search(pattern, url_lower):
                        arch_match = arch
                        logging.info(
                            f"Found architecture {arch_match} using pattern: {pattern}"
                        )
                        break

                if not arch_match:
                    logging.info("No architecture pattern matched")

                pair = f'{arch_match or "NA"}-{ext_match}'
                logging.info(f"Adding pair: {pair}")
                pairs.append(pair)

            result = ",".join(sorted(set(pairs))) if pairs else ""
            logging.info(f"Final arch-ext pairs: {result}")
            return result
        except Exception as e:
            raise PackageProcessingError(
                f"Failed to extract architecture-extension pairs: {str(e)}"
            )
            if not self.unique_rows:
                return pl.DataFrame()

            column_names = [f"column_{i}" for i in range(self.max_dots + 1)]
            data_dict = {name: [] for name in column_names}

            for row in self.unique_rows:
                for i, value in enumerate(row):
                    data_dict[column_names[i]].append(value)

            return pl.DataFrame(data_dict)
        except Exception as e:
            logging.error(f"Error creating manifest dataframe: {e}")
            return pl.DataFrame()

    def extract_arch_ext_pairs(self, urls: List[str]) -> str:
        pairs = []
        logging.info(f"Processing {len(urls)} URLs for architecture-extension pairs")
        for url in urls:
            url_lower = url.lower().strip()
            logging.info(f"\nProcessing URL: {url_lower}")

            # Find extension
            ext_match = None
            for ext in self.extensions:
                if url_lower.endswith(f".{ext}"):
                    ext_match = ext
                    logging.info(f"Found extension: {ext_match}")
                    break

            if not ext_match:
                logging.info(f"No valid extension found in URL: {url_lower}")
                continue

            # Find architecture
            arch_match = None
            logging.info(f"Searching for architecture patterns in: {url_lower}")
            for arch in self.architectures:
                logging.info(f"Checking architecture pattern: {arch}")
                pattern = None
                if arch in ["aarch64", "x86_64", "x86-64"]:
                    pattern = (
                        f"[^a-z0-9]({arch})[^a-z0-9]|[_.-]({arch})[_.-]|[_.-]({arch})$"
                    )
                elif arch == "x86_x64":
                    pattern = f"(x86_x64|x86[_.-]x64|x86[-_.]64)"
                elif arch == "x86only":
                    pattern = "(x86only|x86[_.-]only)"
                elif arch in ["32", "64"]:
                    pattern = f"(installer[-]?{arch}|{arch}[-]?bit|x{arch}|[_.-]{arch})[_.-]|[_.-](installer[-]?{arch}|{arch}[-]?bit|x{arch}|{arch})$|[^a-z0-9]x{arch}[^a-z0-9]"
                elif arch in ["installer32", "installer64", "shared-32", "shared-64"]:
                    base = arch.split("-")[0] if "-" in arch else arch[:-2]
                    num = arch[-2:]
                    pattern = f"({base}[-]?{num}|{base}[_.-]{num})"
                else:
                    pattern = f"[^a-z0-9]({arch})[^a-z0-9]|[_.-]({arch})[_.-]|[_.-]({arch})$|[^a-z0-9]{arch}[^a-z0-9]"

                if re.search(pattern, url_lower):
                    arch_match = arch
                    logging.info(
                        f"Found architecture {arch_match} using pattern: {pattern}"
                    )
                    break

            if not arch_match:
                logging.info("No architecture pattern matched")

            pair = f'{arch_match or "NA"}-{ext_match}'
            logging.info(f"Adding pair: {pair}")
            pairs.append(pair)

        result = ",".join(sorted(set(pairs))) if pairs else ""
        logging.info(f"Final arch-ext pairs: {result}")
        return result

    def count_download_urls(self, yaml_path: Path, package_name: str) -> int:
        try:
            data = self.process_yaml_file(yaml_path)
            if not data or "Installers" not in data:
                return 0

            urls = []
            extensions = []
            count = 0
            for installer in data["Installers"]:
                if "InstallerUrl" in installer:
                    url = installer["InstallerUrl"]
                    urls.append(url)
                    if "." in url:
                        ext = url.split(".")[-1].lower()
                        extensions.append(ext)
                    count += 1

            if urls:
                self.latest_urls[package_name] = urls
                self.latest_extensions[package_name] = extensions
                self.arch_ext_pairs[package_name] = self.extract_arch_ext_pairs(urls)

            return count
        except Exception as e:
            logging.error(f"Error counting download URLs in {yaml_path}: {e}")
            return 0

    def process_package(self, package_parts: List[str]) -> None:
        try:
            package_path = self.get_package_path(package_parts)
            if not package_path or not package_path.exists():
                return

            package_name = ".".join(package_parts)
            all_dirs = [d.name for d in package_path.iterdir() if d.is_dir()]
            if not all_dirs:
                return

            # Store all versions
            valid_version_dirs = []
            for version_dir in all_dirs:
                version_path = package_path / version_dir
                # Check if this directory contains any YAML files and no subdirectories with YAML files
                yaml_files = [f for f in version_path.glob("*.yaml") if f.is_file()]
                subdirs_with_yaml = any(
                    any(f.is_file() and f.suffix == ".yaml" for f in d.iterdir())
                    for d in version_path.iterdir()
                    if d.is_dir()
                )
                if bool(yaml_files) and not subdirs_with_yaml:
                    valid_version_dirs.append(version_dir)

            if not valid_version_dirs:
                return

            self.package_versions[package_name] = set(valid_version_dirs)

            # Modified version comparison to preserve trailing zeros
            def version_key(v):
                parts = re.split("([0-9]+)", v)
                return [p if not p.isdigit() else p.zfill(10) for p in parts]

            latest_version = max(valid_version_dirs, key=version_key)
            self.latest_version_map[package_name] = latest_version

            # Direct path to installer yaml
            yaml_path = package_path / latest_version / f"{package_name}.installer.yaml"
            if yaml_path.exists():
                data = self.process_yaml_file(yaml_path)
                if data and "Installers" in data:
                    urls = []
                    extensions = []
                    count = 0
                    for installer in data["Installers"]:
                        if "InstallerUrl" in installer:
                            url = installer["InstallerUrl"].replace("%2B", "+")
                            urls.append(url)
                            if "." in url:
                                ext = url.split(".")[-1].lower()
                                extensions.append(ext)
                            count += 1

                    if urls:
                        # Keep all versions but update other metadata
                        self.latest_urls[package_name] = urls
                        self.latest_extensions[package_name] = extensions
                        self.package_downloads[package_name] = count
                        # Initialize version patterns set if not exists
                        if package_name not in self.version_patterns:
                            self.version_patterns[package_name] = set()
                        # Add patterns for all versions
                        for version in self.package_versions[package_name]:
                            pattern = VersionPatternDetector.determine_version_pattern(
                                version
                            )
                            self.version_patterns[package_name].add(pattern)
                        # Extract and store arch-ext pairs
                        self.arch_ext_pairs[package_name] = self.extract_arch_ext_pairs(
                            urls
                        )

        except Exception as e:
            logging.error(
                f"Error processing package {package_name if 'package_name' in locals() else '.'.join(package_parts)}: {e}"
            )

    def check_package_in_prs(self, package_name: str, pr_titles: List[str]) -> str:
        package_lower = package_name.lower()
        return (
            "present"
            if any(package_lower in title.lower() for title in pr_titles)
            else "absent"
        )

    def create_analysis_dataframe(
        self, pr_titles: Optional[List[str]] = None
    ) -> pl.DataFrame:
        try:
            data = []
            for pkg, vers in self.package_versions.items():
                # Process URLs and extract arch-ext pairs if not already done
                if pkg in self.latest_urls and not self.arch_ext_pairs.get(pkg):
                    urls = self.latest_urls[pkg]
                    self.arch_ext_pairs[pkg] = self.extract_arch_ext_pairs(urls)

                data.append(
                    {
                        "PackageIdentifier": pkg,
                        "AvailableVersions": ",".join(sorted(vers)),
                        "VersionFormatPattern": ",".join(
                            sorted(self.version_patterns.get(pkg, {"unknown"}))
                        ),
                        "CurrentLatestVersionInWinGet": self.latest_version_map.get(
                            pkg, ""
                        ),
                        "InstallerURLsCount": self.package_downloads.get(pkg, 0),
                        "LatestVersionURLsInWinGet": ",".join(
                            self.latest_urls.get(pkg, [])
                        ),
                        "ArchExtPairs": self.arch_ext_pairs.get(pkg, ""),
                        "HasOpenPullRequests": (
                            self.check_package_in_prs(pkg, pr_titles)
                            if pr_titles
                            else "unknown"
                        ),
                    }
                )

            # Ensure arch_ext_pairs are populated
            for item in data:
                pkg = item["PackageIdentifier"]
                if pkg in self.latest_urls and not self.arch_ext_pairs.get(pkg):
                    self.arch_ext_pairs[pkg] = self.extract_arch_ext_pairs(
                        self.latest_urls[pkg]
                    )
            return pl.DataFrame(data)
        except Exception as e:
            logging.error(f"Error creating analysis dataframe: {e}")
            return pl.DataFrame()

    def process_files(self) -> None:
        try:
            # Process manifest files
            yaml_files = self.get_yaml_files()
            if not yaml_files:
                logging.warning("No YAML files found")
                return

            self.calculate_max_dots(yaml_files)
            self.parallel_process(yaml_files, self.process_manifest_file)
            manifest_df = self.create_manifest_dataframe()
            self.save_dataframe(manifest_df, self.config.output_manifest_file)

            # Process package versions and analysis
            package_parts_list = []
            for row in manifest_df.to_dicts():
                parts = [
                    row[f"column_{i}"] for i in range(len(row)) if row[f"column_{i}"]
                ]
                if parts:
                    package_parts_list.append(parts)

            self.parallel_process(package_parts_list, self.process_package)

            # Fetch and save open PRs
            pr_titles = self.fetch_and_save_open_prs()

            # Create and save analysis dataframe
            analysis_df = self.create_analysis_dataframe(pr_titles)
            if not analysis_df.is_empty():
                self.save_dataframe(analysis_df, self.config.output_analysis_file)

        except Exception as e:
            logging.error(f"Error processing files: {e}")

    def _init_github_config(self) -> None:
        try:
            token = self.token_manager.get_available_token()
            if not token:
                raise RuntimeError("No available GitHub tokens found")
            self.github_config = GitHubConfig(token=token)
        except Exception as e:
            logging.error(f"Error initializing GitHub config: {e}")
            raise

    def get_open_prs(self, owner: str, repo: str) -> List[Dict]:
        all_prs = []
        page = 1
        session = requests.Session()
        session.headers.update(
            {
                "Authorization": f"token {self.github_config.token}",
                "Accept": "application/vnd.github.v3+json",
            }
        )

        while True:
            try:
                url = f"{self.github_config.base_url}/repos/{owner}/{repo}/pulls"
                params = {
                    "state": "open",
                    "per_page": self.github_config.per_page,
                    "page": page,
                }

                response = session.get(url, params=params)
                response.raise_for_status()

                prs = response.json()
                if not prs:
                    break

                all_prs.extend(
                    [
                        {
                            "number": pr["number"],
                            "title": pr["title"],
                            "user": pr["user"]["login"],
                            "created_at": pr["created_at"],
                            "updated_at": pr["updated_at"],
                            "url": pr["html_url"],
                        }
                        for pr in prs
                    ]
                )

                if "next" not in response.links:
                    break

                page += 1

                remaining = int(response.headers.get("X-RateLimit-Remaining", 0))
                if remaining == 0:
                    reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
                    wait_time = max(reset_time - time.time(), 0)
                    logging.info(f"Rate limit reached. Waiting for {wait_time} seconds")
                    time.sleep(wait_time)

            except requests.exceptions.RequestException as e:
                logging.error(f"Error fetching PRs: {e}")
                raise

        return all_prs

    def fetch_and_save_open_prs(self) -> List[str]:
        try:
            owner = "microsoft"
            repo = "winget-pkgs"

            prs = self.get_open_prs(owner, repo)
            df = pl.DataFrame(prs)
            # Use config's output path instead of hardcoded data directory
            output_path = self.config.get_output_path(self.config.open_prs_file)
            df.write_csv(output_path)
            logging.info(f"Saved {len(prs)} PRs to {output_path}")
            return df["title"].to_list()
        except Exception as e:
            logging.error(f"Error fetching and saving PRs: {e}")
            return []


def main():
    try:
        config = ProcessingConfig()
        processor = PackageProcessor(config)
        processor.process_files()
        logging.info("Processing completed successfully")
    except Exception as e:
        logging.error(f"Main process failed: {e}")


if __name__ == "__main__":
    main()
