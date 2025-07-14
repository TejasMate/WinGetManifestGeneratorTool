#!/usr/bin/env python3
"""
Example integration of the configuration system with existing code.

This script demonstrates how to use the new configuration management system
in your existing WinGetManifestGeneratorTool components.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from winget_automation.config import get_config, get_config_manager


def demonstrate_basic_usage():
    """Demonstrate basic configuration usage."""
    print("=== Basic Configuration Usage ===")
    
    # Get the configuration manager
    manager = get_config_manager()
    
    # Get environment information
    env_info = manager.get_environment_info()
    print(f"Environment: {env_info['environment']}")
    print(f"Config path: {env_info['config_path']}")
    print(f"Config files found: {env_info['config_files_found']}")
    
    # Load and display configuration
    config = manager.load_config()
    print(f"Debug mode: {config['debug']}")
    print(f"Log level: {config['logging']['level']}")
    print(f"Max workers: {config['package_processing']['max_workers']}")
    print(f"GitHub tokens configured: {len(config['github']['tokens'])}")


def demonstrate_individual_settings():
    """Demonstrate accessing individual configuration settings."""
    print("\n=== Individual Configuration Settings ===")
    
    # Use the global get_config function for easy access
    log_level = get_config("logging.level", "INFO")
    print(f"Log level: {log_level}")
    
    winget_repo_path = get_config("package_processing.winget_repo_path", "winget-pkgs")
    print(f"WinGet repo path: {winget_repo_path}")
    
    output_formats = get_config("output.formats", ["csv"])
    print(f"Output formats: {output_formats}")
    
    cache_enabled = get_config("performance.cache_enabled", False)
    print(f"Cache enabled: {cache_enabled}")
    
    # Access nested configuration with default fallback
    github_retry_attempts = get_config("github.retry_attempts", 3)
    print(f"GitHub retry attempts: {github_retry_attempts}")


def demonstrate_runtime_modification():
    """Demonstrate modifying configuration at runtime."""
    print("\n=== Runtime Configuration Modification ===")
    
    manager = get_config_manager()
    
    # Get current value
    current_batch_size = manager.get("package_processing.batch_size")
    print(f"Current batch size: {current_batch_size}")
    
    # Modify configuration
    manager.set("package_processing.batch_size", 200)
    new_batch_size = manager.get("package_processing.batch_size")
    print(f"New batch size: {new_batch_size}")
    
    # Add a new configuration value
    manager.set("custom.my_setting", "custom_value")
    custom_setting = manager.get("custom.my_setting")
    print(f"Custom setting: {custom_setting}")


def demonstrate_environment_variables():
    """Demonstrate environment variable integration."""
    print("\n=== Environment Variable Integration ===")
    
    import os
    
    # Show current GitHub tokens
    tokens = get_config("github.tokens", [])
    print(f"Current GitHub tokens: {len(tokens)} tokens configured")
    
    # Show environment variable mappings
    print("\nEnvironment variable mappings:")
    print("TOKEN_1, TOKEN_2, ... -> github.tokens")
    print("LOG_LEVEL -> logging.level") 
    print("MAX_WORKERS -> package_processing.max_workers")
    print("BATCH_SIZE -> package_processing.batch_size")
    print("DEBUG -> debug")
    print("WINGET_ENV -> environment selection")
    
    # Show current environment
    env = os.getenv("WINGET_ENV", "development")
    print(f"Current environment: {env}")


def demonstrate_package_processor_integration():
    """Demonstrate how to integrate configuration with PackageProcessor."""
    print("\n=== PackageProcessor Integration Example ===")
    
    # This is how you would modify PackageProcessor to use configuration
    print("Example code for PackageProcessor integration:")
    print("""
    from config import get_config
    
    class PackageProcessor:
        def __init__(self):
            # Get configuration values
            self.winget_repo_path = get_config("package_processing.winget_repo_path", "winget-pkgs")
            self.output_directory = get_config("package_processing.output_directory", "data")
            self.max_workers = get_config("package_processing.max_workers", 4)
            self.batch_size = get_config("package_processing.batch_size", 100)
            self.timeout = get_config("package_processing.timeout", 300)
            
            # Setup logging based on configuration
            log_level = get_config("logging.level", "INFO")
            logging.getLogger().setLevel(getattr(logging, log_level))
            
        def process_packages(self):
            # Use configuration values
            print(f"Processing packages from {self.winget_repo_path}")
            print(f"Using {self.max_workers} workers")
            print(f"Batch size: {self.batch_size}")
    """)


def demonstrate_github_integration():
    """Demonstrate how to integrate configuration with GitHub module."""
    print("\n=== GitHub Module Integration Example ===")
    
    # Show GitHub configuration
    github_config = get_config("github", {})
    print(f"GitHub API URL: {github_config.get('api_url', 'https://api.github.com')}")
    print(f"Per page: {github_config.get('per_page', 100)}")
    print(f"Retry attempts: {github_config.get('retry_attempts', 3)}")
    print(f"Retry delay: {github_config.get('retry_delay', 1.0)}")
    print(f"Rate limit buffer: {github_config.get('rate_limit_buffer', 100)}")
    
    print("\nExample GitHub module integration:")
    print("""
    from config import get_config
    
    class GitHubAPI:
        def __init__(self):
            # Get GitHub configuration
            self.tokens = get_config("github.tokens", [])
            self.api_url = get_config("github.api_url", "https://api.github.com")
            self.per_page = get_config("github.per_page", 100)
            self.retry_attempts = get_config("github.retry_attempts", 3)
            self.retry_delay = get_config("github.retry_delay", 1.0)
            
        def make_request(self, endpoint):
            # Use configuration values for API requests
            for attempt in range(self.retry_attempts):
                try:
                    # Make API request with configured parameters
                    pass
                except Exception:
                    time.sleep(self.retry_delay)
    """)


def demonstrate_validation():
    """Demonstrate configuration validation."""
    print("\n=== Configuration Validation ===")
    
    manager = get_config_manager()
    
    # Validate current configuration
    is_valid, errors = manager.validate_config()
    if is_valid:
        print("✓ Current configuration is valid")
    else:
        print("✗ Configuration validation failed:")
        for error in errors:
            print(f"  - {error}")
    
    # Test invalid configuration
    invalid_config = {
        "logging": {
            "level": "INVALID_LEVEL"
        }
    }
    
    is_valid, errors = manager.validate_config(invalid_config)
    if not is_valid:
        print("✓ Invalid configuration correctly rejected")
        print("  Sample errors:")
        for error in errors[:3]:  # Show first 3 errors
            print(f"  - {error}")


def main():
    """Run all demonstration examples."""
    print("WinGet Manifest Generator Tool Configuration System Integration Examples")
    print("=" * 75)
    
    try:
        demonstrate_basic_usage()
        demonstrate_individual_settings()
        demonstrate_runtime_modification()
        demonstrate_environment_variables()
        demonstrate_package_processor_integration()
        demonstrate_github_integration()
        demonstrate_validation()
        
        print("\n" + "=" * 75)
        print("✅ Configuration system integration examples completed successfully!")
        print("\nNext steps:")
        print("1. Integrate configuration into your existing modules")
        print("2. Replace hardcoded values with get_config() calls")
        print("3. Set environment variables for your deployment")
        print("4. Customize config files for your environment")
        
    except Exception as e:
        print(f"\n❌ Error during demonstration: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
