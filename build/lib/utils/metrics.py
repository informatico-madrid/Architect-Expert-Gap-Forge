# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0
"""
Prometheus-compatible metrics for the discovery module.

T030: Implement metrics exportables (Prometheus-friendly) for:
- ParseError counter (by repo/profile)
- Latencies
- Files marked rate

Usage:
    from src.utils.metrics import DiscoveryMetrics

    metrics = DiscoveryMetrics()
    metrics.increment_parse_error("my_repo", "homeassistant")
    metrics.record_file_processing_time("my_repo", 0.123)
    metrics.increment_files_marked("my_repo", 5)
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class ParseErrorMetric:
    """Tracks parse errors per repo and profile."""

    repo: str
    profile: str


@dataclass(slots=True, frozen=True)
class ProcessingLatency:
    """Tracks processing latency for a file."""

    repo: str
    latency_seconds: float
    timestamp: float = field(default_factory=time.time)


class DiscoveryMetrics:
    """Metrics collector for discovery module.

    Thread-safe metrics collection with Prometheus-compatible format.
    """

    def __init__(self) -> None:
        """Initialize the metrics collector."""
        self._lock = threading.RLock()
        self._parse_errors: dict[str, ParseErrorMetric] = {}
        self._parse_error_counts: dict[str, int] = {}
        self._latencies: list[ProcessingLatency] = []
        self._files_marked: dict[str, int] = {}
        self._files_processed: dict[str, int] = {}

    def _make_key(self, repo: str, profile: str) -> str:
        """Create a unique key for the metric."""
        return f"{repo}:{profile}"

    def increment_parse_error(self, repo: str, profile: str) -> None:
        """Increment parse error counter for the given repo/profile.

        Args:
            repo: Repository name.
            profile: Profile name (e.g., 'homeassistant').
        """
        key = self._make_key(repo, profile)
        with self._lock:
            if key not in self._parse_errors:
                self._parse_errors[key] = ParseErrorMetric(repo=repo, profile=profile)
                self._parse_error_counts[key] = 0
            self._parse_error_counts[key] += 1

    def record_file_processing_time(
        self,
        repo: str,
        latency_seconds: float,
    ) -> None:
        """Record the time taken to process a file.

        Args:
            repo: Repository name.
            latency_seconds: Time taken in seconds.
        """
        with self._lock:
            self._latencies.append(
                ProcessingLatency(repo=repo, latency_seconds=latency_seconds)
            )

    def increment_files_marked(self, repo: str, count: int = 1) -> None:
        """Increment the count of files marked for review.

        Args:
            repo: Repository name.
            count: Number of files marked (default: 1).
        """
        with self._lock:
            self._files_marked[repo] = self._files_marked.get(repo, 0) + count

    def increment_files_processed(self, repo: str, count: int = 1) -> None:
        """Increment the count of files processed.

        Args:
            repo: Repository name.
            count: Number of files processed (default: 1).
        """
        with self._lock:
            self._files_processed[repo] = self._files_processed.get(repo, 0) + count

    def get_parse_error_count(self, repo: str, profile: str) -> int:
        """Get parse error count for a repo/profile.

        Args:
            repo: Repository name.
            profile: Profile name.

        Returns:
            Number of parse errors.
        """
        key = self._make_key(repo, profile)
        with self._lock:
            return self._parse_error_counts.get(key, 0)

    def get_mean_latency(self, repo: Optional[str] = None) -> float:
        """Get mean processing latency.

        Args:
            repo: Optional repository filter. If None, returns global mean.

        Returns:
            Mean latency in seconds.
        """
        with self._lock:
            filtered = self._latencies
            if repo:
                filtered = [
                    latency for latency in self._latencies if latency.repo == repo
                ]

            if not filtered:
                return 0.0

            return sum(latency.latency_seconds for latency in filtered) / len(filtered)

    def get_p95_latency(self, repo: Optional[str] = None) -> float:
        """Get P95 processing latency.

        Args:
            repo: Optional repository filter. If None, returns global P95.

        Returns:
            P95 latency in seconds.
        """
        with self._lock:
            filtered = self._latencies
            if repo:
                filtered = [
                    latency for latency in self._latencies if latency.repo == repo
                ]

            if not filtered:
                return 0.0

            sorted_latencies = sorted(latency.latency_seconds for latency in filtered)
            idx = int(len(sorted_latencies) * 0.95)
            return sorted_latencies[min(idx, len(sorted_latencies) - 1)]

    def get_files_marked_count(self, repo: str) -> int:
        """Get count of files marked for review.

        Args:
            repo: Repository name.

        Returns:
            Number of files marked.
        """
        with self._lock:
            return self._files_marked.get(repo, 0)

    def get_files_processed_count(self, repo: str) -> int:
        """Get count of files processed.

        Args:
            repo: Repository name.

        Returns:
            Number of files processed.
        """
        with self._lock:
            return self._files_processed.get(repo, 0)

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format.

        Returns:
            String in Prometheus text format.
        """
        lines = ["# HELP discovery_parse_errors_total Total parse errors"]
        lines.append("# TYPE discovery_parse_errors_total counter")

        with self._lock:
            for key, metric in self._parse_errors.items():
                count = self._parse_error_counts.get(key, 0)
                lines.append(
                    f'discovery_parse_errors_total{{repo="{metric.repo}",profile="{metric.profile}"}} {count}'
                )

            lines.append("")
            lines.append(
                "# HELP discovery_file_processing_seconds File processing latency"
            )
            lines.append("# TYPE discovery_file_processing_seconds summary")
            mean = self.get_mean_latency()
            lines.append(f"discovery_file_processing_seconds_sum {mean:.6f}")
            lines.append(
                f"discovery_file_processing_seconds_count {len(self._latencies)}"
            )

            lines.append("")
            lines.append(
                "# HELP discovery_files_marked_total Total files marked for review"
            )
            lines.append("# TYPE discovery_files_marked_total counter")
            for repo, count in self._files_marked.items():
                lines.append(f'discovery_files_marked_total{{repo="{repo}"}} {count}')

            lines.append("")
            lines.append("# HELP discovery_files_processed_total Total files processed")
            lines.append("# TYPE discovery_files_processed_total counter")
            for repo, count in self._files_processed.items():
                lines.append(
                    f'discovery_files_processed_total{{repo="{repo}"}} {count}'
                )

        return "\n".join(lines)

    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._parse_errors.clear()
            self._parse_error_counts.clear()
            self._latencies.clear()
            self._files_marked.clear()
            self._files_processed.clear()


# Global metrics instance for easy import
_default_metrics: Optional[DiscoveryMetrics] = None  # noqa: RUF015 - module-level default for singleton pattern


def get_metrics() -> DiscoveryMetrics:
    """Get the global metrics instance.

    Returns:
        The global DiscoveryMetrics instance.
    """
    global _default_metrics
    if _default_metrics is None:
        _default_metrics = DiscoveryMetrics()
    return _default_metrics
