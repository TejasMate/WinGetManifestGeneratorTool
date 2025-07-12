"""Configuration management package for WinGetManifestAutomationTool.

This package provides centralized configuration management with support for:
- Environment-specific configurations (development/staging/production)
- Configuration validation using schemas
- Multiple configuration sources (files, environment variables)
- Configuration merging and inheritance

Usage:
    from src.config import get_config, get_config_manager
    
    # Get a specific configuration value
    github_tokens = get_config('github.tokens', [])
    
    # Get the complete configuration
    config = get_config()
    
    # Use the configuration manager directly
    manager = get_config_manager()
    config = manager.load_config()
"""

from .manager import ConfigManager, get_config_manager, get_config
from .schema import ConfigSchema

__all__ = [
    'ConfigManager',
    'ConfigSchema', 
    'get_config_manager',
    'get_config'
]
