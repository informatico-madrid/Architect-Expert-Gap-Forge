#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Backtracking rewriter core engine.

This module provides the async rewrite pipeline and single-record rewrite logic.

Public API
----------
apply_backtracking_rewrite(record, client, config) -- Apply rewrite to single record
rewrite_pipeline(input_path, output_path, config) -- Run full pipeline
load_jsonl(path)      -- Load records from JSONL
save_jsonl(records, path) -- Save records to JSONL
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from pathlib import Path
from typing import Protocol, Sequence, runtime_checkable

from src.schemas.common import RawRecord

from .backtracking_config import BacktrackingConfig, PipelineReport, _PROMPT_BACKTRACKING_PATH, _PROMPT_RECONSTRUCTION_PATH
from .backtracking_helpers import (
    _RejectionSamplingError,
    _format_seconds,
    _get_assistant_content,
    _load_prompt_file,
    extract_think_block,
    replace_think_block,
)
from .backtrack_strategy import (
    _load_governance_context,
    _load_legacy_regexes,
    _validate_resolution_no_legacy,
    build_rewrite_prompt,
    classify_rewrite_strategy,
    passes_backtracking_filter,
)

logger = logging.getLogger(__name__)

__all__ = [
    "apply_backtracking_rewrite",
    "rewrite_pipeline",
    "load_jsonl",
    "save_jsonl",
]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CHARS_PER_TOKEN: int = 4
_THINK_CLOSE_TAG: str = "</think>"
_MAX_RETRIES: int = 3

# ---------------------------------------------------------------------------
# Async inference interface
# ---------------------------------------------------------------------------


@runtime_checkable
class _AsyncGenerateClient(Protocol):
    """Minimal async inference interface consumed by the rewrite pipeline."""

    async def generate(
        self,
        prompt: str,
        *,
        system_prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> str: ...  # pragma: no cover — protocol stub


class _VLLMAsyncAdapter:
    """Async vLLM / OpenAI-compatible inference adapter.

    Wraps ``openai.AsyncOpenAI`` and exposes the ``_AsyncGenerateClient``
    protocol.  Instantiation of the SDK client is deferred to ``__init__``
    so that importing this module does not create network connections.
    """

    def __init__(self, api_url: str, model: str) -> None:
        from openai import AsyncOpenAI  # deferred — no import-time side effects

        self._client = AsyncOpenAI(base_url=api_url, api_key="EMPTY")
        self._model = model

    async def generate(
        self,
        prompt: str,
        *,
        system_prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> str:
        """Send a single generate request to the vLLM endpoint."""
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def load_jsonl(path: Path) -> list[RawRecord]:
    """Load a JSONL file into a list of records."""
    records: list[RawRecord] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def save_jsonl(records: Sequence[RawRecord], path: Path) -> None:
    """Write records to a JSONL file atomically (write-then-rename)."""
    tmp_path = path.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    tmp_path.rename(path)
    logger.info("Wrote %d records to %s", len(records), path)


# ---------------------------------------------------------------------------
# Audit helpers
# ---------------------------------------------------------------------------


def _setup_audit_dir(audit_dir: str | None) -> Path | None:
    """Create a timestamped audit run directory, returning it or ``None``."""
    if not audit_dir:
        return None
    try:
        base = Path(audit_dir)
        ts = time.strftime("%Y%m%d_%H%M%S")
        run_dir = base / f"backtracking_{ts}"
        run_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Audit enabled; records will be saved to %s", run_dir)
        return run_dir
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Could not create audit directory %s (%s); continuing without audit",
            audit_dir,
            exc,
        )
        return None


def _emit_audit_file(result: RawRecord, audit_run_dir: Path) -> None:
    """Write the full output record as pretty-printed JSON for human inspection."""
    safe_id = str(result.get("id", "unknown")).replace("/", "_")
    out_file = audit_run_dir / f"{safe_id}.json"
    try:
        out_file.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.debug("Audit record written to %s", out_file)
    except Exception as exc:  # noqa: BLE001
        logger.debug(
            "Failed to write audit file for id=%s: %s", result.get("id", "?"), exc
        )


# ---------------------------------------------------------------------------
# Single-record rewrite (async)
# ---------------------------------------------------------------------------


async def apply_backtracking_rewrite(
    record: RawRecord,
    client: object,
    config: BacktrackingConfig,
    *,
    _system_bt: str | None = None,
    _system_rc: str | None = None,
    _governance_context: str | None = None,
    _legacy_regexes: tuple[re.Pattern[str], ...] = (),
) -> RawRecord | None:
    """Apply backtracking rewrite to a single record (async).

    Parameters
    ----------
    record:
        Source training record.
    client:
        An async inference client that implements ``_AsyncGenerateClient``
        (i.e. has ``async def generate(prompt, *, system_prompt, max_tokens,
        temperature) -> str``).
    config:
        Pipeline configuration.
    _system_bt:
        Pre-loaded backtracking system prompt text.  Internal keyword argument
        used by the pipeline to avoid repeated file reads.
    _system_rc:
        Pre-loaded trace-reconstruction system prompt text.  Same as above.
    _governance_context:
        Raw text of ``HA_MASTER_GUIDE_2026.md`` to inject in the user message.
        When ``None`` prompts are sent without the governance context block.
    _legacy_regexes:
        Compiled legacy regex patterns for post-generation rejection sampling.
        When non-empty, the resolution half of the generated think block is
        validated; records that still contain legacy code are discarded.

    Returns
    -------
    The rewritten record with updated metadata, or ``None`` if all retries
    fail **or** the generated reasoning fails rejection sampling.

    Sacred Constraint
    -----------------
    Content at and after ``
</think>

`` is **never** modified.
    """
    strategy = classify_rewrite_strategy(record)

    assistant = _get_assistant_content(record)
    think_text, _ = extract_think_block(assistant)

    logger.debug(
        "Applying backtracking rewrite for id=%s strategy=%s",
        record.get("id", "unknown"),
        strategy,
    )

    # Skip inference for pass_through / skip strategies
    if strategy in ("pass_through", "skip"):
        # Still update metadata to track the pass-through
        metadata = dict(record.get("metadata") or {})
        metadata["backtracking_applied"] = False
        metadata["backtracking_strategy"] = strategy
        return {**record, "metadata": metadata}

    # Build prompts (loads prompt files only when needed)
    sys_prompt, user_prompt = build_rewrite_prompt(
        record,
        strategy,
        system_bt=_system_bt,
        system_rc=_system_rc,
        governance_context=_governance_context,
        language=config.language,
    )

    if not sys_prompt or not user_prompt:
        logger.warning(
            "Empty prompts for id=%s strategy=%s; skipping",
            record.get("id", "unknown"),
            strategy,
        )
        return None

    # Retry loop with exponential backoff
    new_think: str | None = None
    last_error = "unknown"
    inf_start = time.monotonic()

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            # Run inference
            raw = await client.generate(
                user_prompt,
                system_prompt=sys_prompt,
                max_tokens=config.max_generation_tokens,
                temperature=config.temperature,
            )

            # Post-process: ensure we have content after <filepath> tag and emit the real,
            # clean answer AFTER the closing tag.  We must take what comes
            # AFTER </think>, not before.
            # For non-thinking models (or when the tag is absent) raw already
            # contains the clean answer and we leave it untouched.
            if _THINK_CLOSE_TAG in raw:
                raw = raw[raw.find(_THINK_CLOSE_TAG) + len(_THINK_CLOSE_TAG) :]
            raw = raw.strip()

            # Sanitize code fences / tool-calls leaked into reasoning
            from .backtracking_helpers import _sanitize_generated_reasoning

            cleaned = _sanitize_generated_reasoning(raw)
            if not cleaned:
                raise ValueError("Sanitized LLM output is empty — retrying")

            new_think = cleaned
            break  # success — exit retry loop

        except Exception as exc:
            last_error = str(exc)
            logger.debug(
                "Attempt %d/%d failed for id=%s: %s",
                attempt,
                _MAX_RETRIES,
                record.get("id", "unknown"),
                last_error,
            )
            if attempt < _MAX_RETRIES:
                await asyncio.sleep(0.5 * attempt)  # exponential back-off

    if not new_think:
        logger.warning(
            "All %d retries exhausted for id=%s (strategy=%s). Last error: %s",
            _MAX_RETRIES,
            record.get("id", "unknown"),
            strategy,
            last_error,
        )
        return None

    inf_elapsed = time.monotonic() - inf_start
    if new_think != (raw if new_think != raw else new_think):  # detect sanitization
        logger.debug(
            "LLM output sanitized for id=%s (len before → after sanitization)",
            record.get("id", "unknown"),
        )
    logger.debug(
        "Inference completed for id=%s strategy=%s in %.2fs",
        record.get("id", "unknown"),
        strategy,
        inf_elapsed,
    )

    # -------------------------------------------------------------------
    # Post-generation rejection sampling (Split Validation)
    # Only the *resolution half* of new_think is checked so that the
    # intentional Legacy Impulse in the first half is not penalised.
    # The sacred code block is also validated.
    # -------------------------------------------------------------------
    if _legacy_regexes and strategy not in ("pass_through", "skip"):
        _, code_rest = extract_think_block(assistant)
        passed, reject_reason = _validate_resolution_no_legacy(
            new_think,
            code_rest,
            _legacy_regexes,
        )
        if not passed:
            logger.warning(
                "Rejection sampling DISCARDED id=%s strategy=%s: %s",
                record.get("id", "unknown"),
                strategy,
                reject_reason,
            )
            raise _RejectionSamplingError(reject_reason)

    # Replace think block, preserving sacred code
    new_content = replace_think_block(assistant, new_think)

    # CRITICAL: Verify sacred constraint - code after the </think> tag
    # must be byte-identical to the original. If not, restore from original.
    _, original_code_rest = extract_think_block(assistant)
    _, new_code_rest = extract_think_block(new_content)
    if original_code_rest != new_code_rest:
        # Code was modified - restore from original (sacred constraint enforcement)
        logger.warning(
            "Sacred constraint violation detected for id=%s: restoring original code",
            record.get("id", "unknown"),
        )
        new_content = f"{new_think}{_THINK_CLOSE_TAG}{original_code_rest}"

    # Shallow-copy conversation with updated assistant content
    conversation = list(record.get("conversation", []))
    for i, msg in enumerate(conversation):
        if isinstance(msg, dict) and msg.get("role") == "assistant":
            conversation[i] = {**msg, "content": new_content}
            break

    metadata = dict(record.get("metadata") or {})
    metadata["backtracking_applied"] = True
    metadata["backtracking_strategy"] = strategy
    metadata["original_think_chars"] = len(think_text)
    metadata["rewritten_think_chars"] = len(new_think)

    return {**record, "conversation": conversation, "metadata": metadata}


# ---------------------------------------------------------------------------
# Pipeline orchestrator (async)
# ---------------------------------------------------------------------------


async def rewrite_pipeline(
    input_path: Path,
    output_path: Path,
    config: BacktrackingConfig,
    client: object | None = None,
) -> PipelineReport:
    """Run the full backtracking rewrite pipeline (async).

    Parameters
    ----------
    input_path:
        Path to the source JSONL dataset.
    output_path:
        Path for the transformed output JSONL.
    config:
        Pipeline configuration.
    client:
        An async inference client implementing ``_AsyncGenerateClient``.
        When ``None``, a :class:`_VLLMAsyncAdapter` is instantiated from
        ``config``.

    Returns
    -------
    :class:`PipelineReport` summarising the run.
    """
    if client is None:
        client = _VLLMAsyncAdapter(
            api_url=config.vllm_api_url,
            model=config.vllm_model,
        )

    # Load required prompt templates once for the entire batch.
    # Raises FileNotFoundError with bootstrap instructions if a file is missing.
    sys_bt = _load_prompt_file(
        config.backtracking_system_prompt_path,
        _PROMPT_BACKTRACKING_PATH,
    )
    sys_rc = _load_prompt_file(
        config.reconstruction_system_prompt_path,
        _PROMPT_RECONSTRUCTION_PATH,
    )

    # Load the HA 2026 governance context once for the entire batch.
    # Returns None (with a WARNING) when the file is absent; other stages continue.
    governance_context = _load_governance_context(config)

    # Load legacy regex patterns for post-generation rejection sampling.
    # Returns an empty tuple (with a WARNING) when the file is absent; the
    # pipeline continues without rejection sampling rather than aborting.
    legacy_regexes: tuple[re.Pattern[str], ...] = ()
    if config.legacy_patterns_file:
        legacy_regexes = _load_legacy_regexes(config.legacy_patterns_file)

    records = load_jsonl(input_path)
    total_records = len(records)
    eligible = [r for r in records if passes_backtracking_filter(r, config)]
    eligible_count = len(eligible)
    filtered_out = total_records - eligible_count

    logger.info(
        "Loaded %d records from %s (%d eligible, %d filtered out) | workers=%d",
        total_records,
        input_path,
        eligible_count,
        filtered_out,
        config.workers,
    )

    audit_run_dir = _setup_audit_dir(config.audit_dir)

    # Concurrency primitives
    semaphore = asyncio.Semaphore(config.workers)
    io_lock = asyncio.Lock()  # guards all shared mutable state below

    # Shared mutable state (mutated only under io_lock)
    output: list[RawRecord] = []
    strategy_counts: dict[str, int] = {}
    rewritten = 0
    pass_through_count = 0
    failed = 0
    rejected = 0
    processed = 0

    start_time = time.monotonic()
    log_interval = max(config.batch_size, 1)

    async def _bounded_rewrite(record: RawRecord) -> None:
        nonlocal rewritten, pass_through_count, failed, rejected, processed

        try:
            async with semaphore:
                result = await apply_backtracking_rewrite(
                    record,
                    client,
                    config,
                    _system_bt=sys_bt,
                    _system_rc=sys_rc,
                    _governance_context=governance_context,
                    _legacy_regexes=legacy_regexes,
                )
        except _RejectionSamplingError:
            async with io_lock:
                processed += 1
                rejected += 1
                logger.info(
                    "Rejected id=%s (processed %d/%d, rejected so far: %d)",
                    record.get("id", "?"),
                    processed,
                    eligible_count,
                    rejected,
                )
            return

        async with io_lock:
            processed += 1

            if result is None:
                failed += 1
                logger.warning(
                    "Rewrite failed for id=%s (processed %d/%d)",
                    record.get("id", "?"),
                    processed,
                    eligible_count,
                )
                return

            strategy = (result.get("metadata") or {}).get(
                "backtracking_strategy", "unknown"
            )
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1

            if strategy in ("pass_through", "skip"):
                pass_through_count += 1
            else:
                rewritten += 1

            output.append(result)

            # Per-record terminal feedback
            try:
                assistant_after = _get_assistant_content(result)
                new_think_after, _ = extract_think_block(assistant_after)
                excerpt = " ".join(new_think_after.strip().splitlines())
                if len(excerpt) > 300:
                    excerpt = excerpt[:297] + "..."
                logger.info(
                    "id=%s strategy=%s new_think_len=%d excerpt=%s",
                    result.get("id", "?"),
                    strategy,
                    len(new_think_after),
                    excerpt,
                )
            except Exception:  # noqa: BLE001
                logger.debug(
                    "Could not extract think text for id=%s", result.get("id", "?")
                )

            # Audit: full record as JSON
            if audit_run_dir is not None:
                _emit_audit_file(result, audit_run_dir)

            if processed % log_interval == 0:
                elapsed = time.monotonic() - start_time
                rate = processed / elapsed if elapsed > 0 else 0.0
                pct = (processed / eligible_count * 100.0) if eligible_count else 0.0
                logger.info(
                    "Progress %d/%d eligible (%.1f%%) — "
                    "rewritten=%d pass=%d failed=%d rejected=%d elapsed=%s rate=%.2f/s",
                    processed,
                    eligible_count,
                    pct,
                    rewritten,
                    pass_through_count,
                    failed,
                    rejected,
                    _format_seconds(time.monotonic() - start_time),
                    rate,
                )

    await asyncio.gather(*[_bounded_rewrite(r) for r in eligible])

    save_jsonl(output, output_path)

    total_elapsed = time.monotonic() - start_time
    total_rate = processed / total_elapsed if total_elapsed > 0 else 0.0
    logger.info(
        "Pipeline complete: %d output records | elapsed=%s rate=%.2f/s "
        "rewritten=%d pass=%d failed=%d rejected=%d filtered=%d",
        len(output),
        _format_seconds(total_elapsed),
        total_rate,
        rewritten,
        pass_through_count,
        failed,
        rejected,
        filtered_out,
    )

    return PipelineReport(
        total_input=total_records,
        filtered_out=filtered_out,
        rewritten=rewritten,
        pass_through=pass_through_count,
        failed=failed,
        rejected=rejected,
        total_output=len(output),
        strategy_counts=strategy_counts,
    )
