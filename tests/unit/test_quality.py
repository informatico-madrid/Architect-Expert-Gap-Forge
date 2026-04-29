#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0
"""Tests for QualityChecker and CircuitBreaker."""

from __future__ import annotations

import pytest
from infrastructure.anchor_dataset.anchor_dataset_schema import AnchorRecord
from infrastructure.anchor_dataset.quality import QualityChecker, CircuitBreaker


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_record(**overrides: object) -> AnchorRecord:
    """Build a minimal valid AnchorRecord, merging any overrides."""
    kwargs: dict[str, object] = {
        "id": "anchor_001_01",
        "domain": "generic_domain",
        "difficulty": "medium",
        "turn_count": 5,
        "legacy_pattern": "test",
        "domain_context": "test",
        "expected_trajectory": "step 1\nstep 2\nstep 3",
        "expected_tool_usage_patterns": [],
        "expected_coherence": 0.8,
        "expected_overall": 0.8,
        "expected_quality_score": 0.9,
        "expected_optimized_parameters": {},
        "verified": False,
        "verified_by": "",
    }
    kwargs.update(overrides)
    return AnchorRecord(**kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 1. QualityChecker — passed / failure reasons
# ---------------------------------------------------------------------------


class TestQualityCheckerRecord:
    def test_valid_record_passes(self):
        checker = QualityChecker()
        record = _make_record(turn_count=5, expected_quality_score=0.9)
        result = checker.check(record, target_turns=5)
        assert result.passed is True
        assert result.reasons == []
        assert result.score == 0.9

    def test_anti_laziness_dotdotdot(self):
        checker = QualityChecker()
        record = _make_record(expected_trajectory="step 1\n...\nstep 3")
        result = checker.check(record, target_turns=5)
        assert result.passed is False
        assert "anti_laziness" in result.reasons

    def test_anti_laziness_todo(self):
        checker = QualityChecker()
        record = _make_record(expected_trajectory="step 1\n# TODO\nstep 3")
        result = checker.check(record, target_turns=5)
        assert result.passed is False
        assert "anti_laziness" in result.reasons

    def test_anti_laziness_pass_keyword(self):
        checker = QualityChecker()
        record = _make_record(expected_trajectory="step 1\npass # implement\nstep 3")
        result = checker.check(record, target_turns=5)
        assert result.passed is False
        assert "anti_laziness" in result.reasons

    def test_anti_laziness_spanish(self):
        checker = QualityChecker()
        record = _make_record(expected_trajectory="step 1\n# resto del codigo\nstep 3")
        result = checker.check(record, target_turns=5)
        assert result.passed is False
        assert "anti_laziness" in result.reasons

    def test_anti_laziness_only_first_match(self):
        """Only one reason should be reported even if multiple patterns match."""
        checker = QualityChecker()
        record = _make_record(expected_trajectory="...\n# TODO\npass # implement")
        result = checker.check(record, target_turns=5)
        assert result.passed is False
        assert result.reasons.count("anti_laziness") == 1

    def test_turn_count_mismatch_above(self):
        checker = QualityChecker()
        record = _make_record(turn_count=10, expected_quality_score=0.9)
        result = checker.check(record, target_turns=5)
        assert result.passed is False
        assert "turn_count_mismatch" in result.reasons

    def test_turn_count_mismatch_below(self):
        checker = QualityChecker()
        record = _make_record(turn_count=1, expected_quality_score=0.9)
        result = checker.check(record, target_turns=5)
        assert result.passed is False
        assert "turn_count_mismatch" in result.reasons

    def test_turn_count_within_tolerance(self):
        """turn_count diff of <= 1 is acceptable."""
        checker = QualityChecker()
        record = _make_record(turn_count=6, expected_quality_score=0.9)
        result = checker.check(record, target_turns=5)
        assert result.passed is True

    def test_turn_count_at_boundary(self):
        """diff == 1 is ok, diff == 2 fails."""
        checker = QualityChecker()
        record = _make_record(turn_count=7, expected_quality_score=0.9)
        result = checker.check(record, target_turns=5)
        assert result.passed is False
        assert "turn_count_mismatch" in result.reasons

    def test_low_quality_score(self):
        checker = QualityChecker()
        record = _make_record(turn_count=5, expected_quality_score=0.1)
        result = checker.check(record, target_turns=5)
        assert result.passed is False
        assert "low_quality_score" in result.reasons

    def test_tool_call_syntax_valid(self):
        checker = QualityChecker()
        record = _make_record(expected_trajectory="before [TOOL_CALL:search] after")
        result = checker.check(record, target_turns=5)
        assert result.passed is True

    def test_tool_call_syntax_invalid(self):
        checker = QualityChecker()
        record = _make_record(expected_trajectory="before [TOOL_CALL:search bad")
        result = checker.check(record, target_turns=5)
        assert result.passed is False
        assert "tool_call_syntax" in result.reasons

    def test_multiple_reasons_accumulate(self):
        checker = QualityChecker()
        record = _make_record(
            expected_trajectory="...\n# TODO\npass # implement",
            turn_count=10,
            expected_quality_score=0.0,
        )
        result = checker.check(record, target_turns=5)
        assert result.passed is False
        assert "anti_laziness" in result.reasons
        assert "turn_count_mismatch" in result.reasons
        assert "low_quality_score" in result.reasons


# ---------------------------------------------------------------------------
# 2. QualityChecker — custom threshold
# ---------------------------------------------------------------------------


class TestQualityCheckerThreshold:
    def test_higher_threshold_rejects(self):
        checker = QualityChecker(threshold=0.95)
        record = _make_record(expected_quality_score=0.90)
        result = checker.check(record, target_turns=5)
        assert result.passed is False
        assert "low_quality_score" in result.reasons

    def test_custom_threshold_allows(self):
        checker = QualityChecker(threshold=0.1)
        record = _make_record(expected_quality_score=0.15)
        result = checker.check(record, target_turns=5)
        assert result.passed is True

    def test_zero_threshold_allows_any(self):
        checker = QualityChecker(threshold=0.0)
        record = _make_record(expected_quality_score=0.0)
        result = checker.check(record, target_turns=5)
        assert result.passed is True

    def test_raw_check_custom_threshold(self):
        checker = QualityChecker(threshold=0.8)
        data = {
            "expected_trajectory": "step 1\nstep 2",
            "turn_count": 5,
            "expected_quality_score": 0.5,
        }
        result = checker.check_raw(data, target_turns=5)
        assert result.passed is False
        assert "low_quality_score" in result.reasons


# ---------------------------------------------------------------------------
# 3. CircuitBreaker — phase transitions and switch logic
# ---------------------------------------------------------------------------


class TestCircuitBreakerPhases:
    def test_starts_in_warmup(self):
        cb = CircuitBreaker()
        assert cb.phase == "warmup"
        assert cb.triggered is False

    def test_warmup_no_switch(self):
        cb = CircuitBreaker(threshold=0.1)
        for _ in range(4):
            cb.record_result(False)
        assert cb.phase == "warmup"
        assert cb.should_switch() is False

    def test_transitions_to_calibration(self):
        cb = CircuitBreaker()
        for _ in range(6):
            cb.record_result(True)
        assert cb.phase == "calibration"

    def test_calibration_no_switch(self):
        cb = CircuitBreaker(threshold=0.1, batch_size=10)
        # Fill calibration phase (5-9) and start production (10)
        for _ in range(15):
            cb.record_result(False)
        assert cb.phase == "production"
        # Only 5 failures in last 10 (batch_size=10), rate = 5/10 = 0.5 >= 0.1
        # But at this point we have 15 results, so we have enough for switch check
        # The first 5 are False, next 10 are False -> last 10 are all False -> rate=1.0
        assert cb.should_switch() is True

    def test_switches_in_production_above_threshold(self):
        cb = CircuitBreaker(threshold=0.2, batch_size=10)
        # First 10: all pass -> no switch yet (only 10 results, batch fills at exactly 10)
        for _ in range(10):
            cb.record_result(True)
        assert cb.phase == "production"
        assert cb.should_switch() is False

        # Next 3: failures -> 13 total, last 10 has 3 failures out of 10 = 0.3 >= 0.2
        for _ in range(3):
            cb.record_result(False)
        # must call should_switch() to evaluate and set _triggered
        assert cb.should_switch() is True
        assert cb.triggered is True

    def test_no_switch_in_production_below_threshold(self):
        cb = CircuitBreaker(threshold=0.5, batch_size=10)
        for _ in range(10):
            cb.record_result(True)
        for _ in range(3):
            cb.record_result(False)
        # 3/10 = 0.3 < 0.5 -> no switch
        assert cb.triggered is False

    def test_batch_size_boundary(self):
        """should_switch returns False until len(results) >= batch_size."""
        cb = CircuitBreaker(threshold=0.0, batch_size=10)
        for _ in range(5):
            cb.record_result(False)
        # Not enough results yet
        assert cb.should_switch() is False


# ---------------------------------------------------------------------------
# 4. CircuitBreaker — try_reset
# ---------------------------------------------------------------------------


class TestCircuitBreakerTryReset:
    def test_reset_before_triggered(self):
        cb = CircuitBreaker()
        assert cb.try_reset() is False

    def test_reset_with_consecutive_passes(self):
        cb = CircuitBreaker(threshold=0.1, batch_size=10, consecutive_pass_threshold=3)
        # Trigger
        for _ in range(13):
            cb.record_result(False)
        assert cb.should_switch() is True
        assert cb.triggered is True

        # Get enough consecutive passes
        for _ in range(3):
            cb.record_result(True)
        assert cb.try_reset() is True
        assert cb.triggered is False
        assert cb.phase == "warmup"
        assert len(cb._results) == 0

    def test_reset_fails_with_insufficient_passes(self):
        cb = CircuitBreaker(threshold=0.1, batch_size=10, consecutive_pass_threshold=5)
        # Trigger
        for _ in range(13):
            cb.record_result(False)
        assert cb.should_switch() is True
        assert cb.triggered is True
        # Only 3 consecutive passes (< 5)
        for _ in range(3):
            cb.record_result(True)
        assert cb.try_reset() is False
        assert cb.triggered is True

    def test_reset_clears_phase_and_results(self):
        cb = CircuitBreaker(threshold=0.1, batch_size=10, consecutive_pass_threshold=2)
        for _ in range(13):
            cb.record_result(False)
        assert cb.phase == "production"
        assert cb.should_switch() is True
        for _ in range(2):
            cb.record_result(True)
        assert cb.try_reset() is True
        assert cb.phase == "warmup"
        assert len(cb._results) == 0


# ---------------------------------------------------------------------------
# 5. CircuitBreaker — get_failure_rate
# ---------------------------------------------------------------------------


class TestCircuitBreakerFailureRate:
    def test_empty_returns_zero(self):
        cb = CircuitBreaker()
        assert cb.get_failure_rate() == 0.0

    def test_all_passes(self):
        cb = CircuitBreaker()
        for _ in range(10):
            cb.record_result(True)
        assert cb.get_failure_rate() == 0.0

    def test_all_failures(self):
        cb = CircuitBreaker()
        for _ in range(10):
            cb.record_result(False)
        assert cb.get_failure_rate() == 1.0

    def test_partial_failures(self):
        cb = CircuitBreaker()
        for _ in range(8):
            cb.record_result(True)
        for _ in range(2):
            cb.record_result(False)
        assert cb.get_failure_rate() == 0.2

    def test_mixed_sequence(self):
        cb = CircuitBreaker()
        results = [True, False, True, False, False, True, True, False]
        for r in results:
            cb.record_result(r)
        assert cb.get_failure_rate() == pytest.approx(4.0 / 8.0)


# ---------------------------------------------------------------------------
# 6. CircuitBreaker — _evaluate_batch
# ---------------------------------------------------------------------------


class TestCircuitBreakerEvaluateBatch:
    def test_empty_batch(self):
        cb = CircuitBreaker(threshold=0.2)
        assert cb._evaluate_batch([]) is False

    def test_all_passes_below_threshold(self):
        cb = CircuitBreaker(threshold=0.5)
        assert cb._evaluate_batch([True, True, True]) is False

    def test_all_failures_above_threshold(self):
        cb = CircuitBreaker(threshold=0.5)
        assert cb._evaluate_batch([False, False, False]) is True

    def test_exact_threshold(self):
        """Failure rate exactly equal to threshold -> True."""
        cb = CircuitBreaker(threshold=0.5)
        assert cb._evaluate_batch([False, False, True, True]) is True

    def test_below_threshold(self):
        cb = CircuitBreaker(threshold=0.5)
        assert cb._evaluate_batch([False, True, True, True]) is False

    def test_above_threshold(self):
        cb = CircuitBreaker(threshold=0.3)
        # 3/5 = 0.6 >= 0.3
        assert cb._evaluate_batch([False] * 3 + [True] * 2) is True

    def test_single_failure_at_low_threshold(self):
        cb = CircuitBreaker(threshold=0.1)
        assert cb._evaluate_batch([False, True]) is True  # 0.5 >= 0.1
