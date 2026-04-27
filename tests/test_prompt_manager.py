#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for src/audit/prompt_manager.py.

Covers:
- Happy-path load from a valid YAML file
- FileNotFoundError for non-existent paths
- system() / user_template() / format() accessors
- KeyError for unknown groups and missing keys
- groups() lists all loaded template groups
- Chained format() with multiple placeholders
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from src.audit.prompt_manager import PromptManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_prompts(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "prompts.yaml"
    p.write_text(textwrap.dedent(content), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPromptManagerConstruction:
    def test_loads_valid_yaml(self, prompts_yaml_path: Path) -> None:
        pm = PromptManager(prompts_yaml_path)
        assert "test_group" in pm.groups()

    def test_raises_file_not_found_for_missing_yaml(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent.yaml"
        with pytest.raises(FileNotFoundError, match="Prompt YAML not found"):
            PromptManager(missing)

    def test_accepts_string_path(self, prompts_yaml_path: Path) -> None:
        pm = PromptManager(str(prompts_yaml_path))
        assert len(pm.groups()) > 0

    def test_accepts_path_object(self, prompts_yaml_path: Path) -> None:
        pm = PromptManager(prompts_yaml_path)
        assert len(pm.groups()) > 0


# ---------------------------------------------------------------------------
# system()
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPromptManagerSystem:
    def test_returns_system_prompt(self, prompts_yaml_path: Path) -> None:
        pm = PromptManager(prompts_yaml_path)
        sys_prompt = pm.system("test_group")
        assert "test assistant" in sys_prompt.lower()

    def test_raises_key_error_for_unknown_group(self, prompts_yaml_path: Path) -> None:
        pm = PromptManager(prompts_yaml_path)
        with pytest.raises(KeyError, match="Unknown prompt group"):
            pm.system("does_not_exist")


# ---------------------------------------------------------------------------
# user_template()
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPromptManagerUserTemplate:
    def test_returns_raw_template_with_placeholders(
        self, prompts_yaml_path: Path
    ) -> None:
        pm = PromptManager(prompts_yaml_path)
        tmpl = pm.user_template("test_group")
        assert "{name}" in tmpl
        assert "{question}" in tmpl

    def test_raises_key_error_for_unknown_group(self, prompts_yaml_path: Path) -> None:
        pm = PromptManager(prompts_yaml_path)
        with pytest.raises(KeyError, match="Unknown prompt group"):
            pm.user_template("ghost_group")


# ---------------------------------------------------------------------------
# format()
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPromptManagerFormat:
    def test_substitutes_all_placeholders(self, prompts_yaml_path: Path) -> None:
        pm = PromptManager(prompts_yaml_path)
        result = pm.format("test_group", name="Alice", question="What is HA?")
        assert "Alice" in result
        assert "What is HA?" in result
        assert "{name}" not in result
        assert "{question}" not in result

    def test_raises_key_error_for_missing_placeholder(
        self, prompts_yaml_path: Path
    ) -> None:
        pm = PromptManager(prompts_yaml_path)
        with pytest.raises(KeyError):
            pm.format("test_group", name="Alice")  # missing 'question'

    def test_format_does_not_mutate_template(self, prompts_yaml_path: Path) -> None:
        pm = PromptManager(prompts_yaml_path)
        pm.format("test_group", name="A", question="Q")
        # Template must still contain placeholders after format() call
        tmpl = pm.user_template("test_group")
        assert "{name}" in tmpl


# ---------------------------------------------------------------------------
# groups()
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPromptManagerGroups:
    def test_returns_all_loaded_groups(self, prompts_yaml_path: Path) -> None:
        pm = PromptManager(prompts_yaml_path)
        groups = pm.groups()
        assert "test_group" in groups
        assert "another_group" in groups

    def test_returns_list(self, prompts_yaml_path: Path) -> None:
        pm = PromptManager(prompts_yaml_path)
        assert isinstance(pm.groups(), list)

    def test_group_count_matches_yaml(self, prompts_yaml_path: Path) -> None:
        pm = PromptManager(prompts_yaml_path)
        # conftest writes exactly 2 groups
        assert len(pm.groups()) == 2


# ---------------------------------------------------------------------------
# Edge: group with missing 'user' or 'system' key
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPromptManagerMissingKeys:
    def test_raises_key_error_when_system_key_absent(self, tmp_path: Path) -> None:
        p = _write_prompts(
            tmp_path,
            """\
            incomplete_group:
              user: "Only user template."
            """,
        )
        pm = PromptManager(p)
        with pytest.raises(KeyError, match="no 'system' template"):
            pm.system("incomplete_group")

    def test_raises_key_error_when_user_key_absent(self, tmp_path: Path) -> None:
        p = _write_prompts(
            tmp_path,
            """\
            incomplete_group:
              system: "Only system prompt."
            """,
        )
        pm = PromptManager(p)
        with pytest.raises(KeyError, match="no 'user' template"):
            pm.user_template("incomplete_group")
