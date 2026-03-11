#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0
"""
Baseline comparison script for performance benchmarking.

Compares new benchmark results against stored baselines to detect regressions.

Usage:
    python scripts/benchmark/compare_baseline.py --current reports/latest.json
    python scripts/benchmark/compare_baseline.py --current reports/latest.json --baseline scripts/benchmark/baselines/homeassistant.json
    python scripts/benchmark/compare_baseline.py --current reports/latest.json --threshold 0.2

T032: Performance benchmarking & CI comparison.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    """Load JSON from file."""
    with open(path) as f:
        return json.load(f)


def compare_results(
    current: dict[str, Any],
    baseline: dict[str, Any],
    threshold: float = 0.1,
) -> dict[str, Any]:
    """Compare current results against baseline.

    Args:
        current: Current benchmark results.
        baseline: Baseline benchmark results.
        threshold: Acceptable regression threshold (default 10%).

    Returns:
        Comparison results dictionary.
    """
    comparisons = {}

    # Latency comparisons
    for metric in ["mean_ms", "p95_ms", "p99_ms"]:
        current_val = current.get("latency", {}).get(metric, 0)
        baseline_val = baseline.get("latency", {}).get(metric, 0)

        if baseline_val > 0:
            pct_change = ((current_val - baseline_val) / baseline_val) * 100
        else:
            pct_change = 0

        comparisons[metric] = {
            "current": current_val,
            "baseline": baseline_val,
            "pct_change": pct_change,
            "regression": pct_change > (threshold * 100),
        }

    # Throughput comparisons
    current_throughput = current.get("throughput", {}).get("files_per_hour", 0)
    baseline_throughput = baseline.get("throughput", {}).get("files_per_hour", 0)

    if baseline_throughput > 0:
        throughput_pct_change = (
            (current_throughput - baseline_throughput) / baseline_throughput
        ) * 100
    else:
        throughput_pct_change = 0

    comparisons["throughput_files_per_hour"] = {
        "current": current_throughput,
        "baseline": baseline_throughput,
        "pct_change": throughput_pct_change,
        "regression": throughput_pct_change < -(threshold * 100),
    }

    # Error rate comparisons
    current_error_rate = (
        current.get("total_errors", 0) / current.get("total_files", 1)
    ) * 100
    baseline_error_rate = (
        baseline.get("total_errors", 0) / baseline.get("total_files", 1)
    ) * 100

    comparisons["error_rate"] = {
        "current": current_error_rate,
        "baseline": baseline_error_rate,
        "pct_change": current_error_rate - baseline_error_rate,
        "regression": current_error_rate > baseline_error_rate,
    }

    return comparisons


def main():
    parser = argparse.ArgumentParser(
        description="Compare benchmark results against baseline"
    )
    parser.add_argument(
        "--current",
        type=str,
        required=True,
        help="Path to current benchmark results JSON",
    )
    parser.add_argument(
        "--baseline",
        type=str,
        default=None,
        help="Path to baseline JSON (default: scripts/benchmark/baselines/<profile>.json)",
    )
    parser.add_argument(
        "--profile",
        type=str,
        default="homeassistant",
        help="Profile name (used to find baseline if not specified)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.1,
        help="Acceptable regression threshold as decimal (default: 0.1 = 10%%)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output JSON file for comparison results",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed comparison",
    )

    args = parser.parse_args()

    # Load current results
    current_path = Path(args.current)
    if not current_path.exists():
        print(f"Error: Current results not found: {current_path}", file=sys.stderr)
        sys.exit(1)

    current = load_json(current_path)

    # Determine baseline path
    if args.baseline:
        baseline_path = Path(args.baseline)
    else:
        baseline_path = (
            Path(__file__).resolve().parent / "baselines" / f"{args.profile}.json"
        )

    if not baseline_path.exists():
        print(f"Error: Baseline not found: {baseline_path}", file=sys.stderr)
        sys.exit(1)

    baseline = load_json(baseline_path)

    # Compare
    comparisons = compare_results(current, baseline, args.threshold)

    # Check for regressions
    regressions = [k for k, v in comparisons.items() if v.get("regression", False)]

    # Print results
    print("=== Baseline Comparison ===")
    print(f"Current: {args.current}")
    print(f"Baseline: {baseline_path}")
    print(f"Threshold: {args.threshold * 100}%")
    print()

    if args.verbose:
        print("=== Detailed Comparisons ===")
        for metric, data in comparisons.items():
            print(f"{metric}:")
            print(f"  Current: {data.get('current', 'N/A')}")
            print(f"  Baseline: {data.get('baseline', 'N/A')}")
            pct = data.get("pct_change", 0)
            print(f"  Change: {pct:+.2f}%")
            print(f"  Regression: {data.get('regression', False)}")
            print()

    print("=== Summary ===")
    if regressions:
        print(f"⚠ REGRESSIONS DETECTED: {len(regressions)}")
        for r in regressions:
            print(f"  - {r}")
    else:
        print("✓ No regressions detected")

    # Write output if requested
    if args.output:
        output_data = {
            "current": str(current_path),
            "baseline": str(baseline_path),
            "threshold": args.threshold,
            "comparisons": comparisons,
            "regressions": regressions,
            "has_regressions": len(regressions) > 0,
        }
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(output_data, f, indent=2)
        print(f"\nComparison written to: {output_path}")

    # Exit with error if regressions detected
    if regressions:
        print("\n⚠ Performance regressions detected!", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
