# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Tests for discovery config validation.

T026: Configuration validation tests ensure YAML configs have correct structure
before execution, preventing silent failures like Python configs running instead
of TypeScript configs.
"""

from __future__ import annotations

import pytest
from pathlib import Path
from pydantic import ValidationError

from src.discovery.ingestor import DiscoveryConfig


class TestDiscoveryConfigValidation:
    """Tests for DiscoveryConfig validation."""

    def test_config_accepts_extensions_field(self) -> None:
        """Config accepts 'extensions' field (mapped to profile_extensions)."""
        valid_config = {
            "category": "test",
            "mode": "static",
            "profile": "typescript",
            "extensions": [".ts", ".tsx"],  # Correct field name
            "static_repos": ["test/repo"],
        }

        config = DiscoveryConfig(**valid_config)
        assert config.profile_extensions is not None
        assert ".ts" in config.profile_extensions
        assert ".tsx" in config.profile_extensions

    def test_config_accepts_profile_extensions_field(self) -> None:
        """Config also accepts 'profile_extensions' field directly."""
        valid_config = {
            "category": "test",
            "mode": "static",
            "profile": "typescript",
            "profile_extensions": [".ts", ".tsx"],  # Direct field
            "static_repos": ["test/repo"],
        }

        config = DiscoveryConfig(**valid_config)
        assert config.profile_extensions is not None
        assert ".ts" in config.profile_extensions

    def test_config_requires_static_repos_for_static_mode(self) -> None:
        """Static mode requires non-empty static_repos list."""
        invalid_config = {
            "category": "test",
            "mode": "static",
            "profile": "typescript",
            "extensions": [".ts"],
            "static_repos": [],  # Empty list should fail
        }

        with pytest.raises(ValidationError) as exc_info:
            DiscoveryConfig(**invalid_config)

        assert "static_repos" in str(exc_info.value).lower()

    def test_config_invalid_mode(self) -> None:
        """Config rejects invalid mode values."""
        invalid_config = {
            "category": "test",
            "mode": "invalid_mode",  # Should be static or dynamic
            "extensions": [".ts"],
            "static_repos": ["test/repo"],
        }

        with pytest.raises(ValidationError):
            DiscoveryConfig(**invalid_config)

    def test_config_ignored_paths_optional(self) -> None:
        """Config handles optional ignore_patterns field."""
        valid_config = {
            "category": "test",
            "mode": "static",
            "profile": "typescript",
            "extensions": [".ts"],
            "static_repos": ["test/repo"],
        }

        config = DiscoveryConfig(**valid_config)
        assert config is not None

    def test_config_with_ignore_patterns(self) -> None:
        """Config accepts optional 'ignore_patterns' (mapped to profile_ignored_paths)."""
        valid_config = {
            "category": "test",
            "mode": "static",
            "profile": "typescript",
            "extensions": [".ts"],
            "ignore_patterns": [".git", "__pycache__"],
            "static_repos": ["test/repo"],
        }

        config = DiscoveryConfig(**valid_config)
        assert config.profile_ignored_paths is not None
        assert ".git" in config.profile_ignored_paths

    def test_config_with_profile_ignored_paths(self) -> None:
        """Config also accepts 'profile_ignored_paths' field directly."""
        valid_config = {
            "category": "test",
            "mode": "static",
            "profile": "typescript",
            "extensions": [".ts"],
            "profile_ignored_paths": [".git", "__pycache__"],
            "static_repos": ["test/repo"],
        }

        config = DiscoveryConfig(**valid_config)
        assert config.profile_ignored_paths is not None
        assert ".git" in config.profile_ignored_paths


class TestConfigFileValidation:
    """Tests for validating YAML config files."""

    def test_homeassistant_frontend_config_structure(self) -> None:
        """homeassistant_frontend.yaml has correct field names."""
        config_path = Path(
            "configs/stage_1_discovery/examples/homeassistant_frontend.yaml"
        )
        assert config_path.exists(), f"Config file not found: {config_path}"

        import yaml

        config_data = yaml.safe_load(config_path.read_text())

        # Must have 'extensions' field
        assert "extensions" in config_data, (
            "Config must have 'extensions' field, not 'profile_extensions'"
        )

        # Must have 'static_repos' for static mode
        assert config_data.get("mode") == "static", "Config mode should be 'static'"
        assert "static_repos" in config_data, (
            "Static mode config must have 'static_repos' field"
        )

    def test_homeassistant_frontend_requires_extensions(self) -> None:
        """homeassistant_frontend config must have TypeScript extensions."""
        import yaml

        config_path = Path(
            "configs/stage_1_discovery/examples/homeassistant_frontend.yaml"
        )
        config_data = yaml.safe_load(config_path.read_text())

        extensions = config_data.get("extensions", [])
        assert ".ts" in extensions or ".tsx" in extensions, (
            "Frontend config must include .ts or .tsx extensions"
        )

    def test_homeassistant_frontend_uses_typescript_profile(self) -> None:
        """homeassistant_frontend config uses typescript profile for adapter selection."""
        import yaml

        config_path = Path(
            "configs/stage_1_discovery/examples/homeassistant_frontend.yaml"
        )
        config_data = yaml.safe_load(config_path.read_text())

        # Profile should be typescript to force TypeScriptAdapter
        assert config_data.get("profile") == "typescript", (
            "Frontend config should use profile: typescript to get TypeScriptAdapter"
        )

    def test_homeassistant_frontend_static_repos_non_empty(self) -> None:
        """homeassistant_frontend config must have non-empty static_repos."""
        import yaml

        config_path = Path(
            "configs/stage_1_discovery/examples/homeassistant_frontend.yaml"
        )
        config_data = yaml.safe_load(config_path.read_text())

        static_repos = config_data.get("static_repos", [])
        assert len(static_repos) > 0, "static_repos must be non-empty"
        assert "home-assistant/frontend" in static_repos, (
            "Should include home-assistant/frontend repo"
        )
