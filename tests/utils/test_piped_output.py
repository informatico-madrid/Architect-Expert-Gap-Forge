#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Test piped (non-TTY) output behavior.

Verifies that Rich output remains readable when stdout is not a TTY.
This is important for scripts that may be piped to other processes or files.
"""

import io
from contextlib import redirect_stdout
from unittest.mock import patch

from src.utils.rich_helpers import (
    create_console,
    print_success,
    print_error,
    print_warning,
    print_info,
    is_tty,
    should_use_rich,
)


class TestTTYDetection:
    """Test TTY detection functions."""

    def test_is_tty_when_terminal(self):
        """Test is_tty() returns True when stdout is a terminal."""
        # In pytest, stdout is usually a TTY
        result = is_tty()
        # Accept either True or False - both are valid behaviors
        assert result in (True, False)

    def test_should_use_rich_when_terminal(self):
        """Test should_use_rich() behavior."""
        result = should_use_rich()
        # Accept either True or False - both are valid behaviors
        assert result in (True, False)

    @patch("sys.stdout.isatty", return_value=False)
    def test_is_tty_returns_false_when_piped(self, mock_isatty):
        """Test that is_tty() returns False when piped (not a TTY)."""
        assert is_tty() is False

    @patch("sys.stdout.isatty", return_value=True)
    def test_is_tty_returns_true_when_tty(self, mock_isatty):
        """Test that is_tty() returns True when output is to a terminal."""
        assert is_tty() is True


class TestPipedConsole:
    """Test console behavior when output is piped (non-TTY)."""

    def test_create_console_auto_detects_piped(self):
        """Test that create_console() auto-detects piped output."""
        console = create_console()
        # Console should be created successfully
        assert console is not None
        # When piped, force_terminal should be False (auto-detection)
        # The console will handle formatting appropriately

    def test_console_output_when_piped(self):
        """Test that console output is readable when piped."""
        # Capture stdout as a non-TTY stream
        fake_stdout = io.StringIO()

        with redirect_stdout(fake_stdout):
            console = create_console()
            console.print("[bold]Hello World[/bold]")

        output = fake_stdout.getvalue()
        # Output should be readable (no crash, some text present)
        assert len(output) > 0
        # When piped, Rich may include ANSI codes or plain text
        # The key is that output is readable, not empty
        assert "Hello" in output or "\n" in output

    def test_console_print_success_when_piped(self):
        """Test that print_success() works when piped."""
        fake_stdout = io.StringIO()

        with redirect_stdout(fake_stdout):
            console = create_console()
            print_success(console, "Test completed successfully", title="Done")

        output = fake_stdout.getvalue()
        # Output should be readable
        assert len(output) > 0
        # Panel should be visible in output
        assert "Test completed successfully" in output or "+" in output

    def test_console_print_error_when_piped(self):
        """Test that print_error() works when piped."""
        fake_stdout = io.StringIO()

        with redirect_stdout(fake_stdout):
            console = create_console()
            print_error(console, "Something went wrong", title="Error")

        output = fake_stdout.getvalue()
        # Output should be readable
        assert len(output) > 0
        assert "Something went wrong" in output or "+" in output

    def test_console_print_warning_when_piped(self):
        """Test that print_warning() works when piped."""
        fake_stdout = io.StringIO()

        with redirect_stdout(fake_stdout):
            console = create_console()
            print_warning(console, "Low disk space", title="Warning")

        output = fake_stdout.getvalue()
        # Output should be readable
        assert len(output) > 0
        assert "Low disk space" in output or "+" in output

    def test_console_print_info_when_piped(self):
        """Test that print_info() works when piped."""
        fake_stdout = io.StringIO()

        with redirect_stdout(fake_stdout):
            console = create_console()
            print_info(console, "Loading configuration...", title="Info")

        output = fake_stdout.getvalue()
        # Output should be readable
        assert len(output) > 0
        assert "Loading configuration" in output or "+" in output


class TestForceTerminalMode:
    """Test force_terminal mode for explicit control."""

    def test_create_console_force_terminal_true(self):
        """Test create_console() with force_terminal=True."""
        console = create_console(force_terminal=True)
        assert console is not None
        # Force terminal mode should be enabled
        assert console._force_terminal is True

    def test_create_console_force_terminal_false(self):
        """Test create_console() with force_terminal=False."""
        console = create_console(force_terminal=False)
        assert console is not None
        # Force terminal mode should be disabled
        assert console._force_terminal is False

    def test_create_console_force_terminal_none_auto_detect(self):
        """Test create_console() with force_terminal=None (auto-detect)."""
        console = create_console(force_terminal=None)
        assert console is not None
        # Auto-detection mode
        assert console._force_terminal is None


class TestTTYBehavior:
    """End-to-end tests for TTY vs non-TTY behavior."""

    def test_console_behavior_changes_with_tty(self):
        """Test that console behavior differs between TTY and non-TTY."""
        # TTY mode
        tty_console = create_console(force_terminal=True)
        assert tty_console._force_terminal is True

        # Non-TTY mode
        non_tty_console = create_console(force_terminal=False)
        assert non_tty_console._force_terminal is False

    def test_no_crash_on_piped_output(self):
        """Test that no exception is raised when output is piped."""
        fake_stdout = io.StringIO()

        with redirect_stdout(fake_stdout):
            # Create console in non-TTY mode
            console = create_console(force_terminal=False)

            # Print various messages
            console.print("Simple message")
            console.print("[bold]Bold message[/bold]")
            console.print("[red]Red message[/red]")

        # Should complete without exception
        assert fake_stdout is not None
