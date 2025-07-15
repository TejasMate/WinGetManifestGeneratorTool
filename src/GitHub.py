# Handle both relative and absolute imports
import sys
import os
from pathlib import Path

# Add current directory to path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

try:
    from github.MatchSimilarURLs import process_urls
    from github.GitHubPackageProcessor import VersionAnalyzer
    from github.Filter import process_filters
    from github.AsyncPullRequestSearcher import AsyncPRStatusProcessor, run_async_pr_status_processing
    from utils.token_manager import TokenManager
    from utils.unified_utils import GitHubAPI, GitHubConfig
    from config import get_config_manager, get_config
except ImportError as e:
    print(f"Import error: {e}")
    # Add parent directory as fallback
    parent_dir = current_dir.parent
    sys.path.insert(0, str(parent_dir))
    
    from src.github.MatchSimilarURLs import process_urls
    from src.github.GitHubPackageProcessor import VersionAnalyzer
    from src.github.Filter import process_filters
    from src.github.AsyncPullRequestSearcher import AsyncPRStatusProcessor, run_async_pr_status_processing
    from src.utils.token_manager import TokenManager
    from src.utils.unified_utils import GitHubAPI, GitHubConfig
    from src.config import get_config_manager, get_config

import logging
from pathlib import Path


def setup_logging():
    """Configure logging for the package analysis process."""
    try:
        config = get_config()
        logging_config = config.get('logging', {})
        
        logging.basicConfig(
            level=getattr(logging, logging_config.get('level', 'INFO')),
            format=logging_config.get('format', "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
        )
    except Exception:
        # Fallback to default logging if config fails
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )


def ensure_data_directory(data_path: str) -> None:
    """Ensure the data directory exists.

    Args:
        data_path (str): Path to the data directory
    """
    Path(data_path).mkdir(parents=True, exist_ok=True)


def main():
    # Set up logging
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        # Load configuration
        app_config = get_config()
        
        # Initialize GitHub API
        token_manager = TokenManager(app_config)
        token = token_manager.get_available_token()
        if not token:
            raise RuntimeError("No available GitHub tokens found")

        # Create GitHub config from app config
        github_config_data = app_config.get('github', {})
        config = GitHubConfig(
            token=token,
            base_url=github_config_data.get('api_url', 'https://api.github.com'),
            per_page=github_config_data.get('per_page', 100)
        )
        github_api = GitHubAPI(config)

        # Define paths from configuration
        package_config = app_config.get('package_processing', {})
        output_dir = package_config.get('output_directory', 'data')
        
        # Create GitHub subdirectory
        github_dir = Path(output_dir) / "github"
        github_dir.mkdir(parents=True, exist_ok=True)
        
        input_path = f"{output_dir}/AllPackageInfo.csv"
        github_info_path = f"{github_dir}/GitHubPackageInfo.csv"
        cleaned_urls_path = f"{github_dir}/GitHubPackageInfo_CleanedURLs.csv"
        pr_status_path = f"{github_dir}/GitHubPackageInfo_PRStatus.csv"
        filter_output_dir = str(github_dir)

        # Ensure output directories exist
        ensure_data_directory(output_dir)
        ensure_data_directory(str(github_dir))

        # Initialize analyzer
        analyzer = VersionAnalyzer(github_api)

        logger.info("Starting package analysis pipeline...")

        # Step 1: Analyze versions
        logger.info("Analyzing package versions...")
        analyzer.analyze_versions(input_path, github_info_path)

        # Step 2: Process URLs
        logger.info("Processing GitHub URLs...")
        process_urls(github_info_path, cleaned_urls_path)

        # Step 3: Add PR status information for packages without URL matches (ASYNC)
        logger.info("Processing PR status for packages without URL matches (using async implementation)...")
        run_async_pr_status_processing(cleaned_urls_path, pr_status_path, app_config)

        # Step 4: Apply filters
        logger.info("Applying filters...")
        process_filters(pr_status_path, filter_output_dir)

        logger.info("Package analysis pipeline completed successfully")

    except Exception as e:
        logger.error(f"Error in package analysis pipeline: {str(e)}")
        raise


if __name__ == "__main__":
    main()
