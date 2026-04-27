#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for src/audit/judge.py utility functions."""

from __future__ import annotations


from src.audit.judge import _extract_code_blocks, _sanitize_for_logging


class TestExtractCodeBlocksJudge:
    """Tests for _extract_code_blocks function in judge.py."""

    def test_extract_single_code_block(self) -> None:
        """Should extract a single fenced code block."""
        text = "Some text\n```python\nprint('hello')\n```\nMore text"
        result = _extract_code_blocks(text)
        assert "print('hello')" in result

    def test_extract_multiple_code_blocks(self) -> None:
        """Should extract multiple fenced code blocks."""
        text = "```python\nx = 1\n```\n```yaml\nkey: value\n```"
        result = _extract_code_blocks(text)
        assert "x = 1" in result
        assert "key: value" in result

    def test_extract_no_code_blocks(self) -> None:
        """Should return empty string when no code blocks."""
        text = "Just plain text without code"
        result = _extract_code_blocks(text)
        assert result == ""

    def test_extract_with_language_specifier(self) -> None:
        """Should extract code blocks with language specifier."""
        text = "```javascript\nconst x = 42;\n```"
        result = _extract_code_blocks(text)
        assert "const x = 42;" in result


class TestSanitizeForLogging:
    """Tests for _sanitize_for_logging function."""

    def test_sanitize_empty_string(self) -> None:
        """Should return empty string for empty input."""
        result = _sanitize_for_logging("")
        assert result == ""

    def test_sanitize_none(self) -> None:
        """Should return empty string for None input."""
        result = _sanitize_for_logging(None)  # type: ignore
        assert result == ""

    def test_sanitize_short_text(self) -> None:
        """Should not truncate short text."""
        text = "short"
        result = _sanitize_for_logging(text)
        assert result == "short"

    def test_sanitize_long_text_truncates(self) -> None:
        """Should truncate long text with default max_length."""
        text = "a" * 300
        result = _sanitize_for_logging(text)
        assert len(result) <= 203  # 200 + "..."
        assert result.endswith("...")

    def test_sanitize_custom_max_length(self) -> None:
        """Should use custom max_length when provided."""
        text = "a" * 150
        result = _sanitize_for_logging(text, max_length=100)
        assert len(result) <= 103  # 100 + "..."
        assert result.endswith("...")

    def test_sanitize_replaces_newlines(self) -> None:
        """Should replace newlines with escaped version."""
        text = "line1\nline2\rline3"
        result = _sanitize_for_logging(text)
        assert "\n" not in result
        assert "\r" not in result
        assert "line1" in result
        assert "line2" in result

    def test_sanitize_preserves_content(self) -> None:
        """Should preserve the actual text content."""
        text = "Hello\nWorld"
        result = _sanitize_for_logging(text)
        assert "Hello" in result
        assert "World" in result
