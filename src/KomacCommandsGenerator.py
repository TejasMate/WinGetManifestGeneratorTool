import logging
from pathlib import Path
import polars as pl

# Handle both relative and absolute imports
try:
    from .config import get_config
except ImportError:
    # Fallback for direct script execution
    import sys
    from pathlib import Path
    current_dir = Path(__file__).parent
    sys.path.append(str(current_dir))
    from config import get_config


def generate_komac_commands_github(input_path: Path = None, output_path: Path = None) -> None:
    try:
        # Load configuration
        config = get_config()
        package_config = config.get('package_processing', {})
        output_dir = package_config.get('output_directory', 'data')
        
        # Use config-based paths if not provided
        if input_path is None:
            input_path = Path(output_dir) / "github" / "GitHubPackageInfo_Filter8.csv"
        if output_path is None:
            output_path = Path(output_dir) / "github" / "komac_update_commands_github.txt"
        
        # Read the GitHub package info CSV file
        df = pl.read_csv(input_path)
        logging.info(f"Loaded {len(df)} entries from {input_path}")

        # Open output file for writing commands
        with open(output_path, "w") as f:
            for row in df.iter_rows(named=True):
                package_name = row["PackageIdentifier"]
                github_latest = row["GitHubLatest"].lstrip("vV")
                latest_urls = row["LatestGitHubURLs"]

                if not all([package_name, github_latest, latest_urls]):
                    logging.warning(f"Skipping incomplete entry for {package_name}")
                    continue

                # Replace comma with space for multiple URLs
                urls_for_command = latest_urls.replace(',', ' ')

                # Format the komac update command
                command = f"komac update {package_name} --version {github_latest} --urls {urls_for_command}"
                f.write(command + "\n")
                logging.info(f"Generated command for {package_name}")

        logging.info(f"Commands written to {output_path}")

    except Exception as e:
        logging.error(f"Error generating komac commands: {e}")
        raise


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # Generate commands using config-based paths
    generate_komac_commands_github()
    logging.info("Command generation completed successfully")
