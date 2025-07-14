import logging
from pathlib import Path
import polars as pl


def generate_komac_commands_github(input_path: Path, output_path: Path) -> None:
    try:
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

                # Format the komac update command
                command = f"komac update {package_name} --version {github_latest} --urls {latest_urls}"
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

    # Set up paths
    input_path = Path("data/github/GitHubPackageInfo_Filter8.csv")
    output_path = Path("data/github/komac_update_commands_github.txt")

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    generate_komac_commands_github(input_path, output_path)
    logging.info("Command generation completed successfully")
