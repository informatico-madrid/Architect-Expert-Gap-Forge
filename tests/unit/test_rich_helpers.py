#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Tests for AEGF Rich Helpers Module
==================================
Unit tests for src/utils/rich_helpers.py
"""

from __future__ import annotations



from rich.console import Console
from rich.table import Table

from src.utils.rich_helpers import (
    BOLD_STYLE,
    ERROR_STYLE,
    INFO_STYLE,
    SUCCESS_STYLE,
    WARNING_STYLE,
    create_console,
    create_table,
    format_duration,
    format_size,
    get_console,
    get_logger,
    is_tty,
    print_error,
    print_exception,
    print_info,
    print_success,
    print_status,
    print_table,
    print_warning,
    setup_rich_logging,
    should_use_rich,
)


class TestConsoleFactory:
    """Tests for console creation functions."""

    def test_create_console_auto_detect(self):
        """Test console creation with auto-detection."""
        console = create_console()
        assert isinstance(console, Console)

    def test_create_console_force_terminal_true(self):
        """Test console creation with force_terminal=True."""
        console = create_console(force_terminal=True)
        assert isinstance(console, Console)

    def test_create_console_force_terminal_false(self):
        """Test console creation with force_terminal=False."""
        console = create_console(force_terminal=False)
        assert isinstance(console, Console)

    def test_create_console_no_color(self):
        """Test console creation with no_color=True."""
        console = create_console(no_color=True)
        assert isinstance(console, Console)

    def test_get_console_singleton(self):
        """Test that get_console returns a singleton instance."""
        console1 = get_console()
        console2 = get_console()
        assert console1 is console2


class TestFormattingUtilities:
    """Tests for formatting utility functions."""

    def test_print_success(self, capsys):
        """Test success panel printing."""
        console = get_console()
        print_success(console, "Operation completed", title="Done")
        captured = capsys.readouterr()
        assert "Operation completed" in captured.out

    def test_print_error(self, capsys):
        """Test error panel printing."""
        console = get_console()
        print_error(console, "Something went wrong", title="Failed")
        captured = capsys.readouterr()
        assert "Something went wrong" in captured.out

    def test_print_warning(self, capsys):
        """Test warning panel printing."""
        console = get_console()
        print_warning(console, "Low disk space", title="Caution")
        captured = capsys.readouterr()
        assert "Low disk space" in captured.out

    def test_print_info(self, capsys):
        """Test info panel printing."""
        console = get_console()
        print_info(console, "Loading data...", title="Status")
        captured = capsys.readouterr()
        assert "Loading data..." in captured.out

    def test_print_status(self, capsys):
        """Test status printing."""
        console = get_console()
        print_status(console, "Processing files...")
        captured = capsys.readouterr()
        assert "Processing files..." in captured.out


class TestTableUtilities:
    """Tests for table utilities."""

    def test_create_table(self):
        """Test table creation with default settings."""
        table = create_table()
        assert isinstance(table, Table)
        assert table.show_header is True
        assert table.show_lines is False

    def test_create_table_with_title(self):
        """Test table creation with custom title."""
        table = create_table(title="My Table")
        assert table.title == "My Table"

    def test_create_table_no_header(self):
        """Test table creation without header."""
        table = create_table(show_header=False)
        assert table.show_header is False

    def test_print_table(self, capsys):
        """Test table printing."""
        console = get_console()
        table = create_table(title="Test Table")
        table.add_column("Column 1")
        table.add_column("Column 2")
        table.add_row("Value 1", "Value 2")
        print_table(console, table)
        captured = capsys.readouterr()
        assert "Test Table" in captured.out


class TestLoggingIntegration:
    """Tests for logging integration."""

    def test_setup_rich_logging(self):
        """Test rich logging setup."""
        setup_rich_logging("test_logger", level=10)  # DEBUG level
        import logging

        root_logger = logging.getLogger()
        assert root_logger.level == 10

    def test_get_logger(self):
        """Test logger retrieval."""
        logger = get_logger("test_module")
        assert logger.name == "test_module"


class TestErrorHandling:
    """Tests for error handling utilities."""

    def test_print_exception(self, capsys):
        """Test exception printing."""
        console = get_console()
        test_error = ValueError("Test error message")
        print_exception(console, test_error, context="Operation failed")
        captured = capsys.readouterr()
        assert "ValueError" in captured.out
        assert "Test error message" in captured.out

    def test_print_exception_no_context(self, capsys):
        """Test exception printing without context."""
        console = get_console()
        test_error = RuntimeError("Runtime error")
        print_exception(console, test_error)
        captured = capsys.readouterr()
        assert "RuntimeError" in captured.out


class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_format_size_bytes(self):
        """Test format_size with bytes."""
        assert format_size(1024) == "1.0 KB"
        assert format_size(0) == "0.0 B"

    def test_format_size_kb(self):
        """Test format_size with kilobytes."""
        assert format_size(1536) == "1.5 KB"

    def test_format_size_mb(self):
        """Test format_size with megabytes."""
        assert format_size(1572864) == "1.5 MB"

    def test_format_size_gb(self):
        """Test format_size with gigabytes."""
        assert format_size(1610612736) == "1.5 GB"

    def test_format_duration_seconds(self):
        """Test format_duration with seconds."""
        result = format_duration(30.5)
        assert "30.5s" in result

    def test_format_duration_minutes(self):
        """Test format_duration with minutes."""
        result = format_duration(120.5)
        assert "2m" in result or "1m" in result

    def test_format_duration_hours(self):
        """Test format_duration with hours."""
        result = format_duration(3665.5)
        assert "1h" in result

    def test_is_tty(self):
        """Test is_tty detection."""
        result = is_tty()
        assert isinstance(result, bool)

    def test_should_use_rich(self):
        """Test should_use_rich detection."""
        result = should_use_rich()
        assert isinstance(result, bool)

    def test_constants(self):
        """Test that constants are defined correctly."""
        assert SUCCESS_STYLE == "green"
        assert ERROR_STYLE == "red"
        assert WARNING_STYLE == "yellow"
        assert INFO_STYLE == "blue"
        assert BOLD_STYLE == "bold"


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_create_table_multiple_columns(self):
        """Test table creation with multiple columns."""
        table = create_table(title="Users")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Email", style="green")
        assert len(table.columns) == 3

    def test_print_exception_with_custom_context(self, capsys):
        """Test exception printing with custom context."""
        console = get_console()
        test_error = ConnectionError("Connection refused")
        print_exception(console, test_error, context="Failed to connect")
        captured = capsys.readouterr()
        assert "Failed to connect" in captured.out
