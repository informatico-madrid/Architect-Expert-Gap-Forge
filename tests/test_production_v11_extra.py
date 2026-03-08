#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Extra unit tests for small production_v11 helpers not covered elsewhere."""

from __future__ import annotations

import json
from pathlib import Path

from src.factory import production_v11 as pv11


def test_make_and_load_checkpoint(tmp_path: Path) -> None:
    out = tmp_path / "out.jsonl"
    rej = tmp_path / "out_rejected.jsonl"

    k1 = pv11.make_checkpoint_key("fragA", "a.py")
    k2 = pv11.make_checkpoint_key("fragB", "b.py")

    rec1 = {"metadata": {"checkpoint_key": k1}}
    rec2 = {"checkpoint_key": k2}

    # Accepted file has a valid JSON line and a malformed line
    out.write_text(json.dumps(rec1) + "\n" + "notjson\n")
    rej.write_text(json.dumps(rec2) + "\n")

    seen = pv11.load_checkpoint(out, rej)
    assert k1 in seen and k2 in seen


def test_build_system_with_blueprint_appends_context() -> None:
    master = "Master Content"
    changelog = "Change log"
    blueprint = "MODULE BLUEPRINT"
    governance = "RULES: no legacy"

    s = pv11.build_system_with_blueprint(master, changelog, blueprint=blueprint, local_imports="[]", governance=governance)
    assert "MODULE BLUEPRINT" in s
    assert "RULES: no legacy" in s
    # suffix expected to be appended
    assert "NOMINAL" in s or "nominal" in s
