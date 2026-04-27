# SPDX-License-Identifier: Apache-2.0
"""DSPy signature for LLM-based judge evaluation.

Defines JudgeSignature — a DSPy Signature that describes the input/output
contract for the judge: five scored responses (exam question, evaluation
criteria, target patterns, baseline response, adapter response) produce
scoring dictionaries for baseline and adapter plus human-readable reasoning.
"""

import dspy


class JudgeSignature(dspy.Signature):
    """Evaluate and score baseline and adapter responses against exam criteria.

    Input: exam_question, eval_criteria, target_patterns, baseline_response,
    adapter_response.

    The judge scores both responses on five dimensions:
      - ha_modernity (weight 0.30): novelty and architectural innovation
      - reasoning_depth (weight 0.25): depth and coherence of reasoning
      - functionality (weight 0.25): functional correctness and completeness
      - completeness (weight 0.12): thoroughness of the response
      - style (weight 0.08): clarity and professional writing quality

    Output: baseline and adapter scored dictionaries keyed by dimension name
    with float scores, plus reasoning explaining the differential.
    """

    # --- Input fields ---
    exam_question: str = dspy.InputField(description="The exam question to evaluate")
    eval_criteria: str = dspy.InputField(description="Evaluation criteria and rubric")
    target_patterns: str = dspy.InputField(description="Target architectural patterns to look for")
    baseline_response: str = dspy.InputField(description="Baseline (reference) response for comparison")
    adapter_response: str = dspy.InputField(description="Adapter response to evaluate")

    # --- Output fields ---
    baseline: dict[str, float] = dspy.OutputField(
        description="Baseline scoring dictionary keyed by dimension with float scores"
    )
    adapter: dict[str, float] = dspy.OutputField(
        description="Adapter scoring dictionary keyed by dimension with float scores"
    )
    reasoning: str = dspy.OutputField(
        description="Human-readable reasoning explaining the differential scores"
    )
