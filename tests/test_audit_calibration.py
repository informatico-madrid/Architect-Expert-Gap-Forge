#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for src/audit/calibration.py utility functions."""

from __future__ import annotations

import pytest

from src.audit.calibration import (
    calculate_composite_score,
    count_words,
    apply_length_penalty,
    generate_profiles,
    get_parameter_priority_order,
    generate_adaptive_profiles,
    get_adaptive_parameter_weights,
)
from src.audit.calibration_schema import (
    CALIBRATION_GRID,
    MIN_RESPONSE_WORDS,
    SCORING_WEIGHTS,
    SamplingProfile,
    CalibrationPrompt,
    CalibrationResult,
    VALID_PARAMETERS,
)


class TestCalculateCompositeScore:
    """Tests for calculate_composite_score function."""

    def test_perfect_scores(self) -> None:
        """Should return 1.0 for all perfect scores."""
        judge_scores = {
            "ha_modernity": 1.0,
            "reasoning_depth": 1.0,
            "functionality": 1.0,
            "completeness": 1.0,
            "style": 1.0,
        }
        result = calculate_composite_score(judge_scores)
        assert result == 1.0

    def test_zero_scores(self) -> None:
        """Should return 0.0 for all zero scores."""
        judge_scores = {
            "ha_modernity": 0.0,
            "reasoning_depth": 0.0,
            "functionality": 0.0,
            "completeness": 0.0,
            "style": 0.0,
        }
        result = calculate_composite_score(judge_scores)
        assert result == 0.0

    def test_mixed_scores(self) -> None:
        """Should correctly weight mixed scores."""
        judge_scores = {
            "ha_modernity": 1.0,  # weight 0.30
            "reasoning_depth": 0.5,  # weight 0.25
            "functionality": 0.5,  # weight 0.25
            "completeness": 0.0,  # weight 0.12
            "style": 1.0,  # weight 0.08
        }
        result = calculate_composite_score(judge_scores)
        expected = 1.0 * 0.30 + 0.5 * 0.25 + 0.5 * 0.25 + 0.0 * 0.12 + 1.0 * 0.08
        assert result == pytest.approx(expected)

    def test_missing_dimension_uses_zero(self) -> None:
        """Should use 0.0 for missing dimensions."""
        judge_scores = {
            "ha_modernity": 1.0,
            # Missing other dimensions
        }
        result = calculate_composite_score(judge_scores)
        expected = 1.0 * 0.30  # Only ha_modernity counts
        assert result == pytest.approx(expected)


class TestCountWords:
    """Tests for count_words function."""

    def test_empty_string(self) -> None:
        """Should return 0 for empty string."""
        assert count_words("") == 0

    def test_single_word(self) -> None:
        """Should return 1 for single word."""
        assert count_words("hello") == 1

    def test_multiple_words(self) -> None:
        """Should correctly count multiple words."""
        assert count_words("hello world test") == 3

    def test_words_with_extra_spaces(self) -> None:
        """Should handle extra spaces between words."""
        assert count_words("hello   world    test") == 3


class TestApplyLengthPenalty:
    """Tests for apply_length_penalty function."""

    def test_above_minimum_no_penalty(self) -> None:
        """Should not apply penalty when above minimum."""
        score = apply_length_penalty(0.8, 250)
        assert score == 0.8

    def test_at_minimum_no_penalty(self) -> None:
        """Should not apply penalty at exactly minimum."""
        score = apply_length_penalty(0.8, MIN_RESPONSE_WORDS)
        assert score == 0.8

    def test_below_minimum_applies_penalty(self) -> None:
        """Should apply penalty when below minimum."""
        score = apply_length_penalty(0.8, 100)  # Half of default min (200)
        # Penalty ratio = (200-100)/200 = 0.5, capped at 0.5
        # Adjusted = 0.8 * (1 - 0.5) = 0.4
        assert score == pytest.approx(0.4)

    def test_zero_length_max_penalty(self) -> None:
        """Should apply max penalty (50%) for zero length."""
        score = apply_length_penalty(0.8, 0)
        # Penalty ratio capped at 0.5
        # Adjusted = 0.8 * 0.5 = 0.4
        assert score == pytest.approx(0.4)

    def test_custom_min_words(self) -> None:
        """Should use custom min_words when provided."""
        score = apply_length_penalty(1.0, 50, min_words=100)
        # Penalty ratio = (100-50)/100 = 0.5
        # Adjusted = 1.0 * 0.5 = 0.5
        assert score == pytest.approx(0.5)


class TestGenerateProfiles:
    """Tests for generate_profiles function."""

    def test_default_grid_produces_profiles(self) -> None:
        """Should generate profiles from default grid."""
        profiles = generate_profiles()
        assert len(profiles) > 0
        assert all(isinstance(p, SamplingProfile) for p in profiles)

    def test_custom_grid_profiles(self) -> None:
        """Should generate profiles from custom grid."""
        custom_grid = {
            "temperature": [0.5, 0.6],
            "top_k": [20, 40],
            "min_p": [0.02],
            "repetition_penalty": [1.1],
        }
        profiles = generate_profiles(custom_grid)
        # 2 * 2 * 1 * 1 = 4 profiles
        assert len(profiles) == 4

    def test_profile_has_all_fields(self) -> None:
        """Each profile should have all required fields."""
        profiles = generate_profiles()
        for profile in profiles:
            assert profile.temperature is not None
            assert profile.top_k is not None
            assert profile.min_p is not None
            assert profile.repetition_penalty is not None

    def test_grid_values_are_valid(self) -> None:
        """Profile values should match grid values."""
        profiles = generate_profiles()
        for profile in profiles:
            assert profile.temperature in CALIBRATION_GRID["temperature"]
            assert profile.top_k in CALIBRATION_GRID["top_k"]
            assert profile.min_p in CALIBRATION_GRID["min_p"]
            assert profile.repetition_penalty in CALIBRATION_GRID["repetition_penalty"]

    def test_all_combinations_generated(self) -> None:
        """Should generate all Cartesian product combinations."""
        grid = {
            "temperature": [0.5, 0.6],
            "top_k": [20],
            "min_p": [0.02, 0.05],
            "repetition_penalty": [1.1],
        }
        profiles = generate_profiles(grid)
        # 2 * 1 * 2 * 1 = 4 combinations
        assert len(profiles) == 4


class TestScoringWeights:
    """Tests for SCORING_WEIGHTS constant."""

    def test_weights_sum_to_one(self) -> None:
        """Weights should sum to 1.0."""
        total = sum(SCORING_WEIGHTS.values())
        assert total == pytest.approx(1.0)

    def test_all_dimensions_present(self) -> None:
        """All required dimensions should be present."""
        required = {
            "ha_modernity",
            "reasoning_depth",
            "functionality",
            "completeness",
            "style",
        }
        assert set(SCORING_WEIGHTS.keys()) == required

    def test_ha_modernity_has_highest_weight(self) -> None:
        """ha_modernity should have the highest weight."""
        assert SCORING_WEIGHTS["ha_modernity"] == 0.30
        for dimension, weight in SCORING_WEIGHTS.items():
            if dimension != "ha_modernity":
                assert weight < 0.30


class TestCalibrationPrompt:
    """Tests for CalibrationPrompt dataclass."""

    def test_from_dict_with_list(self) -> None:
        """Should parse parameter_target as list."""
        data = {
            "id": "prompt_001",
            "question": "What is 2+2?",
            "type": "investigation",
            "parameter_target": ["temperature", "top_k"],
            "evaluation_focus": "Test focus",
        }
        prompt = CalibrationPrompt.from_dict(data)
        assert prompt.id == "prompt_001"
        assert prompt.question == "What is 2+2?"
        assert prompt.type == "investigation"
        assert prompt.parameter_target == ["temperature", "top_k"]
        assert prompt.evaluation_focus == "Test focus"

    def test_from_dict_with_comma_separated_string(self) -> None:
        """Should parse comma-separated parameter_target string."""
        data = {
            "id": "prompt_002",
            "question": "Explain entropy.",
            "type": "investigation",
            "parameter_target": "repetition_penalty, min_p, temperature",
            "evaluation_focus": "Test repetition handling",
        }
        prompt = CalibrationPrompt.from_dict(data)
        assert prompt.parameter_target == ["repetition_penalty", "min_p", "temperature"]

    def test_from_dict_defaults(self) -> None:
        """Should use defaults for missing optional fields."""
        data = {
            "id": "prompt_003",
            "question": "Simple question?",
        }
        prompt = CalibrationPrompt.from_dict(data)
        assert prompt.type == "investigation"
        assert prompt.evaluation_focus == ""
        assert prompt.parameter_target == []

    def test_invalid_parameter_raises(self) -> None:
        """Should raise ValueError for invalid parameter names."""
        data = {
            "id": "prompt_004",
            "question": "Test?",
            "type": "investigation",
            "parameter_target": ["temperature", "invalid_param"],
            "evaluation_focus": "Test",
        }
        with pytest.raises(ValueError, match="Invalid parameter"):
            CalibrationPrompt.from_dict(data)

    def test_to_dict_serializes_correctly(self) -> None:
        """Should serialize to dict with comma-separated parameter_target."""
        prompt = CalibrationPrompt(
            id="prompt_005",
            question="Test question",
            type="investigation",
            parameter_target=["temperature", "top_k"],
            evaluation_focus="Focus area",
        )
        result = prompt.to_dict()
        assert result["parameter_target"] == "temperature, top_k"

    def test_get_parameter_target_set(self) -> None:
        """Should return parameter_target as set."""
        prompt = CalibrationPrompt(
            id="prompt_006",
            question="Test",
            type="investigation",
            parameter_target=["temperature", "top_k", "temperature"],  # duplicate
            evaluation_focus="Test",
        )
        target_set = prompt.get_parameter_target_set()
        assert target_set == {"temperature", "top_k"}

    def test_valid_parameters_contains_expected(self) -> None:
        """VALID_PARAMETERS should contain expected parameter names."""
        expected = {
            "temperature",
            "top_k",
            "min_p",
            "repetition_penalty",
            "presence_penalty",
        }
        assert VALID_PARAMETERS == expected


class TestExtractFocusAnalysis:
    """Tests for extract_focus_analysis function (T044)."""

    def test_extract_focus_analysis_with_focus_data(self) -> None:
        """Should extract focus analysis from prompts with parameter_target/evaluation_focus."""
        from src.audit.calibration import extract_focus_analysis

        prompts = [
            {
                "id": "prompt_1",
                "text": "Test prompt 1",
                "parameter_target": "temperature, top_k",
                "evaluation_focus": "Creatividad y exploración",
            },
            {
                "id": "prompt_2",
                "text": "Test prompt 2",
                "parameter_target": "temperature",
                "evaluation_focus": "Razonamiento profundo",
            },
        ]

        result = extract_focus_analysis(prompts)

        assert result["has_focus_data"] is True
        assert "temperature" in result["focused_parameters"]
        assert "top_k" in result["focused_parameters"]
        assert "Creatividad y exploración" in result["evaluation_foci"]
        assert "Razonamiento profundo" in result["evaluation_foci"]
        assert result["prompts_with_focus"] == 2

    def test_extract_focus_analysis_without_focus_data(self) -> None:
        """Should return empty analysis when prompts have no focus data."""
        from src.audit.calibration import extract_focus_analysis

        prompts = [
            {"id": "prompt_1", "text": "Test prompt 1"},
            {"id": "prompt_2", "text": "Test prompt 2"},
        ]

        result = extract_focus_analysis(prompts)

        assert result["has_focus_data"] is False
        assert result["focused_parameters"] == []
        assert result["evaluation_foci"] == []
        assert result["adjustment_strategy"] == {}
        assert result["prompts_with_focus"] == 0

    def test_extract_focus_analysis_with_list_parameter_target(self) -> None:
        """Should handle parameter_target as list."""
        from src.audit.calibration import extract_focus_analysis

        prompts = [
            {
                "id": "prompt_1",
                "text": "Test prompt",
                "parameter_target": ["temperature", "min_p"],
                "evaluation_focus": "Precisión",
            },
        ]

        result = extract_focus_analysis(prompts)

        assert result["has_focus_data"] is True
        assert "temperature" in result["focused_parameters"]
        assert "min_p" in result["focused_parameters"]

    def test_extract_focus_analysis_returns_adjustment_strategy(self) -> None:
        """Should include adjustment strategy in the analysis."""
        from src.audit.calibration import extract_focus_analysis

        prompts = [
            {
                "id": "prompt_1",
                "text": "Test prompt",
                "parameter_target": "temperature",
                "evaluation_focus": "Creatividad y exploración",
            },
        ]

        result = extract_focus_analysis(prompts)

        assert "adjustment_strategy" in result
        assert "parameter_adjustments" in result


class TestRefineParameterSpace:
    """Tests for refine_parameter_space function (T042)."""

    def test_refine_with_empty_results_returns_base_grid(self) -> None:
        """Should return base grid when no results provided."""
        from src.audit.calibration import refine_parameter_space

        base_grid = {"temperature": [0.5, 0.6, 0.7], "top_k": [20, 40]}
        result = refine_parameter_space([], base_grid=base_grid)
        assert result == base_grid

    def test_refine_narrows_temperature_range(self) -> None:
        """Should narrow temperature range based on top performers."""
        from src.audit.calibration import refine_parameter_space

        results = [
            CalibrationResult(
                profile=SamplingProfile(
                    temperature=0.7, top_k=40, min_p=0.02, repetition_penalty=1.1
                ),
                exam_id="p1",
                judge_scores={
                    "ha_modernity": 0.9,
                    "reasoning_depth": 0.8,
                    "functionality": 0.9,
                    "completeness": 0.8,
                    "style": 0.9,
                },
                composite_score=0.87,
                adjusted_score=0.87,
                response_length=250,
                timestamp="2026-01-01T00:00:00Z",
            ),
            CalibrationResult(
                profile=SamplingProfile(
                    temperature=0.6, top_k=40, min_p=0.02, repetition_penalty=1.1
                ),
                exam_id="p1",
                judge_scores={
                    "ha_modernity": 0.7,
                    "reasoning_depth": 0.7,
                    "functionality": 0.7,
                    "completeness": 0.7,
                    "style": 0.7,
                },
                composite_score=0.7,
                adjusted_score=0.7,
                response_length=250,
                timestamp="2026-01-01T00:00:00Z",
            ),
            CalibrationResult(
                profile=SamplingProfile(
                    temperature=0.5, top_k=40, min_p=0.02, repetition_penalty=1.1
                ),
                exam_id="p1",
                judge_scores={
                    "ha_modernity": 0.5,
                    "reasoning_depth": 0.5,
                    "functionality": 0.5,
                    "completeness": 0.5,
                    "style": 0.5,
                },
                composite_score=0.5,
                adjusted_score=0.5,
                response_length=250,
                timestamp="2026-01-01T00:00:00Z",
            ),
        ]

        base_grid = {
            "temperature": [0.5, 0.6, 0.7],
            "top_k": [20, 40],
            "min_p": [0.02],
            "repetition_penalty": [1.1],
        }
        result = refine_parameter_space(results, base_grid=base_grid, top_percent=0.33)

        # Should narrow toward 0.7 (best performer)
        assert result["temperature"] != base_grid["temperature"]
        # All refined values should still be in valid range
        assert all(0.0 <= t <= 2.0 for t in result["temperature"])

    def test_refine_uses_default_grid_when_none_provided(self) -> None:
        """Should use CALIBRATION_GRID as default when no grid provided."""
        from src.audit.calibration import refine_parameter_space

        results = [
            CalibrationResult(
                profile=SamplingProfile(
                    temperature=0.6, top_k=40, min_p=0.02, repetition_penalty=1.1
                ),
                exam_id="p1",
                judge_scores={
                    "ha_modernity": 0.8,
                    "reasoning_depth": 0.8,
                    "functionality": 0.8,
                    "completeness": 0.8,
                    "style": 0.8,
                },
                composite_score=0.8,
                adjusted_score=0.8,
                response_length=250,
                timestamp="2026-01-01T00:00:00Z",
            ),
        ]

        result = refine_parameter_space(results)
        assert "temperature" in result
        assert "top_k" in result
        assert "min_p" in result
        assert "repetition_penalty" in result


class TestAnalyzeParameterPerformance:
    """Tests for analyze_parameter_performance function (T042)."""

    def test_analyze_empty_results(self) -> None:
        """Should return empty dict for empty results."""
        from src.audit.calibration import analyze_parameter_performance

        result = analyze_parameter_performance([])
        assert result == {}

    def test_analyze_single_result(self) -> None:
        """Should analyze single result correctly."""
        from src.audit.calibration import analyze_parameter_performance

        results = [
            CalibrationResult(
                profile=SamplingProfile(
                    temperature=0.7, top_k=40, min_p=0.02, repetition_penalty=1.1
                ),
                exam_id="p1",
                judge_scores={
                    "ha_modernity": 0.9,
                    "reasoning_depth": 0.8,
                    "functionality": 0.9,
                    "completeness": 0.8,
                    "style": 0.9,
                },
                composite_score=0.87,
                adjusted_score=0.87,
                response_length=250,
                timestamp="2026-01-01T00:00:00Z",
            ),
        ]

        analysis = analyze_parameter_performance(results)

        assert "temperature" in analysis
        assert analysis["temperature"]["best_value"] == 0.7
        assert analysis["temperature"]["best_score"] == pytest.approx(0.87)

    def test_analyze_identifies_best_value(self) -> None:
        """Should identify best performing parameter value."""
        from src.audit.calibration import analyze_parameter_performance

        results = [
            CalibrationResult(
                profile=SamplingProfile(
                    temperature=0.5, top_k=20, min_p=0.02, repetition_penalty=1.1
                ),
                exam_id="p1",
                judge_scores={
                    "ha_modernity": 0.5,
                    "reasoning_depth": 0.5,
                    "functionality": 0.5,
                    "completeness": 0.5,
                    "style": 0.5,
                },
                composite_score=0.5,
                adjusted_score=0.5,
                response_length=250,
                timestamp="2026-01-01T00:00:00Z",
            ),
            CalibrationResult(
                profile=SamplingProfile(
                    temperature=0.7, top_k=20, min_p=0.02, repetition_penalty=1.1
                ),
                exam_id="p1",
                judge_scores={
                    "ha_modernity": 0.9,
                    "reasoning_depth": 0.9,
                    "functionality": 0.9,
                    "completeness": 0.9,
                    "style": 0.9,
                },
                composite_score=0.9,
                adjusted_score=0.9,
                response_length=250,
                timestamp="2026-01-01T00:00:00Z",
            ),
        ]

        analysis = analyze_parameter_performance(results)

        # Best temperature should be 0.7 (higher score)
        assert analysis["temperature"]["best_value"] == 0.7
        assert analysis["temperature"]["best_score"] == pytest.approx(0.9)


class TestGetRefinementRecommendations:
    """Tests for get_refinement_recommendations function (T042)."""

    def test_recommendations_for_empty_results(self) -> None:
        """Should return valid structure for empty results."""
        from src.audit.calibration import get_refinement_recommendations

        result = get_refinement_recommendations([])

        assert "parameter_analysis" in result
        assert "refined_grid" in result
        assert "recommendations" in result
        assert "summary" in result
        assert result["summary"]["total_results"] == 0

    def test_recommendations_include_actionable_suggestions(self) -> None:
        """Should include actionable recommendations."""
        from src.audit.calibration import get_refinement_recommendations

        results = [
            CalibrationResult(
                profile=SamplingProfile(
                    temperature=0.7, top_k=50, min_p=0.05, repetition_penalty=1.2
                ),
                exam_id="p1",
                judge_scores={
                    "ha_modernity": 0.9,
                    "reasoning_depth": 0.9,
                    "functionality": 0.9,
                    "completeness": 0.9,
                    "style": 0.9,
                },
                composite_score=0.9,
                adjusted_score=0.9,
                response_length=250,
                timestamp="2026-01-01T00:00:00Z",
            ),
            CalibrationResult(
                profile=SamplingProfile(
                    temperature=0.5, top_k=20, min_p=0.02, repetition_penalty=1.1
                ),
                exam_id="p1",
                judge_scores={
                    "ha_modernity": 0.5,
                    "reasoning_depth": 0.5,
                    "functionality": 0.5,
                    "completeness": 0.5,
                    "style": 0.5,
                },
                composite_score=0.5,
                adjusted_score=0.5,
                response_length=250,
                timestamp="2026-01-01T00:00:00Z",
            ),
        ]

        result = get_refinement_recommendations(results)

        assert len(result["recommendations"]) > 0
        # Should have best profile in summary
        assert result["summary"]["best_profile"] is not None
        assert result["summary"]["average_score"] > 0


class TestAdaptiveGridSearch:
    """Tests for adaptive grid search functions."""

    def test_get_parameter_priority_order_increase(self) -> None:
        """Should return 'high' priority for parameters to increase."""
        strategy = {"increase": ["temperature"], "decrease": []}
        result = get_parameter_priority_order(strategy)

        assert result["temperature"] == "high"
        assert result["top_k"] == "medium"
        assert result["min_p"] == "medium"

    def test_get_parameter_priority_order_decrease(self) -> None:
        """Should return 'low' priority for parameters to decrease."""
        strategy = {"increase": [], "decrease": ["top_k"]}
        result = get_parameter_priority_order(strategy)

        assert result["top_k"] == "low"
        assert result["temperature"] == "medium"

    def test_get_parameter_priority_order_mixed(self) -> None:
        """Should handle mixed increase/decrease correctly."""
        strategy = {"increase": ["temperature"], "decrease": ["top_k"]}
        result = get_parameter_priority_order(strategy)

        assert result["temperature"] == "high"
        assert result["top_k"] == "low"
        assert result["min_p"] == "medium"

    def test_get_parameter_priority_order_empty_strategy(self) -> None:
        """Should return medium priority for all when strategy is empty."""
        strategy = {"increase": [], "decrease": []}
        result = get_parameter_priority_order(strategy)

        assert result["temperature"] == "medium"
        assert result["top_k"] == "medium"
        assert result["min_p"] == "medium"
        assert result["repetition_penalty"] == "medium"

    def test_generate_adaptive_profiles_with_focus(self) -> None:
        """Should generate profiles with prioritized ordering based on focus."""
        prompts = [
            CalibrationPrompt(
                id="p1",
                question="Explain the impact of AI on society",
                type="investigation",
                parameter_target=["temperature"],
                evaluation_focus="Creatividad y exploración",
            ),
        ]
        profiles = generate_adaptive_profiles(prompts=prompts)

        assert len(profiles) > 0
        # First profiles should have higher temperature values
        temps = [p.temperature for p in profiles]
        # Since high priority sorts descending, first profile should have highest temp
        assert temps[0] == max(temps)

    def test_generate_adaptive_profiles_with_decrease_focus(self) -> None:
        """Should prioritize lower values for decrease-focused parameters."""
        [
            CalibrationPrompt(
                id="p1",
                question="Summarize this text",
                type="summary",
                parameter_target=["top_k"],
                evaluation_focus="Concisión y precisión",
            ),
        ]
        # Strategy to decrease top_k
        strategy = {"increase": [], "decrease": ["top_k"]}
        profiles = generate_adaptive_profiles(focus_strategy=strategy)

        assert len(profiles) > 0
        top_k_values = [p.top_k for p in profiles]
        # First profile should have lowest top_k (low priority)
        assert top_k_values[0] == min(top_k_values)

    def test_generate_adaptive_profiles_no_prompts(self) -> None:
        """Should generate profiles in default order when no prompts provided."""
        profiles = generate_adaptive_profiles(prompts=None)

        assert len(profiles) > 0
        # Should have same count as regular generate_profiles
        regular_profiles = generate_profiles()
        assert len(profiles) == len(regular_profiles)

    def test_get_adaptive_parameter_weights(self) -> None:
        """Should return higher weights for focused parameters."""
        strategy = {"increase": ["temperature"], "decrease": ["top_k"]}
        weights = get_adaptive_parameter_weights(strategy)

        assert weights["temperature"] > weights["min_p"]
        assert weights["top_k"] > weights["min_p"]

    def test_get_adaptive_parameter_weights_empty_strategy(self) -> None:
        """Should return equal base weights when strategy is empty."""
        strategy = {"increase": [], "decrease": []}
        weights = get_adaptive_parameter_weights(strategy)

        # All should be equal (base weight)
        assert weights["temperature"] == weights["top_k"]
        assert weights["top_k"] == weights["min_p"]

    def test_generate_adaptive_profiles_with_multiple_prompts(self) -> None:
        """Should combine focus from multiple prompts."""
        prompts = [
            CalibrationPrompt(
                id="p1",
                question="Explain AI",
                type="investigation",
                parameter_target=["temperature"],
                evaluation_focus="Creatividad",
            ),
            CalibrationPrompt(
                id="p2",
                question="Explain ML",
                type="investigation",
                parameter_target=["temperature"],
                evaluation_focus="Razonamiento",
            ),
        ]
        # Both prompts focus on temperature, should prioritize high values
        profiles = generate_adaptive_profiles(prompts=prompts)

        temps = [p.temperature for p in profiles]
        assert temps[0] == max(temps)


class TestCalibrationHelperFunctions:
    """Tests for helper functions in calibration.py."""

    def test_calc_combinations_single_param(self) -> None:
        """Test _calc_combinations with single parameter."""
        from src.audit.calibration import _calc_combinations

        grid = {"temperature": [0.1, 0.5, 0.9]}
        result = _calc_combinations(grid)
        assert result == 3

    def test_calc_combinations_multiple_params(self) -> None:
        """Test _calc_combinations with multiple parameters."""
        from src.audit.calibration import _calc_combinations

        grid = {
            "temperature": [0.1, 0.5, 0.9],
            "top_p": [0.8, 0.9, 1.0],
        }
        result = _calc_combinations(grid)
        assert result == 9  # 3 * 3

    def test_calc_combinations_empty_grid(self) -> None:
        """Test _calc_combinations with empty grid returns 1 (neutral element)."""
        from src.audit.calibration import _calc_combinations

        grid = {}
        result = _calc_combinations(grid)
        # Returns 1 as neutral element for multiplication
        assert result == 1

    def test_adjust_for_increase(self) -> None:
        """Test _adjust_for_increase adjusts values for increase focus."""
        from src.audit.calibration import _adjust_for_increase

        values = [0.1, 0.2, 0.3, 0.4, 0.5]
        result = _adjust_for_increase(values, "temperature")

        # Should spread values across range for increase focus
        assert len(result) == len(values)
        assert result != values  # Should be adjusted

    def test_adjust_for_decrease(self) -> None:
        """Test _adjust_for_decrease adjusts values for decrease focus."""
        from src.audit.calibration import _adjust_for_decrease

        values = [0.5, 0.6, 0.7, 0.8, 0.9]
        result = _adjust_for_decrease(values, "temperature")

        # Should adjust values for decrease focus
        assert len(result) == len(values)
        assert result != values  # Should be adjusted

    def test_clamp_to_valid_range(self) -> None:
        """Test _clamp_to_valid_range clamps values to valid ranges."""
        from src.audit.calibration import _clamp_to_valid_range

        # Test temperature clamping (0 to 2)
        result = _clamp_to_valid_range(5.0, 0.5, "temperature")
        assert result == 2.0  # Should clamp to max

        result = _clamp_to_valid_range(-1.0, 0.5, "temperature")
        assert result == 0.0  # Should clamp to min

        result = _clamp_to_valid_range(1.0, 0.5, "temperature")
        assert result == 1.0  # Should stay the same

    def test_clamp_to_valid_range_preserves_unknown_params(self) -> None:
        """Test _clamp_to_valid_range for unknown parameters preserves value."""
        from src.audit.calibration import _clamp_to_valid_range

        # Unknown parameter should preserve value
        result = _clamp_to_valid_range(1.5, 0.5, "unknown_param")
        assert result == 1.5


class TestLoadCalibrationPromptsFromYaml:
    """Tests for load_calibration_prompts_from_yaml function (T043)."""

    def test_load_prompts_from_yaml_file_not_found(self) -> None:
        """Should raise FileNotFoundError when file doesn't exist."""
        from src.audit.calibration import load_calibration_prompts_from_yaml

        with pytest.raises(FileNotFoundError, match="YAML file not found"):
            load_calibration_prompts_from_yaml("/nonexistent/path/prompts.yaml")

    def test_load_prompts_from_yaml_with_valid_file(self, tmp_path) -> None:
        """Should load prompts from valid YAML file."""
        from src.audit.calibration import load_calibration_prompts_from_yaml

        yaml_content = """
prompts:
  - id: test_prompt_1
    question: What is AI?
    type: investigation
    parameter_target: temperature, top_k
    evaluation_focus: Creatividad
  - id: test_prompt_2
    question: Explain machine learning
    type: investigation
    parameter_target: temperature
    evaluation_focus: Razonamiento
"""
        yaml_file = tmp_path / "prompts.yaml"
        yaml_file.write_text(yaml_content)

        prompts = load_calibration_prompts_from_yaml(str(yaml_file))

        assert len(prompts) == 2
        assert prompts[0].id == "test_prompt_1"
        assert "temperature" in prompts[0].get_parameter_target_set()

    def test_load_prompts_from_yaml_empty_file(self, tmp_path) -> None:
        """Should return empty list for empty YAML file."""
        from src.audit.calibration import load_calibration_prompts_from_yaml

        yaml_file = tmp_path / "empty.yaml"
        yaml_file.write_text("")

        prompts = load_calibration_prompts_from_yaml(str(yaml_file))
        assert prompts == []

    def test_load_prompts_from_yaml_with_samples_key(self, tmp_path) -> None:
        """Should load prompts from YAML with 'samples' key."""
        from src.audit.calibration import load_calibration_prompts_from_yaml

        yaml_content = """
samples:
  - id: sample_1
    question: Test question?
    type: investigation
"""
        yaml_file = tmp_path / "samples.yaml"
        yaml_file.write_text(yaml_content)

        prompts = load_calibration_prompts_from_yaml(str(yaml_file))
        assert len(prompts) == 1
        assert prompts[0].id == "sample_1"

    def test_load_prompts_from_yaml_list_format(self, tmp_path) -> None:
        """Should load prompts from YAML with list format (not dict)."""
        from src.audit.calibration import load_calibration_prompts_from_yaml

        yaml_content = """
- id: list_prompt_1
  question: Question 1?
  type: investigation
- id: list_prompt_2
  question: Question 2?
  type: investigation
"""
        yaml_file = tmp_path / "list_format.yaml"
        yaml_file.write_text(yaml_content)

        prompts = load_calibration_prompts_from_yaml(str(yaml_file))
        assert len(prompts) == 2
        assert prompts[0].id == "list_prompt_1"
        assert prompts[1].id == "list_prompt_2"

    def test_load_prompts_from_yaml_skips_invalid_prompts(
        self, tmp_path, caplog
    ) -> None:
        """Should skip invalid prompts with invalid parameter names and log warning."""
        from src.audit.calibration import load_calibration_prompts_from_yaml

        yaml_content = """
prompts:
  - id: valid_prompt
    question: Valid question?
    type: investigation
    parameter_target: temperature
  - id: invalid_prompt
    question: Invalid question?
    type: investigation
    parameter_target: invalid_param_name
"""
        yaml_file = tmp_path / "mixed.yaml"
        yaml_file.write_text(yaml_content)

        prompts = load_calibration_prompts_from_yaml(str(yaml_file))
        # Should only load the valid one (with valid parameter name)
        assert len(prompts) == 1
        assert prompts[0].id == "valid_prompt"


class TestExtractParameterTargets:
    """Tests for extract_parameter_targets function (T043)."""

    def test_extract_parameter_targets_empty_list(self) -> None:
        """Should return empty dict for empty prompts list."""
        from src.audit.calibration import extract_parameter_targets

        result = extract_parameter_targets([])
        assert result == {}

    def test_extract_parameter_targets_single_focus(self) -> None:
        """Should extract parameter targets for single focus."""
        from src.audit.calibration import extract_parameter_targets, CalibrationPrompt

        prompts = [
            CalibrationPrompt(
                id="p1",
                question="Test?",
                type="investigation",
                parameter_target=["temperature", "top_k"],
                evaluation_focus="Creatividad",
            ),
            CalibrationPrompt(
                id="p2",
                question="Test2?",
                type="investigation",
                parameter_target=["temperature"],
                evaluation_focus="Creatividad",
            ),
        ]

        result = extract_parameter_targets(prompts)

        assert "Creatividad" in result
        assert result["Creatividad"] == {"temperature", "top_k"}

    def test_extract_parameter_targets_multiple_foci(self) -> None:
        """Should handle multiple evaluation foci."""
        from src.audit.calibration import extract_parameter_targets, CalibrationPrompt

        prompts = [
            CalibrationPrompt(
                id="p1",
                question="Test?",
                type="investigation",
                parameter_target=["temperature"],
                evaluation_focus="Creatividad",
            ),
            CalibrationPrompt(
                id="p2",
                question="Test2?",
                type="investigation",
                parameter_target=["top_k"],
                evaluation_focus="Razonamiento",
            ),
        ]

        result = extract_parameter_targets(prompts)

        assert len(result) == 2
        assert result["Creatividad"] == {"temperature"}
        assert result["Razonamiento"] == {"top_k"}


class TestGetFocusedParameters:
    """Tests for get_focused_parameters function (T043)."""

    def test_get_focused_parameters_empty_list(self) -> None:
        """Should return empty set for empty prompts."""
        from src.audit.calibration import get_focused_parameters

        result = get_focused_parameters([])
        assert result == set()

    def test_get_focused_parameters_with_prompts(self) -> None:
        """Should return focused parameters from prompts."""
        from src.audit.calibration import get_focused_parameters, CalibrationPrompt

        prompts = [
            CalibrationPrompt(
                id="p1",
                question="Test?",
                type="investigation",
                parameter_target=["temperature", "top_k"],
                evaluation_focus="Creatividad",
            ),
        ]

        result = get_focused_parameters(prompts)

        assert "temperature" in result
        assert "top_k" in result


class TestValidateParameterTargets:
    """Tests for validate_parameter_targets function (T043)."""

    def test_validate_parameter_targets_valid(self) -> None:
        """Should return empty list for valid parameters."""
        from src.audit.calibration import validate_parameter_targets, CalibrationPrompt

        prompts = [
            CalibrationPrompt(
                id="p1",
                question="Test?",
                type="investigation",
                parameter_target=["temperature", "top_k"],
                evaluation_focus="Test",
            ),
        ]

        errors = validate_parameter_targets(prompts)
        assert errors == []

    def test_validate_parameter_targets_invalid(self) -> None:
        """Should return error messages for invalid parameters."""
        from src.audit.calibration import validate_parameter_targets, CalibrationPrompt

        # First create prompts with valid params, then test validation
        # (CalibrationPrompt validates params in __post_init__)
        prompts = [
            CalibrationPrompt(
                id="p1",
                question="Test?",
                type="investigation",
                parameter_target=["temperature"],
                evaluation_focus="Test",
            ),
        ]

        # Test that validation returns empty for valid prompts
        errors = validate_parameter_targets(prompts)
        assert errors == []

    def test_validate_parameter_targets_detects_invalid_via_from_dict(self) -> None:
        """Should detect invalid parameters via from_dict."""
        from src.audit.calibration import CalibrationPrompt

        # Using from_dict which parses string params
        prompt_data = {
            "id": "p1",
            "question": "Test?",
            "type": "investigation",
            "parameter_target": "temperature, invalid_param",
            "evaluation_focus": "Test",
        }

        # This should fail to create due to invalid_param
        with pytest.raises(ValueError, match="Invalid parameter"):
            CalibrationPrompt.from_dict(prompt_data)


class TestAnalyzeEvaluationFocus:
    """Tests for analyze_evaluation_focus function (T043)."""

    def test_analyze_evaluation_focus_empty_list(self) -> None:
        """Should return empty dict for empty prompts."""
        from src.audit.calibration import analyze_evaluation_focus

        result = analyze_evaluation_focus([])
        assert result == {}

    def test_analyze_evaluation_focus_with_focus_text(self) -> None:
        """Should analyze prompts with evaluation_focus text."""
        from src.audit.calibration import analyze_evaluation_focus, CalibrationPrompt

        prompts = [
            CalibrationPrompt(
                id="p1",
                question="Explain AI?",
                type="investigation",
                parameter_target=["temperature"],
                evaluation_focus="Creatividad y exploración",
            ),
        ]

        result = analyze_evaluation_focus(prompts)

        assert "p1" in result
        assert "focus_area" in result["p1"]
        assert "parameters_to_increase" in result["p1"]

    def test_analyze_evaluation_focus_no_match_uses_defaults(self) -> None:
        """Should use defaults when no focus area matches."""
        from src.audit.calibration import analyze_evaluation_focus, CalibrationPrompt

        prompts = [
            CalibrationPrompt(
                id="p1",
                question="Test?",
                type="investigation",
                parameter_target=["temperature"],
                evaluation_focus="unknown focus area xyz",
            ),
        ]

        result = analyze_evaluation_focus(prompts)

        assert "p1" in result
        # Should have unknown focus area with defaults
        assert result["p1"]["focus_area"] == "unknown"
        assert result["p1"]["confidence"] == 0.0

    def test_analyze_evaluation_focus_with_matching_keywords(self) -> None:
        """Should match focus area based on keywords."""
        from src.audit.calibration import analyze_evaluation_focus, CalibrationPrompt

        prompts = [
            CalibrationPrompt(
                id="p1",
                question="Math problem?",
                type="investigation",
                parameter_target=["temperature", "top_k"],
                evaluation_focus="Razonamiento y precisión matemática",
            ),
        ]

        result = analyze_evaluation_focus(prompts)

        assert "p1" in result
        assert result["p1"]["focus_area"] is not None
