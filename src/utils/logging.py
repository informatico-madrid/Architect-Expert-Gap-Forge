#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Architect-Expert-Gap-Forge (AEGF) - Logging Utilities

Centralized logging configuration for uniform imports across the codebase.
Provides a helper function to get configured loggers with consistent settings.

SPDX-License-Identifier: Apache-2.0
Copyright 2026 AEGF
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Final

# Default logging format for all AEGF loggers
_DEFAULT_FORMAT: Final[str] = "%(asctime)s | %(name)-30s | %(levelname)-8s | %(message)s"
_DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance.

    This helper provides uniform logger configuration across the codebase.
    All loggers use RichHandler for consistent terminal output with
    automatic TTY detection (works in terminals and when piped).

    Args:
        name: The logger name, typically __name__ from the calling module.

    Returns:
        A configured Logger instance with RichHandler for formatted output.

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing %d records", count)
    """
    logger = logging.getLogger(name)

    # Only configure if not already configured (avoid duplicate handlers)
    if not logger.handlers and not logger.parent.handlers:
        from rich.logging import RichHandler

        # Use RichHandler for consistent terminal output
        # Automatically detects TTY and adjusts output accordingly
        handler = RichHandler(
            rich_tracebacks=False,
            show_time=True,
            show_path=False,
            console=None,  # Auto-detect from sys.stderr
        )
        handler.setFormatter(logging.Formatter(fmt=_DEFAULT_FORMAT, datefmt=_DATE_FORMAT))
        logger.addHandler(handler)
        logger.propagate = False

    # Set default level if not set
    if logger.level == logging.NOTSET:
        logger.setLevel(logging.INFO)

    return logger
