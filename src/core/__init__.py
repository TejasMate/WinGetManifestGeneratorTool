"""Core functionality for WinGet Manifest Generator Tool."""

from .base import BaseProcessor
from .interfaces import IPackageProcessor, IManifestGenerator, IConfigProvider
from .constants import (
    DEFAULT_TIMEOUT,
    MAX_RETRIES,
    API_RATE_LIMIT,
    SUPPORTED_MANIFEST_VERSIONS,
    MANIFEST_SCHEMAS
)

__all__ = [
    "BaseProcessor",
    "IPackageProcessor", 
    "IManifestGenerator",
    "IConfigProvider",
    "DEFAULT_TIMEOUT",
    "MAX_RETRIES", 
    "API_RATE_LIMIT",
    "SUPPORTED_MANIFEST_VERSIONS",
    "MANIFEST_SCHEMAS"
]
