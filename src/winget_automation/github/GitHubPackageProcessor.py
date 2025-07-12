import polars as pl
import logging
import re
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass
from ..utils.token_manager import TokenManager
from ..utils.unified_utils import GitHubAPI, GitHubConfig, GitHubURLProcessor
from concurrent.futures import ThreadPoolExecutor
import json

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


@dataclass
class VersionAnalyzer:
    def __init__(self, github_api: GitHubAPI):
        self.github_api = github_api
        self.github_repos = {}

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

    def process_package(self, row: List) -> Dict:
        package_name = row[0]  # PackageIdentifier
        versions = row[1]  # AvailableVersions
        version_pattern = row[2]  # VersionFormatPattern
        latest_version = row[3]  # CurrentLatestVersioninWinGet
        download_urls_count = row[4]  # InstallerURLsCount
        installer_urls = row[5]  # LatestVersionURLsinWinGet
        arch_ext_pairs = row[6]  # ArchExtPairs
        open_prs = row[7]  # HasOpenPullRequests

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
                    "GitHubRepo": "",
                    "AvailableVersions": versions,
                    "VersionFormatPattern": version_pattern,
                    "CurrentLatestVersionInWinGet": latest_version,
                    "InstallerURLsCount": download_urls_count,
                    "LatestVersionURLsInWinGet": installer_urls,
                    "ArchExtPairs": arch_ext_pairs,
                    "HasOpenPullRequests": open_prs,
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

            # Filter URLs based on extensions from arch_ext_pairs
            if latest_release and arch_ext_pairs:
                all_urls = [
                    url.replace("%2B", "+")
                    for url in latest_release.get("asset_urls", [])
                ]
                filtered_urls = []

                # Extract extensions from arch_ext_pairs
                valid_extensions = set()
                for pair in arch_ext_pairs.split(","):
                    if pair:
                        parts = pair.rsplit("-", 1)
                        if len(parts) == 2:
                            _, ext = parts
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

            return {
                "PackageIdentifier": package_name,
                "GitHubRepo": github_repo,
                "AvailableVersions": versions,
                "VersionFormatPattern": version_pattern,
                "CurrentLatestVersionInWinGet": latest_version,
                "InstallerURLsCount": download_urls_count,
                "LatestVersionURLsInWinGet": installer_urls,
                "ArchExtPairs": arch_ext_pairs,
                "HasOpenPullRequests": open_prs,
                "GitHubLatest": (
                    latest_version_github if latest_version_github else "Not found"
                ),
                "LatestGitHubURLs": latest_github_urls,
            }

        except Exception as e:
            logging.error(f"Error processing {package_name}: {e}")
            return {
                "PackageIdentifier": package_name,
                "GitHubRepo": github_repo if github_repo else "",
                "AvailableVersions": versions,
                "VersionFormatPattern": version_pattern,
                "CurrentLatestVersionInWinGet": latest_version,
                "InstallerURLsCount": download_urls_count,
                "LatestVersionURLsInWinGet": installer_urls,
                "ArchExtPairs": arch_ext_pairs,
                "HasOpenPullRequests": open_prs,
                "GitHubLatest": (
                    latest_version_github if latest_version_github else "Not found"
                ),
                "LatestGitHubURLs": latest_github_urls,
            }

    def analyze_versions(self, input_path: Path, output_path: Path) -> None:
        try:
            # Read and process package info
            df = pl.read_csv(input_path)

            # Read blocked packages
            block_packages_path = Path("../../package_blocklist.json")
            if block_packages_path.exists():
                with open(block_packages_path, "r") as f:
                    blocked_packages = set(json.load(f)["blocked_packages"])
                # Filter out blocked packages
                df = df.filter(~pl.col("PackageIdentifier").is_in(blocked_packages))

            # Filter for packages with GitHub URLs
            df_filtered = df.filter(
                pl.col("LatestVersionURLsInWinGet").str.contains("github.com")
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
