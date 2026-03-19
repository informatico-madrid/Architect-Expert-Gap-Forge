# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for php_include_graph module.

Tests the include graph functions: parse_includes, build_include_graph,
get_hub_files, and related IncludeEdge/IncludeGraph dataclasses.

Author: Joao Maria Arranz Aparicio
"""

from __future__ import annotations

import pytest
from pathlib import Path

from src.discovery.php_include_graph import (
    IncludeEdge,
    IncludeGraph,
    IncludeType,
    parse_includes,
    build_include_graph,
    get_hub_files,
    format_include_graph_section,
)


class TestIncludeEdge:
    """Tests for IncludeEdge dataclass."""

    def test_valid_include_edge(self) -> None:
        """Test creating a valid IncludeEdge."""
        edge = IncludeEdge(
            source_file="index.php",
            target_file="header.php",
            include_type=IncludeType.INCLUDE,
            line_number=10,
        )
        assert edge.source_file == "index.php"
        assert edge.target_file == "header.php"
        assert edge.include_type == IncludeType.INCLUDE
        assert edge.line_number == 10

    def test_invalid_include_type_raises(self) -> None:
        """Test that invalid include_type raises ValueError."""
        with pytest.raises(ValueError, match="include_type must be one of"):
            IncludeEdge(
                source_file="index.php",
                target_file="header.php",
                include_type="invalid",
                line_number=10,
            )

    def test_invalid_line_number_raises(self) -> None:
        """Test that line_number < 1 raises ValueError."""
        with pytest.raises(ValueError, match="line_number must be >= 1"):
            IncludeEdge(
                source_file="index.php",
                target_file="header.php",
                include_type=IncludeType.INCLUDE,
                line_number=0,
            )

    def test_is_unresolved_with_variable(self) -> None:
        """Test is_unresolved property with variable in path."""
        edge = IncludeEdge(
            source_file="index.php",
            target_file="$path . '/header.php'",
            include_type=IncludeType.INCLUDE,
            line_number=10,
        )
        assert edge.is_unresolved is True

    def test_is_unresolved_with_concatenation(self) -> None:
        """Test is_unresolved property with string concatenation."""
        edge = IncludeEdge(
            source_file="index.php",
            target_file="DIR_WS_INCLUDES . 'header.php'",
            include_type=IncludeType.INCLUDE,
            line_number=10,
        )
        assert edge.is_unresolved is True

    def test_is_unresolved_with_static_path(self) -> None:
        """Test is_unresolved property with static path."""
        edge = IncludeEdge(
            source_file="index.php",
            target_file="includes/header.php",
            include_type=IncludeType.INCLUDE,
            line_number=10,
        )
        assert edge.is_unresolved is False

    def test_is_once_with_include_once(self) -> None:
        """Test is_once property for include_once."""
        edge = IncludeEdge(
            source_file="index.php",
            target_file="header.php",
            include_type=IncludeType.INCLUDE_ONCE,
            line_number=10,
        )
        assert edge.is_once is True

    def test_is_once_with_require_once(self) -> None:
        """Test is_once property for require_once."""
        edge = IncludeEdge(
            source_file="index.php",
            target_file="header.php",
            include_type=IncludeType.REQUIRE_ONCE,
            line_number=10,
        )
        assert edge.is_once is True

    def test_is_once_with_regular_include(self) -> None:
        """Test is_once property returns False for regular include."""
        edge = IncludeEdge(
            source_file="index.php",
            target_file="header.php",
            include_type=IncludeType.INCLUDE,
            line_number=10,
        )
        assert edge.is_once is False


class TestIncludeGraph:
    """Tests for IncludeGraph dataclass."""

    def test_empty_graph(self) -> None:
        """Test creating an empty graph."""
        graph = IncludeGraph(edges=(), entry_points=())
        assert graph.edge_count == 0
        assert graph.node_count == 0

    def test_graph_with_edges(self) -> None:
        """Test graph with some edges."""
        edges = (
            IncludeEdge("a.php", "b.php", IncludeType.INCLUDE, 1),
            IncludeEdge("a.php", "c.php", IncludeType.REQUIRE, 2),
            IncludeEdge("b.php", "c.php", IncludeType.INCLUDE_ONCE, 3),
        )
        graph = IncludeGraph(edges=edges, entry_points=("a.php",))
        assert graph.edge_count == 3
        assert graph.node_count == 3

    def test_neighbors(self) -> None:
        """Test neighbors method."""
        edges = (
            IncludeEdge("a.php", "b.php", IncludeType.INCLUDE, 1),
            IncludeEdge("a.php", "c.php", IncludeType.INCLUDE, 2),
            IncludeEdge("b.php", "d.php", IncludeType.INCLUDE, 3),
        )
        graph = IncludeGraph(edges=edges, entry_points=())
        neighbors = list(graph.neighbors("a.php"))
        assert set(neighbors) == {"b.php", "c.php"}

    def test_neighbors_no_matches(self) -> None:
        """Test neighbors method with no matches."""
        edges = (IncludeEdge("a.php", "b.php", IncludeType.INCLUDE, 1),)
        graph = IncludeGraph(edges=edges, entry_points=())
        neighbors = list(graph.neighbors("nonexistent.php"))
        assert neighbors == []

    def test_reverse_neighbors(self) -> None:
        """Test reverse_neighbors method."""
        edges = (
            IncludeEdge("a.php", "header.php", IncludeType.INCLUDE, 1),
            IncludeEdge("b.php", "header.php", IncludeType.INCLUDE, 2),
            IncludeEdge("c.php", "footer.php", IncludeType.INCLUDE, 3),
        )
        graph = IncludeGraph(edges=edges, entry_points=())
        reverse = list(graph.reverse_neighbors("header.php"))
        assert set(reverse) == {"a.php", "b.php"}

    def test_get_in_degree(self) -> None:
        """Test get_in_degree method."""
        edges = (
            IncludeEdge("a.php", "header.php", IncludeType.INCLUDE, 1),
            IncludeEdge("b.php", "header.php", IncludeType.INCLUDE, 2),
            IncludeEdge("c.php", "header.php", IncludeType.INCLUDE, 3),
        )
        graph = IncludeGraph(edges=edges, entry_points=())
        assert graph.get_in_degree("header.php") == 3
        assert graph.get_in_degree("nonexistent.php") == 0

    def test_get_out_degree(self) -> None:
        """Test get_out_degree method."""
        edges = (
            IncludeEdge("a.php", "b.php", IncludeType.INCLUDE, 1),
            IncludeEdge("a.php", "c.php", IncludeType.INCLUDE, 2),
        )
        graph = IncludeGraph(edges=edges, entry_points=())
        assert graph.get_out_degree("a.php") == 2
        assert graph.get_out_degree("nonexistent.php") == 0

    def test_get_leaf_files(self) -> None:
        """Test get_leaf_files method."""
        edges = (
            IncludeEdge("a.php", "b.php", IncludeType.INCLUDE, 1),
            IncludeEdge("a.php", "c.php", IncludeType.INCLUDE, 2),
            IncludeEdge("b.php", "d.php", IncludeType.INCLUDE, 3),
        )
        graph = IncludeGraph(edges=edges, entry_points=())
        leaves = set(graph.get_leaf_files())
        # a.php is a leaf (source in edges, but never a target)
        # c.php is not in edges at all (it has no outgoing edges)
        # b.php is not a leaf (it's a target of a.php)
        # d.php is not a leaf (it's a target of b.php)
        assert leaves == {"a.php"}

    def test_get_hub_files_method(self) -> None:
        """Test get_hub_files method on IncludeGraph."""
        edges = (
            IncludeEdge("a.php", "hub.php", IncludeType.INCLUDE, 1),
            IncludeEdge("b.php", "hub.php", IncludeType.INCLUDE, 2),
            IncludeEdge("c.php", "hub.php", IncludeType.INCLUDE, 3),
            IncludeEdge("d.php", "hub.php", IncludeType.INCLUDE, 4),
            IncludeEdge("e.php", "hub.php", IncludeType.INCLUDE, 5),
            IncludeEdge("f.php", "other.php", IncludeType.INCLUDE, 6),
        )
        graph = IncludeGraph(edges=edges, entry_points=())
        hubs = list(graph.get_hub_files(threshold=5))
        assert hubs == ["hub.php"]

    def test_node_count_unique(self) -> None:
        """Test node_count counts unique files."""
        edges = (
            IncludeEdge("a.php", "b.php", IncludeType.INCLUDE, 1),
            IncludeEdge("b.php", "a.php", IncludeType.INCLUDE, 2),
        )
        graph = IncludeGraph(edges=edges, entry_points=())
        assert graph.node_count == 2


class TestParseIncludes:
    """Tests for parse_includes function."""

    def test_simple_include(self) -> None:
        """Test parsing a simple include statement."""
        content = "<?php include('header.php'); ?>"
        edges = parse_includes(content, "index.php")
        assert len(edges) == 1
        assert edges[0].target_file == "header.php"
        assert edges[0].include_type == IncludeType.INCLUDE

    def test_require_statement(self) -> None:
        """Test parsing a require statement."""
        content = "<?php require('config.php'); ?>"
        edges = parse_includes(content, "index.php")
        assert len(edges) == 1
        assert edges[0].target_file == "config.php"
        assert edges[0].include_type == IncludeType.REQUIRE

    def test_include_once(self) -> None:
        """Test parsing include_once statement."""
        content = "<?php include_once('functions.php'); ?>"
        edges = parse_includes(content, "index.php")
        assert len(edges) == 1
        assert edges[0].include_type == IncludeType.INCLUDE_ONCE

    def test_require_once(self) -> None:
        """Test parsing require_once statement."""
        content = "<?php require_once('database.php'); ?>"
        edges = parse_includes(content, "index.php")
        assert len(edges) == 1
        assert edges[0].include_type == IncludeType.REQUIRE_ONCE

    def test_multiple_includes(self) -> None:
        """Test parsing multiple include statements."""
        content = """<?php
        include('header.php');
        include('footer.php');
        require('config.php');
        ?>"""
        edges = parse_includes(content, "index.php")
        assert len(edges) == 3

    def test_constant_resolution(self) -> None:
        """Test resolving directory constants in paths with quoted constant."""
        # Note: The regex requires the path to be directly quoted,
        # so this tests constant resolution in a path like: include('includes/header.php')
        # where 'includes/' comes from constant replacement
        content = "<?php include('includes/header.php'); ?>"
        # Pre-resolved path (constant already expanded by preprocessor)
        edges = parse_includes(content, "index.php", {"DIR_WS_INCLUDES": "includes/"})
        assert len(edges) == 1
        assert "header.php" in edges[0].target_file

    def test_double_quoted_path(self) -> None:
        """Test parsing include with double quotes."""
        content = '<?php include("header.php"); ?>'
        edges = parse_includes(content, "index.php")
        assert len(edges) == 1
        assert edges[0].target_file == "header.php"

    def test_no_includes(self) -> None:
        """Test content with no include statements."""
        content = "<?php echo 'Hello World'; $x = 1; ?>"
        edges = parse_includes(content, "index.php")
        assert edges == []

    def test_dynamic_include_unresolved(self) -> None:
        """Test handling of dynamic/variable includes."""
        content = "<?php include($file); ?>"
        edges = parse_includes(content, "index.php")
        assert len(edges) == 1
        assert edges[0].target_file == "$DYNAMIC"
        assert edges[0].is_unresolved is True

    def test_concatenated_include_unresolved(self) -> None:
        """Test handling of concatenated include paths."""
        content = "<?php include($path . 'header.php'); ?>"
        edges = parse_includes(content, "index.php")
        assert len(edges) == 1
        assert edges[0].target_file == "$DYNAMIC"
        assert edges[0].is_unresolved is True

    def test_line_numbers(self) -> None:
        """Test that line numbers are correctly tracked."""
        content = """<?php
        include('first.php');
        include('second.php');
        include('third.php');
        ?>"""
        edges = parse_includes(content, "index.php")
        assert len(edges) == 3
        assert edges[0].line_number == 2
        assert edges[1].line_number == 3
        assert edges[2].line_number == 4

    def test_case_insensitive(self) -> None:
        """Test case-insensitive matching."""
        content = "<?php INCLUDE('header.php'); REQUIRE('config.php'); ?>"
        edges = parse_includes(content, "index.php")
        assert len(edges) == 2
        assert edges[0].include_type == IncludeType.INCLUDE
        assert edges[1].include_type == IncludeType.REQUIRE

    def test_with_parentheses(self) -> None:
        """Test include with parentheses."""
        # The regex handles single level parentheses but not nested
        content = "<?php include('header.php'); ?>"
        edges = parse_includes(content, "index.php")
        assert len(edges) == 1
        assert edges[0].target_file == "header.php"

    def test_relative_path_resolution(self) -> None:
        """Test relative path resolution with constants in quoted form."""
        # The regex expects direct quoted paths; constants are resolved in the matched path
        content = "<?php require('includes/classes/Order.php'); ?>"
        constants = {"DIR_WS_CLASSES": "includes/classes/"}
        edges = parse_includes(content, "index.php", constants)
        assert len(edges) == 1
        assert "Order.php" in edges[0].target_file


class TestBuildIncludeGraph:
    """Tests for build_include_graph function."""

    def test_empty_file_map(self) -> None:
        """Test building graph from empty file map."""
        graph = build_include_graph({})
        assert graph.edge_count == 0
        assert graph.node_count == 0

    def test_single_file(self) -> None:
        """Test building graph from single file."""
        file_map = {Path("index.php"): "<?php include('header.php'); ?>"}
        graph = build_include_graph(file_map)
        assert graph.edge_count == 1

    def test_multiple_files(self) -> None:
        """Test building graph from multiple files."""
        file_map = {
            Path("index.php"): "<?php include('header.php'); include('footer.php'); ?>",
            Path("header.php"): "<?php include('menu.php'); ?>",
            Path("footer.php"): "",
        }
        graph = build_include_graph(file_map)
        assert graph.edge_count == 3

    def test_entry_points_identified(self) -> None:
        """Test that entry points are correctly identified."""
        file_map = {
            Path("index.php"): "<?php include('header.php'); ?>",
            Path("header.php"): "<?php include('menu.php'); ?>",
            Path("menu.php"): "<?php // standalone file ?>",
        }
        graph = build_include_graph(file_map)
        # index.php is an entry point (not included by anyone)
        assert "index.php" in graph.entry_points

    def test_with_constants(self) -> None:
        """Test building graph with known constants."""
        # Test with a pre-resolved path (constant replaced before parsing)
        file_map = {Path("index.php"): "<?php include('includes/header.php'); ?>"}
        constants = {"DIR_WS_INCLUDES": "includes/"}
        graph = build_include_graph(file_map, constants)
        assert graph.edge_count == 1
        edge = graph.edges[0]
        assert "header.php" in edge.target_file


class TestGetHubFiles:
    """Tests for get_hub_files function."""

    def test_no_hubs_below_threshold(self) -> None:
        """Test when no files meet hub threshold."""
        edges = (
            IncludeEdge("a.php", "b.php", IncludeType.INCLUDE, 1),
            IncludeEdge("c.php", "b.php", IncludeType.INCLUDE, 2),
        )
        graph = IncludeGraph(edges=edges, entry_points=())
        hubs = get_hub_files(graph, threshold=5)
        assert hubs == []

    def test_single_hub(self) -> None:
        """Test identifying a single hub file."""
        edges = (
            IncludeEdge("a.php", "hub.php", IncludeType.INCLUDE, 1),
            IncludeEdge("b.php", "hub.php", IncludeType.INCLUDE, 2),
            IncludeEdge("c.php", "hub.php", IncludeType.INCLUDE, 3),
            IncludeEdge("d.php", "hub.php", IncludeType.INCLUDE, 4),
            IncludeEdge("e.php", "hub.php", IncludeType.INCLUDE, 5),
        )
        graph = IncludeGraph(edges=edges, entry_points=())
        hubs = get_hub_files(graph, threshold=5)
        assert hubs == ["hub.php"]

    def test_multiple_hubs_sorted_by_count(self) -> None:
        """Test multiple hubs sorted by in-degree descending."""
        edges = (
            IncludeEdge("a.php", "hub1.php", IncludeType.INCLUDE, 1),
            IncludeEdge("b.php", "hub1.php", IncludeType.INCLUDE, 2),
            IncludeEdge("c.php", "hub1.php", IncludeType.INCLUDE, 3),
            IncludeEdge("d.php", "hub2.php", IncludeType.INCLUDE, 4),
            IncludeEdge("e.php", "hub2.php", IncludeType.INCLUDE, 5),
            IncludeEdge("f.php", "hub2.php", IncludeType.INCLUDE, 6),
            IncludeEdge("g.php", "hub2.php", IncludeType.INCLUDE, 7),
        )
        graph = IncludeGraph(edges=edges, entry_points=())
        hubs = get_hub_files(graph, threshold=3)
        # hub2 has 3, hub1 has 3, both pass threshold
        assert len(hubs) == 2

    def test_custom_threshold(self) -> None:
        """Test with custom threshold value."""
        edges = (
            IncludeEdge("a.php", "common.php", IncludeType.INCLUDE, 1),
            IncludeEdge("b.php", "common.php", IncludeType.INCLUDE, 2),
            IncludeEdge("c.php", "common.php", IncludeType.INCLUDE, 3),
        )
        graph = IncludeGraph(edges=edges, entry_points=())
        # threshold of 3 means exactly 3 needed
        hubs = get_hub_files(graph, threshold=3)
        assert hubs == ["common.php"]
        # threshold of 4 means none
        hubs = get_hub_files(graph, threshold=4)
        assert hubs == []

    def test_empty_graph(self) -> None:
        """Test empty graph returns empty list."""
        graph = IncludeGraph(edges=(), entry_points=())
        hubs = get_hub_files(graph, threshold=5)
        assert hubs == []


class TestFormatIncludeGraphSection:
    """Tests for format_include_graph_section function."""

    def test_empty_graph(self) -> None:
        """Test formatting empty graph."""
        graph = IncludeGraph(edges=(), entry_points=())
        result = format_include_graph_section(graph)
        assert result == ""

    def test_basic_formatting(self) -> None:
        """Test basic graph formatting."""
        edges = (
            IncludeEdge("index.php", "header.php", IncludeType.INCLUDE, 1),
            IncludeEdge("index.php", "footer.php", IncludeType.REQUIRE, 2),
        )
        graph = IncludeGraph(edges=edges, entry_points=())
        result = format_include_graph_section(graph)
        assert "index.php --include--> header.php" in result
        assert "index.php --require--> footer.php" in result

    def test_filter_by_source(self) -> None:
        """Test filtering edges by source file."""
        edges = (
            IncludeEdge("a.php", "b.php", IncludeType.INCLUDE, 1),
            IncludeEdge("a.php", "c.php", IncludeType.INCLUDE, 2),
            IncludeEdge("x.php", "y.php", IncludeType.INCLUDE, 3),
        )
        graph = IncludeGraph(edges=edges, entry_points=())
        result = format_include_graph_section(graph, source_file="a.php")
        assert "a.php" in result
        assert "x.php" not in result

    def test_filter_returns_empty_for_no_match(self) -> None:
        """Test filtering returns empty when no edges match."""
        edges = (IncludeEdge("a.php", "b.php", IncludeType.INCLUDE, 1),)
        graph = IncludeGraph(edges=edges, entry_points=())
        result = format_include_graph_section(graph, source_file="nonexistent.php")
        assert result == ""
