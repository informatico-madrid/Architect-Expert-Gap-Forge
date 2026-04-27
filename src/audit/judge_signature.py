# SPDX-License-Identifier: Apache-2.0
"""DSPy signature for LLM-based judge evaluation.

Defines JudgeSignature — a DSPy Signature that describes the input/output
contract for the judge: five scored responses (exam question, evaluation
criteria, target patterns, baseline response, adapter response) produce
scoring dictionaries for baseline and adapter plus human-readable reasoning.
"""

import dspy


class JudgeSignature(dspy.Signature):
    """Senior Architecture 2026 Auditor — measure the Knowledge Gap closure
    between baseline and adapter responses.

    The judge evaluates both responses on five dimensions:
      - ha_modernity   — Architectural Fidelity: whether the implementation
                           strictly follows the "Laws of Architecture" from
                           the reference standards; a reasoning change that
                           does not manifest in code scores 0.0.
      - reasoning_depth — Critical Analysis: whether the <think> block
                           identifies the baseline's technical debt; if the
                           reasoning claims a fix but the code retains the
                           legacy pattern, score < 0.3 (Logic Incoherence).
      - functionality   — Engineering Execution: whether the code block
                           actually applies the 2026 standards; forbidden
                           patterns (blocking I/O, untyped runtime) are
                           functional failures.
      - completeness    — all requested fixes implemented.
      - style           — zero apologies, structured reasoning, professional
                           docstrings.

    Scoring Scale (0.0 to 1.0):
      - 0.0: Total failure or legacy code only.
      - 0.3: Identified the 2026 requirement but failed to implement it.
      - 0.6: Correct 2026 logic/API used but with syntax or minor
             architectural errors.
      - 0.9+: Production-ready Architecture 2026 code.

    Scoring Guidelines:
      - BE NUANCED: Do not give a 0.0 if there is partial progress.
      - IDENTIFICATION vs IMPLEMENTATION: Award 0.4 if the model identifies
        the error correctly in <think>, even if the code implementation is
        imperfect.
      - DELTA FOCUSED: Your primary job is to find the improvement (Delta).
        If the Adapter identifies 2026 requirements that the Baseline ignores,
        the score MUST reflect this gap.

    Input: exam_question, eval_criteria, target_patterns, baseline_response,
    adapter_response.

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
