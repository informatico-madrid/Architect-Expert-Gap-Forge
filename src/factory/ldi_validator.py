#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
LDI Validation and Example Type Assignment Module
===================================================
Handles Length Density Index validation and example type classification
for the data factory pipeline.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import Literal

from src.schemas.common import FragmentTypedDict

from .config import DIST_NOMINAL, DIST_CONTRAST, EVOL_LEVELS

logger = logging.getLogger(__name__)


# ======================================================================
# RESULT TYPES
# ======================================================================


@dataclass(slots=True, frozen=True)
class LDIResult:
    """Result of LDI (Length Density Index) validation.

    The LDI measures the ratio of generated code length to reasoning length,
    ensuring the model produces sufficient explanatory context.
    """

    is_valid: bool
    score: float
    reason: str


@dataclass(slots=True, frozen=True)
class ExampleTypeAssignment:
    """Assignment of example type and difficulty level.

    Determines whether a fragment should be generated as nominal (with
    difficulty), contrast (correction), or error_recovery example.
    """

    example_type: Literal["nominal", "contrast", "error_recovery"]
    difficulty: Literal["easy", "medium", "hard"] | None


# ======================================================================
# LDI VALIDATION
# ======================================================================


def validate_ldi(code_len: int, reasoning_len: int, subtype: str) -> LDIResult:
    """Validate code-to-reasoning Length Density Index.

    Args:
        code_len: Length of the generated code in characters.
        reasoning_len: Length of the reasoning/thinking block in characters.
        subtype: Fragment subtype (e.g., 'code', 'test', 'doc', 'jinja', 'yaml').

    Returns:
        LDIResult with validation status, computed score, and reason message.
    """
    if reasoning_len == 0:
        return LDIResult(is_valid=False, score=0.0, reason="Zero reasoning")

    ldi = round(code_len / reasoning_len, 3)

    if subtype in ("test", "doc", "jinja", "yaml"):
        if reasoning_len < 50:
            return LDIResult(
                is_valid=False,
                score=ldi,
                reason="Reasoning too short for doc/test/template",
            )
        return LDIResult(
            is_valid=True, score=ldi, reason="Pass (Doc/Test/Template Mode)"
        )

    k_factor = 1200
    base_threshold = 0.10
    dynamic_limit = base_threshold * (code_len / (code_len + k_factor))

    if code_len > 0 and code_len < 100 and ldi > 0.01:
        return LDIResult(
            is_valid=True, score=ldi, reason="Pass (Micro-Snippet Exception)"
        )

    if ldi < dynamic_limit:
        return LDIResult(
            is_valid=False,
            score=ldi,
            reason=f"Verbosity (LDI {ldi} < Dynamic {round(dynamic_limit, 3)})",
        )

    return LDIResult(
        is_valid=True,
        score=ldi,
        reason=f"Pass (Dynamic Threshold {round(dynamic_limit, 3)})",
    )


# ======================================================================
# EXAMPLE TYPE ASSIGNMENT
# ======================================================================


def assign_example_type(
    fragment: FragmentTypedDict,
    has_legacy: bool = False,
) -> ExampleTypeAssignment:
    """Assign an example type to the fragment based on distribution:
      50% nominal (easy/medium/hard), 30% contrast, 20% error_recovery

    Args:
        fragment: The fragment to classify.
        has_legacy: Whether the fragment contains legacy 2023/2024 patterns.

    Returns:
        ExampleTypeAssignment with type and optional difficulty.

    ANTI-SCHIZOPHRENIA FILTER:
    If has_legacy=True, the gold code contains 2023/2024 patterns.
    In that case we FORCE contrast or error_recovery (NEVER nominal),
    because in contrast/error_recovery the model MUST correct the legacy
    pattern, and Gold Injection is SKIPPED (model generates 2026 code).
    Assigning nominal with legacy gold = weight schizophrenia.
    """
    if has_legacy:
        # Legacy gold is PERFECT for teaching correction (contrast/error_recovery)
        # but TOXIC for nominal (think=2026 + gold=legacy = schizophrenia)
        if random.random() < 0.60:
            return ExampleTypeAssignment(example_type="contrast", difficulty=None)
        else:
            return ExampleTypeAssignment(example_type="error_recovery", difficulty=None)

    roll = random.random()
    if roll < DIST_NOMINAL:
        difficulty = random.choice(EVOL_LEVELS)
        return ExampleTypeAssignment(example_type="nominal", difficulty=difficulty)
    elif roll < DIST_NOMINAL + DIST_CONTRAST:
        return ExampleTypeAssignment(example_type="contrast", difficulty=None)
    else:
        return ExampleTypeAssignment(example_type="error_recovery", difficulty=None)


__all__ = [
    "LDIResult",
    "ExampleTypeAssignment",
    "validate_ldi",
    "assign_example_type",
]
