#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Architect-Expert-Gap-Forge (AEGF) - Factory Schema Definitions

Factory-specific Pydantic v2 immutable models for agentic trajectory generation.
Includes turn types, trajectory modes, error simulation, and trajectory structures.

SPDX-License-Identifier: Apache-2.0
Copyright 2026 AEGF
"""

from enum import Enum

from pydantic import BaseModel, Field

from src.utils.schema import (
    CompositionReport,
    DatasetRecord,
    Message,
)


class TurnType(str, Enum):
    """Type of turn in an agentic trajectory."""

    OBSERVATION = "observation"
    REASONING = "reasoning"
    ACTION = "action"
    ERROR = "error"
    CORRECT = "correct"
    VERIFY = "verify"


class TrajectoryMode(str, Enum):
    """Mode for trajectory generation."""

    HARD_QUERY = "hard_query"
    EXPLICIT = "explicit"
    NO_CALL = "no_call"


class SimulatedErrorType(str, Enum):
    """Type of simulated error for trajectory injection."""

    TOOL_FAILURE = "tool_failure"
    WRONG_RESULT = "wrong_result"
    CASCADE_FAILURE = "cascade_failure"


class Turn(BaseModel):
    """A single turn in an agentic trajectory."""

    model_config = {"frozen": True}

    turn_index: int = Field(description="Index of this turn in the trajectory")
    turn_type: TurnType = Field(description="Type of turn: observation/reasoning/action/error/correct/verify")
    content: str = Field(description="Turn content or tool output")
    tool_name: str | None = Field(default=None, description="Tool name if action turn")
    tool_args: dict | None = Field(default=None, description="Tool arguments if action turn")
    tool_result: str | None = Field(default=None, description="Tool execution result")
    reasoning: str | None = Field(default=None, description="Model reasoning if available")


class SimulatedError(BaseModel):
    """Simulated error injected into a trajectory."""

    model_config = {"frozen": True}

    error_type: SimulatedErrorType = Field(description="Type of simulated error")
    turn_index: int = Field(description="Turn index where error is injected")
    description: str = Field(description="Description of the error")
    recovery_turn_index: int | None = Field(
        default=None, description="Index of turn that corrects the error"
    )


class AgenticTrajectory(BaseModel):
    """An agentic multi-turn trajectory with backtracking and error injection."""

    model_config = {"frozen": True}

    seed_id: str = Field(description="Seed identifier")
    mode: TrajectoryMode = Field(
        description="Trajectory generation mode: hard_query/explicit/no_call"
    )
    turns: list[Turn] = Field(default_factory=list, description="List of turns")
    errors: list[SimulatedError] = Field(
        default_factory=list, description="Injected errors in trajectory"
    )
    use_case: str = Field(description="Use case domain (e.g., home_assistant)")
    messages: list[Message] = Field(
        default_factory=list, description="Serialized ChatML messages"
    )


# Re-export shared entities from utils schema
__all__ = [
    "AgenticTrajectory",
    "CompositionReport",
    "DatasetRecord",
    "Message",
    "SimulatedError",
    "SimulatedErrorType",
    "TrajectoryMode",
    "Turn",
    "TurnType",
]
