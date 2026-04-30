#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0
"""Added unit tests for selected pure helpers in src/factory/production_v11.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.factory import prompt_builder as pb_module
from src.factory.prompt_builder import (
    _render,
    build_system_nominal,
    detect_legacy_patterns,
    load_master_docs,
    load_taxonomy,
)
from src.factory import config


def test__render_substitutes_template() -> None:
    out = _render("Hello $name", name="Tester")
    assert out == "Hello Tester"


def test_detect_legacy_patterns_code() -> None:
    code = "hass.data['foo'] = 1\n"
    found = detect_legacy_patterns(code)
    assert any("entry.runtime_data" in d for d in found)


def test_detect_legacy_patterns_jinja() -> None:
    jinja = "trigger:\n  - platform: state\n"
    found = detect_legacy_patterns(jinja, subtype="jinja")
    assert found


def test_load_taxonomy_and_prompt(tmp_path: Path) -> None:
    # Save original globals to restore after test
    originals = {
        "_TAX": dict(pb_module._TAX),
        "HA_ERROR_TEMPLATES": list(pb_module.HA_ERROR_TEMPLATES),
        "LEGACY_2023_PATTERNS": list(pb_module.LEGACY_2023_PATTERNS),
        "JINJA_HA_ERROR_TEMPLATES": list(pb_module.JINJA_HA_ERROR_TEMPLATES),
        "JINJA_LEGACY_2023_PATTERNS": list(pb_module.JINJA_LEGACY_2023_PATTERNS),
        "THEORY_QUESTION_TEMPLATES": list(pb_module.THEORY_QUESTION_TEMPLATES),
        "TOOLS_DEFINITION": list(pb_module.TOOLS_DEFINITION),
    }
    try:
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

        pb_module.load_taxonomy(p)
        assert "prompts" in pb_module._TAX

        master, changelog = "MASTER", "CHANGELOG"
        out = build_system_nominal(master, changelog)
        assert "BASE" in out
    finally:
        # Restore original globals
        pb_module._TAX = originals["_TAX"]
        pb_module.HA_ERROR_TEMPLATES = originals["HA_ERROR_TEMPLATES"]
        pb_module.LEGACY_2023_PATTERNS = originals["LEGACY_2023_PATTERNS"]
        pb_module.JINJA_HA_ERROR_TEMPLATES = originals["JINJA_HA_ERROR_TEMPLATES"]
        pb_module.JINJA_LEGACY_2023_PATTERNS = originals["JINJA_LEGACY_2023_PATTERNS"]
        pb_module.THEORY_QUESTION_TEMPLATES = originals["THEORY_QUESTION_TEMPLATES"]
        pb_module.TOOLS_DEFINITION = originals["TOOLS_DEFINITION"]


def test_load_master_docs_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_master_docs(tmp_path)


def test_load_master_docs_success(tmp_path: Path) -> None:
    (tmp_path / config._MASTER_GUIDE_FILENAME).write_text("MASTER")
    (tmp_path / config._TECHNICAL_CHANGELOG_FILENAME).write_text("CHANGELOG")
    (tmp_path / config._JINJA_YAML_GUIDE_FILENAME).write_text("JINJA")
    m, c, j = load_master_docs(tmp_path)
    assert m == "MASTER"
    assert c == "CHANGELOG"
    assert j == "JINJA"
