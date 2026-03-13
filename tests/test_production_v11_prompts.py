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

from src.factory import prompt_builder as pb_module


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
            },
        }
    }
    monkeypatch.setattr(pb_module, "_TAX", taxonomy, raising=False)
    monkeypatch.setattr(
        pb_module, "TOOLS_DEFINITION", [{"name": "tool"}], raising=False
    )
    monkeypatch.setattr(
        pb_module,
        "LEGACY_2023_PATTERNS",
        [{"legacy_code": "hass.data[]", "context_type": "python"}],
        raising=False,
    )
    monkeypatch.setattr(
        pb_module,
        "HA_ERROR_TEMPLATES",
        [{"context_type": "python", "error": "Error {entity} at {component}"}],
        raising=False,
    )
    monkeypatch.setattr(
        pb_module,
        "THEORY_QUESTION_TEMPLATES",
        [{"template": "What is the essence of {section_title}?", "type": "theory"}],
        raising=False,
    )


def _restore_globals(originals: Dict[str, object]) -> None:
    for name, value in originals.items():
        setattr(pb_module, name, value)


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
        "theory_question_templates": [
            {"template": "Q {section_title}", "type": "doctrine"}
        ],
        "tools_definition": [{"name": "tool"}],
    }
    path = tmp_path / "taxonomy.yaml"
    path.write_text(yaml.safe_dump(payload))
    originals = {
        "_TAX": copy.deepcopy(pb_module._TAX),
        "HA_ERROR_TEMPLATES": list(pb_module.HA_ERROR_TEMPLATES),
        "LEGACY_2023_PATTERNS": list(pb_module.LEGACY_2023_PATTERNS),
        "JINJA_HA_ERROR_TEMPLATES": list(pb_module.JINJA_HA_ERROR_TEMPLATES),
        "JINJA_LEGACY_2023_PATTERNS": list(pb_module.JINJA_LEGACY_2023_PATTERNS),
        "THEORY_QUESTION_TEMPLATES": list(pb_module.THEORY_QUESTION_TEMPLATES),
        "TOOLS_DEFINITION": list(pb_module.TOOLS_DEFINITION),
    }
    try:
        pb_module.load_taxonomy(path)
        assert pb_module._TAX["prompts"]["system"]["python"]["base"] == "base"
        assert pb_module.LEGACY_2023_PATTERNS[0]["legacy_code"] == "legacy"
        assert pb_module.HA_ERROR_TEMPLATES[0]["error"] == "error"
        assert pb_module.THEORY_QUESTION_TEMPLATES[0]["type"] == "doctrine"
    finally:
        _restore_globals(originals)


def test_prompt_and_render_with_sample_taxonomy(minimal_taxonomy: None) -> None:
    base = pb_module._prompt("system.python.base")
    assert base == "[BASE]"
    formatted = pb_module._render("${name}", name="foo")
    assert formatted == "foo"


def test_load_master_docs_reads_expected_files(tmp_path: Path) -> None:
    for name, content in (
        ("HA_MASTER_GUIDE_2026.md", "guide"),
        ("technical_changelog_2026.md", "changelog"),
        ("HA_JINJA_YAML_GUIDE_2026.md", "jinja"),
    ):
        (tmp_path / name).write_text(content)
    master, changelog, jinja = pb_module.load_master_docs(tmp_path)
    assert master == "guide"
    assert changelog == "changelog"
    assert jinja == "jinja"


def test_load_master_docs_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        pb_module.load_master_docs(tmp_path)


def test_build_system_with_blueprint_appends_context(minimal_taxonomy: None) -> None:
    prompt = pb_module.build_system_with_blueprint(
        master="guide",
        changelog="changelog",
        blueprint="blueprint",
        local_imports='["dep"]',
        governance="rules",
    )
    assert "[BLUEPRINT" in prompt
    assert "[GOV" in prompt
    assert prompt.endswith("[NOMINAL]")


def test_build_user_nominal_hard_anchor_free(
    minimal_taxonomy: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    frag = _sample_frag()
    monkeypatch.setattr(pb_module.random, "random", lambda: 0.1)
    monkeypatch.setattr(pb_module.random, "choice", lambda choices: choices[0])
    prompt = pb_module.build_user_nominal(frag, difficulty="hard")
    assert "hard-free" in prompt


def test_build_user_contrast_uses_legacy_pattern(
    minimal_taxonomy: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    frag = _sample_frag()
    monkeypatch.setattr(
        pb_module.random, "choice", lambda seq: {"legacy_code": "legacy code"}
    )
    prompt = pb_module.build_user_contrast(frag)
    assert "legacy code" in prompt


def test_build_user_error_recovery_formats_message(
    minimal_taxonomy: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    frag = _sample_frag()
    monkeypatch.setattr(pb_module.random, "choice", lambda seq: seq[0])
    prompt = pb_module.build_user_error_recovery(frag)
    assert "error" in prompt


def test_get_theory_fragments_and_build(
    minimal_taxonomy: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    master = "# Section One\n" + "Long paragraph " * 20
    changelog = "## Change Log\n" + "Long paragraph " * 20
    fragments = pb_module.get_theory_fragments(master, changelog)
    assert fragments
    output, subtype = pb_module.build_user_theory(fragments[0])
    assert "Section" in output
    assert subtype == "theory"
