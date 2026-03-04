#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Regression test: loading persisted sample with legacy key `ha_standards`.

The code base removed the legacy `ha_standards` coupling; the loader now
strictly constructs `SampleRecord` and will raise a `TypeError` when an
unexpected key is present. This test asserts that behavior.
"""
from __future__ import annotations

import json
import pytest
from pathlib import Path

from src.audit.persistence import load_persisted_sample


def test_load_persisted_sample_with_ha_standards_key_raises_typeerror(tmp_path):
    payload = {
        "created_at": "2026-03-04T00:00:00Z",
        "sample_size": 1,
        "type_distribution": {"nominal": 1},
        "record_ids": ["r1"],
        "records": [
            {
                "id": "r1",
                "example_type": "nominal",
                "evol_difficulty": "low",
                "fragment_name": "frag.py",
                "source_file": "src/frag.py",
                "user_prompt": "Do X",
                "reference_response": "Response",
                "gold_injected": False,
                "ldi": 0.1,
                # Legacy key that should now be rejected by the loader
                "ha_standards": "MASTER_GUIDE: ...",
                "gap_analysis": "",
            }
        ],
    }

    p = tmp_path / "eval_sample.json"
    p.write_text(json.dumps(payload, ensure_ascii=False))

    with pytest.raises(TypeError):
        load_persisted_sample(str(tmp_path))
