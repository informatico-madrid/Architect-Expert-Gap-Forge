#!/usr/bin/env python3
# Copyright 2026 Bunker AI
# SPDX-License-Identifier: Apache-2.0
"""Test factories for anchor-dataset tests."""

from __future__ import annotations

from infrastructure.anchor_dataset.anchor_dataset_schema import AnchorRecord

_DEFAULTS: dict = {
    "id": "anchor_001_00",
    "domain": "home_assistant",
    "difficulty": "easy",
    "turn_count": 3,
    "legacy_pattern": "test_pattern",
    "domain_context": "test context",
    "expected_trajectory": "[ROLE:user]\ntest\n\n[ROLE:assistant]\ntool\n",
    "expected_tool_usage_patterns": [],
    "expected_coherence": 0.8,
    "expected_overall": 0.7,
    "expected_quality_score": 0.75,
    "expected_optimized_parameters": {},
    "verified": False,
    "verified_by": "",
}


def build_anchor_record(**overrides: object) -> AnchorRecord:
    """Build a valid AnchorRecord with optional field overrides.

    Merges *overrides* into sensible defaults so callers can freely
    change individual fields without needing to supply every argument.
    """
    data: dict = dict(_DEFAULTS)
    data.update(overrides)  # type: ignore[arg-type]
    return AnchorRecord(**data)  # type: ignore[arg-type]
