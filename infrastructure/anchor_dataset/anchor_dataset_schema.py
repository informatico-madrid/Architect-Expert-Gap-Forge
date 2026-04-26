#!/usr/bin/env python3
# Copyright 2026 Bunker AI
# SPDX-License-Identifier: Apache-2.0
"""Pydantic models for anchor dataset records and manifests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


DSPY_FIELD_MAP: dict[str, list[str]] = {
    "inputs": ["legacy_pattern", "domain_context"],
    "labels": [
        "expected_trajectory",
        "expected_tool_usage_patterns",
        "expected_coherence",
        "expected_overall",
        "expected_quality_score",
        "expected_optimized_parameters",
    ],
}


class AnchorRecord(BaseModel):
    """A single anchor dataset sample record."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=r"^anchor_\d{3}_\d{2}$")
    domain: str = Field(pattern=r"^(home_assistant|php_legacy|generic_domain|other)$")
    difficulty: str = Field(pattern=r"^(easy|medium|hard)$")
    turn_count: int = Field(ge=1, le=10)
    legacy_pattern: str
    domain_context: str
    expected_trajectory: str = Field(min_length=5)
    expected_tool_usage_patterns: list[str] = Field(default_factory=list)
    expected_coherence: float = Field(ge=0.0, le=1.0)
    expected_overall: float = Field(ge=0.0, le=1.0)
    expected_quality_score: float = Field(ge=0.0, le=1.0)
    expected_optimized_parameters: dict[str, float] = Field(default_factory=dict)
    verified: bool = False
    verified_by: str = ""


class AnchorManifest(BaseModel):
    """Metadata about a generated anchor dataset."""

    total_samples: int
    provider: str
    cb_triggered: bool
    failed_count: int
    generation_timestamp: str
    seed_sha256: str = ""
    domain_distribution: dict = Field(
        default_factory=lambda: {
            "home_assistant": 0.4,
            "php_legacy": 0.3,
            "generic_domain": 0.2,
            "other": 0.1,
        }
    )
    difficulty_distribution: dict = Field(
        default_factory=lambda: {"easy": 0.3, "medium": 0.5, "hard": 0.2}
    )


def jsonl_to_dspy_examples(path: str) -> list[Any]:
    """Convert a JSONL file of AnchorRecords to DSPy examples.

    Requires the ``dspy`` package. Raises ``ImportError`` with guidance
    if dspy is not installed.
    """
    try:
        import dspy  # type: ignore[import-not-found,import-untyped]
    except ImportError as exc:
        raise ImportError(
            "dspy is required for jsonl_to_dspy_examples. "
            "Install it with: pip install dspy-ai"
        ) from exc

    file_path = Path(path)
    if not file_path.exists() or file_path.stat().st_size == 0:
        return []

    examples: list[dspy.Example] = []
    with file_path.open("r") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            record_dict = json.loads(line)
            record = AnchorRecord.model_validate(record_dict)
            example_fields: dict[str, Any] = {}
            for inp in DSPY_FIELD_MAP["inputs"]:
                example_fields[inp] = getattr(record, inp)
            for lbl in DSPY_FIELD_MAP["labels"]:
                example_fields[lbl] = getattr(record, lbl)
            examples.append(dspy.Example(**example_fields))

    return examples
