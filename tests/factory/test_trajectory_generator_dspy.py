#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

import pytest

from src.factory.dspy_utils import get_predict
from src.factory.schema import AgenticTrajectory, TrajectoryMode
from src.factory.trajectory_signature import TrajectorySignature


def test_get_predict_returns_none_without_lm():
    """Without LM configured, get_predict returns None (template path)."""
    assert get_predict(TrajectorySignature) is None


@pytest.mark.asyncio
async def test_generator_creates_trajectory_without_dspy():
    """Generator produces a 3+ turn trajectory when no LM is configured (template fallback)."""
    from src.factory.trajectory_generator import TrajectoryGenerator

    gen = TrajectoryGenerator(
        use_case="home_assistant",
        mode=TrajectoryMode.EXPLICIT,
        error_probability=0.0,
    )
    seed_data = {
        "seed_id": "test-001",
        "question": "Test question",
        "context": "Test context",
    }
    result = await gen.generate(seed_data)
    assert isinstance(result, AgenticTrajectory)
    assert result.seed_id == "test-001"
    assert len(result.turns) >= 3
    for turn in result.turns:
        assert turn.content is not None and len(turn.content) > 0


def test_dual_path_fallback():
    """When predictor is None, template path is used."""
    # Without LM, predictor should be None
    assert get_predict(TrajectorySignature) is None
    # This means generate() will use the template fallback path
