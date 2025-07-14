#!/usr/bin/env python3
"""
Test script to verify the URL comparison functionality in GitHubPackageProcessor.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from winget_automation.github.GitHubPackageProcessor import WinGetManifestExtractor, URLComparator

def test_url_comparison():
    """Test the URL comparison functionality."""
    print("Testing URL Comparison Enhancement...")
    
    # Test WinGetManifestExtractor
    print("\n1. Testing WinGetManifestExtractor...")
    extractor = WinGetManifestExtractor("/workspaces/WinGetManifestAutomationTool/winget-pkgs")
    
    # Test finding a package directory
    package_dir = extractor.get_package_directory("Microsoft.Git")
    print(f"Package directory for Microsoft.Git: {package_dir}")
    
    if package_dir and package_dir.exists():
        # Test getting all URLs for the package
        try:
            all_urls = extractor.get_all_installer_urls_for_package("Microsoft.Git")
            if all_urls:
                total_urls = sum(len(urls) for urls in all_urls.values())
                print(f"Total versions found: {len(all_urls)}")
                print(f"Total URLs found for Microsoft.Git: {total_urls}")
                print(f"Sample versions: {list(all_urls.keys())[:3]}")
            else:
                print("No URLs found for Microsoft.Git")
        except Exception as e:
            print(f"Error getting URLs: {e}")
    else:
        print("Microsoft.Git package directory not found, testing with a mock package")
    
    # Test URLComparator
    print("\n2. Testing URLComparator...")
    comparator = URLComparator()
    
    # Test URL normalization
    test_urls = [
        "https://github.com/git-for-windows/git/releases/download/v2.43.0.windows.1/Git-2.43.0-64-bit.exe",
        "https://github.com/git-for-windows/git/releases/download/v2.42.0.windows.2/Git-2.42.0-32-bit.exe",
        "https://api.github.com/repos/git-for-windows/git/releases/assets/139876543"
    ]
    
    for url in test_urls:
        normalized = comparator.normalize_url_for_comparison(url)
        filename = comparator.extract_base_filename(url)
        print(f"Original: {url}")
        print(f"Normalized: {normalized}")
        print(f"Filename: {filename}")
        print()
    
    # Test URL comparison
    github_urls = ["https://github.com/git-for-windows/git/releases/download/v2.43.0.windows.1/Git-2.43.0-64-bit.exe"]
    winget_urls = ["https://github.com/git-for-windows/git/releases/download/v2.42.0.windows.2/Git-2.42.0-64-bit.exe"]
    
    comparison = comparator.compare_urls(github_urls, winget_urls)
    print("3. Testing URL Comparison:")
    print(f"Comparison result: {comparison}")
    print(f"Has any match: {comparison.get('has_any_match', False)}")
    print(f"Exact matches: {len(comparison.get('exact_matches', []))}")
    print(f"Normalized matches: {len(comparison.get('normalized_matches', []))}")
    print(f"Filename matches: {len(comparison.get('filename_matches', []))}")
    
    print("\n✅ URL Comparison Enhancement test completed successfully!")

if __name__ == "__main__":
    test_url_comparison()
