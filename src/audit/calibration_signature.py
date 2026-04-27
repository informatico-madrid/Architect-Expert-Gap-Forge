# SPDX-License-Identifier: Apache-2.0
"""DSPy signature for sampling profile calibration optimization.

Defines CalibrationSignature — a DSPy Signature that describes the input/output
contract for the calibration process: structured parameter targets, quality
metrics, and judge scores produce the best sampling profile as JSON, along
with effectiveness metrics and reasoning.
"""

import dspy
from typing import Dict, List


class CalibrationSignature(dspy.Signature):
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
    top_k, min_p, quality_target, judge_scores, composite_score.

    Output: best_profile_json (JSON string with temperature, top_k, min_p,
    repetition_penalty, presence_penalty), composite_score, reasoning,
    and parameter_effectiveness (0.0–1.0).
    """

    # --- Input fields ---
    parameter_target: List[str] = dspy.InputField(
        description="Structured list of parameter targets to optimize"
    )
    evaluation_focus: str = dspy.InputField(
        description="Focus area for evaluation"
    )
    question: str = dspy.InputField(
        description="Question or prompt to calibrate against"
    )
    temperature: float = dspy.InputField(
        description="Current temperature setting"
    )
    top_k: int = dspy.InputField(
        description="Current top-k setting"
    )
    min_p: float = dspy.InputField(
        description="Current min-p setting"
    )
    quality_target: str = dspy.InputField(
        description="Target quality level or dimension"
    )
    judge_scores: Dict[str, float] = dspy.InputField(
        description="Judge scoring dictionary keyed by dimension with float scores"
    )
    composite_score: float = dspy.InputField(
        description="Weighted composite score from all dimensions"
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
