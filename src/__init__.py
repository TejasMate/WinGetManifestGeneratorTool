"""
WinGet Manifest Generator Tool - Professional automation suite for WinGet package management.

This package provides a comprehensive set of tools for automating the creation,
validation, and maintenance of WinGet package manifests with enterprise-grade
monitoring and observability features.
"""

__version__ = "1.0.0"
__author__ = "TejasMate"
__email__ = "tejasmate@example.com"
__description__ = "Professional generator tool for managing and updating WinGet package manifests"
__url__ = "https://github.com/TejasMate/WinGetManifestGeneratorTool"

# Public API
from .exceptions import (
    WinGetAutomationError,
    ConfigurationError,
    GitHubAPIError,
    PackageProcessingError,
    DataValidationError
)

__all__ = [
    "WinGetAutomationError",
    "ConfigurationError", 
    "GitHubAPIError",
    "PackageProcessingError",
    "DataValidationError"
]
