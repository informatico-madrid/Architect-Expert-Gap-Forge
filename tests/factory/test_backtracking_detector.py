"""Unit tests for BacktrackingDetector basic detection."""
import pytest
from src.factory.schema import Turn, TurnType
from src.factory.backtracking_detector import BacktrackingDetector, BacktrackingResult


class TestBacktrackingDetector:
    """Tests for BacktrackingDetector defined in src.factory.backtracking_detector."""

    def test_empty_turns(self):
        detected, indices, reason = BacktrackingDetector.detect([])
        assert detected is False
        assert indices == []
        assert reason == "no_turns"

    def test_no_backtracking(self):
        turns = [
            Turn(turn_index=0, turn_type=TurnType.OBSERVATION, content="test"),
            Turn(turn_index=1, turn_type=TurnType.REASONING, content="thinking"),
            Turn(turn_index=2, turn_type=TurnType.ACTION, content="action"),
        ]
        detected, indices, reason = BacktrackingDetector.detect(turns)
        assert detected is False
        assert reason == "none"

    def test_error_recovery_detected(self):
        turns = [
            Turn(turn_index=0, turn_type=TurnType.OBSERVATION, content="obs"),
            Turn(turn_index=1, turn_type=TurnType.ERROR, content="failed"),
            Turn(turn_index=2, turn_type=TurnType.CORRECT, content="fixed"),
        ]
        detected, indices, reason = BacktrackingDetector.detect(turns)
        assert detected is True
        assert 1 in indices
        assert 2 in indices
        assert reason == "error_recovery"

    def test_no_dspy_import(self):
        assert "dspy" not in open("src/factory/backtracking_detector.py").read()
