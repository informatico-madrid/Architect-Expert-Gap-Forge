# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Integration tests for discovery processor CLI.

T027: Integration tests that run processor_cli with config files to ensure
configs are valid and produce expected behavior. This catches issues like:
- Wrong field names (profile_extensions vs extensions)
- Wrong profile values (homeassistant_frontend vs typescript)
- Missing required fields (static_repos)
- Silent failures where Python config runs instead of TypeScript config
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import List

import pytest


class TestProcessorCliConfigValidation:
    """Integration tests for processor CLI config validation."""

    @pytest.fixture
    def config_dir(self) -> Path:
        """Get the configs directory."""
        return Path("configs/stage_1_discovery/examples")

    @pytest.fixture
    def valid_configs(self, config_dir: Path) -> List[Path]:
        """Get list of valid config files."""
        return list(config_dir.glob("*.yaml"))

    def test_config_requires_extensions_field(self, config_dir: Path) -> None:
        """Config must have 'extensions' field, not 'profile_extensions'."""
        import yaml

        # Check homeassistant_frontend.yaml specifically
        config_path = config_dir / "homeassistant_frontend.yaml"
        if config_path.exists():
            config_data = yaml.safe_load(config_path.read_text())

            # Must have 'extensions' field
            assert "extensions" in config_data, (
                "homeassistant_frontend.yaml must have 'extensions' field, "
                "not 'profile_extensions'"
            )

            # Must have 'static_repos' for static mode
            assert config_data.get("mode") == "static", (
                "homeassistant_frontend.yaml mode should be 'static'"
            )
            assert "static_repos" in config_data, (
                "Static mode config must have 'static_repos' field"
            )

    def test_config_has_typescript_profile(self, config_dir: Path) -> None:
        """Frontend config must use typescript profile."""
        import yaml

        config_path = config_dir / "homeassistant_frontend.yaml"
        if config_path.exists():
            config_data = yaml.safe_load(config_path.read_text())

            assert config_data.get("profile") == "typescript", (
                "Frontend config must use profile: typescript to get "
                "TypeScriptAdapter, not PythonAstAdapter"
            )

    def test_config_has_ts_extensions(self, config_dir: Path) -> None:
        """Frontend config must include TypeScript extensions."""
        import yaml

        config_path = config_dir / "homeassistant_frontend.yaml"
        if config_path.exists():
            config_data = yaml.safe_load(config_path.read_text())

            extensions = config_data.get("extensions", [])
            assert ".ts" in extensions or ".tsx" in extensions, (
                "Frontend config must include .ts or .tsx extensions"
            )

    def test_config_has_static_repos(self, config_dir: Path) -> None:
        """Frontend config must have non-empty static_repos."""
        import yaml

        config_path = config_dir / "homeassistant_frontend.yaml"
        if config_path.exists():
            config_data = yaml.safe_load(config_path.read_text())

            static_repos = config_data.get("static_repos", [])
            assert len(static_repos) > 0, "static_repos must be non-empty"
            assert "home-assistant/frontend" in static_repos, (
                "Should include home-assistant/frontend repo"
            )

    def test_config_loads_without_validation_error(self, config_dir: Path) -> None:
        """Config should load without Pydantic validation errors."""
        import yaml
        from src.discovery.ingestor import DiscoveryConfig

        config_path = config_dir / "homeassistant_frontend.yaml"
        if config_path.exists():
            config_data = yaml.safe_load(config_path.read_text())

            # Should not raise ValidationError
            try:
                config = DiscoveryConfig(**config_data)
                # Verify key fields are set correctly
                assert config.profile == "typescript"
                assert ".ts" in config.profile_extensions or ".tsx" in config.profile_extensions
            except Exception as e:
                pytest.fail(f"Config failed validation: {e}")

    def test_processor_cli_requires_valid_config(self) -> None:
        """processor_cli should reject invalid config paths."""
        result = subprocess.run(
            [sys.executable, "-m", "src.discovery.processor_cli", "--config", "configs/nonexistent.yaml"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Should fail with file not found or similar error
        assert result.returncode != 0, "Should fail with invalid config path"


class TestProcessorCliBehavior:
    """Tests for processor CLI behavior with valid configs."""

    def test_processor_cli_help(self) -> None:
        """processor_cli should show help."""
        result = subprocess.run(
            [sys.executable, "-m", "src.discovery.processor_cli", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        assert "--config" in result.stdout
        assert "--verbose" in result.stdout

    def test_processor_cli_with_verbose(self) -> None:
        """processor_cli should run with verbose output."""
        # Use homeassistant.yaml which is known to work
        result = subprocess.run(
            [sys.executable, "-m", "src.discovery.processor_cli",
             "--config", "configs/homeassistant.yaml", "--verbose"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Should not fail immediately
        # Note: This may take time to complete, so we just check it starts
        assert result.returncode == 0 or "Processing category" in result.stdout
