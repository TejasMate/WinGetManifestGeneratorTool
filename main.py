"""
Main Entry Point for WinGet Manifest Generator Tool.

This module replaces the legacy GitHub.py and provides a unified entry point
for processing packages from multiple sources.
"""

import sys
import logging
import argparse
from pathlib import Path
from typing import Dict, Any, Optional

# Handle imports for different execution contexts
try:
    from .core.processor import UnifiedPackageProcessor
    from .sources import SourceType, get_factory
    from .config import get_config, get_config_manager
    from .utils.file_utils import ensure_directory_exists, validate_csv_file
    from .monitoring.logging_setup import setup_logging
except ImportError:
    # Fallback for direct execution
    current_dir = Path(__file__).parent
    sys.path.insert(0, str(current_dir))
    
    from core.processor import UnifiedPackageProcessor
    from sources import SourceType, get_factory
    from config import get_config, get_config_manager
    from utils.file_utils import ensure_directory_exists, validate_csv_file

logger = logging.getLogger(__name__)


def setup_directories():
    """Set up required directories."""
    directories = ['data', 'logs', 'output']
    
    for dir_name in directories:
        try:
            ensure_directory_exists(Path(dir_name))
            logger.debug(f"Ensured directory exists: {dir_name}")
        except Exception as e:
            logger.warning(f"Failed to create directory {dir_name}: {e}")


def validate_input_file(file_path: str) -> bool:
    """Validate the input file."""
    is_valid, error_msg = validate_csv_file(Path(file_path))
    
    if not is_valid:
        logger.error(f"Input file validation failed: {error_msg}")
        return False
    
    logger.info(f"Input file validated: {file_path}")
    return True


def create_processor(config: Dict[str, Any]) -> UnifiedPackageProcessor:
    """Create and configure the package processor."""
    try:
        processor = UnifiedPackageProcessor(config)
        logger.info("Created unified package processor")
        return processor
    except Exception as e:
        logger.error(f"Failed to create processor: {e}")
        raise


def process_packages(processor: UnifiedPackageProcessor, input_file: str, 
                    output_file: Optional[str] = None, use_async: bool = False) -> str:
    """Process packages from input file."""
    try:
        logger.info(f"Starting package processing: {input_file}")
        
        if use_async:
            logger.info("Using async processing mode")
            # For async mode, we'd need to modify the processor
            # For now, fall back to sync mode
            logger.warning("Async mode not fully implemented, using sync mode")
        
        output_path = processor.process_from_csv(input_file, output_file)
        
        logger.info(f"Package processing completed: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Package processing failed: {e}")
        raise


def print_source_status():
    """Print status of available sources."""
    factory = get_factory()
    registry = factory.registry
    
    available_sources = registry.get_available_sources()
    
    print("\nAvailable Package Sources:")
    print("-" * 30)
    
    for source_type in available_sources:
        source = registry.get_source_instance(source_type)
        if source:
            status = "✓ Ready"
            if not source.validate_config():
                status = "⚠ Configuration issues"
        else:
            status = "✗ Failed to initialize"
        
        print(f"  {source_type.value}: {status}")
    
    print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="WinGet Manifest Generator Tool - Multi-Source Package Processor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s input.csv                              # Process packages from CSV
  %(prog)s input.csv -o output.csv                # Specify output file
  %(prog)s input.csv --config config.yaml        # Use custom config
  %(prog)s input.csv --async                     # Use async processing
  %(prog)s --status                              # Show source status
        """
    )
    
    parser.add_argument('input', nargs='?', help='Input CSV file path')
    parser.add_argument('-o', '--output', help='Output CSV file path')
    parser.add_argument('-c', '--config', help='Configuration file path')
    parser.add_argument('--async', dest='async_mode', action='store_true', help='Use async processing')
    parser.add_argument('--status', action='store_true', help='Show source status and exit')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose logging')
    parser.add_argument('--debug', action='store_true', help='Debug logging')
    
    args = parser.parse_args()
    
    # Set up logging
    try:
        if hasattr(setup_logging, '__call__'):
            setup_logging()
        else:
            # Fallback logging setup
            level = logging.DEBUG if args.debug else (logging.INFO if args.verbose else logging.WARNING)
            logging.basicConfig(
                level=level,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
    except Exception as e:
        print(f"Warning: Failed to set up logging: {e}")
        logging.basicConfig(level=logging.INFO)
    
    logger.info("Starting WinGet Manifest Generator Tool")
    
    # Show source status if requested
    if args.status:
        print_source_status()
        return 0
    
    # Validate arguments
    if not args.input:
        parser.error("Input file is required (use --status to check source status)")
    
    try:
        # Set up directories
        setup_directories()
        
        # Load configuration
        config = {}
        if args.config:
            try:
                config = get_config(args.config)
                logger.info(f"Loaded configuration from: {args.config}")
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
                return 1
        else:
            # Try to load default config
            try:
                config = get_config()
                logger.info("Loaded default configuration")
            except Exception as e:
                logger.warning(f"Failed to load default config: {e}")
                logger.info("Proceeding with minimal configuration")
        
        # Show source status
        print_source_status()
        
        # Validate input file
        if not validate_input_file(args.input):
            return 1
        
        # Create processor
        processor = create_processor(config)
        
        # Process packages
        output_path = process_packages(processor, args.input, args.output, args.async_mode)
        
        print(f"\n✓ Processing completed successfully!")
        print(f"Output saved to: {output_path}")
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Processing interrupted by user")
        print("\nProcessing interrupted by user")
        return 1
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"\n✗ Processing failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
