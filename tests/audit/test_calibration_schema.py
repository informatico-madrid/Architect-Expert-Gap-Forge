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
    CalibrationReport,
    CalibrationCheckpoint,
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

    def test_from_dict(self) -> None:
        """Test deserialization from dict."""
        data = {
            "profile": {
                "temperature": 1.0,
                "top_k": 50,
                "min_p": 0.1,
                "repetition_penalty": 1.1,
                "presence_penalty": 0.0,
            },
            "exam_id": "test123",
            "judge_scores": {"ha_modernity": 0.8},
            "composite_score": 0.75,
            "adjusted_score": 0.7,
            "response_length": 150,
            "timestamp": "2026-01-01T12:00:00",
            "response_text": "test response text",
        }
        result = CalibrationResult.from_dict(data)
        assert result.exam_id == "test123"
        assert result.composite_score == 0.75
        assert result.profile.temperature == 1.0


class TestSamplingProfileFromDict:
    """Tests for SamplingProfile.from_dict."""

    def test_from_dict_basic(self) -> None:
        """Test creating profile from dict."""
        data = {
            "temperature": 0.8,
            "top_k": 40,
            "min_p": 0.15,
            "repetition_penalty": 1.2,
        }
        profile = SamplingProfile.from_dict(data)
        assert profile.temperature == 0.8
        assert profile.top_k == 40
        assert profile.min_p == 0.15
        assert profile.repetition_penalty == 1.2

    def test_from_dict_with_presence_penalty(self) -> None:
        """Test creating profile from dict with presence_penalty."""
        data = {
            "temperature": 0.9,
            "top_k": 60,
            "min_p": 0.2,
            "repetition_penalty": 1.0,
            "presence_penalty": 0.5,
        }
        profile = SamplingProfile.from_dict(data)
        assert profile.presence_penalty == 0.5

    def test_str_representation(self) -> None:
        """Test string representation of profile."""
        profile = SamplingProfile(
            temperature=1.0,
            top_k=50,
            min_p=0.1,
            repetition_penalty=1.1,
        )
        str_repr = str(profile)
        assert "t=" in str_repr
        assert "k=" in str_repr


class TestCalibrationReportToFromDict:
    """Tests for CalibrationReport to_dict and from_dict."""

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
        )
        report = CalibrationReport(
            timestamp="2026-01-01T00:00:00",
            total_iterations=10,
            best_profile=profile,
            best_score=0.85,
            all_results=[result],
            prompt_count=5,
            focus_analysis={"focus1": "strategy1"},
        )
        d = report.to_dict()
        assert d["timestamp"] == "2026-01-01T00:00:00"
        assert d["total_iterations"] == 10
        assert d["best_score"] == 0.85
        assert d["prompt_count"] == 5

    def test_from_dict(self) -> None:
        """Test deserialization from dict."""
        profile_dict = {
            "temperature": 1.0,
            "top_k": 50,
            "min_p": 0.1,
            "repetition_penalty": 1.1,
        }
        result_dict = {
            "profile": profile_dict,
            "exam_id": "test",
            "judge_scores": {"ha_modernity": 0.8},
            "composite_score": 0.8,
            "adjusted_score": 0.8,
            "response_length": 100,
            "timestamp": "2026-01-01T00:00:00",
            "response_text": "test",
        }
        data = {
            "timestamp": "2026-01-01T00:00:00",
            "total_iterations": 10,
            "best_profile": profile_dict,
            "best_score": 0.85,
            "all_results": [result_dict],
            "prompt_count": 5,
            "focus_analysis": {},
        }
        report = CalibrationReport.from_dict(data)
        assert report.total_iterations == 10
        assert report.best_score == 0.85
        assert len(report.all_results) == 1


class TestCalibrationCheckpointToFromDict:
    """Tests for CalibrationCheckpoint to_dict, from_dict, and progress_percentage."""

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
        )
        checkpoint = CalibrationCheckpoint(
            timestamp="2026-01-01T00:00:00",
            current_prompt_idx=1,
            current_profile_idx=2,
            completed_profiles=[0, 1],
            all_results=[result],
            total_profiles=10,
            total_prompts=5,
            discarded_params={"temperature": [0.1]},
        )
        d = checkpoint.to_dict()
        assert d["current_prompt_idx"] == 1
        assert d["current_profile_idx"] == 2
        assert len(d["completed_profiles"]) == 2

    def test_from_dict(self) -> None:
        """Test deserialization from dict."""
        profile_dict = {
            "temperature": 1.0,
            "top_k": 50,
            "min_p": 0.1,
            "repetition_penalty": 1.1,
        }
        result_dict = {
            "profile": profile_dict,
            "exam_id": "test",
            "judge_scores": {"ha_modernity": 0.8},
            "composite_score": 0.8,
            "adjusted_score": 0.8,
            "response_length": 100,
            "timestamp": "2026-01-01T00:00:00",
            "response_text": "test",
        }
        data = {
            "timestamp": "2026-01-01T00:00:00",
            "current_prompt_idx": 1,
            "current_profile_idx": 2,
            "completed_profiles": [0, 1],
            "all_results": [result_dict],
            "total_profiles": 10,
            "total_prompts": 5,
            "discarded_params": {},
        }
        checkpoint = CalibrationCheckpoint.from_dict(data)
        assert checkpoint.current_prompt_idx == 1
        assert checkpoint.total_profiles == 10
        assert len(checkpoint.completed_profiles) == 2

    def test_progress_percentage_zero_total(self) -> None:
        """Test progress percentage when total is zero."""
        checkpoint = CalibrationCheckpoint(
            timestamp="2026-01-01T00:00:00",
            current_prompt_idx=0,
            current_profile_idx=0,
            completed_profiles=[],
            all_results=[],
            total_profiles=0,
            total_prompts=0,
        )
        assert checkpoint.progress_percentage == 0.0

    def test_progress_percentage_with_progress(self) -> None:
        """Test progress percentage calculation."""
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
        )
        checkpoint = CalibrationCheckpoint(
            timestamp="2026-01-01T00:00:00",
            current_prompt_idx=1,
            current_profile_idx=2,
            completed_profiles=[0, 1],
            all_results=[result],
            total_profiles=10,
            total_prompts=5,
        )
        # 2 completed out of 50 total (5*10)
        assert checkpoint.progress_percentage == pytest.approx(4.0, rel=0.1)
