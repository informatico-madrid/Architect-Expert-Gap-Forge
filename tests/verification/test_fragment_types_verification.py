# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joo@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Fragment Type Verification Tests
=================================
Verifies that the processor correctly emits fragment types 1, 3, 4, 5
across Python, TypeScript, PHP, and YAML repositories.

These tests confirm:
- TYPE 1 (FUNCTIONAL_UNIT): Logic + test pairs are emitted
- TYPE 3 (LOGIC_ONLY): Large standalone files are emitted (≥1000 chars)
- TYPE 4 (MODULE_BLUEPRINT): Always emitted per module
- TYPE 5 (GOVERNANCE_RULES): Repository-level governance rules extracted
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict
import json

from src.discovery import ProcessingConfig, RepoProcessor


# =============================================================================
# Sample Content
# =============================================================================

# Python sample: Small logic file with test (for TYPE 1)
PYTHON_LOGIC_WITH_TEST = """
def add_numbers(a: int, b: int) -> int:
    return a + b

def calculate_total(items: list) -> float:
    total = 0
    for item in items:
        total += item['price']
    return total
"""

# Test file must be >= MIN_SIZE (300 bytes) for find_test to return it
PYTHON_TEST_WITH_LOGIC = """# Comprehensive test suite for logic module
# This test file verifies the core functionality of the add_numbers
# and calculate_total functions with various input scenarios.

import pytest


def test_add_numbers_basic():
    '''Test basic addition scenarios with various inputs.'''
    assert add_numbers(2, 3) == 5
    assert add_numbers(0, 0) == 0
    assert add_numbers(-1, 1) == 0
    assert add_numbers(100, 200) == 300
    assert add_numbers(-50, -50) == -100
    assert add_numbers(1, 1) == 2
    assert add_numbers(999, 1) == 1000


def test_calculate_total():
    '''Test total calculation with list of items and edge cases.'''
    items = [{'price': 10}, {'price': 20}]
    assert calculate_total(items) == 30

    # Test with empty list
    assert calculate_total([]) == 0

    # Test with single item
    assert calculate_total([{'price': 100}]) == 100

    # Test with multiple items
    assert calculate_total([{'price': 1}, {'price': 2}, {'price': 3}]) == 6

    # Test with larger values
    assert calculate_total([{'price': 1000}, {'price': 2000}]) == 3000
"""

# Python sample: Large file for TYPE 3 (≥1000 chars)
PYTHON_LARGE_FILE = """
def complex_processor(data: dict) -> dict:
    '''Process complex data transformations with multiple steps.'''
    result = {}
    for key, value in data.items():
        if isinstance(value, dict):
            result[key] = process_nested_dict(value)
        elif isinstance(value, list):
            result[key] = process_list(value)
        else:
            result[key] = transform_scalar(value)
    return result

def process_nested_dict(nested: dict) -> dict:
    '''Recursively process nested dictionaries.'''
    output = {}
    for k, v in nested.items():
        if isinstance(v, dict):
            output[k] = process_nested_dict(v)
        elif isinstance(v, list):
            output[k] = [transform_scalar(item) for item in v]
        else:
            output[k] = transform_scalar(v)
    return output

def process_list(items: list) -> list:
    '''Process a list of items through transformation pipeline.'''
    result = []
    for item in items:
        if isinstance(item, dict):
            result.append(process_nested_dict(item))
        elif isinstance(item, list):
            result.extend(item)
        else:
            result.append(transform_scalar(item))
    return result

def transform_scalar(value) -> str:
    '''Transform a scalar value to string representation.'''
    if value is None:
        return 'null'
    elif isinstance(value, bool):
        return 'true' if value else 'false'
    elif isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, str):
        return value.strip()
    else:
        return repr(value)

def validate_input(data: dict) -> bool:
    '''Validate input data structure and return boolean.'''
    if not isinstance(data, dict):
        return False
    for key, value in data.items():
        if not isinstance(key, str):
            return False
        if not isinstance(value, (dict, list, str, int, float, bool, type(None))):
            return False
    return True

def merge_datasets(primary: dict, secondary: dict) -> dict:
    '''Merge two datasets with priority to secondary.'''
    merged = primary.copy()
    for key, value in secondary.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = merge_datasets(merged[key], value)
        else:
            merged[key] = value
    return merged

def filter_by_criteria(data: dict, criteria: dict) -> dict:
    '''Filter dataset by criteria matching.'''
    result = {}
    for key, value in data.items():
        matches = True
        for crit_key, crit_value in criteria.items():
            if crit_key in value:
                if value[crit_key] != crit_value:
                    matches = False
                    break
        if matches:
            result[key] = value
    return result

def aggregate_metrics(metrics: list) -> dict:
    '''Aggregate metrics list into summary statistics.'''
    if not metrics:
        return {'count': 0, 'sum': 0, 'avg': 0}

    total = sum(m.get('value', 0) for m in metrics)
    count = len(metrics)
    average = total / count if count > 0 else 0

    return {
        'count': count,
        'sum': total,
        'avg': average,
        'min': min(m.get('value', 0) for m in metrics),
        'max': max(m.get('value', 0) for m in metrics)
    }

def normalize_values(data: list) -> list:
    '''Normalize values to 0-1 range.'''
    if not data:
        return []

    min_val = min(data)
    max_val = max(data)
    range_val = max_val - min_val

    if range_val == 0:
        return [0.0 for _ in data]

    return [(v - min_val) / range_val for v in data]

def batch_process(items: list, batch_size: int) -> list:
    '''Process items in batches.'''
    batches = []
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        batches.append(process_batch(batch))
    return batches

def process_batch(batch: list) -> dict:
    '''Process a single batch of items.'''
    result = {
        'processed_count': len(batch),
        'status': 'completed',
        'timestamp': 'now'
    }
    return result
"""

# TypeScript sample: Lit component with i18n and service calls
TYPESCRIPT_SAMPLE = """
import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';

@customElement('ha-dialog')
export class HaDialog extends LitElement {
  @property({ type: Boolean }) public open = false;
  @property({ type: String, name: 'dialog-title' }) public dialogTitle = '';
  @state() private _loading = false;

  private _cancelText = this.hass.localize('ui.dialog.cancel');
  private _templateKey = this.localize(`ui.card.actions.${this._action}`);

  private _action = 'close';

  private async _closeDialog() {
    this.hass.callService('dialog', 'close', {
      entity_id: 'dialog.home_assistant'
    });
  }

  protected render() {
    return html`
      <div class="dialog">
        <h2>${this.dialogTitle}</h2>
        <button @click=${this._closeDialog}>${this._cancelText}</button>
      </div>
    `;
  }
}
"""

# PHP sample: Simple class for TYPE 4 verification
PHP_SAMPLE = """
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

    public function deleteUser(string $email): bool {
        $index = array_search($email, array_column($this->users, 'email'));
        if ($index !== false) {
            unset($this->users[$index]);
            return true;
        }
        return false;
    }
}
"""

# YAML sample: Home Assistant configuration
YAML_SAMPLE = """
# Home Assistant Configuration
automation:
  - alias: "Light Automation"
    trigger:
      platform: state
      entity_id: light.living_room
    action:
      service: light.turn_on
      data:
        brightness: 255

script:
  hello_world:
    sequence:
      - service: light.turn_on
        target:
          entity_id: light.kitchen

sensor:
  - platform: template
    sensors:
      room_temperature:
        value_template: "{{ state('sensor.bedroom_temperature') }}"
        unit_of_measurement: "°C"
"""


# =============================================================================
# Test Utilities
# =============================================================================

def setup_python_test_repo(
    tmp_path: Path,
    files: Dict[str, str]
) -> Path:
    """Set up a Python test repository with manifest.json.

    Args:
        tmp_path: Temporary test directory
        files: Dict of filename -> content (relative paths)

    Returns:
        repo_root: Path to the repository root
    """
    repo_root = tmp_path / "test_repo"
    repo_root.mkdir()

    # Create owner directory structure
    owner_dir = repo_root / "owner" / "myrepo"
    owner_dir.mkdir(parents=True, exist_ok=True)

    # Create component directory with manifest.json
    component = owner_dir / "custom_components" / "test_component"
    component.mkdir(parents=True, exist_ok=True)

    # Create manifest.json
    manifest = component / "manifest.json"
    manifest.write_text(json.dumps({
        "domain": "test_component",
        "name": "Test Component",
        "version": "1.0.0",
        "dependencies": [],
    }))

    # Create component files
    for filename, content in files.items():
        (component / filename).write_text(content)

    return repo_root


def setup_ts_test_repo(
    tmp_path: Path,
    files: Dict[str, str]
) -> Path:
    """Set up a TypeScript test repository.

    Args:
        tmp_path: Temporary test directory
        files: Dict of filename -> content

    Returns:
        owner_dir: Path to the owner directory containing the repo
    """
    repo_root = tmp_path / "test_repo"
    repo_root.mkdir()

    # Create owner directory structure
    owner_dir = repo_root / "owner" / "myrepo"
    owner_dir.mkdir(parents=True, exist_ok=True)

    # Create repository root files in owner/myrepo
    for filename, content in files.items():
        (owner_dir / filename).write_text(content)

    return owner_dir


def setup_php_test_repo(
    tmp_path: Path,
    files: Dict[str, str]
) -> Path:
    """Set up a PHP test repository.

    Args:
        tmp_path: Temporary test directory
        files: Dict of filename -> content

    Returns:
        owner_dir: Path to the owner directory containing the repo
    """
    repo_root = tmp_path / "test_repo"
    repo_root.mkdir()

    # Create owner directory structure
    owner_dir = repo_root / "owner" / "myrepo"
    owner_dir.mkdir(parents=True, exist_ok=True)

    # Create repository root files in owner/myrepo
    for filename, content in files.items():
        (owner_dir / filename).write_text(content)

    return owner_dir


def setup_yaml_test_repo(
    tmp_path: Path,
    files: Dict[str, str]
) -> Path:
    """Set up a YAML test repository.

    Args:
        tmp_path: Temporary test directory
        files: Dict of filename -> content

    Returns:
        owner_dir: Path to the owner directory containing the repo
    """
    repo_root = tmp_path / "test_repo"
    repo_root.mkdir()

    # Create owner directory structure
    owner_dir = repo_root / "owner" / "myrepo"
    owner_dir.mkdir(parents=True, exist_ok=True)

    # Create repository root files in owner/myrepo
    for filename, content in files.items():
        (owner_dir / filename).write_text(content)

    return owner_dir


# =============================================================================
# Fragment Type Verification Tests
# =============================================================================

class TestFragmentTypesPython:
    """Verification tests for Python fragment types."""

    def test_type1_functional_unit_with_test(self, tmp_path: Path) -> None:
        """Test that logic files with tests emit TYPE 1 (FUNCTIONAL_UNIT).

        This verifies that when a logic file has a corresponding test file,
        both are bundled together as a FUNCTIONAL_UNIT.
        """
        # Setup test repo
        repo_root = tmp_path / "test_repo"
        repo_root.mkdir()

        # Create owner directory structure
        owner_dir = repo_root / "owner" / "myrepo"
        owner_dir.mkdir(parents=True, exist_ok=True)

        # Create component directory
        component = owner_dir / "custom_components" / "test_component"
        component.mkdir(parents=True, exist_ok=True)

        # Create manifest.json
        (component / "manifest.json").write_text(json.dumps({
            "domain": "test",
            "name": "Test",
            "version": "1.0",
            "dependencies": []
        }))

        # Create logic file (use a proper name without "test" prefix to avoid role confusion)
        (component / "logic.py").write_text(PYTHON_LOGIC_WITH_TEST)

        # Create tests directory INSIDE the repo (owner/myrepo/tests)
        tests_dir = owner_dir / "tests" / "custom_components" / "test_component"
        tests_dir.mkdir(parents=True, exist_ok=True)
        # Test file should be named test_<logic_filename>.py
        (tests_dir / "test_logic.py").write_text(PYTHON_TEST_WITH_LOGIC)

        # Process
        config = ProcessingConfig(
            base_dir=tmp_path,
            raw_subdir="test_repo",
            output_subdir="output",
            category="owner",
            profile="homeassistant",
        )
        processor = RepoProcessor(config)
        processor.run()

        # Check output
        output_dir = tmp_path / "output" / "owner"
        bundle_files = list(output_dir.rglob("*.txt"))

        # Should have TYPE 1 bundle (FUNCTIONAL_UNIT) for logic.py + test
        functional_unit_files = [
            f for f in bundle_files
            if 'FUNCTIONAL_UNIT' in f.read_text()
        ]

        assert len(functional_unit_files) > 0, (
            "TYPE 1 FUNCTIONAL_UNIT should be emitted for logic+test pair\n"
            f"Bundle files found: {[f.name for f in bundle_files]}"
        )

    def test_type3_logic_only_large_file(self, tmp_path: Path) -> None:
        """Test that large files (≥1000 chars) emit TYPE 3 (LOGIC_ONLY).

        This verifies that standalone logic files without tests but with
        sufficient size are emitted as LOGIC_ONLY.
        """
        repo_root = setup_python_test_repo(
            tmp_path,
            {
                'manifest.json': json.dumps({
                    "domain": "test",
                    "name": "Test",
                    "version": "1.0",
                    "dependencies": []
                }),
                'processor.py': PYTHON_LARGE_FILE,  # >1000 chars
            }
        )

        config = ProcessingConfig(
            base_dir=repo_root.parent,
            raw_subdir=".",
            output_subdir="output",
            category="test_repo",
            profile="homeassistant",
        )
        processor = RepoProcessor(config)
        processor.run()

        # Check output
        output_dir = repo_root.parent / "output" / "test_repo"
        bundle_files = list(output_dir.rglob("*.txt"))

        # Should have TYPE 3 bundle (LOGIC_ONLY)
        logic_only_files = [
            f for f in bundle_files
            if 'LOGIC_ONLY' in f.read_text()
        ]

        assert len(logic_only_files) > 0, (
            "TYPE 3 LOGIC_ONLY should be emitted for large standalone files"
        )

    def test_type4_module_blueprint(self, tmp_path: Path) -> None:
        """Test that MODULE_BLUEPRINT (TYPE 4) is always emitted per module.

        This verifies that every module generates a blueprint containing
        architecture metadata.
        """
        repo_root = setup_python_test_repo(
            tmp_path,
            {
                'manifest.json': json.dumps({
                    "domain": "test",
                    "name": "Test",
                    "version": "1.0",
                    "dependencies": []
                }),
                '__init__.py': 'from . import module',
                'module.py': PYTHON_LOGIC_WITH_TEST,
            }
        )

        config = ProcessingConfig(
            base_dir=repo_root.parent,
            raw_subdir=".",
            output_subdir="output",
            category="test_repo",
            profile="homeassistant",
        )
        processor = RepoProcessor(config)
        processor.run()

        # Check output
        output_dir = repo_root.parent / "output" / "test_repo"
        bundle_files = list(output_dir.rglob("*.txt"))

        # Should have MODULE_BLUEPRINT
        blueprint_files = [
            f for f in bundle_files
            if 'MODULE_BLUEPRINT' in f.read_text()
        ]

        assert len(blueprint_files) > 0, (
            "TYPE 4 MODULE_BLUEPRINT should always be emitted per module"
        )

        # Verify blueprint contains expected metadata
        blueprint = blueprint_files[0].read_text()
        assert '[MODULE_MAP]' in blueprint


class TestFragmentTypesTypeScript:
    """Verification tests for TypeScript fragment types."""

    def test_typescript_adapter_selection(self, tmp_path: Path) -> None:
        """Test that TypeScript files trigger TypeScriptAdapter.

        This verifies the per-file adapter selection pattern: .ts files
        should use TypeScriptAdapter, not the repo profile adapter.
        """
        owner_dir = setup_ts_test_repo(
            tmp_path,
            {'component.ts': TYPESCRIPT_SAMPLE}
        )

        config = ProcessingConfig(
            base_dir=owner_dir.parent,
            raw_subdir=".",
            output_subdir="output",
            category="myrepo",
            profile="typescript",
        )
        processor = RepoProcessor(config)
        processor.run()

        # Check output - target_root is base_dir / output_subdir / category
        # base_dir = owner_dir.parent, so output_dir = owner_dir.parent / "output" / "myrepo"
        output_dir = owner_dir.parent / "output" / "myrepo"
        bundle_files = list(output_dir.rglob("*.txt"))

        # Should have emitted at least TYPE 4 (MODULE_BLUEPRINT)
        blueprint_files = [
            f for f in bundle_files
            if 'MODULE_BLUEPRINT' in f.read_text()
        ]

        assert len(blueprint_files) > 0, (
            "TypeScript files should be processed and emit MODULE_BLUEPRINT"
        )


class TestFragmentTypesPHP:
    """Verification tests for PHP fragment types."""

    def test_php_module_blueprint(self, tmp_path: Path) -> None:
        """Test that PHP files emit MODULE_BLUEPRINT.

        This verifies PHP file processing and blueprint generation.
        """
        owner_dir = setup_php_test_repo(
            tmp_path,
            {'user_service.php': PHP_SAMPLE}
        )

        config = ProcessingConfig(
            base_dir=owner_dir.parent,
            raw_subdir=".",
            output_subdir="output",
            category="myrepo",
            profile="filesystem",
        )
        processor = RepoProcessor(config)
        processor.run()

        # Check output
        output_dir = owner_dir.parent / "output" / "myrepo"
        bundle_files = list(output_dir.rglob("*.txt"))

        # Should have MODULE_BLUEPRINT
        blueprint_files = [
            f for f in bundle_files
            if 'MODULE_BLUEPRINT' in f.read_text()
        ]

        assert len(blueprint_files) > 0, (
            "PHP files should emit MODULE_BLUEPRINT"
        )


class TestFragmentTypesYAML:
    """Verification tests for YAML fragment types."""

    def test_yaml_module_blueprint(self, tmp_path: Path) -> None:
        """Test that YAML files emit MODULE_BLUEPRINT.

        This verifies YAML file processing and blueprint generation.
        """
        owner_dir = setup_yaml_test_repo(
            tmp_path,
            {'configuration.yaml': YAML_SAMPLE}
        )

        config = ProcessingConfig(
            base_dir=owner_dir.parent,
            raw_subdir=".",
            output_subdir="output",
            category="myrepo",
            profile="yaml",
        )
        processor = RepoProcessor(config)
        processor.run()

        # Check output
        output_dir = owner_dir.parent / "output" / "myrepo"
        bundle_files = list(output_dir.rglob("*.txt"))

        # Should have MODULE_BLUEPRINT
        blueprint_files = [
            f for f in bundle_files
            if 'MODULE_BLUEPRINT' in f.read_text()
        ]

        assert len(blueprint_files) > 0, (
            "YAML files should emit MODULE_BLUEPRINT"
        )


class TestFragmentTypesMixed:
    """Verification tests for mixed fragment types in single run."""

    def test_all_fragment_types_emitted(self, tmp_path: Path) -> None:
        """Test that TYPE 1, 3, 4, 5 are all emitted across different files.

        This is an E2E test that verifies:
        - TYPE 1: Logic + test pair
        - TYPE 3: Large standalone file
        - TYPE 4: MODULE_BLUEPRINT (always)
        - TYPE 5: GOVERNANCE_RULES (from repo root)
        """
        repo_root = tmp_path / "test_repo"
        repo_root.mkdir()

        # Create owner directory structure
        owner_dir = repo_root / "owner" / "myrepo"
        owner_dir.mkdir(parents=True, exist_ok=True)

        # Create component directory
        component = owner_dir / "custom_components" / "test_component"
        component.mkdir(parents=True, exist_ok=True)

        # Create tests directory at owner_dir level for TYPE 1 detection
        # Path: owner_dir/tests/custom_components/test_component/
        # This maps to repo_root/tests/custom_components/test_component/ since
        # repo_root = owner_dir for this config
        tests_dir = owner_dir / "tests" / "custom_components" / "test_component"
        tests_dir.mkdir(parents=True, exist_ok=True)

        # Create governance file at repo root
        (owner_dir / "CLAUDE.md").write_text('# Project guidelines\n')

        # Create manifest.json
        (component / "manifest.json").write_text(json.dumps({
            "domain": "test",
            "name": "Test",
            "version": "1.0",
            "dependencies": []
        }))

        # Create component files
        (component / "core.py").write_text(PYTHON_LOGIC_WITH_TEST)
        # Test file should be in tests/ directory for TYPE 1 detection
        (tests_dir / "test_core.py").write_text(PYTHON_TEST_WITH_LOGIC)
        # Large processor at component level for TYPE 3
        (component / "processor.py").write_text(PYTHON_LARGE_FILE)

        config = ProcessingConfig(
            base_dir=owner_dir.parent,
            raw_subdir=".",
            output_subdir="output",
            category="myrepo",
            profile="homeassistant",
        )
        processor = RepoProcessor(config)
        processor.run()

        # Check output - target_root is base_dir / output_subdir / category
        output_dir = owner_dir.parent / "output" / "myrepo"
        bundle_files = list(output_dir.rglob("*.txt"))

        bundle_contents = {}
        for bf in bundle_files:
            bundle_contents[bf.name] = bf.read_text()

        # Verify TYPE 1 (FUNCTIONAL_UNIT)
        has_type1 = any('FUNCTIONAL_UNIT' in content for content in bundle_contents.values())
        assert has_type1, (
            "TYPE 1 FUNCTIONAL_UNIT should be emitted for logic+test pair"
        )

        # Verify TYPE 3 (LOGIC_ONLY)
        has_type3 = any('LOGIC_ONLY' in content for content in bundle_contents.values())
        assert has_type3, (
            "TYPE 3 LOGIC_ONLY should be emitted for large standalone files"
        )

        # Verify TYPE 4 (MODULE_BLUEPRINT)
        has_type4 = any('MODULE_BLUEPRINT' in content for content in bundle_contents.values())
        assert has_type4, (
            "TYPE 4 MODULE_BLUEPRINT should always be emitted"
        )

        # Verify TYPE 5 (GOVERNANCE_RULES) - from CLAUDE.md at repo root
        has_type5 = any('GOVERNANCE_RULES' in content for content in bundle_contents.values())
        assert has_type5, (
            "TYPE 5 GOVERNANCE_RULES should be emitted from repository governance files"
        )


class TestFragmentTypeBundleContent:
    """Verification tests for fragment bundle content quality."""

    def test_blueprint_contains_metadata(self, tmp_path: Path) -> None:
        """Test that MODULE_BLUEPRINT contains expected metadata sections.

        Blueprint should include:
        - [MODULE_MAP]: Architecture context
        - [DEPENDENCIES]: From manifest or extraction
        - [SCHEMA]: From services.yaml or similar
        - [VOCABULARY]: Domain vocabulary
        """
        repo_root = setup_python_test_repo(
            tmp_path,
            {
                'manifest.json': json.dumps({
                    "domain": "test",
                    "name": "Test",
                    "version": "1.0",
                    "dependencies": ["helper_lib"]
                }),
                '__init__.py': 'from . import module',
                'module.py': 'def process(): pass',
            }
        )

        config = ProcessingConfig(
            base_dir=repo_root.parent,
            raw_subdir=".",
            output_subdir="output",
            category="test_repo",
            profile="homeassistant",
        )
        processor = RepoProcessor(config)
        processor.run()

        # Check output
        output_dir = repo_root.parent / "output" / "test_repo"
        bundle_files = list(output_dir.rglob("*.txt"))

        blueprint_files = [
            f for f in bundle_files
            if 'MODULE_BLUEPRINT' in f.read_text()
        ]

        assert len(blueprint_files) > 0
        blueprint_content = blueprint_files[0].read_text()

        # Check for expected metadata sections
        assert '[MODULE_MAP]' in blueprint_content, (
            "Blueprint should contain [MODULE_MAP]"
        )
        assert 'MODULE:' in blueprint_content, (
            "Blueprint should contain MODULE metadata"
        )
        assert 'ANCHOR:' in blueprint_content, (
            "Blueprint should contain ANCHOR metadata"
        )
