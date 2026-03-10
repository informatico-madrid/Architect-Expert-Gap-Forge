# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0
"""
Unit tests for the metrics module.

T030: Tests that verify metrics are emitted correctly.
"""

from __future__ import annotations

import pytest

from src.utils.metrics import (
    DiscoveryMetrics,
    ParseErrorMetric,
    ProcessingLatency,
    get_metrics,
)


class TestParseErrorMetric:
    """Tests for ParseErrorMetric."""

    def test_create_parse_error_metric(self) -> None:
        """Test creating a parse error metric."""
        metric = ParseErrorMetric(repo="test_repo", profile="homeassistant")
        assert metric.repo == "test_repo"
        assert metric.profile == "homeassistant"
        assert metric.count == 0


class TestProcessingLatency:
    """Tests for ProcessingLatency."""

    def test_create_processing_latency(self) -> None:
        """Test creating a processing latency record."""
        latency = ProcessingLatency(repo="test_repo", latency_seconds=0.123)
        assert latency.repo == "test_repo"
        assert latency.latency_seconds == 0.123
        assert latency.timestamp > 0


class TestDiscoveryMetrics:
    """Tests for DiscoveryMetrics."""

    def test_increment_parse_error(self) -> None:
        """Test incrementing parse error counter."""
        metrics = DiscoveryMetrics()
        metrics.increment_parse_error("test_repo", "homeassistant")
        metrics.increment_parse_error("test_repo", "homeassistant")

        assert metrics.get_parse_error_count("test_repo", "homeassistant") == 2

    def test_increment_parse_error_different_profiles(self) -> None:
        """Test parse error counting across profiles."""
        metrics = DiscoveryMetrics()
        metrics.increment_parse_error("test_repo", "homeassistant")
        metrics.increment_parse_error("test_repo", "php_hexagonal")

        assert metrics.get_parse_error_count("test_repo", "homeassistant") == 1
        assert metrics.get_parse_error_count("test_repo", "php_hexagonal") == 1

    def test_record_file_processing_time(self) -> None:
        """Test recording file processing time."""
        metrics = DiscoveryMetrics()
        metrics.record_file_processing_time("test_repo", 0.1)
        metrics.record_file_processing_time("test_repo", 0.2)
        metrics.record_file_processing_time("test_repo", 0.3)

        mean = metrics.get_mean_latency("test_repo")
        assert 0.19 <= mean <= 0.21  # Should be ~0.2

    def test_get_p95_latency(self) -> None:
        """Test P95 latency calculation."""
        metrics = DiscoveryMetrics()
        # Add latencies from 1 to 10
        for i in range(1, 11):
            metrics.record_file_processing_time("test_repo", float(i))

        p95 = metrics.get_p95_latency("test_repo")
        assert 9.0 <= p95 <= 10.0  # P95 of 1-10 should be ~9.5

    def test_increment_files_marked(self) -> None:
        """Test incrementing files marked counter."""
        metrics = DiscoveryMetrics()
        metrics.increment_files_marked("test_repo", 5)
        metrics.increment_files_marked("test_repo", 3)

        assert metrics.get_files_marked_count("test_repo") == 8

    def test_increment_files_processed(self) -> None:
        """Test incrementing files processed counter."""
        metrics = DiscoveryMetrics()
        metrics.increment_files_processed("test_repo", 10)
        metrics.increment_files_processed("test_repo", 5)

        assert metrics.get_files_processed_count("test_repo") == 15

    def test_export_prometheus_format(self) -> None:
        """Test Prometheus format export."""
        metrics = DiscoveryMetrics()
        metrics.increment_parse_error("test_repo", "homeassistant")
        metrics.increment_parse_error("test_repo", "homeassistant")
        metrics.increment_files_marked("test_repo", 3)
        metrics.increment_files_processed("test_repo", 10)

        output = metrics.export_prometheus()

        assert "discovery_parse_errors_total" in output
        assert 'repo="test_repo"' in output
        assert 'profile="homeassistant"' in output
        assert "discovery_files_marked_total" in output
        assert "discovery_files_processed_total" in output

    def test_reset_metrics(self) -> None:
        """Test resetting all metrics."""
        metrics = DiscoveryMetrics()
        metrics.increment_parse_error("test_repo", "homeassistant")
        metrics.increment_files_marked("test_repo", 5)

        metrics.reset()

        assert metrics.get_parse_error_count("test_repo", "homeassistant") == 0
        assert metrics.get_files_marked_count("test_repo") == 0


class TestGetMetrics:
    """Tests for the get_metrics function."""

    def test_get_metrics_returns_singleton(self) -> None:
        """Test that get_metrics returns the same instance."""
        m1 = get_metrics()
        m2 = get_metrics()
        assert m1 is m2
