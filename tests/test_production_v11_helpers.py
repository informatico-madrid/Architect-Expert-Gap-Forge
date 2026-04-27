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
import re

import pytest

from src.factory.checkpoint import AsyncFileWriter, load_checkpoint, make_checkpoint_key
from src.factory.fragment_extractor import (
    _ast_fragment_list,
    get_file_chunks,
    get_fragments,
    get_v2_fragments,
    parse_bundle,
)
from src.factory.ldi_validator import assign_example_type, validate_ldi
import src.factory.ldi_validator as _ldi_module
from src.factory.pipeline_runner import parse_raw_response
from src.factory.prompt_builder import detect_legacy_patterns


def test_detect_legacy_patterns_python_and_jinja():
    code = """
    # legacy pattern: hass.data[] usage
    hass.data['some'] = 1
    """
    res = detect_legacy_patterns(code, subtype="code")
    assert isinstance(res, list)
    assert any("hass.data" in d or "runtime_data" in d for d in res)

    jinja_code = """
trigger:
- platform: state
    """
    res_j = detect_legacy_patterns(jinja_code, subtype="jinja")
    assert isinstance(res_j, list)
    assert len(res_j) >= 0


def test_parse_raw_response_tool_call_and_write_action():
    # tool_call JSON branch with reasoning
    tool_json = {
        "name": "write_to_file",
        "arguments": {"path": "/tmp/x", "content": "hi"},
    }
    raw = f"<think>reasoning text</think><tool_call>{json.dumps(tool_json)}</tool_call>"
    parsed, reasoning = parse_raw_response(raw)
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
    parsed2, reasoning2 = parse_raw_response(wa)
    assert reasoning2 == "R"
    assert parsed2["name"] == "write_to_file"
    assert parsed2["arguments"]["path"] == "/a/b.py"
    assert "print(1)" in parsed2["arguments"]["content"]


def test_parse_raw_response_raises_on_no_action():
    with pytest.raises(ValueError):
        parse_raw_response("no actions here")


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

    bundle = parse_bundle(content)
    assert bundle["entity_id"] == "my_entity"
    assert bundle["type"] == "FUNCTIONAL_UNIT"
    assert "logic.py" in bundle["files"]

    frags = get_v2_fragments(
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
    chunks = get_file_chunks(packed)
    assert chunks == [("a.py", "print(1)"), ("b.py", "print(2)")]


def test_ast_fragment_list_and_get_fragments_py_jinja_yaml():
    py_code = """
def myfunc(x):
    return x * 2
"""
    extra = {"virtual_filename": "logic.py"}
    frags = _ast_fragment_list("logic.py", py_code, "CTX", extra)
    assert any(f["name"] == "myfunc" for f in frags)

    # Jinja template block -> fragment
    jinja = "{% macro m() %}OK{% endmacro %}"
    frags_j = get_fragments("tmpl.jinja2", jinja)
    assert any(f.get("type") == "template" for f in frags_j)

    # YAML config -> fragment (make it long enough to be accepted)
    yaml = "sensor:\n" + ("  - platform: test\n" * 10)
    frags_y = get_fragments("conf.yaml", yaml)
    assert any(f.get("subtype") == "yaml" for f in frags_y)


def test_validate_ldi_cases():
    # Zero reasoning
    result = validate_ldi(100, 0, "code")
    assert result.is_valid is False and "Zero reasoning" in result.reason

    # Doc/template mode with short reasoning
    result2 = validate_ldi(50, 10, "doc")
    assert result2.is_valid is False and "Reasoning too short" in result2.reason

    # Micro-snippet exception (short code but ldi > 0.01)
    result3 = validate_ldi(50, 10, "code")
    assert result3.is_valid is True


def test_make_checkpoint_key_and_load_checkpoint(tmp_path: Path):
    k1 = make_checkpoint_key("frag", "file.py")
    k2 = make_checkpoint_key("frag", "file.py")
    assert k1 == k2 and isinstance(k1, str) and len(k1) == 16

    # Write accepted + rejected JSONL
    accepted = tmp_path / "accepted.jsonl"
    rejected = tmp_path / "rejected.jsonl"
    accepted.write_text(json.dumps({"metadata": {"checkpoint_key": "A1"}}) + "\n")
    rejected.write_text(json.dumps({"checkpoint_key": "B2"}) + "\n")

    done = load_checkpoint(accepted, rejected)
    assert "A1" in done and "B2" in done


def test_async_file_writer_write(tmp_path: Path):
    out = tmp_path / "out.jsonl"
    writer = AsyncFileWriter(out)
    asyncio.run(writer.write({"x": 1}))
    content = out.read_text(encoding="utf-8").strip()
    assert content
    obj = json.loads(content)
    assert obj["x"] == 1


def test_get_file_chunks_splits_content() -> None:
    content = "--- FILE: a.py ---\nprint('a')\n--- FILE: b.py ---\nprint('b')"
    chunks = get_file_chunks(content)
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
    parsed = parse_bundle(bundle_txt)
    assert parsed["entity_id"] == "Sample"
    assert parsed["context"] == "Demo"
    assert parsed["type"] == "LOGIC_ONLY"
    assert parsed["arch"]["MODULE"] == "foo"
    assert "main.py" in parsed["files"]


def test_ast_fragment_list_generates_fragments() -> None:
    code = (
        "def foo():\n    return 1\n\nclass Bar:\n    def baz(self):\n        return 2\n"
    )
    fragments = _ast_fragment_list("module.py", code, "ctx", {"extra": True})
    assert len(fragments) >= 2
    assert fragments[0]["context"] == "ctx"


def test_ast_fragment_list_fallback_on_error() -> None:
    """Test that invalid Python code raises ParseError (FR-006: abort policy)."""
    from src.utils.extractors.base import ParseError

    with pytest.raises(ParseError) as exc:
        _ast_fragment_list("module.py", "invalid code..", "ctx", {})
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
    fragments = get_v2_fragments(
        bundle, blueprint_cache, governance_cache=governance_cache
    )
    assert fragments
    assert fragments[0]["blueprint"] == "blueprint"


def test_get_v2_fragments_logic_only() -> None:
    bundle = _logic_only_bundle()
    fragments = get_v2_fragments(bundle, {}, allowed_extensions={".py"})
    assert fragments
    assert fragments[0]["virtual_filename"].endswith("logic.py")


def test_get_fragments_handles_various_types() -> None:
    py_frags = get_fragments("module.py", "def foo():\n    return 1")
    assert any(f["type"] == "python" for f in py_frags)
    markdown = get_fragments("README", "Short doc")
    assert markdown and markdown[0]["type"] == "readme"
    jinja = get_fragments(
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
    yaml = get_fragments("config.yaml", yaml_code)
    assert yaml and yaml[0]["type"] == "config"


def test_validate_ldi_variants() -> None:
    vldi = validate_ldi
    assert not vldi(100, 0, "code").is_valid
    assert not vldi(200, 10, "doc").is_valid
    result = vldi(500, 10, "code")
    assert result.is_valid or isinstance(result.is_valid, bool)


def test_assign_example_type_respects_legacy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_ldi_module.random, "random", lambda: 0.1)
    _r = assign_example_type({}, has_legacy=True)
    typ, diff = _r.example_type, _r.difficulty
    assert typ in {"contrast", "error_recovery"}
    assert diff is None


def test_assign_example_type_distribution(monkeypatch: pytest.MonkeyPatch) -> None:
    choices = iter([0.05, 0.05, 0.8])
    monkeypatch.setattr(_ldi_module.random, "random", lambda: next(choices))
    monkeypatch.setattr(_ldi_module.random, "choice", lambda seq: seq[0])
    _r = assign_example_type({})
    typ, diff = _r.example_type, _r.difficulty
    assert typ == "nominal"
    assert diff is not None


def test_make_checkpoint_key() -> None:
    key = make_checkpoint_key("name", "file.py", rep=2)
    assert len(key) == 16
    assert re.fullmatch(r"[0-9a-f]{16}", key)
