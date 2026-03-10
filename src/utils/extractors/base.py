# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Base types and interfaces for language extractors.

This module defines the core abstractions for the extractor adapter pattern:
- ParseError: Structured exception for parse failures
- Dependency: TypedDict representing an extracted dependency
- ParseResult: Result container for parsed file content
- ExtractorAdapter: Protocol defining the extractor interface
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class ExtractorAdapter(Protocol):
    """Protocol defining the interface for language-specific extractors.

    All language adapters must implement this protocol to provide consistent
    parsing and dependency extraction across different file types.

    The adapter pattern allows:
    - Language-specific parsing logic
    - Swappable implementations (AST-based, tree-sitter, etc.)
    - Testable extraction logic
    """

    def parse_file(self, file_path: Path) -> ParseResult:
        """Parse a file and return its content and AST representation.

        Args:
            file_path: Path to the file to parse.

        Returns:
            ParseResult containing parsed content and metadata.

        Raises:
            ParseError: If the file cannot be parsed.
        """
        ...

    def extract_dependencies(self, file_path: Path) -> List[Dependency]:
        """Extract dependencies from a parsed file.

        Args:
            file_path: Path to the file to analyze.

        Returns:
            List of Dependency objects found in the file.
        """
        ...


@dataclass(slots=True, frozen=True)
class ParseError(Exception):
    """Structured exception for parse failures.

    This exception provides detailed information about why a file could not
    be parsed, including the file path, line number, and error message.

    Attributes:
        file_path: Path to the file that failed to parse.
        line: Line number where the error occurred (1-indexed).
        message: Human-readable error message describing the failure.
    """

    file_path: Path
    line: int
    message: str

    def __str__(self) -> str:
        return f"ParseError in {self.file_path}:{self.line}: {self.message}"


@dataclass(slots=True, frozen=True)
class Dependency:
    """Represents an extracted dependency from a source file.

    Attributes:
        name: The name of the imported module or package.
        module_type: Classification of the dependency type:
            - "stdlib": Python standard library module
            - "external": Third-party package (e.g., from PyPI)
            - "relative": Relative import within the project
            - "unknown": Could not determine the type
        source_module: The original import statement (for relative imports).
    """

    name: str
    module_type: str
    source_module: Optional[str] = None


@dataclass(slots=True, frozen=True)
class ParseResult:
    """Container for the result of parsing a source file.

    Attributes:
        file_path: Path to the parsed file.
        ast_tree: Parsed AST tree (language-specific, may be None for non-AST languages).
        raw_content: Raw file content as string.
        dependencies: Tuple of dependencies extracted from the file.
    """

    file_path: Path
    ast_tree: Any
    raw_content: str
    dependencies: tuple[Dependency, ...]


# Policy options for handling parse errors
class OnParseErrorPolicy:
    """Constants for parse error handling policies."""

    ABORT = "abort"
    """Abort processing and mark the file as needing manual review."""

    SKIP = "skip"
    """Skip the file and continue processing."""

    FALLBACK = "fallback"
    """Attempt fallback parsing (e.g., regex-based for Python)."""
