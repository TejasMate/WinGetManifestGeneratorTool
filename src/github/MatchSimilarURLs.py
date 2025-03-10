import pandas as pd
import re
from pathlib import Path

def extract_extensions_from_archext(archext_str):
    if pd.isna(archext_str) or archext_str == '':
        return set()
    
    extensions = set()
    pairs = archext_str.split(',')
    
    for pair in pairs:
        pair = pair.strip()
        if pair.startswith('NA-'):
            # For NA- patterns, only consider the extension
            ext = pair.split('-')[1] if len(pair.split('-')) > 1 else ''
            if ext:
                extensions.add(ext)
    
    return extensions

def filter_github_urls(row):

    if pd.isna(row['LatestGitHubURLs']) or pd.isna(row['ArchExtPairs']):
        return row['LatestGitHubURLs']
    
    github_urls = row['LatestGitHubURLs'].split(',')
    valid_extensions = extract_extensions_from_archext(row['ArchExtPairs'])
    
    if not valid_extensions:
        return row['LatestGitHubURLs']
    
    # Filter URLs that match the extensions
    filtered_urls = []
    for url in github_urls:
        url = url.strip()
        # Extract extension from URL (assuming it's at the end of the URL)
        url_ext_match = re.search(r'\.([^.]+)$', url)
        if url_ext_match:
            url_ext = url_ext_match.group(1)
            if url_ext in valid_extensions:
                filtered_urls.append(url)
    
    return ','.join(filtered_urls) if filtered_urls else row['LatestGitHubURLs']

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
        df['LatestGitHubURLs'] = df.apply(filter_github_urls, axis=1)
        
        # Create output directory if it doesn't exist
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Save the updated data
        df.to_csv(output_path, index=False)
        
    except Exception as e:
        raise Exception(f"Error processing URLs: {str(e)}")

def main():
    # Example usage when run as script
    input_path = '../../data/GitHubPackageInfo.csv'
    output_path = 'GitHubPackageInfo_CleanedURLs.csv'
    process_urls(input_path, output_path)

if __name__ == "__main__":
    main()