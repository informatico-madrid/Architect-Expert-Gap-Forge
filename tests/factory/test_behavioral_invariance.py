#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0
import pytest

from src.factory.trajectory_generator import TrajectoryGenerator
from src.factory.schema import TrajectoryMode


class TestBehavioralInvariance:
    """Tests verifying template fallback behavior is unchanged."""

    @pytest.mark.asyncio
    async def test_trajectory_without_lm_produces_expected_turns(self):
        """Without DSPy LM, generate() produces template-based turns."""
        gen = TrajectoryGenerator(
            use_case="weather",
            mode=TrajectoryMode.EXPLICIT,
            error_probability=0.0,
        )
        seed_data = {
            "seed_id": "invariant-001",
            "question": "What is the weather?",
            "context": "Local weather data",
            "mode": "explicit",
            "use_case": "weather",
            "error_probability": 0.0,
            "has_error": False,
            "is_cascade": False,
            "tool_format": "json",
        }
        result = await gen.generate(seed_data)
        assert result.seed_id == "invariant-001"
        assert len(result.turns) >= 1
        # Verify first turn is an observation
        assert result.turns[0].turn_type.value == "observation"

    @pytest.mark.asyncio
    async def test_trajectory_mode_preserved(self):
        """Trajectory mode is preserved from seed_data."""
        gen = TrajectoryGenerator(
            use_case="test",
            mode=TrajectoryMode.HARD_QUERY,
            error_probability=0.0,
        )
        seed_data = {
            "seed_id": "mode-test",
            "question": "test",
            "context": "test",
            "mode": "hard_query",
            "use_case": "test",
            "error_probability": 0.0,
            "has_error": False,
            "is_cascade": False,
            "tool_format": "json",
        }
        result = await gen.generate(seed_data)
        assert result.mode.value == "hard_query"
