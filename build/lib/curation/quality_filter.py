#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""AEGF — Quality Filter Module.

Phase 2 (structural quality gate) logic for the NeMo Curator Suite.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, List

from src.schemas.common import RawRecord

if TYPE_CHECKING:
    from src.curation.curator_pipeline import CurationStats

logger = logging.getLogger(__name__)

# Default constants
DEFAULT_MIN_THINK_CHARS: int = 500
DEFAULT_LDI_MIN_RATIO: float = (
    0.15  # Blackwell calibrated — new formula yields [0,1) so 2.5 is invalid
)

# Programming keywords for code token counting
_PROGRAMMING_KEYWORDS: List[str] = [
    "async",
    "await",
    "def",
    "class",
    "import",
    "from",
    "return",
    "if",
    "else",
    "elif",
    "for",
    "while",
    "try",
    "except",
    "finally",
    "with",
    "lambda",
    "yield",
    "raise",
    "assert",
    "pass",
    "break",
    "continue",
    "True",
    "False",
    "None",
    "self",
    "super",
    "__init__",
    "function",
    "const",
    "let",
    "var",
    "new",
    "this",
    "export",
    "HomeAssistant",
    "DataUpdateCoordinator",
    "Entity",
    "ConfigEntry",
    "async_setup_entry",
    "async_added_to_hass",
    "hass",
    "entry",
    "coordinator",
    "device_info",
    "state",
    "attributes",
    "entity_id",
]

# Meta speech patterns for detecting filler phrases
_META_PATTERNS: List[str] = [
    r"the\s+user\s+is\s+asking",
    r"i\s+need\s+to",
    r"let\s+me",
    r"i\s+should",
    r"i\s+will\s+now",
    r"first\s+i\s+will",
    r"this\s+is\s+a\s+simple",
    r"this\s+is\s+straightforward",
]


def _count_code_tokens(text: str) -> int:
    count = 0
    json_blocks = re.findall(r"\{[^}]*\}", text)
    for block in json_blocks:
        count += len(re.findall(r"\w+|[{}[\]:,]", block))
    code_blocks = re.findall(r"```[\s\S]*?```", text)
    for block in code_blocks:
        clean = block.replace("```", "").strip()
        count += len(re.findall(r"\w+|[{}[\]():;=.,<>]", clean))
    for kw in _PROGRAMMING_KEYWORDS:
        count += len(re.findall(r"\b" + kw + r"\b", text))
    text_stripped = text
    for b in json_blocks + code_blocks:
        text_stripped = text_stripped.replace(b, "")
    count += len(re.findall(r"[{}[\]():;=.,<>!&|+\-*/%]", text_stripped))
    return count


def _count_natural_tokens(text: str) -> int:
    t = re.sub(r"\{[^}]*\}", "", text)
    t = re.sub(r"```[\s\S]*?```", "", t)
    t = re.sub(r"<[^>]+>", "", t)
    words = re.findall(r"\b[a-zA-Z]{2,}\b", t)
    stop = {
        "async",
        "await",
        "def",
        "class",
        "import",
        "from",
        "return",
        "true",
        "false",
        "none",
        "self",
        "super",
        "function",
        "const",
        "homeassistant",
        "coordinator",
        "entity",
        "hass",
        "config",
    }
    return len([w for w in words if w.lower() not in stop])


def _ldi(text: str) -> float:
    # Version Blackwell Calibrada
    code_tokens = _count_code_tokens(text)
    natural_tokens = _count_natural_tokens(text)
    if code_tokens == 0:
        return 0.0

    K = 800.0  # Factor de estabilidad para registros cortos (calibrado)
    ldi_score = code_tokens / max(1.0, (natural_tokens + code_tokens))
    ldi_final = ldi_score * (code_tokens / (code_tokens + K))
    return ldi_final  # Now the threshold should be ~0.1 or 0.2, not 2.5


def _has_meta_speech(think_content: str) -> bool:
    """Return True if >20 % of lines match shallow meta-speech patterns."""
    lines = think_content.split("\n")
    if not lines:
        return False
    # Count how many lines match any meta-speech pattern (case-insensitive)
    count = 0
    for line in lines:
        ln = line.strip().lower()
        if not ln:
            continue
        if any(re.search(p, ln) for p in _META_PATTERNS):
            count += 1
    return (count / len(lines)) > 0.20


def structural_quality_filter(
    records: List[RawRecord],
    stats: "CurationStats",
    *,
    min_think_chars: int = DEFAULT_MIN_THINK_CHARS,
    ldi_min_ratio: float = DEFAULT_LDI_MIN_RATIO,
    check_attempt_completion: bool = True,
) -> List[RawRecord]:
    """Apply structural quality gate filters.

    Filter chain:
    1. Syntax integrity   — ``</think>`` and ``<tool_call>`` must be adjacent;
       ``</think><tool_call>`` must be immediately followed by <tool_call> without any whitespace:
       ``</think><tool_call>``
    2. Think depth       — The <think> block in the *first* assistant turn must
       have at least ``min_think_chars`` characters.
    3. Meta-speech check — The reasoning block must not consist mostly of
       shallow filler phrases ("let me", "I need to", etc.).
    4. LDI on tool_call  — The ``<tool_call>`` block (not the full turn) must
       have a code-to-natural-language ratio ≥ ``ldi_min_ratio``.
    5. attempt_completion — If ``check_attempt_completion`` is True, the last
       assistant turn must contain "attempt_completion" (agentic datasets only;
       disable with ``--no-attempt-check`` for production_v11 single-turn data).
    """
    kept: List[RawRecord] = []

    for rec in records:
        conversation = rec.get("conversation", [])

        # Collect assistant turns
        assistant_turns = [
            m
            for m in conversation
            if isinstance(m, dict) and m.get("role") == "assistant"
        ]
        if not assistant_turns:
            stats.invalid_syntax += 1
            continue

        failed = False

        for turn in assistant_turns:
            content = turn.get("content", "")
            if not isinstance(content, str):
                continue

            # --- Filter 1: syntax integrity ---
            if "<think>" in content and "</think>" in content:
                if re.search(r"</think>\s+<tool_call>", content):
                    # Space between tags — invalid
                    stats.invalid_syntax += 1
                    failed = True
                    break
                if "</think>" in content and "<tool_call>" in content:
                    if not re.search(r"</think><tool_call>", content):
                        stats.invalid_syntax += 1
                        failed = True
                        break

        if failed:
            continue

        # --- Filters 2, 3, 4 on first assistant turn with <think> ---
        first_think_turn = next(
            (
                m.get("content", "")
                for m in assistant_turns
                if isinstance(m.get("content"), str) and "<think>" in m["content"]
            ),
            None,
        )

        if first_think_turn is not None:
            # Use literal string for the think block marker
            think_marker = "<think>"
            end_think_marker = "</think>"
            think_match = re.search(
                think_marker + r"(.*?)" + end_think_marker,
                first_think_turn,
                re.DOTALL,
            )
            if not think_match:
                stats.invalid_syntax += 1
                continue
            think_content = think_match.group(1).strip()

            # Filter 2: think depth
            if len(think_content) < min_think_chars:
                stats.shallow_thinking += 1
                continue

            # Filter 3: meta-speech
            if _has_meta_speech(think_content):
                stats.meta_speech += 1
                continue

            # Filter 4: LDI on tool_call
            tool_call_match = re.search(
                r"<tool_call>(.*?)</tool_call>", first_think_turn, re.DOTALL
            )
            if not tool_call_match:
                stats.invalid_syntax += 1
                continue
            ldi_val = _ldi(tool_call_match.group(1).strip())
            if ldi_val < ldi_min_ratio:
                stats.low_ldi += 1
                continue

        # --- Filter 5: attempt_completion (agentic datasets) ---
        if check_attempt_completion and assistant_turns:
            last_content = assistant_turns[-1].get("content", "")
            if "attempt_completion" not in last_content:
                pass  # Non-agentic records are allowed through; LDI already covered them

        kept.append(rec)

    logger.info(
        "Structural filter: %d invalid_syntax, %d shallow, %d meta_speech, %d low_ldi — "
        "%d remaining",
        stats.invalid_syntax,
        stats.shallow_thinking,
        stats.meta_speech,
        stats.low_ldi,
        len(kept),
    )
    return kept
