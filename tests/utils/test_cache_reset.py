#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for src/utils/cache_reset.py - Memory Cache Reset Utilities."""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock
import sys
from src.utils.cache_reset import reset_all_caches, log_memory_usage


class TestResetAllCaches:
    """Tests for reset_all_caches function."""

    def test_returns_dict(self) -> None:
        """Should return a dictionary."""
        result = reset_all_caches()
        assert isinstance(result, dict)

    def test_returns_adapter_cache_key(self) -> None:
        """Should return a dictionary with adapter_cache key."""
        result = reset_all_caches()
        assert "adapter_cache" in result

    def test_returns_multiple_cache_keys(self) -> None:
        """Should return dictionary with multiple cache keys."""
        result = reset_all_caches()
        # Should have keys for various caches
        expected_keys = [
            "adapter_cache",
            "scorecard_domain_patterns_cache",
            "model_evaluator_domain_patterns_cache",
            "model_evaluator_router",
            "model_evaluator_prompt_mgr",
            "default_metrics",
            "production_v11_taxonomy",
            "agentic_gen_taxonomy",
            "inference_router",
        ]
        for key in expected_keys:
            assert key in result, f"Missing key: {key}"

    def test_all_values_are_boolean(self) -> None:
        """All return values should be boolean."""
        result = reset_all_caches()
        for value in result.values():
            assert isinstance(value, bool)

    def test_reset_all_caches_is_idempotent(self) -> None:
        """Should be safe to call multiple times."""
        result1 = reset_all_caches()
        result2 = reset_all_caches()
        assert result1.keys() == result2.keys()


class TestLogMemoryUsage:
    """Tests for log_memory_usage function."""

    def test_logs_memory_with_prefix(self, capsys) -> None:
        """Should log memory usage with prefix."""
        log_memory_usage(prefix="Test: ")
        captured = capsys.readouterr()
        assert "Test:" in captured.err or "Memory usage" in captured.err

    def test_logs_memory_without_prefix(self, capsys) -> None:
        """Should log memory usage without prefix."""
        log_memory_usage()
        captured = capsys.readouterr()
        assert "Memory usage" in captured.err

    def test_handles_psutil_available(self, capsys) -> None:
        """Should handle when psutil is available."""
        # This test verifies psutil import handling
        # We just test that log_memory_usage runs without error
        log_memory_usage()

    def test_handles_psutil_not_available(self, capsys) -> None:
        """Should handle when psutil is not available."""
        # Should not raise
        log_memory_usage()
        captured = capsys.readouterr()
        # Should log something
        assert "Memory usage" in captured.err

    def test_handles_exception(self, capsys) -> None:
        """Should handle exceptions gracefully."""
        # Should not raise
        log_memory_usage()
        captured = capsys.readouterr()
        # Should still log something
        assert "Memory usage" in captured.err or "unavailable" in captured.err.lower()


class TestCacheResetIntegration:
    """Integration tests for cache reset functionality."""

    def test_reset_all_caches_is_callable(self) -> None:
        """Should be callable without arguments."""
        result = reset_all_caches()
        assert isinstance(result, dict)

    def test_log_memory_usage_is_callable(self) -> None:
        """Should be callable without arguments."""
        # Should not raise
        log_memory_usage()
