# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for example profile configurations.

These tests verify that:
1. Example YAML files exist and are valid
2. Required keys are present in the configuration
3. Profile names match entries in master_docs_map.yaml
"""

from __future__ import annotations

from pathlib import Path
import pytest
import yaml


# Path to examples directory
EXAMPLES_DIR = (
    Path(__file__).parent.parent.parent / "configs" / "stage_1_discovery" / "examples"
)


class TestExampleConfigs:
    """Tests for validating example configuration files."""

    @pytest.fixture
    def master_docs_map(self) -> dict | None:
        """Load master_docs_map.yaml to get valid profile names."""
        config_path = (
            Path(__file__).parent.parent.parent
            / "configs"
            / "stage_1_discovery"
            / "master_docs_map.yaml"
        )
        if not config_path.exists():
            return None
        with open(config_path) as f:
            return yaml.safe_load(f)

    def test_php_hexagonal_example_exists(self) -> None:
        """Test that php_hexagonal.yaml example exists."""
        example_path = EXAMPLES_DIR / "php_hexagonal.yaml"
        assert example_path.exists(), f"Example file not found: {example_path}"

    def test_php_hexagonal_example_valid_yaml(self) -> None:
        """Test that php_hexagonal.yaml is valid YAML."""
        example_path = EXAMPLES_DIR / "php_hexagonal.yaml"
        with open(example_path) as f:
            config = yaml.safe_load(f)
        assert config is not None
        assert isinstance(config, dict)

    def test_php_hexagonal_example_required_keys(self, master_docs_map: dict | None) -> None:
        """Test that php_hexagonal.yaml has all required keys."""
        example_path = EXAMPLES_DIR / "php_hexagonal.yaml"
        with open(example_path) as f:
            config = yaml.safe_load(f)

        # Required top-level keys
        required_keys = [
            "profile",
            "display_name",
            "description",
            "extractor",
            "module_discovery",
        ]
        for key in required_keys:
            assert key in config, f"Missing required key: {key}"

        # Profile name should match master_docs_map
        if master_docs_map is not None:
            valid_profiles = list(master_docs_map.get("profiles", {}).keys()) + ["default"]
            assert config["profile"] in valid_profiles, (
                f"Profile '{config['profile']}' not in master_docs_map"
            )
        else:
            # If master_docs_map doesn't exist, just verify profile is a string
            assert isinstance(config["profile"], str)

        # Extractor should have on_parse_error
        assert "on_parse_error" in config["extractor"]
        assert config["extractor"]["on_parse_error"] in ["abort", "skip", "fallback"]

    def test_example_configs_have_file_header(self) -> None:
        """Test that example configs have the required file header."""
        for example_file in EXAMPLES_DIR.glob("*.yaml"):
            with open(example_file) as f:
                content = f.read()

            # Check for AEGF copyright header
            assert "Architect-Expert-Gap-Forge (AEGF)" in content
            assert "Copyright" in content
            assert "Apache License" in content
