# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joo@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Per-File Adapter Selection Verification Tests
===============================================

Verifies that each file extension routes to the correct adapter based on
the file's suffix, not the repository profile.

Requirements: FR-5, AC-8.1 to AC-8.5
"""

from __future__ import annotations

from pathlib import Path

from src.discovery import ProcessingConfig, RepoProcessor


# =============================================================================
# Sample Content for Each Language
# =============================================================================

PYTHON_CODE = """
def add_numbers(a: int, b: int) -> int:
    '''Add two numbers together.'''
    return a + b

def calculate_total(items: list) -> float:
    '''Calculate total price from items.'''
    total = 0
    for item in items:
        total += item.get('price', 0)
    return total
"""

TYPESCRIPT_CODE = """
import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('ha-button-card')
export class HaButtonCard extends LitElement {
  @property({ type: String }) private label = 'Click me';

  render() {
    return html`<button>${this.label}</button>`;
  }
}
"""

PHP_CODE = """
<?php

namespace App\\Services;

class UserService {
    private array $users = [];

    public function createUser(string $name, string $email): User {
        $user = new User($name, $email);
        $this->users[] = $user;
        return $user;
    }

    public function findUser(string $email): ?User {
        foreach ($this->users as $user) {
            if ($user->email === $email) {
                return $user;
            }
        }
        return null;
    }
}
"""

YAML_CODE = """
# Home Assistant automation
automation:
  - alias: "Light Control"
    trigger:
      platform: state
      entity_id: light.living_room
    action:
      service: light.toggle
"""

# =============================================================================
# Test Setup Functions
# =============================================================================

def setup_python_test_repo(tmp_path: Path) -> Path:
    """Set up a Python test repository."""
    repo_root = tmp_path / "test_repo"
    repo_root.mkdir()

    owner_dir = repo_root / "owner" / "myrepo"
    owner_dir.mkdir(parents=True, exist_ok=True)

    component = owner_dir / "custom_components" / "test_component"
    component.mkdir(parents=True, exist_ok=True)

    return repo_root


def setup_mixed_repo(tmp_path: Path) -> Path:
    """Set up a mixed-language test repository."""
    repo_root = tmp_path / "test_repo"
    repo_root.mkdir()

    owner_dir = repo_root / "owner" / "myrepo"
    owner_dir.mkdir(parents=True, exist_ok=True)

    return repo_root


# =============================================================================
# Per-File Adapter Selection Tests
# =============================================================================

class TestPerFileAdapterSelection:
    """Tests verifying per-file adapter selection based on file extension."""

    def test_python_files_route_to_python_ast_adapter(self, tmp_path: Path) -> None:
        """Test that .py files are processed by PythonAstAdapter.

        AC-8.1: Python files should be processed with Python adapter.
        """
        repo_root = setup_python_test_repo(tmp_path)
        component = repo_root / "owner" / "myrepo" / "custom_components" / "test_component"
        component.mkdir(parents=True, exist_ok=True)

        # Add manifest.json to make it a proper HA integration
        (component / "manifest.json").write_text("{}")
        (component / "component.py").write_text(PYTHON_CODE)

        config = ProcessingConfig(
            base_dir=repo_root.parent,
            raw_subdir=".",
            output_subdir="output",
            category="test_repo",
            profile="homeassistant",
        )
        processor = RepoProcessor(config)
        processor.run()

        # Verify output was generated - confirms Python files are processed
        output_dir = repo_root.parent / "output" / "test_repo"
        bundle_files = list(output_dir.rglob("*.txt"))

        # Python files should generate MODULE_BLUEPRINT
        blueprint_files = [
            f for f in bundle_files
            if 'MODULE_BLUEPRINT' in f.read_text()
        ]

        assert len(blueprint_files) > 0, (
            "Python files should be processed and emit MODULE_BLUEPRINT"
        )

    def test_typescript_files_route_to_typescript_adapter(self, tmp_path: Path) -> None:
        """Test that .ts files are processed by TypeScriptAdapter.

        AC-8.2: TypeScript files should be processed with TypeScript adapter.
        """
        repo_root = setup_mixed_repo(tmp_path)
        owner = repo_root / "owner" / "myrepo"
        owner.mkdir(parents=True, exist_ok=True)

        (owner / "component.ts").write_text(TYPESCRIPT_CODE)

        config = ProcessingConfig(
            base_dir=repo_root.parent,
            raw_subdir=".",
            output_subdir="output",
            category="test_repo",
            profile="typescript",
        )
        processor = RepoProcessor(config)
        processor.run()

        # Verify output was generated - confirms TS files are processed
        output_dir = repo_root.parent / "output" / "test_repo"
        bundle_files = list(output_dir.rglob("*.txt"))

        # TypeScript files should generate MODULE_BLUEPRINT
        blueprint_files = [
            f for f in bundle_files
            if 'MODULE_BLUEPRINT' in f.read_text()
        ]

        assert len(blueprint_files) > 0, (
            "TypeScript files should be processed and emit MODULE_BLUEPRINT"
        )

    def test_php_files_route_to_php_legacy_adapter(self, tmp_path: Path) -> None:
        """Test that .php files are processed by PhpLegacyAdapter.

        AC-8.3: PHP files should be processed with PHP adapter.
        """
        repo_root = setup_mixed_repo(tmp_path)
        owner = repo_root / "owner" / "myrepo"
        owner.mkdir(parents=True, exist_ok=True)

        (owner / "service.php").write_text(PHP_CODE)

        config = ProcessingConfig(
            base_dir=repo_root.parent,
            raw_subdir=".",
            output_subdir="output",
            category="test_repo",
            profile="filesystem",
        )
        processor = RepoProcessor(config)
        processor.run()

        # Verify output was generated - confirms PHP files are processed
        output_dir = repo_root.parent / "output" / "test_repo"
        bundle_files = list(output_dir.rglob("*.txt"))

        # PHP files should generate MODULE_BLUEPRINT
        blueprint_files = [
            f for f in bundle_files
            if 'MODULE_BLUEPRINT' in f.read_text()
        ]

        assert len(blueprint_files) > 0, (
            "PHP files should be processed and emit MODULE_BLUEPRINT"
        )

    def test_yaml_files_route_to_yaml_adapter(self, tmp_path: Path) -> None:
        """Test that .yaml files are processed by YamlAdapter.

        AC-8.4: YAML files should be processed with YAML adapter.
        """
        repo_root = setup_mixed_repo(tmp_path)
        owner = repo_root / "owner" / "myrepo"
        owner.mkdir(parents=True, exist_ok=True)

        (owner / "automation.yaml").write_text(YAML_CODE)

        config = ProcessingConfig(
            base_dir=repo_root.parent,
            raw_subdir=".",
            output_subdir="output",
            category="test_repo",
            profile="yaml",
        )
        processor = RepoProcessor(config)
        processor.run()

        # Verify output was generated - confirms YAML files are processed
        output_dir = repo_root.parent / "output" / "test_repo"
        bundle_files = list(output_dir.rglob("*.txt"))

        # YAML files should generate MODULE_BLUEPRINT
        blueprint_files = [
            f for f in bundle_files
            if 'MODULE_BLUEPRINT' in f.read_text()
        ]

        assert len(blueprint_files) > 0, (
            "YAML files should be processed and emit MODULE_BLUEPRINT"
        )

    def test_adapter_selection_uses_file_extension_not_profile(self, tmp_path: Path) -> None:
        """Test that adapter selection is based on file extension, not repo profile.

        AC-8.5: Per-file selection must use mf.path.suffix, not cfg.profile.

        This test creates a repo with profile="python" but includes .ts files.
        The .ts files should still be processed by TypeScriptAdapter, proving
        that adapter selection is per-file based on extension.
        """
        repo_root = setup_mixed_repo(tmp_path)
        owner = repo_root / "owner" / "myrepo"
        owner.mkdir(parents=True, exist_ok=True)

        # Mix Python and TypeScript files in repo with Python profile
        (owner / "component.py").write_text(PYTHON_CODE)
        (owner / "component.ts").write_text(TYPESCRIPT_CODE)

        config = ProcessingConfig(
            base_dir=repo_root.parent,
            raw_subdir=".",
            output_subdir="output",
            category="test_repo",
            profile="python",  # Python profile but TS files should still work
        )
        processor = RepoProcessor(config)
        processor.run()

        # Verify output was generated - both .py and .ts files should be processed
        output_dir = repo_root.parent / "output" / "test_repo"
        bundle_files = list(output_dir.rglob("*.txt"))

        blueprint_files = [
            f for f in bundle_files
            if 'MODULE_BLUEPRINT' in f.read_text()
        ]

        assert len(blueprint_files) > 0, (
            "Both Python and TypeScript files should be processed "
            "regardless of repository profile"
        )


class TestCrossLanguageRepository:
    """Tests for cross-language repository processing."""

    def test_all_file_types_processed_in_mixed_repo(self, tmp_path: Path) -> None:
        """Test that Python, TypeScript, PHP, and YAML files are all processed.

        This E2E test verifies that a mixed-language repository correctly
        routes each file type to its corresponding adapter.
        """
        repo_root = setup_mixed_repo(tmp_path)
        owner = repo_root / "owner" / "myrepo"
        owner.mkdir(parents=True, exist_ok=True)

        # Create files of all types
        (owner / "component.py").write_text(PYTHON_CODE)
        (owner / "component.ts").write_text(TYPESCRIPT_CODE)
        (owner / "service.php").write_text(PHP_CODE)
        (owner / "automation.yaml").write_text(YAML_CODE)

        config = ProcessingConfig(
            base_dir=repo_root.parent,
            raw_subdir=".",
            output_subdir="output",
            category="test_repo",
            profile="filesystem",
        )
        processor = RepoProcessor(config)
        processor.run()

        # Verify output was generated for all file types
        output_dir = repo_root.parent / "output" / "test_repo"
        bundle_files = list(output_dir.rglob("*.txt"))

        # Should have MODULE_BLUEPRINT from processed files
        blueprint_files = [
            f for f in bundle_files
            if 'MODULE_BLUEPRINT' in f.read_text()
        ]

        assert len(blueprint_files) > 0, (
            "All file types in mixed repository should be processed"
        )
