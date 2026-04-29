#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Architect-Expert-Gap-Forge (AEGF) - Trajectory Generator

Generates agentic multi-turn trajectories with error injection and backtracking.
Loads templates from configs/stage_2_factory/prompts/trajectory_templates.yaml.

SPDX-License-Identifier: Apache-2.0
Copyright 2026 AEGF
"""

from __future__ import annotations

import json
import logging
import random
from pathlib import Path
from typing import Any

import yaml

from src.factory.dspy_utils import get_predict
from src.factory.hard_query_builder import HardQueryBuilder
from src.factory.schema import (
    AgenticTrajectory,
    serialize_tool_call_xml,
    should_use_xml_format,
    SimulatedError,
    SimulatedErrorType,
    TrajectoryMode,
    Turn,
    TurnType,
)
from src.factory.trajectory_signature import TrajectorySignature
from src.utils.schema import Message

logger = logging.getLogger(__name__)

# Default template path
_DEFAULT_TEMPLATES_PATH: Path = Path(
    "configs/stage_2_factory/prompts/trajectory_templates.yaml"
)


class PromptLoader:
    """Loads trajectory templates from YAML."""

    def __init__(self, templates_path: Path | str | None = None) -> None:
        """Initialize and load templates."""
        path = Path(templates_path) if templates_path else _DEFAULT_TEMPLATES_PATH

        if not path.exists():
            # Create default templates if file doesn't exist
            logger.warning("Template file not found: %s, using defaults", path)
            self._templates = self._default_templates()
        else:
            with open(path, encoding="utf-8") as fh:
                self._templates = yaml.safe_load(fh) or {}

    def load_templates(self) -> dict[str, Any]:
        """Return loaded templates."""
        return self._templates

    def _default_templates(self) -> dict[str, Any]:
        """Return default templates when file is missing."""
        return {
            "observation": {
                "template": "Observación: {context}\nPregunta: {question}",
                "turn_type": "observation",
            },
            "reasoning": {
                "template": "Razonamiento: {reasoning}",
                "turn_type": "reasoning",
            },
            "action": {
                "template": "Acción: Ejecutando {tool_name}",
                "turn_type": "action",
            },
            "error": {
                "template": "Error: {error_description}",
                "turn_type": "error",
            },
            "correct": {
                "template": "Corrección: {corrective_action}",
                "turn_type": "correct",
            },
            "verify": {
                "template": "Verificación: {verification_result}",
                "turn_type": "verify",
            },
        }


class TrajectoryGenerator:
    """Generates agentic multi-turn trajectories with error injection.

    Produces trajectories with 3-10 turns following the pattern:
    Observation → Reasoning → Action → [Error → Correct → Verify]?

    Attributes:
        use_case: The use case domain (e.g., home_assistant)
        mode: The trajectory generation mode (hard_query/explicit/no_call)
        error_probability: Probability of injecting an error (0.0-1.0)
        cascade_failure_probability: Probability of cascade_failure vs simple error
    """

    def __init__(
        self,
        use_case: str,
        mode: TrajectoryMode = TrajectoryMode.EXPLICIT,
        error_probability: float = 0.7,
        cascade_failure_probability: float = 0.3,
        templates_path: Path | str | None = None,
        hard_query_templates_path: Path | str | None = None,
        seed: int | None = None,
        tool_format: str = "auto",
    ) -> None:
        """Initialize the trajectory generator.

        Args:
            use_case: The use case domain
            mode: Trajectory generation mode
            error_probability: Probability of error injection (default 0.7)
            cascade_failure_probability: Probability of cascade_failure (default 0.3)
            templates_path: Optional path to trajectory templates YAML
            hard_query_templates_path: Optional path to hard query templates YAML
            seed: Optional random seed for reproducibility
            tool_format: Tool call format for action turns (json|xml|auto).
                auto: uses XML for large args (>500 bytes in JSON) via schema.should_use_xml_format
        """
        self.use_case = use_case
        self.mode = mode
        self.error_probability = error_probability
        self.cascade_failure_probability = cascade_failure_probability
        self.tool_format = tool_format
        self._loader = PromptLoader(templates_path)
        self._templates = self._loader.load_templates()

        # Initialize HardQueryBuilder for hard_query mode
        self._hard_query_builder: HardQueryBuilder | None = None
        if mode == TrajectoryMode.HARD_QUERY:
            self._hard_query_builder = HardQueryBuilder(
                use_case=use_case,
                templates_path=hard_query_templates_path,
                seed=seed,
            )

        if seed is not None:
            random.seed(seed)

    def _get_tool_format_for_trajectory(self, sample_args: dict) -> str:
        """Determine the tool format to use for this trajectory.

        Args:
            sample_args: Sample tool arguments to determine format in auto mode.

        Returns:
            "xml" or "json" - the format to use for all action turns.
        """
        if self.tool_format == "auto":
            return "xml" if should_use_xml_format(sample_args) else "json"
        return self.tool_format

    def _serialize_tool_call(
        self, tool_name: str, tool_args: dict, use_xml: bool
    ) -> str:
        """Serialize a tool call to the appropriate format.

        Args:
            tool_name: Name of the tool
            tool_args: Tool arguments dictionary
            use_xml: Whether to use XML format

        Returns:
            Serialized tool call string
        """
        if use_xml:
            return serialize_tool_call_xml(tool_name, tool_args)
        # JSON format: tool_name(args)
        args_str = json.dumps(tool_args)
        return f"{tool_name}({args_str})"

    async def generate(self, seed_data: dict[str, Any]) -> AgenticTrajectory:
        """Generate a trajectory for the given seed.

        Args:
            seed_data: Seed data containing seed_id, question, context, etc.

        Returns:
            AgenticTrajectory with turns, errors, and ChatML messages
        """
        seed_id = seed_data.get("seed_id", "unknown")
        question = seed_data.get("question", "")
        context = seed_data.get("context", "")

        # DSPy dual-path: use predictor when LM configured, fall back to templates
        predictor = get_predict(TrajectorySignature)
        if predictor is not None:
            seed_data_payload = {
                "seed_id": seed_data.get("seed_id", "unknown"),
                "mode": seed_data.get("mode", "explicit"),
                "use_case": seed_data.get("use_case", ""),
                "question": question,
                "context": context,
                "error_probability": self.error_probability,
                "has_error": getattr(self, "has_error", False),
                "is_cascade": bool(self.cascade_failure_probability > 0.5),
                "tool_format": self.tool_format,
            }
            result = predictor(**seed_data_payload)
            turns_parsed = json.loads(result.turns_json)
            errors_parsed = json.loads(result.errors_json)
            messages_parsed = json.loads(result.messages_json)

            agentic_turns = [Turn(**t) for t in turns_parsed]
            agentic_errors = [SimulatedError(**e) for e in errors_parsed]
            agentic_messages = [Message(**m) for m in messages_parsed]

            return AgenticTrajectory(
                seed_id=seed_data_payload["seed_id"],
                mode=TrajectoryMode(seed_data_payload["mode"])
                if isinstance(seed_data_payload["mode"], str)
                else seed_data_payload["mode"],
                turns=agentic_turns,
                errors=agentic_errors,
                use_case=result.inferred_use_case,
                messages=agentic_messages,
            )

        # Sample tool args to determine format for this trajectory (in auto mode)
        sample_tool_args = seed_data.get("tool_args", {"sample": "data"})
        use_xml = self._get_tool_format_for_trajectory(sample_tool_args) == "xml"

        turns: list[Turn] = []
        errors: list[SimulatedError] = []

        # Generate base trajectory (observation/reasoning/action or hard_query based)
        turn_index = 0

        # First turn: use HardQueryBuilder if mode is hard_query, otherwise use observation template
        if (
            self.mode == TrajectoryMode.HARD_QUERY
            and self._hard_query_builder is not None
        ):
            # Generate hard query prompt (abstract objective without tool names)
            first_content = self._hard_query_builder.build(seed_data)
            turns.append(
                Turn(
                    turn_index=turn_index,
                    turn_type=TurnType.OBSERVATION,
                    content=first_content,
                )
            )
        else:
            # Standard observation turn with explicit template
            obs_template = self._templates.get("observation", {}).get(
                "template", "Obs: {question}"
            )
            obs_content = obs_template.format(question=question, context=context)
            turns.append(
                Turn(
                    turn_index=turn_index,
                    turn_type=TurnType.OBSERVATION,
                    content=obs_content,
                )
            )
        turn_index += 1

        # Reasoning turn
        reason_template = self._templates.get("reasoning", {}).get(
            "template", "Reasoning..."
        )
        reason_content = reason_template.format(
            reasoning="Analizando los requisitos para resolver el problema..."
        )
        turns.append(
            Turn(
                turn_index=turn_index,
                turn_type=TurnType.REASONING,
                content=reason_content,
            )
        )
        turn_index += 1

        # Action turn
        tool_name = "async_setup_entry"
        tool_args = {"entry": "config_entry"}
        action_content = self._serialize_tool_call(tool_name, tool_args, use_xml)
        turns.append(
            Turn(
                turn_index=turn_index,
                turn_type=TurnType.ACTION,
                content=action_content,
                tool_name=tool_name,
                tool_args=tool_args,
            )
        )
        turn_index += 1

        # Determine if we should inject error
        inject_error = random.random() < self.error_probability

        if inject_error:
            # Determine error type
            is_cascade = random.random() < self.cascade_failure_probability

            if is_cascade:
                # Add another action turn (that will fail) - use same format as first action
                tool2_name = "get_coordinator_data"
                tool2_args = {"entity_id": "light.living_room"}
                action2_content = self._serialize_tool_call(
                    tool2_name, tool2_args, use_xml
                )
                turns.append(
                    Turn(
                        turn_index=turn_index,
                        turn_type=TurnType.ACTION,
                        content=action2_content,
                        tool_name=tool2_name,
                        tool_args=tool2_args,
                    )
                )
                turn_index += 1

                # Error turn - cascade failure
                error_template = self._templates.get("error", {}).get(
                    "template", "Error: {error_description}\\nDetalles: {error_details}"
                )
                error_content = error_template.format(
                    error_description="Tool failed, then returned wrong data - cascade failure",
                    error_details="El primer error fue de conexión, el segundo retornó datos vacíos",
                )
                turns.append(
                    Turn(
                        turn_index=turn_index,
                        turn_type=TurnType.ERROR,
                        content=error_content,
                    )
                )

                # Record the error
                error = SimulatedError(
                    error_type=SimulatedErrorType.CASCADE_FAILURE,
                    turn_index=turn_index,
                    description="Multiple errors: tool failure followed by wrong result",
                    recovery_turn_index=turn_index + 2,
                )
                errors.append(error)
                turn_index += 1
            else:
                # Simple error (tool_failure)
                error_template = self._templates.get("error", {}).get(
                    "template", "Error: {error_description}\\nDetalles: {error_details}"
                )
                error_content = error_template.format(
                    error_description="Tool failed to execute: ConfigEntryNotReady",
                    error_details="La configuración no está lista para cargar",
                )
                turns.append(
                    Turn(
                        turn_index=turn_index,
                        turn_type=TurnType.ERROR,
                        content=error_content,
                    )
                )

                # Record the error
                error = SimulatedError(
                    error_type=SimulatedErrorType.TOOL_FAILURE,
                    turn_index=turn_index,
                    description="Tool failed to execute",
                    recovery_turn_index=turn_index + 2,
                )
                errors.append(error)
                turn_index += 1

            # Correct turn (mandatory after error)
            correct_template = self._templates.get("correct", {}).get(
                "template",
                "Corrección: {corrective_action}\\nRazón: {correction_reason}",
            )
            correct_content = correct_template.format(
                corrective_action="Corregido el error usando el patrón correcto de HA 2026",
                correction_reason="El patrón async_setup_entry requiere await en el entry",
            )
            turns.append(
                Turn(
                    turn_index=turn_index,
                    turn_type=TurnType.CORRECT,
                    content=correct_content,
                )
            )
            turn_index += 1

        # Verify turn (optional, adds depth)
        if len(turns) < 10 and random.random() < 0.5:
            verify_template = self._templates.get("verify", {}).get(
                "template",
                "Verificación: {verification_result}\\nEstado: {final_state}",
            )
            verify_content = verify_template.format(
                verification_result="Verificación completada exitosamente",
                final_state="Todos los checks pasaron correctamente",
            )
            turns.append(
                Turn(
                    turn_index=turn_index,
                    turn_type=TurnType.VERIFY,
                    content=verify_content,
                )
            )

        # Ensure we have between 3 and 10 turns
        while len(turns) < 3:
            turns.append(
                Turn(
                    turn_index=len(turns),
                    turn_type=TurnType.VERIFY,
                    content="Additional verification turn",
                )
            )

        # Serialize to ChatML messages
        messages = self._serialize_to_chatml(turns)

        return AgenticTrajectory(
            seed_id=seed_id,
            mode=self.mode,
            turns=turns,
            errors=errors,
            use_case=self.use_case,
            messages=messages,
        )

    def _serialize_to_chatml(self, turns: list[Turn]) -> list[Message]:
        """Serialize turns to ChatML message format.

        Args:
            turns: List of turns to serialize

        Returns:
            List of Message objects in ChatML format
        """
        messages: list[Message] = []

        for turn in turns:
            if turn.turn_type == TurnType.OBSERVATION:
                role = "user"
            elif turn.turn_type in (TurnType.ERROR, TurnType.ACTION):
                role = "assistant"  # Model taking action or reporting error
            elif turn.turn_type == TurnType.CORRECT:
                role = "assistant"
            else:
                role = "assistant"

            messages.append(Message(role=role, content=turn.content))

        return messages


__all__ = ["TrajectoryGenerator", "PromptLoader"]
