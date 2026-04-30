# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0
"""
Integration tests for performance benchmarking.

Validates that the processor meets performance targets:
- Throughput: >= 1000 files/hour/worker
- Latency: mean < 200ms, P95 < 1s
- Repos: >= 10 repos/hour

T032: Performance benchmarking & CI comparison.
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pytest

from src.utils.extractors.factory import get_adapter
from src.utils.extractors.base import ParseError
from tests.fixtures.reference_corpus import REFERENCE_CORPUS_PATH


# Performance targets from spec SC-005
THROUGHPUT_TARGET = 1000  # files/hour/worker
LATENCY_MEAN_TARGET_MS = 200
LATENCY_P95_TARGET_MS = 1000
REPOS_PER_HOUR_TARGET = 10


def get_python_files(repo_path: Path) -> list[Path]:
    """Get all Python files from a repository."""
    python_files = []
    for path in repo_path.rglob("*.py"):
        # Skip __pycache__ and hidden directories within the repo
        rel_parts = path.relative_to(repo_path).parts
        if "__pycache__" in rel_parts or any(p.startswith(".") for p in rel_parts):
            continue
        python_files.append(path)
    return python_files


def process_file_timed(adapter, file_path: Path) -> dict:
    """Process a single file and return timing information."""
    start_time = time.perf_counter()
    try:
        dependencies = adapter.extract_dependencies(file_path)
        elapsed = time.perf_counter() - start_time
        return {
            "success": True,
            "elapsed_ms": elapsed * 1000,
            "dependencies": len(dependencies),
            "error": None,
        }
    except ParseError as e:
        elapsed = time.perf_counter() - start_time
        return {
            "success": False,
            "elapsed_ms": elapsed * 1000,
            "dependencies": 0,
            "error": str(e),
        }
    except Exception as e:
        elapsed = time.perf_counter() - start_time
        return {
            "success": False,
            "elapsed_ms": elapsed * 1000,
            "dependencies": 0,
            "error": str(e),
        }


class TestBenchmarkCompare:
    """Test suite for performance benchmarking."""

    def test_benchmark_corpus_exists(self) -> None:
        """Verify that reference corpus exists for benchmarking."""
        corpus_path = REFERENCE_CORPUS_PATH
        assert corpus_path.exists(), f"Reference corpus not found: {corpus_path}"

        homeassistant_path = corpus_path / "homeassistant"
        assert homeassistant_path.exists(), (
            f"Home Assistant corpus not found: {homeassistant_path}"
        )

        repos = [d for d in homeassistant_path.iterdir() if d.is_dir()]
        assert len(repos) >= 5, f"Expected at least 5 repos, found {len(repos)}"

    def test_benchmark_latency_mean(self) -> None:
        """Test that mean latency per file is below target."""
        adapter = get_adapter("homeassistant")
        corpus_path = REFERENCE_CORPUS_PATH / "homeassistant"
        repos = sorted([d for d in corpus_path.iterdir() if d.is_dir()])[:5]

        all_latencies = []
        for repo in repos:
            python_files = get_python_files(repo)
            for file_path in python_files:
                result = process_file_timed(adapter, file_path)
                all_latencies.append(result["elapsed_ms"])

        mean_latency = np.mean(all_latencies)
        assert mean_latency < LATENCY_MEAN_TARGET_MS, (
            f"Mean latency {mean_latency:.2f}ms exceeds target {LATENCY_MEAN_TARGET_MS}ms"
        )

    def test_benchmark_latency_p95(self) -> None:
        """Test that P95 latency per file is below target."""
        adapter = get_adapter("homeassistant")
        corpus_path = REFERENCE_CORPUS_PATH / "homeassistant"
        repos = sorted([d for d in corpus_path.iterdir() if d.is_dir()])[:5]

        all_latencies = []
        for repo in repos:
            python_files = get_python_files(repo)
            for file_path in python_files:
                result = process_file_timed(adapter, file_path)
                all_latencies.append(result["elapsed_ms"])

        p95_latency = np.percentile(all_latencies, 95)
        assert p95_latency < LATENCY_P95_TARGET_MS, (
            f"P95 latency {p95_latency:.2f}ms exceeds target {LATENCY_P95_TARGET_MS}ms"
        )

    def test_benchmark_throughput(self) -> None:
        """Test that throughput meets target."""
        adapter = get_adapter("homeassistant")
        corpus_path = REFERENCE_CORPUS_PATH / "homeassistant"
        repos = sorted([d for d in corpus_path.iterdir() if d.is_dir()])[:5]

        all_latencies = []
        total_files = 0

        for repo in repos:
            python_files = get_python_files(repo)
            for file_path in python_files:
                result = process_file_timed(adapter, file_path)
                all_latencies.append(result["elapsed_ms"])
                total_files += 1

        total_time_seconds = sum(all_latencies) / 1000
        files_per_hour = (
            (total_files / total_time_seconds) * 3600 if total_time_seconds > 0 else 0
        )

        assert files_per_hour >= THROUGHPUT_TARGET, (
            f"Throughput {files_per_hour:.0f} files/hour is below target {THROUGHPUT_TARGET}"
        )

    def test_benchmark_repos_per_hour(self) -> None:
        """Test that repos per hour meets target."""
        adapter = get_adapter("homeassistant")
        corpus_path = REFERENCE_CORPUS_PATH / "homeassistant"
        repos = sorted([d for d in corpus_path.iterdir() if d.is_dir()])[:5]

        repo_times = []
        for repo in repos:
            python_files = get_python_files(repo)
            repo_latencies = []

            for file_path in python_files:
                result = process_file_timed(adapter, file_path)
                repo_latencies.append(result["elapsed_ms"])

            repo_time_seconds = sum(repo_latencies) / 1000
            repo_times.append(repo_time_seconds)

        avg_time_per_repo = np.mean(repo_times) if repo_times else 0
        repos_per_hour = (3600 / avg_time_per_repo) if avg_time_per_repo > 0 else 0

        assert repos_per_hour >= REPOS_PER_HOUR_TARGET, (
            f"Repos per hour {repos_per_hour:.1f} is below target {REPOS_PER_HOUR_TARGET}"
        )

    def test_benchmark_metrics_exportable(self) -> None:
        """Test that benchmark metrics can be exported in Prometheus-friendly format."""
        adapter = get_adapter("homeassistant")
        corpus_path = REFERENCE_CORPUS_PATH / "homeassistant"
        repos = sorted([d for d in corpus_path.iterdir() if d.is_dir()])[:2]

        all_latencies = []
        total_files = 0
        total_errors = 0

        for repo in repos:
            python_files = get_python_files(repo)
            for file_path in python_files:
                result = process_file_timed(adapter, file_path)
                all_latencies.append(result["elapsed_ms"])
                total_files += 1
                if not result["success"]:
                    total_errors += 1

        mean_latency = np.mean(all_latencies)
        p95_latency = np.percentile(all_latencies, 95)
        p99_latency = np.percentile(all_latencies, 99)
        total_time_seconds = sum(all_latencies) / 1000
        files_per_hour = (
            (total_files / total_time_seconds) * 3600 if total_time_seconds > 0 else 0
        )

        # Prometheus-style metrics (gauge format)
        metrics = [
            f"aegf_benchmark_files_processed_total {total_files}",
            f"aegf_benchmark_files_with_errors_total {total_errors}",
            f"aegf_benchmark_latency_mean_ms {mean_latency:.2f}",
            f"aegf_benchmark_latency_p95_ms {p95_latency:.2f}",
            f"aegf_benchmark_latency_p99_ms {p99_latency:.2f}",
            f"aegf_benchmark_throughput_files_per_hour {files_per_hour:.0f}",
        ]

        # Verify metrics can be parsed
        for metric in metrics:
            name = metric.split(" ")[0]
            value = float(metric.split(" ")[1])
            assert name.startswith("aegf_benchmark_"), f"Invalid metric name: {name}"
            assert value >= 0, f"Invalid metric value: {value}"
