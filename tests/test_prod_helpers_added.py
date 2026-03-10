#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0
"""Added unit tests for selected pure helpers in src/factory/production_v11.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.factory import production_v11 as pv11


def test__render_substitutes_template() -> None:
    out = pv11._render("Hello $name", name="Tester")
    assert out == "Hello Tester"


def test_detect_legacy_patterns_code() -> None:
    code = "hass.data['foo'] = 1\n"
    found = pv11.detect_legacy_patterns(code)
    assert any("entry.runtime_data" in d for d in found)


def test_detect_legacy_patterns_jinja() -> None:
    jinja = "trigger:\n  - platform: state\n"
    found = pv11.detect_legacy_patterns(jinja, subtype="jinja")
    assert found


def test_load_taxonomy_and_prompt(tmp_path: Path) -> None:
    taxonomy = {
        "ha_error_templates": [],
        "legacy_2023_patterns": [],
        "jinja_ha_error_templates": [],
        "jinja_legacy_2023_patterns": [],
        "theory_question_templates": [],
        "tools_definition": [],
        "prompts": {
            "system": {
                "python": {
                    "base": "BASE $tools_json $master $changelog",
                    "nominal_suffix": "NOM",
                    "contrast_suffix": "CON",
                    "error_recovery_suffix": "ERR",
                }
            }
        },
    }
    p = tmp_path / "tax.yaml"
    p.write_text(json.dumps(taxonomy))

    pv11.load_taxonomy(p)
    assert "prompts" in pv11._TAX

    master, changelog = "MASTER", "CHANGELOG"
    out = pv11.build_system_nominal(master, changelog)
    assert "BASE" in out


def test_load_master_docs_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        pv11.load_master_docs(tmp_path)


def test_load_master_docs_success(tmp_path: Path) -> None:
    (tmp_path / pv11._MASTER_GUIDE_FILENAME).write_text("MASTER")
    (tmp_path / pv11._TECHNICAL_CHANGELOG_FILENAME).write_text("CHANGELOG")
    (tmp_path / pv11._JINJA_YAML_GUIDE_FILENAME).write_text("JINJA")
    m, c, j = pv11.load_master_docs(tmp_path)
    assert m == "MASTER"
    assert c == "CHANGELOG"
    assert j == "JINJA"
