# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Unit Tests for GOVERNANCE_RULES Extraction
==========================================

Tests governance file detection at repo root (.codecov.yml, .gitlab-ci.yml, etc.)

Requirements: AC-4.1 to AC-4.4, FR-4
"""

from __future__ import annotations

from pathlib import Path

from src.discovery import ProcessingConfig, RepoProcessor


class TestGovernanceExtraction:
    """Unit tests for GOVERNANCE_RULES extraction."""

    def test_codecov_yml_detection(self, tmp_path: Path) -> None:
        """Test that .codecov.yml is detected as governance file.

        AC-4.1: .codecov.yml should be detected as governance file.
        """
        repo_root = tmp_path
        repo_root.mkdir(exist_ok=True)

        owner_dir = repo_root / "owner" / "myrepo"
        owner_dir.mkdir(parents=True)

        # Create .codecov.yml at repo root
        (owner_dir / ".codecov.yml").write_text("""
codecov:
  notify:
    y: 2
    x: 2

coverage:
  status:
    project:
      default:
        target: 80%
    patch:
      default:
        target: 70%
""".strip())

        config = ProcessingConfig(
            base_dir=tmp_path,
            raw_subdir="owner",
            output_subdir="output",
            category="myrepo",
            profile="filesystem",
        )
        processor = RepoProcessor(config)
        processor.run()

        # Verify bundle was created
        output_dir = tmp_path / "output" / "myrepo"
        bundle_files = list(output_dir.rglob("*.txt"))

        # Should have GOVERNANCE_RULES
        governance_files = [
            f for f in bundle_files
            if 'GOVERNANCE_RULES' in f.read_text()
        ]

        assert len(governance_files) > 0, (
            "GOVERNANCE_RULES should be emitted for .codecov.yml"
        )

    def test_gitlab_ci_yml_detection(self, tmp_path: Path) -> None:
        """Test that .gitlab-ci.yml is detected as governance file.

        AC-4.2: .gitlab-ci.yml should be detected as governance file.
        """
        repo_root = tmp_path
        repo_root.mkdir(exist_ok=True)

        owner_dir = repo_root / "myrepo"
        owner_dir.mkdir(exist_ok=True)

        # Create .gitlab-ci.yml at repo root
        (owner_dir / ".gitlab-ci.yml").write_text("""
stages:
  - test
  - deploy

test_job:
  stage: test
  script:
    - pytest
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"

deploy_job:
  stage: deploy
  script:
    - ./deploy.sh
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
""".strip())

        config = ProcessingConfig(
            base_dir=tmp_path,
            raw_subdir=".",
            output_subdir="output",
            category="myrepo",
            profile="filesystem",
        )
        processor = RepoProcessor(config)
        processor.run()

        # Verify bundle was created
        output_dir = tmp_path / "output" / "myrepo"
        bundle_files = list(output_dir.rglob("*.txt"))

        # Should have GOVERNANCE_RULES
        governance_files = [
            f for f in bundle_files
            if 'GOVERNANCE_RULES' in f.read_text()
        ]

        assert len(governance_files) > 0, (
            "GOVERNANCE_RULES should be emitted for CLAUDE.md"
        )

    def test_multiple_governance_files(self, tmp_path: Path) -> None:
        """Test that multiple governance files at repo root are detected.

        AC-4.4: Multiple governance files should all be extracted.
        """
        repo_root = tmp_path
        repo_root.mkdir(exist_ok=True)

        owner_dir = repo_root / "myrepo"
        owner_dir.mkdir(exist_ok=True)

        # Create multiple governance files
        (owner_dir / ".codecov.yml").write_text("""
coverage:
  status:
    project:
      default:
        target: 80%
""".strip())

        (owner_dir / ".gitlab-ci.yml").write_text("""
stages:
  - test
  - deploy

test_job:
  stage: test
  script:
    - pytest
""".strip())

        (owner_dir / "CLAUDE.md").write_text("""# Project Guidelines

Follow these guidelines.
""".strip())

        config = ProcessingConfig(
            base_dir=tmp_path,
            raw_subdir=".",
            output_subdir="output",
            category="myrepo",
            profile="filesystem",
        )
        processor = RepoProcessor(config)
        processor.run()

        # Verify bundle was created
        output_dir = tmp_path / "output" / "myrepo"
        bundle_files = list(output_dir.rglob("*.txt"))

        # Should have GOVERNANCE_RULES
        governance_files = [
            f for f in bundle_files
            if 'GOVERNANCE_RULES' in f.read_text()
        ]

        assert len(governance_files) > 0, (
            "GOVERNANCE_RULES should be emitted for governance files"
        )

        # Verify all governance files are referenced
        governance = governance_files[0].read_text()
        assert '.codecov.yml' in governance, (
            "GOVERNANCE_RULES should reference .codecov.yml"
        )
        assert '.gitlab-ci.yml' in governance, (
            "GOVERNANCE_RULES should reference .gitlab-ci.yml"
        )
        assert 'CLAUDE.md' in governance, (
            "GOVERNANCE_RULES should reference CLAUDE.md"
        )

    def test_governance_not_at_component_level(self, tmp_path: Path) -> None:
        """Test that governance files at component level are NOT extracted.

        Governance files must be at repo root (owner/myrepo), not at component level.
        """
        repo_root = tmp_path
        repo_root.mkdir(exist_ok=True)

        owner_dir = repo_root / "myrepo"
        owner_dir.mkdir(exist_ok=True)

        # Create component directory
        component = owner_dir / "custom_components" / "test_component"
        component.mkdir(parents=True)

        # Create .codecov.yml at component level (NOT at repo root)
        (component / ".codecov.yml").write_text("""
coverage:
  status:
    project:
      default:
        target: 80%
""".strip())

        config = ProcessingConfig(
            base_dir=tmp_path,
            raw_subdir=".",
            output_subdir="output",
            category="myrepo",
            profile="filesystem",
        )
        processor = RepoProcessor(config)
        processor.run()

        # Verify bundle was created
        output_dir = tmp_path / "output" / "myrepo"
        bundle_files = list(output_dir.rglob("*.txt"))

        # Should NOT have GOVERNANCE_RULES (governance file is at component level, not repo root)
        governance_files = [
            f for f in bundle_files
            if 'GOVERNANCE_RULES' in f.read_text()
        ]

        assert len(governance_files) == 0, (
            "Governance file at component level should not be extracted"
        )
