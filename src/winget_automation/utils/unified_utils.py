import concurrent.futures
import os
import polars as pl
import requests
import yaml
import logging
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass

# Handle both relative and absolute imports
try:
    from .token_manager import TokenManager
except ImportError:
    # Fallback for direct script execution
    from token_manager import TokenManager

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


@dataclass
class BaseConfig:
    local_repo: str = "winget-pkgs"
    file_pattern: str = "*.installer.yaml"
    output_dir: str = "data"

    def get_output_path(self, filename: str) -> Path:
        return Path(self.output_dir) / filename


@dataclass
class GitHubConfig:
    token: str
    base_url: str = "https://api.github.com"
    per_page: int = 100
    retry_attempts: int = 3
    retry_backoff: float = 0.5


class YAMLProcessorBase:
    def __init__(self, config: BaseConfig):
        self.config = config
        self.manifests_dir = Path(config.local_repo) / "manifests"

    def get_yaml_files(self) -> List[Path]:
        try:
            return list(self.manifests_dir.rglob(self.config.file_pattern))
        except Exception as e:
            logging.error(f"Error finding YAML files: {e}")
            return []

    def process_yaml_file(self, yaml_path: Path) -> Optional[Dict]:
        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                return data
        except Exception as e:
            logging.error(f"Error processing YAML file {yaml_path}: {e}")
            return None

    def get_package_path(self, package_parts: List[str]) -> Optional[Path]:
        try:
            if not package_parts:
                return None
            first_char = package_parts[0][0].lower()
            return self.manifests_dir / first_char / "/".join(package_parts)
        except Exception as e:
            logging.error(
                f"Error getting package path for {'.'.join(package_parts)}: {e}"
            )
            return None

    def save_dataframe(self, df: pl.DataFrame, output_file: str) -> None:
        try:
            if not df.is_empty():
                output_path = self.config.get_output_path(output_file)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                df.write_csv(output_path)
                logging.info(f"Data written to {output_path}")
            else:
                logging.warning("No data to write")
        except Exception as e:
            logging.error(f"Error writing CSV file: {e}")

    def parallel_process(
        self, items: List, process_func, max_workers: int = None
    ) -> None:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(process_func, item) for item in items]
            concurrent.futures.wait(futures)

            for future in futures:
                if future.exception():
                    logging.error(f"Error in thread: {future.exception()}")


class GitHubAPIBase:
    def __init__(self):
        self.token_manager = TokenManager()
        self.base_url = "https://api.github.com"

    def _make_request(self, method: str, url: str, **kwargs) -> Optional[Dict]:
        """Make a request to GitHub API with token rotation and rate limit handling."""
        while True:
            token = self.token_manager.get_available_token()
            if not token:
                raise RuntimeError(
                    "All tokens are rate limited. Please try again later."
                )

            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
            }
            kwargs["headers"] = headers

            try:
                response = requests.request(method, url, **kwargs)
                self.token_manager.update_token_limits(token, response.headers)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 403 and "rate limit exceeded" in str(e):
                    continue
                raise

    def get_latest_release(self, owner: str, repo: str) -> Optional[Dict]:
        """Fetch the latest release information from a GitHub repository."""
        try:
            return self._make_request(
                "GET", f"{self.base_url}/repos/{owner}/{repo}/releases/latest"
            )
        except Exception as e:
            logging.error(f"Error fetching release for {owner}/{repo}: {e}")
            return None

    def create_pull_request(
        self, owner: str, repo: str, title: str, body: str, head: str, base: str
    ) -> Optional[Dict]:
        """Create a pull request on GitHub."""
        try:
            return self._make_request(
                "POST",
                f"{self.base_url}/repos/{owner}/{repo}/pulls",
                json={"title": title, "body": body, "head": head, "base": base},
            )
        except Exception as e:
            logging.error(f"Error creating pull request: {e}")
            return None


class GitHubAPI:
    def __init__(self, config: GitHubConfig):
        self.config = config
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        try:
            session = requests.Session()
            retry_strategy = Retry(
                total=self.config.retry_attempts,
                backoff_factor=self.config.retry_backoff,
                status_forcelist=[429, 500, 502, 503, 504],
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            session.mount("https://", adapter)
            session.headers.update(
                {
                    "Authorization": f"token {self.config.token}",
                    "Accept": "application/vnd.github.v3+json",
                }
            )
            return session
        except Exception as e:
            logging.error(f"Error creating session: {e}")
            raise

    def get_paginated_data(
        self, url: str, params: Optional[dict] = None
    ) -> Optional[List[dict]]:
        try:
            all_data = []
            while url:
                response = self.session.get(url, params=params)
                if response.status_code == 200:
                    all_data.extend(response.json())
                    url = response.links.get("next", {}).get("url")
                    if response.headers.get("X-RateLimit-Remaining", "1") == "0":
                        reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
                        sleep_time = max(reset_time - time.time(), 0)
                        logging.info(
                            f"Rate limit reached. Waiting for {sleep_time} seconds"
                        )
                        time.sleep(sleep_time)
                else:
                    logging.error(f"Error {response.status_code}: {response.text}")
                    return None
                params = None  # Clear params after first request
            return all_data
        except Exception as e:
            logging.error(f"Error fetching paginated data from {url}: {e}")
            return None

    def get_latest_release(self, username: str, repo_name: str) -> Optional[Dict]:
        try:
            url = f"{self.config.base_url}/repos/{username}/{repo_name}/releases/latest"
            response = self.session.get(url)
            if response.status_code == 200:
                release_data = response.json()
                return {
                    "tag_name": release_data["tag_name"],
                    "asset_urls": [
                        asset["browser_download_url"]
                        for asset in release_data.get("assets", [])
                    ],
                }
            logging.warning(f"No latest release found for {username}/{repo_name}")
            return None
        except Exception as e:
            logging.error(
                f"Error getting latest release for {username}/{repo_name}: {e}"
            )
            return None

    def get_all_releases(self, username: str, repo_name: str) -> Optional[List[str]]:
        try:
            url = f"{self.config.base_url}/repos/{username}/{repo_name}/releases"
            releases = self.get_paginated_data(url, {"per_page": self.config.per_page})
            if releases:
                return [release["tag_name"] for release in releases]
            logging.warning(f"No releases found for {username}/{repo_name}")
            return None
        except Exception as e:
            logging.error(f"Error getting all releases for {username}/{repo_name}: {e}")
            return None


class GitHubAPILegacy(GitHubAPIBase):
    def __init__(self):
        super().__init__()


class GitHubURLProcessor:
    @staticmethod
    def extract_github_info(url: str) -> Optional[Tuple[str, str]]:
        try:
            if "github.com" in url:
                match = re.search(r"github\.com/([^/]+/[^/]+)/", url)
                if match:
                    repo_path = match.group(1)
                    username, repo = repo_path.split("/")
                    return username, repo
            return None
        except Exception as e:
            logging.error(f"Error extracting GitHub info from URL {url}: {e}")
            return None

    @staticmethod
    def get_installer_extension(url: str) -> Optional[str]:
        try:
            extension = url.split(".")[-1].lower()
            if extension in [
                "msixbundle",
                "appxbundle",
                "msix",
                "appx",
                "zip",
                "msi",
                "exe",
            ]:
                return extension
            return None
        except Exception as e:
            logging.error(f"Error getting installer extension from URL {url}: {e}")
            return None


class ManifestProcessor:
    @staticmethod
    def load_manifest(file_path: str) -> Optional[Dict]:
        """Load and parse a YAML manifest file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            logging.error(f"Error loading manifest {file_path}: {e}")
            return None

    @staticmethod
    def save_manifest(file_path: str, data: Dict) -> bool:
        """Save manifest data to a YAML file."""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(data, f, allow_unicode=True)
            return True
        except Exception as e:
            logging.error(f"Error saving manifest {file_path}: {e}")
            return False

    @staticmethod
    def extract_package_info(manifest: Dict) -> Tuple[str, str, str]:
        """Extract package identifier, publisher, and name from manifest."""
        try:
            package_identifier = manifest.get("PackageIdentifier", "")
            publisher = manifest.get("Publisher", "")
            name = manifest.get("PackageName", "")
            return package_identifier, publisher, name
        except Exception as e:
            logging.error(f"Error extracting package info: {e}")
            return "", "", ""


def compare_versions(current: str, latest: str) -> bool:
    """Compare version strings to determine if an update is available."""

    def normalize_version(version: str) -> List[int]:
        # Remove common prefixes and convert to numeric components
        version = version.lower().strip().replace("v", "")
        return [
            int("".join(filter(str.isdigit, part)))
            for part in version.split(".")
            if any(c.isdigit() for c in part)
        ]

    try:
        current_parts = normalize_version(current)
        latest_parts = normalize_version(latest)

        # Pad shorter version with zeros
        max_length = max(len(current_parts), len(latest_parts))
        current_parts.extend([0] * (max_length - len(current_parts)))
        latest_parts.extend([0] * (max_length - len(latest_parts)))

        return latest_parts > current_parts
    except Exception as e:
        logging.error(f"Error comparing versions {current} and {latest}: {e}")
        return False
