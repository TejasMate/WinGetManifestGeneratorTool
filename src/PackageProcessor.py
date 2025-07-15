import asyncio
import aiofiles
import gc
import concurrent.futures
import polars as pl
import logging
import yaml
import re
import time
import requests
import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union
from dataclasses import dataclass

# Handle both relative and absolute imports
import sys
from pathlib import Path

# Add current directory to path for imports
current_dir = Path(__file__).parent if '__file__' in globals() else Path.cwd() / 'src'
sys.path.insert(0, str(current_dir))

try:
    from utils.unified_utils import BaseConfig, YAMLProcessorBase, GitHubURLProcessor
    from utils.version_pattern_utils import VersionPatternDetector
    from utils.token_manager import TokenManager
    from config import get_config_manager, get_config
    from exceptions import (
        PackageProcessingError,
        ManifestParsingError,
        FileOperationError,
        GitHubAPIError,
        ConfigurationError,
    )
except ImportError:
    # Fallback for direct script execution
    parent_dir = current_dir.parent
    sys.path.insert(0, str(parent_dir))
    
    from src.utils.unified_utils import BaseConfig, YAMLProcessorBase, GitHubURLProcessor
    from src.utils.version_pattern_utils import VersionPatternDetector
    from src.utils.token_manager import TokenManager
    from src.config import get_config_manager, get_config
    from src.exceptions import (
        PackageProcessingError,
        ManifestParsingError,
        FileOperationError,
        GitHubAPIError,
        ConfigurationError,
    )

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


@dataclass
class ProcessingConfig(BaseConfig):
    """Configuration for package processing operations.

    Attributes:
        output_analysis_file: Name of the output file for package analysis
        winget_repo_path: Path to WinGet repository
        output_directory: Directory for output files
        batch_size: Batch size for processing
        max_workers: Maximum number of worker threads
        timeout: Timeout for operations
    """

    output_analysis_file: str = "AllPackageInfo.csv"
    winget_repo_path: str = "winget-pkgs"
    output_directory: str = "data"
    batch_size: int = 100
    max_workers: int = 4
    max_concurrent_files: int = 200  # For async operations
    use_async: bool = True  # Enable async processing by default
    timeout: int = 300

    @classmethod
    def from_config(cls, config: dict):
        """Create ProcessingConfig from configuration dictionary."""
        package_config = config.get('package_processing', {})
        return cls(
            winget_repo_path=package_config.get('winget_repo_path', 'winget-pkgs'),
            output_directory=package_config.get('output_directory', 'data'),
            batch_size=package_config.get('batch_size', 100),
            max_workers=package_config.get('max_workers', 4),
            max_concurrent_files=package_config.get('max_concurrent_files', 200),
            use_async=package_config.get('use_async', True),
            timeout=package_config.get('timeout', 300)
        )


class PackageProcessor(YAMLProcessorBase):
    """Processes WinGet package manifests and analyzes package information.

    This class is responsible for:
    - Scanning and parsing WinGet package manifest files
    - Extracting package information and version patterns
    - Analyzing package URLs and metadata
    - Generating structured data outputs for further processing

    Attributes:
        token_manager: Manages GitHub API tokens (for future GitHub.py integration)
        unique_rows: Set of unique package identifier rows
        max_dots: Maximum number of dots in package identifiers
        package_versions: Map of package IDs to their versions
        package_downloads: Map of package IDs to download counts
        version_patterns: Map of package IDs to version patterns
        latest_urls: Map of package IDs to latest release URLs
        latest_extensions: Map of package IDs to file extensions
        latest_version_map: Map of package IDs to latest versions
        arch_ext_pairs: Map of package IDs to architecture-extension pairs
        architectures: List of supported architectures
        extensions: List of supported file extensions
    """

    def __init__(self, config: Optional[ProcessingConfig] = None):
        """Initialize the PackageProcessor.

        Args:
            config: Processing configuration (if None, loads from config system)

        Raises:
            ConfigurationError: If configuration is invalid
        """
        try:
            # Load configuration from config system if not provided
            if config is None:
                app_config = get_config()
                config = ProcessingConfig.from_config(app_config)
            
            super().__init__(config)
            
            # Load configuration
            self.app_config = get_config()
            self.token_manager = TokenManager(self.app_config)

            # Async control structures (initialized lazily)
            self._data_lock = None
            self.semaphore = None
            self._async_initialized = False
            
            # Caching for performance
            self._yaml_cache: Dict[str, Dict] = {}
            self._path_cache: Dict[str, Path] = {}

            # Manifest processing attributes
            self.unique_rows: Set[Tuple[str, ...]] = set()
            self.max_dots = 0

            # Version analysis attributes
            self.package_versions: Dict[str, Set[str]] = {}
            self.package_downloads: Dict[str, int] = {}
            self.version_patterns: Dict[str, Set[str]] = (
                {}
            )  # Changed to Set to store multiple patterns
            self.latest_urls: Dict[str, List[str]] = {}
            self.latest_extensions: Dict[str, List[str]] = {}
            self.latest_version_map: Dict[str, str] = {}
            self.arch_ext_pairs: Dict[str, str] = {}
            
            # Load architectures and extensions from config
            filtering_config = self.app_config.get('filtering', {})
            self.architectures = filtering_config.get('allowed_architectures', [
                "x86-64", "aarch64", "x86_64", "arm64", "arm", "win64", "amd64", "x86",
                "i386", "ia32", "386", "win32", "32bit", "win-arm64", "win-x64", "win-x86",
                "win-ia32", "windows-arm64", "windows-x64", "windows-x86", "windows-ia32",
                "armv6", "armv7", "arm8", "arm9", "x64", "x32", "i686", "64bit",
                "x86_x64", "x86only", "shared-32", "shared-64", "installer32", "installer64",
                "32", "64"
            ])
            self.extensions = filtering_config.get('allowed_extensions', [
                "msixbundle", "appxbundle", "msix", "appx", "zip", "msi", "exe"
            ])

        except Exception as e:
            raise ConfigurationError(f"Failed to initialize PackageProcessor: {str(e)}")

    def get_processing_stats(self) -> Dict[str, int]:
        """Get processing statistics for monitoring performance.
        
        Returns:
            Dictionary containing processing statistics
        """
        return {
            "total_packages_found": len(self.package_versions),
            "packages_with_urls": len(self.latest_urls),
            "packages_with_arch_ext": len([p for p in self.arch_ext_pairs.values() if p]),
            "total_version_patterns": sum(len(patterns) for patterns in self.version_patterns.values()),
            "packages_with_downloads": len(self.package_downloads)
        }

    def get_winget_path(self) -> Path:
        """Get the path to the WinGet repository.
        
        Returns:
            Path to the WinGet repository
        """
        return Path(self.config.winget_repo_path)

    def _init_async_structures(self):
        """Initialize async structures when needed (must be called from async context)."""
        if not self._async_initialized and self.config.use_async:
            self._data_lock = asyncio.Lock()
            self.semaphore = asyncio.Semaphore(self.config.max_concurrent_files)
            self._async_initialized = True

    # Async Methods for Performance Optimization
    
    async def process_yaml_file_async(self, yaml_path: Path) -> Optional[Dict]:
        """Async version of YAML file processing with caching.
        
        Args:
            yaml_path: Path to YAML file
            
        Returns:
            Parsed YAML data or None if processing fails
        """
        cache_key = str(yaml_path)
        if cache_key in self._yaml_cache:
            return self._yaml_cache[cache_key]
        
        # Use semaphore if available, otherwise process directly
        if self.semaphore:
            async with self.semaphore:
                return await self._process_yaml_file_async_internal(yaml_path, cache_key)
        else:
            return await self._process_yaml_file_async_internal(yaml_path, cache_key)

    async def _process_yaml_file_async_internal(self, yaml_path: Path, cache_key: str) -> Optional[Dict]:
        """Internal async YAML processing method."""
        try:
            async with aiofiles.open(yaml_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                result = yaml.safe_load(content)
                
                # Cache the result for future use
                if result and len(self._yaml_cache) < 1000:  # Limit cache size
                    self._yaml_cache[cache_key] = result
                
                return result
        except Exception as e:
            logging.debug(f"Error processing YAML {yaml_path}: {e}")
            return None

    async def _scan_version_dirs_async(self, package_path: Path, package_name: str) -> List[str]:
        """Async version directory scanning.
        
        Args:
            package_path: Path to package directory
            package_name: Package identifier
            
        Returns:
            List of version directory names
        """
        def _scan_sync():
            version_dirs = []
            try:
                for item in package_path.iterdir():
                    if item.is_dir():
                        # Check if this directory contains installer YAML files
                        installer_yaml = item / f"{package_name}.installer.yaml"
                        if installer_yaml.exists():
                            version_dirs.append(item.name)
            except (OSError, PermissionError):
                # Skip packages with permission issues
                pass
            return version_dirs
        
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            return await loop.run_in_executor(executor, _scan_sync)

    async def _process_installer_yaml_async(self, yaml_path: Path, package_name: str) -> None:
        """Async processing of installer YAML file.
        
        Args:
            yaml_path: Path to installer YAML file
            package_name: Package identifier
        """
        try:
            data = await self.process_yaml_file_async(yaml_path)
            if data and "Installers" in data:
                urls = []
                count = 0
                
                for installer in data["Installers"]:
                    if "InstallerUrl" in installer:
                        # Clean URL and add to list
                        url = installer["InstallerUrl"].replace("%2B", "+")
                        urls.append(url)
                        count += 1

                if urls:
                    # Store package metadata (thread-safe)
                    if self._data_lock:
                        async with self._data_lock:
                            self.latest_urls[package_name] = urls
                            self.package_downloads[package_name] = count
                            
                            # Initialize version patterns set if not exists
                            if package_name not in self.version_patterns:
                                self.version_patterns[package_name] = set()
                            
                            # Add patterns for all versions
                            for version in self.package_versions[package_name]:
                                pattern = VersionPatternDetector.determine_version_pattern(version)
                                self.version_patterns[package_name].add(pattern)
                            
                            # Extract and store arch-ext pairs
                            self.arch_ext_pairs[package_name] = self.extract_arch_ext_pairs(urls)
                    else:
                        # Fallback for sync mode
                        self.latest_urls[package_name] = urls
                        self.package_downloads[package_name] = count
                        
                        if package_name not in self.version_patterns:
                            self.version_patterns[package_name] = set()
                        
                        for version in self.package_versions[package_name]:
                            pattern = VersionPatternDetector.determine_version_pattern(version)
                            self.version_patterns[package_name].add(pattern)
                        
                        self.arch_ext_pairs[package_name] = self.extract_arch_ext_pairs(urls)
                        
        except Exception as yaml_error:
            logging.debug(f"Error processing YAML for {package_name}: {yaml_error}")

    async def _async_iterdir(self, path: Path):
        """Async directory iteration using thread pool.
        
        Args:
            path: Directory path to iterate
            
        Yields:
            Directory items
        """
        def _list_dir():
            try:
                return list(path.iterdir())
            except (OSError, PermissionError):
                return []
        
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            items = await loop.run_in_executor(executor, _list_dir)
            for item in items:
                yield item

    async def _is_dir_async(self, path: Path) -> bool:
        """Async directory check using thread pool.
        
        Args:
            path: Path to check
            
        Returns:
            True if path is a directory
        """
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            return await loop.run_in_executor(executor, path.is_dir)

    async def _scan_letter_directory_async(self, first_letter_dir: Path) -> List[List[str]]:
        """Async scanning of a first-letter directory."""
        return await asyncio.get_event_loop().run_in_executor(
            None, self._find_packages_recursive, first_letter_dir, first_letter_dir
        )

    async def get_package_names_from_structure_async(self) -> List[List[str]]:
        """Async version of directory structure scanning.
        
        Returns:
            List of package name parts for efficient processing
            
        Raises:
            PackageProcessingError: If directory scanning fails
        """
        try:
            package_names = []
            manifests_path = self.get_winget_path() / "manifests"
            
            if not manifests_path.exists():
                logging.warning(f"Manifests path not found: {manifests_path}")
                return []
            
            logging.info("Extracting package names from directory structure asynchronously...")
            
            # Scan all first-letter directories concurrently
            tasks = []
            async for first_letter_dir in self._async_iterdir(manifests_path):
                if await self._is_dir_async(first_letter_dir):
                    task = self._scan_letter_directory_async(first_letter_dir)
                    tasks.append(task)
            
            # Wait for all directory scans to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Collect results
            for result in results:
                if isinstance(result, Exception):
                    logging.warning(f"Error scanning directory: {result}")
                else:
                    package_names.extend(result)
            
            logging.info(f"Found {len(package_names)} packages from directory structure (async)")
            return package_names
            
        except Exception as e:
            raise PackageProcessingError(f"Failed to extract package names from structure (async): {str(e)}")

    async def process_package_async(self, package_parts: List[str]) -> None:
        """Async version of package processing.
        
        Args:
            package_parts: List of package name parts
            
        Raises:
            PackageProcessingError: If package processing fails
        """
        package_name = None
        try:
            # Use semaphore if available, otherwise process directly
            if self.semaphore:
                async with self.semaphore:
                    await self._process_single_package_async(package_parts)
            else:
                await self._process_single_package_async(package_parts)

        except Exception as e:
            package_name = ".".join(package_parts) if package_parts else "unknown"
            logging.warning(f"Error processing package {package_name}: {e}")
            # Don't raise exception to continue processing other packages

    async def _process_single_package_async(self, package_parts: List[str]) -> None:
        """Internal async processing method for a single package."""
        package_path = self.get_package_path(package_parts)
        if not package_path or not package_path.exists():
            return

        package_name = ".".join(package_parts)
        
        # Async directory scanning
        version_dirs = await self._scan_version_dirs_async(package_path, package_name)
        if not version_dirs:
            return

        # Store all versions (thread-safe)
        if self._data_lock:
            async with self._data_lock:
                self.package_versions[package_name] = set(version_dirs)
        else:
            self.package_versions[package_name] = set(version_dirs)

        # Find latest version efficiently
        def version_key(v):
            # Optimized version sorting
            parts = re.split(r'([0-9]+)', v)
            return [int(p) if p.isdigit() else p for p in parts]

        try:
            latest_version = max(version_dirs, key=version_key)
        except (ValueError, TypeError):
            # Fallback to string sorting if version parsing fails
            latest_version = max(version_dirs)
            
        if self._data_lock:
            async with self._data_lock:
                self.latest_version_map[package_name] = latest_version
        else:
            self.latest_version_map[package_name] = latest_version

        # Process installer YAML asynchronously
        yaml_path = package_path / latest_version / f"{package_name}.installer.yaml"
        if yaml_path.exists():
            await self._process_installer_yaml_async(yaml_path, package_name)

    async def process_packages_in_batches_async(self, package_names_list: List[List[str]]) -> None:
        """Process packages in async batches for better memory management.
        
        Args:
            package_names_list: List of package name parts to process
        """
        batch_size = self.config.batch_size
        total_batches = (len(package_names_list) + batch_size - 1) // batch_size
        
        for i in range(0, len(package_names_list), batch_size):
            batch = package_names_list[i:i + batch_size]
            batch_num = i // batch_size + 1
            
            logging.info(f"Processing async batch {batch_num}/{total_batches} ({len(batch)} packages)")
            start_time = time.time()
            
            # Process batch asynchronously
            tasks = [self.process_package_async(parts) for parts in batch]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            elapsed = time.time() - start_time
            logging.info(f"Batch {batch_num} completed in {elapsed:.2f}s")
            
            # Optional: Clear intermediate data to manage memory
            if batch_num % 10 == 0:  # Every 10 batches
                gc.collect()

    async def _save_dataframe_async(self, df: pl.DataFrame, output_file: str) -> None:
        """Async version of dataframe saving.
        
        Args:
            df: Polars DataFrame to save
            output_file: Output file name
        """
        def _save_sync():
            self.save_dataframe(df, output_file)
        
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            await loop.run_in_executor(executor, _save_sync)

    async def process_files_async(self) -> None:
        """Async file processing workflow.
        
        This method provides significantly improved performance through:
        - Concurrent file I/O operations
        - Async directory traversal
        - Controlled concurrency with semaphores
        - Batch processing for memory management
        
        Raises:
            PackageProcessingError: If processing fails
        """
        try:
            # Initialize async structures in event loop context
            self._init_async_structures()
            
            logging.info("Starting async package processing workflow...")
            start_time = time.time()
            
            # Get package names asynchronously
            package_names_list = await self.get_package_names_from_structure_async()
            if not package_names_list:
                logging.warning("No packages found in directory structure")
                return
            
            logging.info(f"Processing {len(package_names_list)} packages asynchronously...")
            
            # Process packages in async batches
            await self.process_packages_in_batches_async(package_names_list)
            
            # Create and save analysis dataframe
            analysis_df = self.create_analysis_dataframe()
            if not analysis_df.is_empty():
                await self._save_dataframe_async(analysis_df, self.config.output_analysis_file)
                logging.info(f"Saved analysis data with {len(analysis_df)} packages")
            else:
                logging.warning("No package data to save")
            
            end_time = time.time()
            processing_time = end_time - start_time
            logging.info(f"Async processing completed in {processing_time:.2f} seconds")
            logging.info(f"Processed {len(self.package_versions)} valid packages")
            
        except Exception as e:
            raise PackageProcessingError(f"Error in async file processing: {str(e)}")

    # End of Async Methods

    def _find_packages_recursive(self, current_dir: Path, root_dir: Path) -> List[List[str]]:
        """Recursively find package directories."""
        package_names = []
        
        # Heuristic: If a directory contains subdirectories and at least one of them
        # has an installer YAML for the potential package, it's a package folder.
        potential_package_name = ".".join(current_dir.relative_to(root_dir.parent).parts[1:])
        
        is_package_dir = False
        if potential_package_name:
            for item in current_dir.iterdir():
                if item.is_dir():
                    installer_yaml = item / f"{potential_package_name}.installer.yaml"
                    if installer_yaml.exists():
                        is_package_dir = True
                        break
        
        if is_package_dir:
            package_names.append(potential_package_name.split('.'))
        else:
            # If it's not a package dir, recurse into its subdirectories
            for item in current_dir.iterdir():
                if item.is_dir():
                    package_names.extend(self._find_packages_recursive(item, root_dir))
                    
        return package_names

    def get_package_names_from_structure(self) -> List[List[str]]:
        """Extract package names directly from directory structure.
        
        Returns:
            List of package name parts for efficient processing
            
        Raises:
            PackageProcessingError: If directory scanning fails
        """
        try:
            package_names = []
            manifests_path = self.get_winget_path() / "manifests"
            
            if not manifests_path.exists():
                logging.warning(f"Manifests path not found: {manifests_path}")
                return []
            
            logging.info("Extracting package names from directory structure...")
            
            # Walk through manifests directory structure efficiently
            for first_letter_dir in manifests_path.iterdir():
                if first_letter_dir.is_dir():
                    package_names.extend(self._find_packages_recursive(first_letter_dir, first_letter_dir))
            
            logging.info(f"Found {len(package_names)} packages from directory structure")
            return package_names
            
        except Exception as e:
            raise PackageProcessingError(f"Failed to extract package names from structure: {str(e)}")

    def process_manifest_file(self, file_path: Path) -> None:
        """Process a single manifest file and extract package information.

        Args:
            file_path: Path to the manifest file

        Raises:
            ManifestParsingError: If the manifest file cannot be processed
        """
        try:
            name = file_path.stem.replace(".installer", "")
            parts = name.split(".")

            # The check `if len(set(parts)) == 1: return` was removed
            # as it incorrectly filtered out valid package identifiers.
            
            padded_parts = parts[: self.max_dots + 1] + [""] * (
                self.max_dots + 1 - len(parts)
            )
            row = tuple(padded_parts[: self.max_dots + 1])
            self.unique_rows.add(row)

        except Exception as e:
            raise ManifestParsingError(
                f"Failed to process manifest file: {str(e)}", file_path=str(file_path)
            )

    def calculate_max_dots(self, files: List[Path]) -> None:
        """Calculate the maximum number of dots in package identifiers.

        Args:
            files: List of manifest file paths

        Raises:
            PackageProcessingError: If calculation fails
        """
        try:
            self.max_dots = (
                max(
                    file_path.stem.replace(".installer", "").count(".")
                    for file_path in files
                )
                if files
                else 0
            )
        except Exception as e:
            raise PackageProcessingError(f"Error calculating max dots: {str(e)}")

    def create_manifest_dataframe(self) -> pl.DataFrame:
        """Create a DataFrame from processed manifest data.

        Returns:
            Polars DataFrame containing manifest data

        Raises:
            PackageProcessingError: If DataFrame creation fails
        """
        try:
            if not self.unique_rows:
                return pl.DataFrame()

            column_names = [f"column_{i}" for i in range(self.max_dots + 1)]
            data_dict = {name: [] for name in column_names}

            for row in self.unique_rows:
                for i, value in enumerate(row):
                    data_dict[column_names[i]].append(value)

            return pl.DataFrame(data_dict)
        except Exception as e:
            raise PackageProcessingError(f"Error creating manifest dataframe: {str(e)}")

    def extract_arch_ext_pairs(self, urls: List[str]) -> str:
        """Extract architecture-extension pairs from installer URLs.

        Args:
            urls: List of installer URLs

        Returns:
            String representation of architecture-extension pairs

        Raises:
            PackageProcessingError: If extraction fails
        """
        try:
            pairs = []
            logging.info(
                f"Processing {len(urls)} URLs for architecture-extension pairs"
            )
            for url in urls:
                url_lower = url.lower().strip()
                logging.info(f"\nProcessing URL: {url_lower}")

                # Find extension
                ext_match = None
                for ext in self.extensions:
                    if url_lower.endswith(f".{ext}"):
                        ext_match = ext
                        logging.info(f"Found extension: {ext_match}")
                        break

                if not ext_match:
                    logging.info(f"No valid extension found in URL: {url_lower}")
                    continue

                # Find architecture
                arch_match = None
                logging.info(f"Searching for architecture patterns in: {url_lower}")
                for arch in self.architectures:
                    logging.info(f"Checking architecture pattern: {arch}")
                    pattern = None
                    if arch in ["aarch64", "x86_64", "x86-64"]:
                        pattern = f"[^a-z0-9]({arch})[^a-z0-9]|[_.-]({arch})[_.-]|[_.-]({arch})$"
                    elif arch == "x86_x64":
                        pattern = f"(x86_x64|x86[_.-]x64|x86[-_.]64)"
                    elif arch == "x86only":
                        pattern = "(x86only|x86[_.-]only)"
                    elif arch in ["32", "64"]:
                        pattern = f"(installer[-]?{arch}|{arch}[-]?bit|x{arch}|[_.-]{arch})[_.-]|[_.-](installer[-]?{arch}|{arch}[-]?bit|x{arch}|{arch})$|[^a-z0-9]x{arch}[^a-z0-9]"
                    elif arch in [
                        "installer32",
                        "installer64",
                        "shared-32",
                        "shared-64",
                    ]:
                        base = arch.split("-")[0] if "-" in arch else arch[:-2]
                        num = arch[-2:]
                        pattern = f"({base}[-]?{num}|{base}[_.-]{num})"
                    else:
                        pattern = f"[^a-z0-9]({arch})[^a-z0-9]|[_.-]({arch})[_.-]|[_.-]({arch})$|[^a-z0-9]{arch}[^a-z0-9]"

                    if re.search(pattern, url_lower):
                        arch_match = arch
                        logging.info(
                            f"Found architecture {arch_match} using pattern: {pattern}"
                        )
                        break

                if not arch_match:
                    logging.info("No architecture pattern matched")

                pair = f'{arch_match or "NA"}-{ext_match}'
                logging.info(f"Adding pair: {pair}")
                pairs.append(pair)

            result = ",".join(sorted(set(pairs))) if pairs else ""
            logging.info(f"Final arch-ext pairs: {result}")
            return result
        except Exception as e:
            raise PackageProcessingError(
                f"Failed to extract architecture-extension pairs: {str(e)}"
            )
            if not self.unique_rows:
                return pl.DataFrame()

            column_names = [f"column_{i}" for i in range(self.max_dots + 1)]
            data_dict = {name: [] for name in column_names}

            return pl.DataFrame(data_dict)
        except Exception as e:
            logging.error(f"Error creating manifest dataframe: {e}")
            return pl.DataFrame()

    def count_download_urls(self, yaml_path: Path, package_name: str) -> int:
        try:
            data = self.process_yaml_file(yaml_path)
            if not data or "Installers" not in data:
                return 0

            urls = []
            extensions = []
            count = 0
            for installer in data["Installers"]:
                if "InstallerUrl" in installer:
                    url = installer["InstallerUrl"]
                    urls.append(url)
                    if "." in url:
                        ext = url.split(".")[-1].lower()
                        extensions.append(ext)
                    count += 1

            if urls:
                self.latest_urls[package_name] = urls
                self.latest_extensions[package_name] = extensions
                self.arch_ext_pairs[package_name] = self.extract_arch_ext_pairs(urls)

            return count
        except Exception as e:
            logging.error(f"Error counting download URLs in {yaml_path}: {e}")
            return 0

    def process_package(self, package_parts: List[str]) -> None:
        """Optimized package processing method.
        
        Args:
            package_parts: List of package name parts
            
        Raises:
            PackageProcessingError: If package processing fails
        """
        package_name = None
        try:
            package_path = self.get_package_path(package_parts)
            if not package_path or not package_path.exists():
                return

            package_name = ".".join(package_parts)
            
            # Quick check for version directories
            version_dirs = []
            try:
                for item in package_path.iterdir():
                    if item.is_dir():
                        version_path = item
                        # Check if this directory contains installer YAML files
                        installer_yaml = version_path / f"{package_name}.installer.yaml"
                        if installer_yaml.exists():
                            version_dirs.append(item.name)
            except (OSError, PermissionError):
                # Skip packages with permission issues
                return

            if not version_dirs:
                return

            # Store all versions
            self.package_versions[package_name] = set(version_dirs)

            # Find latest version efficiently
            def version_key(v):
                # Optimized version sorting
                parts = re.split(r'([0-9]+)', v)
                return [int(p) if p.isdigit() else p for p in parts]

            try:
                latest_version = max(version_dirs, key=version_key)
            except (ValueError, TypeError):
                # Fallback to string sorting if version parsing fails
                latest_version = max(version_dirs)
                
            self.latest_version_map[package_name] = latest_version

            # Process installer YAML efficiently
            yaml_path = package_path / latest_version / f"{package_name}.installer.yaml"
            if yaml_path.exists():
                try:
                    data = self.process_yaml_file(yaml_path)
                    if data and "Installers" in data:
                        urls = []
                        count = 0
                        
                        for installer in data["Installers"]:
                            if "InstallerUrl" in installer:
                                # Clean URL and add to list
                                url = installer["InstallerUrl"].replace("%2B", "+")
                                urls.append(url)
                                count += 1

                        if urls:
                            # Store package metadata
                            self.latest_urls[package_name] = urls
                            self.package_downloads[package_name] = count
                            
                            # Initialize version patterns set if not exists
                            if package_name not in self.version_patterns:
                                self.version_patterns[package_name] = set()
                            
                            # Add patterns for all versions (optimized)
                            for version in self.package_versions[package_name]:
                                pattern = VersionPatternDetector.determine_version_pattern(version)
                                self.version_patterns[package_name].add(pattern)
                            
                            # Extract and store arch-ext pairs
                            self.arch_ext_pairs[package_name] = self.extract_arch_ext_pairs(urls)
                            
                except Exception as yaml_error:
                    logging.debug(f"Error processing YAML for {package_name}: {yaml_error}")
                    # Continue processing other packages even if one fails

        except Exception as e:
            if package_name:
                logging.warning(f"Error processing package {package_name}: {e}")
            else:
                logging.warning(f"Error processing package {'.'.join(package_parts)}: {e}")
            # Don't raise exception to continue processing other packages

    def check_package_in_prs(self, package_name: str, pr_titles: List[str]) -> str:
        # Functionality removed - will be implemented in GitHub.py
        return "unknown"

    def create_analysis_dataframe(
        self, pr_titles: Optional[List[str]] = None
    ) -> pl.DataFrame:
        try:
            data = []
            for pkg, vers in self.package_versions.items():
                # Process URLs and extract arch-ext pairs if not already done
                if pkg in self.latest_urls and not self.arch_ext_pairs.get(pkg):
                    urls = self.latest_urls[pkg]
                    self.arch_ext_pairs[pkg] = self.extract_arch_ext_pairs(urls)

                data.append(
                    {
                        "PackageIdentifier": pkg,
                        "AvailableVersions": ",".join(sorted(vers)),
                        "VersionFormatPattern": ",".join(
                            sorted(self.version_patterns.get(pkg, {"unknown"}))
                        ),
                        "CurrentLatestVersionInWinGet": self.latest_version_map.get(
                            pkg, ""
                        ),
                        "InstallerURLsCount": self.package_downloads.get(pkg, 0),
                        "LatestVersionURLsInWinGet": ",".join(
                            self.latest_urls.get(pkg, [])
                        ),
                        "ArchExtPairs": self.arch_ext_pairs.get(pkg, ""),
                        "LatestVersionPullRequest": "unknown",  # Will be populated by GitHub.py
                    }
                )

            # Ensure arch_ext_pairs are populated
            for item in data:
                pkg = item["PackageIdentifier"]
                if pkg in self.latest_urls and not self.arch_ext_pairs.get(pkg):
                    self.arch_ext_pairs[pkg] = self.extract_arch_ext_pairs(
                        self.latest_urls[pkg]
                    )
            return pl.DataFrame(data)
        except Exception as e:
            logging.error(f"Error creating analysis dataframe: {e}")
            return pl.DataFrame()

    def process_files(self) -> None:
        """Optimized file processing workflow with async support.
        
        This method chooses between async and sync processing based on configuration.
        Async processing provides significantly better performance for I/O bound operations.
        
        Raises:
            PackageProcessingError: If processing fails
        """
        if self.config.use_async:
            # Use async processing for better performance
            asyncio.run(self.process_files_async())
        else:
            # Fallback to sync processing
            self.process_files_sync()

    def process_files_sync(self) -> None:
        """Synchronous file processing workflow (legacy).
        
        This method directly processes packages without creating intermediate manifest files,
        making the process more efficient and reducing memory usage.
        
        Raises:
            PackageProcessingError: If processing fails
        """
        try:
            logging.info("Starting synchronous package processing workflow...")
            start_time = time.time()
            
            # Get package names directly from directory structure
            package_names_list = self.get_package_names_from_structure()
            if not package_names_list:
                logging.warning("No packages found in directory structure")
                return
            
            logging.info(f"Processing {len(package_names_list)} packages...")
            
            # Process packages directly without intermediate CSV
            self.parallel_process(package_names_list, self.process_package)
            
            # Create and save analysis dataframe
            analysis_df = self.create_analysis_dataframe()
            if not analysis_df.is_empty():
                self.save_dataframe(analysis_df, self.config.output_analysis_file)
                logging.info(f"Saved analysis data with {len(analysis_df)} packages")
            else:
                logging.warning("No package data to save")
            
            end_time = time.time()
            processing_time = end_time - start_time
            logging.info(f"Synchronous processing completed in {processing_time:.2f} seconds")
            logging.info(f"Processed {len(self.package_versions)} valid packages")
            
        except Exception as e:
            raise PackageProcessingError(f"Error in synchronous file processing: {str(e)}")

    def process_files_legacy(self) -> None:
        """Legacy file processing method (kept for backward compatibility).
        
        This method maintains the original workflow for cases where the intermediate
        manifest CSV file is specifically needed.
        """
        try:
            # Process manifest files
            yaml_files = self.get_yaml_files()
            if not yaml_files:
                logging.warning("No YAML files found")
                return

            self.calculate_max_dots(yaml_files)
            self.parallel_process(yaml_files, self.process_manifest_file)
            manifest_df = self.create_manifest_dataframe()
            
            # Note: PackageNames.csv is no longer generated by default
            # Uncomment the next line if specifically needed:
            # self.save_dataframe(manifest_df, "PackageNames.csv")

            # Process package versions and analysis
            package_parts_list = []
            for row in manifest_df.to_dicts():
                parts = [
                    row[f"column_{i}"] for i in range(len(row)) if row[f"column_{i}"]
                ]
                if parts:
                    package_parts_list.append(parts)

            self.parallel_process(package_parts_list, self.process_package)

            # Create and save analysis dataframe
            analysis_df = self.create_analysis_dataframe()
            if not analysis_df.is_empty():
                self.save_dataframe(analysis_df, self.config.output_analysis_file)

        except Exception as e:
            logging.error(f"Error processing files: {e}")

    def get_winget_path(self) -> Path:
        """Get the path to the WinGet repository."""
        return Path(self.config.winget_repo_path)


async def main_async():
    """Async main entry point for optimized package processing.
    
    This async version provides significantly better performance through:
    - Concurrent I/O operations
    - Async directory traversal
    - Controlled concurrency with semaphores
    - Efficient memory management
    """
    try:
        start_time = time.time()
        logging.info("Starting async PackageProcessor...")
        
        # Load configuration and create processor
        processor = PackageProcessor()
        
        # Run async processing workflow if enabled
        if processor.config.use_async:
            await processor.process_files_async()
        else:
            processor.process_files_sync()
        
        # Display performance statistics
        stats = processor.get_processing_stats()
        end_time = time.time()
        total_time = end_time - start_time
        
        processing_mode = "async" if processor.config.use_async else "sync"
        
        logging.info("=" * 60)
        logging.info(f"PROCESSING COMPLETED SUCCESSFULLY ({processing_mode.upper()})")
        logging.info("=" * 60)
        logging.info(f"Total processing time: {total_time:.2f} seconds")
        logging.info(f"Packages processed: {stats['total_packages_found']}")
        logging.info(f"Packages with URLs: {stats['packages_with_urls']}")
        logging.info(f"Packages with architecture data: {stats['packages_with_arch_ext']}")
        logging.info(f"Total version patterns detected: {stats['total_version_patterns']}")
        logging.info(f"Average processing time per package: {total_time/max(stats['total_packages_found'], 1):.3f}s")
        
        # Performance improvements notice
        if processor.config.use_async:
            logging.info(f"\n🚀 Performance Enhancement: Async processing enabled")
            logging.info(f"   • Concurrent file I/O operations")
            logging.info(f"   • Max concurrent files: {processor.config.max_concurrent_files}")
            logging.info(f"   • Batch size: {processor.config.batch_size}")
        
        # Key outputs
        logging.info("\n📄 Key Output Files:")
        logging.info("  • AllPackageInfo.csv - Complete package analysis data")
        logging.info("\n💡 Note: PackageNames.csv is no longer generated (package names are in AllPackageInfo.csv)")
        logging.info("💡 Note: OpenPRs functionality will be implemented in GitHub.py")
        
    except Exception as e:
        logging.error(f"Async processing failed: {e}")
        logging.error("You can try disabling async processing in configuration if needed")
        raise


def main():
    """Main entry point for optimized package processing.
    
    This optimized version:
    - Supports both async and synchronous processing
    - Processes packages directly from directory structure
    - Eliminates PackageNames.csv generation (redundant with AllPackageInfo.csv)
    - Provides performance metrics
    - Uses efficient memory management
    """
    try:
        # Check if async processing should be used
        config = get_config()
        use_async = config.get('package_processing', {}).get('use_async', True)
        
        if use_async:
            # Run async main function
            asyncio.run(main_async())
        else:
            # Run synchronous version
            start_time = time.time()
            logging.info("Starting synchronous PackageProcessor...")
            
            # Load configuration and create processor
            processor = PackageProcessor()
            
            # Run synchronous processing workflow
            processor.process_files_sync()
            
            # Display performance statistics
            stats = processor.get_processing_stats()
            end_time = time.time()
            total_time = end_time - start_time
            
            logging.info("=" * 60)
            logging.info("PROCESSING COMPLETED SUCCESSFULLY (SYNC)")
            logging.info("=" * 60)
            logging.info(f"Total processing time: {total_time:.2f} seconds")
            logging.info(f"Packages processed: {stats['total_packages_found']}")
            logging.info(f"Packages with URLs: {stats['packages_with_urls']}")
            logging.info(f"Packages with architecture data: {stats['packages_with_arch_ext']}")
            logging.info(f"Total version patterns detected: {stats['total_version_patterns']}")
            logging.info(f"Average processing time per package: {total_time/max(stats['total_packages_found'], 1):.3f}s")
            
            # Key outputs
            logging.info("\n📄 Key Output Files:")
            logging.info("  • AllPackageInfo.csv - Complete package analysis data")
            logging.info("\n💡 Note: PackageNames.csv is no longer generated (package names are in AllPackageInfo.csv)")
            logging.info("💡 Note: OpenPRs functionality will be implemented in GitHub.py")
        
    except Exception as e:
        logging.error(f"Processing failed: {e}")
        logging.error("You can try the legacy processing method if needed")
        raise


if __name__ == "__main__":
    main()
