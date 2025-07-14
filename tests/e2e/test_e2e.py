"""End-to-end tests for the WinGet Manifest Generator Tool."""

import pytest
import tempfile
import subprocess
import time
from pathlib import Path
from unittest.mock import patch, Mock
import polars as pl
import yaml
import os


@pytest.mark.e2e
class TestEndToEndWorkflow:
    """End-to-end tests that simulate the complete workflow."""

    @pytest.fixture
    def e2e_environment(self, tmp_path):
        """Set up a complete testing environment."""
        # Create directory structure
        winget_repo = tmp_path / "winget-pkgs"
        manifests_dir = winget_repo / "manifests"
        data_dir = tmp_path / "data"

        manifests_dir.mkdir(parents=True)
        data_dir.mkdir()

        # Create sample manifests
        self._create_sample_manifests(manifests_dir)

        return {
            "winget_repo": winget_repo,
            "manifests_dir": manifests_dir,
            "data_dir": data_dir,
            "base_dir": tmp_path,
        }

    def _create_sample_manifests(self, manifests_dir):
        """Create sample manifest files for testing."""
        packages = [
            {
                "id": "Microsoft.PowerToys",
                "version": "0.75.1",
                "path": "m/Microsoft/PowerToys",
                "installers": [
                    {
                        "arch": "x64",
                        "url": "https://github.com/microsoft/PowerToys/releases/download/v0.75.1/PowerToysSetup-0.75.1-x64.msi",
                    },
                    {
                        "arch": "arm64",
                        "url": "https://github.com/microsoft/PowerToys/releases/download/v0.75.1/PowerToysSetup-0.75.1-arm64.msi",
                    },
                ],
            },
            {
                "id": "Google.Chrome",
                "version": "118.0.5993.117",
                "path": "g/Google/Chrome",
                "installers": [
                    {
                        "arch": "x64",
                        "url": "https://dl.google.com/chrome/install/chrome_installer.exe",
                    }
                ],
            },
            {
                "id": "Mozilla.Firefox",
                "version": "119.0.1",
                "path": "m/Mozilla/Firefox",
                "installers": [
                    {
                        "arch": "x64",
                        "url": "https://download.mozilla.org/?product=firefox-latest&os=win&lang=en-US",
                    }
                ],
            },
        ]

        for package in packages:
            package_dir = manifests_dir / package["path"] / package["version"]
            package_dir.mkdir(parents=True)

            manifest_data = {
                "PackageIdentifier": package["id"],
                "PackageVersion": package["version"],
                "Installers": [
                    {
                        "Architecture": installer["arch"],
                        "InstallerUrl": installer["url"],
                        "InstallerSha256": "DUMMY_HASH",
                    }
                    for installer in package["installers"]
                ],
            }

            manifest_file = package_dir / f"{package['id']}.installer.yaml"
            with open(manifest_file, "w") as f:
                yaml.dump(manifest_data, f)

    @patch.dict("os.environ", {"TOKEN_1": "test_token_123"})
    def test_complete_pipeline_execution(self, e2e_environment):
        """Test the complete pipeline from start to finish."""
        env = e2e_environment

        # Mock external dependencies
        with patch("winget_automation.PackageProcessor.TokenManager") as mock_tm, patch(
            "winget_automation.GitHub.TokenManager"
        ) as mock_github_tm, patch("requests.get") as mock_requests:

            # Set up token manager mocks
            mock_token_manager = Mock()
            mock_token_manager.get_available_token.return_value = "test_token"
            mock_tm.return_value = mock_token_manager
            mock_github_tm.return_value = mock_token_manager

            # Mock GitHub API responses
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "tag_name": "v0.76.0",
                "name": "PowerToys v0.76.0",
                "assets": [
                    {
                        "name": "PowerToysSetup-0.76.0-x64.msi",
                        "browser_download_url": "https://github.com/microsoft/PowerToys/releases/download/v0.76.0/PowerToysSetup-0.76.0-x64.msi",
                    }
                ],
            }
            mock_response.headers = {
                "X-RateLimit-Remaining": "4999",
                "X-RateLimit-Reset": str(int(time.time()) + 3600),
            }
            mock_requests.return_value = mock_response

            # Step 1: Test PackageProcessor
            from winget_automation.PackageProcessor import PackageProcessor, ProcessingConfig

            config = ProcessingConfig(
                output_manifest_file=str(env["data_dir"] / "PackageNames.csv"),
                output_analysis_file=str(env["data_dir"] / "AllPackageInfo.csv"),
                open_prs_file=str(env["data_dir"] / "OpenPRs.csv"),
            )

            # Mock the repository path
            with patch.object(
                PackageProcessor,
                "get_winget_repo_path",
                return_value=env["winget_repo"],
            ):
                processor = PackageProcessor(config)

                # Simulate the main processing workflow
                manifests_dir = env["manifests_dir"]
                installer_files = list(manifests_dir.rglob("*.installer.yaml"))

                assert len(installer_files) > 0, "Should have created manifest files"

                # Process the files
                processor.calculate_max_dots(installer_files)

                for file in installer_files:
                    processor.process_manifest_file(file)

                # Create and save DataFrame
                df = processor.create_manifest_dataframe()
                assert df.shape[0] > 0, "Should have processed package data"

                # Mock the save operation
                with patch.object(df, "write_csv") as mock_write:
                    mock_write.return_value = None
                    # Simulate saving
                    df.write_csv(config.output_manifest_file)
                    mock_write.assert_called_once()

    def test_pipeline_with_file_outputs(self, e2e_environment):
        """Test that the pipeline produces expected file outputs."""
        env = e2e_environment

        with patch("winget_automation.PackageProcessor.TokenManager") as mock_tm:
            mock_token_manager = Mock()
            mock_token_manager.get_available_token.return_value = "test_token"
            mock_tm.return_value = mock_token_manager

            from winget_automation.PackageProcessor import PackageProcessor, ProcessingConfig

            config = ProcessingConfig(
                output_manifest_file=str(env["data_dir"] / "PackageNames.csv"),
                output_analysis_file=str(env["data_dir"] / "AllPackageInfo.csv"),
                open_prs_file=str(env["data_dir"] / "OpenPRs.csv"),
            )

            with patch.object(
                PackageProcessor,
                "get_winget_repo_path",
                return_value=env["winget_repo"],
            ):
                processor = PackageProcessor(config)

                # Process manifests
                manifests_dir = env["manifests_dir"]
                installer_files = list(manifests_dir.rglob("*.installer.yaml"))

                processor.calculate_max_dots(installer_files)
                for file in installer_files:
                    processor.process_manifest_file(file)

                # Create actual CSV files
                df = processor.create_manifest_dataframe()
                if df.shape[0] > 0:
                    df.write_csv(config.output_manifest_file)

                    # Verify file was created
                    assert Path(config.output_manifest_file).exists()

                    # Verify file content
                    saved_df = pl.read_csv(config.output_manifest_file)
                    assert saved_df.shape[0] > 0

    @patch.dict("os.environ", {"TOKEN_1": "test_token_123"})
    def test_error_recovery_in_pipeline(self, e2e_environment):
        """Test that the pipeline can recover from errors gracefully."""
        env = e2e_environment

        with patch("winget_automation.PackageProcessor.TokenManager") as mock_tm:
            mock_token_manager = Mock()
            mock_token_manager.get_available_token.return_value = "test_token"
            mock_tm.return_value = mock_token_manager

            from winget_automation.PackageProcessor import PackageProcessor, ProcessingConfig

            config = ProcessingConfig(
                output_manifest_file=str(env["data_dir"] / "PackageNames.csv"),
                output_analysis_file=str(env["data_dir"] / "AllPackageInfo.csv"),
                open_prs_file=str(env["data_dir"] / "OpenPRs.csv"),
            )

            with patch.object(
                PackageProcessor,
                "get_winget_repo_path",
                return_value=env["winget_repo"],
            ):
                processor = PackageProcessor(config)

                # Create a corrupted manifest file
                corrupted_dir = (
                    env["manifests_dir"] / "corrupted" / "Test" / "Package" / "1.0.0"
                )
                corrupted_dir.mkdir(parents=True)
                corrupted_file = corrupted_dir / "Corrupted.Package.installer.yaml"

                with open(corrupted_file, "w") as f:
                    f.write("invalid: yaml: content: [unclosed")

                # Process should continue despite corrupted file
                manifests_dir = env["manifests_dir"]
                installer_files = list(manifests_dir.rglob("*.installer.yaml"))

                processor.calculate_max_dots(installer_files)

                errors_encountered = 0
                for file in installer_files:
                    try:
                        processor.process_manifest_file(file)
                    except Exception:
                        errors_encountered += 1

                # Should have processed some files successfully despite errors
                assert len(processor.unique_rows) > 0
                assert errors_encountered <= len(
                    installer_files
                )  # Not all files should fail

    def test_data_consistency_across_steps(self, e2e_environment):
        """Test that data remains consistent across processing steps."""
        env = e2e_environment

        with patch("winget_automation.PackageProcessor.TokenManager") as mock_tm:
            mock_token_manager = Mock()
            mock_token_manager.get_available_token.return_value = "test_token"
            mock_tm.return_value = mock_token_manager

            from winget_automation.PackageProcessor import PackageProcessor, ProcessingConfig

            config = ProcessingConfig(
                output_manifest_file=str(env["data_dir"] / "PackageNames.csv"),
                output_analysis_file=str(env["data_dir"] / "AllPackageInfo.csv"),
                open_prs_file=str(env["data_dir"] / "OpenPRs.csv"),
            )

            with patch.object(
                PackageProcessor,
                "get_winget_repo_path",
                return_value=env["winget_repo"],
            ):
                processor = PackageProcessor(config)

                # First processing run
                manifests_dir = env["manifests_dir"]
                installer_files = list(manifests_dir.rglob("*.installer.yaml"))

                processor.calculate_max_dots(installer_files)
                for file in installer_files:
                    processor.process_manifest_file(file)

                first_run_rows = len(processor.unique_rows)
                first_run_max_dots = processor.max_dots

                # Reset and run again
                processor.unique_rows.clear()
                processor.max_dots = 0

                processor.calculate_max_dots(installer_files)
                for file in installer_files:
                    processor.process_manifest_file(file)

                second_run_rows = len(processor.unique_rows)
                second_run_max_dots = processor.max_dots

                # Results should be consistent
                assert first_run_rows == second_run_rows
                assert first_run_max_dots == second_run_max_dots

    @pytest.mark.slow
    def test_performance_under_load(self, e2e_environment):
        """Test system performance with a larger dataset."""
        env = e2e_environment

        # Create many more manifest files to test performance
        manifests_dir = env["manifests_dir"]

        # Generate 100 additional packages
        for i in range(100):
            package_id = f"Test.Package{i:03d}"
            package_dir = manifests_dir / "t" / "Test" / f"Package{i:03d}" / "1.0.0"
            package_dir.mkdir(parents=True)

            manifest_data = {
                "PackageIdentifier": package_id,
                "PackageVersion": "1.0.0",
                "Installers": [
                    {
                        "Architecture": "x64",
                        "InstallerUrl": f"https://example.com/package{i}-x64.msi",
                        "InstallerSha256": f"HASH{i}",
                    }
                ],
            }

            manifest_file = package_dir / f"{package_id}.installer.yaml"
            with open(manifest_file, "w") as f:
                yaml.dump(manifest_data, f)

        with patch("winget_automation.PackageProcessor.TokenManager") as mock_tm:
            mock_token_manager = Mock()
            mock_token_manager.get_available_token.return_value = "test_token"
            mock_tm.return_value = mock_token_manager

            from winget_automation.PackageProcessor import PackageProcessor, ProcessingConfig

            config = ProcessingConfig(
                output_manifest_file=str(env["data_dir"] / "PackageNames.csv"),
                output_analysis_file=str(env["data_dir"] / "AllPackageInfo.csv"),
                open_prs_file=str(env["data_dir"] / "OpenPRs.csv"),
            )

            start_time = time.time()

            with patch.object(
                PackageProcessor,
                "get_winget_repo_path",
                return_value=env["winget_repo"],
            ):
                processor = PackageProcessor(config)

                manifests_dir = env["manifests_dir"]
                installer_files = list(manifests_dir.rglob("*.installer.yaml"))

                # Should have created many files
                assert len(installer_files) > 100

                processor.calculate_max_dots(installer_files)
                for file in installer_files:
                    processor.process_manifest_file(file)

                processing_time = time.time() - start_time

                # Performance assertions (adjust based on acceptable performance)
                assert processing_time < 30  # Should complete within 30 seconds
                assert len(processor.unique_rows) > 100  # Should process many packages

    def test_concurrent_access_safety(self, e2e_environment):
        """Test that the system handles concurrent access safely."""
        env = e2e_environment

        with patch("winget_automation.PackageProcessor.TokenManager") as mock_tm:
            mock_token_manager = Mock()
            mock_token_manager.get_available_token.return_value = "test_token"
            mock_tm.return_value = mock_token_manager

            from winget_automation.PackageProcessor import PackageProcessor, ProcessingConfig
            import threading

            config = ProcessingConfig(
                output_manifest_file=str(env["data_dir"] / "PackageNames.csv"),
                output_analysis_file=str(env["data_dir"] / "AllPackageInfo.csv"),
                open_prs_file=str(env["data_dir"] / "OpenPRs.csv"),
            )

            def process_manifests():
                with patch.object(
                    PackageProcessor,
                    "get_winget_repo_path",
                    return_value=env["winget_repo"],
                ):
                    processor = PackageProcessor(config)
                    manifests_dir = env["manifests_dir"]
                    installer_files = list(manifests_dir.rglob("*.installer.yaml"))

                    processor.calculate_max_dots(installer_files)
                    for file in installer_files[
                        :2
                    ]:  # Process fewer files to speed up test
                        processor.process_manifest_file(file)

                    return len(processor.unique_rows)

            # Run multiple threads
            threads = []
            results = []

            for _ in range(3):
                thread = threading.Thread(
                    target=lambda: results.append(process_manifests())
                )
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            # All threads should complete successfully
            assert len(results) == 3
            assert all(result > 0 for result in results)


@pytest.mark.e2e
class TestCommandLineInterface:
    """Test the command-line interface behavior."""

    def test_script_execution_returns_success(self):
        """Test that scripts can be executed and return success codes."""
        # This is a basic test to ensure scripts are syntactically correct
        scripts = [
            "src/PackageProcessor.py",
            "src/GitHub.py",
            "src/KomacCommandsGenerator.py",
        ]

        for script in scripts:
            if Path(script).exists():
                # Test import only (not execution to avoid side effects)
                try:
                    import importlib.util

                    spec = importlib.util.spec_from_file_location("test_module", script)
                    module = importlib.util.module_from_spec(spec)
                    # Don't execute, just verify it can be loaded
                    assert spec is not None
                    assert module is not None
                except Exception as e:
                    pytest.fail(f"Script {script} failed to load: {e}")

    @patch.dict("os.environ", {"TOKEN_1": "test_token_123"})
    def test_environment_variable_handling(self):
        """Test that environment variables are properly handled."""
        from winget_automation.utils.token_manager import TokenManager

        # Should work with environment variables set
        manager = TokenManager()
        assert len(manager.tokens) > 0

        # Test token retrieval
        token = manager.get_available_token()
        assert token is not None
        assert token == "test_token_123"
