# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""Think Filter — Inline thought distillation for production pipelines.

Designed to be imported by production_v11.py (and any future pipeline) to
clean redundant content from <think> blocks *before* writing to the dataset.

Public API
----------
filter_think_content(content, min_chars=5000) -> (filtered_content, stats)
apply_to_record(record, min_chars=5000)       -> (filtered_record, stats | None)

Philosophy
----------
distill_v11.py  → CLI tool   — post-processes an *existing* JSONL dataset.
think_filter.py → library    — applied inline during production, zero I/O overhead.

Both use the same distillation logic. Any algorithm change made here should
be mirrored in distill_v11.py (or vice-versa) to keep them consistent.

Sacred Constraint
-----------------
NEVER modify anything at or after </think>.
The code/tool_call output is production gold and must arrive untouched.
"""

from __future__ import annotations

import logging
import re
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple
from src.schemas.common import RawRecord

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tuneable constants (override via think_filter.MIN_THINK_CHARS etc.)
# ---------------------------------------------------------------------------
MIN_THINK_CHARS: int = 5000  # Only distil if think block >= this
PARA_SIM_THRESHOLD: float = 0.82  # Similarity to consider two paragraphs duplicate
CODE_SIM_THRESHOLD: float = 0.80  # Similarity to consider two code blocks duplicate
CYCLE_SIM_THRESHOLD: float = (
    0.70  # Similarity to consider two revision cycles duplicate
)
MAX_CONSECUTIVE_LINES: int = 2  # Max allowed consecutive identical lines

CODE_FENCE_RE = re.compile(r"(```[\w]*\n[\s\S]*?```)", re.MULTILINE)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _norm(text: str, maxlen: int = 500) -> str:
    """Normalise text for comparison: lowercase, collapse whitespace, strip punct."""
    t = text.strip().lower()[:maxlen]
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"[^\w\s]", "", t)
    return t


def _sim(a: str, b: str) -> float:
    """Similarity ratio (0..1) using first 500 chars of each string."""
    na, nb = _norm(a, 500), _norm(b, 500)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    return SequenceMatcher(None, na, nb).ratio()


# ---------------------------------------------------------------------------
# Strategy 1: Collapse consecutive identical lines
# ---------------------------------------------------------------------------


def _collapse_consecutive_lines(text: str) -> str:
    lines = text.split("\n")
    result: List[str] = []
    prev_norm = None
    run = 0
    for line in lines:
        n = _norm(line)
        if n == prev_norm and len(n) > 15:
            run += 1
            if run <= MAX_CONSECUTIVE_LINES:
                result.append(line)
        else:
            run = 1
            prev_norm = n
            result.append(line)
    return "\n".join(result)


# ---------------------------------------------------------------------------
# Strategy 2: Deduplicate code blocks (keep last occurrence)
# ---------------------------------------------------------------------------


def _dedup_code_blocks(text: str) -> str:
    blocks = list(CODE_FENCE_RE.finditer(text))
    if len(blocks) < 2:
        return text

    # Group by normalised content key
    groups: Dict[str, List[re.Match]] = {}
    for m in blocks:
        key = _norm(m.group(1)[3:403])  # skip ``` prefix, cap at 400 chars
        if len(key) < 20:
            continue
        groups.setdefault(key, []).append(m)

    # For each group with duplicates: remove all but last
    to_remove: List[Tuple[int, int]] = []
    for matches in groups.values():
        if len(matches) >= 2:
            for earlier in matches[:-1]:
                if _sim(earlier.group(1), matches[-1].group(1)) >= CODE_SIM_THRESHOLD:
                    to_remove.append((earlier.start(), earlier.end()))

    if not to_remove:
        return text

    # Apply removals from end to start
    to_remove.sort(key=lambda x: x[0], reverse=True)
    for start, end in to_remove:
        text = text[:start].rstrip() + "\n\n" + text[end:].lstrip()
    return text


# ---------------------------------------------------------------------------
# Strategy 3: Deduplicate bullet items within a paragraph
# ---------------------------------------------------------------------------


def _dedup_bullets_in_para(para: str) -> str:
    seen: set = set()
    result: List[str] = []
    for line in para.split("\n"):
        stripped = line.strip()
        is_item = bool(re.match(r"^\s*[-*•]\s+", line)) or bool(
            re.match(r"^\s*\d+[\.\)]\s+", line)
        )
        if is_item:
            key = _norm(stripped)
            if key in seen:
                continue
            seen.add(key)
        result.append(line)
    return "\n".join(result)


# ---------------------------------------------------------------------------
# Strategy 4: Prune iterative revision cycles (keep last complete cycle)
# ---------------------------------------------------------------------------


def _prune_revision_cycles(paragraphs: List[str]) -> List[str]:
    # Detect paragraphs that start a new numbering cycle with "1." or similar
    cycle_starts = [
        i for i, p in enumerate(paragraphs) if re.match(r"^\s*1[\.\)]\s+", p.strip())
    ]
    if len(cycle_starts) < 2:
        return paragraphs

    cycles = []
    for ci, start in enumerate(cycle_starts):
        end = cycle_starts[ci + 1] if ci + 1 < len(cycle_starts) else len(paragraphs)
        cycles.append((start, end, "\n".join(paragraphs[start:end])))

    last_text = cycles[-1][2]
    remove: set = set()
    for start, end, text in cycles[:-1]:
        if _sim(text, last_text) >= CYCLE_SIM_THRESHOLD:
            remove.update(range(start, end))

    if not remove:
        return paragraphs
    return [p for i, p in enumerate(paragraphs) if i not in remove]


# ---------------------------------------------------------------------------
# Strategy 5: Paragraph-level deduplication (keep last occurrence)
# ---------------------------------------------------------------------------


def _dedup_paragraphs(paragraphs: List[str]) -> List[str]:
    n = len(paragraphs)
    keep = [True] * n
    keys = [_norm(p[:300]) for p in paragraphs]

    for i in range(n):
        if not keep[i] or len(paragraphs[i].strip()) < 30:
            continue
        for j in range(i + 1, n):
            if not keep[j]:
                continue
            if keys[i] == keys[j] or (
                len(keys[i]) > 20
                and len(keys[j]) > 20
                and _sim(paragraphs[i], paragraphs[j]) >= PARA_SIM_THRESHOLD
            ):
                keep[i] = False
                break
    return [p for p, k in zip(paragraphs, keep) if k]


# ---------------------------------------------------------------------------
# Core pipeline
# ---------------------------------------------------------------------------


def _distill(think_text: str) -> Tuple[str, Dict[str, Any]]:
    """Apply all distillation strategies to a raw think block.

    Returns (distilled_text, stats).
    """
    original_len = len(think_text)
    applied: List[str] = []
    w = think_text

    # 1 — Collapse consecutive identical lines
    before = len(w)
    w = _collapse_consecutive_lines(w)
    if len(w) < before:
        applied.append(f"consecutive_line_collapse: -{before - len(w)}")

    # 2 — Remove duplicate code blocks (keep last/most-refined)
    before = len(w)
    w = _dedup_code_blocks(w)
    if len(w) < before:
        applied.append(f"code_block_dedup: -{before - len(w)}")

    # 3 — Paragraph-level processing
    paras = [p for p in w.split("\n\n") if p.strip()]

    before_n = sum(len(p) for p in paras)
    paras = [_dedup_bullets_in_para(p) for p in paras]
    after_n = sum(len(p) for p in paras)
    if after_n < before_n:
        applied.append(f"bullet_dedup: -{before_n - after_n}")

    cnt = len(paras)
    paras = _prune_revision_cycles(paras)
    if len(paras) < cnt:
        applied.append(f"revision_cycle_prune: -{cnt - len(paras)} paragraphs")

    cnt = len(paras)
    paras = _dedup_paragraphs(paras)
    if len(paras) < cnt:
        applied.append(f"paragraph_dedup: -{cnt - len(paras)} paragraphs")

    w = "\n\n".join(paras)
    w = re.sub(r"\n{3,}", "\n\n", w)

    stats = {
        "original_chars": original_len,
        "distilled_chars": len(w),
        "reduction_pct": round((1 - len(w) / max(1, original_len)) * 100, 1),
        "strategies": applied,
    }
    return w, stats


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def filter_think_content(
    content: str,
    min_chars: int = MIN_THINK_CHARS,
) -> Tuple[str, Optional[Dict[str, Any]]]:
    """Filter the think block of an assistant *content* string.

    The think block is everything before `</think>` (no opening tag).
    Content at and after `</think>` is **never modified** (sacred constraint).

    Args:
        content:   Full assistant message content.
        min_chars: Minimum think block size (chars) to trigger distillation.
                   Below this threshold the content is returned unchanged.

    Returns:
        (filtered_content, stats) — stats is None if nothing was changed.
    """
    idx = content.lower().find("</think>")
    if idx < 0 or idx < min_chars:
        return content, None  # no think block, or too short — skip

    think_text = content[:idx]
    rest = content[idx:]  # includes </think> and everything after — NEVER TOUCHED

    distilled, stats = _distill(think_text)

    if stats["reduction_pct"] <= 0:
        return content, None

    return distilled + rest, stats


def apply_to_record(
    record: RawRecord,
    min_chars: int = MIN_THINK_CHARS,
) -> Tuple[RawRecord, Optional[Dict[str, Any]]]:
    """Apply think-filter to the first assistant message in a conversation record.

    Args:
        record:    Full SFT record dict (must contain "conversation" list).
        min_chars: Minimum think length to trigger distillation.

    Returns:
        (modified_record, stats) — stats is None if record was not modified.
        The returned record is a shallow copy; the original is not mutated.
    """
    conv = record.get("conversation")
    if not isinstance(conv, list):
        return record, None

    for mi, msg in enumerate(conv):
        if not (isinstance(msg, dict) and msg.get("role") == "assistant"):
            continue
        content = msg.get("content", "")
        if not isinstance(content, str):
            break

        filtered, stats = filter_think_content(content, min_chars=min_chars)
        if stats is None:
            break  # nothing to do

        # Build modified record (shallow copy to avoid mutating caller's dict)
        new_conv = list(conv)
        new_conv[mi] = {**msg, "content": filtered}
        new_record = {**record, "conversation": new_conv}

        # ── Fix filter_text ──────────────────────────────────────────
        # production_v11 stores filter_text in two forms:
        #   Case A (normal): reasoning + "\n\n" + post_think  (no </think> tag)
        #   Case B (theory): full final_assistant string  (may contain </think>)
        # In both cases we must replace the original think with the distilled one.
        ft = record.get("filter_text")
        if isinstance(ft, str) and ft:
            # Extract original think text (before </think> in the filtered content)
            orig_idx = content.lower().find("</think>")
            original_think = content[:orig_idx] if orig_idx >= 0 else ""
            distilled_think = (
                filtered[: filtered.lower().find("</think>")]
                if "</think>" in filtered.lower()
                else ""
            )

            if "</think>" in ft.lower():
                # Case B: apply filter directly on filter_text
                ft_idx = ft.lower().find("</think>")
                ft_think = ft[:ft_idx]
                ft_rest = ft[ft_idx:]
                if len(ft_think) >= min_chars:
                    ft_distilled, _ = filter_think_content(
                        ft_think + "</think>", min_chars=min_chars
                    )
                    if ft_distilled:
                        new_ft_think = ft_distilled[
                            : ft_distilled.lower().find("</think>")
                        ]
                        new_record["filter_text"] = new_ft_think + ft_rest
            elif original_think and ft.startswith(original_think[:200]):
                # Case A: replace reasoning prefix with distilled version
                suffix = ft[len(original_think) :]
                new_record["filter_text"] = distilled_think + suffix

        rid = record.get("id", "unknown")
        logger.debug(
            "think_filter [%s]: %d \u2192 %d chars (%.1f%% reduction) | %s",
            rid,
            stats["original_chars"],
            stats["distilled_chars"],
            stats["reduction_pct"],
            ", ".join(stats["strategies"]),
        )
        return new_record, stats

    return record, None
