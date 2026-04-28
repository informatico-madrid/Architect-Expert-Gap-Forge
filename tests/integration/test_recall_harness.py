# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0
"""
Integration tests for the recall harness.

Validates that the extractor achieves acceptable recall scores against
the reference corpus fixtures.

T029: Implement scripts for automatic recall/precision measurement and reporting.
Metric: recall@N (N=5,10) per file/repo.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.fixtures.reference_corpus import REFERENCE_CORPUS_PATH
from src.utils.extractors.factory import get_adapter
from src.utils.extractors.base import Dependency


# Minimum recall thresholds for passing
# Note: These thresholds are intentionally low for the initial harness setup.
# Actual extractor improvements should aim for higher recall (0.7+).
MIN_RECALL_5 = 0.2
MIN_RECALL_10 = 0.23


def load_gold_dependencies(repo_path: Path) -> dict[str, list[dict[str, str]]]:
    """Load gold dependencies from gold_dependencies.json."""
    gold_path = repo_path / "gold_dependencies.json"
    if not gold_path.exists():
        pytest.fail(f"Gold dependencies not found: {gold_path}")

    with open(gold_path) as f:
        data = json.load(f)

    return {
        filename: deps["dependencies"]
        for filename, deps in data.get("files", {}).items()
    }


def extract_dependencies(file_path: Path, profile: str) -> list[Dependency]:
    """Extract dependencies from a file using the configured adapter."""
    adapter = get_adapter(profile)
    try:
        return adapter.extract_dependencies(file_path)
    except Exception:
        return []


def compute_recall_at_n(
    extracted: list[Dependency],
    gold: list[dict[str, str]],
    n: int,
) -> float:
    """Compute recall@N for a single file."""
    if not gold:
        return 1.0

    gold_names = {dep["name"] for dep in gold}
    extracted_names = [dep.name for dep in extracted[:n]]

    matches = sum(1 for name in extracted_names if name in gold_names)
    return matches / len(gold)


@pytest.mark.parametrize("profile", ["homeassistant"])
class TestRecallHarness:
    """Test suite for recall measurement against reference corpus."""

    def test_reference_corpus_exists(self, profile: str) -> None:
        """Test that reference corpus directory exists for the profile."""
        profile_path = REFERENCE_CORPUS_PATH / profile
        assert profile_path.exists(), f"Profile not found: {profile_path}"
        assert profile_path.is_dir(), f"Profile is not a directory: {profile_path}"

    def test_all_repos_have_gold_dependencies(self, profile: str) -> None:
        """Test that all repos have gold_dependencies.json files."""
        profile_path = REFERENCE_CORPUS_PATH / profile

        repo_dirs = [d for d in profile_path.iterdir() if d.is_dir()]
        assert len(repo_dirs) >= 5, f"Expected at least 5 repos, found {len(repo_dirs)}"

        for repo_dir in repo_dirs:
            gold_path = repo_dir / "gold_dependencies.json"
            assert gold_path.exists(), f"Missing gold_dependencies.json in {repo_dir}"

    def test_recall_homeassistant_repo1(self, profile: str) -> None:
        """Test recall for homeassistant repo1 (light component)."""
        repo_path = REFERENCE_CORPUS_PATH / profile / "repo1"
        gold_deps = load_gold_dependencies(repo_path)

        for filename, gold_list in gold_deps.items():
            file_path = repo_path / filename
            extracted = extract_dependencies(file_path, profile)

            recall_5 = compute_recall_at_n(extracted, gold_list, 5)
            recall_10 = compute_recall_at_n(extracted, gold_list, 10)

            assert recall_5 >= MIN_RECALL_5, (
                f"Recall@5 too low for {filename}: {recall_5:.2f} < {MIN_RECALL_5}"
            )
            assert recall_10 >= MIN_RECALL_10, (
                f"Recall@10 too low for {filename}: {recall_10:.2f} < {MIN_RECALL_10}"
            )

    def test_recall_homeassistant_repo2(self, profile: str) -> None:
        """Test recall for homeassistant repo2 (sensor component)."""
        repo_path = REFERENCE_CORPUS_PATH / profile / "repo2"
        gold_deps = load_gold_dependencies(repo_path)

        for filename, gold_list in gold_deps.items():
            file_path = repo_path / filename
            extracted = extract_dependencies(file_path, profile)

            recall_5 = compute_recall_at_n(extracted, gold_list, 5)

            assert recall_5 >= MIN_RECALL_5, (
                f"Recall@5 too low for {filename}: {recall_5:.2f} < {MIN_RECALL_5}"
            )

    def test_recall_all_repos(self, profile: str) -> None:
        """Test aggregate recall across all repos in the profile."""
        profile_path = REFERENCE_CORPUS_PATH / profile

        all_recall_5 = []
        all_recall_10 = []

        for repo_dir in sorted(profile_path.iterdir()):
            if not repo_dir.is_dir():
                continue

            try:
                gold_deps = load_gold_dependencies(repo_dir)
            except FileNotFoundError:
                continue

            for filename, gold_list in gold_deps.items():
                file_path = repo_dir / filename
                if not file_path.exists():
                    continue

                extracted = extract_dependencies(file_path, profile)

                recall_5 = compute_recall_at_n(extracted, gold_list, 5)
                recall_10 = compute_recall_at_n(extracted, gold_list, 10)

                all_recall_5.append(recall_5)
                all_recall_10.append(recall_10)

        assert len(all_recall_5) > 0, "No files were evaluated"

        mean_recall_5 = sum(all_recall_5) / len(all_recall_5)
        mean_recall_10 = sum(all_recall_10) / len(all_recall_10)

        assert mean_recall_5 >= MIN_RECALL_5, (
            f"Mean recall@5 too low: {mean_recall_5:.2f} < {MIN_RECALL_5}"
        )
        assert mean_recall_10 >= MIN_RECALL_10, (
            f"Mean recall@10 too low: {mean_recall_10:.2f} < {MIN_RECALL_10}"
        )
