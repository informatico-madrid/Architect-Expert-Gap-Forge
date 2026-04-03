# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Fragment Test Helpers
====================

Shared test fixtures and helper functions for fragment verification tests.
This module provides common setup functions for creating test repositories
across different languages (Python, TypeScript, PHP, YAML).

Usage:
    from tests.fixtures.fragment_test_helpers import setup_python_test_repo
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional


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

# Python sample code for adapter selection tests
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

# TypeScript sample code
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

# PHP sample code
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

# YAML sample code
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

# Governance file content
CLAUDE_MD = """# Project Guidelines

This project follows specific development guidelines.
"""


# =============================================================================
# Setup Functions
# =============================================================================

def setup_python_test_repo(
    tmp_path: Path,
    files: Dict[str, str],
    add_test_dir: bool = False,
    tests_dir: Optional[Path] = None
) -> Path:
    """Set up a Python test repository with manifest.json.

    Args:
        tmp_path: Temporary test directory
        files: Dict of filename -> content (relative paths)
        add_test_dir: Whether to add a tests/ directory structure
        tests_dir: Optional path for tests directory

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

    # Create tests directory if requested
    if add_test_dir and tests_dir:
        tests_dir.mkdir(parents=True, exist_ok=True)

    return repo_root


def setup_ts_test_repo(tmp_path: Path, files: Dict[str, str]) -> Path:
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


def setup_php_test_repo(tmp_path: Path, files: Dict[str, str]) -> Path:
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


def setup_yaml_test_repo(tmp_path: Path, files: Dict[str, str]) -> Path:
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


def setup_mixed_repo(tmp_path: Path) -> Path:
    """Set up a mixed-language test repository.

    Args:
        tmp_path: Temporary test directory

    Returns:
        repo_root: Path to the repository root
    """
    repo_root = tmp_path / "test_repo"
    repo_root.mkdir()

    # Create owner directory structure
    owner_dir = repo_root / "owner" / "myrepo"
    owner_dir.mkdir(parents=True, exist_ok=True)

    return repo_root


def setup_governance_file(owner_dir: Path, filename: str = "CLAUDE.md") -> None:
    """Add a governance file to the owner directory.

    Args:
        owner_dir: Path to the owner directory
        filename: Name of the governance file (default: CLAUDE.md)
    """
    (owner_dir / filename).write_text(CLAUDE_MD)


# =============================================================================
# Verification Helper Functions
# =============================================================================

def verify_bundle_content(
    bundle_text: str,
    bundle_type: str,
    required_sections: Optional[list] = None
) -> None:
    """Verify that a bundle contains expected content.

    Args:
        bundle_text: The bundle content to verify
        bundle_type: Expected bundle type (e.g., MODULE_BLUEPRINT)
        required_sections: List of required sections to check for

    Raises:
        AssertionError: If required sections are missing
    """
    assert bundle_type in bundle_text, (
        f"Bundle should contain {bundle_type}"
    )

    if required_sections:
        for section in required_sections:
            assert section in bundle_text, (
                f"Bundle should contain {section}"
            )


def verify_blueprint_content(blueprint_text: str, lang: str) -> None:
    """Verify that MODULE_BLUEPRINT contains expected metadata sections.

    Args:
        blueprint_text: The MODULE_BLUEPRINT content to verify
        lang: Language identifier for error messages

    Raises:
        AssertionError: If required sections are missing
    """
    # Check for TYPE header (either [MODULE_BLUEPRINT] or Type: MODULE_BLUEPRINT)
    has_module_blueprint = (
        '[MODULE_BLUEPRINT]' in blueprint_text or
        'Type: MODULE_BLUEPRINT' in blueprint_text
    )
    assert has_module_blueprint, (
        f"{lang}: MODULE_BLUEPRINT should be present in output"
    )

    # Verify [MODULE_MAP] exists
    assert '[MODULE_MAP]' in blueprint_text, (
        f"{lang}: MODULE_BLUEPRINT should contain [MODULE_MAP]"
    )

    # Verify [DEPENDENCIES] exists (from manifest or extraction)
    assert '[DEPENDENCIES]' in blueprint_text, (
        f"{lang}: MODULE_BLUEPRINT should contain [DEPENDENCIES]"
    )

    # Verify MODULE metadata is present
    assert 'MODULE:' in blueprint_text, (
        f"{lang}: MODULE_BLUEPRINT should contain MODULE metadata"
    )

    # Verify ANCHOR metadata is present
    assert 'ANCHOR:' in blueprint_text, (
        f"{lang}: MODULE_BLUEPRINT should contain ANCHOR metadata"
    )
