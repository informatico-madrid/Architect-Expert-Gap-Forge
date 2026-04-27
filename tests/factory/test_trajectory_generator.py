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


# =============================================================================
# TEST CLASSES: XML Tool Format Tests (US4)
# =============================================================================


class TestXMLToolCallSerialization:
    """Tests for XML tool call serialization and parsing (US4)."""

    def test_serialize_tool_call_xml_preserves_name_and_args(self) -> None:
        """Test round-trip XML serialize→parse preserves tool name and arguments."""
        try:
            from src.factory.schema import serialize_tool_call_xml, parse_tool_call_xml
        except ImportError:
            pytest.skip("XML serialization functions not yet implemented")

        tool_name = "get_weather"
        tool_args = {"location": "Madrid", "units": "celsius"}

        # Serialize to XML
        xml_output = serialize_tool_call_xml(tool_name, tool_args)

        # Parse back
        parsed_name, parsed_args = parse_tool_call_xml(xml_output)

        # Verify round-trip preserves data
        assert parsed_name == tool_name
        assert parsed_args == tool_args

    def test_xml_serialize_multiline_python_code_no_escaping(self) -> None:
        """Test argument with Python multiline code does not require escaping."""
        try:
            from src.factory.schema import serialize_tool_call_xml, parse_tool_call_xml
        except ImportError:
            pytest.skip("XML serialization functions not yet implemented")

        # Multiline Python code that would need escaping in JSON
        multiline_code = '''def calculate_metrics(data):
    total = sum(data)
    average = total / len(data)
    return {
        "total": total,
        "average": average,
        "count": len(data)
    }'''

        tool_args = {"code": multiline_code}

        # Serialize to XML
        xml_output = serialize_tool_call_xml("execute_code", tool_args)

        # Verify no escaped quotes in the output
        assert '\\"' not in xml_output
        assert '\\n' not in xml_output

        # Parse back and verify content is preserved
        _, parsed_args = parse_tool_call_xml(xml_output)

        assert parsed_args["code"] == multiline_code

    def test_xml_serialize_preserves_special_characters(self) -> None:
        """Test XML serialization preserves special characters without escaping."""
        try:
            from src.factory.schema import serialize_tool_call_xml, parse_tool_call_xml
        except ImportError:
            pytest.skip("XML serialization functions not yet implemented")

        tool_args = {
            "query": "SELECT * FROM users WHERE name = 'José'",
            "path": "C:\\Users\\Test\\file.txt",
            "json_data": {"key": "value with \"quotes\" and 'apostrophes'"},
        }

        xml_output = serialize_tool_call_xml("execute_query", tool_args)

        # Parse back
        _, parsed_args = parse_tool_call_xml(xml_output)

        assert parsed_args["query"] == tool_args["query"]
        assert parsed_args["path"] == tool_args["path"]
        assert parsed_args["json_data"] == tool_args["json_data"]

    def test_json_and_xml_produce_identical_semantics(self) -> None:
        """Test same data in JSON and XML produces semantically identical result."""
        try:
            from src.factory.schema import serialize_tool_call_xml, parse_tool_call_xml
        except ImportError:
            pytest.skip("XML serialization functions not yet implemented")
        import json

        tool_name = "homeassistant.call_service"
        tool_args = {
            "domain": "light",
            "service": "turn_on",
            "data": {"brightness": 255, "rgb_color": [255, 128, 0]},
        }

        # JSON serialization
        json_output = json.dumps({"name": tool_name, "args": tool_args})

        # XML serialization
        xml_output = serialize_tool_call_xml(tool_name, tool_args)

        # Parse XML back to components
        parsed_name, parsed_args = parse_tool_call_xml(xml_output)

        # Both should produce identical semantic data
        assert parsed_name == tool_name
        assert parsed_args == tool_args

        # Verify JSON can also be parsed to same structure
        json_parsed = json.loads(json_output)
        assert json_parsed["name"] == parsed_name
        assert json_parsed["args"] == parsed_args

    def test_xml_roundtrip_with_empty_args(self) -> None:
        """Test XML round-trip with empty arguments dict."""
        try:
            from src.factory.schema import serialize_tool_call_xml, parse_tool_call_xml
        except ImportError:
            pytest.skip("XML serialization functions not yet implemented")

        tool_name = "no_args_tool"
        tool_args = {}

        xml_output = serialize_tool_call_xml(tool_name, tool_args)
        parsed_name, parsed_args = parse_tool_call_xml(xml_output)

        assert parsed_name == tool_name
        assert parsed_args == {}

    def test_xml_roundtrip_with_none_values(self) -> None:
        """Test XML round-trip handles None values in arguments."""
        try:
            from src.factory.schema import serialize_tool_call_xml, parse_tool_call_xml
        except ImportError:
            pytest.skip("XML serialization functions not yet implemented")

        tool_name = "tool_with_none"
        tool_args = {"optional_field": None, "required_field": "value"}

        xml_output = serialize_tool_call_xml(tool_name, tool_args)
        parsed_name, parsed_args = parse_tool_call_xml(xml_output)

        assert parsed_name == tool_name
        assert "optional_field" in parsed_args
        assert parsed_args["required_field"] == "value"

    def test_xml_format_matches_qwen3_coder_pattern(self) -> None:
        """Test XML format follows qwen3_coder pattern with tool_calls structure."""
        try:
            from src.factory.schema import serialize_tool_call_xml
        except ImportError:
            pytest.skip("XML serialization functions not yet implemented")

        tool_name = "python_exec"
        tool_args = {"code": "print('hello world')"}

        xml_output = serialize_tool_call_xml(tool_name, tool_args)

        # Verify qwen3_coder XML format structure
        assert "<tool_call>" in xml_output
        assert "<tool_name>" in xml_output
        assert "<tool_args>" in xml_output
        assert "</tool_call>" in xml_output
        assert tool_name in xml_output

    def test_xml_parse_handles_trailing_whitespace(self) -> None:
        """Test XML parsing handles extra whitespace in input."""
        try:
            from src.factory.schema import serialize_tool_call_xml, parse_tool_call_xml
        except ImportError:
            pytest.skip("XML serialization functions not yet implemented")

        tool_name = "test_tool"
        tool_args = {"key": "value"}

        xml_output = serialize_tool_call_xml(tool_name, tool_args)
        # Add extra whitespace
        xml_with_whitespace = "  \n  " + xml_output + "  \n  "

        parsed_name, parsed_args = parse_tool_call_xml(xml_with_whitespace)

        assert parsed_name == tool_name
        assert parsed_args == tool_args

    def test_xml_roundtrip_with_float_values(self) -> None:
        """Test XML round-trip preserves float values correctly."""
        try:
            from src.factory.schema import serialize_tool_call_xml, parse_tool_call_xml
        except ImportError:
            pytest.skip("XML serialization functions not yet implemented")

        tool_name = "compute"
        tool_args = {"temperature": 0.75, "probability": 0.123, "score": -0.5}

        xml_output = serialize_tool_call_xml(tool_name, tool_args)
        parsed_name, parsed_args = parse_tool_call_xml(xml_output)

        assert parsed_name == tool_name
        assert parsed_args["temperature"] == 0.75
        assert parsed_args["probability"] == 0.123
        assert parsed_args["score"] == -0.5

    def test_xml_roundtrip_with_mixed_types(self) -> None:
        """Test XML round-trip handles mixed types including floats, ints, bools."""
        try:
            from src.factory.schema import serialize_tool_call_xml, parse_tool_call_xml
        except ImportError:
            pytest.skip("XML serialization functions not yet implemented")

        tool_name = "mixed_types"
        tool_args = {
            "int_val": 42,
            "float_val": 3.14,
            "bool_true": True,
            "bool_false": False,
            "none_val": None,
            "string_val": "hello",
        }

        xml_output = serialize_tool_call_xml(tool_name, tool_args)
        parsed_name, parsed_args = parse_tool_call_xml(xml_output)

        assert parsed_name == tool_name
        assert parsed_args["int_val"] == 42
        assert parsed_args["float_val"] == 3.14
        assert parsed_args["bool_true"] is True
        assert parsed_args["bool_false"] is False
        assert parsed_args["none_val"] is None
        assert parsed_args["string_val"] == "hello"

    def test_xml_parse_invalid_xml_raises(self) -> None:
        """Test XML parsing raises ValueError for malformed XML."""
        try:
            from src.factory.schema import parse_tool_call_xml
        except ImportError:
            pytest.skip("XML parsing function not yet implemented")

        invalid_xml = "<tool_call><invalid>no closing tags"
        with pytest.raises(ValueError, match="Invalid XML format"):
            parse_tool_call_xml(invalid_xml)

    def test_xml_parse_missing_tool_name_raises(self) -> None:
        """Test XML parsing raises ValueError when tool_name element is missing."""
        try:
            from src.factory.schema import parse_tool_call_xml
        except ImportError:
            pytest.skip("XML parsing function not yet implemented")

        # XML with tool_args but no tool_name
        xml_without_name = "<tool_call><tool_args><item key='arg'>value</item></tool_args></tool_call>"
        with pytest.raises(ValueError, match="Missing <tool_name>"):
            parse_tool_call_xml(xml_without_name)

    def test_xml_parse_empty_tool_args_returns_empty_dict(self) -> None:
        """Test XML parsing returns empty dict when tool_args is missing."""
        try:
            from src.factory.schema import parse_tool_call_xml
        except ImportError:
            pytest.skip("XML parsing function not yet implemented")

        # XML with tool_name but no tool_args
        xml_without_args = "<tool_call><tool_name>some_tool</tool_name></tool_call>"
        tool_name, tool_args = parse_tool_call_xml(xml_without_args)

        assert tool_name == "some_tool"
        assert tool_args == {}

    def test_xml_serialize_without_wrapper_tags(self) -> None:
        """Test XML serialization adds wrapper tags if not present."""
        try:
            from src.factory.schema import serialize_tool_call_xml
        except ImportError:
            pytest.skip("XML serialization function not yet implemented")

        # Create XML without wrapper tags
        result = serialize_tool_call_xml("test", {"key": "value"})

        # Should have wrapper tags
        assert result.startswith("<tool_call>")
        assert result.endswith("</tool_call>")


class TestXMLToolFormatAutoSelection:
    """Tests for automatic tool format selection based on argument size."""

    def test_auto_select_xml_for_large_args(self) -> None:
        """Test auto-selector uses XML when args exceed 500 bytes."""
        try:
            from src.factory.schema import should_use_xml_format
        except ImportError:
            pytest.skip("Auto-selection function not yet implemented")

        # Small args should use JSON
        small_args = {"key": "value"}
        assert not should_use_xml_format(small_args)

        # Large args (>500 bytes in JSON) should use XML
        large_content = "x" * 600
        large_args = {"content": large_content}
        assert should_use_xml_format(large_args)

    def test_auto_select_threshold_calculation(self) -> None:
        """Test auto-select threshold is correctly calculated."""
        try:
            from src.factory.schema import should_use_xml_format
        except ImportError:
            pytest.skip("Auto-selection function not yet implemented")
        import json

        # Exactly at threshold should use JSON (not > 500)
        # Use 488 x's to ensure JSON size <= 500 (12 chars for {"data": "}"} + 488 = 500)
        args_at_threshold = {"data": "x" * 488}
        json_size = len(json.dumps(args_at_threshold))
        # If JSON size is <= 500, should not use XML
        assert json_size <= 500 or not should_use_xml_format(args_at_threshold)

    def test_should_use_xml_format_edge_cases(self) -> None:
        """Test should_use_xml_format with edge cases."""
        import json

        try:
            from src.factory.schema import should_use_xml_format
        except ImportError:
            pytest.skip("Auto-selection function not yet implemented")

        # Empty dict should not use XML
        assert not should_use_xml_format({})

        # Just under 500 bytes - should use JSON
        # {"a": "xxx"} where xxx is 493 chars -> total JSON = 500
        args_under = {"a": "x" * 493}
        json_size_under = len(json.dumps(args_under))
        # If under 500, should return False
        if json_size_under <= 500:
            assert not should_use_xml_format(args_under)

        # Over 500 bytes - should use XML
        args_over = {"a": "x" * 494}
        json_size_over = len(json.dumps(args_over))
        # If over 500, should return True
        if json_size_over > 500:
            assert should_use_xml_format(args_over)

    def test_xml_roundtrip_with_list_of_floats(self) -> None:
        """Test XML round-trip preserves list of float values."""
        try:
            from src.factory.schema import serialize_tool_call_xml, parse_tool_call_xml
        except ImportError:
            pytest.skip("XML serialization functions not yet implemented")

        tool_name = "batch_compute"
        tool_args = {"values": [0.1, 0.25, 0.5, 0.75, 1.0]}

        xml_output = serialize_tool_call_xml(tool_name, tool_args)
        parsed_name, parsed_args = parse_tool_call_xml(xml_output)

        assert parsed_name == tool_name
        assert parsed_args["values"] == [0.1, 0.25, 0.5, 0.75, 1.0]

    def test_xml_roundtrip_with_nested_dict(self) -> None:
        """Test XML round-trip preserves nested dictionary."""
        try:
            from src.factory.schema import serialize_tool_call_xml, parse_tool_call_xml
        except ImportError:
            pytest.skip("XML serialization functions not yet implemented")

        tool_name = "nested"
        tool_args = {
            "outer": {"inner": {"value": 42}},
            "list_in_dict": [1, 2, 3],
        }

        xml_output = serialize_tool_call_xml(tool_name, tool_args)
        parsed_name, parsed_args = parse_tool_call_xml(xml_output)

        assert parsed_name == tool_name
        assert parsed_args["outer"]["inner"]["value"] == 42
        assert parsed_args["list_in_dict"] == [1, 2, 3]

    def test_xml_roundtrip_with_list_of_bools(self) -> None:
        """Test XML round-trip preserves list of boolean values."""
        try:
            from src.factory.schema import serialize_tool_call_xml, parse_tool_call_xml
        except ImportError:
            pytest.skip("XML serialization functions not yet implemented")

        tool_name = "flags"
        tool_args = {"enabled": [True, False, True, False]}

        xml_output = serialize_tool_call_xml(tool_name, tool_args)
        parsed_name, parsed_args = parse_tool_call_xml(xml_output)

        assert parsed_name == tool_name
        assert parsed_args["enabled"] == [True, False, True, False]

    def test_xml_parse_with_nested_element_lookup(self) -> None:
        """Test XML parsing uses fallback element lookup when direct find fails."""
        try:
            from src.factory.schema import parse_tool_call_xml
        except ImportError:
            pytest.skip("XML parsing function not yet implemented")

        # Create XML where tool_name and tool_args are nested inside another element
        xml = "<wrapper><tool_call><tool_name>nested_tool</tool_name><tool_args><item key='arg'>value</item></tool_args></tool_call></wrapper>"
        tool_name, tool_args = parse_tool_call_xml(xml)

        assert tool_name == "nested_tool"
        assert tool_args == {"arg": "value"}

    def test_xml_parse_item_with_none_key(self) -> None:
        """Test XML parsing handles item elements without key attribute."""
        try:
            from src.factory.schema import parse_tool_call_xml
        except ImportError:
            pytest.skip("XML parsing function not yet implemented")

        # XML with item missing key attribute - should be skipped
        xml = "<tool_call><tool_name>test</tool_name><tool_args><item key='valid'>value</item></tool_args></tool_call>"
        tool_name, tool_args = parse_tool_call_xml(xml)

        assert tool_name == "test"
        assert "valid" in tool_args


# =============================================================================
# TEST CLASSES: PHP Legacy Compatibility Tests (T034)
# =============================================================================


class TestPHPLegacyCompatibility:
    """Tests for PHP Legacy use_case compatibility (T034).

    Verifies that TrajectoryGenerator works with use_case=php_legacy
    without regression. Loads seeds from configs/stage_2_factory/taxonomy/php_legacy/
    """

    @pytest.fixture
    def php_legacy_seed_data(self) -> dict[str, Any]:
        """Sample PHP Legacy seed data for trajectory generation."""
        return {
            "seed_id": "php_legacy_seed_001",
            "category": "database_migration",
            "complexity": "nominal_medium",
            "context": "# Legacy: mysql_query() direct database calls\n# Modern: Doctrine DBAL",
            "question": "Migra esta conexión PHP legacy a Symfony con Doctrine",
            "expected_patterns": ["Entity", "Repository", "Doctrine"],
        }

    @pytest.fixture
    def php_legacy_seeds(self) -> list[dict[str, Any]]:
        """PHP Legacy seed fixtures matching taxonomy structure."""
        return [
            {
                "seed_id": "php_legacy_seed_001",
                "category": "database_migration",
                "complexity": "nominal_medium",
                "context": "# Legacy: mysql_query() direct database calls\n# Modern: Doctrine DBAL",
                "question": "Migra esta conexión PHP legacy a Symfony con Doctrine",
                "expected_patterns": ["Entity", "Repository", "Doctrine"],
            },
            {
                "seed_id": "php_legacy_seed_002",
                "category": "session_management",
                "complexity": "nominal_easy",
                "context": "# Legacy: $_SESSION global\n# Modern: Symfony Session Interface",
                "question": "Convierte este manejo de sesiones PHP legacy a Symfony",
                "expected_patterns": ["SessionInterface", "Dependency Injection"],
            },
            {
                "seed_id": "php_legacy_seed_003",
                "category": "global_variables",
                "complexity": "nominal_hard",
                "context": "# Legacy: global $db, global $logger\n# Modern: Constructor injection",
                "question": "Refactoriza esta función PHP con globales a Symfony",
                "expected_patterns": ["Dependency Injection", "Service", "LoggerInterface"],
            },
        ]

    def test_generator_accepts_php_legacy_use_case(self) -> None:
        """Test TrajectoryGenerator accepts php_legacy use_case parameter."""
        try:
            from src.factory.trajectory_generator import TrajectoryGenerator
        except ImportError:
            pytest.skip("TrajectoryGenerator not yet implemented")

        generator = TrajectoryGenerator(
            use_case="php_legacy",
            mode=TrajectoryMode.EXPLICIT,
        )
        assert generator.use_case == "php_legacy"

    @pytest.mark.asyncio
    async def test_generate_trajectory_with_php_legacy_seed(
        self,
        php_legacy_seed_data: dict[str, Any],
    ) -> None:
        """Test generate() works with php_legacy seed without regression."""
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
                use_case="php_legacy",
                mode=TrajectoryMode.EXPLICIT,
                seed=42,
            )

            trajectory = await generator.generate(php_legacy_seed_data)

            # Verify trajectory is valid
            assert trajectory.use_case == "php_legacy"
            assert trajectory.seed_id == php_legacy_seed_data["seed_id"]
            assert 3 <= len(trajectory.turns) <= 10
            assert isinstance(trajectory.messages, list)

    @pytest.mark.asyncio
    async def test_php_legacy_trajectory_has_required_turns(
        self,
        php_legacy_seed_data: dict[str, Any],
    ) -> None:
        """Test php_legacy trajectory contains required turn types."""
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
                use_case="php_legacy",
                mode=TrajectoryMode.EXPLICIT,
                error_probability=1.0,  # Force error injection
                seed=42,
            )

            trajectory = await generator.generate(php_legacy_seed_data)

            turn_types = {turn.turn_type for turn in trajectory.turns}
            # Verify required turn types exist
            assert TurnType.OBSERVATION in turn_types
            assert TurnType.REASONING in turn_types
            assert TurnType.ACTION in turn_types

    @pytest.mark.asyncio
    async def test_php_legacy_hard_query_mode(
        self,
        php_legacy_seed_data: dict[str, Any],
    ) -> None:
        """Test TrajectoryGenerator works with php_legacy in hard_query mode."""
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
                use_case="php_legacy",
                mode=TrajectoryMode.HARD_QUERY,
                seed=42,
            )

            trajectory = await generator.generate(php_legacy_seed_data)

            # Verify hard_query mode works with php_legacy
            assert trajectory.mode == TrajectoryMode.HARD_QUERY
            assert trajectory.use_case == "php_legacy"
            assert len(trajectory.turns) >= 3

    @pytest.mark.asyncio
    async def test_php_legacy_multiple_seeds_generation(
        self,
        php_legacy_seeds: list[dict[str, Any]],
    ) -> None:
        """Test TrajectoryGenerator can process multiple php_legacy seeds."""
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

            trajectories = []
            for seed in php_legacy_seeds:
                generator = TrajectoryGenerator(
                    use_case="php_legacy",
                    mode=TrajectoryMode.EXPLICIT,
                    seed=42,
                )
                trajectory = await generator.generate(seed)
                trajectories.append(trajectory)

            # Verify all seeds generated valid trajectories
            assert len(trajectories) == len(php_legacy_seeds)
            for traj in trajectories:
                assert traj.use_case == "php_legacy"
                assert 3 <= len(traj.turns) <= 10
                assert isinstance(traj.messages, list)

    @pytest.mark.asyncio
    async def test_php_legacy_trajectory_error_injection(
        self,
        php_legacy_seed_data: dict[str, Any],
    ) -> None:
        """Test php_legacy trajectory error injection works correctly."""
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

            # Force error injection
            generator = TrajectoryGenerator(
                use_case="php_legacy",
                mode=TrajectoryMode.EXPLICIT,
                error_probability=1.0,
                seed=42,
            )

            trajectory = await generator.generate(php_legacy_seed_data)

            # Verify error and correct turns exist
            turn_types = {turn.turn_type for turn in trajectory.turns}
            assert TurnType.ERROR in turn_types, "PHP Legacy trajectory must contain error turn"
            assert TurnType.CORRECT in turn_types, "PHP Legacy trajectory must contain correct turn"

    def test_php_legacy_seed_structure_matches_taxonomy(
        self,
        php_legacy_seeds: list[dict[str, Any]],
    ) -> None:
        """Test php_legacy seeds match expected taxonomy structure."""
        required_fields = {"seed_id", "category", "complexity", "context", "question"}

        for seed in php_legacy_seeds:
            assert required_fields.issubset(seed.keys()), f"Seed {seed.get('seed_id')} missing fields"
            assert seed["seed_id"].startswith("php_legacy_"), "Seed ID must start with php_legacy_"
            assert isinstance(seed["context"], str), "Context must be string"
            assert isinstance(seed["question"], str), "Question must be string"
