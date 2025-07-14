"""Configuration management system for WinGet Manifest Generator Tool."""

import os
import json
import yaml
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field

try:
    from .schema import ConfigSchema
    from ..exceptions import ConfigurationError
except ImportError:
    # Fallback for direct script execution
    import sys
    sys.path.append(str(Path(__file__).parent.parent))
    from .schema import ConfigSchema
    from exceptions import ConfigurationError


@dataclass
class EnvironmentConfig:
    """Environment-specific configuration settings."""
    
    name: str
    debug: bool = False
    log_level: str = "INFO"
    cache_enabled: bool = True
    max_workers: int = 4
    batch_size: int = 100
    timeout: int = 300


class ConfigManager:
    """Centralized configuration management system.
    
    This class provides a centralized way to manage configuration for the
    WinGet Manifest Generator Tool with support for:
    - Environment-specific configurations (dev/staging/prod)
    - Configuration validation using schemas
    - Multiple configuration sources (files, environment variables)
    - Configuration merging and inheritance
    """
    
    def __init__(self, config_path: Optional[Union[str, Path]] = None, 
                 environment: Optional[str] = None):
        """Initialize the configuration manager.
        
        Args:
            config_path: Path to the configuration file or directory
            environment: Environment name (development/staging/production)
        """
        self.config_path = Path(config_path) if config_path else self._get_default_config_path()
        self.environment = environment or self._detect_environment()
        self.schema = ConfigSchema()
        self._config: Dict[str, Any] = {}
        self._loaded = False
        
        # Environment-specific defaults
        self.env_configs = {
            "development": EnvironmentConfig(
                name="development",
                debug=True,
                log_level="DEBUG",
                cache_enabled=False,
                max_workers=2,
                batch_size=50,
                timeout=60
            ),
            "staging": EnvironmentConfig(
                name="staging",
                debug=False,
                log_level="INFO",
                cache_enabled=True,
                max_workers=4,
                batch_size=100,
                timeout=300
            ),
            "production": EnvironmentConfig(
                name="production",
                debug=False,
                log_level="WARNING",
                cache_enabled=True,
                max_workers=8,
                batch_size=500,
                timeout=600
            )
        }
    
    def _get_default_config_path(self) -> Path:
        """Get the default configuration path."""
        # Look for config.yaml in various locations
        possible_paths = [
            Path.cwd() / "config" / "config.yaml",
            Path.cwd() / "config.yaml",
            Path(__file__).parent.parent.parent / "config" / "config.yaml",
            Path.home() / ".winget-automation" / "config.yaml",
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
        
        # Default to config directory in project root
        return Path(__file__).parent.parent.parent / "config"
    
    def _detect_environment(self) -> str:
        """Detect the current environment."""
        env = os.getenv("ENVIRONMENT", os.getenv("WINGET_ENV", "development")).lower()
        
        if env in ["prod", "production"]:
            return "production"
        elif env in ["stage", "staging"]:
            return "staging"
        else:
            return "development"
    
    def load_config(self, force_reload: bool = False) -> Dict[str, Any]:
        """Load configuration from unified config file.
        
        Args:
            force_reload: Force reload even if already loaded
            
        Returns:
            Complete configuration dictionary
            
        Raises:
            ConfigurationError: If configuration loading or validation fails
        """
        if self._loaded and not force_reload:
            return self._config
        
        try:
            # Load unified configuration file
            config = self._load_unified_config()
            
            # Apply environment-specific overrides
            config = self._apply_environment_overrides(config)
            
            # Override with environment variables
            env_overrides = self._load_environment_variables()
            config = self._merge_configs(config, env_overrides)
            
            # Validate configuration (non-blocking during load)
            is_valid, errors = self.schema.validate(config)
            if not is_valid:
                # Log validation errors but don't fail loading
                logger = logging.getLogger(__name__)
                logger.warning(f"Configuration validation issues: {'; '.join(errors)}")
            
            self._config = config
            self._loaded = True
            
            return self._config
        
        except Exception as e:
            if isinstance(e, ConfigurationError):
                raise
            raise ConfigurationError(f"Failed to load configuration: {str(e)}")
    
    def _get_environment_defaults(self) -> Dict[str, Any]:
        """Get default configuration for the current environment."""
        env_config = self.env_configs.get(self.environment)
        if not env_config:
            raise ConfigurationError(f"Unknown environment: {self.environment}")
        
        return {
            "environment": env_config.name,
            "debug": env_config.debug,
            "logging": {
                "level": env_config.log_level,
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "file": None,
                "max_size": 10,
                "backup_count": 5
            },
            "github": {
                "tokens": [],
                "api_url": "https://api.github.com",
                "per_page": 100,
                "retry_attempts": 3,
                "retry_delay": 1.0,
                "rate_limit_buffer": 100
            },
            "package_processing": {
                "winget_repo_path": "winget-pkgs",
                "output_directory": "data",
                "file_patterns": ["*.installer.yaml"],
                "max_workers": env_config.max_workers,
                "batch_size": env_config.batch_size,
                "timeout": env_config.timeout
            },
            "filtering": {
                "blocked_packages": [],
                "allowed_architectures": [
                    "x64", "x86", "arm64", "arm", "aarch64", "x86_64"
                ],
                "allowed_extensions": [
                    "msi", "exe", "zip", "msix", "appx", "msixbundle", "appxbundle"
                ],
                "min_download_count": 0,
                "max_package_age_days": 365
            },
            "output": {
                "formats": ["csv"],
                "compression": "none",
                "include_metadata": True,
                "timestamp_format": "%Y%m%d_%H%M%S"
            },
            "performance": {
                "cache_enabled": env_config.cache_enabled,
                "cache_ttl": 3600,
                "memory_limit_mb": 1024,
                "enable_profiling": env_config.debug
            }
        }
    
    def _load_base_config(self) -> Dict[str, Any]:
        """Load base configuration file."""
        base_files = ["config.yaml", "config.yml", "config.json"]
        
        for filename in base_files:
            file_path = self.config_path / filename
            if file_path.exists():
                return self._load_config_file(file_path)
        
        # No base config file found, return empty dict
        return {}
    
    def _load_environment_config(self) -> Dict[str, Any]:
        """Load environment-specific configuration file."""
        env_files = [
            f"config.{self.environment}.yaml",
            f"config.{self.environment}.yml",
            f"config.{self.environment}.json",
            f"{self.environment}.yaml",
            f"{self.environment}.yml",
            f"{self.environment}.json"
        ]
        
        for filename in env_files:
            file_path = self.config_path / filename
            if file_path.exists():
                return self._load_config_file(file_path)
        
        # No environment-specific config found, return empty dict
        return {}
    
    def _load_config_file(self, file_path: Path) -> Dict[str, Any]:
        """Load configuration from a file.
        
        Args:
            file_path: Path to the configuration file
            
        Returns:
            Configuration dictionary
            
        Raises:
            ConfigurationError: If file cannot be loaded or parsed
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.suffix.lower() == '.json':
                    return json.load(f)
                else:  # Assume YAML
                    return yaml.safe_load(f) or {}
        except Exception as e:
            raise ConfigurationError(f"Failed to load config file {file_path}: {str(e)}")
    
    def _load_unified_config(self) -> Dict[str, Any]:
        """Load the unified configuration file."""
        if not self.config_path.exists():
            raise ConfigurationError(f"Configuration file not found: {self.config_path}")
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if not config:
                raise ConfigurationError("Configuration file is empty")
            
            return config
        
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML in configuration file: {e}")
        except Exception as e:
            raise ConfigurationError(f"Failed to read configuration file: {e}")
    
    def _apply_environment_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment-specific overrides from the unified config."""
        # Get environment from config or use detected environment
        env = config.get("environment", self.environment)
        
        # Apply environment-specific overrides if they exist
        environments = config.get("environments", {})
        env_overrides = environments.get(env, {})
        
        if env_overrides:
            config = self._merge_configs(config, env_overrides)
        
        return config

    def _load_environment_variables(self) -> Dict[str, Any]:
        """Load configuration overrides from environment variables."""
        overrides = {}
        
        # GitHub tokens
        github_tokens = []
        i = 1
        while True:
            token = os.getenv(f"TOKEN_{i}")
            if not token:
                # Check for legacy TOKEN variable
                if i == 1:
                    legacy_token = os.getenv("TOKEN")
                    if legacy_token:
                        github_tokens.append(legacy_token)
                break
            github_tokens.append(token)
            i += 1
        
        if github_tokens:
            overrides.setdefault("github", {})["tokens"] = github_tokens
        
        # Other environment variables
        env_mappings = {
            "WINGET_REPO_PATH": ("package_processing", "winget_repo_path"),
            "OUTPUT_DIR": ("package_processing", "output_directory"),
            "LOG_LEVEL": ("logging", "level"),
            "LOG_FILE": ("logging", "file"),
            "MAX_WORKERS": ("package_processing", "max_workers"),
            "BATCH_SIZE": ("package_processing", "batch_size"),
            "TIMEOUT": ("package_processing", "timeout"),
            "CACHE_ENABLED": ("performance", "cache_enabled"),
            "CACHE_TTL": ("performance", "cache_ttl"),
            "DEBUG": ("debug",),
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                # Convert value to appropriate type
                value = self._convert_env_value(value)
                
                # Set nested configuration value
                current = overrides
                for key in config_path[:-1]:
                    current = current.setdefault(key, {})
                current[config_path[-1]] = value
        
        return overrides
    
    def _convert_env_value(self, value: str) -> Union[str, int, float, bool]:
        """Convert environment variable string to appropriate type."""
        # Try boolean
        if value.lower() in ("true", "false"):
            return value.lower() == "true"
        
        # Try integer
        try:
            if "." not in value:
                return int(value)
        except ValueError:
            pass
        
        # Try float
        try:
            return float(value)
        except ValueError:
            pass
        
        # Return as string
        return value
    
    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Merge two configuration dictionaries recursively.
        
        Args:
            base: Base configuration
            override: Override configuration
            
        Returns:
            Merged configuration
        """
        result = base.copy()
        
        for key, value in override.items():
            if (key in result and 
                isinstance(result[key], dict) and 
                isinstance(value, dict)):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value using dot notation.
        
        Args:
            key: Configuration key (e.g., 'github.tokens')
            default: Default value if key is not found
            
        Returns:
            Configuration value
        """
        if not self._loaded:
            self.load_config()
        
        keys = key.split('.')
        current = self._config
        
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        
        return current
    
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value using dot notation.
        
        Args:
            key: Configuration key (e.g., 'github.tokens')
            value: Value to set
        """
        if not self._loaded:
            self.load_config()
        
        keys = key.split('.')
        current = self._config
        
        for k in keys[:-1]:
            current = current.setdefault(k, {})
        
        current[keys[-1]] = value
    
    def save_config(self, file_path: Optional[Path] = None, format: str = "yaml") -> None:
        """Save current configuration to file.
        
        Args:
            file_path: Path to save configuration to
            format: File format ("yaml" or "json")
            
        Raises:
            ConfigurationError: If saving fails
        """
        if not self._loaded:
            self.load_config()
        
        if file_path is None:
            file_path = self.config_path / f"config.{self.environment}.{format}"
        
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                if format.lower() == "json":
                    json.dump(self._config, f, indent=2, sort_keys=True)
                else:  # YAML
                    yaml.dump(self._config, f, default_flow_style=False, sort_keys=True)
        
        except Exception as e:
            raise ConfigurationError(f"Failed to save config to {file_path}: {str(e)}")
    
    def validate_config(self, config: Optional[Dict[str, Any]] = None) -> tuple[bool, List[str]]:
        """Validate configuration against schema.
        
        Args:
            config: Configuration to validate (uses current config if None)
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        if config is None:
            if not self._loaded:
                self.load_config()
            config = self._config
        
        return self.schema.validate(config)
    
    def get_environment_info(self) -> Dict[str, Any]:
        """Get information about the current environment.
        
        Returns:
            Environment information dictionary
        """
        return {
            "environment": self.environment,
            "config_path": str(self.config_path),
            "loaded": self._loaded,
            "available_environments": list(self.env_configs.keys()),
            "config_files_found": self._get_available_config_files()
        }
    
    def _get_available_config_files(self) -> List[str]:
        """Get list of available configuration files."""
        if not self.config_path.exists():
            return []
        
        config_files = []
        patterns = ["config.*", "*.yaml", "*.yml", "*.json"]
        
        for pattern in patterns:
            config_files.extend([f.name for f in self.config_path.glob(pattern)])
        
        return sorted(list(set(config_files)))
    
    @property
    def config(self) -> Dict[str, Any]:
        """Get the complete configuration dictionary."""
        if not self._loaded:
            self.load_config()
        return self._config.copy()
    
    def update_config(self, updates: Dict[str, Any]) -> None:
        """Update configuration with new values.
        
        Args:
            updates: Dictionary of configuration updates
        """
        if not self._loaded:
            self.load_config()
        
        # Merge updates into current config
        self._config = self._merge_configs(self._config, updates)
        
        # Save updated configuration
        self.save_config()
    
    def get_status(self) -> Dict[str, Any]:
        """Get configuration status information.
        
        Returns:
            Dictionary with configuration status details
        """
        if not self._loaded:
            self.load_config()
        
        is_valid, errors = self.validate_config()
        
        return {
            'config_file': str(self.config_path),
            'last_modified': self.config_path.stat().st_mtime if self.config_path.exists() else None,
            'valid': is_valid,
            'errors': errors,
            'environment': self.environment,
            'loaded': self._loaded
        }
    
    def validate_detailed(self) -> Dict[str, Dict[str, Any]]:
        """Perform detailed configuration validation.
        
        Returns:
            Dictionary with detailed validation results by section
        """
        if not self._loaded:
            self.load_config()
        
        # This is a simplified version - in a real implementation,
        # you'd validate each section separately
        is_valid, errors = self.validate_config()
        
        results = {}
        
        # Check each major configuration section
        for section_name in ['github', 'processing', 'monitoring', 'output']:
            section_config = self._config.get(section_name, {})
            section_valid = isinstance(section_config, dict)
            
            results[section_name] = {
                'configuration_present': {
                    'valid': section_name in self._config,
                    'message': f'{section_name} configuration found' if section_name in self._config else f'{section_name} configuration missing'
                },
                'structure_valid': {
                    'valid': section_valid,
                    'message': f'{section_name} structure is valid' if section_valid else f'{section_name} structure is invalid'
                }
            }
        
        return results


# Global configuration manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager(config_path: Optional[Union[str, Path]] = None,
                      environment: Optional[str] = None) -> ConfigManager:
    """Get the global configuration manager instance.
    
    Args:
        config_path: Path to configuration files
        environment: Environment name
        
    Returns:
        ConfigManager instance
    """
    global _config_manager
    
    if _config_manager is None:
        _config_manager = ConfigManager(config_path, environment)
    
    return _config_manager


def get_config(key: str = None, default: Any = None) -> Any:
    """Get configuration value(s).
    
    Args:
        key: Configuration key using dot notation (e.g., 'github.tokens')
        default: Default value if key is not found
        
    Returns:
        Configuration value or complete config if key is None
    """
    manager = get_config_manager()
    
    if key is None:
        return manager.config
    
    return manager.get(key, default)
