import pandas as pd
from pathlib import Path
import logging


def has_matching_urls(row):
    if pd.isna(row["LatestVersionURLsInWinGet"]) or pd.isna(row["LatestGitHubURLs"]):
        return False
    winget_urls = str(row["LatestVersionURLsInWinGet"]).split(",")
    github_urls = str(row["LatestGitHubURLs"]).split(",")
    return any(
        url.strip() in [gh_url.strip() for gh_url in github_urls] for url in winget_urls
    )


def normalize_version(version):
    if pd.isna(version):
        return ""
    version = str(version).lower()
    # Remove common version prefixes
    prefixes = ["v", "ver", "version"]
    for prefix in prefixes:
        if version.startswith(prefix):
            version = version[len(prefix) :].lstrip()
    # Standardize separators
    version = version.replace("+", "_")
    return version.strip()


def versions_match(ver1, ver2):
    return normalize_version(ver1) == normalize_version(ver2)


def count_github_urls(urls):
    if pd.isna(urls) or urls == "":
        return 0
    return len(str(urls).split(","))


def process_filters(input_path: str, output_dir: str) -> None:
    """Process GitHub package information through multiple filters.

    Args:
        input_path (str): Path to the input CSV file
        output_dir (str): Directory where filtered results will be saved

    Raises:
        FileNotFoundError: If input file doesn't exist
        PermissionError: If there are permission issues with input/output files
    """
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    try:
        # Ensure input file exists
        if not Path(input_path).exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        # Create output directory if it doesn't exist
        output_dir_path = Path(output_dir)
        output_dir_path.mkdir(parents=True, exist_ok=True)

        # Read the original CSV file
        df = pd.read_csv(input_path)
        initial_count = len(df)
        logging.info(f"Starting filter process with {initial_count} packages from {input_path}")
        
        # Clean column names to remove any invisible characters or extra spaces
        df.columns = df.columns.str.strip()
        
        removed_rows = pd.DataFrame(columns=df.columns.tolist() + ["reason"])

        # Filter 1: Remove rows with "Not Found" in GitHubLatest
        filter1_removed = df[df["GitHubLatest"] == "Not Found"].copy()
        filter1_removed["reason"] = "No GitHub release found"
        df = df[df["GitHubLatest"] != "Not Found"]
        removed_rows = pd.concat([removed_rows, filter1_removed])
        df.to_csv(output_dir_path / "GitHubPackageInfo_Filter1.csv", index=False)
        # Save removed rows from Filter 1
        if not filter1_removed.empty:
            filter1_removed.to_csv(output_dir_path / "Filter1_Removed.csv", index=False)
            logging.info(f"Filter 1: Removed {len(filter1_removed)} rows (No GitHub release found) -> Filter1_Removed.csv")

        # Filter 2: Remove rows where LatestGitHubURLs is empty
        filter2_removed = df[
            df["LatestGitHubURLs"].isna() | (df["LatestGitHubURLs"] == "")
        ].copy()
        filter2_removed["reason"] = "No GitHub download URLs"
        df = df[~(df["LatestGitHubURLs"].isna() | (df["LatestGitHubURLs"] == ""))]
        removed_rows = pd.concat([removed_rows, filter2_removed])
        df.to_csv(output_dir_path / "GitHubPackageInfo_Filter2.csv", index=False)
        # Save removed rows from Filter 2
        if not filter2_removed.empty:
            filter2_removed.to_csv(output_dir_path / "Filter2_Removed.csv", index=False)
            logging.info(f"Filter 2: Removed {len(filter2_removed)} rows (No GitHub download URLs) -> Filter2_Removed.csv")
        removed_rows = pd.concat([removed_rows, filter2_removed])
        df.to_csv(output_dir_path / "GitHubPackageInfo_Filter2.csv", index=False)

        # Filter 3: Remove rows where LatestVersionPullRequest is open (has open pull requests)
        filter3_removed = df[df["LatestVersionPullRequest"] == "open"].copy()
        filter3_removed["reason"] = "Has open pull requests"
        df = df[df["LatestVersionPullRequest"] != "open"]
        removed_rows = pd.concat([removed_rows, filter3_removed])
        df.to_csv(output_dir_path / "GitHubPackageInfo_Filter3.csv", index=False)
        # Save removed rows from Filter 3
        if not filter3_removed.empty:
            filter3_removed.to_csv(output_dir_path / "Filter3_Removed.csv", index=False)
            logging.info(f"Filter 3: Removed {len(filter3_removed)} rows (Has open pull requests) -> Filter3_Removed.csv")

        # Filter 4: Remove rows where ArchExtPairs is empty
        filter4_removed = df[
            df["ArchExtPairs"].isna() | (df["ArchExtPairs"] == "")
        ].copy()
        filter4_removed["reason"] = "No architecture/extension data"
        df = df[~(df["ArchExtPairs"].isna() | (df["ArchExtPairs"] == ""))]
        removed_rows = pd.concat([removed_rows, filter4_removed])
        df.to_csv(output_dir_path / "GitHubPackageInfo_Filter4.csv", index=False)
        # Save removed rows from Filter 4
        if not filter4_removed.empty:
            filter4_removed.to_csv(output_dir_path / "Filter4_Removed.csv", index=False)
            logging.info(f"Filter 4: Removed {len(filter4_removed)} rows (No architecture/extension data) -> Filter4_Removed.csv")

        # Filter 5: Remove rows where URLs match
        filter5_removed = df[df.apply(has_matching_urls, axis=1)].copy()
        filter5_removed["reason"] = "URLs already match WinGet"
        df = df[~df.apply(has_matching_urls, axis=1)]
        removed_rows = pd.concat([removed_rows, filter5_removed])
        df.to_csv(output_dir_path / "GitHubPackageInfo_Filter5.csv", index=False)
        # Save removed rows from Filter 5
        if not filter5_removed.empty:
            filter5_removed.to_csv(output_dir_path / "Filter5_Removed.csv", index=False)
            logging.info(f"Filter 5: Removed {len(filter5_removed)} rows (URLs already match WinGet) -> Filter5_Removed.csv")

        # Filter 5.5: Remove rows where GitHub URLs match ANY WinGet URLs from ALL versions
        filter5_5_mask = df["HasAnyURLMatch"] == True
        filter5_5_removed = df[filter5_5_mask].copy()
        filter5_5_removed["reason"] = "GitHub URLs match any WinGet version URLs"
        df = df[~filter5_5_mask]
        removed_rows = pd.concat([removed_rows, filter5_5_removed])
        df.to_csv(output_dir_path / "GitHubPackageInfo_Filter5_5.csv", index=False)
        # Save removed rows from Filter 5.5
        if not filter5_5_removed.empty:
            filter5_5_removed.to_csv(output_dir_path / "Filter5_5_Removed.csv", index=False)
            logging.info(f"Filter 5.5: Removed {len(filter5_5_removed)} rows (GitHub URLs match any WinGet version URLs) -> Filter5_5_Removed.csv")

        # Filter 6: Remove rows where versions match exactly
        filter6_removed = df[
            df["CurrentLatestVersionInWinGet"] == df["GitHubLatest"]
        ].copy()
        filter6_removed["reason"] = "Versions match exactly"
        df = df[df["CurrentLatestVersionInWinGet"] != df["GitHubLatest"]]
        removed_rows = pd.concat([removed_rows, filter6_removed])
        df.to_csv(output_dir_path / "GitHubPackageInfo_Filter6.csv", index=False)
        # Save removed rows from Filter 6
        if not filter6_removed.empty:
            filter6_removed.to_csv(output_dir_path / "Filter6_Removed.csv", index=False)
            logging.info(f"Filter 6: Removed {len(filter6_removed)} rows (Versions match exactly) -> Filter6_Removed.csv")

        # Filter 7: Remove rows where versions match after normalization
        filter7_removed = df[
            df.apply(
                lambda row: versions_match(
                    row["CurrentLatestVersionInWinGet"], row["GitHubLatest"]
                ),
                axis=1,
            )
        ].copy()
        filter7_removed["reason"] = "Versions match after normalization"
        df = df[
            ~df.apply(
                lambda row: versions_match(
                    row["CurrentLatestVersionInWinGet"], row["GitHubLatest"]
                ),
                axis=1,
            )
        ]
        removed_rows = pd.concat([removed_rows, filter7_removed])
        df.to_csv(output_dir_path / "GitHubPackageInfo_Filter7.csv", index=False)
        # Save removed rows from Filter 7
        if not filter7_removed.empty:
            filter7_removed.to_csv(output_dir_path / "Filter7_Removed.csv", index=False)
            logging.info(f"Filter 7: Removed {len(filter7_removed)} rows (Versions match after normalization) -> Filter7_Removed.csv")

        # Filter 8: Remove rows where URL counts don't match
        filter8_removed = df[
            df.apply(
                lambda row: count_github_urls(row["LatestGitHubURLs"])
                != row["InstallerURLsCount"],
                axis=1,
            )
        ].copy()
        filter8_removed["reason"] = "URL counts don't match"
        df = df[
            ~df.apply(
                lambda row: count_github_urls(row["LatestGitHubURLs"])
                != row["InstallerURLsCount"],
                axis=1,
            )
        ]
        removed_rows = pd.concat([removed_rows, filter8_removed])
        df.to_csv(output_dir_path / "GitHubPackageInfo_Filter8.csv", index=False)
        # Save removed rows from Filter 8
        if not filter8_removed.empty:
            filter8_removed.to_csv(output_dir_path / "Filter8_Removed.csv", index=False)
            logging.info(f"Filter 8: Removed {len(filter8_removed)} rows (URL counts don't match) -> Filter8_Removed.csv")

        # Save all removed rows to a combined CSV file
        if not removed_rows.empty:
            removed_rows.to_csv(output_dir_path / "RemovedRows.csv", index=False)
            logging.info(f"All removed rows saved to RemovedRows.csv ({len(removed_rows)} total rows)")
        
        # Generate comprehensive summary report
        try:
            generate_filter_summary(str(output_dir_path), initial_count, len(df))
            logging.info(f"Filter summary report generated: {output_dir_path}/FilteringSummary.md")
        except Exception as e:
            logging.error(f"Failed to generate filter summary: {str(e)}")
        
        # Log summary
        logging.info(f"Filtering complete. Final dataset contains {len(df)} rows after all filters applied.")
        print(f"\nFiltering Summary:")
        print(f"- Original packages: {initial_count:,}")
        print(f"- Final packages: {len(df):,}")
        print(f"- Total removed: {initial_count - len(df):,}")
        print(f"- Retention rate: {len(df) / initial_count * 100:.1f}%")
        print(f"- Detailed report: {output_dir_path}/FilteringSummary.md")

    except Exception as e:
        logging.error(f"Error processing filters: {str(e)}")
        raise Exception(f"Error processing filters: {str(e)}")


def generate_filter_summary(output_dir: str, initial_count: int, final_count: int) -> None:
    """Generate a summary report of all filters and what they removed.
    
    Args:
        output_dir (str): Directory where the summary will be saved
        initial_count (int): Initial number of packages before filtering
        final_count (int): Final number of packages after all filters
    """
    output_dir_path = Path(output_dir)
    summary_lines = [
        "# Package Filtering Summary Report",
        f"Generated on: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        f"## Overall Results",
        f"- Initial packages: {initial_count:,}",
        f"- Final packages: {final_count:,}",
        f"- Total removed: {initial_count - final_count:,}",
        f"- Retention rate: {(final_count / initial_count * 100):.1f}%",
        "",
        "## Filter Details",
        ""
    ]
    
    # Check each filter's removed file and add to summary
    filters = [
        ("Filter1_Removed.csv", "Filter 1: No GitHub release found"),
        ("Filter2_Removed.csv", "Filter 2: No GitHub download URLs"),  
        ("Filter3_Removed.csv", "Filter 3: Has open pull requests"),
        ("Filter4_Removed.csv", "Filter 4: No architecture/extension data"),
        ("Filter5_Removed.csv", "Filter 5: URLs already match WinGet"),
        ("Filter5_5_Removed.csv", "Filter 5.5: GitHub URLs match any WinGet version URLs"),
        ("Filter6_Removed.csv", "Filter 6: Versions match exactly"),
        ("Filter7_Removed.csv", "Filter 7: Versions match after normalization"),
        ("Filter8_Removed.csv", "Filter 8: URL counts don't match")
    ]
    
    total_removed_by_filters = 0
    for filename, description in filters:
        filepath = output_dir_path / filename
        if filepath.exists():
            try:
                filter_df = pd.read_csv(filepath)
                count = len(filter_df)
                total_removed_by_filters += count
                percentage = (count / initial_count * 100) if initial_count > 0 else 0
                summary_lines.append(f"### {description}")
                summary_lines.append(f"- Packages removed: {count:,}")
                summary_lines.append(f"- Percentage of original: {percentage:.1f}%")
                summary_lines.append(f"- Output file: `{filename}`")
                summary_lines.append("")
            except Exception as e:
                summary_lines.append(f"### {description}")
                summary_lines.append(f"- Error reading file: {str(e)}")
                summary_lines.append("")
    
    summary_lines.extend([
        "## Files Generated",
        "",
        "### Filtered Results (Remaining Packages)",
        "- `GitHubPackageInfo_Filter1.csv` - After removing packages with no GitHub releases",
        "- `GitHubPackageInfo_Filter2.csv` - After removing packages with no GitHub URLs", 
        "- `GitHubPackageInfo_Filter3.csv` - After removing packages with open PRs",
        "- `GitHubPackageInfo_Filter4.csv` - After removing packages with no arch/ext data",
        "- `GitHubPackageInfo_Filter5.csv` - After removing packages with matching URLs",
        "- `GitHubPackageInfo_Filter5_5.csv` - After removing packages with any URL matches",
        "- `GitHubPackageInfo_Filter6.csv` - After removing packages with exact version matches",
        "- `GitHubPackageInfo_Filter7.csv` - After removing packages with normalized version matches",
        "- `GitHubPackageInfo_Filter8.csv` - After removing packages with URL count mismatches",
        "",
        "### Removed Packages (By Filter)",
        "- `Filter1_Removed.csv` - Packages with no GitHub releases",
        "- `Filter2_Removed.csv` - Packages with no GitHub download URLs",
        "- `Filter3_Removed.csv` - Packages with open pull requests", 
        "- `Filter4_Removed.csv` - Packages with no architecture/extension data",
        "- `Filter5_Removed.csv` - Packages with URLs already matching WinGet",
        "- `Filter5_5_Removed.csv` - Packages with GitHub URLs matching any WinGet version",
        "- `Filter6_Removed.csv` - Packages with exactly matching versions",
        "- `Filter7_Removed.csv` - Packages with versions matching after normalization",
        "- `Filter8_Removed.csv` - Packages with URL count mismatches",
        "",
        "### Combined Files",
        "- `RemovedRows.csv` - All removed packages with reasons",
        "- `FilteringSummary.md` - This summary report",
        "",
        "## Usage",
        "",
        "Each removed package CSV contains the original package data plus a 'reason' column",
        "explaining why it was filtered out. This helps with:",
        "",
        "- Debugging filter logic",
        "- Understanding package update requirements", 
        "- Manual review of filtered packages",
        "- Adjusting filter criteria if needed"
    ])
    
    # Write summary to file
    summary_file = output_dir_path / "FilteringSummary.md"
    with open(summary_file, 'w') as f:
        f.write('\n'.join(summary_lines))
    
    logging.info(f"Filter summary report generated: {summary_file}")


def main():
    # Example usage when run as script
    input_path = "../../test_data/test_input.csv"
    output_dir = "../../test_data/output"
    
    if not Path(input_path).exists():
        print(f"Test file not found: {input_path}")
        print("Creating test data...")
        
        # Create test data
        import pandas as pd
        test_data = {
            'PackageName': ['Test.Package1', 'Test.Package2', 'Test.Package3', 'Test.Package4', 'Test.Package5'],
            'GitHubLatest': ['1.0.0', 'Not Found', '2.0.0', '3.0.0', '4.0.0'],
            'LatestGitHubURLs': ['http://example.com/1.exe', '', 'http://example.com/2.exe', 'http://example.com/3.exe', 'http://example.com/4.exe'],
            'LatestVersionPullRequest': ['not_found', 'not_found', 'open', 'not_found', 'not_found'],
            'ArchExtPairs': ['x64.exe', 'x64.exe', 'x64.exe', '', 'x64.exe'],
            'LatestVersionURLsInWinGet': ['http://different.com/1.exe', 'http://different.com/2.exe', 'http://different.com/3.exe', 'http://different.com/4.exe', 'http://example.com/4.exe'],
            'HasAnyURLMatch': [False, False, False, False, False],
            'CurrentLatestVersionInWinGet': ['0.9.0', '1.0.0', '2.0.0', '3.0.0', '3.0.0'],
            'InstallerURLsCount': [1, 1, 1, 1, 2]
        }
        
        test_df = pd.DataFrame(test_data)
        Path(input_path).parent.mkdir(parents=True, exist_ok=True)
        test_df.to_csv(input_path, index=False)
        print(f"Test data created: {input_path}")
    
    print("Running enhanced filter processing...")
    process_filters(input_path, output_dir)


if __name__ == "__main__":
    main()
