"""Pytest configuration and fixtures."""

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from typing import Generator, Dict, Any

import polars as pl
import yaml

# Test fixtures directory
FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def sample_manifest_data() -> Dict[str, Any]:
    """Sample WinGet manifest data for testing."""
    return {
        "PackageIdentifier": "Microsoft.PowerToys",
        "PackageVersion": "0.75.1",
        "PackageName": "PowerToys",
        "Publisher": "Microsoft Corporation",
        "License": "MIT",
        "ShortDescription": "Windows system utilities to maximize productivity",
        "Installers": [
            {
                "Architecture": "x64",
                "InstallerType": "msi",
                "InstallerUrl": "https://github.com/microsoft/PowerToys/releases/download/v0.75.1/PowerToysSetup-0.75.1-x64.msi",
                "InstallerSha256": "ABC123",
            },
            {
                "Architecture": "arm64",
                "InstallerType": "msi",
                "InstallerUrl": "https://github.com/microsoft/PowerToys/releases/download/v0.75.1/PowerToysSetup-0.75.1-arm64.msi",
                "InstallerSha256": "DEF456",
            },
        ],
    }


@pytest.fixture
def sample_manifest_file(temp_dir: Path, sample_manifest_data: Dict[str, Any]) -> Path:
    """Create a sample manifest file for testing."""
    manifest_file = temp_dir / "Microsoft.PowerToys.installer.yaml"
    with open(manifest_file, "w") as f:
        yaml.dump(sample_manifest_data, f)
    return manifest_file


@pytest.fixture
def sample_package_dataframe() -> pl.DataFrame:
    """Sample package DataFrame for testing."""
    return pl.DataFrame(
        {
            "PackageIdentifier": [
                "Microsoft.PowerToys",
                "Google.Chrome",
                "Mozilla.Firefox",
            ],
            "PackageVersion": ["0.75.1", "118.0.5993.117", "119.0.1"],
            "GitHubURL": [
                "https://github.com/microsoft/PowerToys",
                "https://github.com/chromium/chromium",
                "https://github.com/mozilla/gecko-dev",
            ],
            "InstallerUrl": [
                "https://github.com/microsoft/PowerToys/releases/download/v0.75.1/PowerToysSetup-0.75.1-x64.msi",
                "https://dl.google.com/chrome/install/chrome_installer.exe",
                "https://download.mozilla.org/?product=firefox-latest&os=win&lang=en-US",
            ],
        }
    )


@pytest.fixture
def mock_github_response() -> Dict[str, Any]:
    """Mock GitHub API response for testing."""
    return {
        "tag_name": "v0.76.0",
        "name": "PowerToys v0.76.0",
        "published_at": "2023-11-15T10:00:00Z",
        "assets": [
            {
                "name": "PowerToysSetup-0.76.0-x64.msi",
                "browser_download_url": "https://github.com/microsoft/PowerToys/releases/download/v0.76.0/PowerToysSetup-0.76.0-x64.msi",
                "size": 12345678,
                "download_count": 1000,
            },
            {
                "name": "PowerToysSetup-0.76.0-arm64.msi",
                "browser_download_url": "https://github.com/microsoft/PowerToys/releases/download/v0.76.0/PowerToysSetup-0.76.0-arm64.msi",
                "size": 12345678,
                "download_count": 500,
            },
        ],
    }


@pytest.fixture
def mock_token_manager():
    """Mock TokenManager for testing."""
    with patch("src.utils.token_manager.TokenManager") as mock:
        mock_instance = Mock()
        mock_instance.get_available_token.return_value = "test_token_123"
        mock_instance.tokens = ["test_token_123", "test_token_456"]
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_github_api():
    """Mock GitHub API for testing."""
    with patch("requests.get") as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            "X-RateLimit-Remaining": "4999",
            "X-RateLimit-Reset": "1699200000",
        }
        mock_get.return_value = mock_response
        yield mock_get


@pytest.fixture(scope="session")
def sample_winget_repo(tmp_path_factory) -> Path:
    """Create a sample WinGet repository structure for testing."""
    base_dir = tmp_path_factory.mktemp("winget-pkgs")
    manifests_dir = base_dir / "manifests"

    # Create directory structure
    (manifests_dir / "m" / "Microsoft" / "PowerToys" / "0.75.1").mkdir(parents=True)
    (manifests_dir / "g" / "Google" / "Chrome" / "118.0.5993.117").mkdir(parents=True)

    # Create sample manifest files
    powertoys_manifest = {
        "PackageIdentifier": "Microsoft.PowerToys",
        "PackageVersion": "0.75.1",
        "Installers": [
            {
                "InstallerUrl": "https://github.com/microsoft/PowerToys/releases/download/v0.75.1/PowerToysSetup-0.75.1-x64.msi"
            }
        ],
    }

    chrome_manifest = {
        "PackageIdentifier": "Google.Chrome",
        "PackageVersion": "118.0.5993.117",
        "Installers": [
            {
                "InstallerUrl": "https://dl.google.com/chrome/install/chrome_installer.exe"
            }
        ],
    }

    with open(
        manifests_dir
        / "m"
        / "Microsoft"
        / "PowerToys"
        / "0.75.1"
        / "Microsoft.PowerToys.installer.yaml",
        "w",
    ) as f:
        yaml.dump(powertoys_manifest, f)

    with open(
        manifests_dir
        / "g"
        / "Google"
        / "Chrome"
        / "118.0.5993.117"
        / "Google.Chrome.installer.yaml",
        "w",
    ) as f:
        yaml.dump(chrome_manifest, f)

    return base_dir


@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment variables for each test."""
    # Store original values
    original_env = dict(os.environ)

    # Set test environment variables
    os.environ.update(
        {
            "TOKEN_1": "test_token_1",
            "TOKEN_2": "test_token_2",
        }
    )

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


class MockGitHubAPI:
    """Mock GitHub API class for testing."""

    def __init__(self, responses=None):
        self.responses = responses or {}
        self.call_count = 0

    def get_latest_release(self, owner: str, repo: str):
        """Mock get_latest_release method."""
        self.call_count += 1
        key = f"{owner}/{repo}"
        if key in self.responses:
            return self.responses[key]
        raise Exception(f"No mock response for {key}")

    def get_releases(self, owner: str, repo: str, per_page: int = 30):
        """Mock get_releases method."""
        self.call_count += 1
        return self.responses.get(f"{owner}/{repo}/releases", [])


@pytest.fixture
def mock_github_api_class():
    """Fixture providing MockGitHubAPI class."""
    return MockGitHubAPI
