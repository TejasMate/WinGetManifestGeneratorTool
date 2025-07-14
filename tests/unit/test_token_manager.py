"""Unit tests for the TokenManager class."""

import os
import time
import pytest
from unittest.mock import patch, Mock

from winget_automation.utils.token_manager import TokenManager
from winget_automation.exceptions import TokenManagerError


class TestTokenManager:
    """Test cases for TokenManager class."""

    def test_init_with_valid_tokens(self):
        """Test TokenManager initialization with valid tokens."""
        with patch.dict(os.environ, {"TOKEN_1": "token1", "TOKEN_2": "token2"}):
            manager = TokenManager()
            assert len(manager.tokens) == 2
            assert manager.tokens == ["token1", "token2"]
            assert manager.current_token_index == 0

    def test_init_with_legacy_token(self):
        """Test TokenManager initialization with legacy TOKEN variable."""
        with patch.dict(os.environ, {"TOKEN": "legacy_token"}, clear=True):
            manager = TokenManager()
            assert len(manager.tokens) == 1
            assert manager.tokens == ["legacy_token"]

    def test_init_no_tokens_raises_error(self):
        """Test TokenManager raises error when no tokens are found."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(TokenManagerError) as exc_info:
                TokenManager()
            assert "No GitHub tokens found" in str(exc_info.value)
            assert exc_info.value.available_tokens == 0

    def test_get_available_token_fresh_token(self):
        """Test getting an available token with fresh rate limits."""
        with patch.dict(os.environ, {"TOKEN_1": "token1"}):
            manager = TokenManager()
            token = manager.get_available_token()
            assert token == "token1"

    def test_get_available_token_with_rate_limits(self):
        """Test token rotation when rate limits are hit."""
        with patch.dict(os.environ, {"TOKEN_1": "token1", "TOKEN_2": "token2"}):
            manager = TokenManager()

            # Set rate limits for first token (exhausted)
            future_time = int(time.time()) + 3600
            manager._update_rate_limit("token1", 0, future_time)

            token = manager.get_available_token()
            assert token == "token2"

    def test_get_available_token_all_exhausted(self):
        """Test behavior when all tokens are rate limited."""
        with patch.dict(os.environ, {"TOKEN_1": "token1", "TOKEN_2": "token2"}):
            manager = TokenManager()

            # Exhaust all tokens
            future_time = int(time.time()) + 3600
            manager._update_rate_limit("token1", 0, future_time)
            manager._update_rate_limit("token2", 0, future_time)

            with pytest.raises(TokenManagerError) as exc_info:
                manager.get_available_token()
            assert "All tokens are rate limited" in str(exc_info.value)

    def test_update_token_limits_valid_headers(self):
        """Test updating token limits with valid headers."""
        with patch.dict(os.environ, {"TOKEN_1": "token1"}):
            manager = TokenManager()
            headers = {
                "X-RateLimit-Remaining": "4999",
                "X-RateLimit-Reset": "1699200000",
            }

            manager.update_token_limits("token1", headers)

            assert "token1" in manager.token_limits
            assert manager.token_limits["token1"]["remaining"] == 4999
            assert manager.token_limits["token1"]["reset_time"] == 1699200000

    def test_update_token_limits_invalid_headers(self):
        """Test handling of invalid headers."""
        with patch.dict(os.environ, {"TOKEN_1": "token1"}):
            manager = TokenManager()
            headers = {
                "X-RateLimit-Remaining": "invalid",
                "X-RateLimit-Reset": "invalid",
            }

            with pytest.raises(TokenManagerError):
                manager.update_token_limits("token1", headers)

    def test_has_valid_tokens_true(self):
        """Test has_valid_tokens returns True when tokens are available."""
        with patch.dict(os.environ, {"TOKEN_1": "token1"}):
            manager = TokenManager()
            assert manager.has_valid_tokens() is True

    def test_has_valid_tokens_false(self):
        """Test has_valid_tokens returns False when all tokens are exhausted."""
        with patch.dict(os.environ, {"TOKEN_1": "token1"}, clear=True):
            manager = TokenManager()

            # Exhaust the token
            future_time = int(time.time()) + 3600
            manager._update_rate_limit("token1", 0, future_time)

            assert manager.has_valid_tokens() is False

    def test_is_token_available_fresh_token(self):
        """Test _is_token_available with fresh token."""
        with patch.dict(os.environ, {"TOKEN_1": "token1"}):
            manager = TokenManager()
            assert manager._is_token_available("token1") is True

    def test_is_token_available_exhausted_token(self):
        """Test _is_token_available with exhausted token."""
        with patch.dict(os.environ, {"TOKEN_1": "token1"}):
            manager = TokenManager()

            future_time = int(time.time()) + 3600
            manager._update_rate_limit("token1", 0, future_time)

            assert manager._is_token_available("token1") is False

    def test_is_token_available_reset_token(self):
        """Test _is_token_available with token that has reset."""
        with patch.dict(os.environ, {"TOKEN_1": "token1"}):
            manager = TokenManager()

            past_time = int(time.time()) - 3600
            manager._update_rate_limit("token1", 0, past_time)

            assert manager._is_token_available("token1") is True

    def test_get_token_status(self):
        """Test getting status of all tokens."""
        with patch.dict(os.environ, {"TOKEN_1": "token1", "TOKEN_2": "token2"}):
            manager = TokenManager()

            # Set limits for one token
            manager._update_rate_limit("token1", 4999, int(time.time()) + 3600)

            status = manager.get_token_status()

            assert "token_1" in status
            assert "token_2" in status
            assert status["token_1"]["remaining"] == 4999
            assert status["token_2"]["remaining"] == "unknown"

    def test_token_rotation(self):
        """Test that tokens are properly rotated."""
        with patch.dict(
            os.environ, {"TOKEN_1": "token1", "TOKEN_2": "token2", "TOKEN_3": "token3"}
        ):
            manager = TokenManager()

            # Get first token
            token1 = manager.get_available_token()
            assert token1 == "token1"

            # Exhaust first token and get next
            future_time = int(time.time()) + 3600
            manager._update_rate_limit("token1", 0, future_time)

            token2 = manager.get_available_token()
            assert token2 == "token2"

            # Exhaust second token and get third
            manager._update_rate_limit("token2", 0, future_time)

            token3 = manager.get_available_token()
            assert token3 == "token3"

    @pytest.mark.parametrize(
        "remaining,reset_time,expected",
        [
            (5000, int(time.time()) + 3600, True),  # Has remaining requests
            (0, int(time.time()) - 3600, True),  # Reset time passed
            (0, int(time.time()) + 3600, False),  # No requests and not reset
        ],
    )
    def test_is_token_available_scenarios(self, remaining, reset_time, expected):
        """Test various scenarios for token availability."""
        with patch.dict(os.environ, {"TOKEN_1": "token1"}):
            manager = TokenManager()
            manager._update_rate_limit("token1", remaining, reset_time)

            assert manager._is_token_available("token1") == expected
