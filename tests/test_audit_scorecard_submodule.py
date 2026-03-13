#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for src/audit/scorecard.py utility functions."""

from __future__ import annotations

import pytest

from src.audit.scorecard import (
    _composite,
    _extract_code_blocks,
    _grade_label,
    _load_domain_patterns,
    _verdict,
)


class TestExtractCodeBlocks:
    """Tests for _extract_code_blocks function."""

    def test_extract_single_code_block(self) -> None:
        """Should extract a single fenced code block."""
        text = "Some text\n```python\nprint('hello')\n```\nMore text"
        result = _extract_code_blocks(text)
        assert "print('hello')" in result

    def test_extract_multiple_code_blocks(self) -> None:
        """Should extract multiple fenced code blocks."""
        text = "```python\nx = 1\n```\n```yaml\nkey: value\n```"
        result = _extract_code_blocks(text)
        assert "x = 1" in result
        assert "key: value" in result

    def test_extract_no_code_blocks(self) -> None:
        """Should return empty string when no code blocks."""
        text = "Just plain text without code"
        result = _extract_code_blocks(text)
        assert result == ""

    def test_extract_with_language_specifier(self) -> None:
        """Should extract code blocks with language specifier."""
        text = "```javascript\nconst x = 42;\n```"
        result = _extract_code_blocks(text)
        assert "const x = 42;" in result


class TestGradeLabel:
    """Tests for _grade_label function."""

    def test_grade_a_plus(self) -> None:
        """Score >= 90 should return A+."""
        assert _grade_label(90) == "A+"
        assert _grade_label(95) == "A+"
        assert _grade_label(100) == "A+"

    def test_grade_a(self) -> None:
        """Score >= 80 and < 90 should return A."""
        assert _grade_label(80) == "A"
        assert _grade_label(85) == "A"
        assert _grade_label(89) == "A"

    def test_grade_b(self) -> None:
        """Score >= 70 and < 80 should return B."""
        assert _grade_label(70) == "B"
        assert _grade_label(75) == "B"
        assert _grade_label(79) == "B"

    def test_grade_c(self) -> None:
        """Score >= 60 and < 70 should return C."""
        assert _grade_label(60) == "C"
        assert _grade_label(65) == "C"
        assert _grade_label(69) == "C"

    def test_grade_d(self) -> None:
        """Score >= 50 and < 60 should return D."""
        assert _grade_label(50) == "D"
        assert _grade_label(55) == "D"
        assert _grade_label(59) == "D"

    def test_grade_f(self) -> None:
        """Score < 50 should return F."""
        assert _grade_label(0) == "F"
        assert _grade_label(25) == "F"
        assert _grade_label(49) == "F"


class TestVerdict:
    """Tests for _verdict function."""

    def test_verdict_pass(self) -> None:
        """Grade >= 80 should return PASS."""
        grade = 80
        result = _verdict(grade)
        assert "PASS" in result

    def test_verdict_conditional(self) -> None:
        """Grade >= 60 and < 80 should return CONDITIONAL."""
        grade = 60
        result = _verdict(grade)
        assert "CONDITIONAL" in result

    def test_verdict_warn(self) -> None:
        """Grade >= 40 and < 60 should return WARN."""
        grade = 40
        result = _verdict(grade)
        assert "WARN" in result

    def test_verdict_fail(self) -> None:
        """Grade < 40 should return FAIL."""
        grade = 30
        result = _verdict(grade)
        assert "FAIL" in result


class TestComposite:
    """Tests for _composite function."""

    def test_composite_with_all_weights(self) -> None:
        """Should compute composite score from all dimensions."""
        scores = {
            "ha_modernity": 0.8,
            "ha_quality": 0.9,
            "ha_structure": 0.7,
            "ha_style": 0.85,
            "ha_context": 0.75,
        }
        result = _composite(scores)
        assert 0.0 <= result <= 1.0

    def test_composite_with_missing_dimensions(self) -> None:
        """Should handle missing dimensions gracefully."""
        scores = {"ha_modernity": 0.8}
        result = _composite(scores)
        assert 0.0 <= result <= 1.0

    def test_composite_with_empty_scores(self) -> None:
        """Should return 0 for empty scores."""
        scores = {}
        result = _composite(scores)
        assert result == 0.0


class TestLoadDomainPatterns:
    """Tests for _load_domain_patterns function."""

    def test_load_domain_patterns_returns_dict(self) -> None:
        """Should return a dictionary (possibly empty)."""
        result = _load_domain_patterns()
        assert isinstance(result, dict)


class TestComputeScorecard:
    """Tests for compute_scorecard function."""

    def test_compute_scorecard_dimension_key_mismatch(self) -> None:
        """Should raise ValueError when baseline and adapter have different keys."""
        from src.audit.schema import ExamRecord

        exam = ExamRecord(
            id="test-1",
            example_type="nominal",
            evol_difficulty="easy",
            fragment_name="test.py",
            source_file="test.yaml",
            user_prompt="test prompt",
            reference_response="test ref",
            gold_injected=True,
            ldi=1.0,
        )
        judge_resp = {
            "baseline": {"ha_modernity": 0.8, "functionality": 0.9},
            "adapter": {"ha_modernity": 0.9, "style": 0.7},  # Different keys
            "reasoning": "test",
        }

        from src.audit.scorecard import compute_scorecard

        with pytest.raises(ValueError, match="Dimension key mismatch"):
            compute_scorecard(exam, judge_resp)

    def test_compute_scorecard_with_adapter_response(self) -> None:
        """Should apply pattern penalty when adapter_resp contains code."""
        from src.audit.schema import ExamRecord, ScoreCard

        exam = ExamRecord(
            id="test-1",
            example_type="nominal",
            evol_difficulty="easy",
            fragment_name="test.py",
            source_file="test.yaml",
            user_prompt="test prompt",
            reference_response="test ref",
            gold_injected=True,
            ldi=1.0,
            exam_question="test question",
            target_patterns=["entity_name", "state_name"],
        )
        judge_resp = {
            "baseline": {"ha_modernity": 0.8, "functionality": 0.9},
            "adapter": {"ha_modernity": 0.8, "functionality": 0.9},
            "reasoning": "test",
        }
        # Adapter response with code blocks (missing target patterns)
        adapter_resp = """Here is the code:
```python
# This code doesn't have the expected patterns
def foo():
    pass
```"""

        from src.audit.scorecard import compute_scorecard

        scorecard = compute_scorecard(exam, judge_resp, adapter_resp)
        assert isinstance(scorecard, ScoreCard)
        # Penalty should have been applied
        assert scorecard.ha_modernity < 0.8 or scorecard.functionality < 0.9

    def test_compute_scorecard_notes_include_missing_patterns(self) -> None:
        """Should include missing patterns in notes."""
        from src.audit.schema import ExamRecord

        exam = ExamRecord(
            id="test-1",
            example_type="nominal",
            evol_difficulty="easy",
            fragment_name="test.py",
            source_file="test.yaml",
            user_prompt="test prompt",
            reference_response="test ref",
            gold_injected=True,
            ldi=1.0,
            exam_question="test question",
            target_patterns=["missing_pattern"],
        )
        judge_resp = {
            "baseline": {"ha_modernity": 0.8},
            "adapter": {"ha_modernity": 0.8},
            "reasoning": "test",
        }
        adapter_resp = "```python\n# no patterns here\n```"

        from src.audit.scorecard import compute_scorecard

        scorecard = compute_scorecard(exam, judge_resp, adapter_resp)
        assert "missing_pattern" in scorecard.notes
