#!/usr/bin/env python3

import sys
import os
sys.path.append('/workspaces/WinGetManifestAutomationTool/src')

from winget_automation.github.GitHubPackageProcessor import VersionAnalyzer
from winget_automation.github.GitHubAPI import GitHubAPI

def test_zen_browser():
    print("Testing simplified URL comparison with Zen Browser...")
    
    # Create analyzer
    analyzer = VersionAnalyzer(GitHubAPI('fake_token'))
    
    # Test data for Zen Browser
    test_row = [
        'Zen-Team.Zen-Browser',  # PackageIdentifier
        'multiple_versions',     # AvailableVersions
        'pattern',              # VersionFormatPattern
        '1.14b',               # CurrentLatestVersioninWinGet
        '2',                   # InstallerURLsCount
        'https://github.com/zen-browser/desktop/releases/download/1.14b/zen.installer.exe,https://github.com/zen-browser/desktop/releases/download/1.14b/zen.installer-arm64.exe',  # LatestVersionURLsinWinGet
        'arch_ext_pairs',      # ArchExtPairs
        False                  # HasOpenPullRequests
    ]
    
    print(f"Package: {test_row[0]}")
    print(f"WinGet URLs: {test_row[5]}")
    print()
    
    try:
        result = analyzer.process_package(test_row)
        
        print("=== COMPARISON RESULTS ===")
        print(f"HasAnyURLMatch: {result.get('HasAnyURLMatch', False)}")
        print(f"ExactURLMatches: {result.get('ExactURLMatches', [])}")
        print(f"ExactMatchesCount: {result.get('ExactMatchesCount', 0)}")
        print(f"WinGetVersionsFound: {result.get('WinGetVersionsFound', 0)}")
        print(f"GitHubLatestURLs: {result.get('GitHubLatestURLs', [])}")
        print()
        
        if result.get('HasAnyURLMatch', False):
            print("✅ SUCCESS: URLs matched!")
        else:
            print("❌ FAILED: No URL matches found")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_zen_browser()
