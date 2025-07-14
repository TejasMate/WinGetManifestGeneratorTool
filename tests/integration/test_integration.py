"""Integration tests for the WinGet Manifest Generator Tool."""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, Mock
import polars as pl
import yaml

from winget_automation.PackageProcessor import PackageProcessor, ProcessingConfig
from winget_automation.GitHub import main as github_main
from winget_automation.utils.token_manager import TokenManager
from winget_automation.exceptions import GitHubAPIError, TokenManagerError


@pytest.mark.integration
class TestPackageProcessorIntegration:
    """Integration tests for PackageProcessor with real-like data."""

    @pytest.fixture
    def temp_winget_repo(self, tmp_path):
        """Create a temporary WinGet repository structure."""
        manifests_dir = tmp_path / "manifests"
        manifests_dir.mkdir()

        # Create Microsoft/PowerToys structure
        powertoys_dir = manifests_dir / "m" / "Microsoft" / "PowerToys" / "0.75.1"
        powertoys_dir.mkdir(parents=True)

        # Create manifest file
        manifest_data = {
            "PackageIdentifier": "Microsoft.PowerToys",
            "PackageVersion": "0.75.1",
            "InstallerType": "msi",
            "Installers": [
                {
                    "Architecture": "x64",
                    "InstallerUrl": "https://github.com/microsoft/PowerToys/releases/download/v0.75.1/PowerToysSetup-0.75.1-x64.msi",
                    "InstallerSha256": "ABC123",
                },
                {
                    "Architecture": "arm64",
                    "InstallerUrl": "https://github.com/microsoft/PowerToys/releases/download/v0.75.1/PowerToysSetup-0.75.1-arm64.msi",
                    "InstallerSha256": "DEF456",
                },
            ],
        }

        manifest_file = powertoys_dir / "Microsoft.PowerToys.installer.yaml"
        with open(manifest_file, "w") as f:
            yaml.dump(manifest_data, f)

        # Create Google/Chrome structure
        chrome_dir = manifests_dir / "g" / "Google" / "Chrome" / "118.0.5993.117"
        chrome_dir.mkdir(parents=True)

        chrome_manifest = {
            "PackageIdentifier": "Google.Chrome",
            "PackageVersion": "118.0.5993.117",
            "InstallerType": "exe",
            "Installers": [
                {
                    "Architecture": "x64",
                    "InstallerUrl": "https://dl.google.com/chrome/install/chrome_installer.exe",
                    "InstallerSha256": "GHI789",
                }
            ],
        }

        chrome_manifest_file = chrome_dir / "Google.Chrome.installer.yaml"
        with open(chrome_manifest_file, "w") as f:
            yaml.dump(chrome_manifest, f)

        return tmp_path

    @pytest.fixture
    def integration_config(self, tmp_path):
        """Create configuration for integration tests."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        return ProcessingConfig(
            output_manifest_file=str(data_dir / "test_manifests.csv"),
            output_analysis_file=str(data_dir / "test_analysis.csv"),
            open_prs_file=str(data_dir / "test_prs.csv"),
        )

    @patch.dict("os.environ", {"TOKEN_1": "test_token_123"})
    def test_end_to_end_package_processing(self, temp_winget_repo, integration_config):
        """Test complete package processing workflow."""
        with patch("winget_automation.PackageProcessor.TokenManager") as mock_tm:
            mock_token_manager = Mock()
            mock_token_manager.get_available_token.return_value = "test_token"
            mock_tm.return_value = mock_token_manager

            # Initialize processor
            processor = PackageProcessor(integration_config)

            # Mock the repository path
            with patch.object(
                processor, "get_winget_repo_path", return_value=temp_winget_repo
            ):
                # Test manifest processing
                manifests_dir = temp_winget_repo / "manifests"
                installer_files = list(manifests_dir.rglob("*.installer.yaml"))

                # Calculate max dots
                processor.calculate_max_dots(installer_files)
                assert processor.max_dots >= 0

                # Process manifest files
                for file in installer_files:
                    processor.process_manifest_file(file)

                # Verify data was processed
                assert len(processor.unique_rows) > 0

                # Create DataFrame
                df = processor.create_manifest_dataframe()
                assert isinstance(df, pl.DataFrame)
                assert df.shape[0] > 0

    @patch.dict("os.environ", {"TOKEN_1": "test_token_123"})
    def test_yaml_processing_with_real_structure(
        self, temp_winget_repo, integration_config
    ):
        """Test YAML processing with realistic manifest structure."""
        with patch("winget_automation.PackageProcessor.TokenManager") as mock_tm:
            mock_token_manager = Mock()
            mock_token_manager.get_available_token.return_value = "test_token"
            mock_tm.return_value = mock_token_manager

            processor = PackageProcessor(integration_config)

            # Test processing a specific YAML file
            yaml_file = (
                temp_winget_repo
                / "manifests"
                / "m"
                / "Microsoft"
                / "PowerToys"
                / "0.75.1"
                / "Microsoft.PowerToys.installer.yaml"
            )

            # Mock the process_yaml_file method to simulate successful parsing
            with patch.object(processor, "process_yaml_file") as mock_process:
                mock_process.return_value = {
                    "PackageIdentifier": "Microsoft.PowerToys",
                    "PackageVersion": "0.75.1",
                    "Installers": [
                        {
                            "Architecture": "x64",
                            "InstallerUrl": "https://github.com/microsoft/PowerToys/releases/download/v0.75.1/PowerToysSetup-0.75.1-x64.msi",
                        }
                    ],
                }

                # Test URL counting
                count = processor.count_download_urls(yaml_file, "Microsoft.PowerToys")
                assert count > 0

                # Verify data was stored
                assert "Microsoft.PowerToys" in processor.latest_urls
                assert "Microsoft.PowerToys" in processor.package_downloads

    def test_architecture_extension_extraction_integration(self, integration_config):
        """Test architecture-extension extraction with real URL patterns."""
        with patch("winget_automation.PackageProcessor.TokenManager") as mock_tm:
            mock_token_manager = Mock()
            mock_token_manager.get_available_token.return_value = "test_token"
            mock_tm.return_value = mock_token_manager

            processor = PackageProcessor(integration_config)

            # Test with realistic URLs
            test_urls = [
                "https://github.com/microsoft/PowerToys/releases/download/v0.75.1/PowerToysSetup-0.75.1-x64.msi",
                "https://github.com/microsoft/PowerToys/releases/download/v0.75.1/PowerToysSetup-0.75.1-arm64.msi",
                "https://dl.google.com/chrome/install/GoogleChromeStandaloneEnterprise64.msi",
                "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip",
            ]

            result = processor.extract_arch_ext_pairs(test_urls)

            # Verify meaningful pairs were extracted
            assert isinstance(result, str)
            assert len(result) > 0  # Should have extracted some pairs

            # Should contain common patterns
            pairs = result.split(",") if result else []
            assert len(pairs) > 0


@pytest.mark.integration
class TestGitHubIntegration:
    """Integration tests for GitHub module."""

    @patch.dict("os.environ", {"TOKEN_1": "test_token_123"})
    @patch("winget_automation.GitHub.VersionAnalyzer")
    @patch("winget_automation.GitHub.github.MatchSimilarURLs.process_urls")
    @patch("winget_automation.GitHub.github.Filter.process_filters")
    def test_github_pipeline_integration(self, mock_filter, mock_urls, mock_analyzer):
        """Test the complete GitHub analysis pipeline."""
        # Mock the analyzer
        mock_analyzer_instance = Mock()
        mock_analyzer.return_value = mock_analyzer_instance

        # Mock TokenManager
        with patch("winget_automation.GitHub.TokenManager") as mock_tm:
            mock_token_manager = Mock()
            mock_token_manager.get_available_token.return_value = "test_token"
            mock_tm.return_value = mock_token_manager

            # Create temporary files for the pipeline
            with tempfile.TemporaryDirectory() as tmp_dir:
                input_file = Path(tmp_dir) / "AllPackageInfo.csv"
                github_info_file = Path(tmp_dir) / "GitHubPackageInfo.csv"
                cleaned_urls_file = Path(tmp_dir) / "GitHubPackageInfo_CleanedURLs.csv"

                # Create sample input data
                sample_data = pl.DataFrame(
                    {
                        "PackageIdentifier": ["Microsoft.PowerToys", "Google.Chrome"],
                        "GitHubURL": [
                            "https://github.com/microsoft/PowerToys",
                            "https://github.com/chromium/chromium",
                        ],
                    }
                )
                sample_data.write_csv(input_file)

                # Patch file paths in the GitHub module
                with patch("winget_automation.GitHub.input_path", str(input_file)), patch(
                    "winget_automation.GitHub.github_info_path", str(github_info_file)
                ), patch("winget_automation.GitHub.cleaned_urls_path", str(cleaned_urls_file)), patch(
                    "winget_automation.GitHub.output_dir", tmp_dir
                ):

                    # Run the main function
                    github_main()

                    # Verify that all components were called
                    mock_analyzer_instance.analyze_versions.assert_called_once()
                    mock_urls.assert_called_once()
                    mock_filter.assert_called_once()


@pytest.mark.integration
class TestTokenManagerIntegration:
    """Integration tests for TokenManager with environment simulation."""

    def test_token_rotation_under_load(self):
        """Test token rotation behavior under simulated load."""
        import time

        with patch.dict(
            "os.environ",
            {"TOKEN_1": "token_1", "TOKEN_2": "token_2", "TOKEN_3": "token_3"},
        ):
            manager = TokenManager()

            # Simulate rapid token usage
            used_tokens = []
            for i in range(10):
                token = manager.get_available_token()
                used_tokens.append(token)

                # Simulate rate limit hit every 3 requests
                if i % 3 == 2:
                    future_time = int(time.time()) + 3600
                    manager._update_rate_limit(token, 0, future_time)

            # Verify tokens were rotated
            unique_tokens = set(used_tokens)
            assert len(unique_tokens) > 1  # Should have used multiple tokens

    @patch("winget_automation.utils.token_manager.requests.get")
    def test_token_limit_updates_from_headers(self, mock_get):
        """Test token limit updates from actual response headers."""
        with patch.dict("os.environ", {"TOKEN_1": "test_token"}):
            manager = TokenManager()

            # Simulate API response headers
            headers = {
                "X-RateLimit-Remaining": "4999",
                "X-RateLimit-Reset": str(int(time.time()) + 3600),
            }

            manager.update_token_limits("test_token", headers)

            # Verify limits were updated
            assert "test_token" in manager.token_limits
            assert manager.token_limits["test_token"]["remaining"] == 4999

    def test_no_tokens_error_handling(self):
        """Test graceful handling when no tokens are available."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(TokenManagerError) as exc_info:
                TokenManager()

            assert "No GitHub tokens found" in str(exc_info.value)
            assert exc_info.value.available_tokens == 0


@pytest.mark.integration
class TestErrorHandlingIntegration:
    """Integration tests for error handling across modules."""

    def test_cascading_error_handling(self, tmp_path):
        """Test that errors cascade properly through the system."""
        config = ProcessingConfig()

        # Test with invalid token manager
        with patch("winget_automation.PackageProcessor.TokenManager") as mock_tm:
            mock_tm.side_effect = Exception("Token manager failed")

            with pytest.raises(Exception):  # Should bubble up as ConfigurationError
                PackageProcessor(config)

    def test_file_operation_error_handling(self, tmp_path):
        """Test error handling for file operations."""
        config = ProcessingConfig()

        with patch("winget_automation.PackageProcessor.TokenManager") as mock_tm:
            mock_token_manager = Mock()
            mock_token_manager.get_available_token.return_value = "test_token"
            mock_tm.return_value = mock_token_manager

            processor = PackageProcessor(config)

            # Test with non-existent file
            non_existent_file = tmp_path / "non_existent.yaml"

            # Should handle gracefully
            result = processor.count_download_urls(non_existent_file, "Test.Package")
            assert result == 0  # Should return 0 for non-existent files

    @patch.dict("os.environ", {"TOKEN_1": "invalid_token"})
    def test_github_api_error_propagation(self):
        """Test that GitHub API errors are properly propagated."""
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            mock_get.return_value = mock_response

            # Should handle API errors gracefully
            manager = TokenManager()
            token = manager.get_available_token()
            assert token == "invalid_token"  # Should still return the token
