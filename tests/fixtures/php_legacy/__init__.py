#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Fixtures for PHP legacy driver testing."""

from __future__ import annotations

from pathlib import Path

FIXTURES_DIR = Path(__file__).parent


def load_php_fixture(filename: str) -> str:
    """Load a PHP fixture file as raw string.

    Args:
        filename: Name of the fixture file (e.g., 'oscommerce_categories.php')

    Returns:
        Raw content of the PHP fixture file.

    Raises:
        FileNotFoundError: If the fixture file does not exist.
    """
    path = FIXTURES_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"PHP fixture not found: {path}")
    return path.read_text(encoding="utf-8")


def list_php_fixtures() -> list[str]:
    """List all available PHP fixture files.

    Returns:
        List of fixture filenames.
    """
    return [f.name for f in FIXTURES_DIR.glob("*.php")]


# Known fixture files (to be added in T002-T004)
# - oscommerce_categories.php
# - wordpress_ajax_actions.php
# - zencart_customers.php
