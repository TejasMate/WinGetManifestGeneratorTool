import requests
import polars as pl
from pathlib import Path
from typing import Optional, Tuple, List
from dataclasses import dataclass
import os
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

@dataclass
class GitHubConfig:
    token: str
    base_url: str = "https://api.github.com"
    per_page: int = 100
    retry_attempts: int = 3
    retry_backoff: float = 0.5
    
class GitHubAPI:
    def __init__(self, config: GitHubConfig):
        self.config = config
        self.session = self._create_session()
        
    def _create_session(self) -> requests.Session:
        session = requests.Session()
        retry_strategy = Retry(
            total=self.config.retry_attempts,
            backoff_factor=self.config.retry_backoff,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.headers.update({
            "Authorization": f"token {self.config.token}",
            "Accept": "application/vnd.github.v3+json"
        })
        return session

    def get_paginated_data(self, url: str, params: Optional[dict] = None) -> Optional[List[dict]]:
        all_data = []
        while url:
            response = self.session.get(url, params=params)
            if response.status_code == 200:
                all_data.extend(response.json())
                url = response.links.get("next", {}).get("url")
                if response.headers.get('X-RateLimit-Remaining', '1') == '0':
                    reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
                    sleep_time = max(reset_time - time.time(), 0)
                    time.sleep(sleep_time)
            else:
                print(f"Error {response.status_code}: {response.text}")
                return None
            params = None  # Clear params after first request
        return all_data

    def get_latest_release(self, username: str, repo_name: str) -> Optional[str]:
        url = f"{self.config.base_url}/repos/{username}/{repo_name}/releases/latest"
        response = self.session.get(url)
        if response.status_code == 200:
            return response.json()["tag_name"]
        return None

    def get_all_releases(self, username: str, repo_name: str) -> Optional[List[str]]:
        url = f"{self.config.base_url}/repos/{username}/{repo_name}/releases"
        releases = self.get_paginated_data(url, {"per_page": self.config.per_page})
        return [release["tag_name"] for release in releases] if releases else None

class ReleaseChecker:
    def __init__(self, github_api: GitHubAPI):
        self.github_api = github_api

    def check_versions(self, username: str, reponame: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        latest_version = self.github_api.get_latest_release(username, reponame)
        versions = self.github_api.get_all_releases(username, reponame)
        
        early_lat_ver = None
        early_versions = None
        
        if versions:
            early_versions = "absent" if versions[0] == latest_version else "present"
            early_lat_ver = versions[0]
            
        return latest_version, early_lat_ver, early_versions

    def process_dataframe(self, input_path: Path, output_path: Path) -> None:
        df = pl.read_csv(input_path)
        df_filtered = df.filter(pl.col('version_pattern_match') == 'PatternMatchOnlyNum')
        
        results = []
        for row in df_filtered.rows():
            username, reponame, winget_latest_ver = row[0], row[1], row[2]
            github_latest_ver, ear_lat_version, early_versions = self.check_versions(username, reponame)
            
            update_require = self._determine_update_requirement(
                winget_latest_ver, github_latest_ver, ear_lat_version
            )
            
            results.append({
                "github_latest_ver": github_latest_ver,
                "update_require": update_require,
                "ear_lat_version": ear_lat_version,
                "early_versions": early_versions
            })
            
        df_updated = df_filtered.with_columns([
            pl.Series(name="update_requires", values=[r["update_require"] for r in results]),
            pl.Series(name="github_latest_vers", values=[r["github_latest_ver"] for r in results]),
            pl.Series(name="github_earliest_vers", values=[r["ear_lat_version"] for r in results]),
            pl.Series(name="IsEarliestVerReleases", values=[r["early_versions"] for r in results])
        ])
        
        df_updated.write_csv(output_path)

    @staticmethod
    def _determine_update_requirement(winget_ver: str, github_latest: Optional[str], github_earliest: Optional[str]) -> str:
        if not github_earliest:
            return "NA"
            
        if winget_ver.lower() in github_earliest.lower():
            return "No"
            
        if github_latest and winget_ver.lower() in github_latest.lower():
            return "No"
            
        return "Yes"

def main():
    token = os.environ.get("TOKEN")
    if not token:
        raise RuntimeError("TOKEN environment variable not set")
        
    config = GitHubConfig(token=token)
    github_api = GitHubAPI(config)
    checker = ReleaseChecker(github_api)
    
    checker.process_dataframe(
        input_path=Path("data/GitHub_Release.csv"),
        output_path=Path("data/GitHub_Releasess.csv")
    )

if __name__ == "__main__":
    main()