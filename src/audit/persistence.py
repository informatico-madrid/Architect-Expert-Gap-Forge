#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""AEGF Audit Persistence — Serialize and deserialize pipeline artifacts.

Single Responsibility: write and read the four intermediate JSON payloads
produced by the evaluation pipeline (sample, exam, inference × 2).

Public API
----------
- ``persist_sample`` / ``load_persisted_sample``
- ``persist_exam``   / ``load_exam``
- ``persist_inference`` / ``load_inference``
"""
from __future__ import annotations

import json
import logging
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from src.audit.schema import ExamRecord, InferenceResult, SampleRecord

__all__ = [
    "persist_sample",
    "load_persisted_sample",
    "persist_exam",
    "load_exam",
    "persist_inference",
    "load_inference",
]

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Sample
# ---------------------------------------------------------------------------


def persist_sample(samples: list[SampleRecord], audit_dir: str) -> Path:
    """Save the evaluation sample to disk for reproducibility.

    Args:
        samples: Drawn sample records.
        audit_dir: Directory where ``eval_sample.json`` will be written.

    Returns:
        Path to the written file.
    """
    out_dir = Path(audit_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    sample_path = out_dir / "eval_sample.json"
    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sample_size": len(samples),
        "type_distribution": dict(Counter(s.example_type for s in samples)),
        "record_ids": [s.id for s in samples],
        "records": [asdict(s) for s in samples],
    }
    sample_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    logger.info("Persisted sample (%d records) → %s", len(samples), sample_path)
    return sample_path


def load_persisted_sample(audit_dir: str) -> list[SampleRecord]:
    """Load a previously-persisted evaluation sample.

    Args:
        audit_dir: Directory containing ``eval_sample.json``.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    sample_path = Path(audit_dir) / "eval_sample.json"
    if not sample_path.exists():
        raise FileNotFoundError(
            f"No persisted sample found at {sample_path}. Run 'sample' mode first."
        )
    payload = json.loads(sample_path.read_text(encoding="utf-8"))
    return [SampleRecord(**rec) for rec in payload["records"]]


# ---------------------------------------------------------------------------
# Exam
# ---------------------------------------------------------------------------


def persist_exam(exam_records: list[ExamRecord], audit_dir: str) -> Path:
    """Save professor-generated exam questions to disk.

    Args:
        exam_records: Generated exam records.
        audit_dir: Directory where ``eval_exam.json`` will be written.

    Returns:
        Path to the written file.
    """
    out_dir = Path(audit_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    exam_path = out_dir / "eval_exam.json"
    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "count": len(exam_records),
        "type_distribution": dict(Counter(r.example_type for r in exam_records)),
        "records": [asdict(r) for r in exam_records],
    }
    exam_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    logger.info("Persisted exam (%d questions) → %s", len(exam_records), exam_path)
    return exam_path


def load_exam(audit_dir: str) -> list[ExamRecord]:
    """Load persisted exam questions.

    Args:
        audit_dir: Directory containing ``eval_exam.json``.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    exam_path = Path(audit_dir) / "eval_exam.json"
    if not exam_path.exists():
        raise FileNotFoundError(
            f"No exam found at {exam_path}. Run 'generate-exam' mode first."
        )
    payload = json.loads(exam_path.read_text(encoding="utf-8"))
    return [ExamRecord(**r) for r in payload["records"]]


# ---------------------------------------------------------------------------
# Inference results
# ---------------------------------------------------------------------------


def persist_inference(
    results: list[InferenceResult],
    label: str,
    audit_dir: str,
) -> Path:
    """Save inference results to disk.

    Args:
        results: Inference results from one model.
        label: Short identifier (``"baseline"`` or ``"adapter"``).
        audit_dir: Directory where ``inference_{label}.json`` will be written.

    Returns:
        Path to the written file.
    """
    out_dir = Path(audit_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"inference_{label}.json"
    payload = {
        "label": label,
        "model": results[0].model_name if results else "unknown",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "count": len(results),
        "results": [asdict(r) for r in results],
    }
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    logger.info("Persisted %d inference results → %s", len(results), out_path)
    return out_path


def load_inference(label: str, audit_dir: str) -> list[InferenceResult]:
    """Load persisted inference results.

    Args:
        label: Short identifier (``"baseline"`` or ``"adapter"``).
        audit_dir: Directory containing ``inference_{label}.json``.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    path = Path(audit_dir) / f"inference_{label}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"No inference results at {path}. Run '{label}' mode first."
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [InferenceResult(**r) for r in payload["results"]]
