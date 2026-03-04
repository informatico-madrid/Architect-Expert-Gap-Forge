#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for curation converters.

Verifies RawRecord <-> CurationRecord conversion and minimal properties.
"""
from __future__ import annotations

from src.schemas.converters import curation_raw_to_record, curation_record_to_raw


def test_curation_raw_to_record_and_back():
    raw = {
        "id": "c1",
        "metadata": {
            "example_type": "curation",
            "curation": {"quality_score": 0.78},
        },
        "conversation": [
            {"role": "user", "content": "Hola"},
            {"role": "assistant", "content": "Hola, ¿en qué puedo ayudar?"},
        ],
    }

    cur = curation_raw_to_record(raw)
    assert isinstance(cur, dict)
    assert cur.get("record") is raw
    assert "_text" in cur and "Hola" in cur["_text"]
    assert "_qs" in cur and 0.0 <= cur["_qs"] <= 1.0

    back = curation_record_to_raw(cur)
    assert back["id"] == "c1"
    assert "conversation" in back and isinstance(back["conversation"], list)
