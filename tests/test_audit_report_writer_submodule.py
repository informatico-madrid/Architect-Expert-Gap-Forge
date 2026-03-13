#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for src/audit/report_writer.py utility functions."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import pytest

from src.audit.report_writer import _get_grade_label, _get_verdict, generate_report
from src.audit.schema import AuditReport, ScoreCard


class TestGetGradeLabel:
    """Tests for _get_grade_label function."""

    def test_grade_a(self) -> None:
        """Score >= 90 should return A."""
        assert _get_grade_label(90) == "A"
        assert _get_grade_label(95) == "A"
        assert _get_grade_label(100) == "A"

    def test_grade_b(self) -> None:
        """Score >= 80 and < 90 should return B."""
        assert _get_grade_label(80) == "B"
        assert _get_grade_label(85) == "B"
        assert _get_grade_label(89) == "B"

    def test_grade_c(self) -> None:
        """Score >= 70 and < 80 should return C."""
        assert _get_grade_label(70) == "C"
        assert _get_grade_label(75) == "C"
        assert _get_grade_label(79) == "C"

    def test_grade_d(self) -> None:
        """Score >= 60 and < 70 should return D."""
        assert _get_grade_label(60) == "D"
        assert _get_grade_label(65) == "D"
        assert _get_grade_label(69) == "D"

    def test_grade_e(self) -> None:
        """Score >= 50 and < 60 should return E."""
        assert _get_grade_label(50) == "E"
        assert _get_grade_label(55) == "E"
        assert _get_grade_label(59) == "E"

    def test_grade_f(self) -> None:
        """Score < 50 should return F."""
        assert _get_grade_label(0) == "F"
        assert _get_grade_label(25) == "F"
        assert _get_grade_label(49) == "F"


class TestGetVerdict:
    """Tests for _get_verdict function."""

    def test_verdict_pass(self) -> None:
        """Grade >= 80 should return PASS."""
        grade = 80
        result = _get_verdict(grade)
        assert "PASS" in result

    def test_verdict_conditional(self) -> None:
        """Grade >= 60 and < 80 should return CONDITIONAL."""
        grade = 60
        result = _get_verdict(grade)
        assert "CONDITIONAL" in result

    def test_verdict_warn(self) -> None:
        """Grade >= 40 and < 60 should return WARN."""
        grade = 40
        result = _get_verdict(grade)
        assert "WARN" in result

    def test_verdict_fail(self) -> None:
        """Grade < 40 should return FAIL."""
        grade = 30
        result = _get_verdict(grade)
        assert "FAIL" in result


class TestGenerateReport:
    """Tests for generate_report function."""

    def test_generate_report_basic(self, tmp_path: Path) -> None:
        """Should generate a basic report with minimal data."""
        report = AuditReport(
            dataset_path="data/test.jsonl",
            base_model="base-model",
            adapter_model="adapter-model",
            judge_model="judge-model",
            sample_size=10,
        )
        scorecards = [
            ScoreCard(
                record_id="test-1",
                sample_id="test-1",
                example_type="nominal",
                fragment_name="test.py",
                ha_modernity=0.8,
                reasoning_depth=0.7,
                functionality=0.9,
                completeness=0.85,
                style=0.75,
                composite_score=0.8,
                delta_vs_baseline=0.1,
                judge_reasoning="Good response",
                notes="Test note",
            ),
        ]

        # Create minimal exam records and inference results
        exam_records: list[Any] = []
        baseline_results: list[Any] = []
        adapter_results: list[Any] = []

        report_path, updated_report = generate_report(
            report=report,
            scorecards=scorecards,
            exam_records=exam_records,
            baseline_results=baseline_results,
            adapter_results=adapter_results,
            audit_dir=str(tmp_path / "audit"),
        )

        assert report_path.exists()
        assert updated_report.final_grade > 0

    def test_generate_report_empty_scorecards(self, tmp_path: Path) -> None:
        """Should handle empty scorecards list."""
        report = AuditReport(
            dataset_path="data/test.jsonl",
            base_model="base-model",
            adapter_model="adapter-model",
            judge_model="judge-model",
            sample_size=0,
        )

        report_path, updated_report = generate_report(
            report=report,
            scorecards=[],
            exam_records=[],
            baseline_results=[],
            adapter_results=[],
            audit_dir=str(tmp_path / "audit"),
        )

        assert report_path.exists()
        assert updated_report.final_grade == 0.0

    def test_generate_report_multiple_scorecards(self, tmp_path: Path) -> None:
        """Should generate report with multiple scorecards."""
        report = AuditReport(
            dataset_path="data/test.jsonl",
            base_model="base-model",
            adapter_model="adapter-model",
            judge_model="judge-model",
            sample_size=3,
        )
        scorecards = [
            ScoreCard(
                record_id=f"test-{i}",
                sample_id=f"test-{i}",
                example_type="nominal",
                fragment_name=f"test{i}.py",
                ha_modernity=0.8,
                reasoning_depth=0.7,
                functionality=0.9,
                completeness=0.85,
                style=0.75,
                composite_score=0.8,
                delta_vs_baseline=0.1,
                judge_reasoning="Good",
                notes="",
            )
            for i in range(3)
        ]

        report_path, updated_report = generate_report(
            report=report,
            scorecards=scorecards,
            exam_records=[],
            baseline_results=[],
            adapter_results=[],
            audit_dir=str(tmp_path / "audit"),
        )

        assert report_path.exists()
        # Average of 0.8 * 100 = 80
        assert updated_report.final_grade == 80.0
