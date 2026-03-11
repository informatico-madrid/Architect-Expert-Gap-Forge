#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0
"""
Recall measurement script for extractor quality assessment.

This script measures recall@N (N=5,10) for the dependency extractor
against reference corpus fixtures.

Usage:
    python scripts/measure_recall.py --profile homeassistant
    python scripts/measure_recall.py --profile homeassistant --repo repo1
    python scripts/measure_recall.py --profile homeassistant --output reports/recall.json

T029: Implement scripts for automatic recall/precision measurement and reporting.
Metric: recall@N (N=5,10) per file/repo.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.extractors.factory import get_adapter
from src.utils.extractors.base import Dependency


def load_gold_dependencies(repo_path: Path) -> dict[str, list[dict[str, str]]]:
    """Load gold dependencies from gold_dependencies.json.

    Args:
        repo_path: Path to the repository fixture.

    Returns:
        Dictionary mapping file names to their expected dependencies.
    """
    gold_path = repo_path / "gold_dependencies.json"
    if not gold_path.exists():
        raise FileNotFoundError(f"Gold dependencies not found: {gold_path}")

    with open(gold_path) as f:
        data = json.load(f)

    return {
        filename: deps["dependencies"]
        for filename, deps in data.get("files", {}).items()
    }


def extract_dependencies(file_path: Path, profile: str) -> list[Dependency]:
    """Extract dependencies from a file using the configured adapter.

    Args:
        file_path: Path to the Python file to analyze.
        profile: Profile name (e.g., 'homeassistant').

    Returns:
        List of extracted Dependency objects.
    """
    adapter = get_adapter(profile)
    try:
        adapter.parse_file(file_path)
        return adapter.extract_dependencies(file_path)
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return []


def compute_recall_at_n(
    extracted: list[Dependency],
    gold: list[dict[str, str]],
    n: int,
) -> float:
    """Compute recall@N for a single file.

    Recall@N = (# of correct dependencies in top N) / (# of total gold dependencies)

    Args:
        extracted: List of extracted dependencies (ordered by extraction).
        gold: List of gold standard dependencies.
        n: Top N dependencies to consider.

    Returns:
        Recall score between 0.0 and 1.0.
    """
    if not gold:
        return 1.0  # Perfect recall if no gold dependencies

    gold_names = {dep["name"] for dep in gold}
    extracted_names = [dep.name for dep in extracted[:n]]

    # Count matches
    matches = sum(1 for name in extracted_names if name in gold_names)

    return matches / len(gold)


def measure_recall_for_repo(
    repo_path: Path,
    profile: str,
) -> dict[str, Any]:
    """Measure recall for a single repository.

    Args:
        repo_path: Path to the repository fixture.
        profile: Profile name.

    Returns:
        Dictionary with recall metrics.
    """
    gold_deps = load_gold_dependencies(repo_path)

    results: dict[str, Any] = {
        "repo": repo_path.name,
        "files": {},
        "summary": {},
    }

    total_recall_5 = []
    total_recall_10 = []

    for filename, gold_list in gold_deps.items():
        file_path = repo_path / filename
        if not file_path.exists():
            print(f"Warning: File not found: {file_path}")
            continue

        extracted = extract_dependencies(file_path, profile)

        recall_5 = compute_recall_at_n(extracted, gold_list, 5)
        recall_10 = compute_recall_at_n(extracted, gold_list, 10)

        total_recall_5.append(recall_5)
        total_recall_10.append(recall_10)

        results["files"][filename] = {
            "recall@5": recall_5,
            "recall@10": recall_10,
            "extracted_count": len(extracted),
            "gold_count": len(gold_list),
        }

    # Compute overall recall
    if total_recall_5:
        results["summary"] = {
            "recall@5": sum(total_recall_5) / len(total_recall_5),
            "recall@10": sum(total_recall_10) / len(total_recall_10),
            "files_evaluated": len(total_recall_5),
        }

    return results


def measure_recall_for_profile(
    profile: str,
    corpus_path: Path,
    specific_repo: str | None = None,
) -> dict[str, Any]:
    """Measure recall for all repos in a profile, or a specific repo.

    Args:
        profile: Profile name (e.g., 'homeassistant').
        corpus_path: Path to the reference corpus.
        specific_repo: Optional specific repo name to evaluate.

    Returns:
        Dictionary with recall metrics for all evaluated repos.
    """
    profile_path = corpus_path / profile

    if not profile_path.exists():
        raise FileNotFoundError(f"Profile not found: {profile_path}")

    if specific_repo:
        repo_path = profile_path / specific_repo
        if not repo_path.exists():
            raise FileNotFoundError(f"Repo not found: {repo_path}")
        return measure_recall_for_repo(repo_path, profile)

    # Measure all repos in the profile
    all_results: dict[str, Any] = {
        "profile": profile,
        "repos": {},
        "aggregate": {},
    }

    repo_dirs = [d for d in profile_path.iterdir() if d.is_dir()]
    recall_5_scores = []
    recall_10_scores = []

    for repo_dir in sorted(repo_dirs):
        try:
            result = measure_recall_for_repo(repo_dir, profile)
            all_results["repos"][repo_dir.name] = result

            if "summary" in result:
                recall_5_scores.append(result["summary"]["recall@5"])
                recall_10_scores.append(result["summary"]["recall@10"])
        except Exception as e:
            print(f"Error processing {repo_dir.name}: {e}")

    if recall_5_scores:
        all_results["aggregate"] = {
            "mean_recall@5": sum(recall_5_scores) / len(recall_5_scores),
            "mean_recall@10": sum(recall_10_scores) / len(recall_10_scores),
            "repos_evaluated": len(recall_5_scores),
        }

    return all_results


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Measure extractor recall against reference corpus"
    )
    parser.add_argument(
        "--profile",
        required=True,
        help="Profile name (e.g., 'homeassistant')",
    )
    parser.add_argument(
        "--repo",
        help="Specific repo to evaluate (default: all repos)",
    )
    parser.add_argument(
        "--corpus",
        default="tests/fixtures/reference_corpus",
        help="Path to reference corpus (default: tests/fixtures/reference_corpus)",
    )
    parser.add_argument(
        "--output",
        help="Output file for results (default: stdout)",
    )

    args = parser.parse_args()

    corpus_path = Path(args.corpus)
    if not corpus_path.is_absolute():
        # Make it relative to project root
        project_root = Path(__file__).parent.parent
        corpus_path = project_root / corpus_path

    try:
        results = measure_recall_for_profile(
            args.profile,
            corpus_path,
            args.repo,
        )

        output = json.dumps(results, indent=2)

        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                f.write(output)
            print(f"Results written to {output_path}")
        else:
            print(output)

        # Return exit code based on recall
        if "aggregate" in results:
            recall_5 = results["aggregate"].get("mean_recall@5", 0)
            if recall_5 < 0.8:
                return 1  # Low recall

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
