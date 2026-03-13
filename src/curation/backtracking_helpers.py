#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Backtracking rewriter helper utilities.

This module provides shared utility functions used across the backtracking
rewrite pipeline.

Public API
----------
extract_think_block(content)    -- Split assistant content into (think, rest)
replace_think_block(content, new_think) -- Replace think portion preserving rest
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from src.schemas.common import RawRecord

logger = logging.getLogger(__name__)

__all__ = [
    "extract_think_block",
    "replace_think_block",
    "_get_assistant_content",
    "_estimate_tokens",
    "_format_seconds",
    "_sanitize_generated_reasoning",
    "_detect_language_hint",
    "_RejectionSamplingError",
    "_load_prompt_file",
    "_extract_executable_code",
    "_strip_python_comments",
]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CHARS_PER_TOKEN: int = 4
_THINK_CLOSE_TAG: str = "</think>"

# Canonical paths for required prompt template files.
_PROMPT_BACKTRACKING_PATH: str = "configs/prompts/backtracking_system.txt"
_PROMPT_RECONSTRUCTION_PATH: str = "configs/prompts/reconstruction_system.txt"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


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

    Sacred constraint: bytes after ``
</think>

`` are never touched.
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
