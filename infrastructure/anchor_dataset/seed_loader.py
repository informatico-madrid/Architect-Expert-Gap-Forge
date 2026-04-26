#!/usr/bin/env python3
# Copyright 2026 Bunker AI
# SPDX-License-Identifier: Apache-2.0
# -*- coding: utf-8 -*-
"""
Anchor Dataset — Seed Loader

Load and normalize seed data from YAML fixtures.
Seeds are tagged by domain (home_assistant / php_legacy).

SPDX-License-Identifier: Apache-2.0
Copyright 2026 AEGF
"""

#!/usr/bin/env python3
# Copyright 2026 Bunker AI
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_SEED_FILE = Path(__file__).resolve().parent.parent.parent / "tests" / "fixtures" / "seed_examples.yaml"


@dataclass
class NormalizedSeed:
    """Normalized seed extracted from YAML fixture."""

    seed_id: str
    domain: str
    category: str
    complexity: str
    context: str
    question: str
    expected_patterns: list[str]


def _normalize_seed(raw: dict[str, Any], domain: str) -> NormalizedSeed:
    """Convert raw YAML seed dict into NormalizedSeed."""
    return NormalizedSeed(
        seed_id=str(raw["seed_id"]),
        domain=domain,
        category=str(raw["category"]),
        complexity=str(raw["complexity"]),
        context=str(raw["context"]).strip(),
        question=str(raw["question"]).strip(),
        expected_patterns=[str(p) for p in raw.get("expected_patterns", [])],
    )


def load_seeds(seed_file: Path | None = None) -> list[NormalizedSeed]:
    """Load and normalize seeds from YAML fixture.

    Returns NormalizedSeed objects tagged by domain:
    - home_assistant for top-level ``seeds`` list
    - php_legacy for ``php_legacy_seeds`` list

    Args:
        seed_file: Path to YAML file. Defaults to built-in fixture path.

    Returns:
        List of NormalizedSeed. Empty list if file missing.
    """
    path = seed_file or _SEED_FILE

    try:
        import yaml
    except ImportError:
        logger.info("PyYAML not installed — no seeds available")
        return []

    if not path.exists():
        logger.info("Seed file not found, continuing with empty seed list")
        return []

    with open(path) as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict) or "seeds" not in data:
        logger.info("Seed file has no 'seeds' key, continuing with empty seed list")
        return []

    seeds: list[NormalizedSeed] = []

    # Top-level seeds → home_assistant domain
    for raw in data.get("seeds", []):
        if isinstance(raw, dict):
            seeds.append(_normalize_seed(raw, "home_assistant"))

    # PHP legacy seeds
    for raw in data.get("php_legacy_seeds", []):
        if isinstance(raw, dict):
            seeds.append(_normalize_seed(raw, "php_legacy"))

    return seeds
