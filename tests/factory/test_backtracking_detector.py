#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

from src.factory.schema import Turn, TurnType
from src.factory.backtracking_detector import BacktrackingDetector, BacktrackingResult


class TestBacktrackingDetector:
    """Tests for BacktrackingDetector defined in src.factory.backtracking_detector."""

    def test_empty_turns(self):
        result = BacktrackingDetector.detect([])
        assert isinstance(result, BacktrackingResult)
        assert result.detected is False
        assert result.indices == []
        assert result.reason == "no_turns"

    def test_no_backtracking(self):
        turns = [
            Turn(turn_index=0, turn_type=TurnType.OBSERVATION, content="test"),
            Turn(turn_index=1, turn_type=TurnType.REASONING, content="thinking"),
            Turn(turn_index=2, turn_type=TurnType.ACTION, content="action"),
        ]
        result = BacktrackingDetector.detect(turns)
        assert isinstance(result, BacktrackingResult)
        assert result.detected is False
        assert result.reason == "none"

    def test_error_recovery_detected(self):
        turns = [
            Turn(turn_index=0, turn_type=TurnType.OBSERVATION, content="obs"),
            Turn(turn_index=1, turn_type=TurnType.ERROR, content="failed"),
            Turn(turn_index=2, turn_type=TurnType.CORRECT, content="fixed"),
        ]
        result = BacktrackingDetector.detect(turns)
        assert isinstance(result, BacktrackingResult)
        assert result.detected is True
        assert 1 in result.indices
        assert 2 in result.indices
        assert result.reason == "error_recovery"

    def test_no_dspy_import(self):
        assert "dspy" not in open("src/factory/backtracking_detector.py").read()
