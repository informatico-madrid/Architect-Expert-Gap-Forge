#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Prompt-building smoke tests for production_v11."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Dict

import pytest
import yaml

from src.factory import production_v11 as factory_v11


def _sample_frag() -> Dict[str, str]:
    return {
        "context": "Context block",
        "virtual_filename": "integration/fragment.py",
        "name": "SampleFragment",
        "skeleton": "def sample():\n    pass",
    }


@pytest.fixture
def minimal_taxonomy(monkeypatch: pytest.MonkeyPatch) -> None:
    taxonomy = {
        "prompts": {
            "system": {
                "python": {
                    "base": "[BASE]",
                    "nominal_suffix": "[NOMINAL]",
                    "contrast_suffix": "[CONTRAST]",
                    "error_recovery_suffix": "[ERROR]",
                    "blueprint_context": "[BLUEPRINT $blueprint IMPORTS $local_imports]",
                    "governance_context": "[GOV $governance]",
                },
                "jinja": {
                    "base": "[JINJA_BASE]",
                },
            },
            "user": {
                "python": {
                    "nominal_easy": "easy-$context",
                    "nominal_medium": "medium-$context",
                    "nominal_hard_anchor_free": ["hard-free-$name"],
                    "nominal_hard_anchor": "hard-anchor-$name",
                    "contrast": "contrast-$legacy_code",
                    "error_recovery": "error-$error_msg",
                    "functional_unit": "functional-$context",
                }
            }
        }
    }
    monkeypatch.setattr(factory_v11, "_TAX", taxonomy, raising=False)
    monkeypatch.setattr(factory_v11, "TOOLS_DEFINITION", [{"name": "tool"}], raising=False)
    monkeypatch.setattr(factory_v11, "LEGACY_2023_PATTERNS", [
        {"legacy_code": "hass.data[]", "context_type": "python"}
    ], raising=False)
    monkeypatch.setattr(factory_v11, "HA_ERROR_TEMPLATES", [
        {"context_type": "python", "error": "Error {entity} at {component}"}
    ], raising=False)
    monkeypatch.setattr(factory_v11, "THEORY_QUESTION_TEMPLATES", [
        {"template": "What is the essence of {section_title}?", "type": "theory"}
    ], raising=False)


def _restore_globals(originals: Dict[str, object]) -> None:
    for name, value in originals.items():
        setattr(factory_v11, name, value)


def test_load_taxonomy_updates_globals(tmp_path: Path) -> None:
    payload = {
        "prompts": {
            "system": {
                "python": {
                    "base": "base",
                }
            }
        },
        "ha_error_templates": [{"error": "error"}],
        "legacy_2023_patterns": [{"legacy_code": "legacy"}],
        "jinja_ha_error_templates": [{"error": "jinja error"}],
        "jinja_legacy_2023_patterns": [{"legacy_code": "jinja legacy"}],
        "theory_question_templates": [{"template": "Q {section_title}", "type": "doctrine"}],
        "tools_definition": [{"name": "tool"}],
    }
    path = tmp_path / "taxonomy.yaml"
    path.write_text(yaml.safe_dump(payload))
    originals = {
        "_TAX": copy.deepcopy(factory_v11._TAX),
        "HA_ERROR_TEMPLATES": list(factory_v11.HA_ERROR_TEMPLATES),
        "LEGACY_2023_PATTERNS": list(factory_v11.LEGACY_2023_PATTERNS),
        "JINJA_HA_ERROR_TEMPLATES": list(factory_v11.JINJA_HA_ERROR_TEMPLATES),
        "JINJA_LEGACY_2023_PATTERNS": list(factory_v11.JINJA_LEGACY_2023_PATTERNS),
        "THEORY_QUESTION_TEMPLATES": list(factory_v11.THEORY_QUESTION_TEMPLATES),
        "TOOLS_DEFINITION": list(factory_v11.TOOLS_DEFINITION),
    }
    try:
        factory_v11.load_taxonomy(path)
        assert factory_v11._TAX["prompts"]["system"]["python"]["base"] == "base"
        assert factory_v11.LEGACY_2023_PATTERNS[0]["legacy_code"] == "legacy"
        assert factory_v11.HA_ERROR_TEMPLATES[0]["error"] == "error"
        assert factory_v11.THEORY_QUESTION_TEMPLATES[0]["type"] == "doctrine"
    finally:
        _restore_globals(originals)


def test_prompt_and_render_with_sample_taxonomy(minimal_taxonomy: None) -> None:
    base = factory_v11._prompt("system.python.base")
    assert base == "[BASE]"
    formatted = factory_v11._render("${name}", name="foo")
    assert formatted == "foo"


def test_load_master_docs_reads_expected_files(tmp_path: Path) -> None:
    for name, content in (
        ("HA_MASTER_GUIDE_2026.md", "guide"),
        ("technical_changelog_2026.md", "changelog"),
        ("HA_JINJA_YAML_GUIDE_2026.md", "jinja"),
    ):
        (tmp_path / name).write_text(content)
    master, changelog, jinja = factory_v11.load_master_docs(tmp_path)
    assert master == "guide"
    assert changelog == "changelog"
    assert jinja == "jinja"


def test_load_master_docs_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        factory_v11.load_master_docs(tmp_path)


def test_build_system_with_blueprint_appends_context(minimal_taxonomy: None) -> None:
    prompt = factory_v11.build_system_with_blueprint(
        master="guide",
        changelog="changelog",
        blueprint="blueprint",
        local_imports="[\"dep\"]",
        governance="rules",
    )
    assert "[BLUEPRINT" in prompt
    assert "[GOV" in prompt
    assert prompt.endswith("[NOMINAL]")


def test_build_user_nominal_hard_anchor_free(minimal_taxonomy: None, monkeypatch: pytest.MonkeyPatch) -> None:
    frag = _sample_frag()
    monkeypatch.setattr(factory_v11.random, "random", lambda: 0.1)
    monkeypatch.setattr(factory_v11.random, "choice", lambda choices: choices[0])
    prompt = factory_v11.build_user_nominal(frag, difficulty="hard")
    assert "hard-free" in prompt


def test_build_user_contrast_uses_legacy_pattern(minimal_taxonomy: None, monkeypatch: pytest.MonkeyPatch) -> None:
    frag = _sample_frag()
    monkeypatch.setattr(factory_v11.random, "choice", lambda seq: {"legacy_code": "legacy code"})
    prompt = factory_v11.build_user_contrast(frag)
    assert "legacy code" in prompt


def test_build_user_error_recovery_formats_message(minimal_taxonomy: None, monkeypatch: pytest.MonkeyPatch) -> None:
    frag = _sample_frag()
    monkeypatch.setattr(factory_v11.random, "choice", lambda seq: seq[0])
    prompt = factory_v11.build_user_error_recovery(frag)
    assert "error" in prompt


def test_get_theory_fragments_and_build(minimal_taxonomy: None, monkeypatch: pytest.MonkeyPatch) -> None:
    master = "# Section One\n" + "Long paragraph " * 20
    changelog = "## Change Log\n" + "Long paragraph " * 20
    fragments = factory_v11.get_theory_fragments(master, changelog)
    assert fragments
    output, subtype = factory_v11.build_user_theory(fragments[0])
    assert "Section" in output
    assert subtype == "theory"
