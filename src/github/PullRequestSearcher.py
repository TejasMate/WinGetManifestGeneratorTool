#!/usr/bin/env python3
"""
GitHub GraphQL PR Search Module for WinGet Package Processing

This module provides efficient searching and analysis of Pull Requests in the Windows Package Manager
(WinGet) community repository using GitHub's GraphQL API. It's integrated with the package processing
pipeline to determine the status of package updates.

Key Features:
- Fast GraphQL-based PR searching (more efficient than REST API)
- Search across PR titles and descriptions for specific package names
- Filter by PR state (open, closed, merged)
- Optimized for microsoft/winget-pkgs repository
- Integrated with existing token management system
- Handles HasAnyURLMatch logic: only searches PRs when HasAnyURLMatch is False

Author: GitHub Copilot AI Assistant
License: MIT
"""

import requests
import json
import time
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional, Union
from pathlib import Path
import sys
import polars as pl
import asyncio
import aiohttp

# Handle imports for direct execution
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

try:
    from utils.token_manager import TokenManager
    from utils.unified_utils import GitHubAPI, GitHubConfig
    from config import get_config
except ImportError:
    # Fallback for when run from different directory
    sys.path.insert(0, str(parent_dir.parent))
    from src.utils.token_manager import TokenManager
    from src.utils.unified_utils import GitHubAPI, GitHubConfig
    from src.config import get_config

logger = logging.getLogger(__name__)


class WinGetPRSearcher:
    """
    GitHub GraphQL API client for searching Pull Requests in the microsoft/winget-pkgs repository.
    
    This class provides optimized methods for searching and retrieving PR data using GitHub's GraphQL API,
    specifically designed for WinGet package processing workflow.
    
    Attributes:
        graphql_url (str): GitHub GraphQL API endpoint
        repo_owner (str): Repository owner (microsoft)
        repo_name (str): Repository name (winget-pkgs)  
        session (requests.Session): HTTP session with authentication headers
    """
    
    def __init__(self, token: str):
        """
        Initialize the GitHub GraphQL client with authentication.
        
        Args:
            token (str): GitHub personal access token with appropriate permissions
            
        Raises:
            ValueError: If token is empty or None
        """
        if not token:
            raise ValueError("GitHub token is required for GraphQL API")
        
        self.graphql_url = "https://api.github.com/graphql"
        self.repo_owner = "microsoft"
        self.repo_name = "winget-pkgs"
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        })
    
    def execute_query(self, query: str, variables: Dict = None) -> Dict:
        """
        Execute a GraphQL query against the GitHub API with enhanced error handling and rate limiting.
        
        Args:
            query (str): The GraphQL query string
            variables (Dict, optional): Variables to pass to the GraphQL query
            
        Returns:
            Dict: The data portion of the GraphQL response
            
        Raises:
            Exception: If the HTTP request fails or GraphQL returns errors
        """
        payload = {
            'query': query,
            'variables': variables or {}
        }
        
        # Simple rate limiting - wait 100ms between requests
        time.sleep(0.1)
        
        try:
            response = self.session.post(self.graphql_url, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                
                # Check for GraphQL errors
                if 'errors' in result:
                    logger.error(f"GraphQL errors: {result['errors']}")
                    raise Exception(f"GraphQL errors: {result['errors']}")
                
                return result.get('data', {})
            else:
                logger.error(f"HTTP error {response.status_code}: {response.text}")
                raise Exception(f"HTTP error {response.status_code}: {response.text}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            raise Exception(f"Request error: {e}")
    
    def search_package_prs(self, package_name: str, max_results: int = 100, states: list = None) -> List[Dict]:
        """
        Search for Pull Requests related to a specific package using GitHub's GraphQL search API.
        Enhanced version with state filtering and improved search terms.
        
        Args:
            package_name (str): The package identifier to search for (e.g., "Hugo.Hugo.Extended")
            max_results (int, optional): Maximum number of results to return. Defaults to 100.
            states (list, optional): List of PR states to search for (OPEN, CLOSED, MERGED)
        
        Returns:
            List[Dict]: List of PR objects containing metadata like title, state,
                       creation date, author, and merge/close dates
        """
        if states is None:
            states = ["OPEN", "CLOSED", "MERGED"]
        
        # Escape the package name for GraphQL search
        escaped_package_name = package_name.replace('"', '\\"')
        
        # Build search query - search in PR titles
        search_query = f'repo:{self.repo_owner}/{self.repo_name} is:pr "{escaped_package_name}" in:title'
        
        query = """
        query SearchPackagePRs($query: String!, $first: Int!, $after: String) {
            search(query: $query, type: ISSUE, first: $first, after: $after) {
                issueCount
                pageInfo {
                    hasNextPage
                    endCursor
                }
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
                        labels(first: 5) {
                            nodes {
                                name
                            }
                        }
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
        
        results = []
        cursor = None
        
        while len(results) < max_results:
            variables = {
                'query': search_query,
                'first': min(20, max_results - len(results)),  # Smaller batches
                'after': cursor
            }
            
            try:
                data = self.execute_query(query, variables)
                search_data = data['search']
                
                if not search_data['nodes']:
                    break
                
                # Filter by state and enhance PR data
                for pr in search_data['nodes']:
                    # Filter by state if specified
                    if states and pr['state'] not in states:
                        continue
                    
                    # Extract commit message if available
                    commit_message = None
                    if pr['commits']['nodes']:
                        commit_message = pr['commits']['nodes'][0]['commit']['message']
                    
                    # Enhanced PR data
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
                        "commit_message": commit_message,
                        "labels": [label["name"] for label in pr["labels"]["nodes"]]
                    }
                    
                    results.append(enhanced_pr)
                
                if not search_data['pageInfo']['hasNextPage']:
                    break
                
                cursor = search_data['pageInfo']['endCursor']
                
                # Small delay to be respectful to rate limits
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error searching PRs for {package_name}: {e}")
                break
        
        logger.debug(f"Found {len(results)} PRs for package: {package_name}")
        return results[:max_results]
    
    def search_in_pr_content(self, package_name: str, pr_data: dict) -> bool:
        """
        Search for package name in PR content (title, body, commit messages).
        
        Args:
            package_name (str): The package name to search for
            pr_data (dict): PR data from search_package_prs
            
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
    
    def get_latest_version_pr_status(self, package_name: str) -> str:
        """
        Get the status of the most recent PR for a package with enhanced matching.
        
        This method searches for PRs related to the package using improved content matching
        and returns the status of the most recent one that actually contains the package name.
        
        Args:
            package_name (str): The package identifier to search for
            
        Returns:
            str: PR status - "open", "closed", "merged", or "not_found"
        """
        try:
            # Search for PRs with expanded search
            prs = self.search_package_prs(package_name, max_results=20)
            
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
    
    def get_pr_details(self, pr_number: int) -> dict:
        """
        Get detailed information about a specific pull request.
        
        Args:
            pr_number (int): The pull request number
            
        Returns:
            dict: Detailed PR information including files and commits
        """
        query = f"""
        query {{
            repository(owner: "microsoft", name: "winget-pkgs") {{
                pullRequest(number: {pr_number}) {{
                    number
                    title
                    state
                    createdAt
                    updatedAt
                    closedAt
                    mergedAt
                    author {{
                        login
                    }}
                    baseRefName
                    headRefName
                    url
                    body
                    files(first: 100) {{
                        edges {{
                            node {{
                                path
                                additions
                                deletions
                            }}
                        }}
                    }}
                    commits(first: 100) {{
                        edges {{
                            node {{
                                commit {{
                                    message
                                    committedDate
                                }}
                            }}
                        }}
                    }}
                }}
            }}
        }}
        """
        
        try:
            data = self.execute_query(query)
            
            if "repository" not in data or not data["repository"]["pullRequest"]:
                logger.warning(f"PR #{pr_number} not found")
                return {}
            
            pr = data["repository"]["pullRequest"]
            
            # Extract file information
            files = []
            for edge in pr["files"]["edges"]:
                file_data = edge["node"]
                files.append({
                    "path": file_data["path"],
                    "additions": file_data["additions"],
                    "deletions": file_data["deletions"]
                })
            
            # Extract commit information
            commits = []
            for edge in pr["commits"]["edges"]:
                commit_data = edge["node"]["commit"]
                commits.append({
                    "message": commit_data["message"],
                    "date": commit_data["committedDate"]
                })
            
            pr_details = {
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
                "files": files,
                "commits": commits
            }
            
            return pr_details
            
        except Exception as e:
            logger.error(f"Error getting PR details for #{pr_number}: {e}")
            return {}
    
    def get_rate_limit(self) -> Dict:
        """
        Get current GitHub GraphQL API rate limit status.
        
        Returns:
            Dict: Rate limit information including:
                - limit: Maximum requests allowed per hour
                - remaining: Number of requests remaining in current window
                - resetAt: When the rate limit window resets (ISO 8601 timestamp)
        """
        query = """
        query {
            rateLimit {
                limit
                remaining
                resetAt
                cost
            }
        }
        """
        
        try:
            return self.execute_query(query)
        except Exception as e:
            logger.error(f"Error getting rate limit: {e}")
            return {
                'rateLimit': {
                    'limit': 0,
                    'remaining': 0,
                    'resetAt': '',
                    'cost': 0
                }
            }


class AsyncWinGetPRSearcher:
    """
    Async GitHub GraphQL API client for concurrent Pull Request searching.
    
    This class provides async methods for concurrent PR searching, significantly
    improving performance when processing large numbers of packages.
    """
    
    def __init__(self, token: str, max_concurrent_requests: int = 20):
        """
        Initialize the async PR searcher.
        
        Args:
            token (str): GitHub personal access token
            max_concurrent_requests (int): Maximum concurrent requests to GitHub API
        """
        if not token:
            raise ValueError("GitHub token is required for GraphQL API")
        
        self.graphql_url = "https://api.github.com/graphql"
        self.repo_owner = "microsoft"
        self.repo_name = "winget-pkgs"
        self.token = token
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        # Concurrency control
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        self.session = None
        
        logger.info(f"Async WinGet PR Searcher initialized with max {max_concurrent_requests} concurrent requests")
    
    async def __aenter__(self):
        """Async context manager entry."""
        connector = aiohttp.TCPConnector(limit=50, limit_per_host=30)
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self.session = aiohttp.ClientSession(
            headers=self.headers,
            connector=connector,
            timeout=timeout
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def execute_query_async(self, query: str, variables: Dict = None) -> Dict:
        """
        Execute a GraphQL query asynchronously.
        
        Args:
            query (str): The GraphQL query string
            variables (Dict, optional): Variables to pass to the GraphQL query
            
        Returns:
            Dict: The data portion of the GraphQL response
        """
        async with self.semaphore:  # Limit concurrent requests
            payload = {
                'query': query,
                'variables': variables or {}
            }
            
            try:
                async with self.session.post(self.graphql_url, json=payload) as response:
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
                        
            except asyncio.TimeoutError:
                logger.error("Request timeout")
                raise Exception("Request timeout")
            except Exception as e:
                logger.error(f"Request error: {e}")
                raise
    
    async def search_package_prs_async(self, package_name: str, max_results: int = 20, states: list = None) -> List[Dict]:
        """
        Search for Pull Requests asynchronously.
        
        Args:
            package_name (str): The package identifier to search for
            max_results (int): Maximum number of results to return
            states (list): List of PR states to search for
            
        Returns:
            List[Dict]: List of PR objects
        """
        if states is None:
            states = ["OPEN", "CLOSED", "MERGED"]
        
        # Escape the package name for GraphQL search
        escaped_package_name = package_name.replace('"', '\\"')
        
        # Build search query
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
            'first': min(max_results, 20)  # Limit to prevent large responses
        }
        
        try:
            data = await self.execute_query_async(query, variables)
            
            if "search" not in data:
                logger.debug(f"No search results found for package: {package_name}")
                return []
            
            prs = []
            for pr in data["search"]["nodes"]:
                # Filter by state if specified
                if states and pr["state"] not in states:
                    continue
                
                # Extract commit message if available
                commit_message = None
                if pr["commits"]["nodes"]:
                    commit_message = pr["commits"]["nodes"][0]["commit"]["message"]
                
                # Enhanced PR data
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
        Search for package name in PR content (reused from sync version).
        
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
    
    async def get_latest_version_pr_status_async(self, package_name: str) -> str:
        """
        Get the status of the most recent PR for a package asynchronously.
        
        Args:
            package_name (str): The package identifier to search for
            
        Returns:
            str: PR status - "open", "closed", "merged", or "not_found"
        """
        try:
            # Search for PRs with expanded search
            prs = await self.search_package_prs_async(package_name, max_results=20)
            
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
    
class PRStatusProcessor:
    """
    Processes package data to add PR status information.
    
    This class integrates with the existing package processing pipeline to add
    LatestVersionPullRequest status to packages that have no URL matches.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the PR status processor.
        
        Args:
            config: Configuration dictionary (if None, loads from config system)
        """
        if config is None:
            config = get_config()
        
        self.config = config
        
        # Initialize token manager and get token
        self.token_manager = TokenManager(config)
        token = self.token_manager.get_available_token()
        if not token:
            raise RuntimeError("No available GitHub tokens found")
        
        # Initialize PR searcher
        self.pr_searcher = WinGetPRSearcher(token)
        
    def process_package_pr_status(self, input_csv_path: str, output_csv_path: str) -> None:
        """
        Process packages and add LatestVersionPullRequest status.
        
        This method reads the package data, checks for packages that have no URL matches
        (HasAnyURLMatch is False), and adds PR status information for those packages.
        For packages where HasAnyURLMatch is True, sets LatestVersionPullRequest to "NotRequired".
        
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
            
            # Process packages in batches to respect rate limits
            batch_size = 25  # Reduced batch size for better rate limit management
            processed_packages = []
            
            for i in range(0, len(packages_to_process), batch_size):
                batch = packages_to_process[i:i + batch_size]
                logger.info(f"Processing batch {i//batch_size + 1}/{(len(packages_to_process) + batch_size - 1)//batch_size}")
                
                batch_results = []
                for row in batch.iter_rows(named=True):
                    package_name = row["PackageIdentifier"]
                    
                    try:
                        pr_status = self.pr_searcher.get_latest_version_pr_status(package_name)
                        batch_results.append({
                            "PackageIdentifier": package_name,
                            "LatestVersionPullRequest": pr_status
                        })
                        
                        # Log progress every 10 packages
                        if len(batch_results) % 10 == 0:
                            logger.info(f"Processed {len(processed_packages) + len(batch_results)} packages...")
                            
                    except Exception as e:
                        logger.error(f"Error processing {package_name}: {e}")
                        batch_results.append({
                            "PackageIdentifier": package_name,
                            "LatestVersionPullRequest": "error"
                        })
                
                processed_packages.extend(batch_results)
                
                # Add delay between batches to respect rate limits
                time.sleep(3)  # Increased delay for better rate limit management
            
            # Update the dataframe with PR status results
            if processed_packages:
                pr_status_df = pl.DataFrame(processed_packages)
                
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


class AsyncPRStatusProcessor:
    """
    Async version of PRStatusProcessor for high-performance PR status processing.
    
    This class processes packages concurrently to dramatically improve performance
    when dealing with large numbers of packages.
    """
    
    def __init__(self, config: Optional[Dict] = None, max_concurrent_requests: int = 20):
        """
        Initialize the async PR status processor.
        
        Args:
            config: Configuration dictionary (if None, loads from config system)
            max_concurrent_requests: Maximum concurrent requests to GitHub API
        """
        if config is None:
            config = get_config()
        
        self.config = config
        self.max_concurrent_requests = max_concurrent_requests
        
        # Initialize token manager and get token
        self.token_manager = TokenManager(config)
        token = self.token_manager.get_available_token()
        if not token:
            raise RuntimeError("No available GitHub tokens found")
        
        self.token = token
    
    async def process_package_batch_async(self, packages: List[Dict], searcher: AsyncWinGetPRSearcher) -> List[Dict]:
        """
        Process a batch of packages concurrently.
        
        Args:
            packages: List of package dictionaries
            searcher: Async PR searcher instance
            
        Returns:
            List of results with PR status
        """
        async def process_single_package(package):
            package_name = package["PackageIdentifier"]
            try:
                pr_status = await searcher.get_latest_version_pr_status_async(package_name)
                return {
                    "PackageIdentifier": package_name,
                    "LatestVersionPullRequest": pr_status
                }
            except Exception as e:
                logger.error(f"Error processing {package_name}: {e}")
                return {
                    "PackageIdentifier": package_name,
                    "LatestVersionPullRequest": "error"
                }
        
        # Process all packages in the batch concurrently
        tasks = [process_single_package(pkg) for pkg in packages]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out any exceptions and convert them to error results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Exception processing package {packages[i]['PackageIdentifier']}: {result}")
                processed_results.append({
                    "PackageIdentifier": packages[i]["PackageIdentifier"],
                    "LatestVersionPullRequest": "error"
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def process_package_pr_status_async(self, input_csv_path: str, output_csv_path: str) -> None:
        """
        Process packages and add LatestVersionPullRequest status using async operations.
        
        This method significantly improves performance by processing packages concurrently.
        
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
                df = df.with_columns(pl.lit(False).alias("HasAnyURLMatch"))
            
            # Rename the column if it exists, or add it
            if "HasOpenPullRequests" in df.columns:
                df = df.rename({"HasOpenPullRequests": "LatestVersionPullRequest"})
                logger.info("Renamed HasOpenPullRequests column to LatestVersionPullRequest")
            elif "LatestVersionPullRequest" not in df.columns:
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
            
            logger.info(f"Processing PR status for {len(packages_to_process)} packages without URL matches using async processing")
            
            if len(packages_to_process) == 0:
                logger.info("No packages need PR status processing")
                df.write_csv(output_csv_path)
                return
            
            # Convert to list of dictionaries for async processing
            packages_list = packages_to_process.to_dicts()
            
            # Process packages in batches with async concurrency
            batch_size = 50  # Larger batches since we're using async
            all_results = []
            
            async with AsyncWinGetPRSearcher(self.token, self.max_concurrent_requests) as searcher:
                for i in range(0, len(packages_list), batch_size):
                    batch = packages_list[i:i + batch_size]
                    batch_num = i // batch_size + 1
                    total_batches = (len(packages_list) + batch_size - 1) // batch_size
                    
                    logger.info(f"Processing async batch {batch_num}/{total_batches} ({len(batch)} packages)")
                    
                    start_time = time.time()
                    batch_results = await self.process_package_batch_async(batch, searcher)
                    batch_time = time.time() - start_time
                    
                    all_results.extend(batch_results)
                    
                    logger.info(f"Completed batch {batch_num}/{total_batches} in {batch_time:.2f}s ({len(batch_results)} packages processed)")
                    
                    # Progress update
                    total_processed = len(all_results)
                    logger.info(f"Total progress: {total_processed}/{len(packages_list)} packages processed")
                    
                    # Small delay between batches to be respectful to rate limits
                    if batch_num < total_batches:  # Don't delay after the last batch
                        await asyncio.sleep(1)
            
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


def main():
    """Main function for testing the PR search functionality."""
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Load configuration
        config = get_config()
        
        # Initialize processor
        processor = PRStatusProcessor(config)
        
        # Define paths
        package_config = config.get('package_processing', {})
        output_dir = package_config.get('output_directory', 'data')
        
        input_path = f"{output_dir}/AllPackageInfo.csv"
        output_path = f"{output_dir}/AllPackageInfo_WithPRStatus.csv"
        
        # Process PR status
        processor.process_package_pr_status(input_path, output_path)
        
        logger.info("PR status processing completed successfully")
        
    except Exception as e:
        logger.error(f"Error in PR status processing: {e}")
        raise


if __name__ == "__main__":
    main()
