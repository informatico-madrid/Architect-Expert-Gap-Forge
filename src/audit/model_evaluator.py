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

Environment
-----------
  AEGF_VLLM_API_URL     vLLM endpoint    (default: http://localhost:8000/v1)
  AEGF_AUDIT_DIR        Output folder    (default: data/audit)
  AEGF_SAMPLE_SIZE      Records/sample   (default: 5)
  AEGF_BASE_MODEL       Base model id    (default: qwen3-30b-a3b-thinking-fp8)
  AEGF_ADAPTER_MODEL    Adapter model    (default: platinum_adapter)
  AEGF_JUDGE_MODEL      Professor model  (default: same as base model)
  AEGF_MAX_TOKENS       Max gen tokens   (default: 65536)
  AEGF_TEMPERATURE      Sampling temp    (default: 0.3)
  AEGF_RETRIES          API retry count  (default: 3)
  AEGF_RETRY_DELAY      Retry backoff s  (default: 5.0)

  # Professor/Judge backend (Google Gemini — avoids using local GPU resources)
  AEGF_PROFESSOR_BACKEND  gemini|vllm|auto   (default: auto = gemini if GOOGLE_API_KEY set)
  AEGF_GEMINI_MODEL       Gemini model name  (default: gemini-2.0-flash)
  GOOGLE_API_KEY          Google API key     (required when using Gemini backend)
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

# Optional: Google Gemini SDK — professor calls run on Gemini to avoid
# competing with local GPU training on vLLM.
_GEMINI_AVAILABLE = False
try:
    from google import genai as _genai              # type: ignore[import]
    from google.genai import types as _genai_types  # type: ignore[import]
    _GEMINI_AVAILABLE = True
except ImportError:
    _genai = None        # type: ignore[assignment]
    _genai_types = None  # type: ignore[assignment]

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
DEFAULT_JUDGE_MODEL = os.getenv("AEGF_JUDGE_MODEL", DEFAULT_BASE_MODEL)
DEFAULT_MAX_TOKENS = int(os.getenv("AEGF_MAX_TOKENS", "65536"))   # 64 k — no cut-off
DEFAULT_TEMPERATURE = float(os.getenv("AEGF_TEMPERATURE", "0.3"))
DEFAULT_RETRIES = int(os.getenv("AEGF_RETRIES", "3"))
DEFAULT_RETRY_DELAY = float(os.getenv("AEGF_RETRY_DELAY", "5.0"))
# Professor/Judge backend
DEFAULT_PROFESSOR_BACKEND = os.getenv("AEGF_PROFESSOR_BACKEND", "auto")
DEFAULT_GEMINI_MODEL = os.getenv("AEGF_GEMINI_MODEL", "gemini-2.0-flash")

# Scoring weights per LLM-judged dimension
SCORING_WEIGHTS = {
    "ha_modernity": 0.30,
    "reasoning_depth": 0.25,
    "functionality": 0.25,
    "completeness": 0.12,
    "style": 0.08,
}

# ---------------------------------------------------------------------------
# HA 2026 System Prompt — injected into every student inference call
# ---------------------------------------------------------------------------

HA_SYSTEM_PROMPT_2026 = """\
You are an expert Home Assistant 2026 integration developer.
Always include a <think>...</think> reasoning block BEFORE writing any code.
You MUST follow these architectural rules:

ARCHITECTURE RULES — HA 2026
=============================
1. ConfigEntry data  : Use `entry.runtime_data` typed via a TypeAlias.
                       NEVER use `hass.data[DOMAIN]`.
2. Platform setup    : `await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)`
                       (plural). NEVER singular `async_forward_entry_setup`.
3. Device classes    : `SensorDeviceClass.TEMPERATURE` enum — NEVER legacy
                       `SENSOR_DEVICE_CLASS_TEMPERATURE` or bare strings.
4. Unit constants    : `UnitOfTemperature.CELSIUS` enum — NEVER `TEMP_CELSIUS`.
5. Entity categories : `EntityCategory.CONFIG` enum — NEVER `ENTITY_CATEGORY_CONFIG`.
6. Error handling    : `ConfigEntryNotReady` for transient failures,
                       `ConfigEntryAuthFailed` for auth errors,
                       `UpdateFailed` inside coordinator `_async_update_data`.
7. Coordinator       : All data fetching via `DataUpdateCoordinator`.
                       Entities must subclass `CoordinatorEntity`.
8. Typing            : Full type annotations. `Final` for module-level constants.
9. Code quality      : No `# TODO`, no `# ...`, no placeholder stubs.
                       Return production-ready, compilable code.
"""

# ---------------------------------------------------------------------------
# Professor prompts — exam generation and LLM-as-Judge
# ---------------------------------------------------------------------------

PROFESSOR_EXAM_SYSTEM = """\
You are a senior Home Assistant 2026 architect designing certification exam questions.
Your exams test deep understanding of LDI (Legacy-Detection-Index) migration patterns
and HA 2026 architecture — NOT memorisation of existing code.
"""

PROFESSOR_EXAM_USER_TMPL = """\
Design a NEW and complex exam question based on this integration fragment.

Fragment     : {fragment_name}
Source file  : {source_file}
Example type : {example_type}  (LDI score: {ldi:.3f})

Reference Gold implementation (context only — do NOT include it in the question):
```python
{reference_code}
```

Requirements for the question:
- Introduce a realistic variation (different sensor, added error path, new platform, etc.)
- Require at least 2-3 of: entry.runtime_data, async_forward_entry_setups,
  SensorDeviceClass enum, DataUpdateCoordinator, CoordinatorEntity, ConfigEntryNotReady
- Cannot be answered by copying the reference code verbatim
- Must require a proper <think> reasoning block from the developer

Return ONLY a JSON object (no markdown wrapper) with this schema:
{{
  "exam_question": "<full question text, may include a partial legacy snippet to modernise>",
  "eval_criteria": [
    "<specific measurable criterion 1>",
    "<specific measurable criterion 2>",
    "<specific measurable criterion 3>"
  ],
  "target_patterns": ["<pattern1>", "<pattern2>"]
}}
"""

PROFESSOR_JUDGE_SYSTEM = """\
You are a senior Home Assistant 2026 code reviewer scoring developer exam responses.
Score objectively and strictly based on the rubric. Be precise — scores must reflect
real code quality, not intent.
"""

PROFESSOR_JUDGE_USER_TMPL = """\
Score these two exam responses using the rubric below.

EXAM QUESTION:
{exam_question}

EVALUATION CRITERIA:
{eval_criteria}

--- BASELINE RESPONSE (base model, no fine-tuning) ---
{baseline_response}

--- ADAPTER RESPONSE (LoRA fine-tuned model) ---
{adapter_response}

Score BOTH responses from 0.0 to 1.0 on each dimension:
1. ha_modernity    — Uses modern HA 2026 APIs (entry.runtime_data, plural setup,
                     enum device classes, DataUpdateCoordinator, etc.)
2. reasoning_depth — <think> block correctly identifies edge cases, migration
                     implications, and error paths
3. functionality   — Code is syntactically correct and would work in HA 2026
                     (no deprecated imports, correct method signatures)
4. completeness    — All required functions/classes from the question are implemented
5. style           — AEGF conventions: <think> present, no apology phrases,
                     docstrings, proper typing

Return ONLY a JSON object with this exact schema (no markdown wrapper):
{{
  "baseline": {{
    "ha_modernity": 0.0,
    "reasoning_depth": 0.0,
    "functionality": 0.0,
    "completeness": 0.0,
    "style": 0.0
  }},
  "adapter": {{
    "ha_modernity": 0.0,
    "reasoning_depth": 0.0,
    "functionality": 0.0,
    "completeness": 0.0,
    "style": 0.0
  }},
  "reasoning": "<2-3 sentences explaining key differences between the two responses>"
}}
"""

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
    """Multi-dimensional LLM-judged score for a single record comparison."""

    record_id: str
    example_type: str
    fragment_name: str
    ha_modernity: float = 0.0
    reasoning_depth: float = 0.0
    functionality: float = 0.0
    completeness: float = 0.0
    style: float = 0.0
    composite_score: float = 0.0
    delta_vs_baseline: float = 0.0
    judge_reasoning: str = ""
    notes: str = ""


@dataclass
class AuditReport:
    """Top-level audit report aggregating all evaluation results."""

    timestamp: str = ""
    dataset_path: str = ""
    base_model: str = ""
    adapter_model: str = ""
    judge_model: str = ""
    sample_size: int = 0
    type_distribution: Dict[str, int] = field(default_factory=dict)
    scorecards: List[ScoreCard] = field(default_factory=list)
    final_grade: float = 0.0
    verdict: str = ""


@dataclass
class ExamRecord:
    """A sample record augmented with a professor-generated exam question."""

    # Original sample fields
    id: str
    example_type: str
    evol_difficulty: str
    fragment_name: str
    source_file: str
    user_prompt: str          # original prompt (kept for reference)
    reference_response: str
    gold_injected: bool
    ldi: float
    # Exam fields generated by the professor
    exam_question: str = ""
    eval_criteria: List[str] = field(default_factory=list)
    target_patterns: List[str] = field(default_factory=list)


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


def persist_exam(exam_records: List[ExamRecord], audit_dir: str) -> Path:
    """Save professor-generated exam questions to disk."""
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


def load_exam(audit_dir: str) -> List[ExamRecord]:
    """Load persisted exam questions."""
    exam_path = Path(audit_dir) / "eval_exam.json"
    if not exam_path.exists():
        raise FileNotFoundError(
            f"No exam found at {exam_path}. Run 'generate-exam' mode first."
        )
    payload = json.loads(exam_path.read_text(encoding="utf-8"))
    records = [ExamRecord(**r) for r in payload["records"]]
    logger.info("Loaded exam: %d questions", len(records))
    return records


# ---------------------------------------------------------------------------
# Professor Backend — Gemini (remote) or vLLM (local)
# ---------------------------------------------------------------------------


def call_gemini(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: str = DEFAULT_GEMINI_MODEL,
    max_tokens: int = 2048,
    temperature: float = 0.7,
) -> str:
    """Call Google Gemini API and return the response text.

    Uses the `google-genai` SDK (pip install google-genai).
    Requires the GOOGLE_API_KEY environment variable.
    API calls are independent of the local GPU — safe to call while vLLM trains.
    """
    if not _GEMINI_AVAILABLE:
        raise RuntimeError(
            "google-genai not installed. Run: pip install google-genai"
        )
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY environment variable not set. "
            "Export it, add to .env, or use --professor-backend vllm"
        )

    client = _genai.Client(api_key=api_key)
    config = _genai_types.GenerateContentConfig(
        system_instruction=system_prompt or "",
        max_output_tokens=max_tokens,
        temperature=temperature,
        response_mime_type="text/plain",
    )
    t0 = time.perf_counter()
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=config,
    )
    latency = (time.perf_counter() - t0) * 1000
    logger.debug("  ← Gemini %s: %.0fms", model, latency)
    return response.text


def _resolve_professor_backend(backend: str) -> str:
    """Map 'auto' to the effective backend ('gemini' or 'vllm')."""
    if backend != "auto":
        return backend
    if _GEMINI_AVAILABLE and os.getenv("GOOGLE_API_KEY"):
        return "gemini"
    logger.debug(
        "GOOGLE_API_KEY not set or google-genai unavailable — routing professor to vllm"
    )
    return "vllm"


def _call_professor(
    prompt: str,
    system_prompt: Optional[str],
    professor_backend: str,
    gemini_model: str = DEFAULT_GEMINI_MODEL,
    vllm_judge_model: str = DEFAULT_JUDGE_MODEL,
    api_url: str = DEFAULT_API_URL,
    max_tokens: int = 1024,
    temperature: float = 0.7,
    retries: int = DEFAULT_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY,
) -> str:
    """Route a professor (exam-gen / judge) call to Gemini or vLLM.

    Gemini runs on Google's servers — does not compete with local GPU training.
    Falls back to vLLM automatically when GOOGLE_API_KEY is not set.
    """
    effective = _resolve_professor_backend(professor_backend)
    if effective == "gemini":
        logger.debug("Professor → Gemini (%s)", gemini_model)
        return call_gemini(
            prompt=prompt,
            system_prompt=system_prompt,
            model=gemini_model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    logger.debug("Professor → vLLM (%s)", vllm_judge_model)
    result = call_vllm_with_retry(
        prompt=prompt,
        model=vllm_judge_model,
        api_url=api_url,
        max_tokens=max_tokens,
        temperature=temperature,
        system_prompt=system_prompt,
        retries=retries,
        retry_delay=retry_delay,
    )
    return result.response


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
    """Ask the professor model to synthesise a novel exam question for a sample.

    Routes to Gemini (default when GOOGLE_API_KEY set) or vLLM.
    Parses the JSON response from the professor and returns an ExamRecord.
    Falls back to the original user_prompt if the professor response is invalid.
    In validate mode uses reduced token budget (512) for fast end-to-end testing.
    """
    ref_code = sample.reference_response
    # Truncate reference to ~4000 chars to stay within context for prompt
    if len(ref_code) > 4000:
        ref_code = ref_code[:4000] + "\n... [truncated] ..."

    user_msg = PROFESSOR_EXAM_USER_TMPL.format(
        fragment_name=sample.fragment_name,
        source_file=sample.source_file,
        example_type=sample.example_type,
        ldi=sample.ldi,
        reference_code=ref_code,
    )

    exam_question = ""
    eval_criteria: List[str] = []
    target_patterns: List[str] = []

    max_exam_tokens = 512 if validate else 1024
    try:
        raw = _call_professor(
            prompt=user_msg,
            system_prompt=PROFESSOR_EXAM_SYSTEM,
            professor_backend=professor_backend,
            gemini_model=gemini_model,
            vllm_judge_model=judge_model,
            api_url=api_url,
            max_tokens=max_exam_tokens,
            temperature=0.7,
            retries=retries,
            retry_delay=retry_delay,
        )
        raw = raw.strip()
        # Strip accidental markdown fences
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
        raw = re.sub(r"```\s*$", "", raw, flags=re.MULTILINE).strip()
        parsed = json.loads(raw)
        exam_question = parsed.get("exam_question", "").strip()
        eval_criteria = parsed.get("eval_criteria", [])
        target_patterns = parsed.get("target_patterns", [])
        logger.info("  Exam generated for %s (%d criteria)", sample.id, len(eval_criteria))
    except (json.JSONDecodeError, KeyError, Exception) as exc:
        logger.warning(
            "Could not parse exam for %s: %s — falling back to original prompt",
            sample.id, exc,
        )
        exam_question = sample.user_prompt

    return ExamRecord(
        id=sample.id,
        example_type=sample.example_type,
        evol_difficulty=sample.evol_difficulty,
        fragment_name=sample.fragment_name,
        source_file=sample.source_file,
        user_prompt=sample.user_prompt,
        reference_response=sample.reference_response,
        gold_injected=sample.gold_injected,
        ldi=sample.ldi,
        exam_question=exam_question,
        eval_criteria=eval_criteria,
        target_patterns=target_patterns,
    )


# ---------------------------------------------------------------------------
# Inference Engine
# ---------------------------------------------------------------------------


def call_vllm(
    prompt: str,
    model: str,
    api_url: str = DEFAULT_API_URL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = DEFAULT_TEMPERATURE,
    system_prompt: Optional[str] = None,
) -> InferenceResult:
    """Send a chat completion request to the vLLM OpenAI-compatible API."""
    url = f"{api_url}/chat/completions"
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": 0.95,
    }

    t0 = time.perf_counter()
    try:
        resp = requests.post(url, json=payload, timeout=600)
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


def call_vllm_with_retry(
    prompt: str,
    model: str,
    api_url: str = DEFAULT_API_URL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = DEFAULT_TEMPERATURE,
    system_prompt: Optional[str] = None,
    retries: int = DEFAULT_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY,
) -> InferenceResult:
    """Wrapper around call_vllm with exponential-backoff retries.

    Retries on transient HTTP errors (5xx) and connection timeouts.
    Raises on 4xx (client errors) or after exhausting all attempts.
    """
    last_exc: Exception = RuntimeError("No attempts made")
    for attempt in range(1, retries + 1):
        try:
            return call_vllm(
                prompt=prompt,
                model=model,
                api_url=api_url,
                max_tokens=max_tokens,
                temperature=temperature,
                system_prompt=system_prompt,
            )
        except requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else 0
            if 400 <= status < 500:
                logger.error("Client error %d — not retrying: %s", status, exc)
                raise
            last_exc = exc
            logger.warning(
                "HTTP %d on attempt %d/%d — retrying in %.0fs",
                status, attempt, retries, retry_delay * attempt,
            )
        except requests.exceptions.Timeout as exc:
            last_exc = exc
            logger.warning(
                "Timeout on attempt %d/%d — retrying in %.0fs",
                attempt, retries, retry_delay * attempt,
            )
        except requests.exceptions.RequestException as exc:
            last_exc = exc
            logger.warning(
                "Request error on attempt %d/%d: %s", attempt, retries, exc
            )
        time.sleep(retry_delay * attempt)
    logger.error("All %d attempts failed. Last error: %s", retries, last_exc)
    raise last_exc


def run_inference(
    samples: List[Any],   # SampleRecord | ExamRecord
    model: str,
    api_url: str = DEFAULT_API_URL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = DEFAULT_TEMPERATURE,
    system_prompt: Optional[str] = None,
    retries: int = DEFAULT_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY,
) -> List[InferenceResult]:
    """Run inference on a sample list.

    Accepts both SampleRecord (uses user_prompt) and ExamRecord (uses
    exam_question when available, falls back to user_prompt).
    Injects HA_SYSTEM_PROMPT_2026 when system_prompt is not explicitly provided.
    """
    effective_system = system_prompt if system_prompt is not None else HA_SYSTEM_PROMPT_2026
    results: List[InferenceResult] = []
    total = len(samples)

    for idx, sample in enumerate(samples, 1):
        # Prefer exam_question over raw user_prompt
        prompt = getattr(sample, "exam_question", "") or sample.user_prompt
        logger.info(
            "[%d/%d] Inferring %s (type=%s, frag=%s) with model=%s",
            idx, total, sample.id, sample.example_type,
            sample.fragment_name, model,
        )
        result = call_vllm_with_retry(
            prompt=prompt,
            model=model,
            api_url=api_url,
            max_tokens=max_tokens,
            temperature=temperature,
            system_prompt=effective_system,
            retries=retries,
            retry_delay=retry_delay,
        )
        result.record_id = sample.id
        results.append(result)
        logger.info("  → %d tokens in %.0fms", result.token_count, result.latency_ms)

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
# Scoring Engine — LLM-as-Judge (primary) + regex fallback
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


# --- Legacy / modernity detection patterns (used for regex fallback) ---

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


def _regex_score_single(response: str, reference: str) -> Dict[str, float]:
    """Pure-regex fallback scorer. Returns scores in the LLM-judge dimension format."""
    code = _extract_code_blocks(response)
    ref_code = _extract_code_blocks(reference)

    # ha_modernity via legacy/modern pattern ratio
    legacy_hits = sum(1 for p, _ in LEGACY_PATTERNS if re.search(p, code))
    modern_hits = sum(1 for p, _ in MODERN_PATTERNS if re.search(p, code))
    total_pats = legacy_hits + modern_hits
    ha_modernity = (modern_hits / total_pats) if total_pats > 0 else 0.5

    # reasoning_depth via <think> analysis
    think = _extract_think_block(response)
    if think:
        indicators = [
            r"\b(because|therefore|since|given that)\b",
            r"\b(step \d|first|second|third|finally)\b",
            r"\b(import|from\s+\w+\s+import)\b",
            r"\b(edge case|error handling|exception)\b",
            r"\b(async|await|coordinator|runtime_data)\b",
        ]
        hits = sum(1 for p in indicators if re.search(p, think, re.IGNORECASE))
        words = len(think.split())
        raw_rd = min(hits / 4.0, 1.0)
        if words < 20:
            raw_rd *= 0.5
        elif words > 3000:
            raw_rd *= 0.7
        reasoning_depth = round(raw_rd, 3)
    else:
        reasoning_depth = 0.0

    # functionality — proxy: modern imports present + no syntax-breaking patterns
    functionality = min(ha_modernity + 0.1, 1.0)

    # completeness — function/class coverage vs reference
    targets = set(re.findall(r"\b(?:def|class|async def)\s+(\w+)", ref_code))
    if targets:
        hits_comp = sum(1 for t in targets if t in code)
        completeness = hits_comp / len(targets)
    else:
        completeness = 0.5

    # style consistency
    style_checks = [
        bool(re.search(r"<think>", response)),
        bool(re.search(r"<tool_call>|<write_action>|```python", response)),
        not bool(re.search(r"(?:I'm sorry|I cannot|As an AI)", response, re.IGNORECASE)),
        bool(re.search(r'""".*?"""', response, re.DOTALL)),
    ]
    style = sum(style_checks) / len(style_checks)

    return {
        "ha_modernity": round(ha_modernity, 3),
        "reasoning_depth": reasoning_depth,
        "functionality": round(functionality, 3),
        "completeness": round(completeness, 3),
        "style": round(style, 3),
    }


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
) -> Dict[str, Any]:
    """Ask the professor model to score baseline vs adapter on the rubric.

    Routes to Gemini (default when GOOGLE_API_KEY set) or vLLM.
    Returns a dict with keys 'baseline', 'adapter' (each a scores dict)
    and 'reasoning' (str). Falls back to regex scoring on any error.
    In validate mode uses reduced token budget (512) for fast end-to-end testing.
    """
    criteria_text = "\n".join(
        f"  {i+1}. {c}" for i, c in enumerate(exam.eval_criteria)
    ) if exam.eval_criteria else "  (no specific criteria defined)"

    # Truncate responses to avoid exceeding context
    b_resp = baseline_resp[:6000] + "\n...[truncated]" if len(baseline_resp) > 6000 else baseline_resp
    a_resp = adapter_resp[:6000] + "\n...[truncated]" if len(adapter_resp) > 6000 else adapter_resp

    user_msg = PROFESSOR_JUDGE_USER_TMPL.format(
        exam_question=exam.exam_question or exam.user_prompt,
        eval_criteria=criteria_text,
        baseline_response=b_resp,
        adapter_response=a_resp,
    )

    max_judge_tokens = 512 if validate else 1024
    try:
        raw = _call_professor(
            prompt=user_msg,
            system_prompt=PROFESSOR_JUDGE_SYSTEM,
            professor_backend=professor_backend,
            gemini_model=gemini_model,
            vllm_judge_model=judge_model,
            api_url=api_url,
            max_tokens=max_judge_tokens,
            temperature=0.1,   # low temp for consistent scoring
            retries=retries,
            retry_delay=retry_delay,
        )
        raw = raw.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
        raw = re.sub(r"```\s*$", "", raw, flags=re.MULTILINE).strip()
        parsed = json.loads(raw)

        # Validate expected keys
        for key in ("baseline", "adapter", "reasoning"):
            if key not in parsed:
                raise ValueError(f"Missing key '{key}' in judge response")
        for section in ("baseline", "adapter"):
            for dim in ("ha_modernity", "reasoning_depth", "functionality", "completeness", "style"):
                if dim not in parsed[section]:
                    parsed[section][dim] = 0.5  # safe default
                else:
                    # clamp to [0, 1]
                    parsed[section][dim] = max(0.0, min(1.0, float(parsed[section][dim])))

        logger.debug("  Judge scores — adapter composite: %.3f",
                     sum(parsed["adapter"][d] * w for d, w in SCORING_WEIGHTS.items()))
        return parsed

    except Exception as exc:
        logger.warning(
            "LLM judge failed for %s: %s — falling back to regex", exam.id, exc
        )
        # Regex fallback — returns same structure without judge reasoning
        b_scores = _regex_score_single(baseline_resp, exam.reference_response)
        a_scores = _regex_score_single(adapter_resp, exam.reference_response)
        return {
            "baseline": b_scores,
            "adapter": a_scores,
            "reasoning": f"[regex fallback due to judge error: {exc}]",
        }


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
    """Compute a multi-dimensional LLM-judged scorecard comparing adapter vs baseline.

    Routes professor calls to Gemini or vLLM via _call_professor.
    Falls back transparently to regex scoring if the judge call fails.
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

    def _composite(scores: Dict[str, float]) -> float:
        return sum(scores.get(dim, 0.0) * weight for dim, weight in SCORING_WEIGHTS.items())

    adapter_composite = _composite(a)
    baseline_composite = _composite(b)
    delta = adapter_composite - baseline_composite

    # Diagnostic notes from regex (legacy/modern pattern detection)
    adapter_code = _extract_code_blocks(adapter_resp)
    notes_parts: List[str] = []
    for pat, desc in LEGACY_PATTERNS:
        if re.search(pat, adapter_code):
            notes_parts.append(f"⚠ Legacy: {desc}")
    for pat, desc in MODERN_PATTERNS:
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
    exam_records: List[ExamRecord],
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

    w(f"# AEGF Quality Gate — High-Fidelity Exam Report")
    w(f"")
    w(f"> Generated: {ts}")
    w(f"> Dataset: `{report.dataset_path}`")
    w(f"> Base Model: `{report.base_model}`")
    w(f"> Adapter Model: `{report.adapter_model}`")
    w(f"> Judge Model: `{report.judge_model}`")
    w(f"> Sample Size: {report.sample_size}")
    w(f"> Evaluation: LLM-as-Judge (Professor model) + regex fallback")
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
    if base_lat:
        w(f"| Baseline Avg Latency | {sum(base_lat)/len(base_lat):.0f}ms |")
    if adapt_lat:
        w(f"| Adapter Avg Latency | {sum(adapt_lat)/len(adapt_lat):.0f}ms |")
    w(f"")

    # Per-type breakdown
    w(f"## Score Breakdown by Example Type")
    w(f"")
    w(f"| Type | Count | Avg Score | Avg Δ |")
    w(f"|------|-------|-----------|-------|")
    for et in sorted(type_scores.keys()):
        scores = type_scores[et]
        et_deltas = [sc.delta_vs_baseline for sc in scorecards if sc.example_type == et]
        avg_sc = sum(scores) / len(scores) * 100
        avg_d = sum(et_deltas) / len(et_deltas) if et_deltas else 0.0
        w(f"| {et} | {len(scores)} | {avg_sc:.1f} | {avg_d:+.3f} |")
    w(f"")

    # Detailed scorecards table
    w(f"## Detailed Scorecards (LLM-as-Judge)")
    w(f"")
    w(
        f"| ID | Type | Fragment | HA Modern | Reasoning | Functional"
        f" | Complete | Style | **Composite** | **Δ** |"
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
            f"| {sc.ha_modernity:.2f} | {sc.reasoning_depth:.2f} "
            f"| {sc.functionality:.2f} | {sc.completeness:.2f} "
            f"| {sc.style:.2f} | **{sc.composite_score:.3f}** "
            f"| {sc.delta_vs_baseline:+.3f} |"
        )
    w(f"")

    # Scoring methodology
    w(f"## Scoring Methodology (LLM-as-Judge)")
    w(f"")
    w(f"The Professor model (`{report.judge_model}`) scores each exam response across 5 dimensions:")
    w(f"")
    w(f"| Dimension | Weight | Description |")
    w(f"|-----------|--------|-------------|")
    w(f"| HA Modernity | 30% | Uses entry.runtime_data, plural setup, enum device classes |")
    w(f"| Reasoning Depth | 25% | `<think>` block correctly identifies edge cases and migration paths |")
    w(f"| Functionality | 25% | Code compiles and runs correctly in HA 2026 |")
    w(f"| Completeness | 12% | All required functions/classes implemented |")
    w(f"| Style | 8% | AEGF conventions: `<think>` present, docstrings, no apologies |")
    w(f"")
    w(f"**Composite** = Σ(dimension × weight). **Δ** = adapter − baseline composite.")
    w(f"Falls back to regex scoring if judge API call fails.")
    w(f"")

    # Judge reasoning notes
    judged = [sc for sc in scorecards if sc.judge_reasoning and not sc.judge_reasoning.startswith("[regex")]
    if judged:
        w(f"## Judge Reasoning Highlights")
        w(f"")
        for sc in judged[:8]:  # cap at 8 to keep report readable
            short_id = sc.record_id[-12:]
            w(f"**{short_id}** ({sc.fragment_name}):")
            w(f"> {sc.judge_reasoning}")
            w(f"")

    # Pattern detection notes
    flagged = [sc for sc in scorecards if sc.notes]
    if flagged:
        w(f"## Regex Pattern Detection Notes")
        w(f"")
        for sc in flagged:
            w(f"- **{sc.record_id}** ({sc.fragment_name}): {sc.notes}")
        w(f"")

    w(f"---")
    w(f"")
    w(f"*Report generated by `src/audit/model_evaluator.py` — AEGF Quality Gate v2.0 (LLM-as-Judge)*")

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
        if not args.dataset:
            raise SystemExit("--dataset is required for 'sample' mode")
        records = load_dataset(args.dataset)
        samples = stratified_sample(records, args.sample_size)
        persist_sample(samples, args.audit_dir)

    dist = Counter(s.example_type for s in samples)
    logger.info("Sample distribution: %s", dict(dist))


def cmd_generate_exam(args: argparse.Namespace) -> None:
    """Professor model generates novel exam questions from the persisted sample."""
    exam_path = Path(args.audit_dir) / "eval_exam.json"
    if exam_path.exists() and not args.force:
        logger.info(
            "Exam already exists at %s (use --force to regenerate)", exam_path
        )
        exam_records = load_exam(args.audit_dir)
        logger.info("Loaded %d existing exam questions", len(exam_records))
        return

    samples = load_persisted_sample(args.audit_dir)
    judge_model = args.judge_model
    logger.info(
        "Generating %d exam questions with professor model: %s", len(samples), judge_model
    )

    exam_records: List[ExamRecord] = []
    total = len(samples)
    for idx, sample in enumerate(samples, 1):
        logger.info("[%d/%d] Generating exam for %s (%s)", idx, total, sample.id, sample.fragment_name)
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
        exam_records.append(record)

    persist_exam(exam_records, args.audit_dir)
    generated = sum(1 for r in exam_records if r.exam_question and r.exam_question != r.user_prompt)
    logger.info("Exam generation complete: %d/%d questions generated by professor", generated, total)


def cmd_baseline(args: argparse.Namespace) -> None:
    """Run baseline inference on exam questions with the base model."""
    # Prefer exam records; fall back to plain sample if exam not yet generated
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
    )
    persist_inference(results, "adapter", args.audit_dir)


def cmd_score(args: argparse.Namespace) -> None:
    """LLM-as-Judge scores adapter vs baseline and generates the audit report."""
    # Load exam records (with criteria) for judge context
    try:
        exam_records = load_exam(args.audit_dir)
    except FileNotFoundError:
        logger.warning("No exam found — scoring without exam criteria (fallback to regex)")
        raw_samples = load_persisted_sample(args.audit_dir)
        exam_records = [
            ExamRecord(
                **{k: getattr(s, k) for k in SampleRecord.__dataclass_fields__},
                exam_question=s.user_prompt,
            )
            for s in raw_samples
        ]

    baseline_results = load_inference("baseline", args.audit_dir)
    adapter_results = load_inference("adapter", args.audit_dir)

    baseline_map = {r.record_id: r for r in baseline_results}
    adapter_map = {r.record_id: r for r in adapter_results}
    judge_model = args.judge_model

    logger.info("Scoring %d records with judge model: %s", len(exam_records), judge_model)
    scorecards: List[ScoreCard] = []
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
        report, scorecards, exam_records, baseline_results, adapter_results, args.audit_dir
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
    args.model = None   # force use of base_model
    cmd_baseline(args)

    logger.info("--- Stage 4/5: Adapter Inference ---")
    args.model = None   # force use of adapter_model
    cmd_adapter(args)

    logger.info("--- Stage 5/5: LLM-as-Judge Scoring ---")
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
        "--judge-model",
        default=DEFAULT_JUDGE_MODEL,
        help=f"Professor/judge model for exam generation and scoring (default: {DEFAULT_JUDGE_MODEL})",
    )
    shared.add_argument(
        "--professor-backend",
        default=DEFAULT_PROFESSOR_BACKEND,
        choices=["auto", "gemini", "vllm"],
        help="Backend for professor/judge calls: auto|gemini|vllm (default: auto; auto selects gemini if GOOGLE_API_KEY is set)",
    )
    shared.add_argument(
        "--gemini-model",
        default=DEFAULT_GEMINI_MODEL,
        help=f"Gemini model name when professor-backend=gemini (default: {DEFAULT_GEMINI_MODEL})",
    )
    shared.add_argument(
        "--validate",
        action="store_true",
        help="1-example end-to-end flow test (Gemini→vLLM→Gemini) with minimal token spend",
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
        "--retries",
        type=int,
        default=DEFAULT_RETRIES,
        help=f"API retry attempts on transient errors (default: {DEFAULT_RETRIES})",
    )
    shared.add_argument(
        "--retry-delay",
        type=float,
        default=DEFAULT_RETRY_DELAY,
        help=f"Base retry backoff in seconds (multiplied by attempt) (default: {DEFAULT_RETRY_DELAY})",
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

        model_evaluator full --dataset foo.jsonl --base-model qwen3-... --adapter-model platinum_adapter
    """
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

    # Subcommands — each inherits all shared options via parents=[shared]
    sub = parser.add_subparsers(dest="mode", help="Evaluation stage")
    sub.add_parser("sample",        help="Stage 1: Extract stratified sample",         parents=[shared])
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
