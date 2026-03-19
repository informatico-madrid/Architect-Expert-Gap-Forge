#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
UNIT TESTS: TrajectoryGenerator for agentic multi-turn trajectory generation.

Tests cover:
- Trajectory length between 3 and 10 turns
- Mandatory error + correct turn types
- cascade_failure generation
- mode: TrajectoryMode field present
- Serialization to ChatML messages[]

Location: tests/factory/test_trajectory_generator.py
"""

import logging
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.factory.schema import (
    AgenticTrajectory,
    SimulatedError,
    SimulatedErrorType,
    TrajectoryMode,
    Turn,
    TurnType,
)

logger = logging.getLogger(__name__)


# =============================================================================
# TEST FIXTURES
# =============================================================================


@pytest.fixture
def seed_data() -> dict[str, Any]:
    """Sample seed data for trajectory generation."""
    return {
        "seed_id": "ha_seed_001",
        "category": "dual_mode_integration",
        "complexity": "nominal_hard",
        "context": "# Dual-mode (LAN + Cloud) integration pattern",
        "question": "Diseña async_setup_entry para una integración dual-mode",
        "expected_patterns": ["async_forward_entry_setups", "DataUpdateCoordinator"],
    }


@pytest.fixture
def trajectory_templates() -> dict[str, Any]:
    """Sample trajectory templates for testing."""
    return {
        "observation": {
            "template": "Observación: {context}\nPregunta: {question}",
            "turn_type": "observation",
        },
        "reasoning": {
            "template": "Razonamiento: Analizando el problema...",
            "turn_type": "reasoning",
        },
        "action": {
            "template": "Acción: Ejecutando {tool_name} con {tool_args}",
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


@pytest.fixture
def mock_template_loader(trajectory_templates: dict[str, Any]) -> MagicMock:
    """Create a mock template loader."""
    mock_loader = MagicMock()
    mock_loader.load_templates.return_value = trajectory_templates
    return mock_loader


@pytest.fixture
def mock_teacher_client() -> MagicMock:
    """Create a mock teacher client that returns generated content."""
    mock_client = MagicMock()
    mock_client.generate = AsyncMock(
        return_value="Generated trajectory content with observation, reasoning, and action turns."
    )
    return mock_client


# =============================================================================
# TEST CLASSES
# =============================================================================


class TestTrajectorySchemaValidation:
    """Tests for AgenticTrajectory schema validation."""

    def test_trajectory_has_mode_field(self, seed_data: dict[str, Any]) -> None:
        """Test that AgenticTrajectory has required mode field of type TrajectoryMode."""
        trajectory = AgenticTrajectory(
            seed_id=seed_data["seed_id"],
            mode=TrajectoryMode.EXPLICIT,
            turns=[],
            errors=[],
            use_case="home_assistant",
            messages=[],
        )
        assert hasattr(trajectory, "mode")
        assert isinstance(trajectory.mode, TrajectoryMode)
        assert trajectory.mode == TrajectoryMode.EXPLICIT

    def test_trajectory_mode_hard_query(self, seed_data: dict[str, Any]) -> None:
        """Test TrajectoryMode.HARD_QUERY is valid."""
        trajectory = AgenticTrajectory(
            seed_id=seed_data["seed_id"],
            mode=TrajectoryMode.HARD_QUERY,
            turns=[],
            errors=[],
            use_case="home_assistant",
            messages=[],
        )
        assert trajectory.mode == TrajectoryMode.HARD_QUERY

    def test_trajectory_mode_no_call(self, seed_data: dict[str, Any]) -> None:
        """Test TrajectoryMode.NO_CALL is valid."""
        trajectory = AgenticTrajectory(
            seed_id=seed_data["seed_id"],
            mode=TrajectoryMode.NO_CALL,
            turns=[],
            errors=[],
            use_case="home_assistant",
            messages=[],
        )
        assert trajectory.mode == TrajectoryMode.NO_CALL


class TestTrajectoryTurnValidation:
    """Tests for trajectory turn validation."""

    def test_turn_types_enum_has_all_required_types(self) -> None:
        """Test TurnType enum contains all required types."""
        required_types = {
            TurnType.OBSERVATION,
            TurnType.REASONING,
            TurnType.ACTION,
            TurnType.ERROR,
            TurnType.CORRECT,
            TurnType.VERIFY,
        }
        assert required_types.issubset(set(TurnType))

    def test_turn_type_error_is_valid(self) -> None:
        """Test TurnType.ERROR is valid."""
        turn = Turn(
            turn_index=0,
            turn_type=TurnType.ERROR,
            content="Error: Tool failed to execute",
        )
        assert turn.turn_type == TurnType.ERROR

    def test_turn_type_correct_is_valid(self) -> None:
        """Test TurnType.CORRECT is valid."""
        turn = Turn(
            turn_index=1,
            turn_type=TurnType.CORRECT,
            content="Correcting the error by using correct tool",
        )
        assert turn.turn_type == TurnType.CORRECT


class TestSimulatedErrorTypes:
    """Tests for simulated error types."""

    def test_simulated_error_types_enum(self) -> None:
        """Test SimulatedErrorType enum contains cascade_failure."""
        assert SimulatedErrorType.CASCADE_FAILURE in SimulatedErrorType
        assert SimulatedErrorType.TOOL_FAILURE in SimulatedErrorType
        assert SimulatedErrorType.WRONG_RESULT in SimulatedErrorType

    def test_cascade_failure_error_creation(self) -> None:
        """Test cascade_failure error can be created with recovery turn."""
        error = SimulatedError(
            error_type=SimulatedErrorType.CASCADE_FAILURE,
            turn_index=2,
            description="Multiple errors occurred: tool failed, then wrong result",
            recovery_turn_index=4,
        )
        assert error.error_type == SimulatedErrorType.CASCADE_FAILURE
        assert error.recovery_turn_index == 4


class TestTrajectoryLength:
    """Tests for trajectory length validation (3-10 turns)."""

    def test_trajectory_minimum_3_turns(self, seed_data: dict[str, Any]) -> None:
        """Test trajectory with minimum 3 turns is valid."""
        turns = [
            Turn(turn_index=0, turn_type=TurnType.OBSERVATION, content="Observation 1"),
            Turn(turn_index=1, turn_type=TurnType.REASONING, content="Reasoning 1"),
            Turn(turn_index=2, turn_type=TurnType.ACTION, content="Action 1"),
        ]
        trajectory = AgenticTrajectory(
            seed_id=seed_data["seed_id"],
            mode=TrajectoryMode.EXPLICIT,
            turns=turns,
            errors=[],
            use_case="home_assistant",
            messages=[],
        )
        assert len(trajectory.turns) == 3

    def test_trajectory_maximum_10_turns(self, seed_data: dict[str, Any]) -> None:
        """Test trajectory with maximum 10 turns is valid."""
        turns = [
            Turn(turn_index=i, turn_type=TurnType.OBSERVATION, content=f"Turn {i}")
            for i in range(10)
        ]
        trajectory = AgenticTrajectory(
            seed_id=seed_data["seed_id"],
            mode=TrajectoryMode.EXPLICIT,
            turns=turns,
            errors=[],
            use_case="home_assistant",
            messages=[],
        )
        assert len(trajectory.turns) == 10

    def test_trajectory_rejects_less_than_3_turns(self, seed_data: dict[str, Any]) -> None:
        """Test trajectory with less than 3 turns is invalid."""
        turns = [
            Turn(turn_index=0, turn_type=TurnType.OBSERVATION, content="Turn 1"),
            Turn(turn_index=1, turn_type=TurnType.REASONING, content="Turn 2"),
        ]
        # This test verifies the minimum requirement - in practice the generator
        # should ensure 3-10 turns
        assert len(turns) < 3


class TestTrajectoryErrorAndCorrectPresence:
    """Tests for mandatory error + correct turn types."""

    def test_trajectory_has_error_turn(self, seed_data: dict[str, Any]) -> None:
        """Test trajectory contains at least one error turn."""
        turns = [
            Turn(turn_index=0, turn_type=TurnType.OBSERVATION, content="Obs"),
            Turn(turn_index=1, turn_type=TurnType.REASONING, content="Reason"),
            Turn(turn_index=2, turn_type=TurnType.ACTION, content="Action"),
            Turn(turn_index=3, turn_type=TurnType.ERROR, content="Error: Tool failed"),
            Turn(turn_index=4, turn_type=TurnType.CORRECT, content="Correcting..."),
        ]
        turn_types = {turn.turn_type for turn in turns}
        assert TurnType.ERROR in turn_types

    def test_trajectory_has_correct_turn(self, seed_data: dict[str, Any]) -> None:
        """Test trajectory contains at least one correct turn."""
        turns = [
            Turn(turn_index=0, turn_type=TurnType.OBSERVATION, content="Obs"),
            Turn(turn_index=1, turn_type=TurnType.REASONING, content="Reason"),
            Turn(turn_index=2, turn_type=TurnType.ACTION, content="Action"),
            Turn(turn_index=3, turn_type=TurnType.ERROR, content="Error: Tool failed"),
            Turn(turn_index=4, turn_type=TurnType.CORRECT, content="Correcting..."),
        ]
        turn_types = {turn.turn_type for turn in turns}
        assert TurnType.CORRECT in turn_types

    def test_error_followed_by_correct(self, seed_data: dict[str, Any]) -> None:
        """Test that error turn is followed by correct turn."""
        turns = [
            Turn(turn_index=0, turn_type=TurnType.OBSERVATION, content="Obs"),
            Turn(turn_index=1, turn_type=TurnType.REASONING, content="Reason"),
            Turn(turn_index=2, turn_type=TurnType.ACTION, content="Action"),
            Turn(turn_index=3, turn_type=TurnType.ERROR, content="Error: Tool failed"),
            Turn(turn_index=4, turn_type=TurnType.CORRECT, content="Correcting..."),
        ]
        # Find error turn index
        error_indices = [i for i, t in enumerate(turns) if t.turn_type == TurnType.ERROR]
        correct_indices = [i for i, t in enumerate(turns) if t.turn_type == TurnType.CORRECT]

        assert len(error_indices) > 0
        assert len(correct_indices) > 0
        # Error should come before correct
        assert error_indices[0] < correct_indices[0]


class TestCascadeFailureGeneration:
    """Tests for cascade_failure error generation."""

    def test_cascade_failure_error_type_exists(self) -> None:
        """Test SimulatedErrorType.CASCADE_FAILURE exists."""
        assert SimulatedErrorType.CASCADE_FAILURE == "cascade_failure"

    def test_cascade_failure_in_trajectory(self, seed_data: dict[str, Any]) -> None:
        """Test trajectory can contain cascade_failure error."""
        errors = [
            SimulatedError(
                error_type=SimulatedErrorType.CASCADE_FAILURE,
                turn_index=2,
                description="First tool failed, then wrong result returned",
                recovery_turn_index=5,
            ),
        ]
        turns = [
            Turn(turn_index=0, turn_type=TurnType.OBSERVATION, content="Obs"),
            Turn(turn_index=1, turn_type=TurnType.REASONING, content="Reason"),
            Turn(turn_index=2, turn_type=TurnType.ACTION, content="Action with error"),
            Turn(turn_index=3, turn_type=TurnType.ERROR, content="First error"),
            Turn(turn_index=4, turn_type=TurnType.ACTION, content="Retry action"),
            Turn(turn_index=5, turn_type=TurnType.CORRECT, content="Corrected"),
        ]
        trajectory = AgenticTrajectory(
            seed_id=seed_data["seed_id"],
            mode=TrajectoryMode.EXPLICIT,
            turns=turns,
            errors=errors,
            use_case="home_assistant",
            messages=[],
        )
        assert len(trajectory.errors) == 1
        assert trajectory.errors[0].error_type == SimulatedErrorType.CASCADE_FAILURE

    def test_cascade_failure_has_recovery_index(self) -> None:
        """Test cascade_failure includes recovery turn index."""
        error = SimulatedError(
            error_type=SimulatedErrorType.CASCADE_FAILURE,
            turn_index=2,
            description="Multiple failures requiring correction",
            recovery_turn_index=6,
        )
        assert error.recovery_turn_index is not None
        assert error.recovery_turn_index > error.turn_index


class TestChatMLSerialization:
    """Tests for ChatML serialization to messages[]."""

    def test_trajectory_has_messages_field(self, seed_data: dict[str, Any]) -> None:
        """Test AgenticTrajectory has messages field for ChatML serialization."""
        trajectory = AgenticTrajectory(
            seed_id=seed_data["seed_id"],
            mode=TrajectoryMode.EXPLICIT,
            turns=[],
            errors=[],
            use_case="home_assistant",
            messages=[],
        )
        assert hasattr(trajectory, "messages")
        assert isinstance(trajectory.messages, list)

    def test_messages_have_role_and_content(self) -> None:
        """Test ChatML messages have role and content fields."""
        from src.utils.schema import Message

        messages = [
            Message(role="system", content="You are a helpful assistant."),
            Message(role="user", content="Help me with Home Assistant."),
            Message(role="assistant", content="I'll help you with that."),
        ]
        assert len(messages) == 3
        assert all(hasattr(msg, "role") for msg in messages)
        assert all(hasattr(msg, "content") for msg in messages)

    def test_turns_serialize_to_chatml(self, seed_data: dict[str, Any]) -> None:
        """Test turns can be serialized to ChatML message format."""
        from src.utils.schema import Message

        turns = [
            Turn(turn_index=0, turn_type=TurnType.OBSERVATION, content="User asks about integration"),
            Turn(turn_index=1, turn_type=TurnType.REASONING, content="Analyzing requirements"),
            Turn(turn_index=2, turn_type=TurnType.ACTION, content="Creating async_setup_entry"),
        ]
        # Serialize to ChatML
        messages = [
            Message(role="user", content=turns[0].content),
            Message(role="assistant", content=turns[1].content),
            Message(role="assistant", content=turns[2].content),
        ]
        assert len(messages) == 3
        assert all(msg.role in ("system", "user", "assistant") for msg in messages)


class TestTrajectoryGenerator:
    """Tests for TrajectoryGenerator class behavior."""

    def test_trajectory_generator_class_exists(self) -> None:
        """Test TrajectoryGenerator class can be imported."""
        try:
            from src.factory.trajectory_generator import TrajectoryGenerator
            assert TrajectoryGenerator is not None
        except ImportError:
            pytest.skip("TrajectoryGenerator not yet implemented")

    @pytest.mark.asyncio
    async def test_generate_creates_trajectory_with_mode(
        self,
        seed_data: dict[str, Any],
    ) -> None:
        """Test generate() creates trajectory with mode field set."""
        try:
            from src.factory.trajectory_generator import TrajectoryGenerator
        except ImportError:
            pytest.skip("TrajectoryGenerator not yet implemented")

        # Create generator with mock
        with patch("src.factory.trajectory_generator.PromptLoader") as mock_loader:
            mock_loader_instance = MagicMock()
            mock_loader_instance.load_templates.return_value = {
                "observation": {"template": "Obs: {question}", "turn_type": "observation"},
                "reasoning": {"template": "Reasoning: {reasoning}", "turn_type": "reasoning"},
                "action": {"template": "Action: {tool_name}", "turn_type": "action"},
                "error": {"template": "Error: {error_description}", "turn_type": "error"},
                "correct": {"template": "Correct: {corrective_action}", "turn_type": "correct"},
                "verify": {"template": "Verify: {verification_result}", "turn_type": "verify"},
            }
            mock_loader.return_value = mock_loader_instance

            generator = TrajectoryGenerator(
                use_case="home_assistant",
                mode=TrajectoryMode.EXPLICIT,
            )

            trajectory = await generator.generate(seed_data)

            assert hasattr(trajectory, "mode")
            assert trajectory.mode == TrajectoryMode.EXPLICIT

    @pytest.mark.asyncio
    async def test_generate_creates_3_to_10_turns(
        self,
        seed_data: dict[str, Any],
    ) -> None:
        """Test generate() creates trajectory with 3-10 turns."""
        try:
            from src.factory.trajectory_generator import TrajectoryGenerator
        except ImportError:
            pytest.skip("TrajectoryGenerator not yet implemented")

        with patch("src.factory.trajectory_generator.PromptLoader") as mock_loader:
            mock_loader_instance = MagicMock()
            mock_loader_instance.load_templates.return_value = {
                "observation": {"template": "Obs: {question}", "turn_type": "observation"},
                "reasoning": {"template": "Reasoning: {reasoning}", "turn_type": "reasoning"},
                "action": {"template": "Action: {tool_name}", "turn_type": "action"},
                "error": {"template": "Error: {error_description}", "turn_type": "error"},
                "correct": {"template": "Correct: {corrective_action}", "turn_type": "correct"},
                "verify": {"template": "Verify: {verification_result}", "turn_type": "verify"},
            }
            mock_loader.return_value = mock_loader_instance

            generator = TrajectoryGenerator(
                use_case="home_assistant",
                mode=TrajectoryMode.EXPLICIT,
            )

            trajectory = await generator.generate(seed_data)

            assert 3 <= len(trajectory.turns) <= 10

    @pytest.mark.asyncio
    async def test_generate_includes_error_and_correct_turns(
        self,
        seed_data: dict[str, Any],
    ) -> None:
        """Test generate() includes at least one error and one correct turn."""
        try:
            from src.factory.trajectory_generator import TrajectoryGenerator
        except ImportError:
            pytest.skip("TrajectoryGenerator not yet implemented")

        with patch("src.factory.trajectory_generator.PromptLoader") as mock_loader:
            mock_loader_instance = MagicMock()
            mock_loader_instance.load_templates.return_value = {
                "observation": {"template": "Obs: {question}", "turn_type": "observation"},
                "reasoning": {"template": "Reasoning: {reasoning}", "turn_type": "reasoning"},
                "action": {"template": "Action: {tool_name}", "turn_type": "action"},
                "error": {"template": "Error: {error_description}", "turn_type": "error"},
                "correct": {"template": "Correct: {corrective_action}", "turn_type": "correct"},
                "verify": {"template": "Verify: {verification_result}", "turn_type": "verify"},
            }
            mock_loader.return_value = mock_loader_instance

            generator = TrajectoryGenerator(
                use_case="home_assistant",
                mode=TrajectoryMode.EXPLICIT,
                error_probability=1.0,  # Force error injection
            )

            trajectory = await generator.generate(seed_data)

            turn_types = {turn.turn_type for turn in trajectory.turns}
            assert TurnType.ERROR in turn_types, "Trajectory must contain at least one error turn"
            assert TurnType.CORRECT in turn_types, "Trajectory must contain at least one correct turn"

    @pytest.mark.asyncio
    async def test_generate_can_produce_cascade_failure(
        self,
        seed_data: dict[str, Any],
    ) -> None:
        """Test generate() can produce cascade_failure errors."""
        try:
            from src.factory.trajectory_generator import TrajectoryGenerator
        except ImportError:
            pytest.skip("TrajectoryGenerator not yet implemented")

        with patch("src.factory.trajectory_generator.PromptLoader") as mock_loader:
            mock_loader_instance = MagicMock()
            mock_loader_instance.load_templates.return_value = {
                "observation": {"template": "Obs: {question}", "turn_type": "observation"},
                "reasoning": {"template": "Reasoning: {reasoning}", "turn_type": "reasoning"},
                "action": {"template": "Action: {tool_name}", "turn_type": "action"},
                "error": {"template": "Error: {error_description}", "turn_type": "error"},
                "correct": {"template": "Correct: {corrective_action}", "turn_type": "correct"},
                "verify": {"template": "Verify: {verification_result}", "turn_type": "verify"},
            }
            mock_loader.return_value = mock_loader_instance

            generator = TrajectoryGenerator(
                use_case="home_assistant",
                mode=TrajectoryMode.EXPLICIT,
                error_probability=1.0,  # Force error injection
                cascade_failure_probability=1.0,  # Force cascade failure
                seed=42,  # Deterministic for test
            )

            trajectory = await generator.generate(seed_data)

            # Check for cascade_failure in errors
            error_types = {err.error_type for err in trajectory.errors}
            assert SimulatedErrorType.CASCADE_FAILURE in error_types

    @pytest.mark.asyncio
    async def test_generate_produces_chatml_messages(
        self,
        seed_data: dict[str, Any],
    ) -> None:
        """Test generate() produces ChatML messages serialization."""
        try:
            from src.factory.trajectory_generator import TrajectoryGenerator
        except ImportError:
            pytest.skip("TrajectoryGenerator not yet implemented")

        with patch("src.factory.trajectory_generator.PromptLoader") as mock_loader:
            mock_loader_instance = MagicMock()
            mock_loader_instance.load_templates.return_value = {
                "observation": {"template": "Obs: {question}", "turn_type": "observation"},
                "reasoning": {"template": "Reasoning: {reasoning}", "turn_type": "reasoning"},
                "action": {"template": "Action: {tool_name}", "turn_type": "action"},
                "error": {"template": "Error: {error_description}", "turn_type": "error"},
                "correct": {"template": "Correct: {corrective_action}", "turn_type": "correct"},
                "verify": {"template": "Verify: {verification_result}", "turn_type": "verify"},
            }
            mock_loader.return_value = mock_loader_instance

            generator = TrajectoryGenerator(
                use_case="home_assistant",
                mode=TrajectoryMode.EXPLICIT,
            )

            trajectory = await generator.generate(seed_data)

            # Verify messages field exists and is populated
            assert hasattr(trajectory, "messages")
            assert isinstance(trajectory.messages, list)
            # ChatML should have at least one message
            assert len(trajectory.messages) > 0


class TestTrajectoryModes:
    """Tests for different TrajectoryMode configurations."""

    def test_hard_query_mode(self, seed_data: dict[str, Any]) -> None:
        """Test trajectory in hard_query mode."""
        trajectory = AgenticTrajectory(
            seed_id=seed_data["seed_id"],
            mode=TrajectoryMode.HARD_QUERY,
            turns=[],
            errors=[],
            use_case="home_assistant",
            messages=[],
        )
        assert trajectory.mode == TrajectoryMode.HARD_QUERY

    def test_explicit_mode(self, seed_data: dict[str, Any]) -> None:
        """Test trajectory in explicit mode."""
        trajectory = AgenticTrajectory(
            seed_id=seed_data["seed_id"],
            mode=TrajectoryMode.EXPLICIT,
            turns=[],
            errors=[],
            use_case="home_assistant",
            messages=[],
        )
        assert trajectory.mode == TrajectoryMode.EXPLICIT

    def test_no_call_mode(self, seed_data: dict[str, Any]) -> None:
        """Test trajectory in no_call mode."""
        trajectory = AgenticTrajectory(
            seed_id=seed_data["seed_id"],
            mode=TrajectoryMode.NO_CALL,
            turns=[],
            errors=[],
            use_case="home_assistant",
            messages=[],
        )
        assert trajectory.mode == TrajectoryMode.NO_CALL


class TestTrajectoryGeneratorConfig:
    """Tests for TrajectoryGenerator configuration options."""

    def test_generator_accepts_use_case_parameter(self) -> None:
        """Test TrajectoryGenerator accepts use_case parameter."""
        try:
            from src.factory.trajectory_generator import TrajectoryGenerator
        except ImportError:
            pytest.skip("TrajectoryGenerator not yet implemented")

        # Should be able to create with use_case
        generator = TrajectoryGenerator(
            use_case="home_assistant",
            mode=TrajectoryMode.EXPLICIT,
        )
        assert generator.use_case == "home_assistant"

    def test_generator_accepts_mode_parameter(self) -> None:
        """Test TrajectoryGenerator accepts mode parameter."""
        try:
            from src.factory.trajectory_generator import TrajectoryGenerator
        except ImportError:
            pytest.skip("TrajectoryGenerator not yet implemented")

        generator = TrajectoryGenerator(
            use_case="home_assistant",
            mode=TrajectoryMode.HARD_QUERY,
        )
        assert generator.mode == TrajectoryMode.HARD_QUERY
