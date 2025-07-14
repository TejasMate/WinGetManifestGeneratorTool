"""Constants and configuration values for WinGet Manifest Generator Tool."""

from enum import Enum
from typing import Dict, List


# API Configuration
DEFAULT_TIMEOUT = 30  # seconds
MAX_RETRIES = 3
API_RATE_LIMIT = 5000  # requests per hour
DEFAULT_USER_AGENT = "WinGet-Manifest-Generator-Tool/1.0.0"

# GitHub API Configuration
GITHUB_API_BASE_URL = "https://api.github.com"
GITHUB_RAW_CONTENT_URL = "https://raw.githubusercontent.com"
GITHUB_RELEASES_ENDPOINT = "/repos/{owner}/{repo}/releases"
GITHUB_CONTENTS_ENDPOINT = "/repos/{owner}/{repo}/contents/{path}"

# WinGet Configuration
WINGET_REPO_URL = "https://github.com/microsoft/winget-pkgs"
WINGET_MANIFESTS_PATH = "manifests"
SUPPORTED_MANIFEST_VERSIONS = ["1.0.0", "1.1.0", "1.2.0", "1.4.0", "1.5.0", "1.6.0"]
DEFAULT_MANIFEST_VERSION = "1.6.0"

# File Patterns
INSTALLER_MANIFEST_PATTERN = "*.installer.yaml"
LOCALE_MANIFEST_PATTERN = "*.locale.*.yaml"
VERSION_MANIFEST_PATTERN = "*.yaml"
MANIFEST_EXTENSIONS = [".yaml", ".yml"]

# Processing Configuration
DEFAULT_BATCH_SIZE = 100
MAX_CONCURRENT_REQUESTS = 10
CACHE_TTL = 3600  # 1 hour in seconds
MAX_CACHE_SIZE = 1000

# Monitoring Configuration
DEFAULT_LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
METRICS_PREFIX = "winget_manifest_generator"
HEALTH_CHECK_ENDPOINTS = [
    "https://api.github.com/zen",  # GitHub API health
    "https://httpbin.org/status/200"  # General connectivity
]

# Validation Configuration
REQUIRED_MANIFEST_FIELDS = [
    "PackageIdentifier",
    "PackageVersion", 
    "PackageLocale",
    "Publisher",
    "PackageName",
    "License",
    "ShortDescription",
    "ManifestType",
    "ManifestVersion"
]

OPTIONAL_MANIFEST_FIELDS = [
    "Author",
    "Description",
    "Homepage",
    "LicenseUrl",
    "Copyright",
    "CopyrightUrl",
    "Tags",
    "Category",
    "Moniker",
    "ReleaseNotes",
    "ReleaseNotesUrl"
]


class ManifestType(Enum):
    """Enumeration of manifest types."""
    VERSION = "version"
    INSTALLER = "installer"
    LOCALE = "locale"
    SINGLETON = "singleton"


class ProcessingStatus(Enum):
    """Enumeration of processing statuses."""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class LogLevel(Enum):
    """Enumeration of log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# Schema Templates
MANIFEST_SCHEMAS = {
    "installer": {
        "type": "object",
        "required": [
            "PackageIdentifier",
            "PackageVersion",
            "Installers",
            "ManifestType", 
            "ManifestVersion"
        ],
        "properties": {
            "PackageIdentifier": {"type": "string"},
            "PackageVersion": {"type": "string"},
            "Installers": {"type": "array"},
            "ManifestType": {"type": "string", "enum": ["installer"]},
            "ManifestVersion": {"type": "string"}
        }
    },
    "locale": {
        "type": "object", 
        "required": [
            "PackageIdentifier",
            "PackageVersion",
            "PackageLocale",
            "Publisher",
            "PackageName",
            "License",
            "ShortDescription",
            "ManifestType",
            "ManifestVersion"
        ],
        "properties": {
            "PackageIdentifier": {"type": "string"},
            "PackageVersion": {"type": "string"},
            "PackageLocale": {"type": "string"},
            "Publisher": {"type": "string"},
            "PackageName": {"type": "string"},
            "License": {"type": "string"},
            "ShortDescription": {"type": "string"},
            "ManifestType": {"type": "string", "enum": ["defaultLocale", "locale"]},
            "ManifestVersion": {"type": "string"}
        }
    },
    "version": {
        "type": "object",
        "required": [
            "PackageIdentifier", 
            "PackageVersion",
            "DefaultLocale",
            "ManifestType",
            "ManifestVersion"
        ],
        "properties": {
            "PackageIdentifier": {"type": "string"},
            "PackageVersion": {"type": "string"}, 
            "DefaultLocale": {"type": "string"},
            "ManifestType": {"type": "string", "enum": ["version"]},
            "ManifestVersion": {"type": "string"}
        }
    }
}

# Error Messages
ERROR_MESSAGES = {
    "INVALID_PACKAGE_ID": "Invalid package identifier format",
    "MISSING_REQUIRED_FIELD": "Required field '{field}' is missing",
    "INVALID_VERSION": "Invalid version format",
    "GITHUB_API_ERROR": "GitHub API request failed",
    "MANIFEST_VALIDATION_ERROR": "Manifest validation failed",
    "FILE_NOT_FOUND": "Required file not found: {filename}",
    "PERMISSION_DENIED": "Permission denied accessing: {path}",
    "NETWORK_ERROR": "Network connectivity error",
    "RATE_LIMIT_EXCEEDED": "API rate limit exceeded"
}

# Success Messages
SUCCESS_MESSAGES = {
    "PACKAGE_PROCESSED": "Package processed successfully",
    "MANIFEST_GENERATED": "Manifest generated successfully", 
    "VALIDATION_PASSED": "Validation completed successfully",
    "FILE_SAVED": "File saved successfully: {filename}",
    "BATCH_COMPLETED": "Batch processing completed: {count} packages"
}
