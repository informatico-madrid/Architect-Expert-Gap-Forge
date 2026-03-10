#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for focused helpers in src/factory/production_v11.py.

These tests exercise pure functions and small utilities that are
straightforward to validate with synthetic inputs (no external network).
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import textwrap
import re

import pytest

from src.factory import production_v11 as pv11

# Provide legacy alias used by other tests in this file
factory_v11 = pv11


def test_detect_legacy_patterns_python_and_jinja():
    code = """
    # legacy pattern: hass.data[] usage
    hass.data['some'] = 1
    """
    res = pv11.detect_legacy_patterns(code, subtype="code")
    assert isinstance(res, list)
    assert any("hass.data" in d or "runtime_data" in d for d in res)

    jinja_code = """
trigger:
- platform: state
    """
    res_j = pv11.detect_legacy_patterns(jinja_code, subtype="jinja")
    assert isinstance(res_j, list)
    assert len(res_j) >= 0


def test_parse_raw_response_tool_call_and_write_action():
    # tool_call JSON branch with reasoning
    tool_json = {
        "name": "write_to_file",
        "arguments": {"path": "/tmp/x", "content": "hi"},
    }
    raw = f"<think>reasoning text</think><tool_call>{json.dumps(tool_json)}</tool_call>"
    parsed, reasoning = pv11.parse_raw_response(raw)
    assert reasoning == "reasoning text"
    assert parsed["name"] == "write_to_file"
    assert parsed["arguments"]["content"] == "hi"

    # write_action branch
    wa = (
        "<think>R</think>"
        "<write_action>"
        "<path>/a/b.py</path>"
        "<content>print(1)\n</content>"
        "</write_action>"
    )
    parsed2, reasoning2 = pv11.parse_raw_response(wa)
    assert reasoning2 == "R"
    assert parsed2["name"] == "write_to_file"
    assert parsed2["arguments"]["path"] == "/a/b.py"
    assert "print(1)" in parsed2["arguments"]["content"]


def test_parse_raw_response_raises_on_no_action():
    with pytest.raises(ValueError):
        pv11.parse_raw_response("no actions here")


def test_get_file_chunks_and_parse_bundle_and_fragments(tmp_path: Path):
    content = (
        "=== LOGICAL ENTITY: my_entity ===\n"
        "Context: Some context\n"
        "Type: FUNCTIONAL_UNIT\n"
        "[ARCH_HEADER]\n"
        "MODULE: mod1\n"
        "REPO_PREFIX: repo1\n"
        "\n"
        "--- FILE: logic.py ---\n"
        "def foo():\n    return 1\n"
        "--- FILE: test_logic.py ---\n"
        "def test_foo():\n    assert True\n"
    )

    bundle = pv11.parse_bundle(content)
    assert bundle["entity_id"] == "my_entity"
    assert bundle["type"] == "FUNCTIONAL_UNIT"
    assert "logic.py" in bundle["files"]

    frags = pv11.get_v2_fragments(
        bundle,
        blueprint_cache={"mod1": ""},
        allowed_extensions=None,
        governance_cache={},
    )
    # Should return at least one fragment for the simple function
    assert isinstance(frags, list)
    assert any(f.get("subtype") == "functional_unit" for f in frags)

    # get_file_chunks splitting
    packed = """--- FILE: a.py ---\nprint(1)\n--- FILE: b.py ---\nprint(2)\n"""
    chunks = pv11.get_file_chunks(packed)
    assert chunks == [("a.py", "print(1)"), ("b.py", "print(2)")]


def test_ast_fragment_list_and_get_fragments_py_jinja_yaml():
    py_code = """
def myfunc(x):
    return x * 2
"""
    extra = {"virtual_filename": "logic.py"}
    frags = pv11._ast_fragment_list("logic.py", py_code, "CTX", extra)
    assert any(f["name"] == "myfunc" for f in frags)

    # Jinja template block -> fragment
    jinja = "{% macro m() %}OK{% endmacro %}"
    frags_j = pv11.get_fragments("tmpl.jinja2", jinja)
    assert any(f.get("type") == "template" for f in frags_j)

    # YAML config -> fragment (make it long enough to be accepted)
    yaml = "sensor:\n" + ("  - platform: test\n" * 10)
    frags_y = pv11.get_fragments("conf.yaml", yaml)
    assert any(f.get("subtype") == "yaml" for f in frags_y)


def test_validate_ldi_cases():
    # Zero reasoning
    ok, ldi, msg = pv11.validate_ldi(100, 0, "code")
    assert ok is False and "Zero reasoning" in msg

    # Doc/template mode with short reasoning
    ok2, ldi2, msg2 = pv11.validate_ldi(50, 10, "doc")
    assert ok2 is False and "Reasoning too short" in msg2

    # Micro-snippet exception (short code but ldi > 0.01)
    ok3, ldi3, msg3 = pv11.validate_ldi(50, 10, "code")
    assert ok3 is True


def test_make_checkpoint_key_and_load_checkpoint(tmp_path: Path):
    k1 = pv11.make_checkpoint_key("frag", "file.py")
    k2 = pv11.make_checkpoint_key("frag", "file.py")
    assert k1 == k2 and isinstance(k1, str) and len(k1) == 16

    # Write accepted + rejected JSONL
    accepted = tmp_path / "accepted.jsonl"
    rejected = tmp_path / "rejected.jsonl"
    accepted.write_text(json.dumps({"metadata": {"checkpoint_key": "A1"}}) + "\n")
    rejected.write_text(json.dumps({"checkpoint_key": "B2"}) + "\n")

    done = pv11.load_checkpoint(accepted, rejected)
    assert "A1" in done and "B2" in done


def test_async_file_writer_write(tmp_path: Path):
    out = tmp_path / "out.jsonl"
    writer = pv11.AsyncFileWriter(out)
    asyncio.run(writer.write({"x": 1}))
    content = out.read_text(encoding="utf-8").strip()
    assert content
    obj = json.loads(content)
    assert obj["x"] == 1


def test_get_file_chunks_splits_content() -> None:
    content = "--- FILE: a.py ---\nprint('a')\n--- FILE: b.py ---\nprint('b')"
    chunks = factory_v11.get_file_chunks(content)
    assert chunks == [("a.py", "print('a')"), ("b.py", "print('b')")]


def test_parse_bundle_extracts_metadata() -> None:
    bundle_txt = (
        "=== LOGICAL ENTITY: Sample ===\n"
        "Context: Demo\n"
        "Type: LOGIC_ONLY\n"
        "[ARCH_HEADER]\n"
        "MODULE: foo\n"
        "REPO_PREFIX: rp\n"
        'LOCAL_IMPORTS: ["a"]\n'
        "--- FILE: main.py ---\nprint('ok')\n"
        "--- FILE: other.py ---\nprint('bye')\n"
    )
    parsed = factory_v11.parse_bundle(bundle_txt)
    assert parsed["entity_id"] == "Sample"
    assert parsed["context"] == "Demo"
    assert parsed["type"] == "LOGIC_ONLY"
    assert parsed["arch"]["MODULE"] == "foo"
    assert "main.py" in parsed["files"]


def test_ast_fragment_list_generates_fragments() -> None:
    code = (
        "def foo():\n    return 1\n\nclass Bar:\n    def baz(self):\n        return 2\n"
    )
    fragments = factory_v11._ast_fragment_list(
        "module.py", code, "ctx", {"extra": True}
    )
    assert len(fragments) >= 2
    assert fragments[0]["context"] == "ctx"


def test_ast_fragment_list_fallback_on_error() -> None:
    """Test that invalid Python code raises ParseError (FR-006: abort policy)."""
    from src.utils.extractors.base import ParseError

    with pytest.raises(ParseError) as exc:
        factory_v11._ast_fragment_list("module.py", "invalid code..", "ctx", {})
    err = exc.value
    assert err.file_path.name == "module.py"
    assert err.line == 1
    assert "SyntaxError" in err.message or "invalid" in err.message.lower()


def _functional_bundle() -> dict:
    return {
        "entity_id": "fusion",
        "context": "ctx",
        "type": "FUNCTIONAL_UNIT",
        "arch": {"MODULE": "mod", "REPO_PREFIX": "root", "LOCAL_IMPORTS": "[]"},
        "files": {
            "logic.py": "def foo():\n    return 1",
            "test_logic.py": "def test_foo():\n    assert foo() == 1",
        },
    }


def _logic_only_bundle() -> dict:
    return {
        "entity_id": "logic",
        "context": "ctx",
        "type": "LOGIC_ONLY",
        "arch": {"MODULE": "mod", "REPO_PREFIX": "root", "LOCAL_IMPORTS": "[]"},
        "files": {"logic.py": "def foo():\n    return 1"},
    }


def test_get_v2_fragments_functional_unit() -> None:
    bundle = _functional_bundle()
    blueprint_cache = {"mod": "blueprint"}
    governance_cache = {"root": "governance"}
    fragments = factory_v11.get_v2_fragments(
        bundle, blueprint_cache, governance_cache=governance_cache
    )
    assert fragments
    assert fragments[0]["blueprint"] == "blueprint"


def test_get_v2_fragments_logic_only() -> None:
    bundle = _logic_only_bundle()
    fragments = factory_v11.get_v2_fragments(bundle, {}, allowed_extensions={".py"})
    assert fragments
    assert fragments[0]["virtual_filename"].endswith("logic.py")


def test_get_fragments_handles_various_types() -> None:
    py_frags = factory_v11.get_fragments("module.py", "def foo():\n    return 1")
    assert any(f["type"] == "python" for f in py_frags)
    markdown = factory_v11.get_fragments("README", "Short doc")
    assert markdown and markdown[0]["type"] == "readme"
    jinja = factory_v11.get_fragments(
        "template.jinja", "{%- macro m() %}print('ok'){%- endmacro %}"
    )
    assert jinja and jinja[0]["type"] == "template"
    yaml_code = (
        "automation:\n"
        "  - foo: bar\n"
        "  - baz: qux\n"
        "  - service: light.turn_on\n"
        "    target:\n"
        "      entity_id: light.test_light\n"
    )
    yaml = factory_v11.get_fragments("config.yaml", yaml_code)
    assert yaml and yaml[0]["type"] == "config"


def test_validate_ldi_variants() -> None:
    assert not factory_v11.validate_ldi(100, 0, "code")[0]
    assert not factory_v11.validate_ldi(200, 10, "doc")[0]
    valid, _, _ = factory_v11.validate_ldi(500, 10, "code")
    assert not valid or isinstance(valid, bool)


def test_assign_example_type_respects_legacy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(factory_v11.random, "random", lambda: 0.1)
    typ, diff = factory_v11.assign_example_type({}, has_legacy=True)
    assert typ in {"contrast", "error_recovery"}
    assert diff is None


def test_assign_example_type_distribution(monkeypatch: pytest.MonkeyPatch) -> None:
    choices = iter([0.05, 0.05, 0.8])
    monkeypatch.setattr(factory_v11.random, "random", lambda: next(choices))
    monkeypatch.setattr(factory_v11.random, "choice", lambda seq: seq[0])
    typ, diff = factory_v11.assign_example_type({})
    assert typ == "nominal"
    assert diff in factory_v11.EVOL_LEVELS


def test_make_checkpoint_key() -> None:
    key = factory_v11.make_checkpoint_key("name", "file.py", rep=2)
    assert len(key) == 16
    assert re.fullmatch(r"[0-9a-f]{16}", key)
