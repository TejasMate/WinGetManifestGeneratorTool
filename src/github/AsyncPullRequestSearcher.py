#!/usr/bin/env python3
"""
Async Pull Request Searcher for WinGet packages using GitHub GraphQL API.

This module provides asynchronous functionality to search for pull requests
related to WinGet package manifests, significantly improving performance
over sequential processing.
"""

import asyncio
import aiohttp
import time
import logging
from typing import Dict, List, Optional
from pathlib import Path
import polars as pl
import sys

# Handle imports for direct execution
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

try:
    from utils.token_manager import TokenManager
    from config import get_config
except ImportError:
    # Fallback for when run from different directory
    sys.path.insert(0, str(parent_dir.parent))
    from src.utils.token_manager import TokenManager
    from src.config import get_config

logger = logging.getLogger(__name__)


class AsyncWinGetPRSearcher:
    """
    Async GitHub GraphQL API client for searching Pull Requests in the microsoft/winget-pkgs repository.
    
    This class provides optimized async methods for searching and retrieving PR data using GitHub's GraphQL API,
    with concurrent request handling and intelligent rate limiting.
    """
    
    def __init__(self, tokens: List[str], max_concurrent_requests: int = 10):
        """
        Initialize the async GitHub GraphQL client with multiple tokens for load balancing.
        
        Args:
            tokens (List[str]): List of GitHub personal access tokens
            max_concurrent_requests (int): Maximum concurrent requests
            
        Raises:
            ValueError: If no tokens provided
        """
        if not tokens:
            raise ValueError("At least one GitHub token is required for GraphQL API")
        
        self.tokens = tokens
        self.current_token_index = 0
        self.graphql_url = "https://api.github.com/graphql"
        self.repo_owner = "microsoft"
        self.repo_name = "winget-pkgs"
        self.max_concurrent_requests = max_concurrent_requests
        
        # Rate limiting per token
        self.request_counts = {token: 0 for token in tokens}
        self.last_request_times = {token: 0 for token in tokens}
        self.min_request_interval = 0.1  # 100ms between requests per token
        
        # Semaphore to control concurrent requests
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        
        logger.info(f"Async PR Searcher initialized with {len(tokens)} tokens, max {max_concurrent_requests} concurrent requests")
    
    def get_next_token(self) -> str:
        """Get the next token in round-robin fashion for load balancing."""
        token = self.tokens[self.current_token_index]
        self.current_token_index = (self.current_token_index + 1) % len(self.tokens)
        return token
    
    async def execute_query_async(self, session: aiohttp.ClientSession, query: str, variables: Dict = None) -> Dict:
        """
        Execute a GraphQL query asynchronously with rate limiting.
        
        Args:
            session: aiohttp session
            query (str): The GraphQL query string
            variables (Dict, optional): Variables to pass to the GraphQL query
            
        Returns:
            Dict: The data portion of the GraphQL response
        """
        async with self.semaphore:
            token = self.get_next_token()
            
            # Rate limiting per token
            current_time = time.time()
            last_request_time = self.last_request_times.get(token, 0)
            time_since_last = current_time - last_request_time
            
            if time_since_last < self.min_request_interval:
                await asyncio.sleep(self.min_request_interval - time_since_last)
            
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'query': query,
                'variables': variables or {}
            }
            
            try:
                async with session.post(self.graphql_url, headers=headers, json=payload) as response:
                    self.last_request_times[token] = time.time()
                    self.request_counts[token] += 1
                    
                    if response.status == 200:
                        result = await response.json()
                        
                        if 'errors' in result:
                            logger.error(f"GraphQL errors: {result['errors']}")
                            raise Exception(f"GraphQL errors: {result['errors']}")
                        
                        return result.get('data', {})
                    else:
                        error_text = await response.text()
                        logger.error(f"HTTP error {response.status}: {error_text}")
                        raise Exception(f"HTTP error {response.status}: {error_text}")
                        
            except Exception as e:
                logger.error(f"Request error: {e}")
                raise
    
    async def search_package_prs_async(self, session: aiohttp.ClientSession, package_name: str, max_results: int = 20) -> List[Dict]:
        """
        Search for Pull Requests related to a specific package asynchronously.
        
        Args:
            session: aiohttp session
            package_name (str): The package identifier to search for
            max_results (int): Maximum number of results to return
        
        Returns:
            List[Dict]: List of PR objects containing metadata
        """
        # Escape the package name for GraphQL search
        escaped_package_name = package_name.replace('"', '\\"')
        
        # Build search query - search in PR titles
        search_query = f'repo:{self.repo_owner}/{self.repo_name} is:pr "{escaped_package_name}" in:title'
        
        query = """
        query SearchPackagePRs($query: String!, $first: Int!) {
            search(query: $query, type: ISSUE, first: $first) {
                issueCount
                nodes {
                    ... on PullRequest {
                        number
                        title
                        state
                        createdAt
                        updatedAt
                        closedAt
                        mergedAt
                        url
                        body
                        author {
                            login
                        }
                        baseRefName
                        headRefName
                        commits(first: 1) {
                            nodes {
                                commit {
                                    message
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        
        variables = {
            'query': search_query,
            'first': min(max_results, 20)  # Limit to avoid large responses
        }
        
        try:
            data = await self.execute_query_async(session, query, variables)
            
            if "search" not in data:
                logger.debug(f"No search results found for package: {package_name}")
                return []
            
            prs = []
            for pr in data["search"]["nodes"]:
                # Extract commit message if available
                commit_message = None
                if pr["commits"]["nodes"]:
                    commit_message = pr["commits"]["nodes"][0]["commit"]["message"]
                
                enhanced_pr = {
                    "number": pr["number"],
                    "title": pr["title"],
                    "state": pr["state"],
                    "created_at": pr["createdAt"],
                    "updated_at": pr["updatedAt"],
                    "closed_at": pr["closedAt"],
                    "merged_at": pr["mergedAt"],
                    "author": pr["author"]["login"] if pr["author"] else None,
                    "base_ref": pr["baseRefName"],
                    "head_ref": pr["headRefName"],
                    "url": pr["url"],
                    "body": pr["body"],
                    "commit_message": commit_message
                }
                
                prs.append(enhanced_pr)
            
            logger.debug(f"Found {len(prs)} PRs for package: {package_name}")
            return prs
            
        except Exception as e:
            logger.error(f"Error searching PRs for {package_name}: {e}")
            return []
    
    def search_in_pr_content(self, package_name: str, pr_data: dict) -> bool:
        """
        Search for package name in PR content (title, body, commit messages).
        
        Args:
            package_name (str): The package name to search for
            pr_data (dict): PR data from search_package_prs_async
            
        Returns:
            bool: True if package name found in PR content
        """
        search_terms = [
            package_name.lower(),
            package_name.replace(".", "").lower(),
            package_name.replace("-", "").lower(),
            package_name.replace("_", "").lower()
        ]
        
        # Search in title
        title = pr_data.get("title", "").lower()
        if any(term in title for term in search_terms):
            return True
        
        # Search in body
        body = pr_data.get("body", "") or ""
        if any(term in body.lower() for term in search_terms):
            return True
        
        # Search in commit message
        commit_message = pr_data.get("commit_message", "") or ""
        if any(term in commit_message.lower() for term in search_terms):
            return True
        
        return False
    
    async def get_latest_version_pr_status_async(self, session: aiohttp.ClientSession, package_name: str) -> str:
        """
        Get the status of the most recent PR for a package asynchronously.
        
        Args:
            session: aiohttp session
            package_name (str): The package identifier to search for
            
        Returns:
            str: PR status - "open", "closed", "merged", or "not_found"
        """
        try:
            # Search for PRs with expanded search
            prs = await self.search_package_prs_async(session, package_name, max_results=20)
            
            if not prs:
                logger.debug(f"No PRs found for package: {package_name}")
                return "not_found"
            
            # Filter PRs that actually contain the package name in content
            relevant_prs = []
            for pr in prs:
                if self.search_in_pr_content(package_name, pr):
                    relevant_prs.append(pr)
            
            if not relevant_prs:
                logger.debug(f"No relevant PRs found for package: {package_name}")
                return "not_found"
            
            # Sort by creation date (most recent first) 
            sorted_prs = sorted(relevant_prs, key=lambda x: x['created_at'], reverse=True)
            most_recent_pr = sorted_prs[0]
            
            # Log the found PR for debugging
            logger.debug(f"Found recent PR for {package_name}: #{most_recent_pr['number']} - {most_recent_pr['title']} ({most_recent_pr['state']})")
            
            # Return the state of the most recent relevant PR
            state = most_recent_pr['state'].lower()
            if state == 'open':
                return "open"
            elif state == 'merged':
                return "merged"
            elif state == 'closed':
                return "closed"
            else:
                return "unknown"
                
        except Exception as e:
            logger.error(f"Error getting PR status for {package_name}: {e}")
            return "error"


class AsyncPRStatusProcessor:
    """
    Async processor for adding PR status information to packages.
    
    This class integrates with the existing package processing pipeline to add
    LatestVersionPullRequest status to packages asynchronously with much better performance.
    """
    
    def __init__(self, config: Optional[Dict] = None, max_concurrent_requests: int = 15):
        """
        Initialize the async PR status processor.
        
        Args:
            config: Configuration dictionary (if None, loads from config system)
            max_concurrent_requests: Maximum concurrent requests
        """
        if config is None:
            config = get_config()
        
        self.config = config
        self.max_concurrent_requests = max_concurrent_requests
        
        # Initialize token manager and get multiple tokens if available
        self.token_manager = TokenManager(config)
        
        # Try to get multiple tokens for better performance
        tokens = []
        for _ in range(5):  # Try to get up to 5 tokens
            token = self.token_manager.get_available_token()
            if token and token not in tokens:
                tokens.append(token)
        
        if not tokens:
            raise RuntimeError("No available GitHub tokens found")
        
        # Initialize async PR searcher
        self.pr_searcher = AsyncWinGetPRSearcher(tokens, max_concurrent_requests)
        
        logger.info(f"Async PR Status Processor initialized with {len(tokens)} tokens")
    
    async def process_package_batch_async(self, session: aiohttp.ClientSession, packages: List[Dict]) -> List[Dict]:
        """
        Process a batch of packages asynchronously.
        
        Args:
            session: aiohttp session
            packages: List of package dictionaries
            
        Returns:
            List of results with PR status
        """
        # Create tasks for all packages in the batch
        tasks = []
        for package in packages:
            package_name = package["PackageIdentifier"]
            task = self.process_single_package_async(session, package_name)
            tasks.append(task)
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        batch_results = []
        for i, result in enumerate(results):
            package_name = packages[i]["PackageIdentifier"]
            
            if isinstance(result, Exception):
                logger.error(f"Error processing {package_name}: {result}")
                pr_status = "error"
            else:
                pr_status = result
            
            batch_results.append({
                "PackageIdentifier": package_name,
                "LatestVersionPullRequest": pr_status
            })
        
        return batch_results
    
    async def process_single_package_async(self, session: aiohttp.ClientSession, package_name: str) -> str:
        """
        Process a single package asynchronously.
        
        Args:
            session: aiohttp session
            package_name: Package identifier
            
        Returns:
            PR status string
        """
        try:
            return await self.pr_searcher.get_latest_version_pr_status_async(session, package_name)
        except Exception as e:
            logger.error(f"Error processing {package_name}: {e}")
            return "error"
    
    async def process_package_pr_status_async(self, input_csv_path: str, output_csv_path: str) -> None:
        """
        Process packages and add LatestVersionPullRequest status asynchronously.
        
        This method significantly improves performance by processing multiple packages
        concurrently while respecting GitHub API rate limits.
        
        Args:
            input_csv_path (str): Path to input CSV file (from GitHubPackageProcessor)
            output_csv_path (str): Path to output CSV file with PR status
        """
        try:
            logger.info(f"Reading package data from {input_csv_path}")
            
            # Read the CSV file
            df = pl.read_csv(input_csv_path)
            logger.info(f"Loaded {len(df)} packages")
            
            # Check if HasAnyURLMatch column exists
            if "HasAnyURLMatch" not in df.columns:
                logger.warning("HasAnyURLMatch column not found. This should be run after GitHubPackageProcessor.")
                # If column doesn't exist, treat all packages as needing PR search
                df = df.with_columns(pl.lit(False).alias("HasAnyURLMatch"))
            
            # Rename the column if it exists, or add it
            if "HasOpenPullRequests" in df.columns:
                df = df.rename({"HasOpenPullRequests": "LatestVersionPullRequest"})
                logger.info("Renamed HasOpenPullRequests column to LatestVersionPullRequest")
            elif "LatestVersionPullRequest" not in df.columns:
                # Add the column if it doesn't exist
                df = df.with_columns(pl.lit("unknown").alias("LatestVersionPullRequest"))
                logger.info("Added LatestVersionPullRequest column")

            # Set "NotRequired" for packages where HasAnyURLMatch is True
            packages_with_url_match = df.filter(pl.col("HasAnyURLMatch") == True)
            if len(packages_with_url_match) > 0:
                logger.info(f"Setting LatestVersionPullRequest to 'NotRequired' for {len(packages_with_url_match)} packages with URL matches")
                df = df.with_columns(
                    pl.when(pl.col("HasAnyURLMatch") == True)
                    .then(pl.lit("NotRequired"))
                    .otherwise(pl.col("LatestVersionPullRequest"))
                    .alias("LatestVersionPullRequest")
                )

            # Only process packages where HasAnyURLMatch is False and status is unknown
            packages_to_process = df.filter(
                (pl.col("HasAnyURLMatch") == False) & 
                (pl.col("LatestVersionPullRequest") == "unknown")
            )
            
            logger.info(f"Processing PR status for {len(packages_to_process)} packages without URL matches")
            
            if len(packages_to_process) == 0:
                logger.info("No packages need PR status processing")
                df.write_csv(output_csv_path)
                return
            
            # Convert to list of dictionaries for async processing
            packages_list = packages_to_process.to_dicts()
            
            # Process packages in batches asynchronously
            batch_size = 50  # Larger batches since we're doing async processing
            all_results = []
            
            # Create aiohttp session with timeout
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                for i in range(0, len(packages_list), batch_size):
                    batch = packages_list[i:i + batch_size]
                    batch_num = i // batch_size + 1
                    total_batches = (len(packages_list) + batch_size - 1) // batch_size
                    
                    logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} packages)")
                    start_time = time.time()
                    
                    # Process batch asynchronously
                    batch_results = await self.process_package_batch_async(session, batch)
                    all_results.extend(batch_results)
                    
                    elapsed = time.time() - start_time
                    logger.info(f"Batch {batch_num} completed in {elapsed:.2f}s ({len(batch_results)} packages)")
                    
                    # Small delay between batches to be respectful
                    if i + batch_size < len(packages_list):
                        await asyncio.sleep(1)
            
            logger.info(f"Async processing completed. Processed {len(all_results)} packages")
            
            # Update the dataframe with PR status results
            if all_results:
                pr_status_df = pl.DataFrame(all_results)
                
                # Join with original dataframe to update LatestVersionPullRequest column
                df = df.join(
                    pr_status_df,
                    on="PackageIdentifier",
                    how="left",
                    suffix="_new"
                )
                
                # Update the LatestVersionPullRequest column with new values where available
                df = df.with_columns(
                    pl.when(pl.col("LatestVersionPullRequest_new").is_not_null())
                    .then(pl.col("LatestVersionPullRequest_new"))
                    .otherwise(pl.col("LatestVersionPullRequest"))
                    .alias("LatestVersionPullRequest")
                ).drop("LatestVersionPullRequest_new")
            
            # Write the updated dataframe
            df.write_csv(output_csv_path)
            logger.info(f"Updated package data written to {output_csv_path}")
            
            # Log summary statistics
            status_counts = df.group_by("LatestVersionPullRequest").count().sort("count", descending=True)
            logger.info("PR Status Summary:")
            for row in status_counts.iter_rows(named=True):
                logger.info(f"  {row['LatestVersionPullRequest']}: {row['count']} packages")
                
        except Exception as e:
            logger.error(f"Error processing PR status: {e}")
            raise


# Main function for running async PR status processing
def run_async_pr_status_processing(input_csv_path: str, output_csv_path: str, config: Optional[Dict] = None):
    """
    Run async PR status processing.
    
    Args:
        input_csv_path: Path to input CSV
        output_csv_path: Path to output CSV  
        config: Configuration dictionary
    """
    async def main():
        processor = AsyncPRStatusProcessor(config, max_concurrent_requests=15)
        await processor.process_package_pr_status_async(input_csv_path, output_csv_path)
    
    # Run the async main function
    asyncio.run(main())


if __name__ == "__main__":
    # Example usage
    config = get_config()
    input_path = "data/github/GitHubPackageInfo_CleanedURLs.csv"
    output_path = "data/github/GitHubPackageInfo_PRStatus.csv"
    
    run_async_pr_status_processing(input_path, output_path, config)
