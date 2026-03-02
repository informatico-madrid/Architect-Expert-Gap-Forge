#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""AEGF Model Evaluator — Quality Gate between Training and Merger.

Automated dual-inference evaluation pipeline that compares a base model against
a LoRA-tuned adapter using a stratified sample from the training dataset.

Modes
-----
  sample   — Extract a balanced sample from the dataset and persist it.
  baseline — Run inference with the base model on the persisted sample.
  adapter  — Run inference with the LoRA adapter on the persisted sample.
  score    — Score adapter vs baseline responses and emit audit report.
  full     — Execute sample → baseline → adapter → score in sequence.

Usage
-----
  # Step 1: Extract sample (idempotent — reuses existing sample)
  python -m src.audit.model_evaluator sample \\
      --dataset data/synthetic/v11_PLATINUM_UNIFORM.jsonl

  # Step 2: Baseline inference (uses base model)
  python -m src.audit.model_evaluator baseline \\
      --model qwen3-30b-a3b-thinking-fp8

  # Step 3: Adapter inference (uses LoRA adapter)
  python -m src.audit.model_evaluator adapter \\
      --model platinum_adapter

  # Step 4: Generate comparative report
  python -m src.audit.model_evaluator score

  # Or run everything end-to-end
  python -m src.audit.model_evaluator full \\
      --dataset data/synthetic/v11_PLATINUM_UNIFORM.jsonl \\
      --base-model qwen3-30b-a3b-thinking-fp8 \\
      --adapter-model platinum_adapter

Environment
-----------
  AEGF_VLLM_API_URL     vLLM endpoint  (default: http://localhost:8000/v1)
  AEGF_AUDIT_DIR        Output folder  (default: data/audit)
  AEGF_SAMPLE_SIZE      Records/sample (default: 20)
  AEGF_BASE_MODEL       Base model id  (default: qwen3-30b-a3b-thinking-fp8)
  AEGF_ADAPTER_MODEL    Adapter model  (default: platinum_adapter)
  AEGF_MAX_TOKENS       Max gen tokens (default: 4096)
  AEGF_TEMPERATURE      Sampling temp  (default: 0.3)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import random
import re
import sys
import textwrap
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Config & Constants
# ---------------------------------------------------------------------------

load_dotenv()

LOGGER_NAME = "AEGF.Evaluator"
logger = logging.getLogger(LOGGER_NAME)

# Canonical example types in the AEGF dataset
EXAMPLE_TYPES = ["nominal", "contrast", "error_recovery", "theory"]

# Default inference parameters
DEFAULT_API_URL = os.getenv("AEGF_VLLM_API_URL", "http://localhost:8000/v1")
DEFAULT_AUDIT_DIR = os.getenv("AEGF_AUDIT_DIR", "data/audit")
DEFAULT_SAMPLE_SIZE = int(os.getenv("AEGF_SAMPLE_SIZE", "5"))
DEFAULT_BASE_MODEL = os.getenv("AEGF_BASE_MODEL", "qwen3-30b-a3b-thinking-fp8")
DEFAULT_ADAPTER_MODEL = os.getenv("AEGF_ADAPTER_MODEL", "platinum_adapter")
DEFAULT_MAX_TOKENS = int(os.getenv("AEGF_MAX_TOKENS", "4096"))
DEFAULT_TEMPERATURE = float(os.getenv("AEGF_TEMPERATURE", "0.3"))

# Scoring weights per dimension
SCORING_WEIGHTS = {
    "structural_fidelity": 0.30,
    "api_modernity": 0.25,
    "reasoning_depth": 0.20,
    "completeness": 0.15,
    "style_consistency": 0.10,
}

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class SampleRecord:
    """A single evaluation record extracted from the training dataset."""

    id: str
    example_type: str
    evol_difficulty: str
    fragment_name: str
    source_file: str
    user_prompt: str
    reference_response: str
    gold_injected: bool
    ldi: float


@dataclass
class InferenceResult:
    """Model response for a single sample record."""

    record_id: str
    model_name: str
    response: str
    latency_ms: float
    token_count: int
    timestamp: str


@dataclass
class ScoreCard:
    """Multi-dimensional score for a single record comparison."""

    record_id: str
    example_type: str
    fragment_name: str
    structural_fidelity: float = 0.0
    api_modernity: float = 0.0
    reasoning_depth: float = 0.0
    completeness: float = 0.0
    style_consistency: float = 0.0
    composite_score: float = 0.0
    delta_vs_baseline: float = 0.0
    notes: str = ""


@dataclass
class AuditReport:
    """Top-level audit report aggregating all evaluation results."""

    timestamp: str = ""
    dataset_path: str = ""
    base_model: str = ""
    adapter_model: str = ""
    sample_size: int = 0
    type_distribution: Dict[str, int] = field(default_factory=dict)
    scorecards: List[ScoreCard] = field(default_factory=list)
    final_grade: float = 0.0
    verdict: str = ""


# ---------------------------------------------------------------------------
# Sampling
# ---------------------------------------------------------------------------


def load_dataset(path: str) -> List[Dict[str, Any]]:
    """Load a JSONL dataset into memory."""
    records: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                logger.warning("Skipping malformed line %d: %s", line_no, exc)
    logger.info("Loaded %d records from %s", len(records), path)
    return records


def stratified_sample(
    records: List[Dict[str, Any]],
    sample_size: int = DEFAULT_SAMPLE_SIZE,
    seed: int = 42,
) -> List[SampleRecord]:
    """Extract a balanced sample stratified by example_type.

    Allocation strategy:
    - Divide ``sample_size`` equally across present example types.
    - Remaining slots fill from largest buckets first.
    - Types with fewer records than their quota donate surplus to others.
    """
    rng = random.Random(seed)

    # Bucket by example_type
    buckets: Dict[str, List[Dict]] = defaultdict(list)
    for rec in records:
        et = rec.get("metadata", {}).get("example_type", "unknown")
        buckets[et] = buckets.get(et, [])
        buckets[et].append(rec)

    # Sort type names for determinism
    present_types = sorted(buckets.keys())
    n_types = len(present_types)
    base_quota = sample_size // n_types
    remainder = sample_size % n_types

    # First pass — allocate base quota (capped by bucket size)
    allocation: Dict[str, int] = {}
    surplus = 0
    for et in present_types:
        avail = len(buckets[et])
        alloc = min(base_quota, avail)
        allocation[et] = alloc
        surplus += base_quota - alloc

    # Second pass — distribute surplus + remainder to largest buckets
    leftover = surplus + remainder
    for et in sorted(present_types, key=lambda t: len(buckets[t]), reverse=True):
        if leftover <= 0:
            break
        can_add = len(buckets[et]) - allocation[et]
        add = min(can_add, leftover)
        allocation[et] += add
        leftover -= add

    # Draw samples
    samples: List[SampleRecord] = []
    for et in present_types:
        pool = buckets[et]
        rng.shuffle(pool)
        for rec in pool[: allocation[et]]:
            meta = rec.get("metadata", {})
            conv = rec.get("conversation", [])
            user_msg = next(
                (t["content"] for t in conv if t.get("role") == "user"), ""
            )
            asst_msg = next(
                (t["content"] for t in conv if t.get("role") == "assistant"), ""
            )
            samples.append(
                SampleRecord(
                    id=rec.get("id", f"unknown_{len(samples)}"),
                    example_type=et,
                    evol_difficulty=meta.get("evol_difficulty", "unknown"),
                    fragment_name=meta.get("fragment_name", ""),
                    source_file=meta.get("source_file", ""),
                    user_prompt=user_msg,
                    reference_response=asst_msg,
                    gold_injected=meta.get("gold_injected", False),
                    ldi=meta.get("ldi", 0.0),
                )
            )

    logger.info(
        "Sampled %d records — distribution: %s",
        len(samples),
        {et: allocation[et] for et in present_types},
    )
    return samples


def persist_sample(samples: List[SampleRecord], audit_dir: str) -> Path:
    """Save the evaluation sample to disk for reproducibility."""
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


def load_persisted_sample(audit_dir: str) -> List[SampleRecord]:
    """Load a previously-persisted evaluation sample."""
    sample_path = Path(audit_dir) / "eval_sample.json"
    if not sample_path.exists():
        raise FileNotFoundError(
            f"No persisted sample found at {sample_path}. Run 'sample' mode first."
        )
    payload = json.loads(sample_path.read_text(encoding="utf-8"))
    samples = [SampleRecord(**rec) for rec in payload["records"]]
    logger.info("Loaded persisted sample: %d records", len(samples))
    return samples


# ---------------------------------------------------------------------------
# Inference Engine
# ---------------------------------------------------------------------------


def call_vllm(
    prompt: str,
    model: str,
    api_url: str = DEFAULT_API_URL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = DEFAULT_TEMPERATURE,
) -> InferenceResult:
    """Send a chat completion request to the vLLM OpenAI-compatible API."""
    url = f"{api_url}/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": 0.95,
    }

    t0 = time.perf_counter()
    try:
        resp = requests.post(url, json=payload, timeout=300)
        resp.raise_for_status()
    except requests.exceptions.ConnectionError:
        logger.error(
            "Cannot reach vLLM API at %s. Is the server running?", api_url
        )
        raise SystemExit(1)
    except requests.exceptions.HTTPError as exc:
        logger.error("vLLM API error: %s — %s", exc, resp.text[:500])
        raise
    latency = (time.perf_counter() - t0) * 1000

    data = resp.json()
    choice = data["choices"][0]
    content = choice["message"]["content"]
    usage = data.get("usage", {})
    token_count = usage.get("completion_tokens", len(content.split()))

    return InferenceResult(
        record_id="",
        model_name=model,
        response=content,
        latency_ms=round(latency, 1),
        token_count=token_count,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def run_inference(
    samples: List[SampleRecord],
    model: str,
    api_url: str = DEFAULT_API_URL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = DEFAULT_TEMPERATURE,
) -> List[InferenceResult]:
    """Run inference on all sample records against a given model."""
    results: List[InferenceResult] = []
    total = len(samples)

    for idx, sample in enumerate(samples, 1):
        logger.info(
            "[%d/%d] Inferring %s (type=%s, frag=%s) with model=%s",
            idx,
            total,
            sample.id,
            sample.example_type,
            sample.fragment_name,
            model,
        )
        result = call_vllm(
            prompt=sample.user_prompt,
            model=model,
            api_url=api_url,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        result.record_id = sample.id
        results.append(result)
        logger.info(
            "  → %d tokens in %.0fms", result.token_count, result.latency_ms
        )

    return results


def persist_inference(
    results: List[InferenceResult], label: str, audit_dir: str
) -> Path:
    """Save inference results to disk."""
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


def load_inference(label: str, audit_dir: str) -> List[InferenceResult]:
    """Load persisted inference results."""
    path = Path(audit_dir) / f"inference_{label}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"No inference results at {path}. Run '{label}' mode first."
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [InferenceResult(**r) for r in payload["results"]]


# ---------------------------------------------------------------------------
# Scoring Engine
# ---------------------------------------------------------------------------


def _extract_code_blocks(text: str) -> str:
    """Extract all code from fenced blocks or <tool_call>/<write_action> tags."""
    blocks: List[str] = []
    # Fenced code blocks
    for m in re.finditer(r"```(?:\w+)?\n(.*?)```", text, re.DOTALL):
        blocks.append(m.group(1).strip())
    # <tool_call> / <write_action> blocks
    for tag in ("tool_call", "write_action"):
        for m in re.finditer(
            rf"<{tag}>(.*?)</{tag}>", text, re.DOTALL
        ):
            blocks.append(m.group(1).strip())
    return "\n".join(blocks) if blocks else text


def _extract_think_block(text: str) -> str:
    """Extract reasoning from <think> tags."""
    m = re.search(r"<think>(.*?)</think>", text, re.DOTALL)
    return m.group(1).strip() if m else ""


# --- Legacy / modernity detection patterns ---

LEGACY_PATTERNS = [
    (r"\bhass\.data\b", "hass.data (should use entry.runtime_data)"),
    (r"\basync_forward_entry_setup\b(?!s)", "singular async_forward_entry_setup"),
    (r"\bSENSOR_DEVICE_CLASS_", "old SENSOR_DEVICE_CLASS_ constants"),
    (r"\bUNIT_", "old UNIT_ string constants"),
    (r"\bENTITY_CATEGORY_", "old ENTITY_CATEGORY_ string constants"),
    (r"\bDEVICE_CLASS_", "old DEVICE_CLASS_ string constants"),
    (r"yield from\s+hass\.config_entries", "yield from config_entries (legacy)"),
    (r"\bplatform\.async_register_entity_service\b", "platform.async_register (deprecated)"),
]

MODERN_PATTERNS = [
    (r"\bentry\.runtime_data\b", "entry.runtime_data"),
    (r"\basync_forward_entry_setups\b", "async_forward_entry_setups (plural)"),
    (r"\bSensorDeviceClass\b", "SensorDeviceClass enum"),
    (r"\bUnitOfTemperature\b", "UnitOfTemperature enum"),
    (r"\bEntityCategory\b", "EntityCategory enum"),
    (r"\bConfigEntryNotReady\b", "ConfigEntryNotReady exception"),
    (r"\bConfigEntryAuthFailed\b", "ConfigEntryAuthFailed exception"),
    (r"\bUpdateFailed\b", "UpdateFailed exception"),
    (r"\bDataUpdateCoordinator\b", "DataUpdateCoordinator pattern"),
    (r"\bCoordinatorEntity\b", "CoordinatorEntity pattern"),
]


def score_structural_fidelity(response: str, reference: str) -> float:
    """Measure code-level similarity between response and reference."""
    resp_code = _extract_code_blocks(response)
    ref_code = _extract_code_blocks(reference)
    if not ref_code:
        return 0.5  # No reference code to compare
    return SequenceMatcher(None, resp_code, ref_code).ratio()


def score_api_modernity(response: str) -> float:
    """Score usage of modern HA 2026 APIs vs legacy patterns."""
    code = _extract_code_blocks(response)
    if not code:
        return 0.5

    legacy_hits = sum(
        1 for pat, _ in LEGACY_PATTERNS if re.search(pat, code)
    )
    modern_hits = sum(
        1 for pat, _ in MODERN_PATTERNS if re.search(pat, code)
    )
    total = legacy_hits + modern_hits
    if total == 0:
        return 0.5
    return modern_hits / total


def score_reasoning_depth(response: str) -> float:
    """Evaluate reasoning quality inside <think> blocks."""
    think = _extract_think_block(response)
    if not think:
        return 0.0

    # Score by reasoning indicators
    indicators = [
        r"\b(because|therefore|since|given that)\b",
        r"\b(step \d|first|second|third|finally)\b",
        r"\b(import|from\s+\w+\s+import)\b",
        r"\b(edge case|error handling|exception)\b",
        r"\b(async|await|coordinator|runtime_data)\b",
    ]
    hits = sum(1 for p in indicators if re.search(p, think, re.IGNORECASE))
    # Normalize: >4 indicators = perfect
    raw = min(hits / 4.0, 1.0)

    # Penalize very short or extremely long (loop) reasoning
    words = len(think.split())
    if words < 20:
        raw *= 0.5
    elif words > 3000:
        raw *= 0.7  # Likely cognitive loop

    return round(raw, 3)


def score_completeness(response: str, reference: str) -> float:
    """Check that the response covers all key elements from the reference."""
    ref_code = _extract_code_blocks(reference)
    # Extract function/class names from reference as coverage targets
    targets = set(re.findall(r"\b(?:def|class|async def)\s+(\w+)", ref_code))
    if not targets:
        return 0.5

    resp_code = _extract_code_blocks(response)
    hits = sum(1 for t in targets if t in resp_code)
    return hits / len(targets)


def score_style_consistency(response: str) -> float:
    """Check for AEGF-expected structural conventions."""
    checks = {
        "has_think": bool(re.search(r"<think>", response)),
        "has_action": bool(
            re.search(r"<tool_call>|<write_action>|```python", response)
        ),
        "no_apology": not bool(
            re.search(
                r"(?:I'm sorry|I cannot|I don't|As an AI)", response, re.IGNORECASE
            )
        ),
        "has_docstring": bool(re.search(r'""".*?"""', response, re.DOTALL)),
    }
    return sum(checks.values()) / len(checks)


def compute_scorecard(
    sample: SampleRecord,
    baseline_resp: str,
    adapter_resp: str,
) -> ScoreCard:
    """Compute a multi-dimensional scorecard comparing adapter vs baseline."""
    reference = sample.reference_response

    # Adapter scores
    s_fidelity = score_structural_fidelity(adapter_resp, reference)
    s_modernity = score_api_modernity(adapter_resp)
    s_reasoning = score_reasoning_depth(adapter_resp)
    s_complete = score_completeness(adapter_resp, reference)
    s_style = score_style_consistency(adapter_resp)

    composite = (
        s_fidelity * SCORING_WEIGHTS["structural_fidelity"]
        + s_modernity * SCORING_WEIGHTS["api_modernity"]
        + s_reasoning * SCORING_WEIGHTS["reasoning_depth"]
        + s_complete * SCORING_WEIGHTS["completeness"]
        + s_style * SCORING_WEIGHTS["style_consistency"]
    )

    # Baseline composite for delta
    b_fidelity = score_structural_fidelity(baseline_resp, reference)
    b_modernity = score_api_modernity(baseline_resp)
    b_reasoning = score_reasoning_depth(baseline_resp)
    b_complete = score_completeness(baseline_resp, reference)
    b_style = score_style_consistency(baseline_resp)
    baseline_composite = (
        b_fidelity * SCORING_WEIGHTS["structural_fidelity"]
        + b_modernity * SCORING_WEIGHTS["api_modernity"]
        + b_reasoning * SCORING_WEIGHTS["reasoning_depth"]
        + b_complete * SCORING_WEIGHTS["completeness"]
        + b_style * SCORING_WEIGHTS["style_consistency"]
    )

    delta = composite - baseline_composite

    # Build notes about detected problems
    notes_parts: List[str] = []
    adapter_code = _extract_code_blocks(adapter_resp)
    for pat, desc in LEGACY_PATTERNS:
        if re.search(pat, adapter_code):
            notes_parts.append(f"⚠ Legacy: {desc}")
    for pat, desc in MODERN_PATTERNS:
        if re.search(pat, adapter_code):
            notes_parts.append(f"✓ Modern: {desc}")

    return ScoreCard(
        record_id=sample.id,
        example_type=sample.example_type,
        fragment_name=sample.fragment_name,
        structural_fidelity=round(s_fidelity, 3),
        api_modernity=round(s_modernity, 3),
        reasoning_depth=round(s_reasoning, 3),
        completeness=round(s_complete, 3),
        style_consistency=round(s_style, 3),
        composite_score=round(composite, 3),
        delta_vs_baseline=round(delta, 3),
        notes="; ".join(notes_parts[:5]),  # Cap notes length
    )


# ---------------------------------------------------------------------------
# Report Generation
# ---------------------------------------------------------------------------


def _grade_label(score: float) -> str:
    """Convert numeric score to letter grade."""
    if score >= 90:
        return "A+"
    elif score >= 80:
        return "A"
    elif score >= 70:
        return "B"
    elif score >= 60:
        return "C"
    elif score >= 50:
        return "D"
    return "F"


def _verdict(grade: float) -> str:
    """Return human-readable verdict for the audit."""
    if grade >= 80:
        return "PASS — Adapter demonstrates significant improvement. Safe to merge."
    elif grade >= 60:
        return "CONDITIONAL — Adapter shows improvement but gaps remain. Review recommended."
    elif grade >= 40:
        return "WARN — Marginal improvement. Additional training or data review needed."
    return "FAIL — Adapter does not meet quality threshold. Do NOT merge."


def generate_report(
    report: AuditReport,
    scorecards: List[ScoreCard],
    samples: List[SampleRecord],
    baseline_results: List[InferenceResult],
    adapter_results: List[InferenceResult],
    audit_dir: str,
) -> Path:
    """Generate a comprehensive Markdown audit report."""
    out_dir = Path(audit_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Compute aggregates
    composites = [sc.composite_score for sc in scorecards]
    deltas = [sc.delta_vs_baseline for sc in scorecards]
    final_grade = (sum(composites) / len(composites)) * 100 if composites else 0.0
    avg_delta = sum(deltas) / len(deltas) if deltas else 0.0

    # Per-type breakdown
    type_scores: Dict[str, List[float]] = defaultdict(list)
    for sc in scorecards:
        type_scores[sc.example_type].append(sc.composite_score)

    # Latency stats
    base_lat = [r.latency_ms for r in baseline_results]
    adapt_lat = [r.latency_ms for r in adapter_results]

    report.final_grade = round(final_grade, 1)
    report.verdict = _verdict(final_grade)
    report.scorecards = scorecards

    # --- Build Markdown ---
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines: List[str] = []
    w = lines.append

    w(f"# AEGF Quality Gate — Audit Report")
    w(f"")
    w(f"> Generated: {ts}")
    w(f"> Dataset: `{report.dataset_path}`")
    w(f"> Base Model: `{report.base_model}`")
    w(f"> Adapter Model: `{report.adapter_model}`")
    w(f"> Sample Size: {report.sample_size}")
    w(f"")
    w(f"---")
    w(f"")

    # Final Grade
    w(f"## Final Grade: {report.final_grade}/100 ({_grade_label(report.final_grade)})")
    w(f"")
    w(f"**Verdict:** {report.verdict}")
    w(f"")
    w(f"| Metric | Value |")
    w(f"|--------|-------|")
    w(f"| Composite Score (avg) | {report.final_grade:.1f} |")
    w(f"| Avg Δ vs Baseline | {avg_delta:+.3f} |")
    w(f"| Positive Deltas | {sum(1 for d in deltas if d > 0)}/{len(deltas)} |")
    w(f"| Baseline Avg Latency | {sum(base_lat)/len(base_lat):.0f}ms |") if base_lat else None
    w(f"| Adapter Avg Latency | {sum(adapt_lat)/len(adapt_lat):.0f}ms |") if adapt_lat else None
    w(f"")

    # Per-type breakdown
    w(f"## Score Breakdown by Example Type")
    w(f"")
    w(f"| Type | Count | Avg Score | Avg Δ |")
    w(f"|------|-------|-----------|-------|")
    for et in sorted(type_scores.keys()):
        scores = type_scores[et]
        et_deltas = [
            sc.delta_vs_baseline
            for sc in scorecards
            if sc.example_type == et
        ]
        avg_sc = sum(scores) / len(scores) * 100
        avg_d = sum(et_deltas) / len(et_deltas) if et_deltas else 0.0
        w(f"| {et} | {len(scores)} | {avg_sc:.1f} | {avg_d:+.3f} |")
    w(f"")

    # Detailed scorecards table
    w(f"## Detailed Scorecards")
    w(f"")
    w(
        f"| ID | Type | Fragment | Structural | Modernity | Reasoning "
        f"| Complete | Style | **Composite** | **Δ** |"
    )
    w(
        f"|-----|------|----------|-----------|-----------|----------"
        f"|----------|-------|---------------|-------|"
    )
    for sc in scorecards:
        short_id = sc.record_id[-12:] if len(sc.record_id) > 12 else sc.record_id
        frag = sc.fragment_name[:25] if sc.fragment_name else "—"
        w(
            f"| {short_id} | {sc.example_type} | {frag} "
            f"| {sc.structural_fidelity:.2f} | {sc.api_modernity:.2f} "
            f"| {sc.reasoning_depth:.2f} | {sc.completeness:.2f} "
            f"| {sc.style_consistency:.2f} | **{sc.composite_score:.3f}** "
            f"| {sc.delta_vs_baseline:+.3f} |"
        )
    w(f"")

    # Scoring methodology
    w(f"## Scoring Methodology")
    w(f"")
    w(f"Each record is scored across 5 dimensions with the following weights:")
    w(f"")
    w(f"| Dimension | Weight | Description |")
    w(f"|-----------|--------|-------------|")
    w(f"| Structural Fidelity | 30% | Code similarity to gold reference (SequenceMatcher) |")
    w(f"| API Modernity | 25% | Ratio of modern HA 2026 patterns vs legacy patterns |")
    w(f"| Reasoning Depth | 20% | Quality and depth of `<think>` block analysis |")
    w(f"| Completeness | 15% | Coverage of all functions/classes from reference |")
    w(f"| Style Consistency | 10% | Adherence to AEGF structural conventions |")
    w(f"")
    w(f"**Composite** = Σ(dimension × weight). **Δ** = adapter_composite − baseline_composite.")
    w(f"")

    # Notes / pattern detection
    flagged = [sc for sc in scorecards if sc.notes]
    if flagged:
        w(f"## Pattern Detection Notes")
        w(f"")
        for sc in flagged:
            w(f"- **{sc.record_id}** ({sc.fragment_name}): {sc.notes}")
        w(f"")

    # Weight table for scoring
    w(f"---")
    w(f"")
    w(f"*Report generated by `src/audit/model_evaluator.py` — AEGF Quality Gate v1.0*")

    # Write report
    report_path = out_dir / "audit_report_v11.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Audit report written → %s", report_path)

    # Also persist structured JSON
    json_path = out_dir / "audit_report_v11.json"
    json_path.write_text(
        json.dumps(asdict(report), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("Structured report → %s", json_path)

    return report_path


# ---------------------------------------------------------------------------
# CLI Orchestration
# ---------------------------------------------------------------------------


def cmd_sample(args: argparse.Namespace) -> None:
    """Extract and persist a stratified evaluation sample."""
    sample_path = Path(args.audit_dir) / "eval_sample.json"
    if sample_path.exists() and not args.force:
        logger.info(
            "Sample already exists at %s (use --force to regenerate)", sample_path
        )
        samples = load_persisted_sample(args.audit_dir)
    else:
        records = load_dataset(args.dataset)
        samples = stratified_sample(records, args.sample_size)
        persist_sample(samples, args.audit_dir)

    dist = Counter(s.example_type for s in samples)
    logger.info("Sample distribution: %s", dict(dist))


def cmd_baseline(args: argparse.Namespace) -> None:
    """Run baseline inference with the base model."""
    samples = load_persisted_sample(args.audit_dir)
    results = run_inference(
        samples,
        model=args.model or args.base_model,
        api_url=args.api_url,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
    )
    persist_inference(results, "baseline", args.audit_dir)


def cmd_adapter(args: argparse.Namespace) -> None:
    """Run adapter inference with the LoRA-tuned model."""
    samples = load_persisted_sample(args.audit_dir)
    results = run_inference(
        samples,
        model=args.model or args.adapter_model,
        api_url=args.api_url,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
    )
    persist_inference(results, "adapter", args.audit_dir)


def cmd_score(args: argparse.Namespace) -> None:
    """Score adapter vs baseline and generate the audit report."""
    samples = load_persisted_sample(args.audit_dir)
    baseline_results = load_inference("baseline", args.audit_dir)
    adapter_results = load_inference("adapter", args.audit_dir)

    # Build lookup maps
    baseline_map = {r.record_id: r for r in baseline_results}
    adapter_map = {r.record_id: r for r in adapter_results}

    scorecards: List[ScoreCard] = []
    for sample in samples:
        base_r = baseline_map.get(sample.id)
        adapt_r = adapter_map.get(sample.id)
        if not base_r or not adapt_r:
            logger.warning("Missing inference for %s — skipping", sample.id)
            continue
        sc = compute_scorecard(sample, base_r.response, adapt_r.response)
        scorecards.append(sc)

    report = AuditReport(
        timestamp=datetime.now(timezone.utc).isoformat(),
        dataset_path=args.dataset or "N/A",
        base_model=baseline_results[0].model_name if baseline_results else "N/A",
        adapter_model=adapter_results[0].model_name if adapter_results else "N/A",
        sample_size=len(samples),
        type_distribution=dict(Counter(s.example_type for s in samples)),
        scorecards=scorecards,
    )

    report_path = generate_report(
        report, scorecards, samples, baseline_results, adapter_results, args.audit_dir
    )
    print(f"\n{'='*60}")
    print(f"  AEGF QUALITY GATE — FINAL GRADE: {report.final_grade}/100")
    print(f"  Verdict: {report.verdict}")
    print(f"  Report: {report_path}")
    print(f"{'='*60}\n")


def cmd_full(args: argparse.Namespace) -> None:
    """Run the full evaluation pipeline: sample → baseline → adapter → score."""
    logger.info("=== AEGF Quality Gate — Full Pipeline ===")

    # Step 1: Sample
    logger.info("--- Phase 1/4: Sampling ---")
    cmd_sample(args)

    # Step 2: Baseline
    logger.info("--- Phase 2/4: Baseline Inference ---")
    args.model = args.base_model
    cmd_baseline(args)

    # Step 3: Adapter
    logger.info("--- Phase 3/4: Adapter Inference ---")
    args.model = args.adapter_model
    cmd_adapter(args)

    # Step 4: Score
    logger.info("--- Phase 4/4: Scoring & Report ---")
    cmd_score(args)


def _shared_parser() -> argparse.ArgumentParser:
    """Build a parent parser with all shared options (used by every subcommand)."""
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help=f"vLLM API endpoint (default: {DEFAULT_API_URL})",
    )
    shared.add_argument(
        "--audit-dir",
        default=DEFAULT_AUDIT_DIR,
        help=f"Output directory for audit artifacts (default: {DEFAULT_AUDIT_DIR})",
    )
    shared.add_argument(
        "--dataset",
        default=None,
        help="Path to the training JSONL dataset",
    )
    shared.add_argument(
        "--model",
        default=None,
        help="Model name to use for inference (overrides base/adapter defaults)",
    )
    shared.add_argument(
        "--base-model",
        default=DEFAULT_BASE_MODEL,
        help=f"Base model identifier (default: {DEFAULT_BASE_MODEL})",
    )
    shared.add_argument(
        "--adapter-model",
        default=DEFAULT_ADAPTER_MODEL,
        help=f"LoRA adapter identifier (default: {DEFAULT_ADAPTER_MODEL})",
    )
    shared.add_argument(
        "--sample-size",
        type=int,
        default=DEFAULT_SAMPLE_SIZE,
        help=f"Number of records to sample (default: {DEFAULT_SAMPLE_SIZE})",
    )
    shared.add_argument(
        "--max-tokens",
        type=int,
        default=DEFAULT_MAX_TOKENS,
        help=f"Max generation tokens (default: {DEFAULT_MAX_TOKENS})",
    )
    shared.add_argument(
        "--temperature",
        type=float,
        default=DEFAULT_TEMPERATURE,
        help=f"Sampling temperature (default: {DEFAULT_TEMPERATURE})",
    )
    shared.add_argument(
        "--force",
        action="store_true",
        help="Force regeneration of existing artifacts",
    )
    shared.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    return shared


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser.

    All options are defined in a shared parent parser so they can appear
    either before or after the subcommand name::

        # Both forms are equivalent:
        model_evaluator --dataset foo.jsonl full
        model_evaluator full --dataset foo.jsonl
    """
    shared = _shared_parser()

    parser = argparse.ArgumentParser(
        prog="model_evaluator",
        description="AEGF Quality Gate — Dual-inference model evaluation pipeline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[shared],
        epilog=textwrap.dedent("""\
            Examples:
              %(prog)s sample   --dataset data/synthetic/v11_PLATINUM_UNIFORM.jsonl
              %(prog)s baseline --model qwen3-30b-a3b-thinking-fp8
              %(prog)s adapter  --model platinum_adapter
              %(prog)s score
              %(prog)s full     --dataset data/synthetic/v11_PLATINUM_UNIFORM.jsonl \\
                                --base-model qwen3-30b-a3b-thinking-fp8 \\
                                --adapter-model platinum_adapter
        """),
    )

    # Subcommands — each inherits all shared options via parents=[shared]
    sub = parser.add_subparsers(dest="mode", help="Evaluation mode")
    sub.add_parser(
        "sample",
        help="Extract stratified sample from dataset",
        parents=[shared],
    )
    sub.add_parser(
        "baseline",
        help="Run baseline inference (base model)",
        parents=[shared],
    )
    sub.add_parser(
        "adapter",
        help="Run adapter inference (LoRA model)",
        parents=[shared],
    )
    sub.add_parser(
        "score",
        help="Score and generate audit report",
        parents=[shared],
    )
    sub.add_parser(
        "full",
        help="Run complete pipeline end-to-end",
        parents=[shared],
    )

    return parser


def main() -> None:
    """Entry point for the AEGF Quality Gate evaluator."""
    parser = build_parser()
    args = parser.parse_args()

    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s │ %(name)s │ %(levelname)s │ %(message)s",
        datefmt="%H:%M:%S",
    )

    if not args.mode:
        parser.print_help()
        sys.exit(1)

    dispatch = {
        "sample": cmd_sample,
        "baseline": cmd_baseline,
        "adapter": cmd_adapter,
        "score": cmd_score,
        "full": cmd_full,
    }

    handler = dispatch.get(args.mode)
    if handler:
        handler(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
