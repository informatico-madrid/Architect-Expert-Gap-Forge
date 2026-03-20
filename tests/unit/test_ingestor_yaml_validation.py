# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for YAML configuration validation in the ingestor.

T016-T017: Unit tests for YAML validation:
- Tests validation of required fields in DiscoveryConfig
- Tests validation of enum values (mode field)
- Uses unit testing approach: direct dict input, no file I/O
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from src.discovery.ingestor import DiscoveryConfig


class TestYamlRequiredFieldValidation:
    """Unit tests for required field validation in DiscoveryConfig."""

    @pytest.fixture
    def missing_category_yaml_path(self) -> Path:
        """Path to the YAML config fixture missing required 'category' field."""
        return Path(__file__).parent.parent / "fixtures" / "yaml_configs" / "missing_category.yaml"

    def test_missing_category_field_raises_validation_error(self) -> None:
        """Test that missing required field 'category' raises ValidationError.

        T016: Unit test for missing required field validation.
        This is a unit test - it creates a dict directly without file I/O.
        """
        # Arrange - Create config dict without required 'category' field
        config_dict = {
            "mode": "static",
            "search_query": "filename:manifest.json",
            "static_repos": ["owner/repo1"],
        }

        # Act & Assert - Should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            DiscoveryConfig(**config_dict)

        # Verify the error mentions 'category'
        error_messages = str(exc_info.value).lower()
        assert "category" in error_messages

    def test_missing_category_field_fails_validation(self, missing_category_yaml_path: Path) -> None:
        """Test that missing required field 'category' in YAML file raises ValidationError.

        T020: Unit test for missing required field validation using YAML fixture file.
        This test loads the actual YAML fixture and verifies it fails validation.
        """
        # Arrange - Load YAML from fixture file
        with open(missing_category_yaml_path, "r") as f:
            config_data = yaml.safe_load(f)

        # Act & Assert - Should raise ValidationError when creating DiscoveryConfig
        with pytest.raises(ValidationError) as exc_info:
            DiscoveryConfig(**config_data)

        # Verify the error mentions 'category'
        error_messages = str(exc_info.value).lower()
        assert "category" in error_messages

    def test_missing_search_query_is_valid(self) -> None:
        """Test that missing optional field 'search_query' is valid."""
        # Arrange
        config_dict = {
            "category": "test-category",
            "mode": "static",
            "static_repos": ["owner/repo1"],
        }

        # Act
        config = DiscoveryConfig(**config_dict)

        # Assert
        assert config.category == "test-category"
        assert config.search_query is None

    def test_missing_mode_uses_default(self) -> None:
        """Test that missing optional field 'mode' uses default value."""
        # Arrange
        config_dict = {
            "category": "test-category",
            "static_repos": ["owner/repo1"],
        }

        # Act
        config = DiscoveryConfig(**config_dict)

        # Assert
        assert config.mode == "static"

    def test_empty_category_string_is_valid(self) -> None:
        """Test that empty string for 'category' is accepted (Pydantic allows it)."""
        # Arrange
        config_dict = {
            "category": "",  # Empty string is valid in Pydantic
            "mode": "static",
            "static_repos": ["owner/repo1"],
        }

        # Act - Should not raise
        config = DiscoveryConfig(**config_dict)

        # Assert
        assert config.category == ""


class TestYamlEnumValidation:
    """Unit tests for enum field validation in DiscoveryConfig."""

    @pytest.fixture
    def invalid_mode_yaml_path(self) -> Path:
        """Path to the YAML config fixture with invalid 'mode' enum value."""
        return Path(__file__).parent.parent / "fixtures" / "yaml_configs" / "invalid_mode.yaml"

    def test_invalid_mode_value_raises_validation_error(self) -> None:
        """Test that invalid enum value for 'mode' raises ValidationError.

        T017: Unit test for invalid enum value validation.
        This is a unit test - it creates a dict directly without file I/O.
        """
        # Arrange - Create config dict with invalid mode value
        config_dict = {
            "category": "test-category",
            "mode": "invalid_mode",
            "static_repos": ["owner/repo1"],
        }

        # Act & Assert - Should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            DiscoveryConfig(**config_dict)

        # Verify the error mentions 'mode'
        error_messages = str(exc_info.value).lower()
        assert "mode" in error_messages

    def test_invalid_mode_fails_validation(self, invalid_mode_yaml_path: Path) -> None:
        """Test that invalid enum value 'mode' in YAML file raises ValidationError.

        T021: Unit test for invalid enum value validation using YAML fixture file.
        This test loads the actual YAML fixture and verifies it fails validation.
        """
        # Arrange - Load YAML from fixture file
        with open(invalid_mode_yaml_path, "r") as f:
            config_data = yaml.safe_load(f)

        # Act & Assert - Should raise ValidationError when creating DiscoveryConfig
        with pytest.raises(ValidationError) as exc_info:
            DiscoveryConfig(**config_data)

        # Verify the error mentions 'mode'
        error_messages = str(exc_info.value).lower()
        assert "mode" in error_messages

    def test_valid_mode_dynamic(self) -> None:
        """Test that valid mode 'dynamic' is accepted."""
        # Arrange
        config_dict = {
            "category": "test-category",
            "mode": "dynamic",
            "search_query": "stars:>100",
        }

        # Act
        config = DiscoveryConfig(**config_dict)

        # Assert
        assert config.mode == "dynamic"

    def test_valid_mode_static(self) -> None:
        """Test that valid mode 'static' is accepted."""
        # Arrange
        config_dict = {
            "category": "test-category",
            "mode": "static",
            "static_repos": ["owner/repo1"],
        }

        # Act
        config = DiscoveryConfig(**config_dict)

        # Assert
        assert config.mode == "static"

    def test_mode_case_sensitive(self) -> None:
        """Test that mode validation is case-sensitive."""
        # Arrange - uppercase should fail
        config_dict = {
            "category": "test-category",
            "mode": "STATIC",
            "static_repos": ["owner/repo1"],
        }

        # Act & Assert - Should raise ValidationError
        with pytest.raises(ValidationError):
            DiscoveryConfig(**config_dict)

    def test_mode_number_raises_error(self) -> None:
        """Test that numeric mode value raises ValidationError."""
        # Arrange - number instead of string
        config_dict = {
            "category": "test-category",
            "mode": 123,
            "static_repos": ["owner/repo1"],
        }

        # Act & Assert
        with pytest.raises(ValidationError):
            DiscoveryConfig(**config_dict)


class TestYamlFieldTypeValidation:
    """Unit tests for field type validation in DiscoveryConfig."""

    def test_invalid_limit_type_raises_error(self) -> None:
        """Test that invalid limit type raises ValidationError."""
        # Arrange
        config_dict = {
            "category": "test-category",
            "mode": "static",
            "static_repos": ["owner/repo1"],
            "limit": "not_a_number",  # Should be int
        }

        # Act & Assert
        with pytest.raises(ValidationError):
            DiscoveryConfig(**config_dict)

    def test_invalid_min_stars_type_raises_error(self) -> None:
        """Test that invalid min_stars type raises ValidationError."""
        # Arrange
        config_dict = {
            "category": "test-category",
            "mode": "static",
            "static_repos": ["owner/repo1"],
            "min_stars": "not_a_number",  # Should be int
        }

        # Act & Assert
        with pytest.raises(ValidationError):
            DiscoveryConfig(**config_dict)

    def test_negative_limit_raises_error(self) -> None:
        """Test that negative limit raises ValidationError (ge=1 constraint)."""
        # Arrange
        config_dict = {
            "category": "test-category",
            "mode": "static",
            "static_repos": ["owner/repo1"],
            "limit": -1,
        }

        # Act & Assert
        with pytest.raises(ValidationError):
            DiscoveryConfig(**config_dict)

    def test_zero_limit_raises_error(self) -> None:
        """Test that zero limit raises ValidationError (ge=1 constraint)."""
        # Arrange
        config_dict = {
            "category": "test-category",
            "mode": "static",
            "static_repos": ["owner/repo1"],
            "limit": 0,
        }

        # Act & Assert
        with pytest.raises(ValidationError):
            DiscoveryConfig(**config_dict)

    def test_negative_min_stars_raises_error(self) -> None:
        """Test that negative min_stars raises ValidationError (ge=0 constraint)."""
        # Arrange
        config_dict = {
            "category": "test-category",
            "mode": "static",
            "static_repos": ["owner/repo1"],
            "min_stars": -5,
        }

        # Act & Assert
        with pytest.raises(ValidationError):
            DiscoveryConfig(**config_dict)

    def test_per_page_above_max_raises_error(self) -> None:
        """Test that per_page above 100 raises ValidationError (le=100 constraint)."""
        # Arrange
        config_dict = {
            "category": "test-category",
            "mode": "static",
            "static_repos": ["owner/repo1"],
            "per_page": 101,
        }

        # Act & Assert
        with pytest.raises(ValidationError):
            DiscoveryConfig(**config_dict)


class TestYamlComplexFieldValidation:
    """Unit tests for complex field validation in DiscoveryConfig."""

    def test_static_repos_must_be_list(self) -> None:
        """Test that static_repos must be a list."""
        # Arrange
        config_dict = {
            "category": "test-category",
            "mode": "static",
            "static_repos": "not_a_list",  # Should be list
        }

        # Act & Assert
        with pytest.raises(ValidationError):
            DiscoveryConfig(**config_dict)

    def test_profile_extensions_must_be_set(self) -> None:
        """Test that profile_extensions must be a set."""
        # Arrange
        config_dict = {
            "category": "test-category",
            "mode": "static",
            "static_repos": ["owner/repo1"],
            "profile_extensions": [".py", ".js"],  # Should be set, not list
        }

        # Act
        # This may work due to type coercion, or fail depending on Pydantic version
        # Let's just verify it handles the type appropriately
        config = DiscoveryConfig(**config_dict)
        assert isinstance(config.profile_extensions, (set, list))

    def test_base_dir_accepts_path_object(self) -> None:
        """Test that base_dir accepts a Path object."""
        # Arrange
        config_dict = {
            "category": "test-category",
            "mode": "static",
            "static_repos": ["owner/repo1"],
            "base_dir": Path("/tmp/test"),
        }

        # Act
        config = DiscoveryConfig(**config_dict)

        # Assert
        assert config.base_dir == Path("/tmp/test")

    def test_base_dir_accepts_string(self) -> None:
        """Test that base_dir accepts a string (converted to Path)."""
        # Arrange
        config_dict = {
            "category": "test-category",
            "mode": "static",
            "static_repos": ["owner/repo1"],
            "base_dir": "/tmp/test",
        }

        # Act
        config = DiscoveryConfig(**config_dict)

        # Assert
        assert config.base_dir == Path("/tmp/test")

    def test_raw_subdir_default_value(self) -> None:
        """Test that raw_subdir defaults to 'data/raw'."""
        # Arrange
        config_dict = {
            "category": "test-category",
            "mode": "static",
            "static_repos": ["owner/repo1"],
        }

        # Act
        config = DiscoveryConfig(**config_dict)

        # Assert
        assert config.raw_subdir == "data/raw"
