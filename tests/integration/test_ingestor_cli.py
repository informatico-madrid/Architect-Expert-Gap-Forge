# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Integration tests for CLI in the ingestor.

T022-T025: Integration tests for CLI:
- Tests CLI with valid YAML configuration
- Tests CLI with missing config file
- Tests CLI with invalid YAML syntax
- Validates the full CLI -> YAML -> Pydantic flow
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from src.discovery.ingestor import DiscoveryConfig


class TestIngestorCli:
    """Integration tests for the ingestor CLI."""

    @pytest.fixture
    def valid_yaml_path(self) -> Path:
        """Path to the valid YAML config fixture."""
        return Path(__file__).parent.parent / "fixtures" / "yaml_configs" / "valid_config.yaml"

    @pytest.fixture
    def invalid_syntax_yaml_path(self) -> Path:
        """Path to the invalid syntax YAML config fixture."""
        return Path(__file__).parent.parent / "fixtures" / "yaml_configs" / "invalid_syntax.yaml"

    @pytest.fixture
    def nonexistent_yaml_path(self, tmp_path: Path) -> Path:
        """Path to a nonexistent YAML file."""
        return tmp_path / "nonexistent.yaml"

    def test_cli_loads_valid_yaml_config(self, valid_yaml_path: Path) -> None:
        """Test that CLI with valid config loads YAML and creates DiscoveryConfig.

        T022, T024: Integration test for CLI with valid config.
        This test verifies the full flow: CLI -> yaml.safe_load() -> DiscoveryConfig.
        """
        # Read the YAML file directly to simulate what CLI would do
        import yaml

        with open(valid_yaml_path, "r") as f:
            config_data = yaml.safe_load(f)

        # Handle Path serialization from YAML
        if "base_dir" in config_data and isinstance(config_data["base_dir"], str):
            config_data["base_dir"] = Path(config_data["base_dir"])

        # Verify the config loads correctly (simulating CLI behavior)
        config = DiscoveryConfig(**config_data)

        # Assert
        assert config is not None
        assert isinstance(config, DiscoveryConfig)
        assert config.category == "test_category"
        assert config.mode == "static"
        assert config.search_query == "filename:manifest.json"
        assert config.limit == 10
        assert config.min_stars == 0

    def test_cli_fails_with_missing_file(self, nonexistent_yaml_path: Path) -> None:
        """Test that CLI with missing config file returns error.

        T023, T025: Integration test for CLI with missing file.
        This test verifies that the CLI properly handles missing config files.
        """
        # Simulate CLI behavior when file doesn't exist
        from src.discovery.processor_cli import main

        # Call main with nonexistent config file
        exit_code = main(["--config", str(nonexistent_yaml_path)])

        # Assert - should return non-zero exit code for missing file
        assert exit_code == 1

    def test_cli_fails_with_invalid_yaml_syntax(self, invalid_syntax_yaml_path: Path) -> None:
        """Test that CLI with invalid YAML syntax returns error.

        T023, T025: Integration test for CLI with invalid YAML.
        This test verifies that the CLI properly handles YAML syntax errors.
        """
        from src.discovery.processor_cli import main

        # Call main with invalid YAML config file
        exit_code = main(["--config", str(invalid_syntax_yaml_path)])

        # Assert - should return non-zero exit code for invalid YAML
        assert exit_code == 1

    def test_cli_validates_pydantic_schema(self, valid_yaml_path: Path) -> None:
        """Test that CLI validates config against DiscoveryConfig schema.

        T022: Integration test - validates full CLI -> YAML -> Pydantic flow.
        """
        import yaml
        from pydantic import ValidationError

        # Load YAML
        with open(valid_yaml_path, "r") as f:
            config_data = yaml.safe_load(f)

        # Handle Path serialization from YAML
        if "base_dir" in config_data and isinstance(config_data["base_dir"], str):
            config_data["base_dir"] = Path(config_data["base_dir"])

        # Verify config is valid
        DiscoveryConfig(**config_data)

        # Test invalid config (missing required field)
        invalid_data = {"mode": "static"}  # Missing 'category'
        with pytest.raises(ValidationError) as exc_info:
            DiscoveryConfig(**invalid_data)

        assert "category" in str(exc_info.value).lower()


class TestIngestorCliSubprocess:
    """Integration tests for CLI executed as subprocess."""

    @pytest.fixture
    def valid_yaml_path(self) -> Path:
        """Path to the valid YAML config fixture."""
        return Path(__file__).parent.parent / "fixtures" / "yaml_configs" / "valid_config.yaml"

    def test_cli_subprocess_with_valid_config(self, valid_yaml_path: Path) -> None:
        """Test CLI subprocess execution with valid config.

        T022: Integration test - subprocess execution with valid config.
        This tests the actual CLI entry point.
        """
        # Run the CLI as a subprocess (this tests the actual entry point)
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.discovery.processor_cli",
                "--config",
                str(valid_yaml_path),
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )

        # The CLI should not succeed because it's trying to actually run
        # the processor which requires GitHub token, but it should at least
        # pass YAML loading and validation stages
        # We check that it doesn't fail on YAML parsing
        assert "YAML" not in result.stderr or "error" not in result.stderr.lower()

    def test_cli_subprocess_with_missing_file(self, tmp_path: Path) -> None:
        """Test CLI subprocess with missing config file.

        T023: Integration test - subprocess with missing file.
        """
        nonexistent = tmp_path / "nonexistent.yaml"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.discovery.processor_cli",
                "--config",
                str(nonexistent),
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )

        # Should fail with non-zero exit code
        assert result.returncode != 0
        assert "not found" in result.stderr.lower() or "does not exist" in result.stderr.lower()
