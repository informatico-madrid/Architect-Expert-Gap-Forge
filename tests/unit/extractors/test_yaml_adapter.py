# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Tests for YAML adapter.
"""

from __future__ import annotations

import pytest
from pathlib import Path

from src.utils.extractors.yaml_adapter import YamlAdapter


class TestYamlAdapter:
    """Tests for YamlAdapter."""

    @pytest.fixture
    def adapter(self):
        """Create a YamlAdapter instance."""
        return YamlAdapter()

    @pytest.fixture
    def blueprint_yaml(self, fixtures_dir: Path) -> Path:
        """Get path to blueprint YAML fixture."""
        return fixtures_dir / "yaml_samples" / "blueprint.yaml"

    def test_parse_file_returns_parse_result(self, adapter, blueprint_yaml):
        """YamlAdapter.parse_file returns ParseResult."""
        result = adapter.parse_file(blueprint_yaml)

        assert result is not None
        assert result.file_path == blueprint_yaml
        assert result.raw_content is not None
        assert result.dependencies is not None

    def test_extract_blueprint_pattern(self, adapter, blueprint_yaml):
        """YamlAdapter extracts blueprint pattern (name, description, domain)."""
        result = adapter.parse_file(blueprint_yaml)

        # YAML tree should be parsed
        assert result.ast_tree is not None
        assert isinstance(result.ast_tree, dict)

        # Check blueprint structure
        assert "blueprint" in result.ast_tree
        blueprint = result.ast_tree["blueprint"]
        assert blueprint["name"] == "Update Climate"
        assert (
            "description" in blueprint["name"] or "Update Climate" in blueprint["name"]
        )
        assert blueprint.get("domain") == "automation"

    def test_extract_trigger_pattern(self, adapter, blueprint_yaml):
        """YamlAdapter extracts trigger patterns."""
        result = adapter.parse_file(blueprint_yaml)

        # Check trigger structure
        assert "trigger" in result.ast_tree
        triggers = result.ast_tree["trigger"]
        assert isinstance(triggers, list)
        assert len(triggers) > 0

        # Check first trigger
        first_trigger = triggers[0]
        assert "platform" in first_trigger
        assert first_trigger["platform"] in ["time_pattern", "state"]

    def test_extract_condition_pattern(self, adapter, blueprint_yaml):
        """YamlAdapter extracts condition patterns."""
        result = adapter.parse_file(blueprint_yaml)

        # Check condition structure
        assert "condition" in result.ast_tree
        conditions = result.ast_tree["condition"]
        assert isinstance(conditions, list)

        # Check first condition
        if len(conditions) > 0:
            first_condition = conditions[0]
            assert "condition" in first_condition
            assert first_condition["condition"] == "state"

    def test_extract_action_pattern(self, adapter, blueprint_yaml):
        """YamlAdapter extracts action patterns."""
        result = adapter.parse_file(blueprint_yaml)

        # Check action structure
        assert "action" in result.ast_tree
        actions = result.ast_tree["action"]
        assert isinstance(actions, list)
        assert len(actions) > 0

        # Check first action
        first_action = actions[0]
        assert "service" in first_action
        assert "climate.set_hvac_mode" in first_action["service"]

    def test_extract_input_patterns(self, adapter, blueprint_yaml):
        """YamlAdapter extracts !input patterns."""
        result = adapter.parse_file(blueprint_yaml)

        # Check input parameters
        assert "blueprint" in result.ast_tree
        assert "input" in result.ast_tree["blueprint"]
        input_params = result.ast_tree["blueprint"]["input"]
        assert isinstance(input_params, dict)
        assert "climate_entity" in input_params
        assert "sensor_presence" in input_params

    def test_detect_jinja_expressions(self, adapter, blueprint_yaml):
        """YamlAdapter detects Jinja expressions in YAML values."""
        result = adapter.parse_file(blueprint_yaml)

        # Check for !input references
        assert "trigger" in result.ast_tree
        for trigger in result.ast_tree["trigger"]:
            if "entity_id" in trigger:
                trigger["entity_id"]
                # !input should be in the content
                assert (
                    "!input" in result.raw_content or "entity_id" in result.raw_content
                )

    def test_extract_dependencies(self, adapter, blueprint_yaml):
        """YamlAdapter extracts service call dependencies."""
        dependencies = adapter.extract_dependencies(blueprint_yaml)

        # Should extract service calls
        service_deps = [d for d in dependencies if d.module_type == "external"]
        assert len(service_deps) > 0

        # Check for climate service
        service_names = [d.name for d in dependencies]
        assert any("climate" in name for name in service_names)

    def test_extract_entity_dependencies(self, adapter, blueprint_yaml):
        """YamlAdapter extracts entity ID dependencies."""
        dependencies = adapter.extract_dependencies(blueprint_yaml)

        # Should extract entity references
        entity_deps = [d for d in dependencies if d.module_type == "entity"]
        assert len(entity_deps) > 0


class TestYamlAdapterParsing:
    """Tests for YAML parsing."""

    @pytest.fixture
    def adapter(self):
        """Create a YamlAdapter instance."""
        return YamlAdapter()

    def test_parse_valid_yaml(self, adapter, fixtures_dir: Path):
        """YamlAdapter parses valid YAML without errors."""
        blueprint_yaml = fixtures_dir / "yaml_samples" / "blueprint.yaml"
        result = adapter.parse_file(blueprint_yaml)

        assert result is not None
        assert result.raw_content is not None
        assert len(result.raw_content) > 0

    def test_yaml_tree_structure(self, adapter, fixtures_dir: Path):
        """YamlAdapter preserves YAML tree structure."""
        blueprint_yaml = fixtures_dir / "yaml_samples" / "blueprint.yaml"
        result = adapter.parse_file(blueprint_yaml)

        # Check that tree structure is preserved
        assert result.ast_tree is not None
        assert isinstance(result.ast_tree, dict)

        # Check top-level keys
        expected_keys = ["blueprint", "mode", "trigger", "condition", "action"]
        for key in expected_keys:
            assert key in result.ast_tree, (
                f"Expected key '{key}' not found in YAML tree"
            )
