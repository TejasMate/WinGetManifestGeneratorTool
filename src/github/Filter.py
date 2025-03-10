import pandas as pd
from pathlib import Path

def has_matching_urls(row):
    if pd.isna(row['LatestVersionURLsInWinGet']) or pd.isna(row['LatestGitHubURLs']):
        return False
    winget_urls = str(row['LatestVersionURLsInWinGet']).split(',')
    github_urls = str(row['LatestGitHubURLs']).split(',')
    return any(url.strip() in [gh_url.strip() for gh_url in github_urls] for url in winget_urls)

def normalize_version(version):
    if pd.isna(version):
        return ''
    version = str(version).lower()
    # Remove common version prefixes
    prefixes = ['v', 'ver', 'version']
    for prefix in prefixes:
        if version.startswith(prefix):
            version = version[len(prefix):].lstrip()
    # Standardize separators
    version = version.replace('+', '_')
    return version.strip()

def versions_match(ver1, ver2):
    return normalize_version(ver1) == normalize_version(ver2)

def count_github_urls(urls):
    if pd.isna(urls) or urls == '':
        return 0
    return len(str(urls).split(','))

def process_filters(input_path: str, output_dir: str) -> None:
    """Process GitHub package information through multiple filters.
    
    Args:
        input_path (str): Path to the input CSV file
        output_dir (str): Directory where filtered results will be saved
    
    Raises:
        FileNotFoundError: If input file doesn't exist
        PermissionError: If there are permission issues with input/output files
    """
    try:
        # Ensure input file exists
        if not Path(input_path).exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        # Create output directory if it doesn't exist
        output_dir_path = Path(output_dir)
        output_dir_path.mkdir(parents=True, exist_ok=True)
        
        # Read the original CSV file
        df = pd.read_csv(input_path)
        removed_rows = pd.DataFrame(columns=df.columns.tolist() + ['reason'])

        # Filter 1: Remove rows with "Not Found" in GitHubLatest
        filter1_removed = df[df['GitHubLatest'] == 'Not Found'].copy()
        filter1_removed['reason'] = 'filter 1'
        df = df[df['GitHubLatest'] != 'Not Found']
        removed_rows = pd.concat([removed_rows, filter1_removed])
        df.to_csv(output_dir_path / 'GitHubPackageInfo_Filter1.csv', index=False)

        # Filter 2: Remove rows where LatestGitHubURLs is empty
        filter2_removed = df[df['LatestGitHubURLs'].isna() | (df['LatestGitHubURLs'] == '')].copy()
        filter2_removed['reason'] = 'filter 2'
        df = df[~(df['LatestGitHubURLs'].isna() | (df['LatestGitHubURLs'] == ''))]
        removed_rows = pd.concat([removed_rows, filter2_removed])
        df.to_csv(output_dir_path / 'GitHubPackageInfo_Filter2.csv', index=False)

        # Filter 3: Remove rows where HasOpenPullRequests is Yes
        filter3_removed = df[df['HasOpenPullRequests'] == 'present'].copy()
        filter3_removed['reason'] = 'filter 3'
        df = df[df['HasOpenPullRequests'] != 'present']
        removed_rows = pd.concat([removed_rows, filter3_removed])
        df.to_csv(output_dir_path / 'GitHubPackageInfo_Filter3.csv', index=False)

        # Filter 4: Remove rows where ArchExtPairs is empty
        filter4_removed = df[df['ArchExtPairs'].isna() | (df['ArchExtPairs'] == '')].copy()
        filter4_removed['reason'] = 'filter 4'
        df = df[~(df['ArchExtPairs'].isna() | (df['ArchExtPairs'] == ''))]
        removed_rows = pd.concat([removed_rows, filter4_removed])
        df.to_csv(output_dir_path / 'GitHubPackageInfo_Filter4.csv', index=False)

        # Filter 5: Remove rows where URLs match
        filter5_removed = df[df.apply(has_matching_urls, axis=1)].copy()
        filter5_removed['reason'] = 'filter 5'
        df = df[~df.apply(has_matching_urls, axis=1)]
        removed_rows = pd.concat([removed_rows, filter5_removed])
        df.to_csv(output_dir_path / 'GitHubPackageInfo_Filter5.csv', index=False)

        # Filter 6: Remove rows where versions match exactly
        filter6_removed = df[df['CurrentLatestVersionInWinGet'] == df['GitHubLatest']].copy()
        filter6_removed['reason'] = 'filter 6'
        df = df[df['CurrentLatestVersionInWinGet'] != df['GitHubLatest']]
        removed_rows = pd.concat([removed_rows, filter6_removed])
        df.to_csv(output_dir_path / 'GitHubPackageInfo_Filter6.csv', index=False)

        # Filter 7: Remove rows where versions match after normalization
        filter7_removed = df[df.apply(lambda row: versions_match(row['CurrentLatestVersionInWinGet'], row['GitHubLatest']), axis=1)].copy()
        filter7_removed['reason'] = 'filter 7'
        df = df[~df.apply(lambda row: versions_match(row['CurrentLatestVersionInWinGet'], row['GitHubLatest']), axis=1)]
        removed_rows = pd.concat([removed_rows, filter7_removed])
        df.to_csv(output_dir_path / 'GitHubPackageInfo_Filter7.csv', index=False)

        # Filter 8: Remove rows where URL counts don't match
        filter8_removed = df[df.apply(lambda row: count_github_urls(row['LatestGitHubURLs']) != row['InstallerURLsCount'], axis=1)].copy()
        filter8_removed['reason'] = 'filter 8'
        df = df[~df.apply(lambda row: count_github_urls(row['LatestGitHubURLs']) != row['InstallerURLsCount'], axis=1)]
        removed_rows = pd.concat([removed_rows, filter8_removed])
        df.to_csv(output_dir_path / 'GitHubPackageInfo_Filter8.csv', index=False)

        # Save removed rows to a separate CSV file
        removed_rows.to_csv(output_dir_path / 'RemovedRows.csv', index=False)
        
    except Exception as e:
        raise Exception(f"Error processing filters: {str(e)}")

def main():
    # Example usage when run as script
    input_path = 'data/GitHubPackageInfo_CleanedURLs.csv'
    output_dir = 'filtered_results'
    process_filters(input_path, output_dir)

if __name__ == "__main__":
    main()