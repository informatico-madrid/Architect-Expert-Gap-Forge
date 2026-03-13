#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
AEGF Judge Module
=================
LLM-as-Judge scoring and inference for evaluation samples.
"""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any

from src.audit.config import (
    DEFAULT_API_URL,
    DEFAULT_GEMINI_MODEL,
    DEFAULT_INFERENCE_BACKEND,
    DEFAULT_INFERENCE_MAX_TOKENS,
    DEFAULT_MAX_TOKENS,
    DEFAULT_PROFESSOR_BACKEND,
    DEFAULT_RETRIES,
    DEFAULT_RETRY_DELAY,
    DEFAULT_TEMPERATURE,
    JUDGE_RESPONSE_TRUNCATION_LIMIT,
    _get_inference_router,
    _get_prompt_manager,
)
from src.audit.schema import (
    ExamRecord,
    InferenceResult,
    NormalizedJudgeResponse,
    PromptGenerationError,
    SCORING_WEIGHTS,
)
from src.schemas.converters import normalize_judge_response

# ======================================================================
# LOGGING
# ======================================================================

logger = logging.getLogger(__name__)


# ======================================================================
# UTILITIES
# ======================================================================

def _extract_code_blocks(text: str) -> str:
    """Extract all code from fenced blocks (markdown)."""
    blocks: list[str] = []
    # Only look for markdown code blocks - no tool_call/write_action tags
    for m in re.finditer(r"```(?:\w+)?\n(.*?)```", text, re.DOTALL):
        blocks.append(m.group(1).strip())
    return "\n\n".join(blocks)


def _sanitize_for_logging(text: str, max_length: int = 200) -> str:
    """Sanitize text for logging to avoid sensitive data exposure."""
    if not text:
        return ""
    # Truncate and escape newlines for log safety
    truncated = text[:max_length] + "..." if len(text) > max_length else text
    return truncated.replace("\n", "\\n").replace("\r", "\\r")


# ======================================================================
# INFERENCE
# ======================================================================


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
    client = _get_inference_router().student(
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
            idx,
            total,
            sample.id,
            sample.example_type,
            sample.fragment_name,
            inference_backend,
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


# ======================================================================
# SCORING ENGINE — LLM-AS-JUDGE (fail-fast, no fallback)
# ======================================================================


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
) -> NormalizedJudgeResponse:
    """Ask the professor model to score baseline vs adapter on the rubric.

    Uses JSON mode for structured output. Raises PromptGenerationError on any
    judge failure — no fallback is performed.
    """
    criteria_text = (
        "\n".join(f"  {i + 1}. {c}" for i, c in enumerate(exam.eval_criteria))
        if exam.eval_criteria
        else "  (no specific criteria defined)"
    )

    # Format target_patterns as a bullet checklist for the judge
    if exam.target_patterns:
        tp_text = "\n".join(f"  - {p}" for p in exam.target_patterns)
    else:
        tp_text = "  (no specific patterns required)"

    # Truncate responses to avoid exceeding context
    b_resp = (
        baseline_resp[:JUDGE_RESPONSE_TRUNCATION_LIMIT] + "\n...[truncated]"
        if len(baseline_resp) > JUDGE_RESPONSE_TRUNCATION_LIMIT
        else baseline_resp
    )
    a_resp = (
        adapter_resp[:JUDGE_RESPONSE_TRUNCATION_LIMIT] + "\n...[truncated]"
        if len(adapter_resp) > JUDGE_RESPONSE_TRUNCATION_LIMIT
        else adapter_resp
    )

    pm = _get_prompt_manager()
    user_msg = pm.format(
        "professor_judge",
        exam_question=exam.exam_question or exam.user_prompt,
        eval_criteria=criteria_text,
        target_patterns=tp_text,
        baseline_response=b_resp,
        adapter_response=a_resp,
    )

    max_judge_tokens = 512 if validate else DEFAULT_INFERENCE_MAX_TOKENS
    raw_path: str | None = None

    try:
        client = _get_inference_router().professor(
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
                # Use a simple path approach since we don't have DEFAULT_AUDIT_DIR here
                raw_path = f"data/audit/judge_raw_{exam.id}.txt"
                import os
                os.makedirs(os.path.dirname(raw_path), exist_ok=True)
                with open(raw_path, "w", encoding="utf-8") as f:
                    f.write(raw)
                logger.error(
                    "Judge produced invalid JSON for %s; raw saved to %s",
                    exam.get("sample_id", "unknown"),
                    raw_path,
                )
            except Exception as save_exc:
                logger.error(
                    "Failed to persist raw judge output for %s: %s",
                    exam.get("sample_id", "unknown"),
                    save_exc,
                )
            raise exc_parse

        # Ensure expected top-level keys are present (fail-fast for malformed judge)
        for key in ("baseline", "adapter", "reasoning"):
            if key not in parsed:
                raise ValueError(f"Missing key '{key}' in judge response")

        # Normalize numeric dimensions and fill defaults
        normalized = normalize_judge_response(parsed)

        # Log score with sanitized reasoning (reasoning is NOT logged at DEBUG without sanitization)
        adapter_composite = sum(
            normalized["adapter"][d] * w for d, w in SCORING_WEIGHTS.items()
        )
        logger.debug(
            "  Judge scores — adapter composite: %.3f",
            adapter_composite,
        )
        # At INFO level, log a sanitized summary of reasoning if needed
        if logger.isEnabledFor(logging.INFO):
            reasoning_summary = _sanitize_for_logging(normalized.get("reasoning", ""), max_length=100)
            if reasoning_summary:
                logger.info("  Judge reasoning (sanitized): %s", reasoning_summary)

        return normalized

    except Exception as exc:
        msg = f"LLM judge failed for {exam.id}: {exc}"
        if raw_path:
            msg += f" — raw output saved to {raw_path}"
        logger.error(msg)
        raise PromptGenerationError(msg) from exc
