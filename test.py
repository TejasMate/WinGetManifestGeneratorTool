#!/usr/bin/env python3
"""
GitHub GraphQL PR Search Tool for microsoft/winget-pkgs repository

This tool provides efficient searching and analysis of Pull Requests in the Windows Package Manager
(WinGet) community repository using GitHub's GraphQL API. It's optimized for finding package-related
PRs and extracting relevant information about package updates, new submissions, and maintenance.

Key Features:
- Fast GraphQL-based PR searching (more efficient than REST API)
- Search across PR titles and descriptions
- Filter by PR state (open, closed, merged)
- Get detailed PR information including comments, commits, and file changes
- Repository statistics and rate limit monitoring
- JSON export functionality for further analysis

The tool is specifically designed for the microsoft/winget-pkgs repository which contains
Windows package manifests and has high PR volume, making efficient search crucial.

Usage Examples:
    # Search for a specific package
    python test.py --token TOKEN "Hugo.Hugo.Extended"
    
    # Check rate limits
    python test.py --token TOKEN --rate-limit
    
    # Get repository statistics  
    python test.py --token TOKEN --repo-stats
    
    # Get detailed PR information
    python test.py --token TOKEN --pr-details 12345
    
    # Export search results
    python test.py --token TOKEN "Firefox" --export results.json

Requirements:
    - GitHub personal access token with repo access
    - Python 3.7+ with requests library
    - Internet connection for GitHub API access

Author: GitHub Copilot AI Assistant
License: MIT
"""

import requests
import json
import time
import os
from datetime import datetime, timezone
from typing import List, Dict, Optional, Union
import argparse
import sys

class GitHubGraphQLSearch:
    """
    GitHub GraphQL API client for searching Pull Requests in the microsoft/winget-pkgs repository.
    
    This class provides optimized methods for searching and retrieving PR data using GitHub's GraphQL API,
    which is more efficient than the REST API for bulk operations and complex queries.
    
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
        Execute a GraphQL query against the GitHub API.
        
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
        
        response = self.session.post(self.graphql_url, json=payload)
        
        if response.status_code != 200:
            raise Exception(f"GraphQL query failed: {response.status_code} - {response.text}")
        
        result = response.json()
        
        if 'errors' in result:
            raise Exception(f"GraphQL errors: {result['errors']}")
        
        return result['data']
    
    def get_rate_limit(self) -> Dict:
        """
        Get current GitHub GraphQL API rate limit status.
        
        Returns:
            Dict: Rate limit information including:
                - limit: Maximum requests allowed per hour
                - remaining: Number of requests remaining in current window
                - resetAt: When the rate limit window resets (ISO 8601 timestamp)
                - cost: Cost of the last query in points
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
        
        return self.execute_query(query)
    
    def search_prs_graphql(self, search_string: str, states: List[str] = None, 
                          max_results: int = None) -> List[Dict]:
        """
        Search for Pull Requests using GitHub's GraphQL search API.
        
        This method is more efficient than the REST API for searching across large
        repositories and can return up to 1000 results per search.
        
        Args:
            search_string (str): The text to search for in PR titles and bodies
            states (List[str], optional): PR states to include. Defaults to all states
                                        (OPEN, CLOSED, MERGED)
            max_results (int, optional): Maximum number of results to return.
                                       If None, auto-detects from repository (max 1000)
        
        Returns:
            List[Dict]: List of PR objects containing metadata like title, state,
                       creation date, author, labels, and change statistics
        """
        if states is None:
            states = ["OPEN", "CLOSED", "MERGED"]
        
        # If no max_results specified, get the actual total PR count
        if max_results is None:
            print("🔍 Getting total PR count from repository...")
            total_prs = self.get_total_pr_count()
            max_results = min(total_prs, 1000)  # GitHub Search API still limits to 1000
            print(f"📊 Repository has {total_prs:,} total PRs, searching up to {max_results:,} results")
        
        # Build search query
        search_query = f'repo:{self.repo_owner}/{self.repo_name} is:pr "{search_string}"'
        
        query = """
        query SearchPRs($query: String!, $first: Int!, $after: String) {
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
                        labels(first: 10) {
                            nodes {
                                name
                            }
                        }
                        comments(first: 1) {
                            totalCount
                        }
                        additions
                        deletions
                        changedFiles
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
                'first': min(100, max_results - len(results)),
                'after': cursor
            }
            
            data = self.execute_query(query, variables)
            search_data = data['search']
            
            if not search_data['nodes']:
                break
            
            results.extend(search_data['nodes'])
            
            if not search_data['pageInfo']['hasNextPage']:
                break
            
            cursor = search_data['pageInfo']['endCursor']
            
            # Small delay to be respectful
            time.sleep(0.1)
        
        return results[:max_results]
    
    def get_pr_details(self, pr_number: int) -> Dict:
        """
        Get comprehensive details about a specific Pull Request.
        
        Retrieves detailed information including comments, commits, changed files,
        labels, and statistics for a specific PR number.
        
        Args:
            pr_number (int): The PR number to get details for
            
        Returns:
            Dict: Detailed PR information including:
                - Basic metadata (title, state, dates, author)
                - Comments and their authors
                - Commit history
                - Changed files with addition/deletion counts
                - Labels and their colors
                - Change statistics (additions, deletions, changed files)
        """
        query = """
        query GetPRDetails($owner: String!, $name: String!, $number: Int!) {
            repository(owner: $owner, name: $name) {
                pullRequest(number: $number) {
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
                        url
                    }
                    labels(first: 20) {
                        nodes {
                            name
                            color
                        }
                    }
                    comments(first: 50) {
                        totalCount
                        nodes {
                            body
                            createdAt
                            author {
                                login
                            }
                        }
                    }
                    additions
                    deletions
                    changedFiles
                    headRefName
                    baseRefName
                    commits(first: 10) {
                        totalCount
                        nodes {
                            commit {
                                message
                                author {
                                    name
                                    email
                                }
                            }
                        }
                    }
                    files(first: 20) {
                        totalCount
                        nodes {
                            path
                            additions
                            deletions
                        }
                    }
                }
            }
        }
        """
        
        variables = {
            'owner': self.repo_owner,
            'name': self.repo_name,
            'number': pr_number
        }
        
        data = self.execute_query(query, variables)
        return data['repository']['pullRequest']
    
    def get_repo_stats(self) -> Dict:
        """
        Get comprehensive statistics about the microsoft/winget-pkgs repository.
        
        Returns:
            Dict: Repository statistics including:
                - stargazerCount: Number of stars
                - forkCount: Number of forks  
                - watchers.totalCount: Number of watchers
                - issues.totalCount: Number of open issues
                - openPRs.totalCount: Number of open PRs
                - closedPRs.totalCount: Number of closed PRs
                - mergedPRs.totalCount: Number of merged PRs
                - createdAt: Repository creation date
                - primaryLanguage: Main programming language
                - languages: List of programming languages used
        """
        query = """
        query GetRepoStats($owner: String!, $name: String!) {
            repository(owner: $owner, name: $name) {
                name
                description
                stargazerCount
                forkCount
                watchers {
                    totalCount
                }
                issues(states: OPEN) {
                    totalCount
                }
                openPRs: pullRequests(states: OPEN) {
                    totalCount
                }
                closedPRs: pullRequests(states: CLOSED) {
                    totalCount
                }
                mergedPRs: pullRequests(states: MERGED) {
                    totalCount
                }
                createdAt
                updatedAt
                primaryLanguage {
                    name
                }
                languages(first: 10) {
                    nodes {
                        name
                    }
                }
            }
        }
        """
        
        variables = {
            'owner': self.repo_owner,
            'name': self.repo_name
        }
        
        data = self.execute_query(query, variables)
        return data['repository']
    
    def search_in_pr_content(self, search_string: str, pr_data: Dict) -> Dict:
        """
        Search for a string within PR content and return detailed match information.
        
        Searches through the PR title, body, and comments for the specified string
        and returns structured information about where matches were found.
        
        Args:
            search_string (str): The text to search for (case-insensitive)
            pr_data (Dict): The PR data object from GraphQL response
            
        Returns:
            Dict: Formatted PR data with match details including:
                - pr_number: PR number
                - title: PR title
                - state: PR state (OPEN/CLOSED/MERGED)
                - dates: Creation and update timestamps
                - user: Author username
                - url: PR URL
                - matches: List of locations where search string was found
                - stats: PR statistics (additions, deletions, files, comments)
        """
        matches = []
        
        # Check title
        if search_string.lower() in pr_data.get('title', '').lower():
            matches.append({
                'location': 'title',
                'content': pr_data.get('title', '')
            })
        
        # Check body
        body = pr_data.get('body') or ''
        if search_string.lower() in body.lower():
            matches.append({
                'location': 'body',
                'content': body[:500] + ('...' if len(body) > 500 else '')
            })
        
        # Check comments if available
        if 'comments' in pr_data and 'nodes' in pr_data['comments']:
            for comment in pr_data['comments']['nodes']:
                comment_body = comment.get('body', '')
                if search_string.lower() in comment_body.lower():
                    matches.append({
                        'location': 'comment',
                        'author': comment.get('author', {}).get('login', ''),
                        'content': comment_body[:300] + ('...' if len(comment_body) > 300 else '')
                    })
        
        return {
            'pr_number': pr_data['number'],
            'title': pr_data['title'],
            'state': pr_data['state'],
            'created_at': pr_data['createdAt'],
            'updated_at': pr_data['updatedAt'],
            'user': pr_data.get('author', {}).get('login', '') if pr_data.get('author') else '',
            'url': pr_data['url'],
            'matches': matches,
            'stats': {
                'additions': pr_data.get('additions', 0),
                'deletions': pr_data.get('deletions', 0),
                'changed_files': pr_data.get('changedFiles', 0),
                'comments': pr_data.get('comments', {}).get('totalCount', 0)
            }
        }
    
    def print_results(self, results: List[Dict], show_stats: bool = True):
        """
        Print search results in a user-friendly formatted display.
        
        Args:
            results (List[Dict]): List of processed PR results from search_in_pr_content
            show_stats (bool): Whether to display PR statistics (additions, deletions, etc.)
        """
        print(f"\nFound {len(results)} matching PRs:")
        print("=" * 80)
        
        for result in results:
            print(f"\nPR #{result['pr_number']}: {result['title']}")
            print(f"State: {result['state']} | Author: {result['user']}")
            print(f"Created: {result['created_at']}")
            print(f"URL: {result['url']}")
            
            if show_stats and 'stats' in result:
                stats = result['stats']
                print(f"Stats: +{stats['additions']} -{stats['deletions']} lines, {stats['changed_files']} files, {stats['comments']} comments")
            
            if result.get('matches'):
                print("Matches found in:")
                for match in result['matches']:
                    if match['location'] == 'comment':
                        print(f"  - {match['location']} by {match['author']}: {match['content'][:100]}...")
                    else:
                        print(f"  - {match['location']}: {match['content'][:100]}...")
            
            print("-" * 80)
    
    def export_to_json(self, results: List[Dict], filename: str):
        """
        Export search results to a JSON file for further analysis.
        
        Args:
            results (List[Dict]): Search results to export
            filename (str): Output filename for the JSON file
        """
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"Results exported to {filename}")
    
    def get_total_pr_count(self) -> int:
        """
        Get the total number of Pull Requests in the repository across all states.
        
        Returns:
            int: Total count of PRs (open, closed, and merged combined)
        """
        query = """
        query GetTotalPRCount($owner: String!, $name: String!) {
            repository(owner: $owner, name: $name) {
                pullRequests(states: [OPEN, CLOSED, MERGED]) {
                    totalCount
                }
            }
        }
        """
        
        variables = {
            'owner': self.repo_owner,
            'name': self.repo_name
        }
        
        data = self.execute_query(query, variables)
        return data['repository']['pullRequests']['totalCount']

def main():
    """
    Main function that handles command-line interface and coordinates PR search operations.
    
    Provides a command-line interface for searching Pull Requests in the microsoft/winget-pkgs
    repository using GitHub's GraphQL API. Supports various search modes including text search,
    rate limit checking, repository statistics, and detailed PR information retrieval.
    
    Command line usage examples:
        python test.py --token TOKEN "Hugo.Hugo.Extended" --max-results 100
        python test.py --token TOKEN --rate-limit
        python test.py --token TOKEN --repo-stats  
        python test.py --token TOKEN --pr-details 12345
    """
    parser = argparse.ArgumentParser(description='GitHub GraphQL PR Search Tool - Optimized for WinGet Package Searches')
    
    # Essential arguments
    parser.add_argument('--token', required=True, help='GitHub personal access token (required)')
    parser.add_argument('search_string', nargs='?', help='Package name to search for (e.g., "Hugo.Hugo.Extended")')
    
    # Search options
    parser.add_argument('--states', nargs='+', choices=['OPEN', 'CLOSED', 'MERGED'], 
                       default=['OPEN', 'CLOSED', 'MERGED'], help='PR states to include (default: all)')
    parser.add_argument('--max-results', type=int, default=None, 
                       help='Maximum results to return (default: auto-detect from repository, GitHub API max: 1000)')
    
    # Output options  
    parser.add_argument('--export', help='Export results to JSON file')
    
    # Utility options (optional)
    parser.add_argument('--rate-limit', action='store_true', help='Check GitHub API rate limit')
    parser.add_argument('--pr-details', type=int, metavar='PR_NUMBER', help='Get detailed info for specific PR')
    parser.add_argument('--repo-stats', action='store_true', help='Show microsoft/winget-pkgs repository statistics')
    
    args = parser.parse_args()
    
    try:
        # Initialize GraphQL client
        client = GitHubGraphQLSearch(args.token)
        
        # Utility functions
        if args.rate_limit:
            rate_limit = client.get_rate_limit()
            print("GitHub GraphQL API Rate Limit:")
            print(f"Remaining: {rate_limit['rateLimit']['remaining']}/{rate_limit['rateLimit']['limit']}")
            print(f"Reset at: {rate_limit['rateLimit']['resetAt']}")
            return
        
        if args.repo_stats:
            stats = client.get_repo_stats()
            print("microsoft/winget-pkgs Repository Statistics:")
            print(f"⭐ Stars: {stats['stargazerCount']:,}")
            print(f"🍴 Forks: {stats['forkCount']:,}")
            print(f"👀 Watchers: {stats['watchers']['totalCount']:,}")
            print(f"🐛 Open Issues: {stats['issues']['totalCount']:,}")
            print(f"🔄 Open PRs: {stats['openPRs']['totalCount']:,}")
            print(f"✅ Merged PRs: {stats['mergedPRs']['totalCount']:,}")
            print(f"❌ Closed PRs: {stats['closedPRs']['totalCount']:,}")
            print(f"📅 Created: {stats['createdAt']}")
            return
        
        if args.pr_details:
            pr_data = client.get_pr_details(args.pr_details)
            print(f"📋 PR #{pr_data['number']}: {pr_data['title']}")
            print(f"Status: {pr_data['state']} | Author: {pr_data.get('author', {}).get('login', 'N/A')}")
            print(f"Created: {pr_data['createdAt']}")
            print(f"📊 Changes: +{pr_data.get('additions', 0)} -{pr_data.get('deletions', 0)} lines, {pr_data.get('changedFiles', 0)} files")
            print(f"💬 Comments: {pr_data.get('comments', {}).get('totalCount', 0)}")
            print(f"🔗 URL: {pr_data['url']}")
            
            if args.export:
                client.export_to_json([pr_data], args.export)
            return
        
        # Regular search (MAIN FEATURE)
        if not args.search_string:
            print("Error: search_string is required for search operations")
            print("Usage: python test.py --token TOKEN 'search_term' [--max-results N]")
            print("Example: python test.py --token TOKEN 'Hugo.Hugo.Extended' --max-results 1000")
            print("\nFor utility functions, search_string is not required:")
            print("  --rate-limit    Check API rate limits")
            print("  --repo-stats    Show repository statistics")  
            print("  --pr-details N  Get details for specific PR number")
            return
        
        # Perform optimized GraphQL search
        print(f"🔍 Searching for '{args.search_string}' using GraphQL API...")
        if args.max_results:
            print(f"📊 User specified limit: {args.max_results:,} results")
        
        results = client.search_prs_graphql(args.search_string, args.states, args.max_results)
        
        # Process results for display
        processed_results = []
        for pr in results:
            matches = client.search_in_pr_content(args.search_string, pr)
            processed_results.append(matches)
        
        # Print results
        client.print_results(processed_results)
        
        # Export if requested
        if args.export:
            client.export_to_json(processed_results, args.export)
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
