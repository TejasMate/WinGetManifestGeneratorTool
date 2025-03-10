import os
import re
import requests
import polars as pl
from typing import List, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path

@dataclass
class ReleaseInfo:
    """Data class to store release information."""
    username: str
    reponame: str
    latest_ver: str
    extension: str
    pkgs_name: str
    pkg_pattern: str
    version_pattern_match: str
    update_requires: str
    github_latest_vers: str
    github_earliest_vers: str
    is_earliest_ver_releases: str

class FileModifier:
    """Handles file modification operations."""
    
    @staticmethod
    def modify_file(input_file: str, output_file: str, string_to_add: str) -> None:
        """
        Modify a file by adding a string to each line.
        
        Args:
            input_file: Path to the input file
            output_file: Path to the output file
            string_to_add: String to append to each line
        """
        try:
            with open(input_file, 'r') as f_in, open(output_file, 'w') as f_out:
                for line in f_in:
                    modified_line = f"{line.rstrip()}{string_to_add}\n"
                    f_out.write(modified_line)
        except IOError as e:
            raise IOError(f"Error modifying file: {e}")

class StringValidator:
    """Handles string validation operations."""
    
    @staticmethod
    def is_valid_version_tag(string: str) -> bool:
        """
        Check if string starts with 'v' and contains only letters.
        
        Args:
            string: String to validate
            
        Returns:
            bool: True if string is valid version tag
        """
        if not string:
            return False
        
        first_char = string[0].lower()
        if first_char != 'v':
            return False
            
        second_char = string[1] if len(string) > 1 else ''
        if '.' in second_char:
            return False
            
        filtered_string = ''.join(char for char in string if char.isalpha())
        return filtered_string == 'v' and len(filtered_string) == 1

    @staticmethod
    def is_numeric_string(string: str) -> bool:
        """Check if string contains only numbers and dots."""
        return bool(re.fullmatch(r'[0-9.]+', string))

    @staticmethod
    def contains_substrings(value: str, string1: str, string2: str) -> bool:
        """Check if both substrings are in the value."""
        return string1 in value and string2 in value

class GitHubReleaseProcessor:
    """Processes GitHub releases and generates komac commands."""
    
    def __init__(self, token: str):
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
    def get_release_info(self, release: ReleaseInfo) -> Optional[List[str]]:
        """
        Get release information from GitHub API.
        
        Args:
            release: ReleaseInfo object containing release details
            
        Returns:
            Optional[List[str]]: List of download URLs if successful, None otherwise
        """
        release_tag = release.github_latest_vers
        if not release_tag:
            return None
            
        if not (StringValidator.is_valid_version_tag(release_tag.lower()) or 
                StringValidator.is_numeric_string(release_tag)):
            return None
            
        url = f"https://api.github.com/repos/{release.username}/{release.reponame}/releases/tags/{release_tag}"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            if not data:
                print(f"No releases found for {release.username}/{release.reponame} with tag {release_tag}")
                return None
                
            return [asset["browser_download_url"] for asset in data["assets"]]
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching release info: {e}")
            return None

def main():
    """Main function to process releases and generate commands."""
    # Load environment variables and data
    token = os.environ.get("TOKEN")
    if not token:
        raise ValueError("GitHub token not found in environment variables")
        
    data_dir = Path("data")
    
    # Read and process data
    try:
        df_issues = pl.read_csv(data_dir / "OpenPRs.csv")
        df = pl.read_csv(data_dir / "GitHub_Releasess.csv")
        
        # Filter releases
        df_new = df.filter(
            (pl.col('update_requires') == 'Yes') & 
            (pl.col('extension') != 'zip')
        )
        df_new.write_csv(data_dir / "GitHub_Releasessss.csv")
        
        # Process releases
        processor = GitHubReleaseProcessor(token)
        commands = []
        
        for row in df_new.rows():
            # Create ReleaseInfo object with all columns
            release = ReleaseInfo(*row)
            download_urls = processor.get_release_info(release)
            
            if not download_urls:
                continue
                
            # Filter URLs by extension
            proper_urls = [url for url in download_urls if f".{release.extension}" in url]
            if len(proper_urls) != 1:
                continue
                
            # Process version information
            komac_version = release.github_latest_vers.lower().replace('v', '')
            
            # Check if already processed
            if any(StringValidator.contains_substrings(value, release.pkgs_name, komac_version) 
                   for value in df_issues['Title']):
                continue
                
            # Generate command
            command = (f"komac update {release.pkgs_name} --version {komac_version} "
                      f"--urls {proper_urls[0]} --submit --token")
            commands.append(command)
        
        # Write commands to file
        output_file = "komac_commands.sh"
        with open(output_file, "w") as file:
            file.write("\n".join(commands))
            
        print(f"Successfully generated {len(commands)} commands in {output_file}")
        
    except Exception as e:
        print(f"An error occurred: {e}")
        raise

if __name__ == "__main__":
    main()