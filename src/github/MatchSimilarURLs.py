import pandas as pd
import re
from pathlib import Path


def extract_extensions_from_url_patterns(url_patterns_str):
    """Extract file extensions from URL patterns (e.g., 'x64-exe,setup-x86_64-msi' -> {'exe', 'msi'})"""
    if pd.isna(url_patterns_str) or url_patterns_str == "":
        return set()

    extensions = set()
    patterns = url_patterns_str.split(",")

    for pattern in patterns:
        pattern = pattern.strip()
        if pattern:
            # Split by hyphens and take the last part as the extension
            parts = pattern.split("-")
            if len(parts) > 0:
                ext = parts[-1]  # Last part should be the extension
                if ext and not ext.isdigit():  # Skip if it's just a number
                    extensions.add(ext)

    return extensions


def filter_github_urls(row):

    if pd.isna(row["LatestGitHubURLs"]) or pd.isna(row["URLPatterns"]):
        return row["LatestGitHubURLs"]

    github_urls = row["LatestGitHubURLs"].split(",")
    valid_extensions = extract_extensions_from_url_patterns(row["URLPatterns"])

    if not valid_extensions:
        return row["LatestGitHubURLs"]

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

    return ",".join(filtered_urls) if filtered_urls else row["LatestGitHubURLs"]


def process_urls(input_path: str, output_path: str) -> None:
    """Process GitHub URLs from input CSV and save filtered results to output CSV.

    Args:
        input_path (str): Path to the input CSV file
        output_path (str): Path where the filtered results will be saved

    Raises:
        FileNotFoundError: If input file doesn't exist
        PermissionError: If there are permission issues with input/output files
    """
    try:
        # Ensure input file exists
        if not Path(input_path).exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        # Read the CSV file
        df = pd.read_csv(input_path)

        # Apply the filtering
        df["LatestGitHubURLs"] = df.apply(filter_github_urls, axis=1)

        # Create output directory if it doesn't exist
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # Save the updated data
        df.to_csv(output_path, index=False)

    except Exception as e:
        raise Exception(f"Error processing URLs: {str(e)}")


def main():
    # Example usage when run as script
    input_path = "../../data/GitHubPackageInfo.csv"
    output_path = "GitHubPackageInfo_CleanedURLs.csv"
    process_urls(input_path, output_path)


if __name__ == "__main__":
    main()
