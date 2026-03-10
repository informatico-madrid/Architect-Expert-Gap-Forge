#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Converters between `RawRecord` (TypedDict) and `SampleRecord` (dataclass).

Lightweight, tolerant conversion helpers for incremental migration.
Do not raise errors for missing fields; use sensible default values.
"""

from __future__ import annotations

from typing import Any, Dict, List

from src.schemas.common import RawRecord, NormalizedJudgeResponse, CurationRecord
from src.audit.schema import SampleRecord, SCORING_WEIGHTS


def _clamp01(value: Any) -> float:
    try:
        v = float(value)
    except Exception:
        return 0.0
    return max(0.0, min(1.0, v))


def raw_to_sample(record: RawRecord) -> SampleRecord:
    """Convert a `RawRecord` (dict) to a `SampleRecord`.

    This converter is tolerant: it extracts fields from `metadata` and from
    `conversation` when possible to populate `user_prompt` and
    `reference_response`.
    """
    meta = record.get("metadata", {}) or {}
    conv = record.get("conversation") or record.get("conversations") or []

    user_msg = ""
    asst_msg = ""
    for t in conv:
        if not isinstance(t, dict):
            continue
        role = (t.get("role") or t.get("from") or "").lower()
        content = t.get("content") or t.get("value") or ""
        content = content.strip() if isinstance(content, str) else ""
        if not content:
            continue
        if "user" in role and not user_msg:
            user_msg = content
        if ("assistant" in role or "bot" in role) and not asst_msg:
            asst_msg = content
        if user_msg and asst_msg:
            break

    return SampleRecord(
        id=str(record.get("id") or "unknown"),
        example_type=str(meta.get("example_type", "unknown")),
        evol_difficulty=str(meta.get("evol_difficulty", "unknown")),
        fragment_name=str(meta.get("fragment_name", "")),
        source_file=str(meta.get("source_file", "")),
        user_prompt=user_msg,
        reference_response=asst_msg,
        gold_injected=bool(meta.get("gold_injected", False)),
        ldi=float(meta.get("ldi", 0.0) or 0.0),
        reference_standards=str(meta.get("reference_standards", "")),
        gap_analysis=str(meta.get("gap_analysis", "")),
    )


def sample_to_raw(sample: SampleRecord) -> RawRecord:
    """Convert a `SampleRecord` to a `RawRecord` (TypedDict compatible).

    Useful for JSONL persistence or interoperability with legacy code that
    still expects dicts.
    """
    meta: Dict[str, Any] = {
        "example_type": sample.example_type,
        "evol_difficulty": sample.evol_difficulty,
        "fragment_name": sample.fragment_name,
        "source_file": sample.source_file,
        "gold_injected": sample.gold_injected,
        "ldi": sample.ldi,
        "reference_standards": sample.reference_standards,
        "gap_analysis": sample.gap_analysis,
    }
    conv: list[Dict[str, str]] = []
    if sample.user_prompt:
        conv.append({"role": "user", "content": sample.user_prompt})
    if sample.reference_response:
        conv.append({"role": "assistant", "content": sample.reference_response})

    return {
        "id": sample.id,
        "metadata": meta,
        "conversation": conv,
        "other": {},
    }


def normalize_judge_response(raw: dict) -> NormalizedJudgeResponse:
    """Normalize the judge (LLM) output into `NormalizedJudgeResponse`.

    Ensures the `adapter` and `baseline` sections contain all expected
    dimensions from `SCORING_WEIGHTS` and that values are within 0.0..1.0.
    """
    adapter_raw = raw.get("adapter", {}) or {}
    baseline_raw = raw.get("baseline", {}) or {}

    adapter: dict[str, float] = {}
    baseline: dict[str, float] = {}
    for dim in SCORING_WEIGHTS.keys():
        adapter[dim] = _clamp01(adapter_raw.get(dim, 0.5))
        baseline[dim] = _clamp01(baseline_raw.get(dim, 0.5))

    reasoning = raw.get("reasoning", "") or ""

    return {
        "adapter": adapter,
        "baseline": baseline,
        "reasoning": reasoning,
    }


def curation_raw_to_record(raw: RawRecord) -> CurationRecord:
    """Convert a `RawRecord` to a lightweight `CurationRecord`.

    Extracts a `_text` field (concatenated message text) and an estimated
    `_qs` quality score from `metadata.curation.quality_score` or `_qs`
    if present. Returns a tolerant TypedDict.
    """
    meta = raw.get("metadata", {}) or {}
    conv = raw.get("conversation") or []

    parts: List[str] = []
    if isinstance(conv, list):
        for m in conv:
            if not isinstance(m, dict):
                continue
            content = m.get("content") or m.get("value") or ""
            if content and isinstance(content, str):
                parts.append(content.strip())

    text = "\n\n".join(parts)

    # Try multiple locations for a cached quality score
    qs = 0.5
    try:
        qs = float(
            (meta.get("curation") or {}).get("quality_score", meta.get("_qs", 0.5))
            or 0.5
        )
    except Exception:
        qs = 0.5

    return {
        "record": raw,
        "metadata": meta,
        "_text": text,
        "_qs": max(0.0, min(1.0, qs)),
        "reports": {},
    }


def curation_record_to_raw(curation: CurationRecord) -> RawRecord:
    """Extract the original `RawRecord` from a `CurationRecord`.

    If the `record` key is not present returns a minimal RawRecord.
    """
    rec = curation.get("record") or {}
    # Ensure the result has the minimal expected shape
    return {
        "id": rec.get("id") or "unknown",
        "metadata": rec.get("metadata") or {},
        "conversation": rec.get("conversation") or [],
        "other": rec.get("other") or {},
    }
