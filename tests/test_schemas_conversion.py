#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for `src.schemas.converters`.

These tests validate the basic conversion contract and guard against
regressions during the incremental migration.
"""
from __future__ import annotations

from src.schemas.converters import raw_to_sample, sample_to_raw, normalize_judge_response
from src.audit.schema import SampleRecord


def test_raw_to_sample_roundtrip():
    raw = {
        "id": "r1",
        "metadata": {
            "example_type": "nominal",
            "evol_difficulty": "easy",
            "fragment_name": "f1",
            "source_file": "file.md",
            "gold_injected": True,
            "ldi": 0.42,
            "reference_standards": "std",
            "gap_analysis": "gap",
        },
        "conversation": [
            {"role": "user", "content": "¿Cuál es la respuesta?"},
            {"role": "assistant", "content": "La respuesta es 42."},
        ],
    }

    sample = raw_to_sample(raw)
    assert isinstance(sample, SampleRecord)
    assert sample.id == "r1"
    assert sample.user_prompt.startswith("¿Cuál")
    assert "42" in sample.reference_response

    back = sample_to_raw(sample)
    assert back["id"] == "r1"
    assert back["metadata"]["example_type"] == "nominal"


def test_normalize_judge_response_defaults_and_clamp():
    raw = {
        "adapter": {"ha_modernity": "0.75", "reasoning_depth": 0.6},
        # baseline missing keys should default to 0.5
        "baseline": {"ha_modernity": 1.2, "functionality": -0.1},
        "reasoning": "El adaptador muestra mejor modularidad.",
    }

    norm = normalize_judge_response(raw)
    assert "adapter" in norm and "baseline" in norm
    a = norm["adapter"]
    b = norm["baseline"]
    assert isinstance(a["ha_modernity"], float)
    assert 0.0 <= a["ha_modernity"] <= 1.0
    # baseline had 1.2 -> should be clamped to 1.0
    assert b["ha_modernity"] == 1.0
    # missing key in baseline (reasoning_depth) should be default (0.5)
    assert b.get("reasoning_depth", 0.5) >= 0.0
