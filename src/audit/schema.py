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
from typing import Any, Final, TypedDict

__all__ = [
    # TypedDicts (legacy names for backwards compatibility)
    "SampleRecordTD",
    "ExamRecordTD",
    # Dataclasses (primary exports)
    "SampleRecord",
    "ExamRecord",
    "NormalizedJudgeResponse",
    "InferenceResult",
    "ScoreCard",
    "AuditReport",
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

# Weights for Stage 6: Calibration (direct evaluation)
# These weights prioritize parameter effectiveness over general quality
CALIBRATION_SCORING_WEIGHTS: Final[dict[str, float]] = {
    "parameter_effectiveness": 0.30,
    "task_completion": 0.20,
    "parameter_alignment": 0.25,
    "coherence": 0.15,
    "style": 0.10,
}

# ---------------------------------------------------------------------------
# TypedDicts (immutable structured data contracts)
# ---------------------------------------------------------------------------


class SampleRecordTD(TypedDict):
    """Evaluation record with conversation and metadata (legacy TypedDict)."""

    id: str
    conversation: list[dict]
    metadata: dict


class ExamRecordTD(TypedDict):
    """Exam question with evaluation criteria and target patterns (legacy TypedDict)."""

    sample_id: str
    exam_question: str
    eval_criteria: list[str]
    target_patterns: list[str]
    reference_standards: str
    gap_analysis: str


class NormalizedJudgeResponse(TypedDict):
    """Normalized response from the LLM judge."""

    baseline: dict[str, float]
    adapter: dict[str, float]
    reasoning: str


# ---------------------------------------------------------------------------
# Backward compatibility - factory functions
# ---------------------------------------------------------------------------


def exam_record_from_sample(sample: SampleRecord, **kwargs: Any) -> ExamRecord:
    """Create an ExamRecord from a SampleRecord.

    This function provides backward compatibility for code that previously used
    ExamRecord.from_sample().
    """
    return ExamRecord.from_sample(sample, **kwargs)


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
    """Evaluation record extracted from the original dataset (dataclass version)."""

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
    """Extension of SampleRecord that includes the generated exam (dataclass version)."""

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
    """ScoreCard with original field structure (backward compatibility)."""

    record_id: str
    example_type: str
    fragment_name: str
    sample_id: str = ""  # Alias for record_id (used by report_writer)
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
class ScoreCardTD:
    """Multi-dimensional evaluation of a response produced by the judge (legacy)."""

    sample_id: str
    dimensions: dict[str, float]
    composite_score: float
    delta_vs_baseline: float
    grade: str
    verdict: str
    notes: list[str] = field(default_factory=list)
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
