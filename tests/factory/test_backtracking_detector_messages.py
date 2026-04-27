"""Unit tests for BacktrackingDetector message-based detection."""
from src.factory.backtracking_detector import BacktrackingDetector, BacktrackingResult
from src.utils.schema import Message


class TestBacktrackingDetectorMessages:
    """Tests for BacktrackingDetector detect_from_messages."""

    def test_empty_messages(self):
        result = BacktrackingDetector.detect_from_messages([])
        assert isinstance(result, BacktrackingResult)
        assert result.detected is False
        assert result.reason == "no_turns"

    def test_no_error_pattern(self):
        messages = [
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there!"),
        ]
        result = BacktrackingDetector.detect_from_messages(messages)
        assert isinstance(result, BacktrackingResult)
        assert result.detected is False
        assert result.reason == "none"

    def test_error_recovery_in_messages(self):
        messages = [
            Message(role="user", content="Setup failed"),
            Message(role="assistant", content="Let me correct that and fix the issue"),
        ]
        result = BacktrackingDetector.detect_from_messages(messages)
        assert isinstance(result, BacktrackingResult)
        assert result.detected is True
        assert 0 in result.indices
        assert 1 in result.indices
        assert result.reason == "error_recovery"

    def test_case_insensitive_detection(self):
        messages = [
            Message(role="user", content="ERROR in processing"),
            Message(role="assistant", content="RECOVERY initiated"),
        ]
        result = BacktrackingDetector.detect_from_messages(messages)
        assert isinstance(result, BacktrackingResult)
        assert result.detected is True
        assert result.reason == "error_recovery"
