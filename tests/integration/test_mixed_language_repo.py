# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Integration Test for Mixed-Language Repo Processing
====================================================

Verifies per-file adapter selection when processing mixed-language repositories.

Requirements: FR-5, AC-8.1 to AC-8.5
"""

from __future__ import annotations

from pathlib import Path

from src.discovery import ProcessingConfig, RepoProcessor


class TestMixedLanguageRepo:
    """Integration tests for mixed-language repo processing."""

    def test_per_file_adapter_selection(self, tmp_path: Path) -> None:
        """Test that each file type uses the correct adapter regardless of repo profile.

        AC-8.1: .py files should use Python adapter.
        AC-8.2: .ts files should use TypeScript adapter.
        AC-8.3: .php files should use PHP adapter.
        AC-8.4: .yaml files should use YAML adapter.
        """
        repo_root = tmp_path / "test_repo"
        repo_root.mkdir()

        owner_dir = repo_root / "owner" / "myrepo"
        owner_dir.mkdir(parents=True)

        # Create TypeScript component directory with __init__.py anchor
        ts_component = owner_dir / "components" / "button-card"
        ts_component.mkdir(parents=True)
        (ts_component / "__init__.py").write_text("# TypeScript component anchor")

        # Create Python component directory with __init__.py anchor
        py_component = owner_dir / "custom_components" / "test_component"
        py_component.mkdir(parents=True)
        (py_component / "__init__.py").write_text("# Python component anchor")

        # Create PHP services directory with __init__.py anchor
        php_services = owner_dir / "src" / "Services"
        php_services.mkdir(parents=True)
        (php_services / "__init__.py").write_text("# PHP services anchor")

        # Create YAML configurations directory with __init__.py anchor
        yaml_configs = owner_dir / "configurations"
        yaml_configs.mkdir(parents=True)
        (yaml_configs / "__init__.py").write_text("# YAML configs anchor")

        # Create TypeScript file
        (ts_component / "button-card.ts").write_text("""
import { LitElement, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('ha-button-card')
export class HaButtonCard extends LitElement {
  @property({ type: String }) private label = 'Click me';
  render() { return html`<button>${this.label}</button>`; }
}
""".strip())

        # Create Python file
        (py_component / "manifest.json").write_text('{"domain": "test", "name": "Test", "version": "1.0"}')
        (py_component / "component.py").write_text("""
DOMAIN = 'test_component'

def process_data(data):
    return data
""".strip())

        # Create PHP file
        (php_services / "UserService.php").write_text("""
<?php

namespace App\\Services;

class UserService {
    private array $users = [];

    public function createUser(string $name, string $email): User {
        $user = new User($name, $email);
        $this->users[] = $user;
        return $user;
    }
}
""".strip())

        # Create YAML file
        (yaml_configs / "automation.yaml").write_text("""
automation:
  - alias: "Light Control"
    trigger:
      platform: state
      entity_id: light.living_room
    action:
      service: light.toggle
""".strip())

        # Use init strategy with __init__.py anchors to process all file types
        config = ProcessingConfig(
            base_dir=tmp_path,
            raw_subdir="test_repo",
            output_subdir="output",
            category="owner",
            module_discovery_strategy="init",
            extensions={".ts", ".tsx", ".py", ".php", ".yaml", ".yml", ".jinja", ".jinja2", ".md"},
        )
        processor = RepoProcessor(config)
        processor.run()

        # Verify bundles were created for all languages
        output_dir = tmp_path / "output" / "owner"
        bundle_files = list(output_dir.rglob("*.txt"))

        # Find MODULE_BLUEPRINT files
        blueprint_files = [
            f for f in bundle_files
            if 'MODULE_BLUEPRINT' in f.read_text()
        ]

        assert len(blueprint_files) > 0, (
            "All file types should emit MODULE_BLUEPRINT"
        )

        # Verify TypeScript file was processed
        ts_blueprints = [
            f for f in blueprint_files
            if 'button-card.ts' in f.read_text()
        ]
        assert len(ts_blueprints) > 0, (
            "TypeScript file should be processed"
        )

        # Verify Python file was processed
        py_blueprints = [
            f for f in blueprint_files
            if 'component.py' in f.read_text()
        ]
        assert len(py_blueprints) > 0, (
            "Python file should be processed"
        )

        # Verify PHP file was processed
        php_blueprints = [
            f for f in blueprint_files
            if 'UserService.php' in f.read_text()
        ]
        assert len(php_blueprints) > 0, (
            "PHP file should be processed"
        )

        # Verify YAML file was processed
        yaml_blueprints = [
            f for f in blueprint_files
            if 'automation.yaml' in f.read_text()
        ]
        assert len(yaml_blueprints) > 0, (
            "YAML file should be processed"
        )

    def test_all_fragment_types_mixed_repo(self, tmp_path: Path) -> None:
        """Test that all fragment types (1, 3, 4, 5) are generated in mixed repo.

        AC-8.5: All fragment types should be emitted regardless of language mix.
        """
        repo_root = tmp_path / "test_repo"
        repo_root.mkdir()

        owner_dir = repo_root / "owner" / "myrepo"
        owner_dir.mkdir(parents=True)

        # Create Python component with test (TYPE 1) and __init__.py anchor
        py_component = owner_dir / "custom_components" / "test_component"
        py_component.mkdir(parents=True)
        (py_component / "__init__.py").write_text("# Python component anchor")

        (py_component / "manifest.json").write_text('{"domain": "test", "name": "Test", "version": "1.0"}')
        (py_component / "logic.py").write_text("""
DOMAIN = 'test_component'

def calculate_total(items):
    total = 0
    for item in items:
        total += item.get('price', 0)
    return total
""".strip())

        # Create tests directory with test file (required for TYPE 1)
        # Test file must be >= MIN_SIZE (300 chars)
        # Tests are located relative to owner_dir (the repo root for module processing)
        tests_dir = owner_dir / "tests" / "owner" / "myrepo" / "custom_components" / "test_component"
        tests_dir.mkdir(parents=True)
        (tests_dir / "test_logic.py").write_text("""
import logic

def test_calculate_total():
    '''Test calculate_total with various scenarios.'''
    # Test with simple price list
    items = [{'price': 10}, {'price': 20}]
    result = logic.calculate_total(items)
    assert result == 30, f"Expected 30 but got {result}"

    # Test with empty list
    empty_result = logic.calculate_total([])
    assert empty_result == 0, f"Expected 0 for empty list"

    # Test with mixed price and cost keys
    mixed_items = [
        {'price': 100, 'cost': 50},
        {'cost': 200, 'price': 150}
    ]
    total = logic.calculate_total(mixed_items)
    assert total == 500, f"Expected 500 but got {total}"

    print("All tests passed")
""".strip())

        # Create large PHP file (TYPE 3) with __init__.py anchor
        php_services = owner_dir / "src" / "Services"
        php_services.mkdir(parents=True)
        (php_services / "__init__.py").write_text("# PHP services anchor")

        (php_services / "large_processor.php").write_text("""
<?php

namespace App\\Services;

class LargeProcessor {
    private array $data = [];

    public function processComplexData(array $input): array {
        $result = [];
        foreach ($input as $item) {
            if (is_array($item)) {
                $result[] = $this->processNestedArray($item);
            } else {
                $result[] = $this->transformScalar($item);
            }
        }
        return $result;
    }

    private function processNestedArray(array $nested): array {
        $output = [];
        foreach ($nested as $key => $value) {
            if (is_array($value)) {
                $output[$key] = $this->processNestedArray($value);
            } else {
                $output[$key] = $this->transformScalar($value);
            }
        }
        return $output;
    }

    private function transformScalar($value): string {
        if ($value === null) {
            return 'null';
        } elseif (is_bool($value)) {
            return $value ? 'true' : 'false';
        } elseif (is_numeric($value)) {
            return strval($value);
        } elseif (is_string($value)) {
            return trim($value);
        } else {
            return repr($value);
        }
    }

    public function validateInput(array $data): bool {
        if (!is_array($data)) {
            return false;
        }
        foreach ($data as $key => $value) {
            if (!is_string($key)) {
                return false;
            }
            if (!is_array($value) && !is_string($value) && !is_numeric($value)) {
                return false;
            }
        }
        return true;
    }

    public function mergeArrays(array $primary, array $secondary): array {
        $merged = $primary;
        foreach ($secondary as $key => $value) {
            if (isset($merged[$key]) && is_array($merged[$key]) && is_array($value)) {
                $merged[$key] = $this->mergeArrays($merged[$key], $value);
            } else {
                $merged[$key] = $value;
            }
        }
        return $merged;
    }

    public function filterByCriteria(array $data, array $criteria): array {
        $result = [];
        foreach ($data as $key => $value) {
            $matches = true;
            foreach ($criteria as $critKey => $critValue) {
                if (isset($value[$critKey]) && $value[$critKey] !== $critValue) {
                    $matches = false;
                    break;
                }
            }
            if ($matches) {
                $result[$key] = $value;
            }
        }
        return $result;
    }
}
""".strip())

        # Create governance file (TYPE 5)
        (owner_dir / "CLAUDE.md").write_text("""# Project Guidelines

This project follows specific development guidelines.
""".strip())

        # Create TypeScript file (TYPE 4)
        ts_component = owner_dir / "components" / "button-card"
        ts_component.mkdir(parents=True)

        (ts_component / "button-card.ts").write_text("""
import { LitElement, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('ha-button-card')
export class HaButtonCard extends LitElement {
  @property({ type: String }) private label = 'Click me';
  render() { return html`<button>${this.label}</button>`; }
}
""".strip())

        config = ProcessingConfig(
            base_dir=tmp_path,
            raw_subdir="test_repo",
            output_subdir="output",
            category="owner",
            module_discovery_strategy="init",
            extensions={".py", ".php", ".ts", ".tsx", ".yaml", ".yml", ".jinja", ".jinja2", ".md"},
        )
        processor = RepoProcessor(config)
        processor.run()

        # Verify bundles were created
        output_dir = tmp_path / "output" / "owner"
        bundle_files = list(output_dir.rglob("*.txt"))

        bundle_contents = {}
        for bf in bundle_files:
            if bf.exists():
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

        # Verify TYPE 5 (GOVERNANCE_RULES)
        has_type5 = any('GOVERNANCE_RULES' in content for content in bundle_contents.values())
        assert has_type5, (
            "TYPE 5 GOVERNANCE_RULES should be emitted from governance files"
        )
