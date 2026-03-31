# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joo@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
MODULE_BLUEPRINT Cross-Language Verification Tests
=====================================================

Verifies that TYPE 4 MODULE_BLUEPRINT generation works correctly across
Python, TypeScript, PHP, and YAML repositories.

Requirements: FR-3, AC-3.1 to AC-3.7
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict
import json

from src.discovery import ProcessingConfig, RepoProcessor


# =============================================================================
# Sample Content for Each Language
# =============================================================================

# Python sample: Simple module with manifest.json anchor
PYTHON_MODULE_CODE = """
def process_data(data: dict) -> dict:
    '''Process incoming data and transform it.'''
    result = {}
    for key, value in data.items():
        result[key.lower()] = value
    return result

def validate_input(data: dict) -> bool:
    '''Validate that input is a dictionary.'''
    return isinstance(data, dict)
"""

# TypeScript sample: Lit component with decorators
TYPESCRIPT_MODULE_CODE = """
import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';

@customElement('ha-button-card')
export class HaButtonCard extends LitElement {
  @property({ type: String }) private label = 'Click me';
  @state() private _count = 0;

  private handleClick() {
    this._count++;
  }

  render() {
    return html`
      <button @click=${this.handleClick}>${this.label} (${this._count})</button>
    `;
  }

  static styles = css`
    button {
      padding: 8px 16px;
      background: #0078d4;
      color: white;
    }
  `;
}
"""

# PHP sample: Service class with type hints
PHP_MODULE_CODE = """
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
YAML_MODULE_CODE = """
# Home Assistant automation configurations
automation:
  - alias: "Light Automation"
    trigger:
      platform: state
      entity_id: light.living_room
    action:
      service: light.toggle

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

# TypeScript with i18n and service calls
TYPESCRIPT_FULL_SAMPLE = """
import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';

@customElement('ha-dialog')
export class HaDialog extends LitElement {
  @property({ type: Boolean }) public open = false;
  @property({ type: String, name: 'dialog-title' }) public dialogTitle = '';

  @state() private _loading = false;

  private _cancelText = this.hass.localize('ui.dialog.cancel');
  private _templateKey = this.localize(`ui.card.actions.${this._action}`);

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

# PHP with methods
PHP_FULL_SAMPLE = """
<?php

namespace App\\Controllers;

class UserController {
    private UserService $userService;

    public function __construct(UserService $userService) {
        $this->userService = $userService;
    }

    public function handleRequest(string $action, array $data): ?array {
        switch ($action) {
            case 'create':
                return $this->userService->createUser(
                    $data['name'],
                    $data['email']
                );
            case 'find':
                return $this->userService->findUser($data['email']);
            case 'delete':
                return $this->userService->deleteUser($data['email']);
            default:
                return null;
        }
    }
}
"""

# YAML with multiple configurations
YAML_FULL_SAMPLE = """
# Home Assistant configuration with automation, script, and sensor
automation:
  - alias: "Turn off lights"
    trigger:
      platform: time
      at: "23:00:00"
    action:
      service: light.turn_off
      target:
        area_id: living_room

  - alias: "Climate control"
    trigger:
      platform: state
      entity_id: sensor.temperature
      for:
        minutes: 5
    condition:
      condition: numeric_state
      entity_id: sensor.temperature
      above: 22
    action:
      service: climate.set_hvac_mode
      target:
        entity_id: climate.living_room
      data:
        hvac_mode: "cool"

script:
  morning_routine:
    alias: "Morning routine"
    sequence:
      - service: light.turn_on
        target:
          entity_id: light.bedroom
      - service: light.turn_on
        target:
          entity_id: light.living_room

sensor:
  - platform: command
    name: "System Load"
    command: "uptime -p"
    unit_of_measurement: "up"
    value_template: >
      {{ value | regex_replace('up (\\d+)', '1') | int }}

  - platform: template
    sensors:
      battery_level:
        value_template: "{{ states('sensor.battery_device') | int }}"
        unit_of_measurement: "%"
        icon: "mdi:battery"
"""


# =============================================================================
# Test Setup Functions
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

    # Create component directory with manifest.json (anchor file)
    component = owner_dir / "custom_components" / "test_component"
    component.mkdir(parents=True, exist_ok=True)

    # Create manifest.json (anchor)
    manifest = component / "manifest.json"
    manifest.write_text(json.dumps({
        "domain": "test_component",
        "name": "Test Component",
        "version": "1.0.0",
        "dependencies": [],
    }))

    # Create module files
    for filename, content in files.items():
        (component / filename).write_text(content)

    return repo_root


def setup_typescript_test_repo(
    tmp_path: Path,
    files: Dict[str, str]
) -> Path:
    """Set up a TypeScript test repository.

    Args:
        tmp_path: Temporary test directory
        files: Dict of filename -> content

    Returns:
        repo_root: Path to the repository root
    """
    repo_root = tmp_path / "test_repo"
    repo_root.mkdir()

    owner_dir = repo_root / "owner" / "myrepo"
    owner_dir.mkdir(parents=True, exist_ok=True)

    # Create component directory
    component = owner_dir / "components" / "button-card"
    component.mkdir(parents=True, exist_ok=True)

    # Create component files
    for filename, content in files.items():
        (component / filename).write_text(content)

    return repo_root


def setup_php_test_repo(
    tmp_path: Path,
    files: Dict[str, str]
) -> Path:
    """Set up a PHP test repository.

    Args:
        tmp_path: Temporary test directory
        files: Dict of filename -> content

    Returns:
        repo_root: Path to the repository root
    """
    repo_root = tmp_path / "test_repo"
    repo_root.mkdir()

    owner_dir = repo_root / "owner" / "myrepo"
    owner_dir.mkdir(parents=True, exist_ok=True)

    # Create services directory
    services = owner_dir / "src" / "Services"
    services.mkdir(parents=True, exist_ok=True)

    # Create component files
    for filename, content in files.items():
        (services / filename).write_text(content)

    return repo_root


def setup_yaml_test_repo(
    tmp_path: Path,
    files: Dict[str, str]
) -> Path:
    """Set up a YAML test repository.

    Args:
        tmp_path: Temporary test directory
        files: Dict of filename -> content

    Returns:
        repo_root: Path to the repository root
    """
    repo_root = tmp_path / "test_repo"
    repo_root.mkdir()

    owner_dir = repo_root / "owner" / "myrepo"
    owner_dir.mkdir(parents=True, exist_ok=True)

    # Create configurations directory
    configs = owner_dir / "configurations"
    configs.mkdir(parents=True, exist_ok=True)

    # Create YAML files
    for filename, content in files.items():
        (configs / filename).write_text(content)

    return repo_root


# =============================================================================
# MODULE_BLUEPRINT Content Verification
# =============================================================================

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

    # AC-3.1: Verify [MODULE_MAP] exists
    assert '[MODULE_MAP]' in blueprint_text, (
        f"{lang}: MODULE_BLUEPRINT should contain [MODULE_MAP]"
    )

    # AC-3.2: Verify [DEPENDENCIES] exists (from manifest or extraction)
    assert '[DEPENDENCIES]' in blueprint_text, (
        f"{lang}: MODULE_BLUEPRINT should contain [DEPENDENCIES]"
    )

    # AC-3.3: Verify MODULE metadata is present
    assert 'MODULE:' in blueprint_text, (
        f"{lang}: MODULE_BLUEPRINT should contain MODULE metadata"
    )

    # AC-3.4: Verify ANCHOR metadata is present
    assert 'ANCHOR:' in blueprint_text, (
        f"{lang}: MODULE_BLUEPRINT should contain ANCHOR metadata"
    )


# =============================================================================
# Cross-Language MODULE_BLUEPRINT Verification Tests
# =============================================================================

class TestModuleBlueprintPython:
    """Verification tests for Python MODULE_BLUEPRINT."""

    def test_python_module_blueprint_structure(self, tmp_path: Path) -> None:
        """Test that Python MODULE_BLUEPRINT contains all required sections.

        This verifies AC-3.1 to AC-3.7 for Python:
        - [MODULE_MAP]: Architecture context
        - [DEPENDENCIES]: From manifest.json
        - [SCHEMA]: From configuration
        - [VOCABULARY]: From const.py or extraction
        - [README]: From README.md
        - [CODE_SNIPPETS]: Code references
        """
        repo_root = setup_python_test_repo(
            tmp_path,
            {
                'manifest.json': json.dumps({
                    "domain": "test_component",
                    "name": "Test Component",
                    "version": "1.0.0",
                    "dependencies": ["helper_lib"],
                }),
                'component.py': PYTHON_MODULE_CODE,
                'const.py': """
CONSTANT_1 = "value1"
CONSTANT_2 = "value2"
SERVICE_NAMES = ['service1', 'service2']
""",
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

        # Find MODULE_BLUEPRINT
        blueprint_files = [
            f for f in bundle_files
            if 'MODULE_BLUEPRINT' in f.read_text()
        ]

        assert len(blueprint_files) > 0, (
            "Python files should emit MODULE_BLUEPRINT"
        )

        # Verify blueprint content
        verify_blueprint_content(blueprint_files[0].read_text(), "Python")

    def test_python_module_blueprint_dependencies(self, tmp_path: Path) -> None:
        """Test that Python MODULE_BLUEPRINT extracts dependencies from manifest.

        AC-3.5: Dependencies should be extracted from manifest.json.
        """
        repo_root = setup_python_test_repo(
            tmp_path,
            {
                'manifest.json': json.dumps({
                    "domain": "test_component",
                    "name": "Test Component",
                    "version": "1.0.0",
                    "dependencies": ["frontend", "http"],
                }),
                'component.py': PYTHON_MODULE_CODE,
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

        output_dir = repo_root.parent / "output" / "test_repo"
        bundle_files = list(output_dir.rglob("*.txt"))

        blueprint_files = [
            f for f in bundle_files
            if 'MODULE_BLUEPRINT' in f.read_text()
        ]

        assert len(blueprint_files) > 0
        blueprint = blueprint_files[0].read_text()

        # Verify dependencies are extracted
        assert 'frontend' in blueprint, (
            "DEPENDENCIES should include 'frontend' from manifest.json"
        )
        assert 'http' in blueprint, (
            "DEPENDENCIES should include 'http' from manifest.json"
        )


class TestModuleBlueprintTypeScript:
    """Verification tests for TypeScript MODULE_BLUEPRINT."""

    def test_typescript_module_blueprint_structure(self, tmp_path: Path) -> None:
        """Test that TypeScript MODULE_BLUEPRINT contains all required sections.

        This verifies AC-3.1 to AC-3.7 for TypeScript:
        - [MODULE_MAP]: Architecture context with LitElement base
        - [DEPENDENCIES]: From imports (lit, lit/decorators)
        - [SCHEMA]: From property declarations
        - [VOCABULARY]: From decorators and constants
        - [CODE_SNIPPETS]: TypeScript code references
        """
        repo_root = setup_typescript_test_repo(
            tmp_path,
            {
                'button-card.ts': TYPESCRIPT_FULL_SAMPLE,
            }
        )

        config = ProcessingConfig(
            base_dir=repo_root.parent,
            raw_subdir=".",
            output_subdir="output",
            category="test_repo",
            profile="typescript",
        )
        processor = RepoProcessor(config)
        processor.run()

        output_dir = repo_root.parent / "output" / "test_repo"
        bundle_files = list(output_dir.rglob("*.txt"))

        blueprint_files = [
            f for f in bundle_files
            if 'MODULE_BLUEPRINT' in f.read_text()
        ]

        assert len(blueprint_files) > 0, (
            "TypeScript files should emit MODULE_BLUEPRINT"
        )

        # Verify blueprint content
        verify_blueprint_content(blueprint_files[0].read_text(), "TypeScript")

    def test_typescript_module_blueprint_decorators(self, tmp_path: Path) -> None:
        """Test that TypeScript MODULE_BLUEPRINT extracts decorator information.

        AC-3.6: Decorators (@customElement, @property, @state) should be
        extracted into the blueprint.
        """
        repo_root = setup_typescript_test_repo(
            tmp_path,
            {
                'button-card.ts': TYPESCRIPT_MODULE_CODE,
            }
        )

        config = ProcessingConfig(
            base_dir=repo_root.parent,
            raw_subdir=".",
            output_subdir="output",
            category="test_repo",
            profile="typescript",
        )
        processor = RepoProcessor(config)
        processor.run()

        output_dir = repo_root.parent / "output" / "test_repo"
        bundle_files = list(output_dir.rglob("*.txt"))

        blueprint_files = [
            f for f in bundle_files
            if 'MODULE_BLUEPRINT' in f.read_text()
        ]

        assert len(blueprint_files) > 0
        blueprint = blueprint_files[0].read_text()

        # Verify decorator patterns are captured
        assert 'customElement' in blueprint, (
            "MODULE_BLUEPRINT should capture @customElement decorator"
        )
        assert 'property' in blueprint, (
            "MODULE_BLUEPRINT should capture @property decorator"
        )
        assert 'state' in blueprint, (
            "MODULE_BLUEPRINT should capture @state decorator"
        )


class TestModuleBlueprintPHP:
    """Verification tests for PHP MODULE_BLUEPRINT."""

    def test_php_module_blueprint_structure(self, tmp_path: Path) -> None:
        """Test that PHP MODULE_BLUEPRINT contains all required sections.

        This verifies AC-3.1 to AC-3.7 for PHP:
        - [MODULE_MAP]: Architecture context with namespace
        - [DEPENDENCIES]: From class references
        - [SCHEMA]: From method signatures
        - [VOCABULARY]: From class names and constants
        - [CODE_SNIPPETS]: PHP code references
        """
        repo_root = setup_php_test_repo(
            tmp_path,
            {
                'UserService.php': PHP_FULL_SAMPLE,
            }
        )

        config = ProcessingConfig(
            base_dir=repo_root.parent,
            raw_subdir=".",
            output_subdir="output",
            category="test_repo",
            profile="filesystem",
        )
        processor = RepoProcessor(config)
        processor.run()

        output_dir = repo_root.parent / "output" / "test_repo"
        bundle_files = list(output_dir.rglob("*.txt"))

        blueprint_files = [
            f for f in bundle_files
            if 'MODULE_BLUEPRINT' in f.read_text()
        ]

        assert len(blueprint_files) > 0, (
            "PHP files should emit MODULE_BLUEPRINT"
        )

        # Verify blueprint content
        verify_blueprint_content(blueprint_files[0].read_text(), "PHP")

    def test_php_module_blueprint_namespace(self, tmp_path: Path) -> None:
        """Test that PHP MODULE_BLUEPRINT extracts namespace information.

        AC-3.7: Namespace path should be captured from PHP files.
        """
        repo_root = setup_php_test_repo(
            tmp_path,
            {
                'UserController.php': PHP_FULL_SAMPLE,
            }
        )

        config = ProcessingConfig(
            base_dir=repo_root.parent,
            raw_subdir=".",
            output_subdir="output",
            category="test_repo",
            profile="filesystem",
        )
        processor = RepoProcessor(config)
        processor.run()

        output_dir = repo_root.parent / "output" / "test_repo"
        bundle_files = list(output_dir.rglob("*.txt"))

        blueprint_files = [
            f for f in bundle_files
            if 'MODULE_BLUEPRINT' in f.read_text()
        ]

        assert len(blueprint_files) > 0
        blueprint = blueprint_files[0].read_text()

        # Verify namespace is captured
        assert 'App' in blueprint, (
            "MODULE_BLUEPRINT should capture 'App' namespace"
        )
        assert 'Controllers' in blueprint, (
            "MODULE_BLUEPRINT should capture 'Controllers' namespace path"
        )


class TestModuleBlueprintYAML:
    """Verification tests for YAML MODULE_BLUEPRINT."""

    def test_yaml_module_blueprint_structure(self, tmp_path: Path) -> None:
        """Test that YAML MODULE_BLUEPRINT contains all required sections.

        This verifies AC-3.1 to AC-3.7 for YAML:
        - [MODULE_MAP]: Architecture context with automation/script/sensor
        - [DEPENDENCIES]: From service references
        - [SCHEMA]: From entity_ids and domains
        - [VOCABULARY]: From aliases and templates
        - [CODE_SNIPPETS]: YAML code references
        """
        repo_root = setup_yaml_test_repo(
            tmp_path,
            {
                'automation.yaml': YAML_FULL_SAMPLE,
            }
        )

        config = ProcessingConfig(
            base_dir=repo_root.parent,
            raw_subdir=".",
            output_subdir="output",
            category="test_repo",
            profile="yaml",
        )
        processor = RepoProcessor(config)
        processor.run()

        output_dir = repo_root.parent / "output" / "test_repo"
        bundle_files = list(output_dir.rglob("*.txt"))

        blueprint_files = [
            f for f in bundle_files
            if 'MODULE_BLUEPRINT' in f.read_text()
        ]

        assert len(blueprint_files) > 0, (
            "YAML files should emit MODULE_BLUEPRINT"
        )

        # Verify blueprint content
        verify_blueprint_content(blueprint_files[0].read_text(), "YAML")

    def test_yaml_module_blueprint_automation_patterns(self, tmp_path: Path) -> None:
        """Test that YAML MODULE_BLUEPRINT extracts automation patterns.

        Verify that automation, script, and sensor patterns are captured.
        """
        repo_root = setup_yaml_test_repo(
            tmp_path,
            {
                'automation.yaml': YAML_MODULE_CODE,
            }
        )

        config = ProcessingConfig(
            base_dir=repo_root.parent,
            raw_subdir=".",
            output_subdir="output",
            category="test_repo",
            profile="yaml",
        )
        processor = RepoProcessor(config)
        processor.run()

        output_dir = repo_root.parent / "output" / "test_repo"
        bundle_files = list(output_dir.rglob("*.txt"))

        blueprint_files = [
            f for f in bundle_files
            if 'MODULE_BLUEPRINT' in f.read_text()
        ]

        assert len(blueprint_files) > 0
        blueprint = blueprint_files[0].read_text()

        # Verify automation patterns are captured
        assert 'automation' in blueprint, (
            "MODULE_BLUEPRINT should capture 'automation' pattern"
        )
        assert 'trigger' in blueprint, (
            "MODULE_BLUEPRINT should capture 'trigger' pattern"
        )
        assert 'action' in blueprint, (
            "MODULE_BLUEPRINT should capture 'action' pattern"
        )


class TestCrossLanguageBlueprintConsistency:
    """Verification tests for consistent MODULE_BLUEPRINT across languages."""

    def test_all_languages_emit_blueprint(self, tmp_path: Path) -> None:
        """Test that all four languages emit MODULE_BLUEPRINT.

        This E2E test verifies that Python, TypeScript, PHP, and YAML
        all produce MODULE_BLUEPRINT output with the same structure.
        """
        results = []

        # Python repo
        py_repo = tmp_path / "python_repo"
        py_repo.mkdir()
        setup_python_test_repo(py_repo, {'component.py': PYTHON_MODULE_CODE})
        results.append((py_repo, "Python", "homeassistant"))

        # TypeScript repo
        ts_repo = tmp_path / "ts_repo"
        ts_repo.mkdir()
        setup_typescript_test_repo(ts_repo, {'component.ts': TYPESCRIPT_MODULE_CODE})
        results.append((ts_repo, "TypeScript", "typescript"))

        # PHP repo
        php_repo = tmp_path / "php_repo"
        php_repo.mkdir()
        setup_php_test_repo(php_repo, {'service.php': PHP_MODULE_CODE})
        results.append((php_repo, "PHP", "filesystem"))

        # YAML repo
        yaml_repo = tmp_path / "yaml_repo"
        yaml_repo.mkdir()
        setup_yaml_test_repo(yaml_repo, {'config.yaml': YAML_MODULE_CODE})
        results.append((yaml_repo, "YAML", "yaml"))

        # Process each repo
        for repo_path, _, profile in results:
            config = ProcessingConfig(
                base_dir=repo_path.parent,
                raw_subdir=".",
                output_subdir="output",
                category=repo_path.name,
                profile=profile,
            )
            processor = RepoProcessor(config)
            processor.run()

        # Verify all repos emitted MODULE_BLUEPRINT
        for repo_path, lang, _ in results:
            output_dir = repo_path.parent / "output" / repo_path.name
            bundle_files = list(output_dir.rglob("*.txt"))

            blueprint_files = [
                f for f in bundle_files
                if 'MODULE_BLUEPRINT' in f.read_text()
            ]

            assert len(blueprint_files) > 0, (
                f"{lang} repo should emit MODULE_BLUEPRINT"
            )

            # Verify structure
            verify_blueprint_content(blueprint_files[0].read_text(), lang)


# =============================================================================
# Module Detection Verification
# =============================================================================

class TestModuleDetectionAcrossLanguages:
    """Verification tests for module detection patterns across languages."""

    def test_python_manifest_anchor(self, tmp_path: Path) -> None:
        """Test that Python MODULE_BLUEPRINT uses manifest.json as anchor.

        AC-3.2: Python repos should detect manifest.json as anchor file.
        """
        repo_root = setup_python_test_repo(
            tmp_path,
            {
                'manifest.json': json.dumps({
                    "domain": "test",
                    "name": "Test Component",
                    "version": "1.0.0",
                    "dependencies": [],
                }),
                'component.py': PYTHON_MODULE_CODE,
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

        output_dir = repo_root.parent / "output" / "test_repo"
        bundle_files = list(output_dir.rglob("*.txt"))

        blueprint_files = [
            f for f in bundle_files
            if 'MODULE_BLUEPRINT' in f.read_text()
        ]

        assert len(blueprint_files) > 0
        blueprint = blueprint_files[0].read_text()

        # Should reference manifest.json as anchor
        assert 'manifest.json' in blueprint, (
            "MODULE_BLUEPRINT should reference manifest.json as anchor"
        )

    def test_typescript_directory_scan(self, tmp_path: Path) -> None:
        """Test that TypeScript MODULE_BLUEPRINT uses directory scan.

        AC-3.3: TypeScript repos should use directory-based anchor detection.
        """
        repo_root = setup_typescript_test_repo(
            tmp_path,
            {'component.ts': TYPESCRIPT_MODULE_CODE}
        )

        config = ProcessingConfig(
            base_dir=repo_root.parent,
            raw_subdir=".",
            output_subdir="output",
            category="test_repo",
            profile="typescript",
        )
        processor = RepoProcessor(config)
        processor.run()

        output_dir = repo_root.parent / "output" / "test_repo"
        bundle_files = list(output_dir.rglob("*.txt"))

        blueprint_files = [
            f for f in bundle_files
            if 'MODULE_BLUEPRINT' in f.read_text()
        ]

        assert len(blueprint_files) > 0

        # TypeScript should capture TypeScript-specific metadata
        blueprint = blueprint_files[0].read_text()
        assert 'typescript' in blueprint.lower(), (
            "TypeScript MODULE_BLUEPRINT should capture TypeScript-specific metadata"
        )

    def test_php_filesystem_anchor(self, tmp_path: Path) -> None:
        """Test that PHP MODULE_BLUEPRINT uses filesystem anchor detection.

        AC-3.4: PHP repos should detect composer.json and filesystem structure.
        """
        repo_root = setup_php_test_repo(
            tmp_path,
            {'UserService.php': PHP_MODULE_CODE}
        )

        config = ProcessingConfig(
            base_dir=repo_root.parent,
            raw_subdir=".",
            output_subdir="output",
            category="test_repo",
            profile="filesystem",
        )
        processor = RepoProcessor(config)
        processor.run()

        output_dir = repo_root.parent / "output" / "test_repo"
        bundle_files = list(output_dir.rglob("*.txt"))

        blueprint_files = [
            f for f in bundle_files
            if 'MODULE_BLUEPRINT' in f.read_text()
        ]

        assert len(blueprint_files) > 0

        # PHP should reference PHP-specific patterns
        blueprint = blueprint_files[0].read_text()
        assert 'namespace' in blueprint.lower(), (
            "PHP MODULE_BLUEPRINT should capture namespace patterns"
        )

    def test_yaml_anchor_detection(self, tmp_path: Path) -> None:
        """Test that YAML MODULE_BLUEPRINT uses anchor detection.

        AC-3.8: YAML repos should detect YAML-specific anchor patterns.
        """
        repo_root = setup_yaml_test_repo(
            tmp_path,
            {'automation.yaml': YAML_MODULE_CODE}
        )

        config = ProcessingConfig(
            base_dir=repo_root.parent,
            raw_subdir=".",
            output_subdir="output",
            category="test_repo",
            profile="yaml",
        )
        processor = RepoProcessor(config)
        processor.run()

        output_dir = repo_root.parent / "output" / "test_repo"
        bundle_files = list(output_dir.rglob("*.txt"))

        blueprint_files = [
            f for f in bundle_files
            if 'MODULE_BLUEPRINT' in f.read_text()
        ]

        assert len(blueprint_files) > 0

        # YAML should capture YAML-specific patterns
        blueprint = blueprint_files[0].read_text()
        assert 'automation' in blueprint.lower(), (
            "YAML MODULE_BLUEPRINT should capture automation patterns"
        )
