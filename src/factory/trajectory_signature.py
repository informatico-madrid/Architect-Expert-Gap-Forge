#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
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

import json

import dspy

# Validation: confirm TrajectorySignature output fields produce data
# parsable into AgenticTrajectory schema (Turn, SimulatedError, Message).
# This inline block runs at import time to catch schema mismatches early.
try:
    from src.factory.schema import Message, SimulatedError, Turn, TurnType

    # turns_json -> Turn
    _turn_data = json.loads(
        '{"turn_index":0,"turn_type":"observation","content":"test"}'
    )
    _turn = Turn(**_turn_data)
    assert _turn.turn_type == TurnType.OBSERVATION
    # All TurnType enum values must be parseable
    for _tt in TurnType:
        _test = Turn(turn_index=0, turn_type=_tt, content="x")
        assert _test.turn_type == _tt
    # errors_json -> SimulatedError
    _err_data = json.loads(
        '{"error_type":"tool_failure","turn_index":0,"description":"fail"}'
    )
    _err = SimulatedError(**_err_data)
    assert _err.error_type.value == "tool_failure"
    assert _err.recovery_turn_index is None
    # messages_json -> Message
    _msg_data = json.loads('{"role":"user","content":"hello"}')
    _msg = Message(**_msg_data)
    assert _msg.role == "user"
    assert _msg.content == "hello"
    del _turn_data, _turn, _tt, _test, _err_data, _err, _msg_data, _msg
    del Turn, TurnType, SimulatedError, Message, json
except ImportError:
    # Schema not yet available (e.g. during partial setup) — skip validation
    pass


class TrajectorySignature(dspy.Signature):
    """Generate a structured agentic trajectory from seed metadata.

    Input: seed_id, mode, use_case, question, context, error_probability,
    has_error, is_cascade, tool_format.

    The agent produces a turn-by-turn trajectory following this flow:
      Observation: {context} — {question}
      Reasoning: {reasoning}
      Action: Executing {tool_name}
      Error: {error_description}
      Correction: {corrective_action}
      Verification: {verification_result}

    Output: turns_json (list of {turn_index}, {turn_type}, {content}, {tool_name},
    {tool_args}, {tool_result}, {reasoning}), errors_json (list of {error_type},
    {turn_index}, {description}, {recovery_turn_index}), messages_json (list of
    {role}, {content}), and inferred_use_case (label from trajectory analysis).
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
    turns_json: str = dspy.OutputField(description="JSON string of turn log entries")
    errors_json: str = dspy.OutputField(
        description="JSON string of simulated error records"
    )
    messages_json: str = dspy.OutputField(
        description="JSON string of chat message history"
    )
    inferred_use_case: str = dspy.OutputField(
        description="Inferred use-case label from trajectory analysis"
    )
