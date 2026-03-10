#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for src/factory/production_v11.py.

Covers all pure (no-LLM) functions:
  - _render / detect_legacy_patterns / post_validate_output
  - make_checkpoint_key / load_checkpoint
  - parse_raw_response / get_file_chunks / parse_bundle / _ast_fragment_list
  - get_theory_fragments / load_master_docs / load_taxonomy
  - get_v2_fragments (with minimal fixtures)
"""

from __future__ import annotations

import hashlib
import json
import textwrap
from pathlib import Path

import pytest
import yaml

# ---------------------------------------------------------------------------
# Import module under test
# ---------------------------------------------------------------------------
import src.factory.production_v11 as v11


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture()
def minimal_taxonomy_yaml(tmp_path: Path) -> Path:
    """Write a minimal but structurally valid taxonomy YAML."""
    data = {
        "ha_error_templates": [
            {
                "error": "TemplateError: {entity} failed",
                "category": "enum_migration",
                "legacy_pattern": "TEMP_CELSIUS",
                "modern_fix": "UnitOfTemperature.CELSIUS",
            }
        ],
        "legacy_2023_patterns": [
            {
                "title": "hass.data legacy",
                "legacy_code": "hass.data['my_domain']",
                "modern_code": "entry.runtime_data",
                "explanation": "Use runtime_data instead.",
            }
        ],
        "jinja_ha_error_templates": [
            {
                "error": "Template error: old syntax",
                "category": "legacy_template",
                "context_type": "jinja",
                "legacy_pattern": "value_template:",
                "modern_fix": "state:",
            }
        ],
        "jinja_legacy_2023_patterns": [
            {
                "title": "singular trigger",
                "context_type": "yaml",
                "legacy_code": "trigger:",
                "modern_code": "triggers:",
                "explanation": "Changed in 2024.10.",
            }
        ],
        "theory_question_templates": [
            {
                "template": "Explain the concept of {section_title}.",
                "type": "concept",
            }
        ],
        "tools_definition": [
            {"name": "write_to_file", "description": "Write content to a file."}
        ],
        "prompts": {
            "system": {
                "python": {
                    "base": "System($master|$changelog|$tools_json)",
                    "nominal_suffix": " [nominal]",
                    "contrast_suffix": " [contrast]",
                    "error_recovery_suffix": " [error_recovery]",
                    "blueprint_context": " [blueprint:$blueprint|$local_imports]",
                    "governance_context": " [gov:$governance_rules]",
                },
                "jinja": {
                    "base": "Jinja($jinja_guide|$tools_json)",
                    "nominal_suffix": " [jinja_nominal]",
                    "contrast_suffix": " [jinja_contrast]",
                    "error_recovery_suffix": " [jinja_error]",
                },
                "theory": "Theory($master|$changelog)",
            },
            "user": {
                "python": {
                    "nominal_easy": "easy:$context|$virtual_filename|$name|$skeleton",
                    "nominal_medium": "medium:$context|$virtual_filename|$name|$skeleton",
                    "nominal_hard_anchor": "hard_anchor:$context|$virtual_filename|$name|$skeleton",
                    "nominal_hard_anchor_free": [
                        "hard_free:$context|$virtual_filename|$name|$skeleton"
                    ],
                    "contrast": "contrast:$context|$virtual_filename|$name|$skeleton|$legacy_code",
                    "error_recovery": "error:$context|$virtual_filename|$name|$skeleton|$error_msg",
                    "functional_unit": "fu:$context|$virtual_filename|$name|$skeleton",
                },
                "jinja": {
                    "nominal_easy": "jinja_easy:$context|$virtual_filename|$name|$skeleton",
                    "nominal_medium": "jinja_medium:$context|$virtual_filename|$name|$skeleton",
                    "nominal_hard": "jinja_hard:$context|$virtual_filename|$name|$skeleton",
                    "contrast": "jinja_contrast:$context|$virtual_filename|$name|$skeleton|$legacy_code",
                    "error_recovery": "jinja_error:$context|$virtual_filename|$name|$skeleton|$error_msg",
                },
            },
        },
    }
    path = tmp_path / "taxonomy.yaml"
    path.write_text(yaml.dump(data), encoding="utf-8")
    return path


@pytest.fixture()
def gap_dir_with_docs(tmp_path: Path) -> Path:
    """Create a fake gap_dir with the three required master documents."""
    gap = tmp_path / "Gap"
    gap.mkdir()
    (gap / "HA_MASTER_GUIDE_2026.md").write_text(
        "# HA Guide\nsome content", encoding="utf-8"
    )
    (gap / "technical_changelog_2026.md").write_text(
        "## Changelog\nbreaking change info", encoding="utf-8"
    )
    (gap / "HA_JINJA_YAML_GUIDE_2026.md").write_text(
        "## Jinja Guide\ntriggers:", encoding="utf-8"
    )
    return gap


# ===========================================================================
# _render
# ===========================================================================


class TestRender:
    def test_substitutes_simple_variable(self) -> None:
        result = v11._render("Hello $name!", name="World")
        assert result == "Hello World!"

    def test_leaves_json_braces_intact(self) -> None:
        template = '{"key": "value"} $var'
        result = v11._render(template, var="X")
        assert result == '{"key": "value"} X'

    def test_missing_variable_is_left_as_placeholder(self) -> None:
        # safe_substitute does not raise; unknown placeholders are kept.
        result = v11._render("$a and $b", a="one")
        assert "$b" in result
        assert "one" in result

    def test_empty_template(self) -> None:
        assert v11._render("") == ""


# ===========================================================================
# detect_legacy_patterns
# ===========================================================================


class TestDetectLegacyPatterns:
    def test_clean_code_returns_empty(self) -> None:
        code = textwrap.dedent("""\
            from homeassistant.components.sensor import SensorEntity
            class MySensor(SensorEntity):
                @property
                def native_value(self):
                    return self._coordinator.data.value
        """)
        assert v11.detect_legacy_patterns(code) == []

    def test_detects_hass_data_dict_pattern(self) -> None:
        code = "domain_data = hass.data['my_domain']"
        found = v11.detect_legacy_patterns(code)
        assert any("hass.data" in d for d in found)

    def test_detects_temp_celsius_constant(self) -> None:
        found = v11.detect_legacy_patterns("unit = TEMP_CELSIUS")
        assert any("TEMP_" in d for d in found)

    def test_detects_blocking_requests(self) -> None:
        found = v11.detect_legacy_patterns("resp = requests.get('http://example.com')")
        assert any("requests" in d for d in found)

    def test_detects_sync_update(self) -> None:
        found = v11.detect_legacy_patterns("def update(self):\n    pass")
        assert any("update" in d for d in found)

    def test_detects_self_state_assignment(self) -> None:
        found = v11.detect_legacy_patterns("self._state = 42")
        assert any("_state" in d for d in found)

    def test_detects_platform_schema(self) -> None:
        found = v11.detect_legacy_patterns("PLATFORM_SCHEMA = vol.Schema({})")
        assert any("PLATFORM_SCHEMA" in d for d in found)

    def test_jinja_subtype_triggers_jinja_detectors(self) -> None:
        code = "trigger:\n- platform: state"
        found = v11.detect_legacy_patterns(code, subtype="jinja")
        assert len(found) > 0

    def test_jinja_clean_template_empty(self) -> None:
        code = "triggers:\n  - trigger: state"
        found = v11.detect_legacy_patterns(code, subtype="jinja")
        assert isinstance(found, list)

    def test_yaml_subtype_uses_multiline_flag(self) -> None:
        """Singular 'action:' at start of line must be detected."""
        code = "action:\n  - service: light.turn_on"
        found = v11.detect_legacy_patterns(code, subtype="yaml")
        assert any("action" in d for d in found)


# ===========================================================================
# post_validate_output
# ===========================================================================


class TestPostValidateOutput:
    def test_clean_output_returns_empty(self) -> None:
        code = "{% if value %} {{ value }} {% endif %}"
        assert v11.post_validate_output(code, "nominal") == []

    def test_detects_none_in_template(self) -> None:
        code = "{{ None }}"
        found = v11.post_validate_output(code, "nominal")
        assert any("None" in d for d in found)

    def test_detects_as_timestamp(self) -> None:
        code = "{{ as_timestamp(now()) }}"
        found = v11.post_validate_output(code, "nominal")
        assert any("as_timestamp" in d for d in found)

    def test_detects_platform_template(self) -> None:
        code = "platform: template"
        found = v11.post_validate_output(code, "nominal")
        assert any("platform" in d for d in found)

    def test_multiple_toxic_patterns(self) -> None:
        code = "{{ None }}\n{{ as_timestamp(now()) }}"
        found = v11.post_validate_output(code, "nominal")
        assert len(found) >= 2


# ===========================================================================
# make_checkpoint_key
# ===========================================================================


class TestMakeCheckpointKey:
    def test_deterministic(self) -> None:
        k1 = v11.make_checkpoint_key("MySensor", "sensor.py")
        k2 = v11.make_checkpoint_key("MySensor", "sensor.py")
        assert k1 == k2

    def test_different_names_differ(self) -> None:
        k1 = v11.make_checkpoint_key("A", "f.py")
        k2 = v11.make_checkpoint_key("B", "f.py")
        assert k1 != k2

    def test_different_filenames_differ(self) -> None:
        k1 = v11.make_checkpoint_key("X", "a.py")
        k2 = v11.make_checkpoint_key("X", "b.py")
        assert k1 != k2

    def test_rep_parameter_changes_key(self) -> None:
        k0 = v11.make_checkpoint_key("X", "a.py", rep=None)
        k1 = v11.make_checkpoint_key("X", "a.py", rep=1)
        k2 = v11.make_checkpoint_key("X", "a.py", rep=2)
        assert k0 != k1
        assert k1 != k2

    def test_output_length_is_16(self) -> None:
        k = v11.make_checkpoint_key("MySensor", "sensor.py")
        assert len(k) == 16

    def test_output_is_hex(self) -> None:
        k = v11.make_checkpoint_key("MySensor", "sensor.py")
        int(k, 16)  # raises ValueError if not valid hex


# ===========================================================================
# load_checkpoint
# ===========================================================================


class TestLoadCheckpoint:
    def test_returns_empty_when_no_files(self, tmp_path: Path) -> None:
        done = v11.load_checkpoint(tmp_path / "out.jsonl", tmp_path / "rej.jsonl")
        assert done == set()

    def test_reads_accepted_checkpoint_key(self, tmp_path: Path) -> None:
        output = tmp_path / "out.jsonl"
        output.write_text(
            json.dumps({"metadata": {"checkpoint_key": "abc123"}}) + "\n",
            encoding="utf-8",
        )
        done = v11.load_checkpoint(output, tmp_path / "rej.jsonl")
        assert "abc123" in done

    def test_reads_rejected_checkpoint_key(self, tmp_path: Path) -> None:
        rejected = tmp_path / "rej.jsonl"
        rejected.write_text(
            json.dumps({"checkpoint_key": "rej456", "reason": "failed"}) + "\n",
            encoding="utf-8",
        )
        done = v11.load_checkpoint(tmp_path / "out.jsonl", rejected)
        assert "rej456" in done

    def test_reads_both_files(self, tmp_path: Path) -> None:
        output = tmp_path / "out.jsonl"
        rejected = tmp_path / "rej.jsonl"
        output.write_text(
            json.dumps({"metadata": {"checkpoint_key": "k1"}}) + "\n", encoding="utf-8"
        )
        rejected.write_text(
            json.dumps({"checkpoint_key": "k2"}) + "\n", encoding="utf-8"
        )
        done = v11.load_checkpoint(output, rejected)
        assert "k1" in done and "k2" in done

    def test_skips_invalid_json_lines(self, tmp_path: Path) -> None:
        output = tmp_path / "out.jsonl"
        output.write_text(
            "NOT JSON\n" + json.dumps({"metadata": {"checkpoint_key": "valid"}}) + "\n",
            encoding="utf-8",
        )
        done = v11.load_checkpoint(output, tmp_path / "rej.jsonl")
        assert "valid" in done

    def test_skips_records_without_key(self, tmp_path: Path) -> None:
        output = tmp_path / "out.jsonl"
        output.write_text(json.dumps({"id": "no_ck_key"}) + "\n", encoding="utf-8")
        done = v11.load_checkpoint(output, tmp_path / "rej.jsonl")
        assert len(done) == 0


# ===========================================================================
# parse_raw_response
# ===========================================================================


class TestParseRawResponse:
    def test_parses_write_action_block(self) -> None:
        text = textwrap.dedent("""\
            <think>my reasoning</think>
            <write_action>
            <path>sensor/my_sensor.py</path>
            <content>
            class MySensor: pass
            </content>
            </write_action>
        """)
        result, reasoning = v11.parse_raw_response(text)
        assert result["name"] == "write_to_file"
        assert result["arguments"]["path"] == "sensor/my_sensor.py"
        assert "MySensor" in result["arguments"]["content"]
        assert reasoning == "my reasoning"

    def test_parses_tool_call_fallback(self) -> None:
        payload = {
            "name": "write_to_file",
            "arguments": {"path": "a.py", "content": "x"},
        }
        text = f"<tool_call>{json.dumps(payload)}</tool_call>"
        result, reasoning = v11.parse_raw_response(text)
        assert result["name"] == "write_to_file"
        assert reasoning == ""

    def test_raises_on_missing_action_block(self) -> None:
        with pytest.raises(ValueError, match="No <write_action>"):
            v11.parse_raw_response("some plain text without any action block")

    def test_raises_on_missing_path_tag(self) -> None:
        text = "<write_action><content>x</content></write_action>"
        with pytest.raises(ValueError, match="Missing <path>"):
            v11.parse_raw_response(text)

    def test_raises_on_malformed_content_block(self) -> None:
        text = "<write_action><path>x.py</path></write_action>"
        with pytest.raises(ValueError, match="Malformed"):
            v11.parse_raw_response(text)

    def test_extracts_think_from_response(self) -> None:
        text = textwrap.dedent("""\
            <think>deep reasoning here</think>
            <write_action>
            <path>a.py</path>
            <content>pass</content>
            </write_action>
        """)
        _, reasoning = v11.parse_raw_response(text)
        assert "deep reasoning" in reasoning


# ===========================================================================
# get_file_chunks
# ===========================================================================


class TestGetFileChunks:
    def test_splits_two_files(self) -> None:
        content = (
            "--- FILE: sensor.py ---\nclass S: pass\n"
            "--- FILE: coordinator.py ---\nclass C: pass\n"
        )
        chunks = v11.get_file_chunks(content)
        assert len(chunks) == 2
        assert chunks[0] == ("sensor.py", "class S: pass")
        assert chunks[1] == ("coordinator.py", "class C: pass")

    def test_returns_empty_on_no_markers(self) -> None:
        assert v11.get_file_chunks("no markers here") == []

    def test_single_file(self) -> None:
        content = "--- FILE: only.py ---\nonly content\n"
        chunks = v11.get_file_chunks(content)
        assert len(chunks) == 1
        assert chunks[0][0] == "only.py"


# ===========================================================================
# parse_bundle
# ===========================================================================


class TestParseBundle:
    MODULE_BLUEPRINT_TXT = textwrap.dedent("""\
        === LOGICAL ENTITY: my_integration ===
        Context: Home Assistant HACS integration
        Type: MODULE_BLUEPRINT
        [MODULE_MAP]
        MODULE: my_mod
        REPO_PREFIX: my_repo
        [BUNDLE_END]
    """)

    FUNCTIONAL_UNIT_TXT = textwrap.dedent("""\
        === LOGICAL ENTITY: my_integration ===
        Context: HA 2026 sensor
        Type: FUNCTIONAL_UNIT
        [ARCH_HEADER]
        MODULE: ha_sensor
        REPO_PREFIX: my_repo
        --- FILE: sensor.py ---
        class MySensor: pass
        --- FILE: test_sensor.py ---
        def test_sensor(): pass
    """)

    GOVERNANCE_TXT = textwrap.dedent("""\
        === LOGICAL ENTITY: repo_rules ===
        Context: coding standards
        Type: GOVERNANCE_RULES
        [GOVERNANCE_HEADER]
        MODULE: rules
        REPO_PREFIX: my_repo
        [BUNDLE_END]
    """)

    def test_parses_entity_id(self) -> None:
        bundle = v11.parse_bundle(self.MODULE_BLUEPRINT_TXT)
        assert bundle["entity_id"] == "my_integration"

    def test_parses_type_module_blueprint(self) -> None:
        bundle = v11.parse_bundle(self.MODULE_BLUEPRINT_TXT)
        assert bundle["type"] == "MODULE_BLUEPRINT"

    def test_parses_context(self) -> None:
        bundle = v11.parse_bundle(self.FUNCTIONAL_UNIT_TXT)
        assert bundle["context"] == "HA 2026 sensor"

    def test_parses_arch_header(self) -> None:
        bundle = v11.parse_bundle(self.FUNCTIONAL_UNIT_TXT)
        assert bundle["arch"].get("MODULE") == "ha_sensor"

    def test_parses_files_in_functional_unit(self) -> None:
        bundle = v11.parse_bundle(self.FUNCTIONAL_UNIT_TXT)
        assert "sensor.py" in bundle["files"]
        assert "test_sensor.py" in bundle["files"]
        assert "MySensor" in bundle["files"]["sensor.py"]

    def test_parses_governance_header_fallback(self) -> None:
        bundle = v11.parse_bundle(self.GOVERNANCE_TXT)
        assert bundle["type"] == "GOVERNANCE_RULES"
        assert bundle["arch"].get("MODULE") == "rules"

    def test_empty_string_returns_safe_defaults(self) -> None:
        bundle = v11.parse_bundle("")
        assert bundle["entity_id"] == ""
        assert bundle["type"] == ""
        assert bundle["files"] == {}


# ===========================================================================
# _ast_fragment_list
# ===========================================================================


class TestAstFragmentList:
    def test_extracts_class_fragment(self) -> None:
        code = textwrap.dedent("""\
            import homeassistant

            class MySensor:
                def __init__(self): pass
                def native_value(self): return 42
        """)
        frags = v11._ast_fragment_list(
            "sensor.py", code, "test_ctx", {"virtual_filename": "sensor.py"}
        )
        names = [f["name"] for f in frags]
        assert "MySensor" in names

    def test_extracts_function_fragment(self) -> None:
        code = "def async_setup_entry(hass, entry): pass"
        frags = v11._ast_fragment_list(
            "sensor.py", code, "ctx", {"virtual_filename": "sensor.py"}
        )
        assert any(f["name"] == "async_setup_entry" for f in frags)

    def test_skeleton_contains_placeholder(self) -> None:
        code = "def my_func(): return 42"
        frags = v11._ast_fragment_list("f.py", code, "", {"virtual_filename": "f.py"})
        assert len(frags) == 1
        assert "Expert HA 2026 Implementation" in frags[0]["skeleton"]

    def test_original_contains_real_code(self) -> None:
        code = "def my_func(): return 42"
        frags = v11._ast_fragment_list("f.py", code, "", {"virtual_filename": "f.py"})
        assert "42" in frags[0]["original"] or "return 42" in frags[0]["original"]

    def test_invalid_python_raises_parse_error(self) -> None:
        """Test that invalid Python code raises ParseError instead of fallback."""
        from src.utils.extractors.base import ParseError

        with pytest.raises(ParseError) as exc:
            v11._ast_fragment_list(
                "bad.py", "def broken(::", "ctx", {"virtual_filename": "bad.py"}
            )
        err = exc.value
        assert "bad.py" in str(err.file_path)

    def test_extra_fields_propagated(self) -> None:
        extra = {"virtual_filename": "sensor.py", "context": "HA"}
        code = "def foo(): pass"
        frags = v11._ast_fragment_list("sensor.py", code, "ctx", extra)
        assert frags[0]["virtual_filename"] == "sensor.py"


# ===========================================================================
# get_theory_fragments
# ===========================================================================


class TestGetTheoryFragments:
    def test_extracts_sections_from_master(self) -> None:
        master = textwrap.dedent("""\
            # Introduction
            This is a long enough introduction section with more than 100 chars of content to be included in the fragments.

            ## CoordinatorEntity Pattern
            This section explains the coordinator pattern which is long enough to be included in the fragments list.
        """)
        frags = v11.get_theory_fragments(master, "")
        assert len(frags) >= 1
        names = [f["name"] for f in frags]
        assert any("CoordinatorEntity" in n for n in names)

    def test_skips_short_sections(self) -> None:
        master = "# Short\nSummary."
        frags = v11.get_theory_fragments(master, "")
        assert frags == []

    def test_fragment_has_required_keys(self) -> None:
        master = "# Concept\n" + "x" * 200
        frags = v11.get_theory_fragments(master, "")
        assert len(frags) >= 1
        frag = frags[0]
        for key in (
            "name",
            "type",
            "section_content",
            "original",
            "source_doc",
            "context",
            "virtual_filename",
        ):
            assert key in frag

    def test_processes_both_docs(self) -> None:
        master = "# M Section\n" + "m" * 200
        changelog = "# C Section\n" + "c" * 200
        frags = v11.get_theory_fragments(master, changelog)
        sources = {f["source_doc"] for f in frags}
        assert "MASTER_GUIDE" in sources
        assert "TECHNICAL_CHANGELOG" in sources


# ===========================================================================
# load_master_docs
# ===========================================================================


class TestLoadMasterDocs:
    def test_loads_three_files(self, gap_dir_with_docs: Path) -> None:
        master, changelog, jinja = v11.load_master_docs(gap_dir_with_docs)
        assert "HA Guide" in master
        assert "Changelog" in changelog
        assert "Jinja Guide" in jinja

    def test_raises_when_master_missing(self, tmp_path: Path) -> None:
        gap = tmp_path / "empty_gap"
        gap.mkdir()
        with pytest.raises(FileNotFoundError, match="Master Guide"):
            v11.load_master_docs(gap)

    def test_raises_when_changelog_missing(self, tmp_path: Path) -> None:
        gap = tmp_path / "partial"
        gap.mkdir()
        (gap / "HA_MASTER_GUIDE_2026.md").write_text("x", encoding="utf-8")
        with pytest.raises(FileNotFoundError, match="Technical Changelog"):
            v11.load_master_docs(gap)

    def test_raises_when_jinja_guide_missing(self, tmp_path: Path) -> None:
        gap = tmp_path / "partial2"
        gap.mkdir()
        (gap / "HA_MASTER_GUIDE_2026.md").write_text("x", encoding="utf-8")
        (gap / "technical_changelog_2026.md").write_text("y", encoding="utf-8")
        with pytest.raises(FileNotFoundError, match="Jinja"):
            v11.load_master_docs(gap)


# ===========================================================================
# load_taxonomy
# ===========================================================================


class TestLoadTaxonomy:
    def test_loads_module_globals(self, minimal_taxonomy_yaml: Path) -> None:
        v11.load_taxonomy(minimal_taxonomy_yaml)
        assert len(v11.HA_ERROR_TEMPLATES) == 1
        assert len(v11.LEGACY_2023_PATTERNS) == 1
        assert len(v11.JINJA_HA_ERROR_TEMPLATES) == 1
        assert len(v11.JINJA_LEGACY_2023_PATTERNS) == 1
        assert len(v11.THEORY_QUESTION_TEMPLATES) == 1
        assert len(v11.TOOLS_DEFINITION) == 1

    def test_tax_dict_has_prompts_key(self, minimal_taxonomy_yaml: Path) -> None:
        v11.load_taxonomy(minimal_taxonomy_yaml)
        assert "prompts" in v11._TAX

    def test_prompt_key_accessor_works_after_load(
        self, minimal_taxonomy_yaml: Path
    ) -> None:
        v11.load_taxonomy(minimal_taxonomy_yaml)
        result = v11._prompt("system.python.base")
        assert "$master" in result


# ===========================================================================
# get_v2_fragments
# ===========================================================================


class TestGetV2Fragments:
    def test_module_blueprint_returns_empty(self) -> None:
        bundle = {
            "type": "MODULE_BLUEPRINT",
            "arch": {},
            "files": {},
            "entity_id": "",
            "context": "",
        }
        frags = v11.get_v2_fragments(bundle, blueprint_cache={})
        assert frags == []

    def test_governance_rules_returns_empty(self) -> None:
        bundle = {
            "type": "GOVERNANCE_RULES",
            "arch": {},
            "files": {},
            "entity_id": "",
            "context": "",
        }
        frags = v11.get_v2_fragments(bundle, blueprint_cache={})
        assert frags == []

    def test_logic_only_produces_fragments(self) -> None:
        bundle = {
            "type": "LOGIC_ONLY",
            "entity_id": "test",
            "context": "HA sensor",
            "arch": {
                "MODULE": "ha_sensor",
                "REPO_PREFIX": "repo",
                "LOCAL_IMPORTS": "[]",
            },
            "files": {"sensor.py": "def async_setup_entry(hass, entry): pass\n"},
        }
        frags = v11.get_v2_fragments(bundle, blueprint_cache={})
        assert len(frags) >= 1

    def test_functional_unit_produces_fragments(self) -> None:
        bundle = {
            "type": "FUNCTIONAL_UNIT",
            "entity_id": "test",
            "context": "HA sensor",
            "arch": {
                "MODULE": "ha_sensor",
                "REPO_PREFIX": "repo",
                "LOCAL_IMPORTS": "[]",
            },
            "files": {
                "sensor.py": "class MySensor: pass",
                "test_sensor.py": "def test_sensor(): pass",
            },
        }
        frags = v11.get_v2_fragments(bundle, blueprint_cache={})
        assert len(frags) >= 1
        subtypes = {f.get("subtype") for f in frags}
        assert "functional_unit" in subtypes
