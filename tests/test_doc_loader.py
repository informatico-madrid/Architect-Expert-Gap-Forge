#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for src/utils/doc_loader.py.

Covers:
- Happy-path: loads three files and returns correct content tuple
- FileNotFoundError with descriptive message for each missing file
- Path accepts both str and Path objects
- Loaded content matches what was written
- Empty files are valid (no error)
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.utils.doc_loader import load_master_docs

_MASTER = "HA_MASTER_GUIDE_2026.md"
_CHANGELOG = "technical_changelog_2026.md"
_JINJA = "HA_JINJA_YAML_GUIDE_2026.md"


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLoadMasterDocsHappyPath:
    def test_returns_three_strings(self, gap_dir: Path) -> None:
        result = load_master_docs(gap_dir)
        assert len(result) == 3
        assert all(isinstance(s, str) for s in result)

    def test_content_matches_written_files(self, gap_dir: Path) -> None:
        master, changelog, jinja = load_master_docs(gap_dir)
        assert "Master Guide" in master
        assert "Changelog" in changelog
        assert "Jinja" in jinja

    def test_accepts_string_path(self, gap_dir: Path) -> None:
        master, changelog, jinja = load_master_docs(str(gap_dir))
        assert master  # non-empty

    def test_accepts_path_object(self, gap_dir: Path) -> None:
        load_master_docs(gap_dir)  # must not raise

    def test_order_is_master_changelog_jinja(self, gap_dir: Path) -> None:
        """Return order must be: (master_guide, technical_changelog, jinja_guide)."""
        master, changelog, jinja = load_master_docs(gap_dir)
        assert "Master Guide" in master
        assert "Changelog" in changelog
        assert "Jinja" in jinja


# ---------------------------------------------------------------------------
# Missing files
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLoadMasterDocsMissingFiles:
    def test_raises_when_master_guide_missing(self, tmp_path: Path) -> None:
        d = tmp_path / "gap"
        d.mkdir()
        # Write only changelog and jinja
        (d / _CHANGELOG).write_text("changelog", encoding="utf-8")
        (d / _JINJA).write_text("jinja", encoding="utf-8")
        with pytest.raises(FileNotFoundError, match="Master Guide"):
            load_master_docs(d)

    def test_raises_when_changelog_missing(self, tmp_path: Path) -> None:
        d = tmp_path / "gap"
        d.mkdir()
        (d / _MASTER).write_text("master", encoding="utf-8")
        (d / _JINJA).write_text("jinja", encoding="utf-8")
        with pytest.raises(FileNotFoundError, match="Technical Changelog"):
            load_master_docs(d)

    def test_raises_when_jinja_guide_missing(self, tmp_path: Path) -> None:
        d = tmp_path / "gap"
        d.mkdir()
        (d / _MASTER).write_text("master", encoding="utf-8")
        (d / _CHANGELOG).write_text("changelog", encoding="utf-8")
        with pytest.raises(FileNotFoundError, match="Jinja"):
            load_master_docs(d)

    def test_raises_when_directory_does_not_exist(self, tmp_path: Path) -> None:
        phantom = tmp_path / "does_not_exist"
        with pytest.raises(FileNotFoundError):
            load_master_docs(phantom)

    def test_error_message_includes_path(self, tmp_path: Path) -> None:
        d = tmp_path / "empty_gap"
        d.mkdir()
        with pytest.raises(FileNotFoundError) as exc_info:
            load_master_docs(d)
        assert str(d) in str(exc_info.value) or _MASTER in str(exc_info.value)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLoadMasterDocsEdgeCases:
    def test_empty_files_are_valid(self, tmp_path: Path) -> None:
        d = tmp_path / "gap"
        d.mkdir()
        (d / _MASTER).write_text("", encoding="utf-8")
        (d / _CHANGELOG).write_text("", encoding="utf-8")
        (d / _JINJA).write_text("", encoding="utf-8")
        master, changelog, jinja = load_master_docs(d)
        assert master == ""
        assert changelog == ""
        assert jinja == ""

    def test_unicode_content_is_preserved(self, tmp_path: Path) -> None:
        d = tmp_path / "gap"
        d.mkdir()
        unicode_text = "# Guide\n\nConfigúración avanzada — β-version 🏠"
        (d / _MASTER).write_text(unicode_text, encoding="utf-8")
        (d / _CHANGELOG).write_text("ok", encoding="utf-8")
        (d / _JINJA).write_text("ok", encoding="utf-8")
        master, _, _ = load_master_docs(d)
        assert "β-version" in master
