#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0
"""
Performance benchmarking script for Stage 1 Discovery processor.

This script measures:
- Throughput: files/hour/worker (target >= 1000 files/hour/worker)
- Latency per-file: mean < 200ms, P95 < 1s
- Repos per hour: >= 10 repos/hour

Usage:
    python scripts/benchmark/measure_performance.py --profile homeassistant
    python scripts/benchmark/measure_performance.py --profile homeassistant --repos 5
    python scripts/benchmark/measure_performance.py --profile homeassistant --output reports/benchmark.json

T032: Performance benchmarking & CI comparison.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

# Add project root to path for imports
# Script is at scripts/benchmark/measure_performance.py
# Project root is 3 levels up
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.utils.extractors.factory import get_adapter
from src.utils.extractors.base import ParseError


def process_file_timed(adapter, file_path: Path) -> dict[str, Any]:
    """Process a single file and return timing information.

    Args:
        adapter: The extractor adapter to use.
        file_path: Path to the file to process.

    Returns:
        Dictionary with timing and result information.
    """
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


def get_python_files(repo_path: Path) -> list[Path]:
    """Get all Python files from a repository.

    Args:
        repo_path: Path to the repository.

    Returns:
        List of Python file paths.
    """
    python_files = []
    for path in repo_path.rglob("*.py"):
        # Skip __pycache__ and hidden directories
        if "__pycache__" in path.parts or any(p.startswith(".") for p in path.parts):
            continue
        python_files.append(path)
    return python_files


def benchmark_profile(
    profile: str,
    repos: list[Path] | None = None,
    max_files_per_repo: int | None = None,
) -> dict[str, Any]:
    """Run benchmark for a given profile.

    Args:
        profile: Profile name (e.g., 'homeassistant').
        repos: Optional list of repository paths to benchmark.
        max_files_per_repo: Maximum number of files to process per repo.

    Returns:
        Benchmark results dictionary.
    """
    adapter = get_adapter(profile)

    if repos is None:
        # Use reference corpus
        corpus_path = (
            Path(__file__).resolve().parent.parent.parent
            / "tests"
            / "fixtures"
            / "reference_corpus"
            / profile
        )
        if not corpus_path.exists():
            raise FileNotFoundError(f"Reference corpus not found: {corpus_path}")
        repos = [d for d in corpus_path.iterdir() if d.is_dir()]

    all_file_results = []
    total_files = 0
    total_errors = 0
    total_dependencies = 0

    for repo in repos:
        python_files = get_python_files(repo)
        if max_files_per_repo:
            python_files = python_files[:max_files_per_repo]

        for file_path in python_files:
            result = process_file_timed(adapter, file_path)
            result["file"] = str(file_path.relative_to(repo))
            result["repo"] = repo.name
            all_file_results.append(result)

            total_files += 1
            if result["success"]:
                total_dependencies += result["dependencies"]
            else:
                total_errors += 1

    # Calculate statistics
    latencies = [r["elapsed_ms"] for r in all_file_results]

    return {
        "profile": profile,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "total_files": total_files,
        "total_errors": total_errors,
        "total_dependencies": total_dependencies,
        "files_per_repo": total_files // max(len(repos), 1),
        "repos_count": len(repos),
        "latency": {
            "mean_ms": float(np.mean(latencies)),
            "median_ms": float(np.median(latencies)),
            "p95_ms": float(np.percentile(latencies, 95)),
            "p99_ms": float(np.percentile(latencies, 99)),
            "min_ms": float(np.min(latencies)),
            "max_ms": float(np.max(latencies)),
        },
        "throughput": {
            "files_per_second": total_files / (sum(latencies) / 1000)
            if latencies
            else 0,
            "files_per_hour": (total_files / (sum(latencies) / 1000 / 3600))
            if latencies
            else 0,
        },
        "targets": {
            "throughput_target": 1000,  # files/hour/worker
            "latency_mean_target_ms": 200,
            "latency_p95_target_ms": 1000,
            "repos_per_hour_target": 10,
        },
    }


def check_targets(results: dict[str, Any]) -> dict[str, bool]:
    """Check if results meet performance targets.

    Args:
        results: Benchmark results.

    Returns:
        Dictionary of target checks.
    """
    throughput = results["throughput"]["files_per_hour"]
    latency_mean = results["latency"]["mean_ms"]
    latency_p95 = results["latency"]["p95_ms"]

    # Estimate repos per hour based on files per repo
    files_per_repo = results["files_per_repo"]
    repos_per_hour = (
        (3600 * 1000) / (results["latency"]["mean_ms"] * files_per_repo)
        if files_per_repo > 0
        else 0
    )

    return {
        "throughput_ok": throughput >= results["targets"]["throughput_target"],
        "latency_mean_ok": latency_mean < results["targets"]["latency_mean_target_ms"],
        "latency_p95_ok": latency_p95 < results["targets"]["latency_p95_target_ms"],
        "repos_per_hour_ok": repos_per_hour
        >= results["targets"]["repos_per_hour_target"],
    }


def main():
    parser = argparse.ArgumentParser(
        description="Performance benchmarking for Stage 1 Discovery processor"
    )
    parser.add_argument(
        "--profile",
        type=str,
        default="homeassistant",
        help="Profile to benchmark (default: homeassistant)",
    )
    parser.add_argument(
        "--repos",
        type=int,
        help="Number of repos to use from reference corpus (default: all)",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        help="Maximum files to process per repo (default: all)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output JSON file path (default: print to stdout)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed results",
    )
    parser.add_argument(
        "--save-baseline",
        action="store_true",
        help="Save results as baseline in scripts/benchmark/baselines/",
    )
    parser.add_argument(
        "--no-fail",
        action="store_true",
        help="Don't exit with error if targets fail (useful for CI)",
    )

    args = parser.parse_args()

    # Load repos
    corpus_path = (
        Path(__file__).resolve().parent.parent.parent
        / "tests"
        / "fixtures"
        / "reference_corpus"
        / args.profile
    )
    if not corpus_path.exists():
        print(f"Error: Reference corpus not found: {corpus_path}", file=sys.stderr)
        sys.exit(1)

    all_repos = sorted([d for d in corpus_path.iterdir() if d.is_dir()])
    repos = all_repos[: args.repos] if args.repos else all_repos

    print(f"Benchmarking profile: {args.profile}")
    print(f"Using {len(repos)} repos: {[r.name for r in repos]}")

    try:
        results = benchmark_profile(
            profile=args.profile,
            repos=repos,
            max_files_per_repo=args.max_files,
        )

        # Check targets
        target_checks = check_targets(results)
        results["target_checks"] = target_checks

        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(results, f, indent=2)
            print(f"\nResults written to: {output_path}")

        if args.verbose:
            print("\n=== Detailed Results ===")
            print(json.dumps(results, indent=2))
        else:
            print("\n=== Summary ===")
            print(f"Files processed: {results['total_files']}")
            print(f"Files with errors: {results['total_errors']}")
            print(f"Dependencies extracted: {results['total_dependencies']}")
            print("\nLatency:")
            print(
                f"  Mean: {results['latency']['mean_ms']:.2f}ms (target: <{results['targets']['latency_mean_target_ms']}ms)"
            )
            print(
                f"  P95:  {results['latency']['p95_ms']:.2f}ms (target: <{results['targets']['latency_p95_target_ms']}ms)"
            )
            print("\nThroughput:")
            print(
                f"  {results['throughput']['files_per_hour']:.0f} files/hour (target: >={results['targets']['throughput_target']})"
            )
            print("\nTarget Checks:")
            for check, passed in target_checks.items():
                status = "✓ PASS" if passed else "✗ FAIL"
                print(f"  {check}: {status}")

        # Exit with error if any target fails
        if not all(target_checks.values()) and not args.no_fail:
            print("\n⚠ Some targets did not meet requirements!", file=sys.stderr)
            sys.exit(1)

        # Save as baseline if requested
        if args.save_baseline:
            baseline_dir = Path(__file__).resolve().parent / "baselines"
            baseline_dir.mkdir(parents=True, exist_ok=True)
            baseline_path = baseline_dir / f"{args.profile}.json"

            # Remove target_checks for clean baseline
            baseline_results = {
                k: v for k, v in results.items() if k != "target_checks"
            }
            with open(baseline_path, "w") as f:
                json.dump(baseline_results, f, indent=2)
            print(f"\n✓ Baseline saved to: {baseline_path}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
