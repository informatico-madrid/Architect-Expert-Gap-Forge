# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
PHP Include Graph Module
========================
Provides graph-based representation of PHP include/require dependencies.

This module defines the IncludeEdge and IncludeGraph dataclasses
for representing the module dependency graph in legacy PHP codebases.

Author: Joao Maria Arranz Aparicio
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Iterator

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# Include Types
# ---------------------------------------------------------------------------
class IncludeType:
    """Include type constants for PHP include/require statements."""

    INCLUDE = "include"
    INCLUDE_ONCE = "include_once"
    REQUIRE = "require"
    REQUIRE_ONCE = "require_once"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class IncludeEdge:
    """
    Represents a dependency edge between PHP files.

    An edge captures a relationship where one PHP file includes or requires
    another file, forming part of the module dependency graph.

    Attributes:
        source_file: Path to the file containing the include/require statement
        target_file: Path to the file being included (may be unresolved)
        include_type: Type of include (include|include_once|require|require_once)
        line_number: Line number where the include statement appears (1-indexed)
    """

    source_file: str
    target_file: str
    include_type: str
    line_number: int

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        valid_types = {
            IncludeType.INCLUDE,
            IncludeType.INCLUDE_ONCE,
            IncludeType.REQUIRE,
            IncludeType.REQUIRE_ONCE,
        }
        if self.include_type not in valid_types:
            raise ValueError(
                f"include_type must be one of {valid_types}, got '{self.include_type}'"
            )

        if self.line_number < 1:
            raise ValueError(
                f"line_number must be >= 1, got {self.line_number}"
            )

    @property
    def is_unresolved(self) -> bool:
        """Return True if the target file path contains variables."""
        # Check for common patterns indicating unresolved paths
        unresolved_pattern = r'(\$\w+|\{|\.\s*[\'"]|\.\s*\$\w+)'
        return bool(re.search(unresolved_pattern, self.target_file))

    @property
    def is_once(self) -> bool:
        """Return True if this is an include_once or require_once."""
        return self.include_type in (IncludeType.INCLUDE_ONCE, IncludeType.REQUIRE_ONCE)


@dataclass(frozen=True, slots=True)
class IncludeGraph:
    """
    Represents the include/require dependency graph of a PHP repository.

    A directed graph where nodes are PHP files and edges represent
    include/require relationships. Useful for identifying hub files
    (included by many others) and understanding module architecture.

    Attributes:
        edges: Tuple of IncludeEdge instances representing all dependencies
        entry_points: Tuple of file paths that are entry points (not included by others)
    """

    edges: tuple[IncludeEdge, ...]
    entry_points: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        if not isinstance(self.edges, tuple):
            object.__setattr__(self, 'edges', tuple(self.edges))

        if not isinstance(self.entry_points, tuple):
            object.__setattr__(self, 'entry_points', tuple(self.entry_points))

    def neighbors(self, source_file: str) -> Iterator[str]:
        """
        Get all files that the given source file includes/requires.

        Args:
            source_file: The source file to get neighbors for

        Yields:
            Target file paths that are included by the source file
        """
        for edge in self.edges:
            if edge.source_file == source_file:
                yield edge.target_file

    def reverse_neighbors(self, target_file: str) -> Iterator[str]:
        """
        Get all files that include/require the given target file.

        Args:
            target_file: The target file to get reverse neighbors for

        Yields:
            Source file paths that include the target file
        """
        for edge in self.edges:
            if edge.target_file == target_file:
                yield edge.source_file

    def get_hub_files(self, threshold: int = 5) -> Iterator[str]:
        """
        Get files that are included by many other files (hub files).

        Args:
            threshold: Minimum number of files including this target
                       to be considered a hub (default: 5)

        Yields:
            Target file paths that are included by threshold or more files
        """
        target_counts: dict[str, int] = {}
        for edge in self.edges:
            target_counts[edge.target_file] = target_counts.get(edge.target_file, 0) + 1

        for target, count in target_counts.items():
            if count >= threshold:
                yield target

    def get_leaf_files(self) -> Iterator[str]:
        """
        Get files that include other files but are never included themselves.

        Yields:
            File paths that are leaf nodes in the dependency graph
        """
        included_files = {edge.target_file for edge in self.edges}

        for edge in self.edges:
            source = edge.source_file
            if source not in included_files:
                yield source

    def get_in_degree(self, target_file: str) -> int:
        """
        Get the number of files that include the given target file.

        Args:
            target_file: The target file to check

        Returns:
            Number of files that include this target
        """
        return sum(1 for edge in self.edges if edge.target_file == target_file)

    def get_out_degree(self, source_file: str) -> int:
        """
        Get the number of files included by the given source file.

        Args:
            source_file: The source file to check

        Returns:
            Number of files included by this source
        """
        return sum(1 for edge in self.edges if edge.source_file == source_file)

    @property
    def edge_count(self) -> int:
        """Return the total number of edges in the graph."""
        return len(self.edges)

    @property
    def node_count(self) -> int:
        """Return the total number of unique files in the graph."""
        return len({e.source_file for e in self.edges} | {e.target_file for e in self.edges})


# ---------------------------------------------------------------------------
# Type Aliases
# ---------------------------------------------------------------------------
IncludeEdgeTuple = tuple[IncludeEdge, ...]


# ---------------------------------------------------------------------------
# Core Functions
# ---------------------------------------------------------------------------
def parse_includes(
    content: str,
    source_file: str,
    known_constants: dict[str, str] | None = None
) -> list[IncludeEdge]:
    """
    Parse include/require statements from PHP content.

    Extracts all include, include_once, require, and require_once statements
    and resolves known directory constants where possible.

    Args:
        content: PHP source code to parse
        source_file: Path to the source file (used for relative resolution)
        known_constants: Optional dict of known constants (e.g., DIR_WS_INCLUDES)

    Returns:
        List of IncludeEdge instances found in the content
    """
    edges: list[IncludeEdge] = []
    known_constants = known_constants or {}

    # Regex patterns for include/require statements
    include_pattern = re.compile(
        r'(include|include_once|require|require_once)\s*[(_]?\s*'
        r'["\']([^"\']+)["\']',
        re.IGNORECASE
    )

    # Pattern for variable/dynamic includes (will be marked unresolved)
    dynamic_pattern = re.compile(
        r'(include|include_once|require|require_once)\s*\(?\s*\$',
        re.IGNORECASE
    )

    lines = content.split('\n')

    for line_num, line in enumerate(lines, start=1):
        # Skip dynamic includes (unresolvable)
        if dynamic_pattern.search(line):
            # Still create edge but mark as unresolved
            match = re.search(r'(include|include_once|require|require_once)', line, re.IGNORECASE)
            if match:
                include_type = match.group(1).lower()
                if include_type == 'include':
                    edge_type = IncludeType.INCLUDE
                elif include_type == 'include_once':
                    edge_type = IncludeType.INCLUDE_ONCE
                elif include_type == 'require':
                    edge_type = IncludeType.REQUIRE
                else:
                    edge_type = IncludeType.REQUIRE_ONCE

                edges.append(IncludeEdge(
                    source_file=source_file,
                    target_file="$DYNAMIC",
                    include_type=edge_type,
                    line_number=line_num
                ))
            continue

        # Parse static includes
        for match in include_pattern.finditer(line):
            include_type_raw = match.group(1).lower()
            target_path = match.group(2).strip()

            # Resolve constants in the path
            for const_name, const_value in known_constants.items():
                target_path = target_path.replace(const_name, const_value)

            # Map to canonical include type
            if include_type_raw == 'include':
                edge_type = IncludeType.INCLUDE
            elif include_type_raw == 'include_once':
                edge_type = IncludeType.INCLUDE_ONCE
            elif include_type_raw == 'require':
                edge_type = IncludeType.REQUIRE
            else:
                edge_type = IncludeType.REQUIRE_ONCE

            edges.append(IncludeEdge(
                source_file=source_file,
                target_file=target_path,
                include_type=edge_type,
                line_number=line_num
            ))

    return edges


def build_include_graph(
    file_map: dict[Path, str],
    constants: dict[str, str] | None = None
) -> IncludeGraph:
    """
    Build an include graph from a collection of PHP files.

    Args:
        file_map: Dict mapping file paths to their content
        constants: Optional known constants for path resolution

    Returns:
        IncludeGraph representing the dependency structure
    """
    all_edges: list[IncludeEdge] = []

    for file_path, content in file_map.items():
        source_file = str(file_path)
        edges = parse_includes(content, source_file, constants)
        all_edges.extend(edges)

    # Identify entry points (files that are not included by any other)
    included_files = {edge.target_file for edge in all_edges}
    all_files = {str(p) for p in file_map.keys()}
    entry_points = tuple(f for f in all_files if f not in included_files)

    return IncludeGraph(
        edges=tuple(all_edges),
        entry_points=entry_points
    )


def get_hub_files(graph: IncludeGraph, threshold: int = 5) -> list[str]:
    """
    Get files included by threshold or more other files.

    Args:
        graph: The IncludeGraph to analyze
        threshold: Minimum number of including files (default: 5)

    Returns:
        List of hub file paths sorted by in-degree (descending)
    """
    hub_counts: dict[str, int] = {}
    for edge in graph.edges:
        hub_counts[edge.target_file] = hub_counts.get(edge.target_file, 0) + 1

    hubs = [(f, count) for f, count in hub_counts.items() if count >= threshold]
    hubs.sort(key=lambda x: x[1], reverse=True)

    return [f for f, _ in hubs]


def format_include_graph_section(
    graph: IncludeGraph,
    source_file: str | None = None
) -> str:
    """
    Format the include graph as a section string for bundle output.

    Args:
        graph: The IncludeGraph to format
        source_file: Optional filter - only show edges from this source file

    Returns:
        Formatted graph section string
    """
    if not graph.edges:
        return ""

    edges_to_show = graph.edges
    if source_file:
        edges_to_show = [e for e in edges_to_show if e.source_file == source_file]

    if not edges_to_show:
        return ""

    lines: list[str] = []
    for edge in edges_to_show:
        lines.append(f"{edge.source_file} --{edge.include_type}--> {edge.target_file}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)
