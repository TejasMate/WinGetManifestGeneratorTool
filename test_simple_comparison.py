#!/usr/bin/env python3
"""
Quick test of the simplified URL comparison logic.
"""

import sys
import os
import yaml
from pathlib import Path

def test_zen_browser():
    """Test with Zen Browser specifically."""
    print("Testing Zen Browser URL comparison...")
    
    # Direct path to Zen Browser manifests
    zen_path = Path("/workspaces/WinGetManifestAutomationTool/winget-pkgs/manifests/z/Zen-Team/Zen-Browser")
    
    if not zen_path.exists():
        print(f"❌ Path not found: {zen_path}")
        return
    
    print(f"✅ Found Zen Browser at: {zen_path}")
    
    # Get all versions
    versions = [d.name for d in zen_path.iterdir() if d.is_dir()]
    print(f"Found {len(versions)} versions")
    
    # Collect all URLs from all versions
    all_urls = []
    for version in versions:  # Check ALL versions
        version_path = zen_path / version
        installer_file = version_path / "Zen-Team.Zen-Browser.installer.yaml"
        
        if installer_file.exists():
            try:
                with open(installer_file, 'r', encoding='utf-8') as f:
                    manifest = yaml.safe_load(f)
                
                installers = manifest.get('Installers', [])
                for installer in installers:
                    url = installer.get('InstallerUrl')
                    if url:
                        all_urls.append(url)
                        if version == "1.14b":  # Show the specific version we're testing
                            print(f"  {version}: {url}")
            except Exception as e:
                print(f"  Error reading {version}: {e}")
    
    print(f"\nCollected {len(all_urls)} URLs from {len(versions)} versions")
    
    # Test GitHub URLs from your example
    github_urls = [
        "https://github.com/zen-browser/desktop/releases/download/1.14b/zen.installer.exe",
        "https://github.com/zen-browser/desktop/releases/download/1.14b/zen.installer-arm64.exe"
    ]
    
    print(f"\nTesting {len(github_urls)} GitHub URLs:")
    for url in github_urls:
        print(f"  {url}")
    
    # Simple comparison
    matches = []
    for github_url in github_urls:
        if github_url in all_urls:
            matches.append(github_url)
            print(f"  ✅ MATCH: {github_url}")
        else:
            print(f"  ❌ NO MATCH: {github_url}")
    
    print(f"\n🎯 Result: {len(matches)} out of {len(github_urls)} URLs matched!")
    
    return len(matches) > 0

if __name__ == "__main__":
    test_zen_browser()
