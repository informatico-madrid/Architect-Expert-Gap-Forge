#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""AEGF Evaluation Schema — Dataclasses and exceptions for the evaluation pipeline.

Defines immutable, typed data structures to guarantee the integrity of the
flow: sampling -> exam -> inference -> score.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Final

__all__ = [
    "SampleRecord",
    "InferenceResult",
    "ScoreCard",
    "AuditReport",
    "ExamRecord",
    "PromptGenerationError",
    "SCORING_WEIGHTS",
    "EXAMPLE_TYPES",
]

# ---------------------------------------------------------------------------
# Domain constants (Final)
# ---------------------------------------------------------------------------

EXAMPLE_TYPES: Final[list[str]] = ["nominal", "contrast", "error_recovery", "theory"]

SCORING_WEIGHTS: Final[dict[str, float]] = {
    "ha_modernity": 0.30,
    "reasoning_depth": 0.25,
    "functionality": 0.25,
    "completeness": 0.12,
    "style": 0.08,
}

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class PromptGenerationError(Exception):
    """Raised when synthesis of an exam or evaluation fails."""


# ---------------------------------------------------------------------------
# Dataclasses (Immutable and optimized)
# ---------------------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class SampleRecord:
    """Evaluation record extracted from the original dataset."""

    id: str
    example_type: str
    evol_difficulty: str
    fragment_name: str
    source_file: str
    user_prompt: str
    reference_response: str
    gold_injected: bool
    ldi: float
    reference_standards: str = ""
    gap_analysis: str = ""


@dataclass(slots=True, frozen=True)
class ExamRecord(SampleRecord):
    """Extension of SampleRecord that includes the generated exam."""

    exam_question: str = ""
    eval_criteria: list[str] = field(default_factory=list)
    target_patterns: list[str] = field(default_factory=list)

    @classmethod
    def from_sample(cls, sample: SampleRecord, **kwargs: Any) -> ExamRecord:
        """Factory method to elevate a SampleRecord to an ExamRecord."""
        return cls(**{**asdict(sample), **kwargs})


@dataclass(slots=True, frozen=True)
class InferenceResult:
    """Inference result from a model for an exam question."""

    record_id: str
    model_name: str
    response: str
    latency_ms: float
    token_count: int
    timestamp: str


@dataclass(slots=True, frozen=True)
class ScoreCard:
    """Multi-dimensional evaluation of a response produced by the judge."""

    record_id: str
    example_type: str
    fragment_name: str
    ha_modernity: float = 0.0
    reasoning_depth: float = 0.0
    functionality: float = 0.0
    completeness: float = 0.0
    style: float = 0.0
    composite_score: float = 0.0
    delta_vs_baseline: float = 0.0
    judge_reasoning: str = ""
    notes: str = ""


@dataclass(slots=True, frozen=True)
class AuditReport:
    """Aggregated final report for an audit session."""

    timestamp: str = ""
    dataset_path: str = ""
    base_model: str = ""
    adapter_model: str = ""
    judge_model: str = ""
    sample_size: int = 0
    type_distribution: dict[str, int] = field(default_factory=dict)
    scorecards: list[ScoreCard] = field(default_factory=list)
    final_grade: float = 0.0
    verdict: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Controlled serialization for JSON persistence."""
        return asdict(self)
