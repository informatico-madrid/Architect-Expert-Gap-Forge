# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
AEGF Extractors Package.

This package provides pluggable language extractors for parsing source code
and extracting dependencies. It follows the adapter pattern to support
multiple programming languages while maintaining a consistent interface.

Main components:
- ExtractorAdapter: Protocol defining the extractor interface
- ParseError: Structured exception for parse failures
- Dependency: dataclass for extracted dependency information
- get_adapter(): Factory function for lazy-loading language adapters
"""

from __future__ import annotations

from src.utils.extractors.base import (
    Dependency,
    ExtractorAdapter,
    ParseError,
    ParseResult,
)

__version__ = "1.0.0"

__all__ = [
    "Dependency",
    "ExtractorAdapter",
    "ParseError",
    "ParseResult",
    "get_adapter",
]


def get_adapter(profile: str) -> ExtractorAdapter:
    """Get an extractor adapter for the given profile (lazy-loaded).

    This function lazily imports and returns the appropriate adapter for the
    given profile. This avoids import-time side effects for optional heavy parsers.

    Args:
        profile: The profile name (e.g., "python", "homeassistant").

    Returns:
        An ExtractorAdapter instance for the given profile.
    """
    from src.utils.extractors.factory import get_adapter as _get_adapter  # Lazy import

    return _get_adapter(profile)
