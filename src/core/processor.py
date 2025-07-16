"""
Unified Package Processor.

This module provides a unified processor that can handle packages from multiple
sources (GitHub, GitLab, SourceForge, etc.) using the new source-based architecture.
"""

import logging
import asyncio
import polars as pl
from typing import List, Dict, Any, Optional, Set
from pathlib import Path
from dataclasses import asdict

try:
    from .sources import (
        SourceType, PackageMetadata, get_factory, auto_detect_and_process
    )
    from .config import get_config
    from .utils.file_utils import ensure_directory_exists
except ImportError:
    # Fallback imports for direct execution
    import sys
    current_dir = Path(__file__).parent
    sys.path.insert(0, str(current_dir))
    
    from sources import (
        SourceType, PackageMetadata, get_factory, auto_detect_and_process
    )

logger = logging.getLogger(__name__)


class UnifiedPackageProcessor:
    """
    Unified processor for packages from multiple sources.
    
    This processor evolves from the original PackageProcessor.py to support
    multiple package sources through the new source-based architecture.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Initialize source factory
        self.source_factory = get_factory()
        
        # Processing statistics
        self.stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'by_source': {},
        }
    
    def process_from_csv(self, input_path: str, output_path: str = None) -> str:
        """
        Process packages from a CSV file with URLs.
        
        Args:
            input_path: Path to input CSV file
            output_path: Path for output CSV file (optional)
        
        Returns:
            Path to the generated output file
        """
        if not Path(input_path).exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        # Read input CSV
        try:
            df = pl.read_csv(input_path)
        except Exception as e:
            self.logger.error(f"Failed to read CSV file {input_path}: {e}")
            raise
        
        # Process packages
        packages = self._process_dataframe(df)
        
        # Generate output
        output_file = output_path or self._generate_output_path(input_path)
        self._save_results(packages, output_file)
        
        # Print summary
        self._print_summary()
        
        return output_file
    
    def process_urls(self, urls: List[str]) -> List[PackageMetadata]:
        """
        Process a list of URLs.
        
        Args:
            urls: List of package URLs to process
        
        Returns:
            List of processed package metadata
        """
        packages = []
        
        for url in urls:
            try:
                package = self._process_single_url(url)
                if package:
                    packages.append(package)
                    self.stats['successful'] += 1
                else:
                    self.stats['failed'] += 1
            except Exception as e:
                self.logger.error(f"Failed to process URL {url}: {e}")
                self.stats['failed'] += 1
            
            self.stats['total_processed'] += 1
        
        return packages
    
    async def process_urls_async(self, urls: List[str], max_concurrent: int = 10) -> List[PackageMetadata]:
        """
        Process URLs asynchronously.
        
        Args:
            urls: List of package URLs to process
            max_concurrent: Maximum concurrent processing tasks
        
        Returns:
            List of processed package metadata
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_with_semaphore(url: str) -> Optional[PackageMetadata]:
            async with semaphore:
                return await asyncio.to_thread(self._process_single_url, url)
        
        # Create tasks
        tasks = [process_with_semaphore(url) for url in urls]
        
        # Execute tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        packages = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Failed to process URL {urls[i]}: {result}")
                self.stats['failed'] += 1
            elif result:
                packages.append(result)
                self.stats['successful'] += 1
            else:
                self.stats['failed'] += 1
            
            self.stats['total_processed'] += 1
        
        return packages
    
    def _process_dataframe(self, df: pl.DataFrame) -> List[PackageMetadata]:
        """Process packages from a polars DataFrame."""
        packages = []
        
        # Determine URL column
        url_column = self._find_url_column(df)
        if not url_column:
            raise ValueError("No URL column found in CSV")
        
        # Process each row
        for row in df.iter_rows(named=True):
            url = row.get(url_column)
            if not url:
                continue
            
            try:
                package = self._process_single_url(url)
                if package:
                    packages.append(package)
                    self.stats['successful'] += 1
                else:
                    self.stats['failed'] += 1
            except Exception as e:
                self.logger.error(f"Failed to process URL {url}: {e}")
                self.stats['failed'] += 1
            
            self.stats['total_processed'] += 1
        
        return packages
    
    def _process_single_url(self, url: str) -> Optional[PackageMetadata]:
        """Process a single URL."""
        # Use auto-detection to find appropriate source
        source_configs = self.config.get('source_configs', {})
        package = auto_detect_and_process(url, source_configs)
        
        if package:
            # Update statistics
            source_type = package.source_type.value
            self.stats['by_source'][source_type] = self.stats['by_source'].get(source_type, 0) + 1
        
        return package
    
    def _find_url_column(self, df: pl.DataFrame) -> Optional[str]:
        """Find the URL column in the DataFrame."""
        possible_columns = ['url', 'URL', 'package_url', 'repository_url', 'link']
        
        for col in possible_columns:
            if col in df.columns:
                return col
        
        # Fallback: check if any column contains URLs
        for col in df.columns:
            if df[col].dtype == pl.Utf8:
                sample_values = df[col].head(5).to_list()
                if any('http' in str(val) for val in sample_values if val):
                    return col
        
        return None
    
    def _generate_output_path(self, input_path: str) -> str:
        """Generate output file path based on input path."""
        input_file = Path(input_path)
        output_dir = Path("data")
        ensure_directory_exists(output_dir)
        
        output_file = output_dir / f"AllPackageInfo_{input_file.stem}.csv"
        return str(output_file)
    
    def _save_results(self, packages: List[PackageMetadata], output_path: str):
        """Save processed packages to CSV."""
        if not packages:
            self.logger.warning("No packages to save")
            return
        
        # Convert packages to records
        records = []
        for package in packages:
            record = {
                'PackageIdentifier': package.identifier,
                'Source': package.source_type.value,
                'Name': package.name,
                'RepositoryURL': package.repository.url if package.repository else '',
                'Description': package.repository.description if package.repository else '',
                'Language': package.repository.language if package.repository else '',
                'Stars': package.repository.stars if package.repository else 0,
                'LatestVersion': package.latest_release.version if package.latest_release else '',
                'VersionFormatPattern': self._extract_version_pattern(package.latest_release.version if package.latest_release else ''),
                'InstallerURLsCount': package.installer_urls_count,
                'URLPatterns': ','.join(package.url_patterns) if package.url_patterns else '',
                'DownloadURLs': ','.join(package.latest_release.download_urls) if package.latest_release and package.latest_release.download_urls else '',
                'IsPrerelease': package.latest_release.is_prerelease if package.latest_release else False,
                'ReleaseDate': package.latest_release.release_date if package.latest_release else '',
            }
            records.append(record)
        
        # Create DataFrame and save
        df = pl.DataFrame(records)
        df.write_csv(output_path)
        
        self.logger.info(f"Saved {len(packages)} packages to {output_path}")
        
        # Save summary
        self._save_summary(packages, output_path)
    
    def _extract_version_pattern(self, version: str) -> str:
        """Extract version format pattern from version string."""
        if not version:
            return ''
        
        # Simple pattern extraction (can be enhanced)
        import re
        
        # Replace numbers with placeholders
        pattern = re.sub(r'\d+', 'X', version)
        
        return pattern
    
    def _save_summary(self, packages: List[PackageMetadata], output_path: str):
        """Save processing summary."""
        summary_path = Path(output_path).with_suffix('.summary.txt')
        
        # Count by source
        source_counts = {}
        for package in packages:
            source = package.source_type.value
            source_counts[source] = source_counts.get(source, 0) + 1
        
        # Generate summary
        summary_lines = [
            "Package Processing Summary",
            "=" * 30,
            f"Total packages processed: {len(packages)}",
            f"Processing statistics: {self.stats}",
            "",
            "Packages by source:",
        ]
        
        for source, count in sorted(source_counts.items()):
            summary_lines.append(f"  {source}: {count}")
        
        # Save summary
        with open(summary_path, 'w') as f:
            f.write('\n'.join(summary_lines))
        
        self.logger.info(f"Saved summary to {summary_path}")
    
    def _print_summary(self):
        """Print processing summary to console."""
        self.logger.info(f"Processing completed: {self.stats}")
        
        if self.stats['by_source']:
            self.logger.info("Packages by source:")
            for source, count in self.stats['by_source'].items():
                self.logger.info(f"  {source}: {count}")


def main():
    """Main entry point when run as script."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Unified Package Processor")
    parser.add_argument('input', help='Input CSV file path')
    parser.add_argument('-o', '--output', help='Output CSV file path')
    parser.add_argument('--async', action='store_true', help='Use async processing')
    parser.add_argument('--config', help='Configuration file path')
    
    args = parser.parse_args()
    
    # Load configuration
    config = {}
    if args.config:
        try:
            config = get_config(args.config)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
    
    # Create processor
    processor = UnifiedPackageProcessor(config)
    
    # Process packages
    try:
        output_file = processor.process_from_csv(args.input, args.output)
        print(f"Processing completed. Output saved to: {output_file}")
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
