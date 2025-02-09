import os
import yaml
import json
import re
import polars as pl
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from functools import partial

@dataclass
class Config:
    base_directory: Path = Path("winget-pkgs/manifests/")
    output_urls: Path = Path("data/urls.txt")
    output_data: Path = Path("data/GitHub_Release.csv")
    allowed_extensions: List[str] = None

    def __post_init__(self):
        self.allowed_extensions = ["msixbundle", "appxbundle", "msix", "appx", "zip", "msi", "exe"]

class GitHubReleaseProcessor:
    def __init__(self, config: Config):
        self.config = config
        self.schema = [
            ("username", str),
            ("reponame", str),
            ("latest_ver", str),
            ("extension", str),
            ("pkgs_name", str),
            ("pkg_pattern", str),
            ("version_pattern_match", str)
        ]
        self.df = pl.DataFrame([], schema=self.schema)
        self.installer_urls: List[str] = []

    @staticmethod
    def version_key(version: str) -> List[Any]:
        return [int(x) if x.isdigit() else x for x in re.split(r'([0-9]+)', version)]

    @staticmethod
    def is_dot_number_string(text: str) -> bool:
        return bool(re.match(r'^[\d.]+$', text))

    def determine_version_pattern(self, first_element: str, url_ext: str) -> str:
        if first_element in url_ext:
            if self.is_dot_number_string(first_element):
                return "PatternMatchOnlyNum"
            if first_element.startswith(("v", "r")) and self.is_dot_number_string(first_element[1:]):
                return f"PatternMatchStartWith{first_element[0]}"
            return "PatternMatchExact"

        if url_ext.count('.') - 1 > first_element.count('.'):
            if "-" in first_element:
                string1 = re.sub(r'(\d+(?:\.\d+)*)-', r'\1.0-', first_element)
                if string1 in url_ext:
                    return "DiffMatchDotZeroIncrease"
        elif url_ext.count('.') - 1 < first_element.count('.'):
            if "-" in first_element:
                pattern = r'(\d+)(?:\.\d+)*(-)'
                string1 = re.sub(pattern, 
                               lambda x: x.group(1) + ".0" + x.group(2) if "." not in x.group(1) else x.group(0), 
                               first_element)
                if string1 in url_ext:
                    return "DiffMatchDotZeroReduce"
        return "different"

    def process_installer(self, installer: Dict[str, Any], first_element: str) -> Optional[Dict[str, Any]]:
        if 'InstallerUrl' not in installer or 'https://github.com' not in installer['InstallerUrl']:
            return None

        url = installer['InstallerUrl']
        parts = url.split("/")
        url_ext = parts[-1]
        extension = url_ext.split(".")[-1]

        if extension not in self.config.allowed_extensions:
            return None

        match = re.search(r"https://github\.com/([^/]+)/([^/]+)/", url)
        if not match:
            return None

        return {
            'url': url,
            'username': match.group(1),
            'repo_name': match.group(2),
            'extension': extension,
            'url_ext': url_ext,
            'version_pattern': self.determine_version_pattern(first_element, url_ext)
        }

    def process_yaml_file(self, file_path: Path, dotrow: str, first_element: str) -> None:
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file) if file_path.suffix == '.json' else yaml.safe_load(file)

            if 'Installers' not in data:
                return

            installers = [self.process_installer(installer, first_element) 
                         for installer in data['Installers']]
            installers = [i for i in installers if i]

            if len(installers) == 1:
                installer = installers[0]
                self.installer_urls.append(installer['url'])
                
                df_row = pl.DataFrame({
                    "username": installer['username'],
                    "reponame": installer['repo_name'],
                    "latest_ver": first_element,
                    "extension": installer['extension'],
                    "pkgs_name": dotrow[:-1],
                    "pkg_pattern": installer['url_ext'],
                    "version_pattern_match": installer['version_pattern']
                })
                self.df.extend(df_row)

        except Exception as e:
            print(f"Error processing {file_path}: {e}")

    def process_directory(self, row: List[str]) -> None:
        row = [element for element in row if element]
        slashrow = "/".join(row) + "/"
        dotrow = ".".join(row) + "."
        directory_path = self.config.base_directory / f"{slashrow[0].lower()}" / slashrow

        try:
            subdirectories = sorted(
                [d for d in os.listdir(directory_path) if (directory_path / d).is_dir()],
                key=self.version_key,
                reverse=True
            )

            if not subdirectories:
                return

            first_element = subdirectories[0]
            file_path = directory_path / first_element / f'{dotrow}installer.yaml'
            
            if file_path.exists():
                self.process_yaml_file(file_path, dotrow, first_element)

        except Exception as e:
            print(f"Error processing directory {directory_path}: {e}")

    def process_csv(self, csv_path: Path) -> None:
        df = pl.read_csv(csv_path)
        rows = df.to_numpy().tolist()

        with ThreadPoolExecutor() as executor:
            executor.map(self.process_directory, rows)

    def save_results(self) -> None:
        self.df.write_csv(self.config.output_data)
        
        with open(self.config.output_urls, 'w') as file:
            file.write('\n'.join(self.installer_urls))

def main():
    config = Config()
    processor = GitHubReleaseProcessor(config)
    processor.process_csv(Path("data/filenames.csv"))
    processor.save_results()

if __name__ == "__main__":
    main()