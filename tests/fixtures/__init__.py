"""Fixtures for Golden File Testing in model_evaluator integration tests."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from src.audit.schema import ExamRecord, InferenceResult, SampleRecord


FIXTURES_DIR = Path(__file__).parent


def load_golden_json(filename: str) -> dict[str, Any]:
    """Load a golden JSON fixture file."""
    path = FIXTURES_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Golden fixture not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def golden_sample() -> SampleRecord:
    """Load a golden SampleRecord from fixture."""
    data = load_golden_json("sample_record.json")
    return SampleRecord(
        id=data["id"],
        example_type=data["example_type"],
        evol_difficulty=data["evol_difficulty"],
        fragment_name=data["fragment_name"],
        source_file=data["source_file"],
        user_prompt=data["user_prompt"],
        reference_response=data["reference_response"],
        gold_injected=data["gold_injected"],
        ldi=data["ldi"],
        reference_standards=data["reference_standards"],
        gap_analysis=data["gap_analysis"],
    )


@pytest.fixture
def golden_exam(golden_sample: SampleRecord) -> ExamRecord:
    """Load a golden ExamRecord from fixture."""
    data = load_golden_json("exam_record.json")
    return ExamRecord.from_sample(
        golden_sample,
        exam_question=data["exam_question"],
        eval_criteria=data["eval_criteria"],
        target_patterns=data["target_patterns"],
    )


@pytest.fixture
def golden_inference_results() -> tuple[InferenceResult, InferenceResult]:
    """Load golden baseline and adapter InferenceResults from fixture."""
    data = load_golden_json("inference_results.json")
    baseline = InferenceResult(
        record_id=data["baseline_response"]["record_id"],
        model_name=data["baseline_response"]["model_name"],
        response=data["baseline_response"]["response"],
        latency_ms=data["baseline_response"]["latency_ms"],
        token_count=data["baseline_response"]["token_count"],
        timestamp=data["baseline_response"]["timestamp"],
    )
    adapter = InferenceResult(
        record_id=data["adapter_response"]["record_id"],
        model_name=data["adapter_response"]["model_name"],
        response=data["adapter_response"]["response"],
        latency_ms=data["adapter_response"]["latency_ms"],
        token_count=data["adapter_response"]["token_count"],
        timestamp=data["adapter_response"]["timestamp"],
    )
    return baseline, adapter


@pytest.fixture
def golden_judge_response() -> dict[str, Any]:
    """Load a golden judge scoring response from fixture."""
    return load_golden_json("judge_scoring_response.json")
