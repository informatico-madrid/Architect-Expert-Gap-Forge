#!/usr/bin/env python3
# Copyright 2025
# SPDX-License-Identifier: Apache-2.0

"""Schema definitions for anchor dataset records and manifests."""

import json
import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class AnchorRecord(BaseModel):
    """Pydantic v2 model for a single anchor training sample.

    Frozen to ensure immutability after construction.
    All fields have descriptive documentation.
    """

    model_config = {"frozen": True, "extra": "forbid"}

    id: str = Field(
        description="Unique identifier following anchor_{seed_pool:03d}_{variant:02d} pattern"
    )
    domain: Literal["home_assistant", "php_legacy", "generic_domain", "other"] = Field(
        description="Domain category for the anchor sample"
    )
    difficulty: Literal["easy", "medium", "hard"] = Field(
        description="Difficulty level of the anchor sample"
    )
    turn_count: int = Field(gt=0, description="Expected number of user turns in trajectory")
    legacy_pattern: str = Field(min_length=1, description="Legacy code pattern or pattern category")
    domain_context: str = Field(min_length=1, description="Technical background and context")
    expected_trajectory: str = Field(
        min_length=1,
        description="Multi-turn conversation trajectory with role markers"
    )
    expected_tool_usage_patterns: list[str] = Field(
        default_factory=list,
        description="Expected tool call patterns observed in the trajectory"
    )
    expected_coherence: float = Field(
        ge=0.0, le=1.0, description="Self-assessed coherence score"
    )
    expected_overall: float = Field(
        ge=0.0, le=1.0, description="Self-assessed overall quality score"
    )
    expected_optimized_parameters: dict[str, Any] = Field(
        default_factory=dict, description="Optimized hyperparameters for this sample"
    )
    expected_quality_score: float = Field(
        ge=0.0, le=1.0, description="Self-assessed quality score threshold"
    )
    verified: bool = Field(default=False, description="Whether sample has been verified")
    verified_by: str = Field(default="", description="Verifier identifier")

    @field_validator("id")
    @classmethod
    def validate_id_pattern(cls, v: str) -> str:
        """Validate ID matches anchor_{number}_{number} pattern."""
        if not re.match(r"^anchor_\d+_\d+$", v):
            raise ValueError(
                f"ID must match pattern 'anchor_{{number}}_{{number}}', got: {v}"
            )
        return v


class AnchorManifest(BaseModel):
    """Metadata manifest for an anchor dataset output."""

    model_config = {"frozen": True}

    version: str = Field(default="v1", description="Dataset version identifier")
    created: str = Field(description="ISO8601 timestamp of dataset creation")
    total_samples: int = Field(gt=0, description="Total number of samples in dataset")
    domain_distribution: dict[str, int] = Field(
        description="Count of samples per domain"
    )
    difficulty_distribution: dict[str, int] = Field(
        description="Count of samples per difficulty level"
    )
    provider_used: str = Field(description="LLM provider used for generation")
    circuit_breaker_triggered: bool = Field(
        default=False, description="Whether circuit breaker was triggered"
    )
    failed_sample_count: int = Field(default=0, description="Number of failed samples")


DSPY_FIELD_MAP: dict[str, list[str]] = {
    "inputs": [
        "id",
        "domain",
        "difficulty",
        "turn_count",
        "legacy_pattern",
        "domain_context",
    ],
    "labels": [
        "expected_trajectory",
        "expected_tool_usage_patterns",
        "expected_coherence",
        "expected_overall",
        "expected_quality_score",
        "expected_optimized_parameters",
    ],
}


def jsonl_to_dspy_examples(path: str) -> list:
    """Convert a JSONL file of AnchorRecords to DSPy Examples.

    Imports dspy lazily. Raises ImportError if dspy is not installed.
    Returns empty list for empty files.
    """
    # Check if file is empty first - return [] without needing dspy
    with open(path) as f:
        first_line = f.readline()
        if not first_line or not first_line.strip():
            return []

    # File has content - now import dspy
    try:
        import dspy  # type: ignore
    except ImportError:
        raise ImportError(
            "dspy is not installed. Install it with: pip install dspy-ai"
        )

    examples = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            example = dspy.Example(**{
                k: data[k] for k in DSPY_FIELD_MAP["inputs"] if k in data
            })
            example.set_labels({
                k: data[k] for k in DSPY_FIELD_MAP["labels"] if k in data
            })
            examples.append(example)
    return examples
