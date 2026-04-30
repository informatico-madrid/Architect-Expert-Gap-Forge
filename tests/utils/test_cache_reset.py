#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for src/utils/cache_reset.py - Memory Cache Reset Utilities."""

from __future__ import annotations

from unittest.mock import patch
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


class TestCacheResetEdgeCases:
    """Tests for edge cases in cache reset."""

    def test_adapter_cache_attribute_missing(self, capsys) -> None:
        """Should handle missing _adapter_cache attribute."""
        # First import the factory to ensure it's in sys.modules
        from src.utils.extractors import factory as factory_module

        original_cache = getattr(factory_module, '_adapter_cache', None)
        if hasattr(factory_module, '_adapter_cache'):
            delattr(factory_module, '_adapter_cache')
        try:
            result = reset_all_caches()
            # Should return False for adapter_cache
            assert result["adapter_cache"] is False
        finally:
            # Restore the attribute
            if original_cache is not None:
                factory_module._adapter_cache = original_cache

    def test_scorecard_cache_attribute_missing(self, capsys) -> None:
        """Should handle missing _domain_patterns_cache in scorecard."""
        from src.audit import scorecard
        original_cache = getattr(scorecard, '_domain_patterns_cache', None)
        if hasattr(scorecard, '_domain_patterns_cache'):
            delattr(scorecard, '_domain_patterns_cache')
        try:
            result = reset_all_caches()
            # Should return False for scorecard_domain_patterns_cache
            assert result["scorecard_domain_patterns_cache"] is False
        finally:
            if original_cache is not None:
                scorecard._domain_patterns_cache = original_cache

    def test_metrics_attribute_missing(self, capsys) -> None:
        """Should handle missing _default_metrics in metrics."""
        from src.utils import metrics
        original_metrics = getattr(metrics, '_default_metrics', None)
        # Set to None instead of deleting to maintain module namespace
        metrics._default_metrics = None
        try:
            result = reset_all_caches()
            # Should return True since we successfully set it to None
            assert result["default_metrics"] is True
        finally:
            # Restore original value (which may be None or an instance)
            metrics._default_metrics = original_metrics

    def test_production_v11_not_present(self) -> None:
        """Should handle missing production_v11 module."""
        # Temporarily remove production_v11 from sys.modules
        original_module = sys.modules.get("src.factory.production_v11")
        if "src.factory.production_v11" in sys.modules:
            del sys.modules["src.factory.production_v11"]
        try:
            result = reset_all_caches()
            # Should return False for production_v11_taxonomy
            assert result["production_v11_taxonomy"] is False
        finally:
            # Restore the original module
            if original_module is not None:
                sys.modules["src.factory.production_v11"] = original_module

    def test_agentic_gen_not_present(self) -> None:
        """Should handle missing agentic_gen module."""
        # Temporarily remove agentic_gen from sys.modules
        original_module = sys.modules.get("src.factory.agentic_gen")
        if "src.factory.agentic_gen" in sys.modules:
            del sys.modules["src.factory.agentic_gen"]
        try:
            result = reset_all_caches()
            # Should return False for agentic_gen_taxonomy
            assert result["agentic_gen_taxonomy"] is False
        finally:
            # Restore the original module
            if original_module is not None:
                sys.modules["src.factory.agentic_gen"] = original_module


class TestLogMemoryUsageEdgeCases:
    """Tests for edge cases in log_memory_usage."""

    def test_psutil_import_fails(self, capsys) -> None:
        """Should handle psutil import failure."""
        with patch.dict("sys.modules", {"psutil": None}):
            # Need to reimport to trigger the branch
            import importlib
            import src.utils.cache_reset as cache_reset_module
            importlib.reload(cache_reset_module)
            # Now test with psutil not available
            cache_reset_module.log_memory_usage()
            captured = capsys.readouterr()
            # Should fall back to resource or show unavailable
            assert "Memory usage" in captured.err or "unavailable" in captured.err.lower()

    def test_resource_unavailable(self, capsys) -> None:
        """Should handle resource module unavailable."""
        with patch.dict("sys.modules", {"psutil": None, "resource": None}):
            import importlib
            import src.utils.cache_reset as cache_reset_module
            importlib.reload(cache_reset_module)
            cache_reset_module.log_memory_usage()
            captured = capsys.readouterr()
            # Should show unavailable
            assert "unavailable" in captured.err.lower()
