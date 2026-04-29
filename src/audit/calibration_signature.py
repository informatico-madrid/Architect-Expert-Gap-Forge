#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0
"""DSPy signature for sampling profile calibration optimization.

Defines CalibrationSignature — a DSPy Signature that describes the input/output
contract for the calibration process: structured parameter targets, quality
metrics, and judge scores produce the best sampling profile as JSON, along
with effectiveness metrics and reasoning.
"""

import dspy
from pydantic.fields import FieldInfo
from typing import Dict


# Validation: confirm SamplingProfile and CalibrationResult schemas are
# consistent with what CalibrationSignature expects.
# This inline block runs at import time to catch schema mismatches early.
try:
    from src.audit.calibration_schema import (
        CalibrationResult,
        SamplingProfile,
        VALID_PARAMETERS,
    )
    import json

    # best_profile_json must parse into JSON with SamplingProfile fields
    _sample_json = (
        '{"temperature": 0.6, "top_k": 20, "min_p": 0.05, '
        '"repetition_penalty": 1.1, "presence_penalty": 1.0}'
    )
    _profile_dict = json.loads(_sample_json)
    _profile = SamplingProfile.from_dict(_profile_dict)
    assert isinstance(_profile.temperature, float)
    assert isinstance(_profile.top_k, int)
    assert isinstance(_profile.min_p, float)
    assert isinstance(_profile.repetition_penalty, float)

    # VALID_PARAMETERS must contain expected names
    assert VALID_PARAMETERS == {
        "temperature",
        "top_k",
        "min_p",
        "repetition_penalty",
        "presence_penalty",
    }

    # CalibrationResult must accept SamplingProfile + float fields
    _cr = CalibrationResult(
        profile=_profile,
        exam_id="test-1",
        judge_scores={"ha_modernity": 0.9},
        composite_score=0.85,
        adjusted_score=0.85,
        response_length=500,
        timestamp="2026-01-01T00:00:00Z",
    )
    assert isinstance(_cr.profile, SamplingProfile)
    assert isinstance(_cr.composite_score, float)
    del _sample_json, _profile_dict, _profile, _cr
    del SamplingProfile, CalibrationResult, VALID_PARAMETERS, json
except ImportError:
    # Schema not yet available (e.g. during partial setup) — skip validation
    pass


class _CalibrationSignature(dspy.Signature):
    """Optimize sampling parameters to maximize quality for a target architecture.

    The calibration process performs a grid search over sampling parameter
    candidates and identifies the best configuration. It evaluates each
    candidate against structured parameter targets (a list[str] of parameter
    names such as temperature, top_k, min_p, repetition_penalty, and
    presence_penalty) to determine which grid point maximizes quality.

    **parameter_target** is a structured InputField of type list[str], not
    embedded as plain text in the system prompt. Each element identifies a
    single sampling parameter to tune.

    The process evaluates judge scores across multiple dimensions and computes
    a weighted composite score. The model selects the best profile from the
    candidate grid, produces a JSON profile, and explains the reasoning behind
    the selection.

    Input: parameter_target (list[str]), evaluation_focus, question, temperature,
    top_k, min_p, quality_target, judge_scores.

    Output: best_profile_json (JSON string with temperature, top_k, min_p,
    repetition_penalty, presence_penalty), composite_score, reasoning,
    and parameter_effectiveness (0.0–1.0).
    """

    # --- Input fields ---
    parameter_target: list[str] = dspy.InputField(
        description="Structured list of parameter targets to optimize"
    )
    evaluation_focus: str = dspy.InputField(description="Focus area for evaluation")
    question: str = dspy.InputField(
        description="Question or prompt to calibrate against"
    )
    temperature: float = dspy.InputField(description="Current temperature setting")
    top_k: int = dspy.InputField(description="Current top-k setting")
    min_p: float = dspy.InputField(description="Current min-p setting")
    quality_target: str = dspy.InputField(
        description="Target quality level or dimension"
    )
    judge_scores: Dict[str, float] = dspy.InputField(
        description="Judge scoring dictionary keyed by dimension with float scores"
    )

    # --- Output fields ---
    best_profile_json: str = dspy.OutputField(
        description="JSON string of best sampling profile with temperature, top_k, min_p, repetition_penalty, presence_penalty"
    )
    composite_score: float = dspy.OutputField(
        description="Expected composite score with the best profile"
    )
    reasoning: str = dspy.OutputField(
        description="Human-readable reasoning for the profile selection"
    )
    parameter_effectiveness: float = dspy.OutputField(
        description="Effectiveness metric (0.0-1.0) of current parameters"
    )


# Wrapper to expose composite_score in both input and output fields.
# DSPy (Pydantic) cannot have the same name as both InputField and
# OutputField in a single Signature class definition. The output
# 'composite_score' carries the best profile's expected composite score;
# the input version (added by the wrapper) carries the input composite score.
class _CalibrationSignatureWrapper:
    """Wrapper that exposes composite_score in both input and output fields."""

    def __init__(self, cls: type) -> None:
        self._cls = cls

    @property
    def input_fields(self) -> dict[str, FieldInfo]:
        d = dict(self._cls.input_fields)
        d["composite_score"] = FieldInfo(
            annotation=float,
            description="Weighted composite score from all dimensions",
            json_schema_extra={
                "__dspy_field_type": "input",
                "desc": "Weighted composite score from all dimensions",
                "prefix": "Composite Score:",
            },
        )
        return d

    @property
    def output_fields(self) -> dict[str, FieldInfo]:
        return self._cls.output_fields

    @property
    def __doc__(self) -> str | None:  # type: ignore[override]
        return self._cls.__doc__

    def __getattr__(self, name: str) -> object:
        return getattr(self._cls, name)


CalibrationSignature = _CalibrationSignatureWrapper(_CalibrationSignature)
