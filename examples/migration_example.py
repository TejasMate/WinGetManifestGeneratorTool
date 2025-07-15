"""
Migration Example: From GitHub-only to Multi-Source

This example shows how to migrate existing GitHub-specific code
to use the new multi-source architecture.
"""

# ================================
# BEFORE: GitHub-only approach
# ================================

def old_github_only_approach():
    """Example of how the code worked before with GitHub-only support."""
    
    # Old way - directly using GitHub-specific classes
    from src.utils.unified_utils import GitHubAPI, GitHubConfig
    from src.utils.token_manager import TokenManager
    
    # Initialize GitHub-specific components
    token_manager = TokenManager()
    token = token_manager.get_available_token()
    github_config = GitHubConfig(token=token)
    github_api = GitHubAPI(github_config)
    
    # Process GitHub URLs only
    github_url = "https://github.com/microsoft/PowerToys"
    
    # Extract repo info manually
    import re
    match = re.search(r"github\.com/([^/]+)/([^/]+)", github_url)
    if match:
        username, repo = match.groups()
        
        # Get release info
        release = github_api.get_latest_release(username, repo)
        
        if release:
            print(f"GitHub Release: {release['tag_name']}")
            print(f"Assets: {len(release.get('asset_urls', []))}")
    
    # Limitation: Only works with GitHub URLs
    # Adding GitLab support would require duplicating this entire logic


# ================================
# AFTER: Multi-source approach
# ================================

def new_multi_source_approach():
    """Example of how the code works now with multi-source support."""
    
    # New way - using unified interface that works with any source
    from src.sources import get_package_metadata_for_url
    
    # Works with any supported source - no source-specific code needed!
    urls = [
        "https://github.com/microsoft/PowerToys",      # GitHub
        "https://gitlab.com/inkscape/inkscape",        # GitLab
        "https://sourceforge.net/projects/sevenzip/"   # SourceForge
    ]
    
    for url in urls:
        print(f"\nProcessing: {url}")
        
        # Single unified call works for all sources
        metadata = get_package_metadata_for_url(url)
        
        if metadata:
            print(f"  Source: {metadata.repository_info.source_type.value}")
            print(f"  Package: {metadata.identifier}")
            print(f"  Name: {metadata.name}")
            
            if metadata.latest_release:
                print(f"  Latest: {metadata.latest_release.version}")
                print(f"  Assets: {len(metadata.latest_release.download_urls)}")
        else:
            print("  No metadata available")
    
    # Benefit: Same code works for all sources
    # Adding new sources requires no changes to this code


# ================================
# MIGRATION: Step-by-step process
# ================================

def migration_example():
    """Step-by-step migration from old to new architecture."""
    
    print("🔄 Migration Example: GitHub-only to Multi-source")
    print("=" * 60)
    
    # Step 1: Replace direct GitHub API calls
    print("\n📋 Step 1: Replace direct GitHub API usage")
    
    # OLD:
    # github_api = GitHubAPI(config)
    # release = github_api.get_latest_release(username, repo)
    
    # NEW:
    from src.sources import get_package_source_manager
    from src.core.package_sources import PackageSourceType
    
    manager = get_package_source_manager()
    github_source = manager.get_source_by_type(PackageSourceType.GITHUB)
    print(f"   GitHub source available: {'✅' if github_source else '❌'}")
    
    # Step 2: Use unified metadata instead of raw API responses
    print("\n📋 Step 2: Use standardized metadata")
    
    url = "https://github.com/microsoft/PowerToys"
    
    # OLD: Manual parsing of GitHub API response
    # release_data = github_api.get_latest_release(username, repo)
    # version = release_data['tag_name']
    # urls = release_data['asset_urls']
    
    # NEW: Standardized metadata across all sources
    from src.sources import get_package_metadata_for_url
    
    metadata = get_package_metadata_for_url(url)
    if metadata:
        version = metadata.latest_release.version
        urls = metadata.latest_release.download_urls
        architectures = metadata.architectures
        extensions = metadata.file_extensions
        
        print(f"   ✅ Unified metadata:")
        print(f"      Version: {version}")
        print(f"      URLs: {len(urls)}")
        print(f"      Architectures: {architectures}")
        print(f"      Extensions: {extensions}")
    
    # Step 3: Use multi-source processor for batch operations
    print("\n📋 Step 3: Use multi-source processor")
    
    # OLD: GitHub-specific batch processing
    # for package in packages:
    #     if 'github.com' in package['url']:
    #         process_github_package(package)
    
    # NEW: Universal batch processing
    from src.core.multi_source_processor import MultiSourcePackageProcessor
    
    processor = MultiSourcePackageProcessor()
    test_urls = [
        "https://github.com/microsoft/PowerToys",
        "https://gitlab.com/inkscape/inkscape"
    ]
    
    results = processor.process_package_urls(test_urls)
    
    print(f"   ✅ Processed {len(results)} packages from different sources:")
    for result in results:
        status = "✅" if result.success else "❌"
        source = result.source_type.value if result.source_type else "unknown"
        print(f"      {status} {source}: {result.package_identifier}")
    
    print("\n🎉 Migration complete! Code now supports multiple sources.")


# ================================
# CONFIGURATION: Multi-source setup
# ================================

def configuration_example():
    """Show how to configure multiple package sources."""
    
    print("\n⚙️ Configuration Example")
    print("=" * 60)
    
    # Example configuration in config.yaml
    example_config = """
# Multi-source configuration
package_sources:
  github:
    enabled: true
    # Tokens loaded from .env file
    rate_limit_buffer: 100
    max_retries: 3
    
  gitlab:
    enabled: true
    instances:
      - "gitlab.com"
      - "custom.gitlab.com"
    # Tokens per instance
    
  sourceforge:
    enabled: false  # Can be disabled
    
  # Priority order for package resolution
  priority: ["github", "gitlab", "sourceforge"]

# Filtering applies to all sources
filtering:
  blocked_packages: ["package1", "package2"]
  allowed_architectures: ["x64", "x86", "arm64"]
  allowed_extensions: ["msi", "exe", "zip"]
"""
    
    print("📝 Example configuration:")
    print(example_config)
    
    # Show how configuration is used
    from src.sources import PackageSourceManager
    
    # Configuration is automatically loaded from config system
    manager = PackageSourceManager()
    supported = manager.get_supported_source_types()
    
    print(f"🔧 Currently supported sources: {[s.value for s in supported]}")


# ================================
# MAIN DEMO
# ================================

def main():
    """Main demonstration of migration concepts."""
    
    print("📚 Multi-Source Architecture Migration Guide")
    print("=" * 80)
    
    try:
        print("\n🔍 Comparing old vs new approaches:")
        
        print("\n" + "=" * 40)
        print("OLD: GitHub-only approach")
        print("=" * 40)
        old_github_only_approach()
        
        print("\n" + "=" * 40) 
        print("NEW: Multi-source approach")
        print("=" * 40)
        new_multi_source_approach()
        
        # Show migration steps
        migration_example()
        
        # Show configuration
        configuration_example()
        
        print("\n🎯 Key Benefits of New Architecture:")
        print("   ✅ Unified interface for all package sources")
        print("   ✅ Easy addition of new sources (GitLab, SourceForge, etc.)")
        print("   ✅ Consistent data structures across sources")
        print("   ✅ Source-specific optimizations")
        print("   ✅ Backward compatibility with existing GitHub code")
        print("   ✅ Configuration-driven source management")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
