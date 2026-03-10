#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for src/audit/schema.py.

Covers:
- SampleRecord construction and field defaults
- ExamRecord.from_sample() factory — field propagation and overrides
- ExamRecord default mutable fields (list isolation)
- ScoreCard defaults and field assignment
- AuditReport.to_dict() round-trip serialisation
- EXAMPLE_TYPES and SCORING_WEIGHTS constants invariants
"""

from __future__ import annotations

import dataclasses
from typing import Any, List

import pytest

from src.audit.schema import (
    EXAMPLE_TYPES,
    SCORING_WEIGHTS,
    AuditReport,
    ExamRecord,
    InferenceResult,
    PromptGenerationError,
    SampleRecord,
    ScoreCard,
)
from tests.conftest import make_exam_record, make_sample, make_scorecard


# ---------------------------------------------------------------------------
# SCORING_WEIGHTS invariants
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestScoringWeights:
    def test_weights_sum_to_one(self) -> None:
        total = sum(SCORING_WEIGHTS.values())
        assert abs(total - 1.0) < 1e-9, f"Weights must sum to 1.0, got {total}"

    def test_expected_dimensions_present(self) -> None:
        expected = {
            "ha_modernity",
            "reasoning_depth",
            "functionality",
            "completeness",
            "style",
        }
        assert set(SCORING_WEIGHTS.keys()) == expected

    def test_all_weights_positive(self) -> None:
        assert all(w > 0 for w in SCORING_WEIGHTS.values())


# ---------------------------------------------------------------------------
# EXAMPLE_TYPES invariants
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExampleTypes:
    def test_four_canonical_types(self) -> None:
        assert len(EXAMPLE_TYPES) == 4

    def test_canonical_names_present(self) -> None:
        for name in ("nominal", "contrast", "error_recovery", "theory"):
            assert name in EXAMPLE_TYPES, f"'{name}' must be a canonical example type"

    def test_no_duplicates(self) -> None:
        assert len(EXAMPLE_TYPES) == len(set(EXAMPLE_TYPES))


# ---------------------------------------------------------------------------
# SampleRecord
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSampleRecord:
    def test_construction_with_all_fields(self) -> None:
        r = make_sample()
        assert r.id == "sample-001"
        assert r.example_type == "nominal"
        assert r.ldi == 0.85
        assert r.gold_injected is True

    def test_default_optional_fields(self) -> None:
        r = SampleRecord(
            id="x",
            example_type="nominal",
            evol_difficulty="easy",
            fragment_name="f",
            source_file="s.py",
            user_prompt="u",
            reference_response="r",
            gold_injected=False,
            ldi=0.0,
        )
        assert r.reference_standards == ""
        assert r.gap_analysis == ""

    def test_is_dataclass(self) -> None:
        assert dataclasses.is_dataclass(SampleRecord)

    def test_fields_are_stable(self) -> None:
        """Ensure no accidental field removal breaks downstream code."""
        field_names = {f.name for f in dataclasses.fields(SampleRecord)}
        required = {
            "id",
            "example_type",
            "evol_difficulty",
            "fragment_name",
            "source_file",
            "user_prompt",
            "reference_response",
            "gold_injected",
            "ldi",
            "reference_standards",
            "gap_analysis",
        }
        assert required.issubset(field_names)


# ---------------------------------------------------------------------------
# ExamRecord.from_sample()
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExamRecordFromSample:
    def test_propagates_all_sample_fields(self, sample_record: SampleRecord) -> None:
        exam = ExamRecord.from_sample(sample_record)
        for field in dataclasses.fields(SampleRecord):
            assert getattr(exam, field.name) == getattr(sample_record, field.name), (
                f"Field '{field.name}' not propagated to ExamRecord"
            )

    def test_exam_fields_default_to_empty(self, sample_record: SampleRecord) -> None:
        exam = ExamRecord.from_sample(sample_record)
        assert exam.exam_question == ""
        assert exam.eval_criteria == []
        assert exam.target_patterns == []

    def test_exam_fields_can_be_overridden(self, sample_record: SampleRecord) -> None:
        exam = ExamRecord.from_sample(
            sample_record,
            exam_question="New question?",
            eval_criteria=["crit-1", "crit-2"],
            target_patterns=["pattern-a"],
        )
        assert exam.exam_question == "New question?"
        assert exam.eval_criteria == ["crit-1", "crit-2"]
        assert exam.target_patterns == ["pattern-a"]

    def test_mutable_default_isolation_between_instances(
        self, sample_record: SampleRecord
    ) -> None:
        """Two ExamRecords must not share the same list object for eval_criteria."""
        exam_a = ExamRecord.from_sample(sample_record)
        exam_b = ExamRecord.from_sample(sample_record)
        exam_a.eval_criteria.append("injected")
        assert "injected" not in exam_b.eval_criteria

    def test_does_not_mutate_input_sample(self, sample_record: SampleRecord) -> None:
        original_id = sample_record.id
        ExamRecord.from_sample(sample_record, exam_question="Q")
        assert sample_record.id == original_id

    def test_id_is_preserved(self, sample_record: SampleRecord) -> None:
        exam = ExamRecord.from_sample(sample_record)
        assert exam.id == sample_record.id


# ---------------------------------------------------------------------------
# ScoreCard
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestScoreCard:
    def test_construction_with_defaults(self) -> None:
        sc = ScoreCard(record_id="r1", example_type="nominal", fragment_name="f")
        assert sc.ha_modernity == 0.0
        assert sc.composite_score == 0.0
        assert sc.judge_reasoning == ""

    def test_explicit_values_stored(self) -> None:
        sc = make_scorecard(ha_modernity=0.9, composite_score=0.88)
        assert sc.ha_modernity == 0.9
        assert sc.composite_score == 0.88

    def test_is_dataclass(self) -> None:
        assert dataclasses.is_dataclass(ScoreCard)


# ---------------------------------------------------------------------------
# AuditReport.to_dict()
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAuditReport:
    def test_to_dict_returns_dict(self, audit_report: AuditReport) -> None:
        result = audit_report.to_dict()
        assert isinstance(result, dict)

    def test_to_dict_preserves_scalar_fields(self, audit_report: AuditReport) -> None:
        d = audit_report.to_dict()
        assert d["final_grade"] == audit_report.final_grade
        assert d["verdict"] == audit_report.verdict
        assert d["sample_size"] == audit_report.sample_size

    def test_to_dict_serialises_nested_scorecards(
        self, audit_report: AuditReport
    ) -> None:
        d = audit_report.to_dict()
        assert isinstance(d["scorecards"], list)
        assert len(d["scorecards"]) == 1
        sc_dict = d["scorecards"][0]
        assert isinstance(sc_dict, dict)
        assert "composite_score" in sc_dict

    def test_to_dict_is_idempotent(self, audit_report: AuditReport) -> None:
        """Calling to_dict() twice must return the same value."""
        assert audit_report.to_dict() == audit_report.to_dict()

    def test_empty_report_to_dict(self) -> None:
        report = AuditReport()
        d = report.to_dict()
        assert d["scorecards"] == []
        assert d["type_distribution"] == {}
        assert d["final_grade"] == 0.0

    def test_type_distribution_is_copy(self, audit_report: AuditReport) -> None:
        """Mutating the dict result must not affect the original report."""
        d = audit_report.to_dict()
        d["type_distribution"]["injected"] = 99
        assert "injected" not in audit_report.type_distribution


# ---------------------------------------------------------------------------
# PromptGenerationError
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPromptGenerationError:
    def test_is_exception_subclass(self) -> None:
        assert issubclass(PromptGenerationError, Exception)

    def test_can_be_raised_and_caught(self) -> None:
        with pytest.raises(PromptGenerationError, match="professor failure"):
            raise PromptGenerationError("professor failure")


# ---------------------------------------------------------------------------
# InferenceResult
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestInferenceResult:
    def test_construction(self) -> None:
        ir = InferenceResult(
            record_id="r1",
            model_name="gemini-2.5-flash",
            response="answer",
            latency_ms=350.5,
            token_count=512,
            timestamp="2026-03-03T10:00:00",
        )
        assert ir.record_id == "r1"
        assert ir.latency_ms == 350.5

    def test_is_dataclass(self) -> None:
        assert dataclasses.is_dataclass(InferenceResult)
