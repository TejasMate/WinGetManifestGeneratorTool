"""
Modern Package Processor with Multi-Source Support.

This module provides a refactored package processor that can handle multiple
package sources (GitHub, GitLab, SourceForge, etc.) through a unified interface.
"""

import logging
import polars as pl
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

try:
    from ..sources import PackageSourceManager, PackageMetadata, get_package_metadata_for_url
    from ..core.package_sources import PackageSourceType
    from ..config import get_config
    from ..exceptions import PackageProcessingError, ConfigurationError
except ImportError:
    # Fallback for direct script execution
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent.parent))
    from src.sources import PackageSourceManager, PackageMetadata, get_package_metadata_for_url
    from src.core.package_sources import PackageSourceType
    from src.config import get_config
    from src.exceptions import PackageProcessingError, ConfigurationError

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """Result of processing a single package."""
    package_identifier: str
    success: bool
    metadata: Optional[PackageMetadata] = None
    error_message: Optional[str] = None
    source_type: Optional[PackageSourceType] = None


class MultiSourcePackageProcessor:
    """Package processor that supports multiple package sources."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the multi-source package processor."""
        self.config = config or get_config()
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        
        # Initialize package source manager
        self.source_manager = PackageSourceManager(self.config)
        
        # Get configuration
        self._load_configuration()
        
        self.logger.info("Multi-source package processor initialized")
    
    def _load_configuration(self) -> None:
        """Load processing configuration."""
        try:
            # Processing settings
            processing_config = self.config.get('package_processing', {})
            self.max_workers = processing_config.get('max_workers', 4)
            self.batch_size = processing_config.get('batch_size', 100)
            self.timeout = processing_config.get('timeout', 300)
            
            # Filtering settings
            filtering_config = self.config.get('filtering', {})
            self.blocked_packages = set(filtering_config.get('blocked_packages', []))
            self.allowed_architectures = set(filtering_config.get('allowed_architectures', []))
            self.allowed_extensions = set(filtering_config.get('allowed_extensions', []))
            self.min_download_count = filtering_config.get('min_download_count', 0)
            
            self.logger.info(f"Configuration loaded: {len(self.blocked_packages)} blocked packages, "
                           f"{self.max_workers} workers, batch size {self.batch_size}")
            
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {e}")
    
    def process_package_urls(self, urls: List[str]) -> List[ProcessingResult]:
        """Process multiple package URLs and return results."""
        if not urls:
            return []
        
        self.logger.info(f"Processing {len(urls)} package URLs with {self.max_workers} workers")
        
        results = []
        
        # Filter supported URLs
        supported_urls = [url for url in urls if self.source_manager.is_supported_url(url)]
        unsupported_urls = [url for url in urls if not self.source_manager.is_supported_url(url)]
        
        if unsupported_urls:
            self.logger.warning(f"Skipping {len(unsupported_urls)} unsupported URLs")
            for url in unsupported_urls:
                results.append(ProcessingResult(
                    package_identifier=url,
                    success=False,
                    error_message="Unsupported URL format"
                ))
        
        # Process supported URLs in parallel
        if supported_urls:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all tasks
                future_to_url = {
                    executor.submit(self._process_single_url, url): url 
                    for url in supported_urls
                }
                
                # Collect results
                for future in as_completed(future_to_url):
                    url = future_to_url[future]
                    try:
                        result = future.result(timeout=self.timeout)
                        results.append(result)
                    except Exception as e:
                        self.logger.error(f"Error processing {url}: {e}")
                        results.append(ProcessingResult(
                            package_identifier=url,
                            success=False,
                            error_message=str(e)
                        ))
        
        success_count = sum(1 for r in results if r.success)
        self.logger.info(f"Processing complete: {success_count}/{len(results)} successful")
        
        return results
    
    def _process_single_url(self, url: str) -> ProcessingResult:
        """Process a single package URL."""
        try:
            # Get package metadata
            metadata = get_package_metadata_for_url(url)
            
            if not metadata:
                return ProcessingResult(
                    package_identifier=url,
                    success=False,
                    error_message="Failed to retrieve package metadata"
                )
            
            # Check if package is blocked
            if metadata.identifier in self.blocked_packages:
                return ProcessingResult(
                    package_identifier=metadata.identifier,
                    success=False,
                    error_message="Package is in blocklist"
                )
            
            # Apply filtering
            if not self._passes_filters(metadata):
                return ProcessingResult(
                    package_identifier=metadata.identifier,
                    success=False,
                    error_message="Package filtered out by criteria"
                )
            
            return ProcessingResult(
                package_identifier=metadata.identifier,
                success=True,
                metadata=metadata,
                source_type=metadata.repository_info.source_type
            )
            
        except Exception as e:
            self.logger.error(f"Error processing URL {url}: {e}")
            return ProcessingResult(
                package_identifier=url,
                success=False,
                error_message=str(e)
            )
    
    def _passes_filters(self, metadata: PackageMetadata) -> bool:
        """Check if package metadata passes all filters."""
        try:
            # Architecture filter
            if self.allowed_architectures and metadata.architectures:
                if not any(arch in self.allowed_architectures for arch in metadata.architectures):
                    return False
            
            # File extension filter
            if self.allowed_extensions and metadata.file_extensions:
                if not any(ext in self.allowed_extensions for ext in metadata.file_extensions):
                    return False
            
            # Add more filters as needed
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error applying filters to {metadata.identifier}: {e}")
            return False
    
    def process_csv_file(self, input_path: Path, output_path: Path) -> None:
        """Process packages from a CSV file and save results."""
        try:
            # Read input CSV
            df = pl.read_csv(input_path)
            
            # Extract URLs (assuming there's a column with URLs)
            url_columns = ['GitHubURL', 'RepositoryURL', 'URL', 'LatestVersionURLsInWinGet']
            urls = []
            
            for col in url_columns:
                if col in df.columns:
                    urls.extend(df[col].drop_nulls().to_list())
                    break
            
            if not urls:
                raise PackageProcessingError("No URL column found in CSV file")
            
            # Remove duplicates
            urls = list(set(urls))
            
            self.logger.info(f"Processing {len(urls)} unique URLs from {input_path}")
            
            # Process URLs
            results = self.process_package_urls(urls)
            
            # Convert results to DataFrame
            results_data = []
            for result in results:
                row = {
                    'PackageIdentifier': result.package_identifier,
                    'ProcessingSuccess': result.success,
                    'SourceType': result.source_type.value if result.source_type else None,
                    'ErrorMessage': result.error_message
                }
                
                if result.metadata:
                    row.update({
                        'PackageName': result.metadata.name,
                        'RepositoryURL': result.metadata.repository_info.base_url,
                        'LatestVersion': result.metadata.latest_release.version if result.metadata.latest_release else None,
                        'DownloadURLs': ','.join(result.metadata.install_urls or []),
                        'Architectures': ','.join(result.metadata.architectures or []),
                        'FileExtensions': ','.join(result.metadata.file_extensions or [])
                    })
                
                results_data.append(row)
            
            # Save results
            results_df = pl.DataFrame(results_data)
            results_df.write_csv(output_path)
            
            success_count = sum(1 for r in results if r.success)
            self.logger.info(f"Results saved to {output_path}: {success_count}/{len(results)} successful")
            
        except Exception as e:
            raise PackageProcessingError(f"Error processing CSV file: {e}")
    
    def get_source_statistics(self) -> Dict[str, int]:
        """Get statistics about supported package sources."""
        supported_types = self.source_manager.get_supported_source_types()
        
        stats = {}
        for source_type in supported_types:
            source = self.source_manager.get_source_by_type(source_type)
            if source:
                stats[source_type.value] = 1  # Could expand to show more detailed stats
        
        return stats
    
    def validate_configuration(self) -> Dict[str, bool]:
        """Validate the processor configuration."""
        validation_results = {}
        
        try:
            # Check source manager
            validation_results['source_manager'] = len(self.source_manager.get_supported_source_types()) > 0
            
            # Check configuration
            validation_results['config_loaded'] = bool(self.config)
            validation_results['blocked_packages'] = isinstance(self.blocked_packages, set)
            validation_results['allowed_architectures'] = isinstance(self.allowed_architectures, set)
            validation_results['allowed_extensions'] = isinstance(self.allowed_extensions, set)
            
            # Check threading configuration
            validation_results['max_workers'] = isinstance(self.max_workers, int) and self.max_workers > 0
            validation_results['batch_size'] = isinstance(self.batch_size, int) and self.batch_size > 0
            
        except Exception as e:
            self.logger.error(f"Error validating configuration: {e}")
            validation_results['validation_error'] = str(e)
        
        return validation_results


def main():
    """Main function for testing the multi-source processor."""
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Initialize processor
        processor = MultiSourcePackageProcessor()
        
        # Validate configuration
        validation = processor.validate_configuration()
        print("Configuration validation:", validation)
        
        # Show supported sources
        stats = processor.get_source_statistics()
        print("Supported package sources:", stats)
        
        # Test with some URLs
        test_urls = [
            "https://github.com/microsoft/PowerToys",
            "https://gitlab.com/inkscape/inkscape",
            "https://sourceforge.net/projects/7zip/",
            "https://example.com/unsupported"  # This should fail
        ]
        
        print(f"\nTesting with {len(test_urls)} URLs...")
        results = processor.process_package_urls(test_urls)
        
        for result in results:
            status = "✅" if result.success else "❌"
            print(f"{status} {result.package_identifier}")
            if result.metadata:
                print(f"   Source: {result.source_type.value}")
                print(f"   Name: {result.metadata.name}")
            elif result.error_message:
                print(f"   Error: {result.error_message}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
