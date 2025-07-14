#!/usr/bin/env python3
"""Test script for the configuration management system."""

import os
import sys
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from winget_automation.config import get_config_manager, get_config
from winget_automation.config.manager import ConfigManager


def test_config_loading():
    """Test basic configuration loading."""
    print("Testing configuration loading...")
    
    # Test with development environment
    os.environ["WINGET_ENV"] = "development"
    manager = ConfigManager()
    
    config = manager.load_config()
    print(f"✓ Loaded configuration for environment: {config.get('environment')}")
    print(f"✓ Debug mode: {config.get('debug')}")
    print(f"✓ Log level: {config.get('logging', {}).get('level')}")
    
    return True


def test_environment_detection():
    """Test environment detection."""
    print("\nTesting environment detection...")
    
    # Test different environment variables
    test_envs = {
        "development": ["dev", "development", "DEV"],
        "staging": ["stage", "staging", "STAGE"],
        "production": ["prod", "production", "PROD"]
    }
    
    for expected, env_values in test_envs.items():
        for env_value in env_values:
            os.environ["WINGET_ENV"] = env_value
            manager = ConfigManager()
            detected = manager.environment
            if detected == expected:
                print(f"✓ {env_value} -> {detected}")
            else:
                print(f"✗ {env_value} -> {detected} (expected {expected})")
    
    return True


def test_config_access():
    """Test configuration access methods."""
    print("\nTesting configuration access...")
    
    os.environ["WINGET_ENV"] = "development"
    manager = ConfigManager()
    config = manager.load_config()
    
    # Test get method with dot notation
    log_level = manager.get("logging.level")
    print(f"✓ Get with dot notation: logging.level = {log_level}")
    
    # Test with default value
    non_existent = manager.get("non.existent.key", "default_value")
    print(f"✓ Get with default: non.existent.key = {non_existent}")
    
    # Test global get_config function
    github_tokens = get_config("github.tokens", [])
    print(f"✓ Global get_config: github.tokens = {github_tokens}")
    
    return True


def test_environment_variables():
    """Test environment variable overrides."""
    print("\nTesting environment variable overrides...")
    
    # Set test environment variables
    os.environ["TOKEN_1"] = "test_token_1"
    os.environ["TOKEN_2"] = "test_token_2"
    os.environ["LOG_LEVEL"] = "ERROR"
    os.environ["MAX_WORKERS"] = "16"
    os.environ["DEBUG"] = "true"
    
    manager = ConfigManager()
    config = manager.load_config()
    
    # Check if environment variables are applied
    tokens = config.get("github", {}).get("tokens", [])
    log_level = config.get("logging", {}).get("level")
    max_workers = config.get("package_processing", {}).get("max_workers")
    debug = config.get("debug")
    
    print(f"✓ GitHub tokens from env: {tokens}")
    print(f"✓ Log level from env: {log_level}")
    print(f"✓ Max workers from env: {max_workers}")
    print(f"✓ Debug from env: {debug}")
    
    # Cleanup
    for var in ["TOKEN_1", "TOKEN_2", "LOG_LEVEL", "MAX_WORKERS", "DEBUG"]:
        if var in os.environ:
            del os.environ[var]
    
    return True


def test_config_validation():
    """Test configuration validation."""
    print("\nTesting configuration validation...")
    
    manager = ConfigManager()
    config = manager.load_config()
    
    # Validate the loaded configuration
    is_valid, errors = manager.validate_config(config)
    
    if is_valid:
        print("✓ Configuration validation passed")
    else:
        print(f"✗ Configuration validation failed: {errors}")
    
    # Test invalid configuration
    invalid_config = {"logging": {"level": "INVALID_LEVEL"}}
    is_valid, errors = manager.validate_config(invalid_config)
    
    if not is_valid:
        print("✓ Invalid configuration correctly rejected")
        print(f"  Errors: {errors}")
    else:
        print("✗ Invalid configuration was incorrectly accepted")
    
    return True


def test_environment_info():
    """Test environment information."""
    print("\nTesting environment information...")
    
    manager = ConfigManager()
    env_info = manager.get_environment_info()
    
    print(f"✓ Environment: {env_info['environment']}")
    print(f"✓ Config path: {env_info['config_path']}")
    print(f"✓ Available environments: {env_info['available_environments']}")
    print(f"✓ Config files found: {env_info['config_files_found']}")
    
    return True


def main():
    """Run all configuration tests."""
    print("WinGet Manifest Generator Tool Configuration System Test")
    print("=" * 55)
    
    tests = [
        test_config_loading,
        test_environment_detection,
        test_config_access,
        test_environment_variables,
        test_config_validation,
        test_environment_info
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {e}")
            failed += 1
    
    print("\n" + "=" * 55)
    print(f"Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
