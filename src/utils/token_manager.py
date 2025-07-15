import os
import time
from typing import List, Optional, Dict
import logging

# Handle both relative and absolute imports
try:
    from ..exceptions import TokenManagerError, GitHubAPIError
except ImportError:
    # Fallback for direct script execution
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))
    from exceptions import TokenManagerError, GitHubAPIError

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class TokenManager:
    """Manages GitHub API tokens with automatic rotation and rate limit handling.

    This class handles multiple GitHub API tokens, automatically rotating between them
    when rate limits are hit, and tracking rate limit status for each token.

    Attributes:
        tokens: List of GitHub API tokens
        current_token_index: Index of the currently selected token
        token_limits: Dictionary tracking rate limit info for each token
    """

    def __init__(self, config: Optional[Dict] = None):
        """Initialize the TokenManager.

        Args:
            config: Configuration dictionary (optional)

        Raises:
            TokenManagerError: If no tokens are found in environment variables
        """
        self.config = config or {}
        self.tokens = self._load_tokens()
        self.current_token_index = 0
        self.token_limits: Dict[str, Dict] = {}

    def _load_tokens(self) -> List[str]:
        """Load GitHub tokens from configuration and environment variables.

        Loads tokens from:
        1. Configuration file (github.tokens)
        2. Environment variable GITHUB_TOKENS (comma-separated)
        3. Environment variables named TOKEN_1, TOKEN_2, etc.
        4. Default TOKEN variable for backward compatibility

        Returns:
            List of GitHub API tokens

        Raises:
            TokenManagerError: If no tokens are found
        """
        tokens = []
        
        # 1. Try loading from config
        github_config = self.config.get('github', {})
        config_tokens = github_config.get('tokens', [])
        if config_tokens:
            tokens.extend([token for token in config_tokens if token])
        
        # 2. Try loading from GITHUB_TOKENS environment variable
        github_tokens_env = os.getenv("GITHUB_TOKENS")
        if github_tokens_env:
            env_tokens = [token.strip() for token in github_tokens_env.split(',') if token.strip()]
            tokens.extend(env_tokens)
        
        # 3. Try loading from TOKEN_1, TOKEN_2, etc.
        i = 1
        while True:
            token = os.getenv(f"TOKEN_{i}")
            if not token:
                # Try the default TOKEN for backward compatibility on first iteration
                if i == 1:
                    default_token = os.getenv("TOKEN")
                    if default_token:
                        tokens.append(default_token)
                break
            tokens.append(token)
            i += 1

        # Remove duplicates while preserving order
        seen = set()
        unique_tokens = []
        for token in tokens:
            if token not in seen:
                seen.add(token)
                unique_tokens.append(token)

        if not unique_tokens:
            error_msg = "No GitHub tokens found. Please set tokens in config file or environment variables (GITHUB_TOKENS, TOKEN_1, TOKEN_2, etc.)"
            logging.error(error_msg)
            raise TokenManagerError(error_msg, available_tokens=0)

        logging.info(f"Loaded {len(unique_tokens)} GitHub tokens")
        return unique_tokens

    def _update_rate_limit(self, token: str, remaining: int, reset_time: int) -> None:
        """Update rate limit information for a token.

        Args:
            token: The GitHub API token
            remaining: Number of requests remaining
            reset_time: Unix timestamp when the rate limit resets
        """
        self.token_limits[token] = {"remaining": remaining, "reset_time": reset_time}
        logging.debug(
            f"Updated rate limits for token: remaining={remaining}, reset_time={reset_time}"
        )

    def _is_token_available(self, token: str) -> bool:
        """Check if a token has available rate limit.

        Args:
            token: The GitHub API token to check

        Returns:
            True if the token can be used, False otherwise
        """
        if token not in self.token_limits:
            return True

        limit_info = self.token_limits[token]
        if limit_info["remaining"] > 0:
            return True

        current_time = time.time()
        if current_time >= limit_info["reset_time"]:
            # Token is available again, reset its state for safety
            logging.info(f"Token ending in '...{token[-4:]}' is now available after rate limit reset.")
            limit_info["remaining"] = 1 # Reset to 1 to allow a check
            return True

        return False

    def get_available_token(self) -> str:
        """Get the next available token, rotating through the list if necessary.

        Returns:
            Available GitHub API token.

        Raises:
            TokenManagerError: If no tokens are available and waiting is required.
        """
        if not self.tokens:
            raise TokenManagerError("No tokens loaded.", available_tokens=0)

        start_index = self.current_token_index
        
        for _ in range(len(self.tokens)):
            token = self.tokens[self.current_token_index]
            if self._is_token_available(token):
                logging.info(f"Using token ending in '...{token[-4:]}' (Index: {self.current_token_index})")
                return token
            
            # If not available, move to the next one
            self.current_token_index = (self.current_token_index + 1) % len(self.tokens)
        
        # If we loop through all tokens and none are available
        min_wait_time = self._get_min_wait_time()
        error_msg = f"All tokens are currently rate-limited. Please wait for {min_wait_time:.2f} seconds."
        logging.error(error_msg)
        raise TokenManagerError(error_msg, available_tokens=0, wait_time=min_wait_time)

    def _get_min_wait_time(self) -> float:
        """Calculate the minimum wait time until any token becomes available."""
        current_time = time.time()
        min_wait_time = float("inf")

        if not self.token_limits:
            return 0.0

        for token in self.tokens:
            if token in self.token_limits:
                limit_info = self.token_limits[token]
                wait_time = limit_info.get("reset_time", current_time) - current_time
                if wait_time > 0:
                    min_wait_time = min(min_wait_time, wait_time)
                else:
                    # This token should be available, something is wrong if we get here
                    return 0.0 
            else:
                # Token has never been used, so it's available
                return 0.0

        return min_wait_time if min_wait_time != float("inf") else 0.0

    def handle_rate_limit_exceeded(self, token: str):
        """
        Handles the case where a token has just exceeded its rate limit.
        This method should be called by the API client when a 403 Forbidden
        error with a rate limit exceeded message is received.
        """
        logging.warning(f"Rate limit exceeded for token ending in '...{token[-4:]}'. Rotating to next token.")
        # The token is now known to be exhausted. We don't need to update its limits
        # from headers here, as the next call to get_available_token will find a new one.
        # We just move the index.
        self.current_token_index = (self.current_token_index + 1) % len(self.tokens)


    def update_token_limits(self, token: str, response_headers: Dict) -> None:
        """Update token limits based on GitHub API response headers.

        Args:
            token: The GitHub API token
            response_headers: HTTP response headers from GitHub API

        Raises:
            TokenManagerError: If headers cannot be parsed
        """
        try:
            remaining = int(response_headers.get("X-RateLimit-Remaining", 0))
            reset_time = int(response_headers.get("X-RateLimit-Reset", time.time() + 3600))
            self._update_rate_limit(token, remaining, reset_time)

            if remaining == 0:
                self.handle_rate_limit_exceeded(token)

        except (ValueError, TypeError) as e:
            error_msg = f"Error updating token limits: {e}"
            logging.error(error_msg)
            raise TokenManagerError(error_msg, available_tokens=len(self.tokens))

    def has_valid_tokens(self) -> bool:
        """Check if there are any valid tokens available.

        Returns:
            True if at least one token is available, False otherwise
        """
        for token in self.tokens:
            if self._is_token_available(token):
                return True
        return False

    def get_token_status(self) -> Dict[str, Dict]:
        """Get the status of all tokens.

        Returns:
            Dictionary containing status information for all tokens
        """
        status = {}
        current_time = time.time()

        for i, token in enumerate(self.tokens):
            token_key = f"token_{i+1}"
            if token in self.token_limits:
                limit_info = self.token_limits[token]
                wait_time = max(0, limit_info["reset_time"] - current_time)
                status[token_key] = {
                    "remaining": limit_info["remaining"],
                    "reset_time": limit_info["reset_time"],
                    "wait_time_seconds": wait_time,
                    "available": self._is_token_available(token),
                }
            else:
                status[token_key] = {
                    "remaining": "unknown",
                    "reset_time": "unknown",
                    "wait_time_seconds": 0,
                    "available": True,
                }

        return status
