#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
UNIT TESTS: validate_axolotl_neftune for Axolotl config validation.

Tests cover:
- Valid neftune_noise_alpha within range [5, 15]
- Invalid values below minimum (raises ConfigValidationError)
- Invalid values above maximum (raises ConfigValidationError)
- Missing neftune_noise_alpha (passes)
- Non-numeric values (raises ConfigValidationError)
- File not found (raises FileNotFoundError)

Location: tests/training/test_config_validator.py
"""

from pathlib import Path

import pytest
import yaml

from src.training.config_validator import (
    NEFTUNE_MAX_ALPHA,
    NEFTUNE_MIN_ALPHA,
    validate_axolotl_neftune,
)
from src.utils.exceptions import ConfigValidationError


class TestValidateAxolotlNeftune:
    """Tests for validate_axolotl_neftune function."""

    def test_valid_neftune_min_boundary(self, tmp_path: Path) -> None:
        """Test that neftune_noise_alpha at minimum boundary (5) passes."""
        config = {"neftune_noise_alpha": NEFTUNE_MIN_ALPHA}
        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config, f)

        # Should not raise
        validate_axolotl_neftune(config_file)

    def test_valid_neftune_max_boundary(self, tmp_path: Path) -> None:
        """Test that neftune_noise_alpha at maximum boundary (15) passes."""
        config = {"neftune_noise_alpha": NEFTUNE_MAX_ALPHA}
        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config, f)

        # Should not raise
        validate_axolotl_neftune(config_file)

    def test_valid_neftune_middle_value(self, tmp_path: Path) -> None:
        """Test that neftune_noise_alpha in the middle (10) passes."""
        config = {"neftune_noise_alpha": 10}
        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config, f)

        # Should not raise
        validate_axolotl_neftune(config_file)

    def test_invalid_neftune_below_minimum(self, tmp_path: Path) -> None:
        """Test that neftune_noise_alpha below minimum raises ConfigValidationError."""
        config = {"neftune_noise_alpha": 4}
        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config, f)

        with pytest.raises(ConfigValidationError) as exc_info:
            validate_axolotl_neftune(config_file)

        assert "neftune_noise_alpha=4" in str(exc_info.value)
        assert "fuera del rango [5, 15]" in str(exc_info.value)

    def test_invalid_neftune_above_maximum(self, tmp_path: Path) -> None:
        """Test that neftune_noise_alpha above maximum raises ConfigValidationError."""
        config = {"neftune_noise_alpha": 16}
        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config, f)

        with pytest.raises(ConfigValidationError) as exc_info:
            validate_axolotl_neftune(config_file)

        assert "neftune_noise_alpha=16" in str(exc_info.value)
        assert "fuera del rango [5, 15]" in str(exc_info.value)

    def test_missing_neftune_noise_alpha(self, tmp_path: Path) -> None:
        """Test that missing neftune_noise_alpha passes validation."""
        config = {"num_epochs": 2, "learning_rate": 1e-5}
        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config, f)

        # Should not raise
        validate_axolotl_neftune(config_file)

    def test_invalid_neftune_non_numeric(self, tmp_path: Path) -> None:
        """Test that non-numeric neftune_noise_alpha raises ConfigValidationError."""
        config = {"neftune_noise_alpha": "ten"}
        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config, f)

        with pytest.raises(ConfigValidationError) as exc_info:
            validate_axolotl_neftune(config_file)

        assert "must be a number" in str(exc_info.value)

    def test_file_not_found(self, tmp_path: Path) -> None:
        """Test that non-existent file raises FileNotFoundError."""
        nonexistent = tmp_path / "nonexistent.yaml"

        with pytest.raises(FileNotFoundError):
            validate_axolotl_neftune(nonexistent)

    def test_valid_float_within_range(self, tmp_path: Path) -> None:
        """Test that float values within range pass validation."""
        config = {"neftune_noise_alpha": 7.5}
        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config, f)

        # Should not raise
        validate_axolotl_neftune(config_file)

    def test_invalid_float_out_of_range(self, tmp_path: Path) -> None:
        """Test that float values outside range raise ConfigValidationError."""
        config = {"neftune_noise_alpha": 4.9}
        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config, f)

        with pytest.raises(ConfigValidationError) as exc_info:
            validate_axolotl_neftune(config_file)

        assert "neftune_noise_alpha=4.9" in str(exc_info.value)

    def test_existing_homeassistant_config(self) -> None:
        """Test against the actual config.homeassistant.yaml file."""
        config_path = Path(
            "configs/stage_4_training/axolotl/config.homeassistant.yaml"
        )

        # This should pass since neftune_noise_alpha=10 is valid
        validate_axolotl_neftune(config_path)
