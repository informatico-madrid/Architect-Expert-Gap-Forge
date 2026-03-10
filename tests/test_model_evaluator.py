#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Integration tests for src/audit/model_evaluator.py CLI command handlers.

Tests each cmd_* stage independently, using:
- Temporary directories for all filesystem side-effects.
- Mocked generate_gap_analysis / generate_exam_question / run_inference /
  compute_scorecard / generate_report to avoid LLM API calls.
- Monkeypatched AEGF_DOC_* env vars so the doc_loader resolves fixtures files.

Coverage targets:
  cmd_sample      — Phase 1: FrozenInstanceError regression; injection; skip
  cmd_generate_exam — Phase 2: exam question generation & persistence
  cmd_baseline    — Phase 3: baseline inference persistence
  cmd_adapter     — Phase 4: adapter inference persistence
  cmd_score       — Phase 5: scoring + report
"""

from __future__ import annotations

import argparse
import dataclasses
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.audit.model_evaluator import (
    cmd_adapter,
    cmd_baseline,
    cmd_generate_exam,
    cmd_sample,
    cmd_score,
)
from src.audit.persistence import (
    load_exam,
    load_inference,
    load_persisted_sample,
    persist_exam,
    persist_inference,
)
from src.audit.schema import (
    AuditReport,
    ExamRecord,
    InferenceResult,
    SampleRecord,
    ScoreCard,
)
from tests.conftest import make_exam_record, make_sample, make_scorecard


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DOC_CONTENT_MASTER = "# Master Guide"
_DOC_CONTENT_CHANGELOG = "# Changelog"
_DOC_CONTENT_JINJA = "# Jinja Guide"

_DOC_1_NAME = "doc1.md"
_DOC_2_NAME = "doc2.md"
_DOC_3_NAME = "doc3.md"


def _write_docs(gap_dir: Path) -> None:
    """Write three minimal doc files into gap_dir."""
    (gap_dir / _DOC_1_NAME).write_text(_DOC_CONTENT_MASTER, encoding="utf-8")
    (gap_dir / _DOC_2_NAME).write_text(_DOC_CONTENT_CHANGELOG, encoding="utf-8")
    (gap_dir / _DOC_3_NAME).write_text(_DOC_CONTENT_JINJA, encoding="utf-8")


def _make_raw_jsonl(
    tmp_path: Path,
    *,
    reference_standards: str = "",
    gap_analysis: str = "",
    n_records: int = 4,
) -> Path:
    """Write a minimal JSONL dataset and return its path."""
    out = tmp_path / "dataset.jsonl"
    types = ["nominal", "contrast", "error_recovery", "theory"]
    records: list[dict[str, Any]] = []
    for i in range(n_records):
        et = types[i % len(types)]
        records.append(
            {
                "id": f"{et}-{i:03d}",
                "metadata": {
                    "example_type": et,
                    "evol_difficulty": "medium",
                    "fragment_name": f"fragment_{i}",
                    "source_file": f"components/sensor/{i}.py",
                    "gold_injected": True,
                    "ldi": 0.7 + i * 0.01,
                    "reference_standards": reference_standards,
                    "gap_analysis": gap_analysis,
                },
                "conversation": [
                    {"role": "user", "content": f"Implement sensor {i}."},
                    {
                        "role": "assistant",
                        "content": f"<think>Thinking {i}</think>\n```python\npass\n```",
                    },
                ],
            }
        )
    out.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")
    return out


def _default_args(tmp_path: Path, **overrides: Any) -> argparse.Namespace:
    """Build an argparse.Namespace with sensible test defaults."""
    gap = tmp_path / "gap"
    gap.mkdir(exist_ok=True)
    _write_docs(gap)

    defaults: dict[str, Any] = {
        "audit_dir": str(tmp_path / "audit"),
        "dataset": None,
        "force": False,
        "gap_dir": str(gap),
        "sample_size": 4,
        "professor_backend": "auto",
        "gemini_model": "gemini-2.5-flash",
        "judge_model": "test-judge",
        "api_url": "http://localhost:8000/v1",
        "retries": 1,
        "retry_delay": 0.0,
        "validate": False,
        "base_model": "test-base",
        "adapter_model": "test-adapter",
        "model": None,
        "max_tokens": 512,
        "temperature": 0.3,
        "inference_backend": "vllm",
    }
    defaults.update(overrides)
    Path(defaults["audit_dir"]).mkdir(parents=True, exist_ok=True)
    return argparse.Namespace(**defaults)


# ---------------------------------------------------------------------------
# Phase 1 — cmd_sample
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestCmdSamplePhase1:
    """Phase 1: stratified sampling + reference_standards / gap_analysis injection."""

    @pytest.fixture(autouse=True)
    def _patch_doc_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Route doc_loader to the generic test docs created by _default_args."""
        monkeypatch.setenv("AEGF_DOC_1", _DOC_1_NAME)
        monkeypatch.setenv("AEGF_DOC_2", _DOC_2_NAME)
        monkeypatch.setenv("AEGF_DOC_3", _DOC_3_NAME)

    # ------------------------------------------------------------------
    # Regression: frozen dataclass mutation → FrozenInstanceError
    # ------------------------------------------------------------------

    def test_frozen_mutation_raises_without_fix(self, tmp_path: Path) -> None:
        """Directly verify that assigning to a frozen SampleRecord field raises
        FrozenInstanceError. This documents the root-cause of the production bug."""
        sample = make_sample(reference_standards="", gap_analysis="")
        with pytest.raises((dataclasses.FrozenInstanceError, TypeError)):
            sample.reference_standards = "should not work"  # type: ignore[misc]

    def test_inject_reference_standards_for_empty_records(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """cmd_sample must inject reference_standards into records that arrive with an
        empty string, persisting fully enriched SampleRecords to disk."""
        dataset = _make_raw_jsonl(
            tmp_path, reference_standards="", gap_analysis="existing_gap"
        )
        args = _default_args(
            tmp_path,
            dataset=str(dataset),
            force=True,
            sample_size=4,
        )

        cmd_sample(args)

        persisted = load_persisted_sample(args.audit_dir)
        assert len(persisted) == 4
        for record in persisted:
            assert record.reference_standards, (
                f"reference_standards must be injected for {record.id}"
            )
            assert "MASTER_GUIDE" in record.reference_standards

    def test_skips_reference_standards_injection_when_already_present(
        self, tmp_path: Path
    ) -> None:
        """Records with non-empty reference_standards must not be overwritten."""
        original_standards = "Use entry.runtime_data."
        dataset = _make_raw_jsonl(
            tmp_path,
            reference_standards=original_standards,
            gap_analysis="existing gap analysis",
        )
        args = _default_args(
            tmp_path,
            dataset=str(dataset),
            force=True,
            sample_size=4,
        )

        cmd_sample(args)

        persisted = load_persisted_sample(args.audit_dir)
        for record in persisted:
            assert record.reference_standards == original_standards, (
                f"reference_standards for {record.id} should not be overwritten"
            )

    def test_calls_gap_analysis_generation_when_missing(self, tmp_path: Path) -> None:
        """When gap_analysis is empty, cmd_sample must call generate_gap_analysis
        and persist the returned value on each record."""
        dataset = _make_raw_jsonl(tmp_path, reference_standards="", gap_analysis="")
        args = _default_args(tmp_path, dataset=str(dataset), force=True, sample_size=4)

        mock_gap = "Generated gap analysis text."
        with patch(
            "src.audit.model_evaluator.generate_gap_analysis",
            return_value=mock_gap,
        ) as mock_fn:
            cmd_sample(args)

        persisted = load_persisted_sample(args.audit_dir)
        assert mock_fn.call_count == 4
        for record in persisted:
            assert record.gap_analysis == mock_gap

    def test_skips_gap_analysis_when_already_present(self, tmp_path: Path) -> None:
        """When gap_analysis is already present, generate_gap_analysis must not
        be called even when reference_standards needs injection."""
        dataset = _make_raw_jsonl(
            tmp_path, reference_standards="", gap_analysis="pre-existing"
        )
        args = _default_args(tmp_path, dataset=str(dataset), force=True, sample_size=4)

        with patch(
            "src.audit.model_evaluator.generate_gap_analysis",
        ) as mock_fn:
            cmd_sample(args)

        mock_fn.assert_not_called()

    def test_does_not_regenerate_when_file_exists_and_no_force(
        self, tmp_path: Path
    ) -> None:
        """Without --force a pre-existing eval_sample.json is reloaded silently."""
        # Persist manually
        sample = make_sample(id="cached-001")
        audit_dir = tmp_path / "audit"
        audit_dir.mkdir()
        persist_sample = __import__(
            "src.audit.persistence", fromlist=["persist_sample"]
        ).persist_sample
        persist_sample([sample], str(audit_dir))

        args = _default_args(tmp_path, force=False, audit_dir=str(audit_dir))

        with patch("src.audit.model_evaluator.load_dataset") as mock_load:
            cmd_sample(args)

        mock_load.assert_not_called()
        persisted = load_persisted_sample(str(audit_dir))
        assert persisted[0].id == "cached-001"

    def test_raises_systemexit_when_dataset_missing(self, tmp_path: Path) -> None:
        """--dataset is mandatory when no persisted sample exists."""
        args = _default_args(tmp_path, dataset=None, force=True)
        with pytest.raises(SystemExit):
            cmd_sample(args)


# ---------------------------------------------------------------------------
# Phase 2 — cmd_generate_exam
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestCmdGenerateExamPhase2:
    """Phase 2: Professor model generates and persists exam questions."""

    def _persist_valid_sample(self, audit_dir: str) -> list[SampleRecord]:
        from src.audit.persistence import persist_sample as _ps

        samples = [
            make_sample(
                id=f"s{i:03d}",
                example_type=t,
                reference_standards="Use entry.runtime_data.",
                gap_analysis="Missing coordinator.",
            )
            for i, t in enumerate(["nominal", "contrast", "error_recovery", "theory"])
        ]
        _ps(samples, audit_dir)
        return samples

    def test_generates_and_persists_exam_records(self, tmp_path: Path) -> None:
        """cmd_generate_exam must generate one ExamRecord per sample and
        write them to eval_exam.json in audit_dir."""
        args = _default_args(tmp_path)
        self._persist_valid_sample(args.audit_dir)

        mock_exam = make_exam_record()

        with patch(
            "src.audit.model_evaluator.generate_exam_question",
            return_value=mock_exam,
        ) as mock_fn:
            cmd_generate_exam(args)

        assert mock_fn.call_count == 4
        records = load_exam(args.audit_dir)
        assert len(records) == 4

    def test_skips_generation_when_exam_exists_and_no_force(
        self, tmp_path: Path
    ) -> None:
        """Without --force an existing eval_exam.json is reloaded without
        calling generate_exam_question."""
        args = _default_args(tmp_path)
        samples = self._persist_valid_sample(args.audit_dir)
        exams = [make_exam_record(s) for s in samples]
        persist_exam(exams, args.audit_dir)

        with patch("src.audit.model_evaluator.generate_exam_question") as mock_fn:
            cmd_generate_exam(args)

        mock_fn.assert_not_called()

    def test_raises_systemexit_when_sample_missing_metadata(
        self, tmp_path: Path
    ) -> None:
        """cmd_generate_exam must abort if the persisted sample has records
        without reference_standards or gap_analysis."""
        from src.audit.persistence import persist_sample as _ps

        samples = [
            make_sample(id="incomplete", reference_standards="", gap_analysis="")
        ]
        _ps(samples, args := _default_args(tmp_path).audit_dir)
        args_ns = _default_args(tmp_path)

        with pytest.raises(SystemExit, match="Persisted sample validation failed"):
            cmd_generate_exam(args_ns)


# ---------------------------------------------------------------------------
# Phase 3 — cmd_baseline
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestCmdBaselinePhase3:
    """Phase 3: Baseline model inference on exam questions."""

    def _setup_exam(self, audit_dir: str) -> list[ExamRecord]:
        from src.audit.persistence import persist_sample as _ps

        samples = [
            make_sample(
                id=f"s{i:03d}",
                example_type=t,
                reference_standards="std",
                gap_analysis="gap",
            )
            for i, t in enumerate(["nominal", "contrast", "error_recovery", "theory"])
        ]
        _ps(samples, audit_dir)
        exams = [make_exam_record(s) for s in samples]
        persist_exam(exams, audit_dir)
        return exams

    def test_runs_baseline_inference_and_persists(self, tmp_path: Path) -> None:
        """cmd_baseline must call run_inference and persist InferenceResult list."""
        args = _default_args(tmp_path)
        exams = self._setup_exam(args.audit_dir)

        mock_results = [
            InferenceResult(
                record_id=e.id,
                model_name="test-base",
                response="adapter response",
                latency_ms=100.0,
                token_count=10,
                timestamp="2026-03-03T00:00:00",
            )
            for e in exams
        ]

        with patch(
            "src.audit.model_evaluator.run_inference",
            return_value=mock_results,
        ) as mock_inf:
            cmd_baseline(args)

        mock_inf.assert_called_once()
        results = load_inference("baseline", args.audit_dir)
        assert len(results) == 4
        assert all(r.model_name == "test-base" for r in results)

    def test_falls_back_to_sample_when_no_exam(self, tmp_path: Path) -> None:
        """Without an exam, cmd_baseline falls back to the persisted sample's
        user_prompt, calling run_inference with SampleRecord objects."""
        from src.audit.persistence import persist_sample as _ps

        samples = [
            make_sample(id=f"s{i:03d}", reference_standards="std", gap_analysis="gap")
            for i in range(4)
        ]
        _ps(samples, _default_args(tmp_path).audit_dir)
        args = _default_args(tmp_path)

        mock_results = [
            InferenceResult(
                record_id=s.id,
                model_name="test-base",
                response="response",
                latency_ms=100.0,
                token_count=5,
                timestamp="2026-03-03T00:00:00",
            )
            for s in samples
        ]
        with patch(
            "src.audit.model_evaluator.run_inference",
            return_value=mock_results,
        ):
            cmd_baseline(args)

        results = load_inference("baseline", args.audit_dir)
        assert len(results) == 4


# ---------------------------------------------------------------------------
# Phase 4 — cmd_adapter
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestCmdAdapterPhase4:
    """Phase 4: Adapter (LoRA) model inference on exam questions."""

    def _setup_exam(self, audit_dir: str) -> list[ExamRecord]:
        from src.audit.persistence import persist_sample as _ps

        samples = [
            make_sample(id=f"s{i:03d}", reference_standards="std", gap_analysis="gap")
            for i in range(4)
        ]
        _ps(samples, audit_dir)
        exams = [make_exam_record(s) for s in samples]
        persist_exam(exams, audit_dir)
        return exams

    def test_runs_adapter_inference_and_persists(self, tmp_path: Path) -> None:
        """cmd_adapter must call run_inference and persist results under
        'adapter' key in the inference artifact."""
        args = _default_args(tmp_path)
        exams = self._setup_exam(args.audit_dir)

        mock_results = [
            InferenceResult(
                record_id=e.id,
                model_name="test-adapter",
                response="adapter response",
                latency_ms=100.0,
                token_count=10,
                timestamp="2026-03-03T00:00:00",
            )
            for e in exams
        ]

        with patch(
            "src.audit.model_evaluator.run_inference",
            return_value=mock_results,
        ) as mock_inf:
            cmd_adapter(args)

        mock_inf.assert_called_once()
        results = load_inference("adapter", args.audit_dir)
        assert len(results) == 4
        assert all(r.model_name == "test-adapter" for r in results)


# ---------------------------------------------------------------------------
# Phase 5 — cmd_score
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestCmdScorePhase5:
    """Phase 5: LLM-as-Judge scoring + report generation."""

    def _setup_full_pipeline(
        self, audit_dir: str
    ) -> tuple[list[ExamRecord], list[InferenceResult], list[InferenceResult]]:
        from src.audit.persistence import persist_sample as _ps

        samples = [
            make_sample(id=f"s{i:03d}", reference_standards="std", gap_analysis="gap")
            for i in range(4)
        ]
        _ps(samples, audit_dir)
        exams = [make_exam_record(s) for s in samples]
        persist_exam(exams, audit_dir)
        baseline = [
            InferenceResult(
                record_id=e.id,
                model_name="base",
                response="baseline response",
                latency_ms=100.0,
                token_count=10,
                timestamp="2026-03-03T00:00:00",
            )
            for e in exams
        ]
        adapter = [
            InferenceResult(
                record_id=e.id,
                model_name="adapter",
                response="adapter response",
                latency_ms=100.0,
                token_count=10,
                timestamp="2026-03-03T00:00:00",
            )
            for e in exams
        ]
        persist_inference(baseline, "baseline", audit_dir)
        persist_inference(adapter, "adapter", audit_dir)
        return exams, baseline, adapter

    def test_scores_records_and_generates_report(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        """cmd_score must call compute_scorecard once per record and invoke
        generate_report with the final AuditReport."""
        args = _default_args(tmp_path)
        exams, baseline, adapter = self._setup_full_pipeline(args.audit_dir)

        mock_sc = make_scorecard()
        mock_report_path = Path(args.audit_dir) / "audit_report.md"
        mock_report_path.parent.mkdir(parents=True, exist_ok=True)
        mock_report_path.write_text("# Report", encoding="utf-8")

        with (
            patch(
                "src.audit.model_evaluator.compute_scorecard",
                return_value=mock_sc,
            ) as mock_score,
            patch(
                "src.audit.model_evaluator.generate_report",
                return_value=(mock_report_path, AuditReport()),
            ) as mock_report,
        ):
            cmd_score(args)

        assert mock_score.call_count == 4
        mock_report.assert_called_once()

    def test_falls_back_to_sample_when_no_exam_for_scoring(
        self, tmp_path: Path
    ) -> None:
        """Phase 5 can score without an exam file — it falls back to the
        persisted sample using user_prompt as the exam_question."""
        from src.audit.persistence import persist_sample as _ps

        samples = [
            make_sample(id=f"s{i:03d}", reference_standards="std", gap_analysis="gap")
            for i in range(4)
        ]
        args = _default_args(tmp_path)
        _ps(samples, args.audit_dir)

        baseline = [
            InferenceResult(
                record_id=s.id,
                model_name="base",
                response="r",
                latency_ms=100.0,
                token_count=5,
                timestamp="2026-03-03T00:00:00",
            )
            for s in samples
        ]
        adapter = [
            InferenceResult(
                record_id=s.id,
                model_name="ada",
                response="r",
                latency_ms=100.0,
                token_count=5,
                timestamp="2026-03-03T00:00:00",
            )
            for s in samples
        ]
        persist_inference(baseline, "baseline", args.audit_dir)
        persist_inference(adapter, "adapter", args.audit_dir)

        mock_sc = make_scorecard()
        mock_report_path = Path(args.audit_dir) / "report.md"
        mock_report_path.write_text("# Report", encoding="utf-8")

        with (
            patch("src.audit.model_evaluator.compute_scorecard", return_value=mock_sc),
            patch(
                "src.audit.model_evaluator.generate_report",
                return_value=(mock_report_path, AuditReport()),
            ),
        ):
            cmd_score(args)  # must not raise
