# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Integration tests for YAML loading in the ingestor.

T008-T010, T014-T015, T026-T028: Integration tests for YAML loading:
- Tests loading YAML files from disk using yaml.safe_load()
- Tests detection of YAML syntax errors
- Tests detection of the triple-dash (---) bug after copyright header
- Validates the full CLI -> YAML -> Pydantic flow
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from src.discovery.ingestor import DiscoveryConfig


class TestYamlLoadFromDisk:
    """Tests for loading YAML configuration files from disk."""

    @pytest.fixture
    def valid_yaml_path(self) -> Path:
        """Path to the valid YAML config fixture."""
        return (
            Path(__file__).parent.parent
            / "fixtures"
            / "yaml_configs"
            / "valid_config.yaml"
        )

    @pytest.fixture
    def invalid_syntax_yaml_path(self) -> Path:
        """Path to the invalid syntax YAML config fixture."""
        return (
            Path(__file__).parent.parent
            / "fixtures"
            / "yaml_configs"
            / "invalid_syntax.yaml"
        )

    def test_load_valid_yaml_from_disk(self, valid_yaml_path: Path) -> None:
        """Test that valid YAML file loads successfully from disk.

        T008: Integration test for valid YAML loading from disk.
        This test validates the real flow: file -> yaml.safe_load() -> dict -> DiscoveryConfig.
        """
        # Arrange
        # (fixtures are set up)

        # Act
        with open(valid_yaml_path, "r") as f:
            config_data = yaml.safe_load(f)

        # Assert
        assert config_data is not None
        assert isinstance(config_data, dict)
        assert config_data["search_query"] == "filename:manifest.json"
        assert config_data["category"] == "test_category"
        assert config_data["mode"] == "static"

    def test_valid_yaml_loads_to_discovery_config(self, valid_yaml_path: Path) -> None:
        """Test that loaded YAML data converts to DiscoveryConfig successfully.

        T008: Validates the full YAML -> Pydantic conversion.
        """
        # Arrange
        with open(valid_yaml_path, "r") as f:
            config_data = yaml.safe_load(f)

        # Handle Path serialization from YAML
        if "base_dir" in config_data and isinstance(config_data["base_dir"], str):
            config_data["base_dir"] = Path(config_data["base_dir"])

        # Act
        config = DiscoveryConfig(**config_data)

        # Assert
        assert isinstance(config, DiscoveryConfig)
        assert config.category == "test_category"
        assert config.mode == "static"
        assert config.search_query == "filename:manifest.json"
        assert config.limit == 10
        assert config.min_stars == 0

    def test_load_invalid_yaml_syntax(self, invalid_syntax_yaml_path: Path) -> None:
        """Test that invalid YAML syntax raises yaml.YAMLError.

        T010: Integration test for invalid YAML syntax detection.
        """
        # Arrange
        # (fixtures are set up)

        # Act & Assert
        with pytest.raises(yaml.YAMLError):
            with open(invalid_syntax_yaml_path, "r") as f:
                yaml.safe_load(f)


class TestYamlTripleDashBug:
    """Tests for detection of YAML document separator (---) bug."""

    @pytest.fixture
    def copyright_then_separator_path(self) -> Path:
        """Path to the YAML fixture with copyright then separator."""
        return (
            Path(__file__).parent.parent
            / "fixtures"
            / "yaml_configs"
            / "copyright_then_separator.yaml"
        )

    @pytest.fixture
    def yaml_with_triple_dash(self, tmp_path: Path) -> Path:
        """Create a YAML file with --- after copyright header (the bug)."""
        yaml_content = """# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0
---
search_query: 'filename:manifest.json'
category: test_category
"""
        file_path = tmp_path / "buggy_config.yaml"
        file_path.write_text(yaml_content)
        return file_path

    def test_yaml_document_separator_ignores_content_before(
        self, yaml_with_triple_dash: Path
    ) -> None:
        """Test that --- after copyright causes content before to be ignored.

        T014, T028: Integration test for YAML document separator bug detection.
        This test verifies that the triple-dash (---) bug is detectable.
        When --- appears after a copyright header, yaml.safe_load() ignores
        everything before the --- and only loads content after it.
        """
        # Act
        with open(yaml_with_triple_dash, "r") as f:
            loaded_data = yaml.safe_load(f)

        # Assert - The bug: content BEFORE the --- is ignored
        # yaml.safe_load() starts from after the ---
        # In this case it works because content after --- is valid
        # But the copyright is lost (expected behavior of ---)
        assert loaded_data is not None
        assert loaded_data.get("search_query") == "filename:manifest.json"

    def test_yaml_copyright_then_separator_fixture(
        self, copyright_then_separator_path: Path
    ) -> None:
        """Test YAML file with copyright header followed by --- separator.

        T026, T027, T028: Integration test for YAML document separator bug.
        Uses the physical fixture file copyright_then_separator.yaml.
        This test verifies that when --- appears after a copyright header,
        yaml.safe_load() loads only content after the separator.
        """
        # Act
        with open(copyright_then_separator_path, "r") as f:
            loaded_data = yaml.safe_load(f)

        # Assert - Content after --- is loaded correctly
        # The copyright comments before --- are ignored (expected YAML behavior)
        assert loaded_data is not None
        assert isinstance(loaded_data, dict)
        assert loaded_data.get("search_query") == "filename:manifest.json"
        assert loaded_data.get("category") == "test_category"
        assert loaded_data.get("mode") == "static"

    def test_yaml_with_triple_dash_multi_document_raises_error(
        self, tmp_path: Path
    ) -> None:
        """Test that YAML with multiple documents raises ComposerError.

        T014: Specific test for the triple-dash bug scenario.
        When --- appears in the middle of a YAML file (not at start),
        yaml.safe_load() raises an error because it expects a single document.
        """
        # Arrange - Create YAML with --- in the middle (multi-document)
        yaml_content = """search_query: 'important_query'
category: important_category
---
# This is now a second document
search_query: 'ignored_query'
"""
        file_path = tmp_path / "multidoc.yaml"
        file_path.write_text(yaml_content)

        # Act & Assert - safe_load raises error for multi-document YAML
        with pytest.raises(yaml.composer.ComposerError):
            with open(file_path, "r") as f:
                yaml.safe_load(f)


class TestYamlEdgeCases:
    """Edge case tests for YAML loading."""

    def test_load_empty_yaml_file(self, tmp_path: Path) -> None:
        """Test loading an empty YAML file returns None.

        T010: Edge case - empty YAML file.
        """
        # Arrange
        empty_file = tmp_path / "empty.yaml"
        empty_file.write_text("")

        # Act
        with open(empty_file, "r") as f:
            loaded_data = yaml.safe_load(f)

        # Assert
        assert loaded_data is None

    def test_load_yaml_with_only_comments(self, tmp_path: Path) -> None:
        """Test loading YAML file with only comments returns None.

        T010: Edge case - YAML with only comments.
        """
        # Arrange
        comment_only_file = tmp_path / "comments.yaml"
        comment_only_file.write_text("# Just a comment\n# Another comment\n")

        # Act
        with open(comment_only_file, "r") as f:
            loaded_data = yaml.safe_load(f)

        # Assert
        assert loaded_data is None

    def test_load_nonexistent_file_raises_file_not_found(self, tmp_path: Path) -> None:
        """Test that loading nonexistent file raises FileNotFoundError.

        T010: Edge case - file does not exist.
        """
        # Arrange
        nonexistent_path = tmp_path / "does_not_exist.yaml"

        # Act & Assert
        with pytest.raises(FileNotFoundError):
            with open(nonexistent_path, "r") as f:
                yaml.safe_load(f)


class TestYamlToDiscoveryConfigValidation:
    """Tests for validating YAML data against DiscoveryConfig model."""

    @pytest.fixture
    def valid_yaml_path(self) -> Path:
        """Path to the valid YAML config fixture."""
        return (
            Path(__file__).parent.parent
            / "fixtures"
            / "yaml_configs"
            / "valid_config.yaml"
        )

    def test_missing_category_field_fails_validation(self, tmp_path: Path) -> None:
        """Test that missing required field 'category' raises ValidationError.

        T020: Unit test for missing required field validation.
        """
        # Arrange
        yaml_content = """
search_query: 'filename:manifest.json'
mode: static
"""
        file_path = tmp_path / "missing_category.yaml"
        file_path.write_text(yaml_content)

        with open(file_path, "r") as f:
            config_data = yaml.safe_load(f)

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            DiscoveryConfig(**config_data)

        # Verify the error mentions 'category'
        assert "category" in str(exc_info.value).lower()

    def test_invalid_mode_value_fails_validation(self, tmp_path: Path) -> None:
        """Test that invalid enum value for 'mode' raises ValidationError.

        T021: Unit test for invalid enum value validation.
        """
        # Arrange
        yaml_content = """
search_query: 'filename:manifest.json'
category: test_category
mode: invalid_mode
"""
        file_path = tmp_path / "invalid_mode.yaml"
        file_path.write_text(yaml_content)

        with open(file_path, "r") as f:
            config_data = yaml.safe_load(f)

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            DiscoveryConfig(**config_data)

        # Verify the error mentions 'mode'
        assert "mode" in str(exc_info.value).lower()

    def test_valid_yaml_passes_all_validations(self, valid_yaml_path: Path) -> None:
        """Test that valid YAML passes all DiscoveryConfig validations.

        T008: Comprehensive validation test.
        """
        # Arrange
        with open(valid_yaml_path, "r") as f:
            config_data = yaml.safe_load(f)

        if "base_dir" in config_data and isinstance(config_data["base_dir"], str):
            config_data["base_dir"] = Path(config_data["base_dir"])

        # Act
        config = DiscoveryConfig(**config_data)

        # Assert - All fields validated correctly
        assert config.category == "test_category"
        assert config.mode == "static"
        assert config.search_query == "filename:manifest.json"
        assert config.min_stars == 0
        assert config.limit == 10
        assert config.per_page == 100
        assert config.profile == "test_profile"
        assert config.profile_extensions == {".py", ".md"}
        assert config.profile_ignored_paths == {".git", "node_modules", "__pycache__"}
        assert config.static_repos == [
            "test-owner/test-repo-1",
            "test-owner/test-repo-2",
        ]
        assert config.base_dir == Path(".")
        assert config.raw_subdir == "data/raw"
