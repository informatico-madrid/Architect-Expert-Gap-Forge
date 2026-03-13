#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Backtracking rewriter strategy selection and scoring.

This module provides functions for strategy classification, filtering,
prompt construction, and validation.

Public API
----------
classify_rewrite_strategy(record)  -- Classify the rewrite strategy for a record
build_rewrite_prompt(record, strategy) -- Build system/user prompts for rewriting
passes_backtracking_filter(record, cfg) -- Determine if record is eligible
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import yaml

from src.schemas.common import RawRecord

from .backtracking_config import BacktrackingConfig
from .backtracking_helpers import (
    _detect_language_hint,
    _extract_executable_code,
    _get_assistant_content,
    _load_prompt_file,
    _strip_python_comments,
    extract_think_block,
)

logger = logging.getLogger(__name__)

__all__ = [
    "classify_rewrite_strategy",
    "build_rewrite_prompt",
    "passes_backtracking_filter",
    "_load_governance_context",
    "_validate_resolution_no_legacy",
    "_load_legacy_regexes",
    "_extract_executable_code",
    "_strip_python_comments",
]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CHARS_PER_TOKEN: int = 4
_THINK_CLOSE_TAG: str = "</think>"

_PROMPT_BACKTRACKING_PATH: str = "configs/prompts/backtracking_system.txt"
_PROMPT_RECONSTRUCTION_PATH: str = "configs/prompts/reconstruction_system.txt"

# ---------------------------------------------------------------------------
# Legacy-pattern post-generation validation (Rejection Sampling)
# ---------------------------------------------------------------------------


def _load_legacy_regexes(path: str) -> tuple[re.Pattern[str], ...]:
    """Load compiled legacy regex patterns from a YAML taxonomy file.

    Expects a top-level ``legacy_patterns`` key containing a list of
    ``{pattern: ..., description: ...}`` dicts (same schema used by
    ``configs/stage_5_evaluation/ha_patterns.yaml``).

    Returns an empty tuple with a WARNING when the file is missing or
    contains no usable patterns — the pipeline continues without
    rejection sampling rather than aborting.
    """
    resolved = Path(path)
    if not resolved.exists():
        logger.warning(
            "Legacy patterns file not found: %s; post-generation rejection "
            "sampling is disabled",
            resolved,
        )
        return ()

    with open(resolved, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    raw_patterns = data.get("legacy_patterns", [])
    compiled: list[re.Pattern[str]] = []
    for entry in raw_patterns:
        regex_str = entry.get("pattern", "") if isinstance(entry, dict) else ""
        if not regex_str:
            continue
        try:
            compiled.append(re.compile(regex_str))
        except re.error as exc:
            logger.warning("Skipping invalid legacy regex %r: %s", regex_str, exc)

    logger.info(
        "Loaded %d legacy regex patterns from %s for rejection sampling",
        len(compiled),
        resolved,
    )
    return tuple(compiled)


def _validate_resolution_no_legacy(
    new_think: str,
    code_rest: str,
    legacy_regexes: tuple[re.Pattern[str], ...],
) -> tuple[bool, str]:
    """Executable-Code Validation — check that the resolution half is legacy-free.

    The generated think block follows a 4-step structure:

      1. Legacy Impulse  (first half — intentionally *names* deprecated APIs)
      2. Self-Evaluation
      3. Backtracking
      4. Modern Resolution  (second half — *executable code* must be clean)

    This function:

    1. Splits ``new_think`` at the midpoint (same as before — avoids penalising
       the intentional Legacy Impulse name-drop in the first half).
    2. **Extracts only executable code** from the resolution half (fenced
       blocks, ``<tool_call>`` JSON payloads) via :func:`_extract_executable_code`.
       Plain natural-language text — including BACKTRACKING sentences that
       *name* the legacy API in order to reject it — is ignored.
    3. **Strips Python comments** (``# ...``) from the extracted code via
       :func:`_strip_python_comments`.  Comments such as
       ``# FIX: migrated from hass.data`` are explanatory and must not trigger
       the filter; the *executable* call is what matters.
    4. Applies the legacy regex patterns to the cleaned code only.

    The same extraction + comment-stripping logic is applied to ``code_rest``
    (the sacred code block after ``
</think>

``) before checking it.

    Returns
    -------
    (True, "")
        Validation passed — no legacy patterns in executable code.
    (False, reason)
        Validation failed — ``reason`` describes which pattern matched.
    """
    if not legacy_regexes:
        return True, ""

    midpoint = len(new_think) // 2
    resolution_half = new_think[midpoint:]

    # ── Resolution half: check only extracted executable code (no comments) ──
    resolution_code = _extract_executable_code(resolution_half)
    resolution_code_clean = _strip_python_comments(resolution_code)

    for regex in legacy_regexes:
        match = regex.search(resolution_code_clean)
        if match:
            return False, (
                f"Legacy pattern {regex.pattern!r} found in executable code "
                f"of resolution half: {match.group()!r}"
            )

    # ── Sacred code block: extract executable code and strip comments ──────
    code_rest_exec = _extract_executable_code(code_rest)
    code_rest_clean = _strip_python_comments(code_rest_exec)

    for regex in legacy_regexes:
        match = regex.search(code_rest_clean)
        if match:
            return False, (
                f"Legacy pattern {regex.pattern!r} found in executable "
                f"code block: {match.group()!r}"
            )

    return True, ""


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------


def passes_backtracking_filter(record: RawRecord, config: BacktrackingConfig) -> bool:
    """Determine whether a record is eligible for the backtracking pipeline.

    Exclusions:
    - Type in ``config.excluded_types`` (e.g. theory).
    - Estimated total tokens exceed ``config.max_tokens``.
    - No ``</think>`` tag in assistant content.
    """
    metadata = record.get("metadata") or {}
    example_type = str(metadata.get("example_type", ""))

    if example_type in config.excluded_types:
        return False

    # Total conversation token estimate
    total_chars = sum(
        len(msg.get("content", ""))
        for msg in record.get("conversation", [])
        if isinstance(msg, dict)
    )
    if total_chars // _CHARS_PER_TOKEN > config.max_tokens:
        return False

    # Must have a think tag to split on
    assistant = _get_assistant_content(record)
    if _THINK_CLOSE_TAG not in assistant:
        return False

    return True


# ---------------------------------------------------------------------------
# Strategy classification
# ---------------------------------------------------------------------------


def classify_rewrite_strategy(record: RawRecord) -> str:
    """Classify the rewrite strategy for a record.

    Priority order:
      1. ``theory`` type → ``skip``
      2. ``legacy_detected=True`` → ``full_backtracking``
      3. ``gold_injected=True`` → ``trace_reconstruction``
      4. ``error_recovery`` type → ``error_first``
      5. ``contrast`` type → ``contrast_backtracking``
      6. Clean ``nominal`` → ``pass_through``
    """
    metadata = record.get("metadata") or {}
    example_type = str(metadata.get("example_type", ""))
    gold_injected = bool(metadata.get("gold_injected", False))
    legacy_detected = bool(metadata.get("legacy_detected", False))

    if example_type == "theory":
        return "skip"

    if legacy_detected:
        return "full_backtracking"

    if gold_injected:
        return "trace_reconstruction"

    if example_type == "error_recovery":
        return "error_first"

    if example_type == "contrast":
        return "contrast_backtracking"

    # Clean nominal — already high quality
    return "pass_through"


# ---------------------------------------------------------------------------
# Governance context loader
# ---------------------------------------------------------------------------


def _load_governance_context(config: BacktrackingConfig) -> str | None:
    """Load ``HA_MASTER_GUIDE_2026.md`` from *config.gap_dir* as injection text.

    Returns ``None`` with a WARNING when the file is absent — the pipeline
    continues without citation grounding rather than aborting.
    """
    path = Path(config.gap_dir) / "HA_MASTER_GUIDE_2026.md"
    if not path.exists():
        logger.warning(
            "Governance context file not found: %s; prompts will not include it",
            path,
        )
        return None
    content = path.read_text(encoding="utf-8").strip()
    limit = config.governance_context_chars
    if limit and len(content) > limit:
        content = content[:limit]
        logger.debug("Governance context truncated to %d chars", limit)
    logger.info("Loaded governance context from %s (%d chars)", path, len(content))
    return content


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------


def build_rewrite_prompt(
    record: RawRecord,
    strategy: str,
    *,
    system_bt: str | None = None,
    system_rc: str | None = None,
    governance_context: str | None = None,
    language: str | None = None,
) -> tuple[str, str]:
    """Build (system_prompt, user_prompt) for the given rewrite strategy.

    Parameters
    ----------
    record:
        Source training record.
    strategy:
        One of the strategy names returned by :func:`classify_rewrite_strategy`.
    system_bt:
        Pre-loaded backtracking system prompt text.  Falls back to the
        built-in default when ``None``.
    system_rc:
        Pre-loaded trace-reconstruction system prompt text.  Falls back to
        the built-in default when ``None``.
    governance_context:
        Raw text of ``HA_MASTER_GUIDE_2026.md`` to inject as a
        ``[HA 2026 GOVERNANCE CONTEXT] … [/HA 2026 GOVERNANCE CONTEXT]`` block
        in the user message.  When ``None`` the block is omitted silently.

    Returns
    -------
    tuple of ``("", "")`` for ``pass_through`` or ``skip`` strategies,
    otherwise ``(system_prompt, user_prompt)``.
    """
    if strategy in ("pass_through", "skip"):
        return "", ""

    _sys_bt = (
        system_bt
        if system_bt is not None
        else _load_prompt_file(None, _PROMPT_BACKTRACKING_PATH)
    )
    _sys_rc = (
        system_rc
        if system_rc is not None
        else _load_prompt_file(None, _PROMPT_RECONSTRUCTION_PATH)
    )

    metadata = record.get("metadata") or {}
    assistant = _get_assistant_content(record)
    think_text, code_rest = extract_think_block(assistant)
    user_content = ""
    for msg in record.get("conversation", []):
        if isinstance(msg, dict) and msg.get("role") == "user":
            user_content = msg.get("content", "")
            break

    # Prefer explicit language from config/CLI when provided; fall back to
    # per-record detection otherwise. Inject a neutral token that prompts
    # can interpret to require the same output language as the original.
    lang_hint = language if language else _detect_language_hint(think_text)
    lang_prefix = f"ORIGINAL_THINK_LANGUAGE: {lang_hint}\n\n"
    ctx_block = (
        f"[HA 2026 GOVERNANCE CONTEXT]\n{governance_context}\n[/HA 2026 GOVERNANCE CONTEXT]\n\n"
        if governance_context
        else ""
    )

    if strategy == "full_backtracking":
        legacy_patterns = metadata.get("legacy_patterns", [])
        patterns_str = (
            "\n".join(f"- {p}" for p in legacy_patterns) if legacy_patterns else "N/A"
        )
        user_prompt = (
            f"{lang_prefix}"
            f"{ctx_block}"
            f"ORIGINAL USER PROMPT:\n{user_content}\n\n"
            f"DETECTED LEGACY PATTERNS:\n{patterns_str}\n\n"
            f"CURRENT THINK BLOCK:\n{think_text}\n\n"
            f"CODE (for reference only — do NOT modify):\n{code_rest[:2000]}\n\n"
            "Rewrite the think block with full backtracking reasoning."
        )
        return _sys_bt, user_prompt

    if strategy == "trace_reconstruction":
        user_prompt = (
            f"{lang_prefix}"
            f"{ctx_block}"
            f"ORIGINAL USER PROMPT:\n{user_content}\n\n"
            f"PERFECT SOLUTION CODE:\n{code_rest[:3000]}\n\n"
            "Write the expert reasoning trace that leads to this exact code."
        )
        return _sys_rc, user_prompt

    if strategy == "error_first":
        user_prompt = (
            f"{lang_prefix}"
            f"{ctx_block}"
            f"ORIGINAL USER PROMPT:\n{user_content}\n\n"
            f"CURRENT THINK BLOCK:\n{think_text}\n\n"
            f"CODE (for reference only — do NOT modify):\n{code_rest[:2000]}\n\n"
            "Rewrite the think block: first identify the error scenario, "
            "propose a wrong fix, catch the mistake, then give the correct solution."
        )
        return _sys_bt, user_prompt

    if strategy == "contrast_backtracking":
        user_prompt = (
            f"{lang_prefix}"
            f"{ctx_block}"
            f"ORIGINAL USER PROMPT:\n{user_content}\n\n"
            f"CURRENT THINK BLOCK:\n{think_text}\n\n"
            f"CODE (for reference only — do NOT modify):\n{code_rest[:2000]}\n\n"
            "Rewrite the think block: present both old and new approach, "
            "explicitly reject the old one with technical justification."
        )
        return _sys_bt, user_prompt

    return "", ""
