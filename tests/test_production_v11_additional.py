#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Additional unit coverage for production_v11 helper routines."""

from __future__ import annotations

import asyncio
import hashlib
import json
import random
import textwrap
from pathlib import Path
from typing import Any, Dict, List

import pytest
import yaml

from src.factory.production_v11 import (
    AsyncFileWriter,
    ProgressTracker,
    assign_example_type,
    build_system_contrast,
    build_system_contrast_jinja,
    build_system_error_recovery,
    build_system_error_recovery_jinja,
    build_system_nominal,
    build_system_nominal_jinja,
    build_system_theory,
    build_system_with_blueprint,
    build_user_contrast,
    build_user_contrast_jinja,
    build_user_error_recovery,
    build_user_error_recovery_jinja,
    build_user_functional_unit,
    build_user_nominal,
    build_user_nominal_jinja,
    detect_legacy_patterns,
    get_fragments,
    get_theory_fragments,
    get_v2_fragments,
    load_checkpoint,
    load_taxonomy,
    make_checkpoint_key,
    parse_bundle,
    parse_raw_response,
    post_validate_output,
    validate_ldi,
    get_file_chunks,
)


TAXONOMY_BODY: Dict[str, Any] = {
    "ha_error_templates": [
        {
            "context_type": "python",
            "error": "Error {entity} in {component} after {seconds}s: {literal}",
        }
    ],
    "legacy_2023_patterns": [
        {"legacy_code": "requests.get("},
    ],
    "jinja_ha_error_templates": [
        {
            "context_type": "jinja",
            "error": "Jinja failure in {template_source} at {automation}",
        }
    ],
    "jinja_legacy_2023_patterns": [
        {"legacy_code": "trigger:", "context_type": "jinja"},
    ],
    "theory_question_templates": [
        {"template": "Explain {section_title} with precision", "type": "explain"}
    ],
    "tools_definition": [{"name": "write_to_file", "description": "Writes files"}],
    "prompts": {
        "system": {
            "python": {
                "base": "PYTHON BASE $master $changelog",
                "nominal_suffix": "NOMINAL_SUFFIX",
                "contrast_suffix": "CONTRAST_SUFFIX",
                "error_recovery_suffix": "ERROR_SUFFIX",
                "blueprint_context": "BLUEPRINT CONTEXT $blueprint $local_imports",
                "governance_context": "GOVERNANCE CONTEXT $governance_rules",
            },
            "jinja": {
                "base": "JINJA BASE",
                "nominal_suffix": "JINJA NOMINAL",
                "contrast_suffix": "JINJA CONTRAST",
                "error_recovery_suffix": "JINJA ERROR",
            },
            "theory": "THEORY $master $changelog",
        },
        "user": {
            "python": {
                "nominal_easy": "NOMINAL EASY $context",
                "nominal_medium": "NOMINAL MEDIUM $context",
                "nominal_hard_anchor_free": ["HARD FREE $name"],
                "nominal_hard_anchor": "HARD ANCHOR $name",
                "contrast": "CONTRAST with $legacy_code",
                "error_recovery": "ERROR $error_msg",
                "functional_unit": "FUNCTIONAL_UNIT $context",
            },
            "jinja": {
                "nominal_easy": "JINJA NOMINAL EASY $context",
                "nominal_medium": "JINJA NOMINAL MEDIUM $context",
                "nominal_hard_anchor_free": ["JINJA HARD FREE $name"],
                "nominal_hard_anchor": "JINJA HARD ANCHOR $name",
                "contrast": "JINJA CONTRAST $legacy_code",
                "error_recovery": "JINJA ERROR $error_msg",
            },
        },
    },
}


@pytest.fixture(autouse=True)
def load_sample_taxonomy(tmp_path: Path) -> Path:
    path = tmp_path / "taxonomy.yaml"
    path.write_text(yaml.safe_dump(TAXONOMY_BODY))
    load_taxonomy(path)
    return path


def _make_fragment(subtype: str = "code", name: str = "fragment") -> Dict[str, Any]:
    return {
        "name": name,
        "context": "Context text",
        "virtual_filename": "file.py",
        "skeleton": "def stub(): pass",
        "original": "def stub(): pass",
        "subtype": subtype,
    }


def _make_bundle(bundle_type: str) -> Dict[str, Any]:
    return {
        "entity_id": "entity-1",
        "context": "Bundle context",
        "type": bundle_type,
        "arch": {
            "MODULE": "module_x",
            "REPO_PREFIX": "repo",
            "LOCAL_IMPORTS": "[]",
        },
        "files": {
            "logic.py": "def entry(): pass",
            "test_logic.py": "def test_entry(): assert True",
        },
    }


@pytest.mark.unit
class TestPromptBuilders:
    def test_system_prompts_contain_master_and_changelog(self) -> None:
        master = "MASTER"
        changelog = "CHANGE"
        assert "MASTER" in build_system_nominal(master, changelog)
        assert "CONTRAST" in build_system_contrast(master, changelog)
        assert "ERROR_SUFFIX" in build_system_error_recovery(master, changelog)
        assert "BLUEPRINT" in build_system_with_blueprint(
            master, changelog, blueprint="B", governance="G"
        )
        assert "JINJA NOMINAL" in build_system_nominal_jinja("guide")
        assert "JINJA CONTRAST" in build_system_contrast_jinja("guide")
        assert "JINJA ERROR" in build_system_error_recovery_jinja("guide")

    def test_user_prompts_render_templates(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        frag = _make_fragment()
        assert "NOMINAL EASY" in build_user_nominal(frag, "easy")
        assert "NOMINAL MEDIUM" in build_user_nominal(frag, "medium")
        monkeypatch.setattr(random, "random", lambda: 0.1)
        assert "HARD FREE" in build_user_nominal(frag, "hard")
        monkeypatch.setattr(random, "random", lambda: 0.8)
        assert "HARD ANCHOR" in build_user_nominal(frag, "hard")
        assert "CONTRAST" in build_user_contrast(frag)
        assert "ERROR" in build_user_error_recovery(frag)
        assert "FUNCTIONAL_UNIT" in build_user_functional_unit(frag)
        vfrag = {**frag, "subtype": "jinja", "virtual_filename": "template.jinja"}
        assert "JINJA NOMINAL EASY" in build_user_nominal_jinja(vfrag, "easy")
        assert "JINJA NOMINAL MEDIUM" in build_user_nominal_jinja(vfrag, "medium")
        monkeypatch.setattr(random, "random", lambda: 0.2)
        assert "JINJA HARD FREE" in build_user_nominal_jinja(vfrag, "hard")
        monkeypatch.setattr(random, "random", lambda: 0.9)
        assert "JINJA HARD ANCHOR" in build_user_nominal_jinja(vfrag, "hard")
        assert "JINJA CONTRAST" in build_user_contrast_jinja(vfrag)
        assert "JINJA ERROR" in build_user_error_recovery_jinja(vfrag)


@pytest.mark.unit
class TestLegacyAndValidation:
    def test_detects_code_and_template_patterns(self) -> None:
        assert detect_legacy_patterns("requests.get(")
        assert detect_legacy_patterns("trigger:", subtype="jinja")

    def test_post_validate_output_flags_poison(self) -> None:
        toxins = post_validate_output("as_timestamp(", "contrast")
        assert "as_timestamp" in toxins[0]

    def test_validate_ldi_various_cases(self) -> None:
        ok, ldi, _ = validate_ldi(200, 100, "code")
        assert ok and ldi > 0
        valid, _, reason = validate_ldi(100, 20000, "code")
        assert not valid and "Verbosity" in reason
        doc_mode, _, msg = validate_ldi(5, 60, "doc")
        assert doc_mode and "Doc/Test/Template" in msg


@pytest.mark.unit
class TestParsingUtilities:
    def test_parse_raw_response_with_write_action(self) -> None:
        text = textwrap.dedent(
            """
            <think>reasoning</think>
            <write_action>
            <path>/tmp/out.py</path>
            <content>pass</content>
            </write_action>
            """
        )
        parsed, reasoning = parse_raw_response(text)
        assert parsed["arguments"]["path"] == "/tmp/out.py"
        assert reasoning == "reasoning"

    def test_parse_raw_response_falls_back_to_tool_call(self) -> None:
        text = '<think>reason</think><tool_call>{"name": "write"}</tool_call>'
        parsed, _ = parse_raw_response(text)
        assert parsed["name"] == "write"

    def test_get_file_chunks(self) -> None:
        content = "--- FILE: logic.py ---\nprint(1)\n--- FILE: test.py ---\nassert True"
        chunks = get_file_chunks(content)
        assert chunks[0][0] == "logic.py"
        assert chunks[1][0] == "test.py"

    def test_parse_bundle_parses_headers_and_files(self) -> None:
        raw = textwrap.dedent(
            """
            === LOGICAL ENTITY: sensors ===
            Context: sensors integration
            Type: FUNCTIONAL_UNIT
            [ARCH_HEADER]
            MODULE: sensors
            REPO_PREFIX: homeassistant
            LOCAL_IMPORTS: []
            --- FILE: logic.py ---
            def fn():
                pass
            --- FILE: test_logic.py ---
            def test_fn():
                pass
            """
        )
        parsed = parse_bundle(raw)
        assert parsed["entity_id"] == "sensors"
        assert "logic.py" in parsed["files"]

    def test_ast_and_fragment_generation(self) -> None:
        bundle = _make_bundle("FUNCTIONAL_UNIT")
        fragments = get_v2_fragments(
            bundle,
            {"module_x": "blueprint"},
            governance_cache={"repo": "gov"},
        )
        assert fragments
        logic_only = {
            **bundle,
            "type": "LOGIC_ONLY",
            "files": {"logic.py": "def fn(): pass"},
        }
        fragments = get_v2_fragments(
            logic_only,
            {"module_x": "blueprint"},
            governance_cache={"repo": "gov"},
        )
        assert fragments
        assert all("blueprint" in frag for frag in fragments)

    def test_get_fragments_for_formats(self) -> None:
        py = get_fragments("module.py", "def fn():\n    pass")
        assert any(f["type"] == "python" for f in py)
        jinja = get_fragments("template.jinja", "{%- macro m() %}{% endmacro %}")
        assert any(f["type"] == "template" for f in jinja)
        yaml_text = textwrap.dedent(
            """
            sensor:
              - platform: template
                value_template: '{{ value | float }}'
                friendly_name: 'Test Sensor'
            """
        )
        yaml_frag = get_fragments("config.yaml", yaml_text)
        assert any(f["type"] == "config" for f in yaml_frag)


@pytest.mark.unit
class TestCheckpointsAndIo:
    def test_checkpoint_key_and_load(self, tmp_path: Path) -> None:
        key = make_checkpoint_key("frag", "file.py")
        assert len(key) == 16
        accepted = tmp_path / "accepted.jsonl"
        rejected = tmp_path / "rejected.jsonl"
        accepted.write_text(json.dumps({"metadata": {"checkpoint_key": key}}) + "\n")
        rejected.write_text(json.dumps({"checkpoint_key": "other"}) + "\n")
        keys = load_checkpoint(accepted, rejected)
        assert key in keys and "other" in keys

    def test_async_writer_appends_record(self, tmp_path: Path) -> None:
        path = tmp_path / "out.jsonl"

        async def _write_once() -> None:
            writer = AsyncFileWriter(path)
            await writer.write({"foo": "bar"})

        asyncio.run(_write_once())
        data = path.read_text()
        assert "foo" in data

    def test_progress_tracker_records(self) -> None:
        tracker = ProgressTracker(2)

        async def _record_steps() -> None:
            await tracker.record("accepted", "nominal", "easy")
            await tracker.record("rejected", "contrast", None, gold_injected=False)

        asyncio.run(_record_steps())
        tracker.close()
        summary = tracker.summary()
        assert "Accepted" in summary and "Rejected" in summary


@pytest.mark.unit
class TestTheoryFragments:
    def test_theory_fragments_are_generated(self) -> None:
        master = "# Section 1\n" + "A" * 200
        changelog = "# Change 1\n" + "B" * 200
        fragments = get_theory_fragments(master, changelog)
        assert fragments
        assert all("source_doc" in frag for frag in fragments)
        theory_prompt = build_system_theory(master, changelog)
        assert "THEORY" in theory_prompt


@pytest.mark.unit
class TestAssignExampleType:
    def test_assigns_nominal_when_clean(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(random, "random", lambda: 0.25)
        monkeypatch.setattr(random, "choice", lambda seq: "medium")
        example_type, difficulty = assign_example_type(
            _make_fragment(), has_legacy=False
        )
        assert example_type == "nominal"
        assert difficulty == "medium"

    def test_forces_contrast_for_legacy(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(random, "random", lambda: 0.1)
        t, d = assign_example_type(_make_fragment(), has_legacy=True)
        assert t in {"contrast", "error_recovery"}
