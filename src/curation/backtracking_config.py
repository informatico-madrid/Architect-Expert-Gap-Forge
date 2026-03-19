#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Backtracking rewriter configuration and data structures.

This module provides immutable configuration dataclasses for the
backtracking rewrite pipeline.

Public API
----------
BacktrackingConfig        -- Immutable pipeline configuration
PipelineReport            -- Immutable run summary
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

__all__ = [
    "BacktrackingConfig",
    "PipelineReport",
    "load_backtracking_config",
]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Canonical paths for required prompt template files.
# Copy the corresponding .example file to create them on a fresh checkout:
#   cp configs/prompts/backtracking_system.txt.example configs/prompts/backtracking_system.txt
#   cp configs/prompts/reconstruction_system.txt.example configs/prompts/reconstruction_system.txt
_PROMPT_BACKTRACKING_PATH: str = "configs/prompts/backtracking_system.txt"
_PROMPT_RECONSTRUCTION_PATH: str = "configs/prompts/reconstruction_system.txt"
_DEFAULT_LEGACY_PATTERNS_FILE: str = "configs/stage_5_evaluation/ha_patterns.yaml"


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class BacktrackingConfig:
    """Immutable configuration for the backtracking rewriter pipeline."""

    max_tokens: int = 4000
    excluded_types: tuple[str, ...] = ("theory",)
    vllm_api_url: str = "http://localhost:8000/v1"
    vllm_model: str = "qwen3-30b-a3b-thinking-fp8"
    temperature: float = 0.6
    max_generation_tokens: int = 3000
    batch_size: int = 10
    seed: int = 42
    workers: int = 8
    audit_dir: str | None = None
    # Optional paths to external prompt template files.
    # When None the built-in fallback strings are used.
    backtracking_system_prompt_path: str | None = None
    reconstruction_system_prompt_path: str | None = None
    # Governance context injection: path to the directory containing HA_MASTER_GUIDE_2026.md.
    gap_dir: str = "data/Gap"
    # Maximum characters of the governance document to inject in user prompts.
    # The full HA_MASTER_GUIDE_2026.md is ~5 200 chars — 0 means no truncation.
    governance_context_chars: int = 5200
    # Optional explicit language to enforce for all rewrites (e.g. "Spanish").
    # When ``None`` the rewriter will auto-detect language per-record.
    # This value is injected into the user prompt as a neutral token and
    # does not perform any translation within the Python code.
    language: str | None = None
    # Path to YAML file with legacy_patterns regex entries used for
    # post-generation rejection sampling.  When set, the *resolution half*
    # of a generated think block is checked against these patterns.
    # Records whose resolution still mentions legacy code are discarded.
    # Set to ``None`` to disable the check entirely.
    legacy_patterns_file: str | None = _DEFAULT_LEGACY_PATTERNS_FILE


@dataclass(slots=True, frozen=True)
class PipelineReport:
    """Immutable summary of a backtracking rewrite run."""

    total_input: int
    filtered_out: int
    rewritten: int
    pass_through: int
    failed: int
    rejected: int
    total_output: int
    strategy_counts: dict[str, int]


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------


def load_backtracking_config(path: Path) -> BacktrackingConfig:
    """Load config from a YAML file, merging with defaults."""
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    # Convert list to tuple for frozen dataclass
    if "excluded_types" in data and isinstance(data["excluded_types"], list):
        data["excluded_types"] = tuple(data["excluded_types"])

    # Only pass known fields
    known_fields = {f.name for f in BacktrackingConfig.__dataclass_fields__.values()}
    filtered = {k: v for k, v in data.items() if k in known_fields}
    return BacktrackingConfig(**filtered)
