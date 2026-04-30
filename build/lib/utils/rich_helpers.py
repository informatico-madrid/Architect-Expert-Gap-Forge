#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
AEGF Rich Helpers Module
========================
Reusable Rich utilities for terminal output in CLI applications.

Provides:
- Console instance factory with TTY detection
- Common formatting utilities (tables, panels, progress)
- Logging integration helpers
- Error handling helpers
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Sequence

from rich.console import Console
from rich.panel import Panel
from rich.table import Table


# =============================================================================
# CONSTANTS
# =============================================================================

# Default console settings
DEFAULT_STYLE = "default"
SUCCESS_STYLE = "green"
ERROR_STYLE = "red"
WARNING_STYLE = "yellow"
INFO_STYLE = "blue"
BOLD_STYLE = "bold"


# =============================================================================
# CONSOLE INSTANCE FACTORY
# =============================================================================


def create_console(
    force_terminal: bool | None = None,
    no_color: bool | None = None,
) -> Console:
    """
    Create a Console instance with appropriate settings.

    Detects TTY automatically unless force_terminal is specified.
    This ensures proper output when piped to files or other processes.

    Args:
        force_terminal: Force terminal mode regardless of TTY detection.
                       If None, auto-detect from sys.stdout.isatty().
        no_color: Disable colored output. If None, use auto-detection.

    Returns:
        Configured Console instance ready for use.

    Examples:
        >>> console = create_console()  # Auto-detect TTY
        >>> console.print("[green]Hello![/]")
        >>> console = create_console(force_terminal=False)  # Force non-TTY mode
    """
    return Console(
        force_terminal=force_terminal,
        no_color=no_color,
    )


def get_console() -> Console:
    """
    Get a shared Console instance for the module.

    Returns a single instance that can be reused across the application.
    This follows the pattern of reusing Console instances for efficiency.

    Returns:
        Shared Console instance.

    Examples:
        >>> console = get_console()
        >>> console.print("Shared console output")
    """
    # Create module-level instance that persists across function calls
    if not hasattr(get_console, "_instance"):
        get_console._instance = create_console()  # type: ignore[attr-defined]
    return get_console._instance  # type: ignore[attr-defined]


# =============================================================================
# FORMATTING UTILITIES
# =============================================================================


def print_success(
    console: Console,
    message: str,
    title: str = "Success",
    style: str = SUCCESS_STYLE,
) -> None:
    """
    Print a success message in a styled panel.

    Args:
        console: Console instance to use for output.
        message: The message to display.
        title: Panel title (default: "Success").
        style: Color/style for the panel border (default: green).

    Examples:
        >>> console = get_console()
        >>> print_success(console, "All tests passed!", title="Tests Complete")
    """
    console.print(
        Panel(
            message,
            title=f"[{style}]{title}[/]",
            border_style=style,
        )
    )


def print_error(
    console: Console,
    message: str,
    title: str = "Error",
    style: str = ERROR_STYLE,
) -> None:
    """
    Print an error message in a styled panel.

    Args:
        console: Console instance to use for output.
        message: The error message to display.
        title: Panel title (default: "Error").
        style: Color/style for the panel border (default: red).

    Examples:
        >>> console = get_console()
        >>> print_error(console, "Connection refused", title="Failed")
    """
    console.print(
        Panel(
            message,
            title=f"[{style}]{title}[/]",
            border_style=style,
        )
    )


def print_warning(
    console: Console,
    message: str,
    title: str = "Warning",
    style: str = WARNING_STYLE,
) -> None:
    """
    Print a warning message in a styled panel.

    Args:
        console: Console instance to use for output.
        message: The warning message to display.
        title: Panel title (default: "Warning").
        style: Color/style for the panel border (default: yellow).

    Examples:
        >>> console = get_console()
        >>> print_warning(console, "Low disk space", title="Caution")
    """
    console.print(
        Panel(
            message,
            title=f"[{style}]{title}[/]",
            border_style=style,
        )
    )


def print_info(
    console: Console,
    message: str,
    title: str = "Info",
    style: str = INFO_STYLE,
) -> None:
    """
    Print an informational message in a styled panel.

    Args:
        console: Console instance to use for output.
        message: The informational message to display.
        title: Panel title (default: "Info").
        style: Color/style for the panel border (default: blue).

    Examples:
        >>> console = get_console()
        >>> print_info(console, "Loading configuration...", title="Loading")
    """
    console.print(
        Panel(
            message,
            title=f"[{style}]{title}[/]",
            border_style=style,
        )
    )


def print_status(
    console: Console,
    message: str,
    style: str = BOLD_STYLE,
) -> None:
    """
    Print a status message with styled text.

    Args:
        console: Console instance to use for output.
        message: The status message to display.
        style: Text style (default: bold).

    Examples:
        >>> console = get_console()
        >>> print_status(console, "Processing files...", style="bold cyan")
    """
    console.print(f"[{style}]{message}[/]")


def create_table(
    title: str | None = None,
    show_header: bool = True,
    show_lines: bool = False,
) -> Table:
    """
    Create a configured Table instance.

    Args:
        title: Optional table title.
        show_header: Whether to show column headers (default: True).
        show_lines: Whether to show lines between rows (default: False).

    Returns:
        Configured Table instance.

    Examples:
        >>> table = create_table(title="Files Processed")
        >>> table.add_column("Name", style="cyan")
        >>> table.add_column("Size", justify="right")
        >>> table.add_row("data.json", "1.2 MB")
        >>> console.print(table)
    """
    table = Table(title=title, show_header=show_header, show_lines=show_lines)
    return table


def add_rows_to_table(
    table: Table,
    rows: Sequence[Sequence[str]],
    column_styles: list[str] | None = None,
) -> None:
    """
    Add multiple rows to a table efficiently.

    Args:
        table: The Table instance to add rows to.
        rows: List of row data (each row is a sequence of strings).
        column_styles: Optional list of styles for each column.

    Examples:
        >>> table = create_table(title="Users")
        >>> table.add_column("ID")
        >>> table.add_column("Name")
        >>> add_rows_to_table(table, [["1", "Alice"], ["2", "Bob"]])
    """
    for row in rows:
        table.add_row(*row)  # type: ignore[arg-type]


def print_table(
    console: Console,
    table: Table,
    center: bool = False,
) -> None:
    """
    Print a table to the console.

    Args:
        console: Console instance to use for output.
        table: The Table to print.
        center: Whether to center the table (default: False).

    Examples:
        >>> table = create_table(title="Summary")
        >>> table.add_column("Metric", style="bold")
        >>> table.add_column("Value", justify="right")
        >>> table.add_row("Tests", "42")
        >>> print_table(console, table)
    """
    if center:
        console.print(table)
    else:
        console.print(table)


# =============================================================================
# LOGGING INTEGRATION
# =============================================================================


def setup_rich_logging(
    logger_name: str = "AEGF",
    level: int | None = None,
    rich_tracebacks: bool = True,
) -> None:
    """
    Configure logging with RichHandler for consistent output.

    This integrates Rich with Python's logging module, providing
    consistent styled output across the application.

    Args:
        logger_name: Base name for the logger.
        level: Logging level (default: INFO).
        rich_tracebacks: Whether to show rich tracebacks for exceptions.

    Examples:
        >>> setup_rich_logging("myapp", level=logging.DEBUG)
    """
    import logging

    from rich.logging import RichHandler

    # Get or create root logger
    root_logger = logging.getLogger()

    # Clear existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Configure with RichHandler
    handler = RichHandler(
        rich_tracebacks=rich_tracebacks,
        show_time=True,
        show_path=False,
        console=get_console(),
    )

    root_logger.addHandler(handler)
    root_logger.setLevel(level or logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.

    This is a convenience wrapper that ensures consistent logger naming
    across the application.

    Args:
        name: Logger name (typically __name__).

    Returns:
        Configured Logger instance.

    Examples:
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing started")
    """
    return logging.getLogger(name)


# =============================================================================
# ERROR HANDLING
# =============================================================================


def print_exception(
    console: Console,
    exception: Exception,
    context: str | None = None,
) -> None:
    """
    Print exception information in a styled format.

    Args:
        console: Console instance to use for output.
        exception: The exception to display.
        context: Optional context message to prepend.

    Examples:
        >>> try:
        ...     risky_operation()
        ... except ValueError as e:
        ...     print_exception(console, e, "Failed to process data")
    """
    message = str(exception)

    if context:
        full_message = f"{context}: {message}"
    else:
        full_message = message

    console.print(
        Panel(
            f"[red]{type(exception).__name__}:[/]\n{full_message}",
            title="[bold red]Exception[/]",
            border_style="red",
        )
    )


def print_traceback(
    console: Console,
    exception: Exception,
    show_locals: bool = False,
) -> None:
    """
    Print a formatted traceback for an exception.

    Args:
        console: Console instance to use for output.
        exception: The exception to show traceback for.
        show_locals: Whether to show local variables in tracebacks.

    Examples:
        >>> try:
        ...     risky_operation()
        ... except Exception as e:
        ...     print_traceback(console, e, show_locals=True)
    """
    from rich.traceback import Traceback

    console.print(
        Traceback(
            exception,
            show_locals=show_locals,
            width=100,
            word_wrap=True,
        )
    )


# =============================================================================
# PROGRESS HELPERS
# =============================================================================


def create_progress_task(
    console: Console,
    description: str,
    total: int | None = None,
    completed: int = 0,
    style: str = "blue",
    task_id: str | None = None,
) -> int:
    """
    Create a progress task and return its ID.

    Note: This is a helper for manual progress management.
    For automatic progress, use the `Progress` context manager directly.

    Args:
        console: Console instance.
        description: Description of the task.
        total: Total units to complete (None for indefinite).
        completed: Initial completed count (default: 0).
        style: Progress bar style.
        task_id: Optional task ID (auto-generated if None).

    Returns:
        Task ID for updating the progress.

    Examples:
        >>> with progress := Console().status("Working..."):
        ...     task_id = create_progress_task(console, "Processing files")
        ...     for i in range(100):
        ...         progress.update(task_id, advance=1)
    """
    # Note: This function returns a task ID but the Progress context
    # should be managed by the caller. See the Progress documentation
    # for the proper usage pattern.

    return 0  # Placeholder - use Progress context manager directly


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


def format_size(size_bytes: int, suffix: str = "B") -> str:
    """
    Format a byte count into human-readable form.

    Args:
        size_bytes: Size in bytes.
        suffix: Suffix to append (default: "B").

    Returns:
        Human-readable size string (e.g., "1.5 MB").

    Examples:
        >>> format_size(1024)
        '1.0 KB'
        >>> format_size(1536000, suffix=" bytes")
        '1.5 MB bytes'
    """
    for unit in ["", "K", "M", "G", "T"]:
        if abs(size_bytes) < 1024.0:
            return f"{size_bytes:.1f} {unit}{suffix}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} Y{suffix}"


def format_duration(seconds: float, style: str = BOLD_STYLE) -> str:
    """
    Format a duration in seconds into human-readable form.

    Args:
        seconds: Duration in seconds.
        style: Text style for the output.

    Returns:
        Human-readable duration string (e.g., "1h 30m 15s").

    Examples:
        >>> format_duration(3665.5)
        '1h 1m 5s'
    """
    if seconds < 60:
        return f"[{style}]{seconds:.1f}s[/]"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"[{style}]{minutes}m {secs:.1f}s[/]"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"[{style}]{hours}h {minutes}m {secs:.1f}s[/]"


def is_tty() -> bool:
    """
    Check if stdout is a terminal.

    Returns:
        True if output is to a terminal, False otherwise.

    Examples:
        >>> if is_tty():
        ...     print("[green]Interactive mode[/]")
        ... else:
        ...     print("Piped output mode")
    """
    return sys.stdout.isatty()


def should_use_rich() -> bool:
    """
    Determine if Rich output should be used.

    Rich is appropriate when:
    - Output is to a TTY
    - OR force_terminal mode is desired

    Returns:
        True if Rich output is recommended.

    Examples:
        >>> if should_use_rich():
        ...     console = create_console()
        ...     console.print("[green]Rich output enabled[/]")
        ... else:
        ...     print("Plain text output")
    """
    return is_tty()
