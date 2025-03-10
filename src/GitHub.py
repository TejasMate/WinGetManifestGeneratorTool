import github.MatchSimilarURLs
from github.GitHubPackageProcessor import VersionAnalyzer
import github.Filter
from utils.token_manager import TokenManager
from utils.unified_utils import GitHubAPI, GitHubConfig
import logging
from pathlib import Path

def setup_logging():
    """Configure logging for the package analysis process."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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
        # Initialize GitHub API
        token_manager = TokenManager()
        token = token_manager.get_available_token()
        if not token:
            raise RuntimeError("No available GitHub tokens found")

        config = GitHubConfig(token=token)
        github_api = GitHubAPI(config)

        # Define paths
        input_path = "data/AllPackageInfo.csv"
        github_info_path = "data/GitHubPackageInfo.csv"
        cleaned_urls_path = "data/GitHubPackageInfo_CleanedURLs.csv"
        output_dir = "data/"

        # Ensure data directory exists
        ensure_data_directory(output_dir)

        # Initialize analyzer
        analyzer = VersionAnalyzer(github_api)
        
        logger.info("Starting package analysis pipeline...")
        
        # Step 1: Analyze versions
        logger.info("Analyzing package versions...")
        analyzer.analyze_versions(input_path, github_info_path)
        
        # Step 2: Process URLs
        logger.info("Processing GitHub URLs...")
        github.MatchSimilarURLs.process_urls(github_info_path, cleaned_urls_path)
        
        # Step 3: Apply filters
        logger.info("Applying filters...")
        github.Filter.process_filters(cleaned_urls_path, output_dir)
        
        logger.info("Package analysis pipeline completed successfully")
        
    except Exception as e:
        logger.error(f"Error in package analysis pipeline: {str(e)}")
        raise

if __name__ == "__main__":
    main()