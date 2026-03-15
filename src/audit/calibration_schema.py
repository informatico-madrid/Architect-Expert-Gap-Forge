#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""AEGF Calibration Schema — Dataclasses for inference parameter calibration.

Defines immutable, typed data structures for the Inference Calibration Suite
(Stage 6): sampling profiles, calibration results, reports, and checkpoints.

Public API
----------
- ``SamplingProfile`` — Configuration of sampling parameters.
- ``CalibrationResult`` — Single calibration iteration result.
- ``CalibrationReport`` — Aggregated calibration results.
- ``CalibrationCheckpoint`` — Resume state for interrupted calibrations.
- ``CALIBRATION_GRID`` — Parameter grid for Cartesian product.
- ``SCORING_WEIGHTS`` — Judge score weights for composite calculation.
- ``MIN_RESPONSE_WORDS`` — Minimum word count before length penalty applies.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Final

__all__ = [
    "SamplingProfile",
    "CalibrationResult",
    "CalibrationReport",
    "CalibrationCheckpoint",
    "CalibrationPrompt",
    "CALIBRATION_GRID",
    "SCORING_WEIGHTS",
    "MIN_RESPONSE_WORDS",
    "LENGTH_PENALTY_THRESHOLD",
    "VALID_PARAMETERS",
]

# ---------------------------------------------------------------------------
# Domain constants (Final)
# ---------------------------------------------------------------------------

# Minimum word count for responses before length penalty is applied
MIN_RESPONSE_WORDS: Final[int] = 200

# Length penalty applies when response is below this threshold
LENGTH_PENALTY_THRESHOLD: Final[int] = 200

# Scoring weights for composite score calculation (from schema.py for consistency)
SCORING_WEIGHTS: Final[dict[str, float]] = {
    "ha_modernity": 0.30,
    "reasoning_depth": 0.25,
    "functionality": 0.25,
    "completeness": 0.12,
    "style": 0.08,
}

# Parameter grid for calibration (Pivot around base model values)
# Base model values: Temperature=0.6, TopP=0.95, TopK=20, MinP=0
# Grid pivots around these base values to find optimal settings
# Expanded grid for broader exploration - noxious filter will prune bad values
CALIBRATION_GRID: Final[dict[str, list[Any]]] = {
    "temperature": [0.3, 0.5, 0.6, 0.7, 0.9, 1.1],          # pivot 0.6
    "top_p": [0.7, 0.8, 0.9, 0.95, 1.0],                      # pivot 0.9
    "top_k": [5, 10, 20, 40, 60, 80],                          # pivot 20
    "min_p": [0.0, 0.02, 0.05, 0.1, 0.15],                    # pivot 0.0
    "repetition_penalty": [1.0, 1.05, 1.1, 1.15, 1.2],        # pivot 1.0
    "presence_penalty": [0.0, 0.5, 1.0, 1.5, 2.0],           # pivot 1.0 (range -2 to 2)
}

# Valid parameter names that can be targeted in calibration prompts
VALID_PARAMETERS: Final[set[str]] = {
    "temperature",
    "top_p",
    "top_k",
    "min_p",
    "repetition_penalty",
    "presence_penalty",
}


# ---------------------------------------------------------------------------
# Dataclasses (Immutable and optimized)
# ---------------------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class SamplingProfile:
    """Configuration of sampling parameters for LLM inference.

    Represents a single combination of sampling parameters to be evaluated
    during the calibration process.

    Validation (enforced via __post_init__):
    - temperature: 0.0 <= temperature <= 2.0
    - top_p: 0.0 <= top_p <= 1.0
    - top_k: 1 <= top_k <= 200
    - min_p: 0.0 <= min_p <= 1.0
    - repetition_penalty: 1.0 <= repetition_penalty <= 2.0
    - presence_penalty: 0.0 <= presence_penalty <= 2.0
    """

    temperature: float
    top_p: float
    top_k: int
    min_p: float
    repetition_penalty: float
    presence_penalty: float | None = None

    def __post_init__(self) -> None:
        """Validate sampling parameters after initialization."""
        # Temperature validation
        if not (0.0 <= self.temperature <= 2.0):
            raise ValueError(
                f"temperature must be in range [0.0, 2.0], got {self.temperature}"
            )

        # top_p validation
        if not (0.0 <= self.top_p <= 1.0):
            raise ValueError(
                f"top_p must be in range [0.0, 1.0], got {self.top_p}"
            )

        # top_k validation
        if not (1 <= self.top_k <= 200):
            raise ValueError(
                f"top_k must be in range [1, 200], got {self.top_k}"
            )

        # min_p validation
        if not (0.0 <= self.min_p <= 1.0):
            raise ValueError(
                f"min_p must be in range [0.0, 1.0], got {self.min_p}"
            )

        # repetition_penalty validation
        if not (1.0 <= self.repetition_penalty <= 2.0):
            raise ValueError(
                f"repetition_penalty must be in range [1.0, 2.0], "
                f"got {self.repetition_penalty}"
            )

        # presence_penalty validation (if provided)
        if self.presence_penalty is not None:
            if not (-2.0 <= self.presence_penalty <= 2.0):
                raise ValueError(
                    f"presence_penalty must be in range [-2.0, 2.0] if provided, "
                    f"got {self.presence_penalty}"
                )

    def to_dict(self) -> dict[str, Any]:
        """Controlled serialization for JSON persistence."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SamplingProfile:
        """Create a SamplingProfile from a dictionary."""
        return cls(
            temperature=float(data["temperature"]),
            top_p=float(data.get("top_p", 0.9)),
            top_k=int(data["top_k"]),
            min_p=float(data["min_p"]),
            repetition_penalty=float(data["repetition_penalty"]),
            presence_penalty=data.get("presence_penalty"),
        )

    def __str__(self) -> str:
        """Human-readable representation."""
        return (
            f"SamplingProfile(t={self.temperature}, k={self.top_k}, "
            f"min_p={self.min_p}, rep_pen={self.repetition_penalty})"
        )


@dataclass(slots=True, frozen=True)
class CalibrationResult:
    """Result of a single calibration iteration.

    Contains the sampling profile used, judge scores, computed composite
    and adjusted scores, and metadata about the response.
    """

    profile: SamplingProfile
    exam_id: str
    judge_scores: dict[str, float]
    composite_score: float
    adjusted_score: float
    response_length: int
    timestamp: str
    response_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Controlled serialization for JSON persistence."""
        return {
            "profile": self.profile.to_dict(),
            "exam_id": self.exam_id,
            "judge_scores": self.judge_scores,
            "composite_score": self.composite_score,
            "adjusted_score": self.adjusted_score,
            "response_length": self.response_length,
            "timestamp": self.timestamp,
            "response_text": self.response_text,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CalibrationResult:
        """Create a CalibrationResult from a dictionary."""
        return cls(
            profile=SamplingProfile.from_dict(data["profile"]),
            exam_id=data["exam_id"],
            judge_scores=data["judge_scores"],
            composite_score=data["composite_score"],
            adjusted_score=data["adjusted_score"],
            response_length=data["response_length"],
            timestamp=data["timestamp"],
            response_text=data.get("response_text", ""),
        )


@dataclass(slots=True, frozen=True)
class CalibrationReport:
    """Aggregated calibration results for a complete calibration run.

    Contains all iteration results, the best profile found, and
    statistical summary of the calibration process.
    """

    timestamp: str
    total_iterations: int
    best_profile: SamplingProfile
    best_score: float
    all_results: list[CalibrationResult]
    statistics: dict[str, Any] = field(default_factory=dict)
    prompt_count: int = 0
    focus_analysis: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Controlled serialization for JSON persistence."""
        return {
            "timestamp": self.timestamp,
            "total_iterations": self.total_iterations,
            "best_profile": self.best_profile.to_dict(),
            "best_score": self.best_score,
            "all_results": [r.to_dict() for r in self.all_results],
            "statistics": self.statistics,
            "prompt_count": self.prompt_count,
            "focus_analysis": self.focus_analysis,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CalibrationReport:
        """Create a CalibrationReport from a dictionary."""
        return cls(
            timestamp=data["timestamp"],
            total_iterations=data["total_iterations"],
            best_profile=SamplingProfile.from_dict(data["best_profile"]),
            best_score=data["best_score"],
            all_results=[
                CalibrationResult.from_dict(r) for r in data["all_results"]
            ],
            statistics=data.get("statistics", {}),
            prompt_count=data.get("prompt_count", 0),
            focus_analysis=data.get("focus_analysis", {}),
        )


@dataclass(slots=True, frozen=True)
class CalibrationCheckpoint:
    """Resume state for interrupted calibration runs.

    Stores the current progress so calibration can be resumed from
    where it left off after interruption.
    """

    timestamp: str
    current_prompt_idx: int
    current_profile_idx: int
    completed_profiles: list[tuple[int, int]]  # (prompt_idx, profile_idx)
    all_results: list[CalibrationResult]
    total_profiles: int
    total_prompts: int

    def to_dict(self) -> dict[str, Any]:
        """Controlled serialization for JSON persistence."""
        return {
            "timestamp": self.timestamp,
            "current_prompt_idx": self.current_prompt_idx,
            "current_profile_idx": self.current_profile_idx,
            "completed_profiles": self.completed_profiles,
            "all_results": [r.to_dict() for r in self.all_results],
            "total_profiles": self.total_profiles,
            "total_prompts": self.total_prompts,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CalibrationCheckpoint:
        """Create a CalibrationCheckpoint from a dictionary."""
        return cls(
            timestamp=data["timestamp"],
            current_prompt_idx=data["current_prompt_idx"],
            current_profile_idx=data["current_profile_idx"],
            completed_profiles=data["completed_profiles"],
            all_results=[
                CalibrationResult.from_dict(r) for r in data["all_results"]
            ],
            total_profiles=data["total_profiles"],
            total_prompts=data["total_prompts"],
        )

    @property
    def progress_percentage(self) -> float:
        """Calculate completion percentage."""
        total = self.total_prompts * self.total_profiles
        if total == 0:
            return 0.0
        return (len(self.completed_profiles) / total) * 100


@dataclass(slots=True, frozen=True)
class CalibrationPrompt:
    """A calibration prompt with metadata for intelligent parameter targeting.

    Contains the prompt text along with parameter_target and evaluation_focus
    fields that guide the intelligent calibration analysis (Phase 9/US5).

    The parameter_target field specifies which sampling parameters this prompt
    is designed to test. The evaluation_focus field describes what aspect
    of model behavior should be evaluated (e.g., creativity, reasoning depth,
    obedience to constraints).
    """

    id: str
    question: str
    type: str
    parameter_target: list[str]
    evaluation_focus: str

    def __post_init__(self) -> None:
        """Validate parameter_target contains valid parameter names."""
        for param in self.parameter_target:
            if param not in VALID_PARAMETERS:
                raise ValueError(
                    f"Invalid parameter '{param}'. Must be one of: {VALID_PARAMETERS}"
                )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CalibrationPrompt:
        """Create a CalibrationPrompt from a dictionary.

        Handles both direct list format and comma-separated string format
        for parameter_target field.

        Args:
            data: Dictionary with prompt data. Expected keys: id, question,
                  type, parameter_target, evaluation_focus.

        Returns:
            CalibrationPrompt instance.
        """
        # Handle parameter_target as either list or comma-separated string
        param_target = data.get("parameter_target", [])
        if isinstance(param_target, str):
            # Parse comma-separated string
            param_target = [
                p.strip() for p in param_target.split(",") if p.strip()
            ]

        return cls(
            id=str(data["id"]),
            question=str(data["question"]),
            type=str(data.get("type", "investigation")),
            parameter_target=list(param_target),
            evaluation_focus=str(data.get("evaluation_focus", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        """Controlled serialization for JSON/YAML persistence."""
        return {
            "id": self.id,
            "question": self.question,
            "type": self.type,
            "parameter_target": ", ".join(self.parameter_target),
            "evaluation_focus": self.evaluation_focus,
        }

    def get_parameter_target_set(self) -> set[str]:
        """Return parameter_target as a set for O(1) lookup."""
        return set(self.parameter_target)
