#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""Report generation for AEGF audit results.

This module provides functionality to generate comprehensive Markdown audit reports
from evaluation scorecards, including detailed breakdowns by example type,
scoring methodology explanations, and judge reasoning highlights.
"""

from __future__ import annotations

import dataclasses
import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from src.audit.schema import AuditReport, ScoreCard

if TYPE_CHECKING:
    from src.audit.schema import ExamRecord, InferenceResult

logger = logging.getLogger(__name__)


def _get_grade_label(score: float) -> str:
    """Return letter grade for numeric score (0-100)."""
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    if score >= 50:
        return "E"
    return "F"


def _get_verdict(grade: float) -> str:
    """Return human-readable verdict for the audit."""
    if grade >= 80:
        return "PASS — Adapter demonstrates significant improvement. Safe to merge."
    if grade >= 60:
        return "CONDITIONAL — Adapter shows improvement but gaps remain. Review recommended."
    if grade >= 40:
        return "WARN — Marginal improvement. Additional training or data review needed."
    return "FAIL — Adapter does not meet quality threshold. Do NOT merge."


def generate_report(
    report: AuditReport,
    scorecards: list[ScoreCard],
    exam_records: list["ExamRecord"],
    baseline_results: list["InferenceResult"],
    adapter_results: list["InferenceResult"],
    audit_dir: str,
) -> tuple[Path, AuditReport]:
    """Generate a comprehensive Markdown audit report and return the
    path to the written report plus the updated `AuditReport` instance.

    Args:
        report: The audit report instance to populate with results.
        scorecards: List of scorecard evaluations from the judge.
        exam_records: List of exam records used in evaluation.
        baseline_results: List of inference results from baseline model.
        adapter_results: List of inference results from adapter model.
        audit_dir: Directory path to write the report files.

    Returns:
        A tuple of (path to the written markdown report, updated AuditReport).
    """
    out_dir = Path(audit_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    composites = [sc.composite_score for sc in scorecards]
    deltas = [sc.delta_vs_baseline for sc in scorecards]
    final_grade = (sum(composites) / len(composites)) * 100 if composites else 0.0
    avg_delta = sum(deltas) / len(deltas) if deltas else 0.0

    # Group scores by example type
    type_scores: dict[str, list[float]] = defaultdict(list)
    for sc in scorecards:
        # Try to get example_type from dimensions or use a default
        example_type = sc.dimensions.get("example_type", "unknown") if hasattr(sc, "dimensions") else "unknown"
        type_scores[example_type].append(sc.composite_score)

    base_lat = [r.latency_ms for r in baseline_results if hasattr(r, "latency_ms")]
    adapt_lat = [r.latency_ms for r in adapter_results if hasattr(r, "latency_ms")]

    # Update report with computed values
    report = dataclasses.replace(
        report,
        final_grade=round(final_grade, 1),
        verdict=_get_verdict(final_grade),
        scorecards=scorecards,
    )

    # --- Build Markdown ---
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines: list[str] = []
    w = lines.append

    w("# AEGF Quality Gate — High-Fidelity Exam Report")
    w("")
    w(f"> Generated: {ts}")
    w(f"> Dataset: `{report.dataset_path}`")
    w(f"> Base Model: `{report.base_model}`")
    w(f"> Adapter Model: `{report.adapter_model}`")
    w(f"> Judge Model: `{report.judge_model}`")
    w(f"> Sample Size: {report.sample_size}")
    w("> Evaluation: LLM-as-Judge (Professor model) — fail-fast (no fallback)")
    w("")
    w("---")
    w("")

    w(f"## Final Grade: {report.final_grade}/100 ({_get_grade_label(report.final_grade)})")
    w("")
    w(f"**Verdict:** {report.verdict}")
    w("")
    w("| Metric | Value |")
    w("|--------|-------|")
    w(f"| Composite Score (avg) | {report.final_grade:.1f} |")
    w(f"| Avg Δ vs Baseline | {avg_delta:+.3f} |")
    w(f"| Positive Deltas | {sum(1 for d in deltas if d > 0)}/{len(deltas)} |")
    if base_lat:
        w(f"| Baseline Avg Latency | {sum(base_lat) / len(base_lat):.0f}ms |")
    if adapt_lat:
        w(f"| Adapter Avg Latency | {sum(adapt_lat) / len(adapt_lat):.0f}ms |")
    w("")

    w("## Score Breakdown by Example Type")
    w("")
    w("| Type | Count | Avg Score | Avg Δ |")
    w("|------|-------|-----------|-------|")
    for et in sorted(type_scores.keys()):
        scores = type_scores[et]
        # Calculate deltas per example type
        et_deltas = [sc.delta_vs_baseline for sc in scorecards]
        avg_sc = sum(scores) / len(scores) * 100 if scores else 0.0
        avg_d = sum(et_deltas) / len(et_deltas) if et_deltas else 0.0
        w(f"| {et} | {len(scores)} | {avg_sc:.1f} | {avg_d:+.3f} |")
    w("")

    w("## Detailed Scorecards (LLM-as-Judge)")
    w("")
    w(
        "| ID | Type | Fragment | HA Modern | Reasoning | Functional"
        " | Complete | Style | **Composite** | **Δ** |"
    )
    w(
        "|-----|------|----------|-----------|-----------|----------"
        "|----------|-------|---------------|-------|"
    )
    for sc in scorecards:
        # Extract fields from ScoreCard - use direct fields (not dimensions dict)
        sample_id = sc.sample_id
        short_id = sample_id[-12:] if len(sample_id) > 12 else sample_id

        # Get dimension values directly from ScoreCard fields
        ha_modernity = sc.ha_modernity
        reasoning_depth = sc.reasoning_depth
        functionality = sc.functionality
        completeness = sc.completeness
        style = sc.style

        # Fragment name from notes or other available field
        fragment_name = sc.notes[0] if sc.notes else "—"

        w(
            f"| {short_id} | {sc.example_type} | {fragment_name[:25]} "
            f"| {ha_modernity:.2f} | {reasoning_depth:.2f} "
            f"| {functionality:.2f} | {completeness:.2f} "
            f"| {style:.2f} | **{sc.composite_score:.3f}** "
            f"| {sc.delta_vs_baseline:+.3f} |"
        )
    w("")

    w("## Scoring Methodology (LLM-as-Judge)")
    w("")
    w(
        f"The Professor model (`{report.judge_model}`) scores each exam response across 5 dimensions:"
    )
    w("")
    w("| Dimension | Weight | Description |")
    w("|-----------|--------|-------------|")
    w(
        "| HA Modernity | 30% | Uses entry.runtime_data, plural setup, enum device classes |"
    )
    w(
        "| Reasoning Depth | 25% | `<think>` block correctly identifies edge cases and migration paths |"
    )
    w("| Functionality | 25% | Code compiles and runs correctly in Home Assistant |")
    w("| Completeness | 12% | All required functions/classes implemented |")
    w("| Style | 8% | AEGF conventions: `<think>` present, docstrings, no apologies |")
    w("")
    w("**Composite** = Σ(dimension × weight). **Δ** = adapter − baseline composite.")
    w("No regex fallback: judge failures abort the audit.")
    w("")

    # Judge reasoning highlights
    judged = [sc for sc in scorecards if sc.notes and len(sc.notes) > 1]
    if judged:
        w("## Judge Reasoning Highlights")
        w("")
        for sc in judged[:8]:
            short_id = sc.sample_id[-12:] if len(sc.sample_id) > 12 else sc.sample_id
            fragment = sc.notes[0] if sc.notes else "—"
            reasoning = sc.notes[1] if len(sc.notes) > 1 else ""
            w(f"**{short_id}** ({fragment}):")
            w(f"> {reasoning}")
            w("")

    # Regex pattern detection notes
    flagged = [sc for sc in scorecards if sc.notes and len(sc.notes) > 2]
    if flagged:
        w("## Regex Pattern Detection Notes")
        w("")
        for sc in flagged:
            note = sc.notes[2] if len(sc.notes) > 2 else ""
            w(f"- **{sc.sample_id}** ({sc.notes[0] if sc.notes else '—'}): {note}")
        w("")

    w("---")
    w("")
    w(
        "*Report generated by `src/audit/model_evaluator.py` — AEGF Quality Gate v3.0 (LLM-as-Judge)*"
    )

    report_path = out_dir / "audit_report_v11.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Audit report written → %s", report_path)

    json_path = out_dir / "audit_report_v11.json"
    json_path.write_text(
        json.dumps(report.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("Structured report → %s", json_path)

    return report_path, report
