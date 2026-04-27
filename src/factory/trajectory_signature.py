# SPDX-License-Identifier: Apache-2.0
"""DSPy signature for agentic trajectory generation.

Defines TrajectorySignature — a DSPy Signature that describes what the
trajectory generator produces: turns, errors, and messages as JSON strings,
plus the inferred use case.

Note: DSPy (Pydantic) cannot have the same name as both InputField and
OutputField in a single Signature class definition. The input 'use_case'
carries the known use-case seed; the output 'inferred_use_case' carries the
generated use-case label.
"""

import dspy


class TrajectorySignature(dspy.Signature):
    """Generate a structured agentic trajectory from seed data.

    Takes seed metadata and context, then produces JSON-serialized turn logs,
    error records, chat messages, and an inferred use-case label.
    """

    # --- Input fields ---
    seed_id: str = dspy.InputField(description="Unique identifier for the seed")
    mode: str = dspy.InputField(description="Execution mode")
    use_case: str = dspy.InputField(description="Known use case category")
    question: str = dspy.InputField(description="User question or prompt")
    context: str = dspy.InputField(description="Additional context for generation")
    error_probability: float = dspy.InputField(
        description="Probability of simulating an error"
    )
    has_error: bool = dspy.InputField(description="Whether an error is simulated")
    is_cascade: bool = dspy.InputField(description="Whether error cascades")
    tool_format: str = dspy.InputField(description="Tool output format specification")

    # --- Output fields ---
    turns_json: str = dspy.OutputField(
        description="JSON string of turn log entries"
    )
    errors_json: str = dspy.OutputField(
        description="JSON string of simulated error records"
    )
    messages_json: str = dspy.OutputField(
        description="JSON string of chat message history"
    )
    inferred_use_case: str = dspy.OutputField(
        description="Inferred use-case label from trajectory analysis"
    )
