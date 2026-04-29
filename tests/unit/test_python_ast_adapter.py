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
        # Should find all imports including nested: os.path -> os, json, typing, dataclasses
        assert "os" in dep_names
        assert "json" in dep_names
        assert "typing" in dep_names
        assert "dataclasses" in dep_names

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


class TestPythonAstAdapterRegexFallback:
    """Test suite for regex fallback extraction in PythonAstAdapter."""

    def test_extract_with_regex_relative_imports(
        self, adapter: PythonAstAdapter, tmp_path: Path
    ) -> None:
        """_extract_with_regex should extract relative imports."""
        # Create a file with relative imports
        # Note: The regex pattern r"from\s+(\.[.\w]*)\s+import" captures
        # relative paths like .sub, ..utils, etc. (not single dots)
        test_file = tmp_path / "relative_imports.py"
        test_file.write_text(
            "from .sub import module_a\n"
            "from ..utils import helper\n"
            "from ...package import something\n"
        )

        deps = adapter._extract_with_regex(test_file)

        # Should find relative imports (with .py suffix per the code)
        relative_deps = [d for d in deps if d.module_type == "relative"]
        assert len(relative_deps) > 0

    def test_extract_with_regex_regular_imports(
        self, adapter: PythonAstAdapter, tmp_path: Path
    ) -> None:
        """_extract_with_regex should extract regular imports."""
        test_file = tmp_path / "regular_imports.py"
        test_file.write_text(
            "import os\nimport sys\nimport requests\nimport numpy as np\n"
        )

        deps = adapter._extract_with_regex(test_file)

        dep_names = [d.name for d in deps]
        assert "os" in dep_names
        assert "sys" in dep_names
        assert "requests" in dep_names
        assert "numpy" in dep_names

    def test_extract_with_regex_mixed_imports(
        self, adapter: PythonAstAdapter, tmp_path: Path
    ) -> None:
        """_extract_with_regex should handle mixed import styles."""
        test_file = tmp_path / "mixed_imports.py"
        test_file.write_text(
            "import json\nfrom .local import something\nimport pandas\n"
        )

        deps = adapter._extract_with_regex(test_file)

        dep_names = [d.name for d in deps]
        assert "json" in dep_names
        assert "pandas" in dep_names
        # Relative imports should be detected
        relative_deps = [d for d in deps if d.module_type == "relative"]
        assert len(relative_deps) > 0

    def test_extract_with_regex_file_read_error(
        self, adapter: PythonAstAdapter, tmp_path: Path
    ) -> None:
        """_extract_with_regex should return empty list on file read error."""
        # Use a non-existent file
        nonexistent_file = tmp_path / "nonexistent.py"

        deps = adapter._extract_with_regex(nonexistent_file)

        assert deps == []

    def test_extract_with_regex_classifies_stdlib(
        self, adapter: PythonAstAdapter, tmp_path: Path
    ) -> None:
        """_extract_with_regex should classify stdlib modules correctly."""
        test_file = tmp_path / "stdlib_imports.py"
        test_file.write_text("import os\nimport sys\nimport json\n")

        deps = adapter._extract_with_regex(test_file)

        stdlib_deps = [d for d in deps if d.module_type == "stdlib"]
        dep_names = [d.name for d in stdlib_deps]
        assert "os" in dep_names
        assert "sys" in dep_names
        assert "json" in dep_names

    def test_extract_with_regex_classifies_external(
        self, adapter: PythonAstAdapter, tmp_path: Path
    ) -> None:
        """_extract_with_regex should classify external modules correctly."""
        test_file = tmp_path / "external_imports.py"
        test_file.write_text("import requests\nimport numpy\nimport torch\n")

        deps = adapter._extract_with_regex(test_file)

        external_deps = [d for d in deps if d.module_type == "external"]
        dep_names = [d.name for d in external_deps]
        assert "requests" in dep_names
        assert "numpy" in dep_names
        assert "torch" in dep_names

    def test_extract_with_regex_avoids_duplicates(
        self, adapter: PythonAstAdapter, tmp_path: Path
    ) -> None:
        """_extract_with_regex should not include duplicate dependencies."""
        test_file = tmp_path / "duplicate_imports.py"
        test_file.write_text(
            "import os\nimport os\nimport sys\nimport os as operating_system\n"
        )

        deps = adapter._extract_with_regex(test_file)

        # Should only have unique dependencies
        dep_names = [d.name for d in deps]
        assert dep_names.count("os") == 1
        assert dep_names.count("sys") == 1

    def test_classify_module_stdlib(self, adapter: PythonAstAdapter) -> None:
        """_classify_module should return 'stdlib' for known stdlib modules."""
        assert adapter._classify_module("os") == "stdlib"
        assert adapter._classify_module("sys") == "stdlib"
        assert adapter._classify_module("json") == "stdlib"
        assert adapter._classify_module("typing") == "stdlib"

    def test_classify_module_external(self, adapter: PythonAstAdapter) -> None:
        """_classify_module should return 'external' for known external modules."""
        assert adapter._classify_module("requests") == "external"
        assert adapter._classify_module("numpy") == "external"
        assert adapter._classify_module("pandas") == "external"
        assert adapter._classify_module("django") == "external"

    def test_classify_module_unknown(self, adapter: PythonAstAdapter) -> None:
        """_classify_module should return 'external' for unknown modules."""
        assert adapter._classify_module("unknown_module_xyz") == "external"
        assert adapter._classify_module("mystery_package") == "external"
