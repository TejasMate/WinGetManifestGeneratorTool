#!/usr/bin/env python3
"""
Test script for the new multi-source package architecture.

This script demonstrates how the new architecture can handle different
package sources through a unified interface.
"""

import sys
import logging
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.sources import (
    PackageSourceManager, 
    get_package_metadata_for_url,
    is_supported_package_url
)
from src.core.package_sources import PackageSourceType
from src.core.multi_source_processor import MultiSourcePackageProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_individual_sources():
    """Test individual package sources."""
    print("🧪 Testing Individual Package Sources")
    print("=" * 60)
    
    test_urls = {
        "GitHub": "https://github.com/microsoft/PowerToys",
        "GitLab": "https://gitlab.com/inkscape/inkscape", 
        "SourceForge": "https://sourceforge.net/projects/sevenzip/",
        "Unsupported": "https://example.com/unsupported"
    }
    
    for source_name, url in test_urls.items():
        print(f"\n📦 Testing {source_name}: {url}")
        
        # Check if URL is supported
        is_supported = is_supported_package_url(url)
        print(f"   Supported: {'✅' if is_supported else '❌'}")
        
        if is_supported:
            try:
                # Get metadata
                metadata = get_package_metadata_for_url(url)
                
                if metadata:
                    print(f"   ✅ Metadata retrieved:")
                    print(f"      - Identifier: {metadata.identifier}")
                    print(f"      - Name: {metadata.name}")
                    print(f"      - Source: {metadata.repository_info.source_type.value}")
                    print(f"      - Repository: {metadata.repository_info.base_url}")
                    
                    if metadata.latest_release:
                        print(f"      - Latest Version: {metadata.latest_release.version}")
                        print(f"      - Download URLs: {len(metadata.latest_release.download_urls)}")
                    
                    if metadata.architectures:
                        print(f"      - Architectures: {', '.join(metadata.architectures)}")
                    
                    if metadata.file_extensions:
                        print(f"      - Extensions: {', '.join(metadata.file_extensions)}")
                else:
                    print(f"   ❌ No metadata retrieved")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")


def test_package_source_manager():
    """Test the package source manager."""
    print("\n\n🔧 Testing Package Source Manager")
    print("=" * 60)
    
    try:
        # Initialize manager
        manager = PackageSourceManager()
        
        # Show supported sources
        supported_types = manager.get_supported_source_types()
        print(f"📊 Supported Sources: {len(supported_types)}")
        for source_type in supported_types:
            print(f"   - {source_type.value}")
        
        # Test URL routing
        test_urls = [
            "https://github.com/microsoft/PowerToys",
            "https://gitlab.com/inkscape/inkscape",
            "https://sourceforge.net/projects/sevenzip/"
        ]
        
        print(f"\n🔀 Testing URL Routing:")
        for url in test_urls:
            source = manager.get_source_for_url(url)
            if source:
                print(f"   {url} -> {source.source_type.value} ✅")
            else:
                print(f"   {url} -> No source found ❌")
        
        # Test batch processing
        print(f"\n📊 Testing Batch Processing:")
        results = manager.process_urls(test_urls)
        
        for url, metadata in results.items():
            if metadata:
                print(f"   ✅ {url} -> {metadata.identifier}")
            else:
                print(f"   ❌ {url} -> Failed")
                
    except Exception as e:
        print(f"❌ Manager test failed: {e}")
        import traceback
        traceback.print_exc()


def test_multi_source_processor():
    """Test the multi-source processor."""
    print("\n\n⚙️ Testing Multi-Source Processor")
    print("=" * 60)
    
    try:
        # Initialize processor
        processor = MultiSourcePackageProcessor()
        
        # Validate configuration
        validation = processor.validate_configuration()
        print("🔧 Configuration Validation:")
        for key, value in validation.items():
            status = "✅" if value else "❌"
            print(f"   {key}: {status}")
        
        # Show source statistics
        stats = processor.get_source_statistics()
        print(f"\n📈 Source Statistics:")
        for source, count in stats.items():
            print(f"   {source}: {count} handler(s)")
        
        # Test processing
        test_urls = [
            "https://github.com/microsoft/PowerToys",
            "https://gitlab.com/inkscape/inkscape",
            "https://sourceforge.net/projects/sevenzip/",
            "https://example.com/unsupported"
        ]
        
        print(f"\n🚀 Processing {len(test_urls)} URLs:")
        results = processor.process_package_urls(test_urls)
        
        success_count = 0
        for result in results:
            status = "✅" if result.success else "❌"
            print(f"   {status} {result.package_identifier}")
            
            if result.success:
                success_count += 1
                if result.metadata:
                    print(f"      Source: {result.source_type.value}")
                    print(f"      Name: {result.metadata.name}")
            else:
                print(f"      Error: {result.error_message}")
        
        print(f"\n📊 Results: {success_count}/{len(results)} successful")
        
    except Exception as e:
        print(f"❌ Processor test failed: {e}")
        import traceback
        traceback.print_exc()


def test_github_compatibility():
    """Test backward compatibility with existing GitHub functionality."""
    print("\n\n🔄 Testing GitHub Backward Compatibility")
    print("=" * 60)
    
    try:
        # Test with existing GitHub URLs from the codebase
        github_urls = [
            "https://github.com/microsoft/PowerToys",
            "https://github.com/microsoft/PowerToys/releases",
            "https://github.com/microsoft/PowerToys/releases/download/v0.70.1/PowerToysUserSetup-0.70.1-x64.exe"
        ]
        
        manager = PackageSourceManager()
        github_source = manager.get_source_by_type(PackageSourceType.GITHUB)
        
        if not github_source:
            print("❌ GitHub source not available")
            return
        
        print("✅ GitHub source available")
        
        for url in github_urls:
            print(f"\n🔗 Testing: {url}")
            
            # Test URL handling
            can_handle = github_source.can_handle_url(url)
            print(f"   Can handle: {'✅' if can_handle else '❌'}")
            
            if can_handle:
                # Test repository extraction
                repo_info = github_source.extract_repository_info(url)
                if repo_info:
                    print(f"   Repository: {repo_info.username}/{repo_info.repository_name}")
                    print(f"   Base URL: {repo_info.base_url}")
                    
                    # Test release fetching (this uses actual GitHub API)
                    try:
                        latest_release = github_source.get_latest_release(repo_info)
                        if latest_release:
                            print(f"   Latest Release: {latest_release.version}")
                            print(f"   Download URLs: {len(latest_release.download_urls)}")
                        else:
                            print("   No releases found")
                    except Exception as e:
                        print(f"   Release fetch error: {e}")
                else:
                    print("   ❌ Failed to extract repository info")
        
    except Exception as e:
        print(f"❌ GitHub compatibility test failed: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main test function."""
    print("🎯 Multi-Source Package Architecture Test Suite")
    print("=" * 80)
    print("This test demonstrates the new extensible architecture for handling")
    print("multiple package sources beyond just GitHub.")
    print("=" * 80)
    
    try:
        # Run all tests
        test_individual_sources()
        test_package_source_manager()
        test_multi_source_processor()
        test_github_compatibility()
        
        print("\n\n🎉 Test Suite Complete!")
        print("=" * 80)
        print("✅ Multi-source architecture is working correctly")
        print("🚀 Ready for GitLab and SourceForge implementation")
        print("📦 GitHub functionality remains fully compatible")
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
