#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""AEGF Scorecard — Multi-dimensional LLM-judged evaluation.

This module provides the core scoring logic for the audit pipeline,
computing scorecards from pre-computed judge responses.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from src.audit.schema import (
    SCORING_WEIGHTS,
    ExamRecord,
    ScoreCard,
)
from src.schemas.common import NormalizedJudgeResponse

logger = logging.getLogger(__name__)

# Cache for domain patterns (module-level) - MUST be before function definition
_domain_patterns_cache: dict[str, Any] | None = None


def _extract_code_blocks(text: str) -> str:
    """Extract all code from fenced blocks (markdown)."""
    blocks: list[str] = []
    # Only look for markdown code blocks - no tool_call/write_action tags
    for m in re.finditer(r"```(?:\w+)?\n(.*?)```", text, re.DOTALL):
        blocks.append(m.group(1).strip())
    return "\n\n".join(blocks)


def _load_domain_patterns() -> dict[str, Any]:
    """Lazy-load domain-specific modernity patterns from the YAML taxonomy.

    Returns the parsed contents of ``ha_patterns.yaml``.  On first call the
    file is read; subsequent calls return the cached dict.
    """
    global _domain_patterns_cache
    if _domain_patterns_cache is None:
        from pathlib import Path

        _PATTERNS_CONFIG_PATH = Path("configs/stage_5_evaluation/ha_patterns.yaml")
        import yaml

        if _PATTERNS_CONFIG_PATH.exists():  # pragma: no cover - config file exists in deployment, not in tests
            with open(_PATTERNS_CONFIG_PATH, "r", encoding="utf-8") as fh:
                _domain_patterns_cache = yaml.safe_load(fh) or {}
        else:
            logger.warning(
                "Domain patterns config not found at %s — using empty taxonomy",
                _PATTERNS_CONFIG_PATH,
            )
            _domain_patterns_cache = {}
    return _domain_patterns_cache


def _composite(scores: dict[str, float]) -> float:
    """Compute weighted composite score from dimension scores."""
    return sum(scores.get(dim, 0.0) * weight for dim, weight in SCORING_WEIGHTS.items())


def _grade_label(score: float) -> str:
    """Convert numeric score to letter grade."""
    if score >= 90:
        return "A+"
    if score >= 80:
        return "A"
    if score >= 70:
        return "B"
    if score >= 60:
        return "C"
    if score >= 50:
        return "D"
    return "F"


def _verdict(grade: float) -> str:
    """Return human-readable verdict for the audit."""
    if grade >= 80:
        return "PASS — Adapter demonstrates significant improvement. Safe to merge."
    if grade >= 60:
        return "CONDITIONAL — Adapter shows improvement but gaps remain. Review recommended."
    if grade >= 40:
        return "WARN — Marginal improvement. Additional training or data review needed."
    return "FAIL — Adapter does not meet quality threshold. Do NOT merge."


def compute_scorecard(
    exam: ExamRecord,
    judge_resp: NormalizedJudgeResponse,
    adapter_resp: str | None = None,
) -> ScoreCard:
    """Compute a multi-dimensional LLM-judged scorecard.

    Args:
        exam: The exam record containing target patterns and metadata.
        judge_resp: Pre-computed judge response with baseline and adapter scores.
        adapter_resp: Optional adapter response string for pattern matching.

    Returns:
        ScoreCard with dimension scores, composite, and delta.

    Raises:
        ValueError: If baseline and adapter have different dimension keys.
    """
    # Validate that baseline and adapter have identical dimension keys
    baseline_keys = set(judge_resp.get("baseline", {}).keys())
    adapter_keys = set(judge_resp.get("adapter", {}).keys())

    if baseline_keys != adapter_keys:
        raise ValueError(
            f"Dimension key mismatch: baseline has {baseline_keys}, "
            f"adapter has {adapter_keys}. Both must have identical keys."
        )

    # Work with mutable copies so deterministic corrections do not mutate cached judgment
    a: dict[str, float] = dict(judge_resp["adapter"])
    b: dict[str, float] = dict(judge_resp["baseline"])

    # Extract code blocks for pattern matching if adapter_resp provided
    adapter_code = ""
    if adapter_resp:
        adapter_code = _extract_code_blocks(adapter_resp)

    # --- Deterministic target-pattern coverage penalty ---
    # Applied AFTER the LLM judgment so it cannot be bypassed by <think> labia.
    # For each expected architectural marker absent from the code block, deduct 0.3
    # from ha_modernity and functionality (same penalty the prompt instructs the LLM
    # to apply, but enforced deterministically here as a hard floor).
    target_patterns_list: list[str] = list(exam.target_patterns or [])
    missing_patterns: list[str] = []
    if target_patterns_list and adapter_code:
        missing_patterns = [
            p
            for p in target_patterns_list
            if not re.search(re.escape(p), adapter_code, re.IGNORECASE)
        ]
        if missing_patterns:
            per_pattern_penalty = 0.3
            total_penalty = round(
                min(
                    per_pattern_penalty
                    * len(missing_patterns)
                    / len(target_patterns_list),
                    0.3,
                ),
                3,
            )
            a["ha_modernity"] = round(
                max(0.0, a.get("ha_modernity", 0.0) - total_penalty), 3
            )
            a["functionality"] = round(
                max(0.0, a.get("functionality", 0.0) - total_penalty), 3
            )
            logger.info(
                "  [pattern-penalty] %s: -%.3f on ha_modernity+functionality "
                "(%d/%d markers absent from code: %s)",
                exam.id,
                total_penalty,
                len(missing_patterns),
                len(target_patterns_list),
                missing_patterns,
            )

    adapter_composite = _composite(a)
    baseline_composite = _composite(b)
    delta = adapter_composite - baseline_composite

    # Diagnostic notes: domain taxonomy regex (ha_patterns.yaml) + target_pattern coverage
    notes_parts: list[str] = []
    if adapter_code:
        _patterns = _load_domain_patterns()
        _legacy = [
            (e["pattern"], e["description"])
            for e in _patterns.get("legacy_patterns", [])
        ]
        _modern = [
            (e["pattern"], e["description"])
            for e in _patterns.get("modern_patterns", [])
        ]
        for pat, desc in _legacy:
            if re.search(pat, adapter_code):
                notes_parts.append(f"⚠ Legacy: {desc}")
        for pat, desc in _modern:
            if re.search(pat, adapter_code):
                notes_parts.append(f"✓ Modern: {desc}")
        # Append missing target-pattern fingerprints to notes for report visibility
        for mp in missing_patterns:
            notes_parts.append(f"✗ Missing marker: {mp}")

    return ScoreCard(
        record_id=exam.id,
        sample_id=exam.id,  # Alias for record_id (used by report_writer)
        example_type=exam.example_type,
        fragment_name=exam.fragment_name,
        ha_modernity=round(a.get("ha_modernity", 0.0), 3),
        reasoning_depth=round(a.get("reasoning_depth", 0.0), 3),
        functionality=round(a.get("functionality", 0.0), 3),
        completeness=round(a.get("completeness", 0.0), 3),
        style=round(a.get("style", 0.0), 3),
        composite_score=round(adapter_composite, 3),
        delta_vs_baseline=round(delta, 3),
        judge_reasoning=judge_resp.get("reasoning", ""),
        notes="; ".join(notes_parts[:6]),
    )
