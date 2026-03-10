# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for the Python AST adapter.

These tests verify that the Python AST adapter correctly parses Python files
and extracts dependencies, preserving the behavior of the original
processor._extract_local_imports method.
"""

from __future__ import annotations

from pathlib import Path
from typing import List
import pytest

from src.utils.extractors.base import (
    Dependency,
    ParseError,
    ParseResult,
)
from src.utils.extractors.python_ast_adapter import PythonAstAdapter


@pytest.fixture
def adapter() -> PythonAstAdapter:
    """Create a PythonAstAdapter instance for testing."""
    return PythonAstAdapter()


@pytest.fixture
def fixtures_dir() -> Path:
    """Path to the test fixtures directory."""
    return Path(__file__).parent.parent / "fixtures" / "python_samples"


class TestPythonAstAdapter:
    """Test suite for PythonAstAdapter."""

    def test_parse_file_returns_parse_result(
        self, adapter: PythonAstAdapter, fixtures_dir: Path
    ) -> None:
        """parse_file should return a ParseResult with content and AST."""
        test_file = fixtures_dir / "simple_imports.py"
        result = adapter.parse_file(test_file)

        assert isinstance(result, ParseResult)
        assert result.file_path == test_file
        assert result.raw_content != ""
        assert result.ast_tree is not None

    def test_parse_file_reads_content(
        self, adapter: PythonAstAdapter, fixtures_dir: Path
    ) -> None:
        """parse_file should read the file content."""
        test_file = fixtures_dir / "simple_imports.py"
        result = adapter.parse_file(test_file)

        assert "import os" in result.raw_content
        assert "from requests import get, post" in result.raw_content

    def test_parse_file_has_ast_tree(
        self, adapter: PythonAstAdapter, fixtures_dir: Path
    ) -> None:
        """parse_file should return a valid AST tree."""
        import ast

        test_file = fixtures_dir / "simple_imports.py"
        result = adapter.parse_file(test_file)

        assert isinstance(result.ast_tree, ast.AST)

    def test_extract_dependencies_finds_stdlib(
        self, adapter: PythonAstAdapter, fixtures_dir: Path
    ) -> None:
        """extract_dependencies should find standard library imports."""
        test_file = fixtures_dir / "simple_imports.py"
        deps = adapter.extract_dependencies(test_file)

        dep_names = [d.name for d in deps]
        assert "os" in dep_names
        assert "sys" in dep_names

    def test_extract_dependencies_finds_external(
        self, adapter: PythonAstAdapter, fixtures_dir: Path
    ) -> None:
        """extract_dependencies should find external (third-party) imports."""
        test_file = fixtures_dir / "simple_imports.py"
        deps = adapter.extract_dependencies(test_file)

        external_deps = [d for d in deps if d.module_type == "external"]
        assert len(external_deps) > 0
        assert any(d.name == "requests" for d in external_deps)

    def test_extract_dependencies_finds_relative(
        self, adapter: PythonAstAdapter, fixtures_dir: Path
    ) -> None:
        """extract_dependencies should find relative imports."""
        test_file = fixtures_dir / "simple_imports.py"
        deps = adapter.extract_dependencies(test_file)

        relative_deps = [d for d in deps if d.module_type == "relative"]
        assert len(relative_deps) > 0
        # Relative imports should have source_module
        assert any(d.source_module is not None for d in relative_deps)

    def test_extract_dependencies_handles_nested_imports(
        self, adapter: PythonAstAdapter, fixtures_dir: Path
    ) -> None:
        """extract_dependencies should handle nested module imports."""
        test_file = fixtures_dir / "nested_imports.py"
        deps = adapter.extract_dependencies(test_file)

        dep_names = [d.name for d in deps]
        # Should find typing, dataclasses, ast, json
        assert "typing" in dep_names or "List" in str(deps)
        assert "dataclasses" in dep_names
        assert "ast" in dep_names

    def test_parse_file_raises_on_syntax_error(
        self, adapter: PythonAstAdapter, fixtures_dir: Path
    ) -> None:
        """parse_file should raise ParseError on syntax errors."""
        test_file = fixtures_dir / "syntax_error.py"

        with pytest.raises(ParseError) as exc_info:
            adapter.parse_file(test_file)

        assert test_file.name in str(exc_info.value)

    def test_extract_dependencies_returns_list(
        self, adapter: PythonAstAdapter, fixtures_dir: Path
    ) -> None:
        """extract_dependencies should return a list of Dependency."""
        test_file = fixtures_dir / "simple_imports.py"
        deps = adapter.extract_dependencies(test_file)

        assert isinstance(deps, list)
        assert all(isinstance(d, Dependency) for d in deps)

    def test_adapter_implements_protocol(self, adapter: PythonAstAdapter) -> None:
        """Adapter should implement the ExtractorAdapter protocol."""
        from src.utils.extractors.base import ExtractorAdapter

        assert isinstance(adapter, ExtractorAdapter)
