#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for src/factory/agentic_gen.py.

Covers all pure (no-LLM) functions:
  - _render / detect_legacy_patterns
  - make_checkpoint_key / load_checkpoint
  - get_file_chunks / get_fragments / validate_ldi
  - assign_example_type / extract_and_validate
  - ToolCallModel (Pydantic validation)
  - load_master_docs / load_taxonomy
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

import src.factory.agentic_gen as ag


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture()
def gap_dir_two_docs(tmp_path: Path) -> Path:
    """Create a minimal gap_dir with the two required master documents."""
    gap = tmp_path / "Gap"
    gap.mkdir()
    (gap / "HA_MASTER_GUIDE_2026.md").write_text(
        "# HA Guide 2026\ncontent", encoding="utf-8"
    )
    (gap / "technical_changelog_2026.md").write_text(
        "## Changelog\nbreaks", encoding="utf-8"
    )
    return gap


@pytest.fixture()
def minimal_agentic_taxonomy(tmp_path: Path) -> Path:
    """Write a minimal structurally valid agentic taxonomy YAML."""
    data = {
        "ha_error_templates": [
            {
                "error": "TemplateError in {component}",
                "category": "coordinator",
                "legacy_pattern": "hass.data",
                "modern_fix": "entry.runtime_data",
            }
        ],
        "legacy_2023_patterns": [
            {
                "title": "hass.data pattern",
                "legacy_code": "hass.data['domain']",
                "modern_code": "entry.runtime_data",
                "explanation": "Use runtime_data.",
            }
        ],
        "tools_definition": [
            {"name": "write_to_file", "description": "Write file", "parameters": {}}
        ],
        "prompts": {
            "system": {
                "base": "System base $master $changelog $tools_json",
                "nominal_suffix": " [nominal]",
                "contrast_suffix": " [contrast]",
                "error_recovery_suffix": " [error]",
            },
            "user": {
                "nominal_easy": "Easy $context $virtual_filename $name $skeleton",
                "nominal_medium": "Medium $context $virtual_filename $name $skeleton",
                "nominal_hard_anchor": "Hard $context $virtual_filename $name $skeleton",
                "nominal_hard_anchor_free": [
                    "Hard free $context $virtual_filename $name $skeleton"
                ],
                "contrast": "Contrast $context $virtual_filename $name $skeleton $legacy_code",
                "error_recovery": "Error $context $virtual_filename $name $skeleton $error_msg",
            },
        },
    }
    path = tmp_path / "agentic_taxonomy.yaml"
    path.write_text(yaml.dump(data), encoding="utf-8")
    return path


# ===========================================================================
# _render
# ===========================================================================


class TestRender:
    def test_basic_substitution(self) -> None:
        assert ag._render("Hello $name!", name="World") == "Hello World!"

    def test_safe_with_json_braces(self) -> None:
        result = ag._render('{"k": "v"} $x', x="OK")
        assert '{"k": "v"} OK' == result

    def test_unknown_placeholder_kept(self) -> None:
        result = ag._render("$a $b", a="1")
        assert "$b" in result

    def test_empty_string(self) -> None:
        assert ag._render("") == ""


# ===========================================================================
# detect_legacy_patterns
# ===========================================================================


class TestDetectLegacyPatterns:
    def test_clean_code_is_empty(self) -> None:
        code = textwrap.dedent("""\
            from homeassistant.components.sensor import SensorEntity
            class MySensor(SensorEntity):
                @property
                def native_value(self): return self._value
        """)
        assert ag.detect_legacy_patterns(code) == []

    def test_detects_hass_data(self) -> None:
        found = ag.detect_legacy_patterns("d = hass.data['domain']")
        assert any("hass.data" in d for d in found)

    def test_detects_temp_celsius(self) -> None:
        found = ag.detect_legacy_patterns("unit = TEMP_CELSIUS")
        assert any("TEMP_" in d for d in found)

    def test_detects_blocking_requests(self) -> None:
        found = ag.detect_legacy_patterns("requests.post('http://...')")
        assert any("requests" in d for d in found)

    def test_detects_singular_async_forward_entry_setup(self) -> None:
        code = "await hass.config_entries.async_forward_entry_setup(entry, 'sensor')"
        found = ag.detect_legacy_patterns(code)
        assert any("async_forward_entry_setup" in d for d in found)

    def test_detects_string_device_class(self) -> None:
        found = ag.detect_legacy_patterns("device_class='temperature'")
        assert any("device_class" in d for d in found)

    def test_detects_time_sleep(self) -> None:
        found = ag.detect_legacy_patterns("time.sleep(1)")
        assert any("sleep" in d for d in found)

    def test_returns_list_type(self) -> None:
        assert isinstance(ag.detect_legacy_patterns(""), list)


# ===========================================================================
# ToolCallModel (Pydantic validation)
# ===========================================================================


class TestToolCallModel:
    def test_valid_model(self) -> None:
        m = ag.ToolCallModel(
            name="write_to_file", arguments={"path": "a.py", "content": "x"}
        )
        assert m.name == "write_to_file"
        assert m.arguments["path"] == "a.py"

    def test_missing_name_raises(self) -> None:
        with pytest.raises(ValidationError):
            ag.ToolCallModel(arguments={"path": "x"})  # type: ignore[call-arg]

    def test_missing_arguments_raises(self) -> None:
        with pytest.raises(ValidationError):
            ag.ToolCallModel(name="write_to_file")  # type: ignore[call-arg]

    def test_arguments_can_be_empty_dict(self) -> None:
        m = ag.ToolCallModel(name="attempt_completion", arguments={})
        assert m.arguments == {}


# ===========================================================================
# make_checkpoint_key
# ===========================================================================


class TestMakeCheckpointKey:
    def test_deterministic(self) -> None:
        k1 = ag.make_checkpoint_key("MySensor", "sensor.py")
        k2 = ag.make_checkpoint_key("MySensor", "sensor.py")
        assert k1 == k2

    def test_different_inputs_differ(self) -> None:
        k1 = ag.make_checkpoint_key("A", "f.py")
        k2 = ag.make_checkpoint_key("B", "f.py")
        assert k1 != k2

    def test_rep_parameter_changes_key(self) -> None:
        k0 = ag.make_checkpoint_key("X", "a.py", rep=None)
        k1 = ag.make_checkpoint_key("X", "a.py", rep=1)
        assert k0 != k1

    def test_key_length_is_16(self) -> None:
        k = ag.make_checkpoint_key("Foo", "bar.py")
        assert len(k) == 16

    def test_key_is_valid_hex(self) -> None:
        k = ag.make_checkpoint_key("Foo", "bar.py")
        int(k, 16)


# ===========================================================================
# load_checkpoint
# ===========================================================================


class TestLoadCheckpoint:
    def test_empty_when_no_files(self, tmp_path: Path) -> None:
        done = ag.load_checkpoint(tmp_path / "out.jsonl", tmp_path / "rej.jsonl")
        assert done == set()

    def test_reads_accepted_key(self, tmp_path: Path) -> None:
        output = tmp_path / "out.jsonl"
        output.write_text(
            json.dumps({"metadata": {"checkpoint_key": "ck_accepted"}}) + "\n",
            encoding="utf-8",
        )
        done = ag.load_checkpoint(output, tmp_path / "rej.jsonl")
        assert "ck_accepted" in done

    def test_reads_rejected_key(self, tmp_path: Path) -> None:
        rejected = tmp_path / "rej.jsonl"
        rejected.write_text(
            json.dumps({"checkpoint_key": "ck_rejected"}) + "\n",
            encoding="utf-8",
        )
        done = ag.load_checkpoint(tmp_path / "out.jsonl", rejected)
        assert "ck_rejected" in done

    def test_combines_both_files(self, tmp_path: Path) -> None:
        output = tmp_path / "out.jsonl"
        rejected = tmp_path / "rej.jsonl"
        output.write_text(
            json.dumps({"metadata": {"checkpoint_key": "k_out"}}) + "\n",
            encoding="utf-8",
        )
        rejected.write_text(
            json.dumps({"checkpoint_key": "k_rej"}) + "\n", encoding="utf-8"
        )
        done = ag.load_checkpoint(output, rejected)
        assert "k_out" in done and "k_rej" in done

    def test_tolerates_invalid_json(self, tmp_path: Path) -> None:
        output = tmp_path / "out.jsonl"
        output.write_text(
            "INVALID\n"
            + json.dumps({"metadata": {"checkpoint_key": "valid_k"}})
            + "\n",
            encoding="utf-8",
        )
        done = ag.load_checkpoint(output, tmp_path / "rej.jsonl")
        assert "valid_k" in done


# ===========================================================================
# get_file_chunks
# ===========================================================================


class TestGetFileChunks:
    def test_splits_correctly(self) -> None:
        content = "--- FILE: a.py ---\ncode_a\n--- FILE: b.py ---\ncode_b\n"
        chunks = ag.get_file_chunks(content)
        assert len(chunks) == 2
        assert chunks[0] == ("a.py", "code_a")
        assert chunks[1] == ("b.py", "code_b")

    def test_empty_on_no_markers(self) -> None:
        assert ag.get_file_chunks("plain text") == []

    def test_single_file(self) -> None:
        chunks = ag.get_file_chunks("--- FILE: only.py ---\nonly\n")
        assert len(chunks) == 1
        assert chunks[0][0] == "only.py"


# ===========================================================================
# get_fragments
# ===========================================================================


class TestGetFragments:
    def test_extracts_python_class(self) -> None:
        code = "class MySensor:\n    def native_value(self): return 1"
        frags = ag.get_fragments("sensor.py", code)
        assert any(f["name"] == "MySensor" for f in frags)

    def test_extracts_python_function(self) -> None:
        code = "def async_setup_entry(hass, entry): pass"
        frags = ag.get_fragments("sensor.py", code)
        assert any(f["name"] == "async_setup_entry" for f in frags)

    def test_skeleton_has_placeholder(self) -> None:
        code = "def my_func(): return 42"
        frags = ag.get_fragments("f.py", code)
        assert any("Expert HA 2026 Implementation" in f["skeleton"] for f in frags)

    def test_test_file_subtype_is_test(self) -> None:
        code = "def test_sensor(): pass"
        frags = ag.get_fragments("test_sensor.py", code)
        assert any(f.get("subtype") == "test" for f in frags)

    def test_markdown_short_file(self) -> None:
        content = "# Heading\nsome docs"
        frags = ag.get_fragments("README.md", content)
        assert len(frags) >= 1

    def test_invalid_python_returns_empty(self) -> None:
        frags = ag.get_fragments("bad.py", "def broken(::")
        assert frags == []


# ===========================================================================
# validate_ldi
# ===========================================================================


class TestValidateLdi:
    def test_zero_reasoning_fails(self) -> None:
        ok, ldi, reason = ag.validate_ldi(
            code_len=200, reasoning_len=0, f_subtype="code"
        )
        assert not ok
        assert "Zero" in reason

    def test_doc_subtype_passes_with_sufficient_reasoning(self) -> None:
        ok, _, reason = ag.validate_ldi(
            code_len=500, reasoning_len=200, f_subtype="doc"
        )
        assert ok
        assert "Pass" in reason

    def test_doc_subtype_fails_with_tiny_reasoning(self) -> None:
        ok, _, reason = ag.validate_ldi(code_len=500, reasoning_len=10, f_subtype="doc")
        assert not ok

    def test_micro_snippet_exception(self) -> None:
        """Code < 100 chars with any LDI passes via micro-snippet exception."""
        ok, _, reason = ag.validate_ldi(
            code_len=50, reasoning_len=5000, f_subtype="code"
        )
        assert ok
        assert "Micro-Snippet" in reason

    def test_verbose_reasoning_fails_dynamic_threshold(self) -> None:
        """Very long reasoning relative to short code should fail."""
        ok, ldi, _ = ag.validate_ldi(
            code_len=200, reasoning_len=100_000, f_subtype="code"
        )
        assert not ok

    def test_balanced_code_passes(self) -> None:
        ok, _, _ = ag.validate_ldi(code_len=2000, reasoning_len=500, f_subtype="code")
        assert ok


# ===========================================================================
# assign_example_type
# ===========================================================================


class TestAssignExampleType:
    def test_has_legacy_never_nominal(self) -> None:
        for _ in range(50):
            etype, _ = ag.assign_example_type({}, has_legacy=True)
            assert etype != "nominal"

    def test_has_legacy_returns_contrast_or_error_recovery(self) -> None:
        types = {ag.assign_example_type({}, has_legacy=True)[0] for _ in range(50)}
        assert types.issubset({"contrast", "error_recovery"})

    def test_no_legacy_can_return_nominal(self) -> None:
        types = {ag.assign_example_type({}, has_legacy=False)[0] for _ in range(200)}
        assert "nominal" in types

    def test_nominal_returns_difficulty(self) -> None:
        for _ in range(50):
            etype, diff = ag.assign_example_type({}, has_legacy=False)
            if etype == "nominal":
                assert diff in ("easy", "medium", "hard")
                break


# ===========================================================================
# extract_and_validate
# ===========================================================================


class TestExtractAndValidate:
    def test_valid_tool_call(self) -> None:
        payload = json.dumps({"name": "write_to_file", "arguments": {"path": "a.py"}})
        text = f"<think>reasoning</think><tool_call>{payload}</tool_call>"
        model, reasoning = ag.extract_and_validate(text)
        assert model is not None
        assert model.name == "write_to_file"
        assert reasoning == "reasoning"

    def test_missing_tool_call_returns_none(self) -> None:
        model, reasoning = ag.extract_and_validate("<think>r</think> no tool call here")
        assert model is None

    def test_invalid_json_returns_none(self) -> None:
        model, _ = ag.extract_and_validate("<tool_call>NOT JSON</tool_call>")
        assert model is None

    def test_extracts_reasoning_from_think_tags(self) -> None:
        payload = json.dumps({"name": "x", "arguments": {}})
        text = f"<think>deep reasoning</think><tool_call>{payload}</tool_call>"
        _, reasoning = ag.extract_and_validate(text)
        assert "deep reasoning" in reasoning

    def test_extracts_reasoning_from_think_close_only(self) -> None:
        payload = json.dumps({"name": "x", "arguments": {}})
        text = f"some prefix</think><tool_call>{payload}</tool_call>"
        _, reasoning = ag.extract_and_validate(text)
        assert "some prefix" in reasoning


# ===========================================================================
# load_master_docs
# ===========================================================================


class TestLoadMasterDocs:
    def test_loads_two_files(self, gap_dir_two_docs: Path) -> None:
        master, changelog = ag.load_master_docs(gap_dir_two_docs)
        assert "HA Guide 2026" in master
        assert "Changelog" in changelog

    def test_raises_missing_master(self, tmp_path: Path) -> None:
        gap = tmp_path / "empty"
        gap.mkdir()
        with pytest.raises(FileNotFoundError, match="Master Guide"):
            ag.load_master_docs(gap)

    def test_raises_missing_changelog(self, tmp_path: Path) -> None:
        gap = tmp_path / "partial"
        gap.mkdir()
        (gap / "HA_MASTER_GUIDE_2026.md").write_text("x", encoding="utf-8")
        with pytest.raises(FileNotFoundError, match="Technical Changelog"):
            ag.load_master_docs(gap)


# ===========================================================================
# load_taxonomy
# ===========================================================================


class TestLoadTaxonomy:
    def test_populates_globals(self, minimal_agentic_taxonomy: Path) -> None:
        ag.load_taxonomy(minimal_agentic_taxonomy)
        assert len(ag.HA_ERROR_TEMPLATES) == 1
        assert len(ag.LEGACY_2023_PATTERNS) == 1
        assert len(ag.TOOLS_DEFINITION) == 1

    def test_tools_json_is_serialized(self, minimal_agentic_taxonomy: Path) -> None:
        ag.load_taxonomy(minimal_agentic_taxonomy)
        # _TOOLS_JSON is a JSON-serialized string
        parsed = json.loads(ag._TOOLS_JSON)
        assert isinstance(parsed, list)
        assert len(parsed) == 1

    def test_prompt_accessor_works_after_load(
        self, minimal_agentic_taxonomy: Path
    ) -> None:
        ag.load_taxonomy(minimal_agentic_taxonomy)
        result = ag._prompt("system.base")
        assert "$master" in result
