#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""AEGF Model Evaluator — High-Fidelity Exam-Based Quality Gate.

High-fidelity dual-inference evaluation pipeline that tests GENERALISATION,
not memorisation: a "Professor" model (base LLM) first synthesises novel exam
questions from each gold reference, then scores both baseline and LoRA-adapter
responses using an LLM-as-a-Judge rubric.

Modes
-----
  sample          — Extract a balanced stratified sample and persist it.
  generate-exam   — Professor generates novel exam questions from the sample.
  baseline        — Run inference (base model) on the exam questions.
  adapter         — Run inference (LoRA adapter) on the exam questions.
  score           — LLM-as-Judge scores + emits the full audit report.
  full            — Execute all five stages in sequence.

Pipeline
--------
  sample → generate-exam → baseline → adapter → score

Usage
-----
  # One-shot end-to-end evaluation
  python -m src.audit.model_evaluator full \\
      --dataset data/synthetic/v11_PLATINUM_UNIFORM.jsonl \\
      --base-model qwen3-30b-a3b-thinking-fp8 \\
      --adapter-model platinum_adapter

  # Step by step
  python -m src.audit.model_evaluator sample         --dataset data/synthetic/v11_PLATINUM_UNIFORM.jsonl
  python -m src.audit.model_evaluator generate-exam  --judge-model qwen3-30b-a3b-thinking-fp8
  python -m src.audit.model_evaluator baseline       --base-model qwen3-30b-a3b-thinking-fp8
  python -m src.audit.model_evaluator adapter        --adapter-model platinum_adapter
  python -m src.audit.model_evaluator score          --judge-model qwen3-30b-a3b-thinking-fp8
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import os
import re
import sys
import textwrap
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from src.audit.inference import InferenceRouter
from src.audit.persistence import (
    load_exam,
    load_inference,
    load_persisted_sample,
    persist_exam,
    persist_inference,
    persist_sample,
)
from src.audit.prompt_manager import PromptManager
from src.audit.sampling import load_dataset, stratified_sample
from src.audit.schema import (
    SCORING_WEIGHTS,
    AuditReport,
    ExamRecord,
    InferenceResult,
    PromptGenerationError,
    SampleRecord,
    ScoreCard,
)
from src.utils.doc_loader import load_master_docs

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

load_dotenv()

LOGGER_NAME = "AEGF.Evaluator"
logger = logging.getLogger(LOGGER_NAME)


# ---------------------------------------------------------------------------
# Configuration — YAML + env overrides
# ---------------------------------------------------------------------------

_CONFIG_PATH = Path("configs/stage_5_evaluation/eval_config.yaml")
_PATTERNS_CONFIG_PATH = Path("configs/stage_5_evaluation/ha_patterns.yaml")


def _load_config() -> dict[str, Any]:
    """Load evaluation config from YAML, with environment variable overrides."""
    if _CONFIG_PATH.exists():
        with open(_CONFIG_PATH, "r", encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh) or {}
    else:
        logger.warning("Config not found at %s — using defaults", _CONFIG_PATH)
        cfg = {}

    # Env overrides (AEGF_ prefix)
    _env = {
        "api_url":              os.getenv("AEGF_VLLM_API_URL"),
        "audit_dir":            os.getenv("AEGF_AUDIT_DIR"),
        "sample_size":          os.getenv("AEGF_SAMPLE_SIZE"),
        "base_model":           os.getenv("AEGF_BASE_MODEL"),
        "adapter_model":        os.getenv("AEGF_ADAPTER_MODEL"),
        "judge_model":          os.getenv("AEGF_JUDGE_MODEL"),
        "max_tokens":           os.getenv("AEGF_MAX_TOKENS"),
        "temperature":          os.getenv("AEGF_TEMPERATURE"),
        "retries":              os.getenv("AEGF_RETRIES"),
        "retry_delay":          os.getenv("AEGF_RETRY_DELAY"),
        "professor_backend":    os.getenv("AEGF_PROFESSOR_BACKEND"),
        "inference_backend":    os.getenv("AEGF_INFERENCE_BACKEND"),
        "gemini_model":         os.getenv("AEGF_GEMINI_MODEL"),
        "professor_max_tokens": os.getenv("AEGF_PROFESSOR_MAX_TOKENS"),
        "inference_max_tokens": os.getenv("AEGF_INFERENCE_MAX_TOKENS"),
    }
    for k, v in _env.items():
        if v is not None:
            # Coerce numeric types
            if k in ("sample_size", "max_tokens", "retries", "professor_max_tokens", "inference_max_tokens"):
                cfg[k] = int(v)
            elif k in ("temperature", "retry_delay"):
                cfg[k] = float(v)
            else:
                cfg[k] = v

    return cfg


CFG = _load_config()

# Convenience accessors with typed defaults
DEFAULT_API_URL: str = CFG.get("api_url", "http://localhost:8000/v1")
DEFAULT_AUDIT_DIR: str = CFG.get("audit_dir", "data/audit")
DEFAULT_SAMPLE_SIZE: int = CFG.get("sample_size", 5)
DEFAULT_BASE_MODEL: str = CFG.get("base_model", "qwen3-30b-a3b-thinking-fp8")
DEFAULT_ADAPTER_MODEL: str = CFG.get("adapter_model", "platinum_adapter")
DEFAULT_JUDGE_MODEL: str = CFG.get("judge_model") or DEFAULT_BASE_MODEL
DEFAULT_MAX_TOKENS: int = CFG.get("max_tokens", 65536)
DEFAULT_TEMPERATURE: float = CFG.get("temperature", 0.3)
DEFAULT_RETRIES: int = CFG.get("retries", 3)
DEFAULT_RETRY_DELAY: float = CFG.get("retry_delay", 5.0)
DEFAULT_PROFESSOR_BACKEND: str = CFG.get("professor_backend", "auto")
DEFAULT_INFERENCE_BACKEND: str = CFG.get("inference_backend", "vllm")
DEFAULT_GEMINI_MODEL: str = CFG.get("gemini_model", "gemini-2.5-flash")
DEFAULT_PROFESSOR_MAX_TOKENS: int = CFG.get("professor_max_tokens", 12288)
DEFAULT_INFERENCE_MAX_TOKENS: int = CFG.get("inference_max_tokens", 65536)

# Singletons
_prompt_mgr: PromptManager | None = None
_router: InferenceRouter | None = None
_domain_patterns_cache: dict[str, Any] | None = None


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
            + master[:8000] + "\n\n"
            + changelog[:8000] + "\n\n"
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


def _prompts() -> PromptManager:
    global _prompt_mgr
    if _prompt_mgr is None:
        _prompt_mgr = PromptManager()
    return _prompt_mgr


def _inference_router() -> InferenceRouter:
    global _router
    if _router is None:
        _router = InferenceRouter()
    return _router


# ---------------------------------------------------------------------------
# Gap Analysis
# ---------------------------------------------------------------------------


def generate_gap_analysis(
    sample: SampleRecord,
    master: str,
    changelog: str,
    jinja_guide: str,
    professor_backend: str = DEFAULT_PROFESSOR_BACKEND,
    gemini_model: str = DEFAULT_GEMINI_MODEL,
    judge_model: str = DEFAULT_JUDGE_MODEL,
    api_url: str = DEFAULT_API_URL,
    retries: int = DEFAULT_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY,
    validate: bool = False,
) -> str:
    """Genera un análisis de gaps en texto plano para un SampleRecord.

    Llama al Professor (Gemini o vLLM) y devuelve directamente el texto
    de la respuesta sin ningún parseo JSON.
    """
    ref_code = sample.reference_response or sample.user_prompt or ""
    if len(ref_code) > 4000:
        ref_code = ref_code[:4000] + "\n... [truncated] ..."

    pm = _prompts()
    user_msg = pm.format(
        "gap_analysis",
        fragment_name=sample.fragment_name,
        source_file=sample.source_file,
        reference_code=ref_code,
        master=master[:8000],
        changelog=changelog[:8000],
        jinja=jinja_guide[:3000],
    )

    if validate:
        logger.info("Validate mode: skipping professor call for gap_analysis %s", sample.id)
        return f"[validate] gap_analysis placeholder for {sample.fragment_name} ({sample.source_file})"

    client = _inference_router().professor(
        backend=professor_backend,
        gemini_model=gemini_model,
        vllm_model=judge_model,
        api_url=api_url,
    )
    raw = client.generate_with_retry(
        prompt=user_msg,
        system_prompt=pm.system("gap_analysis"),
        max_tokens=DEFAULT_PROFESSOR_MAX_TOKENS,
        temperature=0.2,
        retries=retries,
        retry_delay=retry_delay,
    )
    gap_text = raw.strip()
    if not gap_text:
        raise PromptGenerationError(f"Professor produced empty gap_analysis for {sample.id}")
    return gap_text


# ---------------------------------------------------------------------------
# Exam Generation
# ---------------------------------------------------------------------------


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
        sample.reference_standards, sample.gap_analysis,
    )

    pm = _prompts()
    user_msg = pm.format(
        "professor_exam",
        fragment_name=sample.fragment_name,
        source_file=sample.source_file,
        example_type=sample.example_type,
        ldi=sample.ldi,
        reference_code=ref_code,
        reference_standards_section=reference_standards_section,
    )

    client = _inference_router().professor(
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
            sample.id, exc, raw[:2000],
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
            sample.id, raw[:2000],
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


# ---------------------------------------------------------------------------
# Student Inference
# ---------------------------------------------------------------------------


def run_inference(
    samples: list[Any],
    model: str,
    api_url: str = DEFAULT_API_URL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = DEFAULT_TEMPERATURE,
    retries: int = DEFAULT_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY,
    inference_backend: str = DEFAULT_INFERENCE_BACKEND,
    gemini_model: str = DEFAULT_GEMINI_MODEL,
) -> list[InferenceResult]:
    """Run closed-book inference on a sample list.

    Accepts both SampleRecord and ExamRecord. Enforces closed-book evaluation:
    student inferences run WITHOUT any system prompt.
    """
    client = _inference_router().student(
        backend=inference_backend,
        gemini_model=gemini_model,
        model=model,
        api_url=api_url,
    )
    results: list[InferenceResult] = []
    total = len(samples)

    for idx, sample in enumerate(samples, 1):
        prompt = getattr(sample, "exam_question", "") or sample.user_prompt
        logger.info(
            "[%d/%d] Inferring %s (type=%s, frag=%s) via %s",
            idx, total, sample.id, sample.example_type,
            sample.fragment_name, inference_backend,
        )
        t0 = time.perf_counter()
        raw = client.generate_with_retry(
            prompt=prompt,
            system_prompt=None,  # Closed-book: NO system prompt
            max_tokens=max_tokens,
            temperature=temperature,
            retries=retries,
            retry_delay=retry_delay,
        )
        latency = (time.perf_counter() - t0) * 1000

        result = InferenceResult(
            record_id=sample.id,
            model_name=model,
            response=raw,
            latency_ms=round(latency, 1),
            token_count=len(raw.split()) if raw else 0,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        results.append(result)
        logger.info("  → %d tokens in %.0fms", result.token_count, result.latency_ms)

    return results


# ---------------------------------------------------------------------------
# Scoring Engine — LLM-as-Judge (fail-fast, no fallback)
# ---------------------------------------------------------------------------


def _extract_code_blocks(text: str) -> str:
    """Extract all code from fenced blocks or <tool_call>/<write_action> tags."""
    blocks: list[str] = []
    for m in re.finditer(r"```(?:\w+)?\n(.*?)```", text, re.DOTALL):
        blocks.append(m.group(1).strip())
    for tag in ("tool_call", "write_action"):
        for m in re.finditer(rf"<{tag}>(.*?)</{tag}>", text, re.DOTALL):
            blocks.append(m.group(1).strip())
    return "\n\n".join(blocks)


# Modernity patterns are loaded lazily from ha_patterns.yaml via _load_domain_patterns().


def llm_judge_score(
    exam: ExamRecord,
    baseline_resp: str,
    adapter_resp: str,
    judge_model: str,
    api_url: str = DEFAULT_API_URL,
    retries: int = DEFAULT_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY,
    professor_backend: str = DEFAULT_PROFESSOR_BACKEND,
    gemini_model: str = DEFAULT_GEMINI_MODEL,
    validate: bool = False,
) -> dict[str, Any]:
    """Ask the professor model to score baseline vs adapter on the rubric.

    Uses JSON mode for structured output. Raises PromptGenerationError on any
    judge failure — no fallback is performed.
    """
    criteria_text = "\n".join(
        f"  {i+1}. {c}" for i, c in enumerate(exam.eval_criteria)
    ) if exam.eval_criteria else "  (no specific criteria defined)"

    # Truncate responses to avoid exceeding context
    b_resp = baseline_resp[:6000] + "\n...[truncated]" if len(baseline_resp) > 6000 else baseline_resp
    a_resp = adapter_resp[:6000] + "\n...[truncated]" if len(adapter_resp) > 6000 else adapter_resp

    pm = _prompts()
    user_msg = pm.format(
        "professor_judge",
        exam_question=exam.exam_question or exam.user_prompt,
        eval_criteria=criteria_text,
        baseline_response=b_resp,
        adapter_response=a_resp,
    )

    max_judge_tokens = 512 if validate else DEFAULT_INFERENCE_MAX_TOKENS
    raw_path: Path | None = None

    try:
        client = _inference_router().professor(
            backend=professor_backend,
            gemini_model=gemini_model,
            vllm_model=judge_model,
            api_url=api_url,
        )
        raw = client.generate_with_retry(
            prompt=user_msg,
            system_prompt=pm.system("professor_judge"),
            max_tokens=max_judge_tokens,
            temperature=0.0,  # deterministic scoring
            retries=retries,
            retry_delay=retry_delay,
            json_mode=True,  # Use structured JSON output
        )
        raw = raw.strip()

        # Clean markdown fences (defensive — json_mode should prevent these)
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
        cleaned = re.sub(r"```\s*$", "", cleaned, flags=re.MULTILINE).strip()

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as exc_parse:
            try:
                out_dir = Path(DEFAULT_AUDIT_DIR)
                out_dir.mkdir(parents=True, exist_ok=True)
                raw_path = out_dir / f"judge_raw_{exam.id}.txt"
                raw_path.write_text(raw, encoding="utf-8")
                logger.error("Judge produced invalid JSON for %s; raw saved to %s", exam.id, raw_path)
            except Exception as save_exc:
                logger.error("Failed to persist raw judge output for %s: %s", exam.id, save_exc)
            raise exc_parse

        # Validate expected keys
        for key in ("baseline", "adapter", "reasoning"):
            if key not in parsed:
                raise ValueError(f"Missing key '{key}' in judge response")
        for section in ("baseline", "adapter"):
            for dim in SCORING_WEIGHTS:
                if dim not in parsed[section]:
                    parsed[section][dim] = 0.5
                else:
                    parsed[section][dim] = max(0.0, min(1.0, float(parsed[section][dim])))

        logger.debug(
            "  Judge scores — adapter composite: %.3f",
            sum(parsed["adapter"][d] * w for d, w in SCORING_WEIGHTS.items()),
        )
        return parsed

    except Exception as exc:
        msg = f"LLM judge failed for {exam.id}: {exc}"
        if raw_path:
            msg += f" — raw output saved to {raw_path}"
        logger.error(msg)
        raise PromptGenerationError(msg) from exc


def compute_scorecard(
    exam: ExamRecord,
    baseline_resp: str,
    adapter_resp: str,
    judge_model: str,
    api_url: str = DEFAULT_API_URL,
    retries: int = DEFAULT_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY,
    professor_backend: str = DEFAULT_PROFESSOR_BACKEND,
    gemini_model: str = DEFAULT_GEMINI_MODEL,
    validate: bool = False,
) -> ScoreCard:
    """Compute a multi-dimensional LLM-judged scorecard.

    Raises PromptGenerationError if the judge call fails (no fallback).
    """
    judgment = llm_judge_score(
        exam=exam,
        baseline_resp=baseline_resp,
        adapter_resp=adapter_resp,
        judge_model=judge_model,
        api_url=api_url,
        retries=retries,
        retry_delay=retry_delay,
        professor_backend=professor_backend,
        gemini_model=gemini_model,
        validate=validate,
    )

    a = judgment["adapter"]
    b = judgment["baseline"]

    def _composite(scores: dict[str, float]) -> float:
        return sum(scores.get(dim, 0.0) * weight for dim, weight in SCORING_WEIGHTS.items())

    adapter_composite = _composite(a)
    baseline_composite = _composite(b)
    delta = adapter_composite - baseline_composite

    # Diagnostic notes from regex pattern detection (taxonomy from ha_patterns.yaml)
    _patterns = _load_domain_patterns()
    _legacy = [(e["pattern"], e["description"]) for e in _patterns.get("legacy_patterns", [])]
    _modern = [(e["pattern"], e["description"]) for e in _patterns.get("modern_patterns", [])]
    adapter_code = _extract_code_blocks(adapter_resp)
    notes_parts: list[str] = []
    for pat, desc in _legacy:
        if re.search(pat, adapter_code):
            notes_parts.append(f"⚠ Legacy: {desc}")
    for pat, desc in _modern:
        if re.search(pat, adapter_code):
            notes_parts.append(f"✓ Modern: {desc}")

    return ScoreCard(
        record_id=exam.id,
        example_type=exam.example_type,
        fragment_name=exam.fragment_name,
        ha_modernity=round(a.get("ha_modernity", 0.0), 3),
        reasoning_depth=round(a.get("reasoning_depth", 0.0), 3),
        functionality=round(a.get("functionality", 0.0), 3),
        completeness=round(a.get("completeness", 0.0), 3),
        style=round(a.get("style", 0.0), 3),
        composite_score=round(adapter_composite, 3),
        delta_vs_baseline=round(delta, 3),
        judge_reasoning=judgment.get("reasoning", ""),
        notes="; ".join(notes_parts[:6]),
    )


# ---------------------------------------------------------------------------
# Report Generation
# ---------------------------------------------------------------------------


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


def generate_report(
    report: AuditReport,
    scorecards: list[ScoreCard],
    exam_records: list[ExamRecord],
    baseline_results: list[InferenceResult],
    adapter_results: list[InferenceResult],
    audit_dir: str,
) -> Path:
    """Generate a comprehensive Markdown audit report."""
    out_dir = Path(audit_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    composites = [sc.composite_score for sc in scorecards]
    deltas = [sc.delta_vs_baseline for sc in scorecards]
    final_grade = (sum(composites) / len(composites)) * 100 if composites else 0.0
    avg_delta = sum(deltas) / len(deltas) if deltas else 0.0

    type_scores: dict[str, list[float]] = defaultdict(list)
    for sc in scorecards:
        type_scores[sc.example_type].append(sc.composite_score)

    base_lat = [r.latency_ms for r in baseline_results]
    adapt_lat = [r.latency_ms for r in adapter_results]

    report = dataclasses.replace(
        report,
        final_grade=round(final_grade, 1),
        verdict=_verdict(final_grade),
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

    w(f"## Final Grade: {report.final_grade}/100 ({_grade_label(report.final_grade)})")
    w("")
    w(f"**Verdict:** {report.verdict}")
    w("")
    w("| Metric | Value |")
    w("|--------|-------|")
    w(f"| Composite Score (avg) | {report.final_grade:.1f} |")
    w(f"| Avg Δ vs Baseline | {avg_delta:+.3f} |")
    w(f"| Positive Deltas | {sum(1 for d in deltas if d > 0)}/{len(deltas)} |")
    if base_lat:
        w(f"| Baseline Avg Latency | {sum(base_lat)/len(base_lat):.0f}ms |")
    if adapt_lat:
        w(f"| Adapter Avg Latency | {sum(adapt_lat)/len(adapt_lat):.0f}ms |")
    w("")

    w("## Score Breakdown by Example Type")
    w("")
    w("| Type | Count | Avg Score | Avg Δ |")
    w("|------|-------|-----------|-------|")
    for et in sorted(type_scores.keys()):
        scores = type_scores[et]
        et_deltas = [sc.delta_vs_baseline for sc in scorecards if sc.example_type == et]
        avg_sc = sum(scores) / len(scores) * 100
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
        short_id = sc.record_id[-12:] if len(sc.record_id) > 12 else sc.record_id
        frag = sc.fragment_name[:25] if sc.fragment_name else "—"
        w(
            f"| {short_id} | {sc.example_type} | {frag} "
            f"| {sc.ha_modernity:.2f} | {sc.reasoning_depth:.2f} "
            f"| {sc.functionality:.2f} | {sc.completeness:.2f} "
            f"| {sc.style:.2f} | **{sc.composite_score:.3f}** "
            f"| {sc.delta_vs_baseline:+.3f} |"
        )
    w("")

    w("## Scoring Methodology (LLM-as-Judge)")
    w("")
    w(f"The Professor model (`{report.judge_model}`) scores each exam response across 5 dimensions:")
    w("")
    w("| Dimension | Weight | Description |")
    w("|-----------|--------|-------------|")
    w("| HA Modernity | 30% | Uses entry.runtime_data, plural setup, enum device classes |")
    w("| Reasoning Depth | 25% | `<think>` block correctly identifies edge cases and migration paths |")
    w("| Functionality | 25% | Code compiles and runs correctly in Home Assistant |")
    w("| Completeness | 12% | All required functions/classes implemented |")
    w("| Style | 8% | AEGF conventions: `<think>` present, docstrings, no apologies |")
    w("")
    w("**Composite** = Σ(dimension × weight). **Δ** = adapter − baseline composite.")
    w("No regex fallback: judge failures abort the audit.")
    w("")

    judged = [sc for sc in scorecards if sc.judge_reasoning]
    if judged:
        w("## Judge Reasoning Highlights")
        w("")
        for sc in judged[:8]:
            short_id = sc.record_id[-12:]
            w(f"**{short_id}** ({sc.fragment_name}):")
            w(f"> {sc.judge_reasoning}")
            w("")

    flagged = [sc for sc in scorecards if sc.notes]
    if flagged:
        w("## Regex Pattern Detection Notes")
        w("")
        for sc in flagged:
            w(f"- **{sc.record_id}** ({sc.fragment_name}): {sc.notes}")
        w("")

    w("---")
    w("")
    w("*Report generated by `src/audit/model_evaluator.py` — AEGF Quality Gate v3.0 (LLM-as-Judge)*")

    report_path = out_dir / "audit_report_v11.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Audit report written → %s", report_path)

    json_path = out_dir / "audit_report_v11.json"
    json_path.write_text(
        json.dumps(report.to_dict(), indent=2, ensure_ascii=False),
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
        logger.info("Sample already exists at %s (use --force to regenerate)", sample_path)
        samples = load_persisted_sample(args.audit_dir)
    else:
        if not args.dataset:
            raise SystemExit("--dataset is required for 'sample' mode")
        records = load_dataset(args.dataset)

        gap_dir = Path(args.gap_dir)
        master, changelog, jinja_guide = load_master_docs(gap_dir)

        samples = stratified_sample(records, args.sample_size)

        # SampleRecord is frozen — use dataclasses.replace() to create enriched copies.
        enriched: list[SampleRecord] = []
        for s in samples:
            replacements: dict[str, str] = {}
            if not (s.reference_standards and s.reference_standards.strip()):
                # Format reference standards using domain-agnostic config-driven logic
                replacements["reference_standards"] = _format_reference_standards(
                    master, changelog, jinja_guide
                )
            # Apply reference_standards first (may be needed by generate_gap_analysis)
            s_enriched = dataclasses.replace(s, **replacements) if replacements else s
            if not (s_enriched.gap_analysis and s_enriched.gap_analysis.strip()):
                try:
                    gap = generate_gap_analysis(
                        s_enriched, master, changelog, jinja_guide,
                        professor_backend=args.professor_backend,
                        gemini_model=args.gemini_model,
                        judge_model=args.judge_model,
                        api_url=args.api_url,
                        retries=args.retries,
                        retry_delay=args.retry_delay,
                        validate=args.validate,
                    )
                    s_enriched = dataclasses.replace(s_enriched, gap_analysis=gap)
                except PromptGenerationError as exc:
                    # Propagated from generate_gap_analysis; tested via mock failure
                    logger.error("Gap analysis generation failed for %s: %s", s.id, exc)
                    raise SystemExit(f"Gap analysis generation failed for {s.id}: {exc}") from exc
            enriched.append(s_enriched)
        samples = enriched

        persist_sample(samples, args.audit_dir)

    dist = Counter(s.example_type for s in samples)
    logger.info("Sample distribution: %s", dict(dist))


def cmd_generate_exam(args: argparse.Namespace) -> None:
    """Professor model generates novel exam questions from the persisted sample."""
    exam_path = Path(args.audit_dir) / "eval_exam.json"
    if exam_path.exists() and not args.force:
        logger.info("Exam already exists at %s (use --force to regenerate)", exam_path)
        exam_records = load_exam(args.audit_dir)
        logger.info("Loaded %d existing exam questions", len(exam_records))
        return

    samples = load_persisted_sample(args.audit_dir)
    missing = [
        s.id for s in samples
        if not (s.reference_standards and s.reference_standards.strip())
        or not (s.gap_analysis and s.gap_analysis.strip())
    ]
    if missing:
        logger.error("Persisted sample has records missing HA metadata: %s", missing)
        raise SystemExit("Persisted sample validation failed: all records must include reference_standards and gap_analysis.")

    judge_model = args.judge_model
    logger.info("Generating %d exam questions with professor model: %s", len(samples), judge_model)

    exam_records: list[ExamRecord] = []
    for idx, sample in enumerate(samples, 1):
        logger.info("[%d/%d] Generating exam for %s (%s)", idx, len(samples), sample.id, sample.fragment_name)
        try:
            record = generate_exam_question(
                sample=sample,
                judge_model=judge_model,
                api_url=args.api_url,
                retries=args.retries,
                retry_delay=args.retry_delay,
                professor_backend=args.professor_backend,
                gemini_model=args.gemini_model,
                validate=args.validate,
            )
        except PromptGenerationError as exc:
            # Propagated from generate_exam_question; tested via mock failure
            logger.error("Exam generation failed for %s: %s", sample.id, exc)
            raise SystemExit(f"Exam generation failed for {sample.id}: {exc}") from exc
        exam_records.append(record)

    persist_exam(exam_records, args.audit_dir)
    generated = sum(1 for r in exam_records if r.exam_question and r.exam_question != r.user_prompt)
    logger.info("Exam generation complete: %d/%d questions generated by professor", generated, len(samples))


def cmd_baseline(args: argparse.Namespace) -> None:
    """Run baseline inference on exam questions with the base model."""
    try:
        records = load_exam(args.audit_dir)
        logger.info("Using exam questions for baseline inference")
    except FileNotFoundError:
        logger.warning("No exam found — using original sample prompts (run generate-exam first)")
        records = load_persisted_sample(args.audit_dir)

    results = run_inference(
        records,
        model=args.model or args.base_model,
        api_url=args.api_url,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        retries=args.retries,
        retry_delay=args.retry_delay,
        inference_backend=args.inference_backend,
        gemini_model=args.gemini_model,
    )
    persist_inference(results, "baseline", args.audit_dir)


def cmd_adapter(args: argparse.Namespace) -> None:
    """Run adapter inference on exam questions with the LoRA model."""
    try:
        records = load_exam(args.audit_dir)
        logger.info("Using exam questions for adapter inference")
    except FileNotFoundError:
        logger.warning("No exam found — using original sample prompts (run generate-exam first)")
        records = load_persisted_sample(args.audit_dir)

    results = run_inference(
        records,
        model=args.model or args.adapter_model,
        api_url=args.api_url,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        retries=args.retries,
        retry_delay=args.retry_delay,
        inference_backend=args.inference_backend,
        gemini_model=args.gemini_model,
    )
    persist_inference(results, "adapter", args.audit_dir)


def cmd_score(args: argparse.Namespace) -> None:
    """LLM-as-Judge scores adapter vs baseline and generates the audit report."""
    try:
        exam_records = load_exam(args.audit_dir)
    except FileNotFoundError:
        logger.warning("No exam found — scoring without exam criteria")
        raw_samples = load_persisted_sample(args.audit_dir)
        exam_records = [ExamRecord.from_sample(s, exam_question=s.user_prompt) for s in raw_samples]

    baseline_results = load_inference("baseline", args.audit_dir)
    adapter_results = load_inference("adapter", args.audit_dir)

    baseline_map = {r.record_id: r for r in baseline_results}
    adapter_map = {r.record_id: r for r in adapter_results}
    judge_model = args.judge_model

    logger.info("Scoring %d records with judge model: %s", len(exam_records), judge_model)
    scorecards: list[ScoreCard] = []
    total = len(exam_records)
    for idx, exam in enumerate(exam_records, 1):
        base_r = baseline_map.get(exam.id)
        adapt_r = adapter_map.get(exam.id)
        if not base_r or not adapt_r:
            logger.warning("[%d/%d] Missing inference for %s — skipping", idx, total, exam.id)
            continue
        logger.info("[%d/%d] Judging %s", idx, total, exam.id)
        sc = compute_scorecard(
            exam=exam,
            baseline_resp=base_r.response,
            adapter_resp=adapt_r.response,
            judge_model=judge_model,
            api_url=args.api_url,
            retries=args.retries,
            retry_delay=args.retry_delay,
            professor_backend=args.professor_backend,
            gemini_model=args.gemini_model,
            validate=args.validate,
        )
        scorecards.append(sc)

    report = AuditReport(
        timestamp=datetime.now(timezone.utc).isoformat(),
        dataset_path=args.dataset or "N/A",
        base_model=baseline_results[0].model_name if baseline_results else "N/A",
        adapter_model=adapter_results[0].model_name if adapter_results else "N/A",
        judge_model=judge_model,
        sample_size=len(exam_records),
        type_distribution=dict(Counter(e.example_type for e in exam_records)),
        scorecards=scorecards,
    )

    report_path = generate_report(
        report, scorecards, exam_records, baseline_results, adapter_results, args.audit_dir,
    )
    print(f"\n{'='*64}")
    print(f"  AEGF QUALITY GATE — FINAL GRADE: {report.final_grade}/100")
    print(f"  Verdict: {report.verdict}")
    print(f"  Report:  {report_path}")
    print(f"{'='*64}\n")


def cmd_full(args: argparse.Namespace) -> None:
    """Run the full 5-stage evaluation pipeline."""
    if args.validate:
        args.sample_size = 1
        args.force = True
        logger.info("Validate mode: sample_size=1, force=True — minimal-token end-to-end flow test")
    logger.info("=== AEGF Quality Gate — High-Fidelity Exam Pipeline ===")

    logger.info("--- Stage 1/5: Stratified Sampling ---")
    cmd_sample(args)

    logger.info("--- Stage 2/5: Exam Generation (Professor) ---")
    cmd_generate_exam(args)

    logger.info("--- Stage 3/5: Baseline Inference ---")
    args.model = None
    cmd_baseline(args)

    logger.info("--- Stage 4/5: Adapter Inference ---")
    args.model = None
    cmd_adapter(args)

    logger.info("--- Stage 5/5: LLM-as-Judge Scoring ---")
    cmd_score(args)


# ---------------------------------------------------------------------------
# Argument Parser
# ---------------------------------------------------------------------------


def _shared_parser() -> argparse.ArgumentParser:
    """Build a parent parser with all shared options."""
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--api-url", default=DEFAULT_API_URL,
                        help=f"vLLM API endpoint (default: {DEFAULT_API_URL})")
    shared.add_argument("--audit-dir", default=DEFAULT_AUDIT_DIR,
                        help=f"Output directory for audit artifacts (default: {DEFAULT_AUDIT_DIR})")
    shared.add_argument("--dataset", default=None,
                        help="Path to the training JSONL dataset")
    shared.add_argument("--model", default=None,
                        help="Model name override for inference")
    shared.add_argument("--base-model", default=DEFAULT_BASE_MODEL,
                        help=f"Base model identifier (default: {DEFAULT_BASE_MODEL})")
    shared.add_argument("--adapter-model", default=DEFAULT_ADAPTER_MODEL,
                        help=f"LoRA adapter identifier (default: {DEFAULT_ADAPTER_MODEL})")
    shared.add_argument("--judge-model", default=DEFAULT_JUDGE_MODEL,
                        help=f"Professor/judge model (default: {DEFAULT_JUDGE_MODEL})")
    shared.add_argument("--professor-backend", default=DEFAULT_PROFESSOR_BACKEND,
                        choices=["auto", "gemini", "vllm"],
                        help="Backend for professor/judge calls (default: auto)")
    shared.add_argument("--gemini-model", default=DEFAULT_GEMINI_MODEL,
                        help=f"Gemini model name (default: {DEFAULT_GEMINI_MODEL})")
    shared.add_argument("--inference-backend", default=DEFAULT_INFERENCE_BACKEND,
                        choices=["vllm", "gemini"],
                        help="Backend for student inference (default: vllm)")
    shared.add_argument("--validate", action="store_true",
                        help="1-example end-to-end flow test with minimal token spend")
    shared.add_argument("--sample-size", type=int, default=DEFAULT_SAMPLE_SIZE,
                        help=f"Number of records to sample (default: {DEFAULT_SAMPLE_SIZE})")
    shared.add_argument("--gap-dir", default=CFG.get("gap_dir", "data/Gap"),
                        help="Path to directory containing HA master docs")
    shared.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS,
                        help=f"Max generation tokens (default: {DEFAULT_MAX_TOKENS})")
    shared.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE,
                        help=f"Sampling temperature (default: {DEFAULT_TEMPERATURE})")
    shared.add_argument("--retries", type=int, default=DEFAULT_RETRIES,
                        help=f"API retry attempts (default: {DEFAULT_RETRIES})")
    shared.add_argument("--retry-delay", type=float, default=DEFAULT_RETRY_DELAY,
                        help=f"Base retry backoff in seconds (default: {DEFAULT_RETRY_DELAY})")
    shared.add_argument("--force", action="store_true",
                        help="Force regeneration of existing artifacts")
    shared.add_argument("-v", "--verbose", action="store_true",
                        help="Enable debug logging")
    return shared


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    shared = _shared_parser()

    parser = argparse.ArgumentParser(
        prog="model_evaluator",
        description="AEGF Quality Gate — High-Fidelity Exam-Based Evaluation Pipeline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[shared],
        epilog=textwrap.dedent("""\
            Pipeline stages (run in order or all at once with 'full'):
              1. sample          Extract stratified sample from dataset
              2. generate-exam   Professor generates novel exam questions
              3. baseline        Base model inference on exam questions
              4. adapter         LoRA adapter inference on exam questions
              5. score           LLM-as-Judge scoring + audit report

            Examples:
              # One-shot end-to-end:
              %(prog)s full --dataset data/synthetic/v11_PLATINUM_UNIFORM.jsonl \\
                           --base-model qwen3-30b-a3b-thinking-fp8 \\
                           --adapter-model platinum_adapter

              # Step by step:
              %(prog)s sample        --dataset data/synthetic/v11_PLATINUM_UNIFORM.jsonl
              %(prog)s generate-exam --judge-model qwen3-30b-a3b-thinking-fp8
              %(prog)s baseline      --base-model qwen3-30b-a3b-thinking-fp8
              %(prog)s adapter       --adapter-model platinum_adapter
              %(prog)s score         --judge-model qwen3-30b-a3b-thinking-fp8
        """),
    )

    sub = parser.add_subparsers(dest="mode", help="Evaluation stage")
    sub.add_parser("sample",        help="Stage 1: Extract stratified sample",          parents=[shared])
    sub.add_parser("generate-exam", help="Stage 2: Professor generates exam questions", parents=[shared])
    sub.add_parser("baseline",      help="Stage 3: Base model inference",               parents=[shared])
    sub.add_parser("adapter",       help="Stage 4: LoRA adapter inference",             parents=[shared])
    sub.add_parser("score",         help="Stage 5: LLM-as-Judge scoring + report",      parents=[shared])
    sub.add_parser("full",          help="Run all 5 stages end-to-end",                 parents=[shared])

    return parser


def main() -> None:
    """Entry point for the AEGF Quality Gate evaluator."""
    parser = build_parser()
    args = parser.parse_args()

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
        "generate-exam": cmd_generate_exam,
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
