# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Markdown Adapter Module
=======================

Provides a simple adapter for parsing markdown files.
Markdown files don't have code dependencies to extract, so this adapter
simply reads and returns the raw content.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from src.utils.extractors.base import (
    Dependency,
    ExtractorAdapter,
    ParseError,
    ParseResult,
)


class MarkdownAdapter(ExtractorAdapter):
    """Adapter for parsing markdown files.

    Markdown files are documentation and don't have code dependencies.
    This adapter simply reads the raw content and returns an empty
    dependency list.
    """

    def parse_file(self, file_path: Path) -> ParseResult:
        """Parse a markdown file and return its raw content.

        Args:
            file_path: Path to the markdown file to parse.

        Returns:
            ParseResult containing raw content and empty dependencies.

        Raises:
            ParseError: If the file cannot be read.
        """
        try:
            raw_content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            raise ParseError(
                file_path=file_path,
                line=0,
                message=f"Failed to read markdown file: {e}",
            )

        return ParseResult(
            file_path=file_path,
            ast_tree=None,  # Markdown doesn't have an AST
            raw_content=raw_content,
            dependencies=(),  # No dependencies in markdown
        )

    def extract_dependencies(self, file_path: Path) -> List[Dependency]:
        """Extract dependencies from a markdown file.

        Markdown files don't have code dependencies, so this always
        returns an empty list.

        Args:
            file_path: Path to the markdown file.

        Returns:
            Empty list of dependencies.
        """
        return []
