#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Error case tests for model_evaluator.py — Comprehensive exception handling coverage.

Tests that cover all error paths by mocking failure scenarios:
- Empty LLM responses
- Invalid JSON from LLMs
- Missing/incomplete fields in LLM responses
- Schema mismatches in judge responses
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.audit.gap_generator import generate_gap_analysis
from src.audit.exam_builder import generate_exam_question
from src.audit.judge import llm_judge_score
from src.audit.schema import PromptGenerationError, SampleRecord, ExamRecord
from tests.fixtures import golden_sample, golden_exam


@pytest.mark.integration
class TestGapAnalysisErrorCases:
    """Test error handling in gap analysis generation."""

    def test_empty_gap_analysis_response_raises_error(self, golden_sample: Any) -> None:
        """generate_gap_analysis must raise PromptGenerationError when response is empty."""
        with patch("src.audit.gap_generator._get_inference_router") as mock_router:
            mock_client = MagicMock()
            mock_client.generate_with_retry.return_value = ""  # Empty response
            mock_router.return_value.professor.return_value = mock_client

            with pytest.raises(PromptGenerationError, match="empty gap_analysis"):
                generate_gap_analysis(
                    golden_sample, "master", "changelog", "jinja", validate=False
                )


@pytest.mark.integration
class TestExamGenerationErrorCases:
    """Test error handling in exam question generation."""

    def test_invalid_json_response_raises_error(self, golden_sample: Any) -> None:
        """generate_exam_question must raise PromptGenerationError on invalid JSON."""
        with patch("src.audit.exam_builder._get_inference_router") as mock_router:
            mock_client = MagicMock()
            mock_client.generate_with_retry.return_value = "{ invalid json"  # Invalid
            mock_router.return_value.professor.return_value = mock_client

            with pytest.raises(
                PromptGenerationError, match="Professor failed to generate valid JSON"
            ):
                generate_exam_question(golden_sample, "test-judge", validate=False)

    def test_missing_exam_question_field_raises_error(self, golden_sample: Any) -> None:
        """generate_exam_question must raise when exam_question field is missing."""
        # Return valid JSON but without exam_question
        incomplete_response = {
            "eval_criteria": ["criterion 1"],
            "target_patterns": ["pattern 1"],
        }

        with patch("src.audit.exam_builder._get_inference_router") as mock_router:
            mock_client = MagicMock()
            mock_client.generate_with_retry.return_value = json.dumps(
                incomplete_response
            )
            mock_router.return_value.professor.return_value = mock_client

            with pytest.raises(PromptGenerationError, match="missing required fields"):
                generate_exam_question(golden_sample, "test-judge", validate=False)

    def test_missing_eval_criteria_field_raises_error(self, golden_sample: Any) -> None:
        """generate_exam_question must raise when eval_criteria field is missing."""
        # Return valid JSON but without eval_criteria
        incomplete_response = {
            "exam_question": "What is this code?",
            "target_patterns": ["pattern 1"],
        }

        with patch("src.audit.exam_builder._get_inference_router") as mock_router:
            mock_client = MagicMock()
            mock_client.generate_with_retry.return_value = json.dumps(
                incomplete_response
            )
            mock_router.return_value.professor.return_value = mock_client

            with pytest.raises(PromptGenerationError, match="missing required fields"):
                generate_exam_question(golden_sample, "test-judge", validate=False)


@pytest.mark.integration
class TestJudgeScoringErrorCases:
    """Test error handling in LLM judge scoring."""

    def test_invalid_judge_json_response_raises_error(self, golden_exam: Any) -> None:
        """llm_judge_score must raise on invalid JSON from judge."""
        with patch("src.audit.judge._get_inference_router") as mock_router:
            mock_client = MagicMock()
            mock_client.generate_with_retry.return_value = "{ not valid json"
            mock_router.return_value.professor.return_value = mock_client

            with pytest.raises(PromptGenerationError, match="LLM judge failed"):
                llm_judge_score(
                    golden_exam,
                    "baseline response",
                    "adapter response",
                    "test-judge",
                    validate=False,
                )

    def test_missing_baseline_key_in_judge_response_raises_error(
        self, golden_exam: Any
    ) -> None:
        """llm_judge_score must raise when baseline key is missing from judge response."""
        # Valid JSON but missing 'baseline' key
        incomplete = {
            "adapter": {"ha_modernity": 0.9},
            "reasoning": "judgment text",
        }

        with patch("src.audit.judge._get_inference_router") as mock_router:
            mock_client = MagicMock()
            mock_client.generate_with_retry.return_value = json.dumps(incomplete)
            mock_router.return_value.professor.return_value = mock_client

            with pytest.raises(PromptGenerationError, match="Missing key 'baseline'"):
                llm_judge_score(
                    golden_exam,
                    "baseline response",
                    "adapter response",
                    "test-judge",
                    validate=False,
                )

    def test_missing_adapter_key_in_judge_response_raises_error(
        self, golden_exam: Any
    ) -> None:
        """llm_judge_score must raise when adapter key is missing."""
        # Valid JSON but missing 'adapter' key
        incomplete = {
            "baseline": {"ha_modernity": 0.75},
            "reasoning": "judgment text",
        }

        with patch("src.audit.judge._get_inference_router") as mock_router:
            mock_client = MagicMock()
            mock_client.generate_with_retry.return_value = json.dumps(incomplete)
            mock_router.return_value.professor.return_value = mock_client

            with pytest.raises(PromptGenerationError, match="Missing key 'adapter'"):
                llm_judge_score(
                    golden_exam,
                    "baseline response",
                    "adapter response",
                    "test-judge",
                    validate=False,
                )

    def test_missing_reasoning_key_in_judge_response_raises_error(
        self, golden_exam: Any
    ) -> None:
        """llm_judge_score must raise when reasoning key is missing."""
        # Valid JSON but missing 'reasoning' key
        incomplete = {
            "baseline": {"ha_modernity": 0.75},
            "adapter": {"ha_modernity": 0.9},
        }

        with patch("src.audit.judge._get_inference_router") as mock_router:
            mock_client = MagicMock()
            mock_client.generate_with_retry.return_value = json.dumps(incomplete)
            mock_router.return_value.professor.return_value = mock_client

            with pytest.raises(PromptGenerationError, match="Missing key 'reasoning'"):
                llm_judge_score(
                    golden_exam,
                    "baseline response",
                    "adapter response",
                    "test-judge",
                    validate=False,
                )

    def test_dimension_normalization_handles_missing_dimensions(
        self, golden_exam: Any
    ) -> None:
        """llm_judge_score must gracefully handle missing dimension scores."""
        # Response with only some dimensions (missing others)
        incomplete_dims = {
            "baseline": {"ha_modernity": 0.75},  # Missing other dimensions
            "adapter": {"ha_modernity": 0.9},  # Missing other dimensions
            "reasoning": "judgment text",
        }

        with patch("src.audit.judge._get_inference_router") as mock_router:
            mock_client = MagicMock()
            mock_client.generate_with_retry.return_value = json.dumps(incomplete_dims)
            mock_router.return_value.professor.return_value = mock_client

            # Should NOT raise — missing dimensions are filled with 0.5 default
            result = llm_judge_score(
                golden_exam,
                "baseline response",
                "adapter response",
                "test-judge",
                validate=False,
            )
            assert "baseline" in result
            assert "adapter" in result
            assert result["adapter"]["reasoning_depth"] == 0.5  # Default fill value


@pytest.mark.integration
class TestCmdGenerateGapErrorCases:
    """Test error handling in cmd_sample (gap analysis generation)."""

    def test_cmd_sample_propagates_error_from_generate_gap_analysis(
        self, golden_sample: Any, tmp_path: Path
    ) -> None:
        """cmd_sample must propagate PromptGenerationError from generate_gap_analysis."""
        # Create a sample WITHOUT gap_analysis so cmd_sample tries to generate it
        sample_without_gap = dataclasses.replace(golden_sample, gap_analysis="")

        # Mock generate_gap_analysis to raise PromptGenerationError
        with patch("src.audit.cli.generate_gap_analysis") as mock_gap_gen:
            mock_gap_gen.side_effect = PromptGenerationError(
                "Gap analysis generation failed: mocked error"
            )

            # Create a minimal args namespace
            import argparse

            args = argparse.Namespace(
                audit_dir=str(tmp_path),
                dataset="dummy",
                sample_size=10,
                gap_dir=".",
                enrich=False,
                force=False,
                professor_backend="gemini",
                gemini_model="gemini-2.0-flash",
                judge_model="gemini-2.0-flash",
                api_url="http://localhost:8000",
                retries=1,
                retry_delay=0.1,
                validate=False,
            )

            # Mock load_dataset to avoid file I/O
            with patch("src.audit.cli.load_dataset") as mock_load_ds:
                mock_load_ds.return_value = [
                    {"id": "test", "metadata": {"example_type": "nominal"}}
                ]

                # Mock stratified_sample to return sample without gap_analysis
                with patch("src.audit.cli.stratified_sample") as mock_strat:
                    mock_strat.return_value = [sample_without_gap]

                    # Mock load_master_docs to avoid I/O
                    with patch("src.audit.cli.load_master_docs") as mock_docs:
                        mock_docs.return_value = ("master", "changelog", "jinja")

                        # Mock persist_sample to avoid I/O
                        with patch("src.audit.persistence.persist_sample"):
                            # Import and call the function
                            from src.audit.cli import cmd_sample

                            with pytest.raises(
                                SystemExit, match="Gap analysis generation failed"
                            ):
                                cmd_sample(args)


@pytest.mark.integration
class TestCmdGenerateExamErrorCases:
    """Test error handling in cmd_generate_exam (exam generation)."""

    def test_generate_exam_raises_propagates_error_from_generate_exam_question(
        self, golden_sample: Any, tmp_path: Path
    ) -> None:
        """cmd_generate_exam must propagate PromptGenerationError from generate_exam_question."""
        # Mock generate_exam_question to raise PromptGenerationError
        with patch("src.audit.cli.generate_exam_question") as mock_exam_gen:
            mock_exam_gen.side_effect = PromptGenerationError(
                "Exam generation failed: mocked error"
            )

            # Mock load_persisted_sample to return samples with ha_standards and gap_analysis
            with patch("src.audit.cli.load_persisted_sample") as mock_load:
                # Create a sample with reference_standards and gap_analysis to pass validation
                complete_sample = dataclasses.replace(
                    golden_sample,
                    reference_standards="Sample standards",
                    gap_analysis="Sample gap analysis",
                )
                mock_load.return_value = [complete_sample]

                # Create a minimal args namespace
                import argparse

                args = argparse.Namespace(
                    audit_dir=str(tmp_path),
                    force=True,
                    judge_model="gemini-2.0-flash",
                    api_url="http://localhost:8000",
                    retries=1,
                    retry_delay=0.1,
                    professor_backend="gemini",
                    gemini_model="gemini-2.0-flash",
                    validate=False,
                )

                # Mock persist_exam to avoid I/O
                with patch("src.audit.persistence.persist_exam"):
                    # Import and call the function
                    from src.audit.cli import cmd_generate_exam

                    with pytest.raises(SystemExit, match="Exam generation failed"):
                        cmd_generate_exam(args)
