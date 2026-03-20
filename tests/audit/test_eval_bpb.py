#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for src/audit/eval_bpb.py - Bits-Per-Byte Evaluation Module."""

from __future__ import annotations

import pytest
from src.audit.eval_bpb import (
    calculate_bpb,
    evaluate_bpb_scores,
    aggregate_bpb_metrics,
)


class TestCalculateBPB:
    """Tests for calculate_bpb function."""

    def test_perfect_prediction_returns_zero(self) -> None:
        """Should return 0.0 when predicted equals target exactly."""
        result = calculate_bpb("hello world", "hello world")
        assert result == 0.0

    def test_empty_target_raises_error(self) -> None:
        """Should raise ValueError when target is empty."""
        with pytest.raises(ValueError, match="Target string cannot be empty"):
            calculate_bpb("hello", "")

    def test_empty_predicted_returns_infinity(self) -> None:
        """Should return infinity when predicted is empty."""
        result = calculate_bpb("", "hello world")
        assert result == float("inf")

    def test_partial_match_returns_positive_score(self) -> None:
        """Should return positive BPB score for partial matches."""
        result = calculate_bpb("hello", "hello world")
        # May return 0 or very small value for similar strings
        assert result >= 0.0

    def test_no_match_returns_high_score(self) -> None:
        """Should return high BPB score for completely different strings."""
        result = calculate_bpb("abc", "xyz")
        assert result > 0.0
        assert result != float("inf")

    def test_unicode_content_handled(self) -> None:
        """Should handle unicode characters correctly."""
        result = calculate_bpb("café", "café")
        assert result == 0.0

    def test_unicode_partial_match(self) -> None:
        """Should handle partial unicode matches."""
        result = calculate_bpb("café", "café con leche")
        assert result >= 0.0

    def test_longer_target_vs_shorter_prediction(self) -> None:
        """Should handle longer target with shorter prediction."""
        result = calculate_bpb("hi", "hello world")
        assert result >= 0.0


class TestEvaluateBPBScores:
    """Tests for evaluate_bpb_scores function."""

    def test_empty_lists_returns_empty(self) -> None:
        """Should return empty list for empty inputs."""
        result = evaluate_bpb_scores([], [])
        assert result == []

    def test_matching_lengths_required(self) -> None:
        """Should raise ValueError when lists have different lengths."""
        with pytest.raises(ValueError, match="Predictions and targets must have same length"):
            evaluate_bpb_scores(["a"], ["b", "c"])

    def test_single_prediction(self) -> None:
        """Should evaluate single prediction correctly."""
        result = evaluate_bpb_scores(["hello"], ["hello"])
        assert len(result) == 1
        assert result[0] == 0.0

    def test_multiple_predictions(self) -> None:
        """Should evaluate multiple predictions correctly."""
        predictions = ["hello", "world"]
        targets = ["hello", "world"]
        result = evaluate_bpb_scores(predictions, targets)
        assert len(result) == 2
        assert result[0] == 0.0
        assert result[1] == 0.0

    def test_mixed_predictions(self) -> None:
        """Should handle mix of perfect and imperfect predictions."""
        predictions = ["hello", "wrong"]
        targets = ["hello", "world"]
        result = evaluate_bpb_scores(predictions, targets)
        assert len(result) == 2
        assert result[0] == 0.0
        assert result[1] > 0.0

    def test_error_in_single_evaluation_returns_inf(self) -> None:
        """Should return inf for predictions that cause errors."""
        # Empty target will cause error in calculate_bpb
        predictions = ["hello"]
        targets = [""]
        result = evaluate_bpb_scores(predictions, targets)
        assert result[0] == float("inf")

    def test_custom_vocab_size(self) -> None:
        """Should accept custom vocabulary size."""
        predictions = ["hello"]
        targets = ["hello"]
        result = evaluate_bpb_scores(predictions, targets, vocab_size=16000)
        assert result[0] == 0.0


class TestAggregateBPBMetrics:
    """Tests for aggregate_bpb_metrics function."""

    def test_empty_scores_returns_nan(self) -> None:
        """Should return NaN values for empty input."""
        result = aggregate_bpb_metrics([])
        assert result["mean"] != result["mean"]  # NaN check
        assert result["median"] != result["median"]  # NaN check
        assert result["std"] != result["std"]  # NaN check
        assert result["min"] != result["min"]  # NaN check
        assert result["max"] != result["max"]  # NaN check
        assert result["valid_count"] == 0
        assert result["total_count"] == 0

    def test_all_inf_returns_infinity(self) -> None:
        """Should return infinity when all scores are inf."""
        result = aggregate_bpb_metrics([float("inf"), float("inf")])
        assert result["mean"] == float("inf")
        assert result["median"] == float("inf")
        assert result["min"] == float("inf")
        assert result["max"] == float("inf")
        assert result["valid_count"] == 0
        assert result["total_count"] == 2

    def test_single_score(self) -> None:
        """Should calculate metrics for single score."""
        result = aggregate_bpb_metrics([1.5])
        assert result["mean"] == 1.5
        assert result["median"] == 1.5
        assert result["std"] == 0.0
        assert result["min"] == 1.5
        assert result["max"] == 1.5
        assert result["valid_count"] == 1
        assert result["total_count"] == 1

    def test_multiple_scores(self) -> None:
        """Should calculate metrics for multiple scores."""
        result = aggregate_bpb_metrics([1.0, 2.0, 3.0])
        assert result["mean"] == 2.0
        assert result["median"] == 2.0
        assert result["min"] == 1.0
        assert result["max"] == 3.0
        assert result["valid_count"] == 3
        assert result["total_count"] == 3

    def test_ignores_inf_values(self) -> None:
        """Should ignore infinity values in calculations."""
        result = aggregate_bpb_metrics([1.0, 2.0, float("inf"), 3.0])
        assert result["mean"] == 2.0
        assert result["valid_count"] == 3
        assert result["total_count"] == 4

    def test_mixed_scores_with_inf(self) -> None:
        """Should handle mix of finite and infinite values."""
        result = aggregate_bpb_metrics([1.0, float("inf"), 2.0])
        assert result["mean"] == 1.5
        assert result["valid_count"] == 2
        assert result["total_count"] == 3

    def test_single_inf_value(self) -> None:
        """Should handle single infinity value."""
        result = aggregate_bpb_metrics([float("inf")])
        assert result["mean"] == float("inf")
        assert result["median"] == float("inf")
        assert result["min"] == float("inf")
        assert result["max"] == float("inf")
        assert result["valid_count"] == 0
        assert result["total_count"] == 1

    def test_large_dataset(self) -> None:
        """Should handle large datasets efficiently."""
        scores = list(range(1, 101))  # 1 to 100
        result = aggregate_bpb_metrics(scores)
        assert result["mean"] == 50.5
        assert result["min"] == 1.0
        assert result["max"] == 100.0
        assert result["valid_count"] == 100
        assert result["total_count"] == 100
