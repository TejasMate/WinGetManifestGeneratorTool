#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from winget_automation.github.GitHubPackageProcessor import VersionAnalyzer, WinGetManifestExtractor
from winget_automation.utils.unified_utils import GitHubAPI, GitHubConfig

def test_comparison():
    try:
        # Simple test
        config = GitHubConfig({'token': 'dummy', 'rate_limit_requests': 1000})
        github_api = GitHubAPI(config)
        analyzer = VersionAnalyzer(github_api)

        # Test the comparison
        github_urls = [
            'https://github.com/zen-browser/desktop/releases/download/1.14b/zen.installer.exe',
            'https://github.com/zen-browser/desktop/releases/download/1.14b/zen.installer-arm64.exe'
        ]

        print("🔍 Testing URL comparison for Zen-Team.Zen-Browser...")
        print(f"GitHub URLs: {github_urls}")

        result = analyzer.compare_with_all_winget_versions('Zen-Team.Zen-Browser', github_urls)
        print('\n🎯 Comparison Result:')
        for key, value in result.items():
            print(f'  {key}: {value}')
            
        if result.get('has_any_match', False):
            print("\n✅ SUCCESS: URLs matched!")
        else:
            print("\n❌ No matches found")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_comparison()
