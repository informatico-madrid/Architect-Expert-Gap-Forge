#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Architect-Expert-Gap-Forge (AEGF) - Training Configuration Validator

Validates Axolotl training configuration files, particularly NEFTune parameters.

SPDX-License-Identifier: Apache-2.0
Copyright 2026 AEGF
"""

from pathlib import Path

import yaml

from src.utils.exceptions import ConfigValidationError

NEFTUNE_MIN_ALPHA = 5
NEFTUNE_MAX_ALPHA = 15


def validate_axolotl_neftune(path: Path) -> None:
    """Validate that neftune_noise_alpha is within the allowed range [5, 15].

    Args:
        path: Path to the Axolotl YAML configuration file.

    Raises:
        ConfigValidationError: If neftune_noise_alpha is not in range [5, 15].
        FileNotFoundError: If the config file does not exist.
        yaml.YAMLError: If the YAML file is malformed.
    """
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    neftune_value = config.get("neftune_noise_alpha")

    if neftune_value is not None:
        if not isinstance(neftune_value, (int, float)):
            raise ConfigValidationError(
                f"neftune_noise_alpha={neftune_value} must be a number, got {type(neftune_value).__name__}"
            )

        if not (NEFTUNE_MIN_ALPHA <= neftune_value <= NEFTUNE_MAX_ALPHA):
            raise ConfigValidationError(
                f"neftune_noise_alpha={neftune_value} fuera del rango [{NEFTUNE_MIN_ALPHA}, {NEFTUNE_MAX_ALPHA}]"
            )
