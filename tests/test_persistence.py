#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for src/audit/persistence.py.

Covers all six persistence functions via round-trip and error-path scenarios:
- persist_sample / load_persisted_sample
- persist_exam    / load_exam
- persist_inference / load_inference
- FileNotFoundError on missing artifact
- Output JSON is valid and contains expected metadata
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.audit.persistence import (
    load_exam,
    load_inference,
    load_persisted_sample,
    persist_exam,
    persist_inference,
    persist_sample,
)
from src.audit.schema import ExamRecord, InferenceResult, SampleRecord


# ---------------------------------------------------------------------------
# Helpers — minimal valid fixtures
# ---------------------------------------------------------------------------


def _make_sample(idx: int = 0) -> SampleRecord:
    return SampleRecord(
        id=f"s-{idx:03d}",
        example_type="nominal",
        evol_difficulty="medium",
        fragment_name=f"frag_{idx}",
        source_file=f"components/sensor/{idx}.py",
        user_prompt="Implement sensor.",
        reference_response="<think>OK</think>\n```python\npass\n```",
        gold_injected=True,
        ldi=0.8 + idx * 0.01,
        reference_standards="Use entry.runtime_data.",
        gap_analysis="Legacy pattern detected.",
    )


def _make_exam(idx: int = 0) -> ExamRecord:
    sample = _make_sample(idx)
    return ExamRecord.from_sample(
        sample,
        exam_question=f"Implement a modern {idx} sensor without legacy patterns.",
        eval_criteria=["Uses entry.runtime_data", "Uses async_forward_entry_setups"],
        target_patterns=["entry.runtime_data"],
    )


def _make_result(idx: int = 0, label: str = "baseline") -> InferenceResult:
    return InferenceResult(
        record_id=f"s-{idx:03d}",
        model_name=f"model-{label}",
        response="<think>OK</think>\n```python\npass\n```",
        latency_ms=123.4,
        token_count=42,
        timestamp="2026-01-01T00:00:00+00:00",
    )


# ---------------------------------------------------------------------------
# persist_sample / load_persisted_sample
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSampleRoundTrip:
    def test_persist_creates_file(self, tmp_path: Path) -> None:
        samples = [_make_sample(i) for i in range(3)]
        path = persist_sample(samples, str(tmp_path))
        assert path.exists()
        assert path.suffix == ".json"

    def test_persist_payload_structure(self, tmp_path: Path) -> None:
        samples = [_make_sample(i) for i in range(2)]
        path = persist_sample(samples, str(tmp_path))
        payload = json.loads(path.read_text())
        assert payload["sample_size"] == 2
        assert "type_distribution" in payload
        assert len(payload["records"]) == 2

    def test_load_roundtrip(self, tmp_path: Path) -> None:
        samples = [_make_sample(i) for i in range(4)]
        persist_sample(samples, str(tmp_path))
        loaded = load_persisted_sample(str(tmp_path))
        assert len(loaded) == 4
        assert all(isinstance(s, SampleRecord) for s in loaded)
        assert [s.id for s in loaded] == [s.id for s in samples]

    def test_load_missing_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="Run 'sample' mode first"):
            load_persisted_sample(str(tmp_path))

    def test_persist_creates_parent_dir(self, tmp_path: Path) -> None:
        deep = tmp_path / "nested" / "audit"
        persist_sample([_make_sample()], str(deep))
        assert (deep / "eval_sample.json").exists()


# ---------------------------------------------------------------------------
# persist_exam / load_exam
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExamRoundTrip:
    def test_persist_creates_file(self, tmp_path: Path) -> None:
        exams = [_make_exam(i) for i in range(2)]
        path = persist_exam(exams, str(tmp_path))
        assert path.name == "eval_exam.json"

    def test_persist_payload_count(self, tmp_path: Path) -> None:
        exams = [_make_exam(i) for i in range(3)]
        path = persist_exam(exams, str(tmp_path))
        payload = json.loads(path.read_text())
        assert payload["count"] == 3

    def test_load_roundtrip(self, tmp_path: Path) -> None:
        exams = [_make_exam(i) for i in range(2)]
        persist_exam(exams, str(tmp_path))
        loaded = load_exam(str(tmp_path))
        assert len(loaded) == 2
        assert all(isinstance(e, ExamRecord) for e in loaded)
        assert loaded[0].exam_question == exams[0].exam_question

    def test_load_missing_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="Run 'generate-exam' mode first"):
            load_exam(str(tmp_path))


# ---------------------------------------------------------------------------
# persist_inference / load_inference
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestInferenceRoundTrip:
    def test_persist_creates_labelled_file(self, tmp_path: Path) -> None:
        results = [_make_result(i, "baseline") for i in range(3)]
        path = persist_inference(results, "baseline", str(tmp_path))
        assert path.name == "inference_baseline.json"

    def test_persist_payload_model_name(self, tmp_path: Path) -> None:
        results = [_make_result(0, "adapter")]
        path = persist_inference(results, "adapter", str(tmp_path))
        payload = json.loads(path.read_text())
        assert payload["model"] == "model-adapter"
        assert payload["label"] == "adapter"

    def test_load_roundtrip(self, tmp_path: Path) -> None:
        results = [_make_result(i, "baseline") for i in range(5)]
        persist_inference(results, "baseline", str(tmp_path))
        loaded = load_inference("baseline", str(tmp_path))
        assert len(loaded) == 5
        assert all(isinstance(r, InferenceResult) for r in loaded)

    def test_load_missing_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="Run 'baseline' mode first"):
            load_inference("baseline", str(tmp_path))

    def test_persist_empty_results_model_unknown(self, tmp_path: Path) -> None:
        path = persist_inference([], "baseline", str(tmp_path))
        payload = json.loads(path.read_text())
        assert payload["model"] == "unknown"
        assert payload["count"] == 0
