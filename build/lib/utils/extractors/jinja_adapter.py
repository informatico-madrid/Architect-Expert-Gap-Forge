# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Jinja Adapter for Home Assistant Template Files.

This adapter provides:
- Jinja template parsing
- Variable extraction
- Filter extraction
- Test extraction
- Loop and conditional extraction
- Home Assistant specific expression detection

Author: Joao Maria Arranz Aparicio
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import List, Set

from src.utils.extractors.base import (
    Dependency,
    ExtractorAdapter,
    ParseError,
    ParseResult,
)
from src.utils.extractors.extractors.jinja_base import (
    extract_jinja_variables,
    extract_jinja_filters,
    extract_jinja_tests,
    extract_jinja_loops,
    extract_jinja_conditionals,
    extract_jinja_statements,
)

logger = logging.getLogger(__name__)


class JinjaAdapter(ExtractorAdapter):
    """Adapter for parsing Jinja template files.

    This adapter provides:
    - Jinja template parsing
    - Variable extraction with line numbers
    - Filter extraction with source variables
    - Test extraction with source variables
    - Loop and conditional extraction
    - Home Assistant specific expression detection

    Attributes:
        use_regex_fallback: Whether to use regex fallback for parsing.
    """

    def __init__(self, use_regex_fallback: bool = True):
        """Initialize JinjaAdapter.

        Args:
            use_regex_fallback: Whether to use regex fallback for parsing.
        """
        self.use_regex_fallback = use_regex_fallback

    def parse_file(self, file_path: Path) -> ParseResult:
        """Parse a Jinja template file and extract tokens.

        Args:
            file_path: Path to the Jinja file to parse.

        Returns:
            ParseResult containing parsed content and tokens.

        Raises:
            ParseError: If the file cannot be read.
        """
        try:
            raw_content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            raise ParseError(
                file_path=file_path,
                line=1,
                message=f"Failed to read file: {str(e)}",
            )

        # Extract all tokens
        variables = extract_jinja_variables(raw_content, str(file_path))
        filters = extract_jinja_filters(raw_content, str(file_path))
        tests = extract_jinja_tests(raw_content, str(file_path))
        loops = extract_jinja_loops(raw_content, str(file_path))
        conditionals = extract_jinja_conditionals(raw_content, str(file_path))
        statements = extract_jinja_statements(raw_content, str(file_path))

        # Combine all tokens
        (
            variables + filters + tests + loops + conditionals + statements
        )

        # Extract dependencies
        dependencies = self._extract_dependencies(raw_content)

        return ParseResult(
            file_path=file_path,
            ast_tree=None,  # No AST for Jinja templates
            raw_content=raw_content,
            dependencies=tuple(dependencies),
        )

    def extract_dependencies(self, file_path: Path) -> List[Dependency]:
        """Extract dependencies from a Jinja template.

        Args:
            file_path: Path to the Jinja file to analyze.

        Returns:
            List of Dependency objects.
        """
        try:
            raw_content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            raise ParseError(
                file_path=file_path,
                line=1,
                message=f"Failed to read file: {str(e)}",
            )

        return self._extract_dependencies(raw_content)

    def _extract_dependencies(self, raw_content: str) -> List[Dependency]:
        """Extract dependencies from Jinja content.

        Args:
            raw_content: Jinja template content

        Returns:
            List of Dependency objects
        """
        dependencies: List[Dependency] = []
        seen: Set[str] = set()

        # Extract Home Assistant states() calls with string arguments
        # Match patterns like: states('climate.living_room'), states("climate.living_room")
        states_pattern = re.compile(r'states\s*\(\s*[\'"](\w+)\.(\w+)[\'"]')
        for match in states_pattern.finditer(raw_content):
            domain = match.group(1)
            entity = match.group(2)
            dep_name = f"{domain}/{entity}"
            if dep_name not in seen:
                seen.add(dep_name)
                dependencies.append(
                    Dependency(
                        name=dep_name,
                        module_type="entity",
                    )
                )

        # Extract state_attr() calls
        state_attr_pattern = re.compile(r'state_attr\(["\'](\w+)\.(\w+)["\']')
        for match in state_attr_pattern.finditer(raw_content):
            domain = match.group(1)
            entity = match.group(2)
            dep_name = f"state_attr/{domain}/{entity}"
            if dep_name not in seen:
                seen.add(dep_name)
                dependencies.append(
                    Dependency(
                        name=dep_name,
                        module_type="entity",
                    )
                )

        # Extract now() and date/time functions
        now_pattern = re.compile(r'now\s*\(\s*\)')
        if now_pattern.search(raw_content):
            dep_name = "now()"
            if dep_name not in seen:
                seen.add(dep_name)
                dependencies.append(
                    Dependency(
                        name=dep_name,
                        module_type="time",
                    )
                )

        # Extract !input variables
        input_pattern = re.compile(r'!input\s+["\']([^"\']+)["\']')
        for match in input_pattern.finditer(raw_content):
            var_name = match.group(1)
            dep_name = f"!input/{var_name}"
            if dep_name not in seen:
                seen.add(dep_name)
                dependencies.append(
                    Dependency(
                        name=dep_name,
                        module_type="input",
                    )
                )

        return dependencies

    @staticmethod
    def _classify_module(name: str) -> str:
        """Classify a module as standard, entity, or time.

        Args:
            name: Module name to classify.

        Returns:
            "entity" if it's an entity ID, "time" if it's a time function,
            "input" if it's an input variable, "external" otherwise.
        """
        if name.startswith("states/"):
            return "entity"
        if name.startswith("state_attr/"):
            return "entity"
        if name == "now()":
            return "time"
        if name.startswith("!input/"):
            return "input"
        return "external"
