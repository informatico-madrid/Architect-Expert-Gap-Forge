#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Backtracking Rewriter — Think-block transformation for self-correction training.

Transforms existing training samples so their ``<think>`` blocks follow the
Self-Evaluation + Backtracking pattern from OpenCodeReasoning / AgentMath:

  1. Legacy Impulse — propose the old/wrong approach first.
  2. Self-Evaluation — check against HA 2026 governance.
  3. Backtracking — explicitly reject the wrong path.
  4. Modern Resolution — commit to the correct approach.

Public API
----------
extract_think_block(content)              -> (think, rest)
replace_think_block(content, new_think)   -> new_content
classify_rewrite_strategy(record)         -> strategy_name
build_rewrite_prompt(record, strategy)    -> (system_prompt, user_prompt)
passes_backtracking_filter(record, cfg)   -> bool
apply_backtracking_rewrite(record, client, cfg) -> record | None
load_jsonl(path)                          -> list[RawRecord]
save_jsonl(records, path)                 -> None
load_backtracking_config(path)            -> BacktrackingConfig
rewrite_pipeline(input_path, output_path, cfg) -> PipelineReport

Sacred Constraint
-----------------
Content at and after ``</think>`` is NEVER modified.  The code output is
production gold and must arrive byte-identical in the output dataset.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Final, Protocol, Sequence, runtime_checkable

import yaml

# ---------------------------------------------------------------------------
# Script-mode path bootstrap (no-op when imported as a package module)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    _project_root = Path(__file__).resolve().parent.parent.parent
    if str(_project_root) not in sys.path:
        sys.path.insert(0, str(_project_root))

from src.schemas.common import RawRecord  # noqa: E402

logger = logging.getLogger(__name__)

__all__ = [
    "BacktrackingConfig",
    "PipelineReport",
    "extract_think_block",
    "replace_think_block",
    "classify_rewrite_strategy",
    "build_rewrite_prompt",
    "passes_backtracking_filter",
    "apply_backtracking_rewrite",
    "load_jsonl",
    "save_jsonl",
    "load_backtracking_config",
    "rewrite_pipeline",
    "main",
    # Exposed for testing — considered semi-public.
    "_load_legacy_regexes",
    "_validate_resolution_no_legacy",
    "_extract_executable_code",
    "_strip_python_comments",
]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CHARS_PER_TOKEN: Final[int] = 4
_THINK_CLOSE_TAG: Final[str] = "</think>"
_MAX_RETRIES: Final[int] = 3

# Canonical paths for required prompt template files.
# Copy the corresponding .example file to create them on a fresh checkout:
#   cp configs/prompts/backtracking_system.txt.example configs/prompts/backtracking_system.txt
#   cp configs/prompts/reconstruction_system.txt.example configs/prompts/reconstruction_system.txt
_PROMPT_BACKTRACKING_PATH: Final[str] = "configs/prompts/backtracking_system.txt"
_PROMPT_RECONSTRUCTION_PATH: Final[str] = "configs/prompts/reconstruction_system.txt"
_DEFAULT_LEGACY_PATTERNS_FILE: Final[str] = (
    "configs/stage_5_evaluation/ha_patterns.yaml"
)


class _RejectionSamplingError(Exception):
    """Raised when a generated think block fails post-generation validation.

    This is an internal control-flow exception — it is never propagated
    outside the pipeline.  It carries the human-readable rejection reason
    so the pipeline can log and count it.
    """


# ---------------------------------------------------------------------------
# Prompt file loader
# ---------------------------------------------------------------------------


def _load_prompt_file(path: str | None, default_path: str) -> str:
    """Load a required prompt template from disk.

    Parameters
    ----------
    path:
        Explicit file path from config.  When ``None``, ``default_path`` is
        used instead.
    default_path:
        Canonical path (relative to the working directory or absolute) used
        when ``path`` is ``None``.

    Raises
    ------
    FileNotFoundError
        When the resolved file does not exist.  The error message includes
        a ``cp`` command to bootstrap the file from the bundled ``.example``
        template.
    ValueError
        When the file exists but is empty.
    """
    resolved = Path(path) if path else Path(default_path)
    example = Path(str(resolved) + ".example")
    if not resolved.exists():
        raise FileNotFoundError(
            f"Required prompt file not found: {resolved}\n"
            f"Bootstrap it from the bundled template:\n"
            f"  cp {example} {resolved}\n"
            f"Then edit the file to customise the prompt."
        )
    content = resolved.read_text(encoding="utf-8").strip()
    if not content:
        raise ValueError(
            f"Prompt file is empty: {resolved}\nSee the reference template: {example}"
        )
    logger.debug("Loaded prompt from %s (%d chars)", resolved, len(content))
    return content


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
# Configuration
# ---------------------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class BacktrackingConfig:
    """Immutable configuration for the backtracking rewriter pipeline."""

    max_tokens: int = 4000
    excluded_types: tuple[str, ...] = ("theory",)
    vllm_api_url: str = "http://localhost:8000/v1"
    vllm_model: str = "qwen3-30b-a3b-thinking-fp8"
    temperature: float = 0.6
    max_generation_tokens: int = 3000
    batch_size: int = 10
    seed: int = 42
    workers: int = 8
    audit_dir: str | None = None
    # Optional paths to external prompt template files.
    # When None the built-in fallback strings are used.
    backtracking_system_prompt_path: str | None = None
    reconstruction_system_prompt_path: str | None = None
    # Governance context injection: path to the directory containing HA_MASTER_GUIDE_2026.md.
    gap_dir: str = "data/Gap"
    # Maximum characters of the governance document to inject in user prompts.
    # The full HA_MASTER_GUIDE_2026.md is ~5 200 chars — 0 means no truncation.
    governance_context_chars: int = 5200
    # Optional explicit language to enforce for all rewrites (e.g. "Spanish").
    # When ``None`` the rewriter will auto-detect language per-record.
    # This value is injected into the user prompt as a neutral token and
    # does not perform any translation within the Python code.
    language: str | None = None
    # Path to YAML file with legacy_patterns regex entries used for
    # post-generation rejection sampling.  When set, the *resolution half*
    # of a generated think block is checked against these patterns.
    # Records whose resolution still mentions legacy code are discarded.
    # Set to ``None`` to disable the check entirely.
    legacy_patterns_file: str | None = _DEFAULT_LEGACY_PATTERNS_FILE


@dataclass(slots=True, frozen=True)
class PipelineReport:
    """Immutable summary of a backtracking rewrite run."""

    total_input: int
    filtered_out: int
    rewritten: int
    pass_through: int
    failed: int
    rejected: int
    total_output: int
    strategy_counts: dict[str, int]


# ---------------------------------------------------------------------------
# Think-block manipulation
# ---------------------------------------------------------------------------


def extract_think_block(content: str) -> tuple[str, str]:
    """Split assistant content into (think_text, rest_after_tag).

    Returns ``("", content)`` when no ``</think>`` tag is found.
    """
    idx = content.find(_THINK_CLOSE_TAG)
    if idx < 0:
        return "", content
    return content[:idx], content[idx + len(_THINK_CLOSE_TAG) :]


def replace_think_block(content: str, new_think: str) -> str:
    """Replace the think portion while preserving everything after ``</think>``.

    Sacred constraint: bytes after ``</think>`` are never touched.
    """
    _, rest = extract_think_block(content)
    return f"{new_think}{_THINK_CLOSE_TAG}{rest}"


# ---------------------------------------------------------------------------
# Content helpers
# ---------------------------------------------------------------------------


def _get_assistant_content(record: RawRecord) -> str:
    """Extract the first assistant turn's content."""
    conversation = record.get("conversation")
    if not isinstance(conversation, list):
        return ""
    for msg in conversation:
        if isinstance(msg, dict) and msg.get("role") == "assistant":
            content = msg.get("content", "")
            return content if isinstance(content, str) else ""
    return ""


def _estimate_tokens(text: str) -> int:
    """Estimate token count using chars / 4 heuristic."""
    return len(text) // _CHARS_PER_TOKEN


def _format_seconds(s: float) -> str:
    """Format seconds into a compact human-readable string."""
    if s < 60:
        return f"{s:.1f}s"
    m = int(s // 60)
    sec = s - m * 60
    return f"{m}m{sec:.1f}s"


def _sanitize_generated_reasoning(text: str) -> str:
    """Remove fenced code, inline code and tool-call blocks from LLM output.

    The rewriter must never include code or tool-call JSON inside the reasoning
    block. This function strips common markers (triple-backticks, inline
    backticks, <tool_call>...</tool_call> and leftover angle tags) while
    preserving technical identifiers (class names, function names, etc.).

    Sacred Constraint (AEGF § 4.2):
    ────────────────────────────────
    Technical identifiers wrapped in single backticks (e.g., `device_class`,
    `async_forward_entry_setups`) MUST NOT be removed. These are essential for
    training Home Assistant integration components. Only code blocks containing
    executable syntax (fenced code, tool-calls, stray XML tags) are sanitized.
    """
    if not text:
        return text

    # STEP 1: Preserve technical identifiers (single backticks)
    # Save them in a map before sanitization
    identifier_map: dict[str, str] = {}
    preserved_text = text

    # Pattern: preserve code-like inline backticked spans. We accept two
    # flavours: (A) short, single-token identifiers with no whitespace
    # (`async_update`, `SensorDeviceClass`), and (B) short code-like
    # expressions that may contain parentheses/commas but are still
    # compact (e.g. ``discovery_flow.async_create_flow(hass, DOMAIN)``).
    # The combined regex uses a lookahead to detect punctuation typical
    # of code and a conservative max-length to avoid preserving long
    # natural-language fragments placed inside backticks.
    preserve_pattern = re.compile(
        r"`((?=[^`]*[()\[\]{},.;:=<>])[^`\n]{1,256}|[^`\s]{1,256})`"
    )
    for match in preserve_pattern.finditer(text):
        placeholder = f"__PRESERVED_ID_{len(identifier_map)}__"
        identifier_map[placeholder] = match.group(0)

    # Replace identifiers with placeholders
    for placeholder, identifier in identifier_map.items():
        preserved_text = preserved_text.replace(identifier, placeholder)

    # STEP 2: Remove fenced code blocks ```...``` (multiline)
    preserved_text = re.sub(r"```[\s\S]*?```", "", preserved_text)

    # STEP 3: Remove backticks that remain (inline code with spaces/syntax)
    # These are likely code snippets like `def func(x)` or `key: value`
    preserved_text = re.sub(r"`[^`]*`", "", preserved_text)

    # STEP 4: Remove explicit <tool_call>...</tool_call> blocks
    preserved_text = re.sub(
        r"<tool_call>[\s\S]*?</tool_call>", "", preserved_text, flags=re.IGNORECASE
    )

    # STEP 5: Remove any remaining angle-bracket tags (conservative)
    preserved_text = re.sub(r"<[^>]+>", "", preserved_text)

    # STEP 6: Restore technical identifiers
    for placeholder, identifier in identifier_map.items():
        preserved_text = preserved_text.replace(placeholder, identifier)

    # STEP 7: Collapse multiple blank lines
    preserved_text = re.sub(r"\n{3,}", "\n\n", preserved_text)

    return preserved_text.strip()


def _detect_language_hint(text: str) -> str:
    """Lightweight heuristic to detect whether text is Spanish or English.

    Returns the string 'Spanish' or 'English'. Used to provide an explicit
    language hint to the rewrite prompt so the LLM replies in the same language
    as the original reasoning.
    """
    if not text:
        return "English"
    s = text.lower()
    es_score = sum(
        s.count(w)
        for w in [
            " el ",
            " la ",
            " que ",
            " y ",
            " para ",
            " usar ",
            " será ",
            " debe ",
            "vamos",
        ]
    )
    en_score = sum(
        s.count(w) for w in [" the ", " and ", " to ", " is ", " will ", " this "]
    )
    return "Spanish" if es_score > en_score else "English"


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


def _extract_executable_code(text: str) -> str:
    """Extract only executable code from a mixed text/code block.

    Handles three common formats generated by the dataset pipeline:

    1. **Fenced code blocks** — ````` ```python ... ``` ````` or ````` ``` ... ``` `````.
    2. **``<tool_call>`` JSON** — parses the JSON payload and extracts the
       ``content`` argument from ``write_to_file`` / ``write_action`` calls.
       Both single-dict and list-of-dicts formats are supported.
    3. Falls back to returning ``text`` as-is when no markers are found, so
       the caller can still apply a coarser check if desired.

    The returned string is a concatenation of all found code fragments.
    """
    extracted: list[str] = []

    # 1. Fenced code blocks: ```[lang]\n...\n```
    fenced = re.findall(r"```(?:\w+)?\n?([\s\S]*?)```", text)
    extracted.extend(fenced)

    # 2. <tool_call>...</tool_call> JSON: extract 'content' from write_to_file
    tool_blocks = re.findall(
        r"<tool_call>([\s\S]*?)</tool_call>", text, flags=re.IGNORECASE
    )
    for block in tool_blocks:
        block = block.strip()
        if not block:
            continue
        try:
            parsed = json.loads(block)
            items = parsed if isinstance(parsed, list) else [parsed]
            for item in items:
                if not isinstance(item, dict):
                    continue
                args = item.get("arguments", {})
                if isinstance(args, str):
                    # arguments may itself be a JSON string
                    try:
                        args = json.loads(args)
                    except (json.JSONDecodeError, ValueError):
                        args = {}
                if isinstance(args, dict):
                    content = args.get("content", "")
                    if content:
                        extracted.append(content)
        except (json.JSONDecodeError, ValueError, AttributeError):
            pass

    if extracted:
        return "\n".join(extracted)

    # 3. No markers found — return the raw text so callers can decide
    return text


def _strip_python_comments(code: str) -> str:
    """Remove single-line Python comments (``# ...``) from *code*.

    This prevents false positives where an explanatory comment such as
    ``# FIX: migrated from hass.data`` triggers a legacy regex while the
    *actual* code on the same or adjacent lines uses the modern API.

    String literals that contain ``#`` are not affected by this heuristic
    because the strip is applied line-by-line from the first unquoted ``#``.
    For the purposes of pattern matching this approximation is sufficient.
    """
    lines: list[str] = []
    for line in code.splitlines():
        # Remove trailing inline comment and full-line comments alike.
        # Simple regex: strip from first # that is not inside a string.
        # Heuristic: scan for # not preceded by an even number of quotes.
        cleaned = re.sub(r"\s*#.*$", "", line)
        lines.append(cleaned)
    return "\n".join(lines)


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
    (the sacred code block after ``</think>``) before checking it.

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
    Content at and after ``</think>`` is **never** modified.
    """
    strategy = classify_rewrite_strategy(record)

    assistant = _get_assistant_content(record)
    think_text, _ = extract_think_block(assistant)

    logger.debug(
        "Applying backtracking rewrite for id=%s strategy=%s",
        record.get("id", "unknown"),
        strategy,
    )

    if strategy in ("pass_through", "skip"):
        metadata = dict(record.get("metadata") or {})
        metadata["backtracking_applied"] = False
        metadata["backtracking_strategy"] = strategy
        metadata["original_think_chars"] = len(think_text)
        metadata["rewritten_think_chars"] = len(think_text)
        return {**record, "metadata": metadata}

    system_prompt, user_prompt = build_rewrite_prompt(
        record,
        strategy,
        system_bt=_system_bt,
        system_rc=_system_rc,
        governance_context=_governance_context,
        language=config.language,
    )
    if not system_prompt:
        return {**record}

    new_think: str = ""
    last_error: str = ""
    inf_start = time.monotonic()

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            # ``client`` follows the _AsyncGenerateClient protocol
            raw: str = await client.generate(  # type: ignore[union-attr]
                user_prompt,
                system_prompt=system_prompt,
                max_tokens=config.max_generation_tokens,
                temperature=config.temperature,
            )

            # For thinking models (e.g. qwen3-thinking), the model wraps its
            # own meta-reasoning in <think>…</think> and emits the real,
            # clean answer AFTER the closing tag.  We must take what comes
            # AFTER </think>, not before.
            # For non-thinking models (or when the tag is absent) raw already
            # contains the clean answer and we leave it untouched.
            if _THINK_CLOSE_TAG in raw:
                raw = raw[raw.find(_THINK_CLOSE_TAG) + len(_THINK_CLOSE_TAG) :]
            raw = raw.strip()

            # Sanitize code fences / tool-calls leaked into reasoning
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

    # CRITICAL: Verify sacred constraint - code after </think> must be byte-identical
    # to the original. If not, restore from original to fix any whitespace issues.
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
# Config loading
# ---------------------------------------------------------------------------


def load_backtracking_config(path: Path) -> BacktrackingConfig:
    """Load config from a YAML file, merging with defaults."""
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    # Convert list to tuple for frozen dataclass
    if "excluded_types" in data and isinstance(data["excluded_types"], list):
        data["excluded_types"] = tuple(data["excluded_types"])

    # Only pass known fields
    known_fields = {f.name for f in BacktrackingConfig.__dataclass_fields__.values()}
    filtered = {k: v for k, v in data.items() if k in known_fields}
    return BacktrackingConfig(**filtered)


# ---------------------------------------------------------------------------
# Pipeline orchestrator (async)
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


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_arg_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="backtracking_rewriter",
        description=(
            "AEGF Stage 3.5 — Backtracking Alignment: rewrite <think> blocks "
            "to embed self-correction patterns into training data."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    # Required I/O
    io = parser.add_argument_group("I/O (required)")
    io.add_argument(
        "--input",
        "-i",
        required=True,
        type=Path,
        metavar="FILE",
        help="Source JSONL dataset.",
    )
    io.add_argument(
        "--output",
        "-o",
        required=True,
        type=Path,
        metavar="FILE",
        help="Destination JSONL dataset.",
    )
    # Config
    cfg_grp = parser.add_argument_group("Configuration")
    cfg_grp.add_argument(
        "--config",
        "-c",
        type=Path,
        default=None,
        metavar="FILE",
        help="YAML config (e.g. configs/stage_3_curation/backtracking_alignment.yaml).",
    )
    cfg_grp.add_argument(
        "--language",
        type=str,
        default=None,
        metavar="LANG",
        help=(
            "Force output language token (e.g. 'Spanish' or 'English'). "
            "When provided this overrides per-record detection."
        ),
    )
    # Inference overrides
    inf_grp = parser.add_argument_group(
        "Inference overrides (take priority over --config)"
    )
    inf_grp.add_argument(
        "--model",
        type=str,
        default=None,
        metavar="NAME",
        help="vLLM model name.",
    )
    inf_grp.add_argument(
        "--base-url",
        type=str,
        default=None,
        metavar="URL",
        help="vLLM API base URL.",
    )
    inf_grp.add_argument(
        "--temperature",
        type=float,
        default=None,
        metavar="FLOAT",
        help="Sampling temperature.",
    )
    inf_grp.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        metavar="N",
        help="Max context tokens filter (discard records exceeding this estimate).",
    )
    inf_grp.add_argument(
        "--max-generation-tokens",
        type=int,
        default=None,
        metavar="N",
        help="Max generation tokens per think-block rewrite.",
    )
    inf_grp.add_argument(
        "--batch-size",
        type=int,
        default=None,
        metavar="N",
        help="Progress log interval (number of eligible records between log lines).",
    )
    inf_grp.add_argument(
        "--workers",
        type=int,
        default=None,
        metavar="N",
        help="Number of concurrent vLLM requests (asyncio.Semaphore size).",
    )
    inf_grp.add_argument(
        "--audit-dir",
        type=Path,
        default=None,
        metavar="DIR",
        help=(
            "Directory to save full rewritten <think> blocks for auditing. "
            "When provided, per-record full texts are written under "
            "<audit-dir>/backtracking_YYYYmmdd_HHMMSS/<id>.txt"
        ),
    )
    inf_grp.add_argument(
        "--gap-dir",
        type=str,
        default=None,
        metavar="DIR",
        help=(
            "Directory containing HA_MASTER_GUIDE_2026.md for governance context "
            "injection.  Defaults to 'data/Gap'."
        ),
    )
    # Diagnostics
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for the backtracking rewriter pipeline.

    Usage example::

        python src/curation/backtracking_rewriter.py \\
            --input  data/synthetic/v11_DISTILLED.jsonl \\
            --output data/synthetic/v11_backtracking_aligned.jsonl \\
            --config configs/stage_3_curation/backtracking_alignment.yaml
    """
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level, logging.INFO),
        format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Load base config from YAML (or fall back to defaults)
    cfg: BacktrackingConfig
    if args.config is not None:
        cfg = load_backtracking_config(args.config)
    else:
        cfg = BacktrackingConfig()

    # Apply any CLI overrides (frozen dataclass requires dataclasses.replace)
    overrides: dict[str, object] = {}
    if args.model is not None:
        overrides["vllm_model"] = args.model
    if args.base_url is not None:
        overrides["vllm_api_url"] = args.base_url
    if args.temperature is not None:
        overrides["temperature"] = args.temperature
    if args.max_tokens is not None:
        overrides["max_tokens"] = args.max_tokens
    if args.max_generation_tokens is not None:
        overrides["max_generation_tokens"] = args.max_generation_tokens
    if args.batch_size is not None:
        overrides["batch_size"] = args.batch_size
    if getattr(args, "workers", None) is not None:
        overrides["workers"] = args.workers
    if getattr(args, "audit_dir", None) is not None:
        # store as string in the frozen dataclass
        overrides["audit_dir"] = str(args.audit_dir)
    if getattr(args, "gap_dir", None) is not None:
        overrides["gap_dir"] = args.gap_dir
    if getattr(args, "language", None) is not None:
        overrides["language"] = args.language
    if overrides:
        cfg = replace(cfg, **overrides)

    logger.info(
        "Backtracking rewriter starting | input=%s output=%s model=%s temperature=%.2f",
        args.input,
        args.output,
        cfg.vllm_model,
        cfg.temperature,
    )

    report = asyncio.run(rewrite_pipeline(args.input, args.output, cfg))
    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
