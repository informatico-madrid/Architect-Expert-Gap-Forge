#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0
"""Added unit tests for selected helpers in src/curation/backtracking_rewriter.py."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.curation import backtracking_rewriter as br


def test_load_prompt_file_missing_raises(tmp_path: Path) -> None:
    missing = tmp_path / "no_such_prompt.txt"
    with pytest.raises(FileNotFoundError):
        br._load_prompt_file(None, str(missing))


def test_load_prompt_file_empty_raises(tmp_path: Path) -> None:
    empty = tmp_path / "empty.txt"
    empty.write_text("\n")
    with pytest.raises(ValueError):
        br._load_prompt_file(None, str(empty))


def test_load_prompt_file_returns_trimmed_content(tmp_path: Path) -> None:
    f = tmp_path / "prompt.txt"
    f.write_text("   hello prompt  \n")
    out = br._load_prompt_file(str(f), str(f))
    assert out == "hello prompt"
