#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
AEGF Exam Builder Module
========================
Builds exam questions from evaluation samples.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

import yaml

from src.audit.config import (
    DEFAULT_API_URL,
    DEFAULT_GEMINI_MODEL,
    DEFAULT_PROFESSOR_BACKEND,
    DEFAULT_PROFESSOR_MAX_TOKENS,
    DEFAULT_RETRIES,
    DEFAULT_RETRY_DELAY,
    _get_config,
    _get_inference_router,
    _get_prompt_manager,
)
from src.audit.schema import ExamRecord, PromptGenerationError, SampleRecord

# Lazy config accessor
CFG = _get_config()

# ======================================================================
# LOGGING
# ======================================================================

logger = logging.getLogger(__name__)

# ======================================================================
# CONFIGURATION PATHS
# ======================================================================

_PATTERNS_CONFIG_PATH = Path("configs/stage_5_evaluation/ha_patterns.yaml")

# ======================================================================
# LAZY SINGLETON STORAGE
# ======================================================================

_domain_patterns_cache: dict[str, Any] | None = None


# ======================================================================
# DOMAIN PATTERNS
# ======================================================================


def _load_domain_patterns() -> dict[str, Any]:
    """Lazy-load domain-specific modernity patterns from the YAML taxonomy.

    Returns the parsed contents of ``ha_patterns.yaml``.  On first call the
    file is read; subsequent calls return the cached dict.
    """
    global _domain_patterns_cache
    if _domain_patterns_cache is None:
        if _PATTERNS_CONFIG_PATH.exists():
            with open(_PATTERNS_CONFIG_PATH, "r", encoding="utf-8") as fh:
                _domain_patterns_cache = yaml.safe_load(fh) or {}
        else:
            logger.warning(
                "Domain patterns config not found at %s — using empty taxonomy",
                _PATTERNS_CONFIG_PATH,
            )
            _domain_patterns_cache = {}
    return _domain_patterns_cache


# ======================================================================
# EXAM GENERATION
# ======================================================================


def _build_domain_standards_section(reference_standards: str, gap_analysis: str) -> str:
    """Build the domain-standards section injected into professor prompts.

    Priority: gap_analysis (most specific) → reference_standards → ``default_standards``
    from ``ha_patterns.yaml`` (domain-agnostic fallback).
    """
    if gap_analysis:
        return f"Gap Analysis & Migration Requirements:\n{gap_analysis}"
    if reference_standards:
        return f"Domain Architectural Standards:\n{reference_standards}"
    return _load_domain_patterns().get("default_standards", "").strip()


def _format_reference_standards(
    master: str,
    changelog: str,
    jinja_guide: str,
) -> str:
    """Format reference standards by concatenating master docs according to
    the domain-specific formatting configuration in eval_config.yaml.

    This function is domain-agnostic: all section names, labels, and truncation
    limits are read from CFG[master_docs_formatting], not hardcoded.

    Args:
        master: Master guide content (may be truncated based on config).
        changelog: Technical changelog content.
        jinja_guide: Jinja/YAML guide content.

    Returns:
        Formatted standards string concatenating all sections with labels.
    """
    fmt_config = CFG.get("master_docs_formatting", {})
    if not fmt_config or not isinstance(fmt_config, dict):
        # Fallback: safe minimal formatting if config missing
        logger.warning("master_docs_formatting not configured; using fallback format")
        return (
            "# Reference Documents\n\n"
            + master[:8000]
            + "\n\n"
            + changelog[:8000]
            + "\n\n"
            + jinja_guide[:4000]
        )

    sections: list[tuple[str, int]] = [
        (master, fmt_config.get("master_guide", {}).get("truncate_at", 8000)),
        (changelog, fmt_config.get("technical_changelog", {}).get("truncate_at", 8000)),
        (jinja_guide, fmt_config.get("jinja_yaml_guide", {}).get("truncate_at", 4000)),
    ]

    parts: list[str] = []
    for content, limit in sections:
        if content:
            parts.append(content[:limit])

    # Rejoin with label headers from config
    result_parts: list[str] = []
    content_idx = 0
    for key in ("master_guide", "technical_changelog", "jinja_yaml_guide"):
        if content_idx < len(parts):
            label = fmt_config.get(key, {}).get("label", key.upper())
            result_parts.append(f"{label}:\n{parts[content_idx]}")
            content_idx += 1

    return "\n\n".join(result_parts)


def generate_exam_question(
    sample: SampleRecord,
    judge_model: str,
    api_url: str = DEFAULT_API_URL,
    retries: int = DEFAULT_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY,
    professor_backend: str = DEFAULT_PROFESSOR_BACKEND,
    gemini_model: str = DEFAULT_GEMINI_MODEL,
    validate: bool = False,
) -> ExamRecord:
    """Ask the professor model to synthesise a novel exam question.

    Routes to Gemini (default when GOOGLE_API_KEY set) or vLLM.
    Uses JSON mode when available. Raises PromptGenerationError on failure (no fallback).
    """
    ref_code = sample.reference_response
    if len(ref_code) > 4000:
        ref_code = ref_code[:4000] + "\n... [truncated] ..."

    reference_standards_section = _build_domain_standards_section(
        sample.reference_standards,
        sample.gap_analysis,
    )

    pm = _get_prompt_manager()
    user_msg = pm.format(
        "professor_exam",
        fragment_name=sample.fragment_name,
        source_file=sample.source_file,
        example_type=sample.example_type,
        ldi=sample.ldi,
        reference_code=ref_code,
        reference_standards_section=reference_standards_section,
    )

    client = _get_inference_router().professor(
        backend=professor_backend,
        gemini_model=gemini_model,
        vllm_model=judge_model,
        api_url=api_url,
    )
    raw = client.generate_with_retry(
        prompt=user_msg,
        system_prompt=pm.system("professor_exam"),
        max_tokens=DEFAULT_PROFESSOR_MAX_TOKENS,
        temperature=0.7,
        retries=retries,
        retry_delay=retry_delay,
        json_mode=True,  # Use structured JSON output
    )
    raw = raw.strip()
    # Strip accidental markdown fences (defensive — json_mode should prevent these)
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"```\s*$", "", raw, flags=re.MULTILINE).strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error(
            "Professor returned invalid JSON for %s: %s\nRaw:\n%s",
            sample.id,
            exc,
            raw[:2000],
        )
        raise PromptGenerationError(
            f"Professor failed to generate valid JSON for {sample.id}: {exc}"
        ) from exc

    exam_question = parsed.get("exam_question", "").strip()
    eval_criteria: list[str] = parsed.get("eval_criteria", [])
    target_patterns: list[str] = parsed.get("target_patterns", [])

    if not exam_question or not eval_criteria:
        logger.error(
            "Professor response missing required fields for %s. Raw:\n%s",
            sample.id,
            raw[:2000],
        )
        raise PromptGenerationError(
            f"Professor response missing required fields for {sample.id}"
        )

    logger.info("  Exam generated for %s (%d criteria)", sample.id, len(eval_criteria))
    return ExamRecord.from_sample(
        sample,
        exam_question=exam_question,
        eval_criteria=eval_criteria,
        target_patterns=target_patterns,
    )
