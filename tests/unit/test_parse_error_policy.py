# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for parse error handling policies.

These tests verify that the parse error policies (abort, skip, fallback)
are correctly defined and handled by the extractor adapters.
"""

from __future__ import annotations

from pathlib import Path
import pytest

from src.utils.extractors.base import (
    OnParseErrorPolicy,
    ParseError,
)
from src.utils.extractors.python_ast_adapter import PythonAstAdapter


class TestParseErrorPolicy:
    """Tests for parse error policy constants."""

    def test_abort_policy_defined(self) -> None:
        """Test that ABORT policy is defined."""
        assert hasattr(OnParseErrorPolicy, "ABORT")
        assert OnParseErrorPolicy.ABORT == "abort"

    def test_skip_policy_defined(self) -> None:
        """Test that SKIP policy is defined."""
        assert hasattr(OnParseErrorPolicy, "SKIP")
        assert OnParseErrorPolicy.SKIP == "skip"

    def test_fallback_policy_defined(self) -> None:
        """Test that FALLBACK policy is defined."""
        assert hasattr(OnParseErrorPolicy, "FALLBACK")
        assert OnParseErrorPolicy.FALLBACK == "fallback"


class TestParseErrorHandling:
    """Tests for ParseError exception behavior."""

    def test_parse_error_message_format(self) -> None:
        """Test ParseError formats message correctly."""
        error = ParseError(
            file_path=Path("/test/file.py"),
            line=42,
            message="unexpected token",
        )
        assert str(error) == "ParseError in /test/file.py:42: unexpected token"

    def test_parse_error_equality(self) -> None:
        """Test ParseError equality based on fields."""
        error1 = ParseError(
            file_path=Path("/test/file.py"),
            line=10,
            message="syntax error",
        )
        error2 = ParseError(
            file_path=Path("/test/file.py"),
            line=10,
            message="syntax error",
        )
        assert error1 == error2

    def test_parse_error_immutable(self) -> None:
        """Test that ParseError is immutable (frozen dataclass)."""
        error = ParseError(
            file_path=Path("/test/file.py"),
            line=10,
            message="error",
        )
        with pytest.raises(AttributeError):
            error.message = "modified"

    def test_parse_error_is_exception(self) -> None:
        """Test ParseError can be raised and caught as Exception."""
        error = ParseError(
            file_path=Path("/test/file.py"),
            line=10,
            message="test error",
        )
        with pytest.raises(ParseError):
            raise error


class TestPythonAstAdapterParseError:
    """Tests for PythonAstAdapter parse error handling."""

    def test_parse_valid_file_no_error(self, tmp_path: Path) -> None:
        """Test parsing valid Python file doesn't raise."""
        test_file = tmp_path / "valid.py"
        test_file.write_text("import os\ndef hello():\n    pass\n")

        adapter = PythonAstAdapter()
        result = adapter.parse_file(test_file)

        assert result.file_path == test_file
        assert result.ast_tree is not None

    def test_parse_invalid_syntax_raises_parse_error(self, tmp_path: Path) -> None:
        """Test parsing invalid Python raises ParseError."""
        test_file = tmp_path / "invalid.py"
        test_file.write_text("def broken(\n    pass\n")  # Missing closing paren

        adapter = PythonAstAdapter()
        with pytest.raises(ParseError) as exc_info:
            adapter.parse_file(test_file)

        assert exc_info.value.file_path == test_file
        assert exc_info.value.line > 0

    def test_extract_dependencies_raises_parse_error_on_syntax_error(
        self, tmp_path: Path
    ) -> None:
        """Test extract_dependencies raises ParseError on syntax error (ParseError-first).

        Per the plan (FR-006), the adapter follows ParseError-first policy where
        parse errors are propagated to the caller (processor) which handles them
        according to the on_parse_error policy.
        """
        test_file = tmp_path / "broken.py"
        test_file.write_text("import os\ndef broken(\n    pass\n")  # Syntax error

        adapter = PythonAstAdapter()
        # extract_dependencies should raise ParseError - it no longer falls back to regex
        with pytest.raises(ParseError) as exc_info:
            adapter.extract_dependencies(test_file)

        assert exc_info.value.file_path == test_file

    def test_parse_nonexistent_file_raises_parse_error(self, tmp_path: Path) -> None:
        """Test parsing nonexistent file raises ParseError."""
        test_file = tmp_path / "nonexistent.py"

        adapter = PythonAstAdapter()
        with pytest.raises(ParseError) as exc_info:
            adapter.parse_file(test_file)

        assert "nonexistent.py" in str(exc_info.value.file_path)
