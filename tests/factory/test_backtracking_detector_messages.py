"""Unit tests for BacktrackingDetector message-based detection."""
import pytest
from src.utils.schema import Message
from src.factory.backtracking_detector import BacktrackingDetector


class TestBacktrackingDetectorMessages:
    """Tests for BacktrackingDetector detect_from_messages."""

    def test_empty_messages(self):
        detected, indices, reason = BacktrackingDetector.detect_from_messages([])
        assert detected is False
        assert reason == "no_turns"

    def test_no_error_pattern(self):
        messages = [
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there!"),
        ]
        detected, indices, reason = BacktrackingDetector.detect_from_messages(messages)
        assert detected is False
        assert reason == "none"

    def test_error_recovery_in_messages(self):
        messages = [
            Message(role="user", content="Setup failed"),
            Message(role="assistant", content="Let me correct that and fix the issue"),
        ]
        detected, indices, reason = BacktrackingDetector.detect_from_messages(messages)
        assert detected is True
        assert 0 in indices
        assert 1 in indices
        assert reason == "error_recovery"

    def test_case_insensitive_detection(self):
        messages = [
            Message(role="user", content="ERROR in processing"),
            Message(role="assistant", content="RECOVERY initiated"),
        ]
        detected, indices, reason = BacktrackingDetector.detect_from_messages(messages)
        assert detected is True
        assert reason == "error_recovery"
