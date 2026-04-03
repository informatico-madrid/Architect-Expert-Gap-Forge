# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for the ExtractorAdapter contract.

This test defines the expected interface and behavior of the ExtractorAdapter
Protocol. All extractors must conform to this contract.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from src.utils.extractors.base import (
    ExtractorAdapter,
    ParseError,
    Dependency,
    ParseResult,
)


class TestExtractorAdapterContract:
    """Test suite defining the ExtractorAdapter contract."""

    def test_extractor_adapter_is_protocol(self) -> None:
        """ExtractorAdapter should be a Protocol defining the interface."""
        # This test verifies the protocol exists and can be used for type checking
        assert hasattr(ExtractorAdapter, "__protocol_attrs__") or hasattr(
            ExtractorAdapter, "__annotations__"
        )

    def test_parse_file_returns_parse_result(self) -> None:
        """parse_file() must return a ParseResult with parsed content."""

        # Create a concrete implementation for testing
        class ConcreteAdapter(ExtractorAdapter):
            def parse_file(self, file_path: Path) -> ParseResult:
                return ParseResult(
                    file_path=file_path,
                    ast_tree=None,
                    raw_content="",
                    dependencies=(),
                )

            def extract_dependencies(self, file_path: Path) -> List[Dependency]:
                return []

        adapter = ConcreteAdapter()
        test_path = Path("/fake/path/test.py")
        result = adapter.parse_file(test_path)

        assert isinstance(result, ParseResult)
        assert result.file_path == test_path

    def test_extract_dependencies_returns_list(self) -> None:
        """extract_dependencies() must return a list of Dependency."""

        class ConcreteAdapter(ExtractorAdapter):
            def parse_file(self, file_path: Path) -> ParseResult:
                return ParseResult(
                    file_path=file_path,
                    ast_tree=None,
                    raw_content="",
                    dependencies=(),
                )

            def extract_dependencies(self, file_path: Path) -> List[Dependency]:
                return [
                    Dependency(
                        name="requests",
                        module_type="external",
                        source_module=None,
                    )
                ]

        adapter = ConcreteAdapter()
        deps = adapter.extract_dependencies(Path("test.py"))

        assert isinstance(deps, list)
        assert len(deps) == 1
        assert deps[0].name == "requests"
        assert deps[0].module_type == "external"

    def test_parse_error_has_required_fields(self) -> None:
        """ParseError must have file_path, line, and message fields."""
        error = ParseError(
            file_path=Path("test.py"),
            line=10,
            message="Syntax error in import statement",
        )

        assert error.file_path == Path("test.py")
        assert error.line == 10
        assert error.message == "Syntax error in import statement"

    def test_dependency_has_required_fields(self) -> None:
        """Dependency must have name, module_type, and optional source_module."""
        dep = Dependency(
            name="os",
            module_type="stdlib",
        )

        assert dep.name == "os"
        assert dep.module_type == "stdlib"
        assert dep.source_module is None

    def test_dependency_with_source_module(self) -> None:
        """Dependency should support source_module for relative imports."""
        dep = Dependency(
            name="helpers",
            module_type="relative",
            source_module="from . import helpers",
        )

        assert dep.source_module == "from . import helpers"
