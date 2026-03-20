#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for src/audit/calibration_schema.py validation functions."""

from __future__ import annotations

import pytest

from src.audit.calibration_schema import (
    SamplingProfile,
    CalibrationPrompt,
    CalibrationResult,
)


class TestSamplingProfileValidation:
    """Tests for SamplingProfile validation."""

    def test_temperature_below_range(self) -> None:
        """Test temperature below valid range raises ValueError."""
        with pytest.raises(ValueError, match="temperature must be in range"):
            SamplingProfile(temperature=-0.1, top_k=50, min_p=0.1, repetition_penalty=1.1)

    def test_temperature_above_range(self) -> None:
        """Test temperature above valid range raises ValueError."""
        with pytest.raises(ValueError, match="temperature must be in range"):
            SamplingProfile(temperature=2.5, top_k=50, min_p=0.1, repetition_penalty=1.1)

    def test_top_k_below_range(self) -> None:
        """Test top_k below valid range raises ValueError."""
        with pytest.raises(ValueError, match="top_k must be in range"):
            SamplingProfile(temperature=1.0, top_k=0, min_p=0.1, repetition_penalty=1.1)

    def test_top_k_above_range(self) -> None:
        """Test top_k above valid range raises ValueError."""
        with pytest.raises(ValueError, match="top_k must be in range"):
            SamplingProfile(temperature=1.0, top_k=300, min_p=0.1, repetition_penalty=1.1)

    def test_min_p_below_range(self) -> None:
        """Test min_p below valid range raises ValueError."""
        with pytest.raises(ValueError, match="min_p must be in range"):
            SamplingProfile(temperature=1.0, top_k=50, min_p=-0.1, repetition_penalty=1.1)

    def test_min_p_above_range(self) -> None:
        """Test min_p above valid range raises ValueError."""
        with pytest.raises(ValueError, match="min_p must be in range"):
            SamplingProfile(temperature=1.0, top_k=50, min_p=1.5, repetition_penalty=1.1)

    def test_repetition_penalty_below_range(self) -> None:
        """Test repetition_penalty below valid range raises ValueError."""
        with pytest.raises(ValueError, match="repetition_penalty must be in range"):
            SamplingProfile(temperature=1.0, top_k=50, min_p=0.1, repetition_penalty=0.9)

    def test_repetition_penalty_above_range(self) -> None:
        """Test repetition_penalty above valid range raises ValueError."""
        with pytest.raises(ValueError, match="repetition_penalty must be in range"):
            SamplingProfile(temperature=1.0, top_k=50, min_p=0.1, repetition_penalty=2.5)

    def test_presence_penalty_below_range(self) -> None:
        """Test presence_penalty below valid range raises ValueError."""
        with pytest.raises(ValueError, match="presence_penalty must be in range"):
            SamplingProfile(
                temperature=1.0, top_k=50, min_p=0.1, repetition_penalty=1.1,
                presence_penalty=-3.0
            )

    def test_presence_penalty_above_range(self) -> None:
        """Test presence_penalty above valid range raises ValueError."""
        with pytest.raises(ValueError, match="presence_penalty must be in range"):
            SamplingProfile(
                temperature=1.0, top_k=50, min_p=0.1, repetition_penalty=1.1,
                presence_penalty=3.0
            )

    def test_valid_profile(self) -> None:
        """Test valid profile creation."""
        profile = SamplingProfile(
            temperature=1.0,
            top_k=50,
            min_p=0.1,
            repetition_penalty=1.1,
            presence_penalty=0.0,
        )
        assert profile.temperature == 1.0
        assert profile.top_k == 50


class TestCalibrationPromptValidation:
    """Tests for CalibrationPrompt validation."""

    def test_empty_target_parameters(self) -> None:
        """Test empty target_parameters list is valid."""
        prompt = CalibrationPrompt(
            id="test",
            question="test question",
            type="test",
            parameter_target=[],
            evaluation_focus="reasoning",
        )
        assert prompt.parameter_target == []

    def test_invalid_target_parameter(self) -> None:
        """Test invalid target parameter raises ValueError."""
        with pytest.raises(ValueError, match="Invalid parameter"):
            CalibrationPrompt(
                id="test",
                question="test question",
                type="test",
                parameter_target=["invalid_param"],
                evaluation_focus="reasoning",
            )

    def test_valid_prompt(self) -> None:
        """Test valid prompt creation."""
        prompt = CalibrationPrompt(
            id="test",
            question="test question",
            type="test",
            parameter_target=["temperature", "top_k"],
            evaluation_focus="reasoning",
        )
        assert prompt.parameter_target == ["temperature", "top_k"]


class TestCalibrationResultValidation:
    """Tests for CalibrationResult validation."""

    def test_valid_result(self) -> None:
        """Test valid result creation."""
        profile = SamplingProfile(
            temperature=1.0,
            top_k=50,
            min_p=0.1,
            repetition_penalty=1.1,
        )
        result = CalibrationResult(
            profile=profile,
            exam_id="test",
            judge_scores={"ha_modernity": 0.8},
            composite_score=0.8,
            adjusted_score=0.8,
            response_length=100,
            timestamp="2026-01-01T00:00:00",
            response_text="test response",
        )
        assert result.composite_score == 0.8

    def test_to_dict(self) -> None:
        """Test serialization to dict."""
        profile = SamplingProfile(
            temperature=1.0,
            top_k=50,
            min_p=0.1,
            repetition_penalty=1.1,
        )
        result = CalibrationResult(
            profile=profile,
            exam_id="test",
            judge_scores={"ha_modernity": 0.8},
            composite_score=0.8,
            adjusted_score=0.8,
            response_length=100,
            timestamp="2026-01-01T00:00:00",
            response_text="test response",
        )
        d = result.to_dict()
        assert "exam_id" in d
        assert d["exam_id"] == "test"
