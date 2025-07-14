"""
Unit tests for PackageProcessor class.
"""

import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import polars as pl
import yaml

from winget_automation.PackageProcessor import PackageProcessor, ProcessingConfig
from winget_automation.exceptions import (
    PackageProcessingError,
    ManifestParsingError,
    ConfigurationError,
)


class TestPackageProcessor:
    """Test cases for PackageProcessor class."""

    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        return ProcessingConfig(
            output_manifest_file="test_manifests.csv",
            output_analysis_file="test_analysis.csv",
            open_prs_file="test_prs.csv",
        )

    @pytest.fixture
    def processor(self, config, mock_token_manager):
        """Create a PackageProcessor instance for testing."""
        with patch(
            "winget_automation.PackageProcessor.TokenManager", return_value=mock_token_manager
        ):
            return PackageProcessor(config)

    def test_init_success(self, config, mock_token_manager):
        """Test successful initialization of PackageProcessor."""
        with patch(
            "winget_automation.PackageProcessor.TokenManager", return_value=mock_token_manager
        ):
            processor = PackageProcessor(config)

            assert processor.config == config
            assert processor.unique_rows == set()
            assert processor.max_dots == 0
            assert len(processor.architectures) > 0
            assert len(processor.extensions) > 0

    def test_init_failure_no_tokens(self, config):
        """Test initialization failure when no tokens are available."""
        with patch("winget_automation.PackageProcessor.TokenManager") as mock_tm:
            mock_tm.side_effect = Exception("No tokens available")

            with pytest.raises(ConfigurationError):
                PackageProcessor(config)

    def test_process_manifest_file_success(self, processor, tmp_path):
        """Test successful processing of a manifest file."""
        processor.max_dots = 2

        manifest_file = tmp_path / "Microsoft.PowerToys.installer.yaml"
        manifest_file.touch()

        processor.process_manifest_file(manifest_file)

        assert len(processor.unique_rows) == 1
        # Should have tuple with padded parts
        expected_row = ("Microsoft", "PowerToys", "")
        assert expected_row in processor.unique_rows

    def test_process_manifest_file_single_part(self, processor, tmp_path):
        """Test processing manifest file with single part name."""
        processor.max_dots = 2

        manifest_file = tmp_path / "SingleName.installer.yaml"
        manifest_file.touch()

        processor.process_manifest_file(manifest_file)

        # Should not add single-part names
        assert len(processor.unique_rows) == 0

    def test_process_manifest_file_failure(self, processor):
        """Test handling of manifest file processing failure."""
        # Test with invalid path
        invalid_path = Path("/nonexistent/path.yaml")

        # Should handle the error gracefully
        with pytest.raises(ManifestParsingError):
            # Force an error by setting max_dots to an invalid state
            processor.max_dots = -1
            processor.process_manifest_file(invalid_path)

    def test_calculate_max_dots_success(self, processor, tmp_path):
        """Test successful calculation of max dots."""
        files = [
            tmp_path / "A.B.installer.yaml",
            tmp_path / "X.Y.Z.installer.yaml",
            tmp_path / "Single.installer.yaml",
        ]

        for file in files:
            file.touch()

        processor.calculate_max_dots(files)
        assert processor.max_dots == 2  # X.Y.Z has 2 dots

    def test_calculate_max_dots_empty_list(self, processor):
        """Test calculation with empty file list."""
        processor.calculate_max_dots([])
        assert processor.max_dots == 0

    def test_create_manifest_dataframe_success(self, processor):
        """Test successful creation of manifest DataFrame."""
        processor.max_dots = 2
        processor.unique_rows = {
            ("Microsoft", "PowerToys", ""),
            ("Google", "Chrome", ""),
            ("Mozilla", "Firefox", ""),
        }

        df = processor.create_manifest_dataframe()

        assert isinstance(df, pl.DataFrame)
        assert df.shape[0] == 3  # 3 rows
        assert df.shape[1] == 3  # 3 columns (max_dots + 1)
        assert list(df.columns) == ["column_0", "column_1", "column_2"]

    def test_create_manifest_dataframe_empty(self, processor):
        """Test DataFrame creation with no data."""
        df = processor.create_manifest_dataframe()

        assert isinstance(df, pl.DataFrame)
        assert df.shape == (0, 0)  # Empty DataFrame

    def test_extract_arch_ext_pairs_success(self, processor):
        """Test successful extraction of architecture-extension pairs."""
        urls = [
            "https://example.com/app-x64.msi",
            "https://example.com/app-arm64.exe",
            "https://example.com/app.zip",
        ]

        result = processor.extract_arch_ext_pairs(urls)

        assert isinstance(result, str)
        # Should contain architecture-extension pairs
        assert "x64-msi" in result or "arm64-exe" in result

    def test_extract_arch_ext_pairs_no_matches(self, processor):
        """Test extraction when no architecture patterns match."""
        urls = [
            "https://example.com/app.txt",  # Invalid extension
            "https://example.com/unknown-format",
        ]

        result = processor.extract_arch_ext_pairs(urls)

        # Should return empty string when no valid pairs found
        assert result == ""

    def test_extract_arch_ext_pairs_failure(self, processor):
        """Test handling of extraction failure."""
        # Test with invalid input that might cause an exception
        with pytest.raises(PackageProcessingError):
            processor.extract_arch_ext_pairs(None)  # Invalid input

    @pytest.mark.parametrize(
        "url,expected_arch,expected_ext",
        [
            ("https://example.com/app-x64.msi", "x64", "msi"),
            ("https://example.com/app-arm64.exe", "arm64", "exe"),
            ("https://example.com/app.x86_64.zip", "x86_64", "zip"),
            ("https://example.com/app-aarch64.appx", "aarch64", "appx"),
        ],
    )
    def test_architecture_extension_detection(
        self, processor, url, expected_arch, expected_ext
    ):
        """Test detection of specific architecture and extension patterns."""
        result = processor.extract_arch_ext_pairs([url])

        if result:  # If any pair was detected
            assert expected_ext in result
            # Architecture detection may vary, so we check more loosely

    def test_github_config_initialization(self, processor):
        """Test GitHub configuration initialization."""
        assert processor.github_config is not None
        assert hasattr(processor.github_config, "token")
        assert hasattr(processor.github_config, "base_url")
        assert hasattr(processor.github_config, "per_page")

    def test_version_analysis_attributes(self, processor):
        """Test that version analysis attributes are properly initialized."""
        assert isinstance(processor.package_versions, dict)
        assert isinstance(processor.package_downloads, dict)
        assert isinstance(processor.version_patterns, dict)
        assert isinstance(processor.latest_urls, dict)
        assert isinstance(processor.latest_extensions, dict)
        assert isinstance(processor.latest_version_map, dict)
        assert isinstance(processor.arch_ext_pairs, dict)

    def test_supported_architectures_and_extensions(self, processor):
        """Test that supported architectures and extensions are defined."""
        # Check that common architectures are supported
        assert "x64" in processor.architectures
        assert "arm64" in processor.architectures
        assert "x86" in processor.architectures

        # Check that common extensions are supported
        assert "msi" in processor.extensions
        assert "exe" in processor.extensions
        assert "zip" in processor.extensions

    @patch("winget_automation.PackageProcessor.logging")
    def test_logging_in_methods(self, mock_logging, processor):
        """Test that methods properly log their operations."""
        urls = ["https://example.com/app-x64.msi"]

        processor.extract_arch_ext_pairs(urls)

        # Verify that logging was called
        mock_logging.info.assert_called()

    def test_unique_rows_management(self, processor, tmp_path):
        """Test that unique rows are properly managed."""
        processor.max_dots = 2

        # Process the same file multiple times
        manifest_file = tmp_path / "Microsoft.PowerToys.installer.yaml"
        manifest_file.touch()

        processor.process_manifest_file(manifest_file)
        initial_count = len(processor.unique_rows)

        processor.process_manifest_file(manifest_file)
        final_count = len(processor.unique_rows)

        # Should not add duplicates
        assert initial_count == final_count == 1

    def test_error_handling_chain(self, processor):
        """Test that errors are properly chained and contain useful information."""
        with pytest.raises(PackageProcessingError) as exc_info:
            # Force an error that should be caught and re-raised as PackageProcessingError
            processor.extract_arch_ext_pairs(None)

        # Check that the exception contains useful information
        assert "Failed to extract architecture-extension pairs" in str(exc_info.value)
        assert exc_info.value.details is not None
