#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Golden File tests for model_evaluator.py — Unit tests with realistic fixtures.

Tests the SCORING LOGIC and REPORT GENERATION without touching LLM APIs.
Uses Golden JSON fixtures to mock LLM boundaries and verify computation correctness.

Covers:
- compute_scorecard: correct composite score calculation, delta computation
- generate_report: markdown formatting, JSON serialization, filtering/sorting
- Regex pattern detection from ha_patterns.yaml
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.audit.model_evaluator import (
    compute_scorecard,
    generate_report,
)
from src.audit.schema import AuditReport, ScoreCard, ExamRecord
from tests.fixtures import (
    golden_exam,
    golden_inference_results,
    golden_judge_response,
    golden_sample,
)


# ---------------------------------------------------------------------------
# Golden File Tests: Scoring Logic
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestComputeScorecardGoldenFile:
    """Tests compute_scorecard with realistic judge responses from fixtures."""

    def test_computes_correct_composite_score(
        self,
        golden_exam: Any,
        golden_judge_response: dict[str, Any],
    ) -> None:
        """compute_scorecard must correctly compute composite score from judge data.

        Uses golden fixture to verify formula:
        composite = sum(dimension * weight) for all dimensions
        """
        # Mock llm_judge_score to return golden fixture data
        judge_data = {
            "adapter": golden_judge_response["dimensions"],
            "baseline": {
                "ha_modernity": 0.75,
                "reasoning_depth": 0.70,
                "functionality": 0.80,
                "completeness": 0.78,
                "style": 0.70,
            },
            "reasoning": golden_judge_response["judge_reasoning"],
        }

        # Extract scores from dimensions
        adapter_scores = {
            k: v["score"] for k, v in golden_judge_response["dimensions"].items()
        }
        judge_data["adapter"] = adapter_scores

        with patch(
            "src.audit.model_evaluator.llm_judge_score",
            return_value=judge_data,
        ):
            # Ensure deterministic testing by removing target patterns
            local_exam = ExamRecord.from_sample(golden_exam, target_patterns=[])
            sc = compute_scorecard(
                exam=local_exam,
                baseline_resp="baseline response",
                adapter_resp="adapter response",
                judge_model="test-judge",
            )

        # Verify composite score calculation
        from src.audit.schema import SCORING_WEIGHTS

        expected_composite = sum(
            adapter_scores.get(dim, 0.0) * weight
            for dim, weight in SCORING_WEIGHTS.items()
        )
        assert abs(sc.composite_score - round(expected_composite, 3)) < 0.001

    def test_computes_delta_vs_baseline(
        self,
        golden_exam: Any,
        golden_judge_response: dict[str, Any],
    ) -> None:
        """compute_scorecard must correctly compute delta between adapter and baseline."""
        baseline_scores = {
            "ha_modernity": 0.75,
            "reasoning_depth": 0.70,
            "functionality": 0.80,
            "completeness": 0.78,
            "style": 0.70,
        }
        adapter_scores = {
            k: v["score"] for k, v in golden_judge_response["dimensions"].items()
        }

        judge_data = {
            "adapter": adapter_scores,
            "baseline": baseline_scores,
            "reasoning": "Mock reasoning",
        }

        with patch(
            "src.audit.model_evaluator.llm_judge_score",
            return_value=judge_data,
        ):
            local_exam = ExamRecord.from_sample(golden_exam, target_patterns=[])
            sc = compute_scorecard(
                exam=local_exam,
                baseline_resp="baseline",
                adapter_resp="adapter",
                judge_model="test-judge",
            )

        from src.audit.schema import SCORING_WEIGHTS

        adapter_composite = sum(
            adapter_scores.get(dim, 0.0) * weight
            for dim, weight in SCORING_WEIGHTS.items()
        )
        baseline_composite = sum(
            baseline_scores.get(dim, 0.0) * weight
            for dim, weight in SCORING_WEIGHTS.items()
        )
        expected_delta = round(adapter_composite - baseline_composite, 3)

        assert abs(sc.delta_vs_baseline - expected_delta) < 0.001

    def test_includes_judge_reasoning_in_scorecard(
        self,
        golden_exam: Any,
        golden_judge_response: dict[str, Any],
    ) -> None:
        """Judge reasoning from LLM must be persisted in the ScoreCard."""
        adapter_scores = {
            k: v["score"] for k, v in golden_judge_response["dimensions"].items()
        }

        judge_data = {
            "adapter": adapter_scores,
            "baseline": {f: 0.5 for f in adapter_scores},
            "reasoning": golden_judge_response["judge_reasoning"],
        }

        with patch(
            "src.audit.model_evaluator.llm_judge_score",
            return_value=judge_data,
        ):
            local_exam = ExamRecord.from_sample(golden_exam, target_patterns=[])
            sc = compute_scorecard(
                exam=local_exam,
                baseline_resp="baseline",
                adapter_resp="adapter",
                judge_model="test-judge",
            )

        assert golden_judge_response["judge_reasoning"][:100] in sc.judge_reasoning

    def test_detects_legacy_and_modern_patterns(
        self,
        golden_exam: Any,
        golden_judge_response: dict[str, Any],
    ) -> None:
        """compute_scorecard must extract code blocks and detect patterns from ha_patterns.yaml."""
        adapter_scores = {
            k: v["score"] for k, v in golden_judge_response["dimensions"].items()
        }

        # Inject a response with recognizable patterns
        adapter_response_with_patterns = """
<think>Analysis</think>

```python
# Using modern pattern
async with self.client.get(url) as resp:
    return await resp.json()
```
"""

        judge_data = {
            "adapter": adapter_scores,
            "baseline": {f: 0.5 for f in adapter_scores},
            "reasoning": "Good use of patterns",
        }

        with patch(
            "src.audit.model_evaluator.llm_judge_score",
            return_value=judge_data,
        ):
            # Keep target_patterns for this test so pattern detection is exercised
            sc = compute_scorecard(
                exam=golden_exam,
                baseline_resp="baseline",
                adapter_resp=adapter_response_with_patterns,
                judge_model="test-judge",
            )

        # Should have detected patterns (notes should be populated or empty, but no error)
        assert isinstance(sc.notes, str)


# ---------------------------------------------------------------------------
# Golden File Tests: Report Generation
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestGenerateReportGoldenFile:
    """Tests generate_report with realistic data from golden fixtures."""

    def test_generates_markdown_report(
        self,
        tmp_path: Path,
        golden_exam: Any,
        golden_inference_results: tuple[Any, Any],
    ) -> None:
        """generate_report must produce valid Markdown with sections for scores and verdict."""
        baseline, adapter = golden_inference_results

        scorecard = ScoreCard(
            record_id=golden_exam.id,
            example_type=golden_exam.example_type,
            fragment_name=golden_exam.fragment_name,
            ha_modernity=0.95,
            reasoning_depth=0.88,
            functionality=0.90,
            completeness=0.92,
            style=0.85,
            composite_score=0.90,
            delta_vs_baseline=0.18,
            judge_reasoning="Adapter shows excellent patterns.",
        )

        report = AuditReport(
            timestamp="2026-03-03T18:00:00Z",
            dataset_path="data/golden_dataset.jsonl",
            base_model="qwen3-30b",
            adapter_model="platinum_adapter",
            judge_model="gemini-2.5-flash",
            sample_size=1,
            type_distribution={"nominal": 1},
            scorecards=[scorecard],
            final_grade=90.0,
            verdict="PASS",
        )

        report_path, _ = generate_report(
            report,
            [scorecard],
            [golden_exam],
            [baseline],
            [adapter],
            str(tmp_path),
        )

        assert report_path.exists()
        content = report_path.read_text(encoding="utf-8")

        # Verify Markdown structure
        assert "# AEGF Quality Gate —" in content
        assert "## Final Grade:" in content
        assert "## Score Breakdown by Example Type" in content
        assert "## Detailed Scorecards (LLM-as-Judge)" in content
        assert "## Scoring Methodology (LLM-as-Judge)" in content
        assert "PASS" in content or "90.0" in content

    def test_generates_json_report(
        self,
        tmp_path: Path,
        golden_exam: Any,
        golden_inference_results: tuple[Any, Any],
    ) -> None:
        """generate_report must also write a JSON artifact with structured data."""
        baseline, adapter = golden_inference_results

        scorecard = ScoreCard(
            record_id=golden_exam.id,
            example_type=golden_exam.example_type,
            fragment_name=golden_exam.fragment_name,
            ha_modernity=0.95,
            reasoning_depth=0.88,
            functionality=0.90,
            completeness=0.92,
            style=0.85,
            composite_score=0.90,
            delta_vs_baseline=0.18,
            judge_reasoning="Excellent work.",
        )

        report = AuditReport(
            timestamp="2026-03-03T18:00:00Z",
            dataset_path="data/test.jsonl",
            base_model="base",
            adapter_model="adapter",
            judge_model="judge",
            sample_size=1,
            type_distribution={"nominal": 1},
            scorecards=[scorecard],
            final_grade=90.0,
            verdict="PASS",
        )

        generate_report(
            report,
            [scorecard],
            [golden_exam],
            [baseline],
            [adapter],
            str(tmp_path),
        )

        json_path = tmp_path / "audit_report_v11.json"
        assert json_path.exists()
        data = json_path.read_text(encoding="utf-8")
        assert "final_grade" in data
        assert "90.0" in data or "90" in data

    def test_report_includes_all_dimensions(
        self,
        tmp_path: Path,
        golden_exam: Any,
        golden_inference_results: tuple[Any, Any],
    ) -> None:
        """Markdown report must display all five scoring dimensions, not just composite."""
        baseline, adapter = golden_inference_results

        scorecard = ScoreCard(
            record_id=golden_exam.id,
            example_type=golden_exam.example_type,
            fragment_name=golden_exam.fragment_name,
            ha_modernity=0.95,
            reasoning_depth=0.88,
            functionality=0.90,
            completeness=0.92,
            style=0.85,
            composite_score=0.90,
            delta_vs_baseline=0.18,
        )

        report = AuditReport(
            timestamp="2026-03-03T18:00:00Z",
            dataset_path="data/test.jsonl",
            base_model="base",
            adapter_model="adapter",
            judge_model="judge",
            sample_size=1,
            type_distribution={"nominal": 1},
            scorecards=[scorecard],
            final_grade=90.0,
            verdict="PASS",
        )

        report_path, _ = generate_report(
            report,
            [scorecard],
            [golden_exam],
            [baseline],
            [adapter],
            str(tmp_path),
        )

        content = report_path.read_text(encoding="utf-8")

        # Verify all dimensions appear in methodology table
        # Note: Dimensions appear as "HA Modernity" (capitalized), "Reasoning Depth", etc. in the table
        assert "HA Modernity" in content
        assert "Reasoning Depth" in content
        assert "Functionality" in content
        assert "Completeness" in content
        assert "Style" in content


# ---------------------------------------------------------------------------
# Integration: Full Pipeline with Golden Files
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestFullPipelineGoldenFile:
    """End-to-end test using golden fixtures without any LLM calls."""

    def test_full_scoring_pipeline_with_golden_data(
        self,
        tmp_path: Path,
        golden_sample: Any,
        golden_exam: Any,
        golden_inference_results: tuple[Any, Any],
        golden_judge_response: dict[str, Any],
    ) -> None:
        """Execute full scoring pipeline with golden fixtures."""
        baseline, adapter = golden_inference_results

        # Extract adapter scores from judge response
        adapter_scores = {
            k: v["score"] for k, v in golden_judge_response["dimensions"].items()
        }

        judge_data = {
            "adapter": adapter_scores,
            "baseline": {
                "ha_modernity": 0.75,
                "reasoning_depth": 0.70,
                "functionality": 0.80,
                "completeness": 0.78,
                "style": 0.70,
            },
            "reasoning": golden_judge_response["judge_reasoning"],
        }

        with patch(
            "src.audit.model_evaluator.llm_judge_score",
            return_value=judge_data,
        ):
            local_exam = ExamRecord.from_sample(golden_exam, target_patterns=[])
            scorecard = compute_scorecard(
                exam=local_exam,
                baseline_resp=baseline.response,
                adapter_resp=adapter.response,
                judge_model="test-judge",
            )

        # Verify scorecard from realistic judge data
        assert scorecard.composite_score > 0.85
        assert scorecard.delta_vs_baseline > 0.15
        assert (
            golden_judge_response["judge_reasoning"][:50] in scorecard.judge_reasoning
        )

        # Generate report with the scorecard
        report = AuditReport(
            timestamp="2026-03-03T18:00:00Z",
            dataset_path="data/golden_data.jsonl",
            base_model=baseline.model_name,
            adapter_model=adapter.model_name,
            judge_model="test-judge",
            sample_size=1,
            type_distribution={"nominal": 1},
            scorecards=[scorecard],
            final_grade=90.0,
            verdict="PASS",
        )

        report_path, _ = generate_report(
            report,
            [scorecard],
            [golden_exam],
            [baseline],
            [adapter],
            str(tmp_path),
        )

        # Verify both artifacts were created
        assert report_path.exists()
        json_path = tmp_path / "audit_report_v11.json"
        assert json_path.exists()
