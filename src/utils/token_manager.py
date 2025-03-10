import os
import time
from typing import List, Optional, Dict
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class TokenManager:
    def __init__(self):
        self.tokens = self._load_tokens()
        self.current_token_index = 0
        self.token_limits: Dict[str, Dict] = {}
        
    def _load_tokens(self) -> List[str]:
        """Load GitHub tokens from environment variables."""
        tokens = []
        i = 1
        while True:
            token = os.getenv(f'TOKEN_{i}')
            if not token:
                # Try the default TOKEN for backward compatibility
                if i == 1:
                    default_token = os.getenv('TOKEN')
                    if default_token:
                        tokens.append(default_token)
                break
            tokens.append(token)
            i += 1
            
        if not tokens:
            logging.error("No GitHub tokens found in environment variables")
            raise ValueError("No GitHub tokens found in environment variables")
        logging.info(f"Loaded {len(tokens)} GitHub tokens")
        return tokens
    
    def _update_rate_limit(self, token: str, remaining: int, reset_time: int) -> None:
        """Update rate limit information for a token."""
        self.token_limits[token] = {
            'remaining': remaining,
            'reset_time': reset_time
        }
        logging.debug(f"Updated rate limits for token: remaining={remaining}, reset_time={reset_time}")
    
    def _is_token_available(self, token: str) -> bool:
        """Check if a token has available rate limit."""
        if token not in self.token_limits:
            return True
            
        limit_info = self.token_limits[token]
        if limit_info['remaining'] > 0:
            return True
            
        current_time = time.time()
        if current_time >= limit_info['reset_time']:
            return True
            
        return False
    
    def get_available_token(self) -> Optional[str]:
        """Get the next available token, rotating through the list if necessary."""
        start_index = self.current_token_index
        
        while True:
            current_token = self.tokens[self.current_token_index]
            
            if self._is_token_available(current_token):
                return current_token
                
            # Move to next token
            self.current_token_index = (self.current_token_index + 1) % len(self.tokens)
            
            # If we've checked all tokens and come back to where we started
            if self.current_token_index == start_index:
                # Calculate the minimum wait time among all tokens
                current_time = time.time()
                min_wait_time = float('inf')
                for token_info in self.token_limits.values():
                    wait_time = token_info['reset_time'] - current_time
                    if wait_time > 0:
                        min_wait_time = min(min_wait_time, wait_time)
                
                if min_wait_time != float('inf'):
                    logging.warning(f"All tokens are rate limited. Minimum wait time: {min_wait_time:.2f} seconds")
                return None
    
    def update_token_limits(self, token: str, response_headers: Dict) -> None:
        """Update token limits based on GitHub API response headers."""
        try:
            remaining = int(response_headers.get('X-RateLimit-Remaining', 0))
            reset_time = int(response_headers.get('X-RateLimit-Reset', 0))
            self._update_rate_limit(token, remaining, reset_time)
        except (ValueError, TypeError) as e:
            logging.error(f"Error updating token limits: {e}")
    
    def has_valid_tokens(self) -> bool:
        """Check if there are any valid tokens available."""
        for token in self.tokens:
            if self._is_token_available(token):
                return True
        return False