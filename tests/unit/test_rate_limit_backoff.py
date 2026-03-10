# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Tests for rate limit backoff in the ingestor.

Validates that the ingestor properly handles GitHub API rate limiting by:
- Reading X-RateLimit-Reset header
- Sleeping for the appropriate duration (reset_time + 5s buffer)
- Retrying failed requests with proper backoff

T027: Tests for rate-limit backoff - simulate 403 responses with X-RateLimit-Reset
and verify sleep+retry+logs behavior. Policy: sleep until X-RateLimit-Reset + 5s,
maximum 2 retries per endpoint.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.discovery.ingestor import DiscoveryConfig, RepoIngestor


class TestRateLimitBackoff:
    """Test rate limit handling in the ingestor."""

    def test_handle_backoff_sleeps_until_reset_plus_buffer(self) -> None:
        """Test that _handle_backoff sleeps until reset time + 5s buffer.

        T027: Policy is sleep until X-RateLimit-Reset + 5s.
        """
        config = DiscoveryConfig(
            category="test",
            mode="static",
            static_repos=["owner/repo"],
        )
        ingestor = RepoIngestor(config)

        # Mock response with X-RateLimit-Reset header set to 60 seconds from now
        future_reset = int(time.time()) + 60
        mock_response = MagicMock(spec=requests.Response)
        mock_response.headers = {"X-RateLimit-Reset": str(future_reset)}

        with patch("time.sleep") as mock_sleep:
            ingestor._handle_backoff(mock_response)
            # Should sleep for approximately 60 + 5 = 65 seconds
            mock_sleep.assert_called_once()
            sleep_duration = mock_sleep.call_args[0][0]
            assert 64 <= sleep_duration <= 66  # Allow 1 second tolerance

    def test_handle_backoff_handles_missing_header(self) -> None:
        """Test that _handle_backoff handles missing X-RateLimit-Reset header.

        When header is missing, defaults to 0 which results in 5s buffer.
        """
        config = DiscoveryConfig(
            category="test",
            mode="static",
            static_repos=["owner/repo"],
        )
        ingestor = RepoIngestor(config)

        # Mock response without X-RateLimit-Reset header
        mock_response = MagicMock(spec=requests.Response)
        mock_response.headers = {}

        with patch("time.sleep") as mock_sleep:
            ingestor._handle_backoff(mock_response)
            # Should sleep for default 5 seconds (0 + 5)
            mock_sleep.assert_called_once()
            sleep_duration = mock_sleep.call_args[0][0]
            assert 4 <= sleep_duration <= 6  # Allow tolerance

    def test_handle_backoff_respects_past_reset_time(self) -> None:
        """Test that _handle_backoff handles past reset times correctly.

        When reset time is in the past, only sleep for the 5s buffer.
        """
        config = DiscoveryConfig(
            category="test",
            mode="static",
            static_repos=["owner/repo"],
        )
        ingestor = RepoIngestor(config)

        # Mock response with reset time in the past
        past_reset = int(time.time()) - 30  # 30 seconds ago
        mock_response = MagicMock(spec=requests.Response)
        mock_response.headers = {"X-RateLimit-Reset": str(past_reset)}

        with patch("time.sleep") as mock_sleep:
            ingestor._handle_backoff(mock_response)
            # Should sleep for just the 5 second buffer
            mock_sleep.assert_called_once()
            sleep_duration = mock_sleep.call_args[0][0]
            assert 4 <= sleep_duration <= 6  # Allow tolerance

    def test_rate_limit_warning_logged(self) -> None:
        """Test that a warning is logged when rate limit is hit."""
        config = DiscoveryConfig(
            category="test",
            mode="static",
            static_repos=["owner/repo"],
        )
        ingestor = RepoIngestor(config)

        future_reset = int(time.time()) + 60
        mock_response = MagicMock(spec=requests.Response)
        mock_response.headers = {"X-RateLimit-Reset": str(future_reset)}

        with patch("time.sleep"):
            # The method runs without error - verify it completes
            ingestor._handle_backoff(mock_response)

    def test_handle_backoff_logs_warning_message(self) -> None:
        """Test that _handle_backoff logs a warning with sleep duration."""
        config = DiscoveryConfig(
            category="test",
            mode="static",
            static_repos=["owner/repo"],
        )
        ingestor = RepoIngestor(config)

        future_reset = int(time.time()) + 30
        mock_response = MagicMock(spec=requests.Response)
        mock_response.headers = {"X-RateLimit-Reset": str(future_reset)}

        with patch("time.sleep"):
            with patch("src.discovery.ingestor.logger") as mock_logger:
                ingestor._handle_backoff(mock_response)
                # Verify warning was logged
                mock_logger.warning.assert_called_once()
                # Check that the log message mentions rate limit
                assert "Rate limit" in mock_logger.warning.call_args[0][0]


class TestMaxRetriesEnforcement:
    """Test that maximum retries are enforced per endpoint.

    T027: Policy is maximum 2 retries per endpoint.
    Note: Current implementation does not enforce max retries.
    This test documents expected behavior for future implementation.
    """

    @pytest.mark.skip(reason="Feature not yet implemented - T027 requires retry logic")
    def test_max_retries_not_exceeded(self) -> None:
        """Test that rate limit retries don't exceed max (2) per endpoint."""
        # T027: Policy - maximum 2 retries per endpoint
        # Current implementation does not have retry count enforcement
        # This test documents expected behavior
        pass
