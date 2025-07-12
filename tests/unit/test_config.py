"""Unit tests for the configuration management system."""

import os
import json
import yaml
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open

try:
    from src.config import ConfigManager, get_config_manager, get_config
    from src.config.schema import ConfigSchema
    from src.exceptions import ConfigurationError
except ImportError:
    # Fallback for direct execution
    import sys
    sys.path.append(str(Path(__file__).parent.parent / "src"))
    from config import ConfigManager, get_config_manager, get_config
    from config.schema import ConfigSchema
    from exceptions import ConfigurationError


class TestConfigSchema:
    """Test cases for ConfigSchema class."""
    
    def test_valid_configuration(self):
        """Test validation of a valid configuration."""
        schema = ConfigSchema()
        
        valid_config = {
            "environment": "development",
            "debug": True,
            "logging": {
                "level": "DEBUG",
                "format": "%(message)s"
            },
            "github": {
                "tokens": ["test_token"],
                "api_url": "https://api.github.com"
            },
            "package_processing": {
                "winget_repo_path": "winget-pkgs",
                "output_directory": "data"
            },
            "filtering": {
                "blocked_packages": [],
                "allowed_architectures": ["x64"]
            },
            "output": {
                "formats": ["csv"]
            },
            "performance": {
                "cache_enabled": True
            }
        }
        
        is_valid, errors = schema.validate(valid_config)
        assert is_valid, f"Valid configuration failed validation: {errors}"
        assert len(errors) == 0
    
    def test_invalid_logging_level(self):
        """Test validation with invalid logging level."""
        schema = ConfigSchema()
        
        invalid_config = {
            "logging": {
                "level": "INVALID_LEVEL"
            }
        }
        
        is_valid, errors = schema.validate(invalid_config)
        assert not is_valid
        assert any("INVALID_LEVEL" in error for error in errors)
    
    def test_missing_required_fields(self):
        """Test validation with missing required fields."""
        schema = ConfigSchema()
        
        incomplete_config = {
            "debug": True
        }
        
        is_valid, errors = schema.validate(incomplete_config)
        assert not is_valid
        assert any("Required field" in error for error in errors)


class TestConfigManager:
    """Test cases for ConfigManager class."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        # Clear environment variables that might affect tests
        env_vars_to_clear = [
            "WINGET_ENV", "ENV", "TOKEN", "TOKEN_1", "TOKEN_2",
            "LOG_LEVEL", "MAX_WORKERS", "DEBUG"
        ]
        self.original_env = {}
        for var in env_vars_to_clear:
            if var in os.environ:
                self.original_env[var] = os.environ[var]
                del os.environ[var]
    
    def teardown_method(self):
        """Clean up test environment after each test."""
        # Restore original environment variables
        for var, value in self.original_env.items():
            os.environ[var] = value
    
    def test_environment_detection_default(self):
        """Test default environment detection."""
        manager = ConfigManager()
        assert manager.environment == "development"
    
    def test_environment_detection_from_env(self):
        """Test environment detection from environment variables."""
        test_cases = [
            ("development", "development"),
            ("dev", "development"),
            ("staging", "staging"),
            ("stage", "staging"),
            ("production", "production"),
            ("prod", "production")
        ]
        
        for env_value, expected in test_cases:
            os.environ["WINGET_ENV"] = env_value
            manager = ConfigManager()
            assert manager.environment == expected, f"Failed for {env_value}"
            del os.environ["WINGET_ENV"]
    
    def test_config_loading_with_defaults(self):
        """Test configuration loading with environment defaults."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir)
            manager = ConfigManager(config_path=config_path, environment="development")
            
            config = manager.load_config()
            
            assert config["environment"] == "development"
            assert config["debug"] is True
            assert config["logging"]["level"] == "DEBUG"
            assert isinstance(config["github"]["tokens"], list)
    
    def test_config_file_loading_yaml(self):
        """Test loading configuration from YAML file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir)
            
            # Create a test config file
            test_config = {
                "logging": {
                    "level": "INFO"
                },
                "github": {
                    "tokens": ["test_token"]
                }
            }
            
            config_file = config_path / "config.yaml"
            with open(config_file, 'w') as f:
                yaml.dump(test_config, f)
            
            manager = ConfigManager(config_path=config_path, environment="development")
            config = manager.load_config()
            
            # Should merge with defaults
            assert config["logging"]["level"] == "INFO"  # From file
            assert config["debug"] is True  # From environment defaults
    
    def test_config_file_loading_json(self):
        """Test loading configuration from JSON file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir)
            
            # Create a test config file
            test_config = {
                "logging": {
                    "level": "WARNING"
                }
            }
            
            config_file = config_path / "config.json"
            with open(config_file, 'w') as f:
                json.dump(test_config, f)
            
            manager = ConfigManager(config_path=config_path, environment="development")
            config = manager.load_config()
            
            assert config["logging"]["level"] == "WARNING"
    
    def test_environment_variable_overrides(self):
        """Test configuration overrides from environment variables."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir)
            
            # Set environment variables
            os.environ["TOKEN_1"] = "env_token_1"
            os.environ["TOKEN_2"] = "env_token_2"
            os.environ["LOG_LEVEL"] = "ERROR"
            os.environ["MAX_WORKERS"] = "8"
            os.environ["DEBUG"] = "false"
            
            manager = ConfigManager(config_path=config_path, environment="development")
            config = manager.load_config()
            
            assert config["github"]["tokens"] == ["env_token_1", "env_token_2"]
            assert config["logging"]["level"] == "ERROR"
            assert config["package_processing"]["max_workers"] == 8
            assert config["debug"] is False
    
    def test_get_config_value(self):
        """Test getting configuration values using dot notation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir)
            manager = ConfigManager(config_path=config_path, environment="development")
            
            # Test getting existing value
            log_level = manager.get("logging.level")
            assert log_level == "DEBUG"
            
            # Test getting non-existent value with default
            non_existent = manager.get("non.existent.key", "default")
            assert non_existent == "default"
            
            # Test getting non-existent value without default
            none_value = manager.get("another.non.existent.key")
            assert none_value is None
    
    def test_set_config_value(self):
        """Test setting configuration values using dot notation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir)
            manager = ConfigManager(config_path=config_path, environment="development")
            manager.load_config()
            
            # Test setting nested value
            manager.set("logging.level", "CRITICAL")
            assert manager.get("logging.level") == "CRITICAL"
            
            # Test setting new nested value
            manager.set("new.nested.key", "test_value")
            assert manager.get("new.nested.key") == "test_value"
    
    def test_config_validation_error(self):
        """Test configuration validation error handling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir)
            
            # Create invalid config file
            invalid_config = {
                "logging": {
                    "level": "INVALID_LEVEL"
                }
            }
            
            config_file = config_path / "config.yaml"
            with open(config_file, 'w') as f:
                yaml.dump(invalid_config, f)
            
            manager = ConfigManager(config_path=config_path, environment="development")
            
            with pytest.raises(ConfigurationError) as exc_info:
                manager.load_config()
            
            assert "Configuration validation failed" in str(exc_info.value)
    
    def test_config_merging(self):
        """Test configuration merging behavior."""
        base = {
            "a": 1,
            "b": {
                "c": 2,
                "d": 3
            }
        }
        
        override = {
            "b": {
                "d": 4,
                "e": 5
            },
            "f": 6
        }
        
        manager = ConfigManager()
        result = manager._merge_configs(base, override)
        
        expected = {
            "a": 1,
            "b": {
                "c": 2,
                "d": 4,
                "e": 5
            },
            "f": 6
        }
        
        assert result == expected
    
    def test_environment_info(self):
        """Test getting environment information."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir)
            manager = ConfigManager(config_path=config_path, environment="staging")
            
            env_info = manager.get_environment_info()
            
            assert env_info["environment"] == "staging"
            assert env_info["config_path"] == str(config_path)
            assert env_info["loaded"] is False
            assert "development" in env_info["available_environments"]
            assert "staging" in env_info["available_environments"]
            assert "production" in env_info["available_environments"]


class TestGlobalConfigFunctions:
    """Test cases for global configuration functions."""
    
    def test_get_config_manager_singleton(self):
        """Test that get_config_manager returns the same instance."""
        manager1 = get_config_manager()
        manager2 = get_config_manager()
        
        assert manager1 is manager2
    
    def test_get_config_function(self):
        """Test the global get_config function."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir)
            
            # Reset the global manager
            import src.config.manager as manager_module
            manager_module._config_manager = None
            
            # Create new manager with test path
            manager = ConfigManager(config_path=config_path, environment="development")
            manager_module._config_manager = manager
            
            # Test getting specific config value
            log_level = get_config("logging.level")
            assert log_level == "DEBUG"
            
            # Test getting complete config
            full_config = get_config()
            assert isinstance(full_config, dict)
            assert "environment" in full_config
            assert "logging" in full_config


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
