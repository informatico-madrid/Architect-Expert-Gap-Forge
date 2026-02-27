#!/usr/bin/env python3
"""Thought Distillation Script for Blackwell SFT Dataset.

Reduces verbosity in <think> blocks by eliminating redundant paragraphs,
duplicate code blocks, and repeated bullet items — while preserving semantic
coherence and the integrity of all <tool_call>/<write_action> content.

Usage (test mode - top N longest):
  python3 diagnose/distill_v11.py \
    --input data/synthetic/v11_diversified_20260226_031536.jsonl \
    --health-report data/reports/health_audit_report.json \
    --test-report data/reports/distillation_test_report.json \
    --min-think-chars 5000 \
    --dev-samples 5

Full dataset mode:
  python3 diagnose/distill_v11.py \
    --input data/synthetic/v11_diversified_20260226_031536.jsonl \
    --output data/synthetic/v11_distilled.jsonl \
    --min-think-chars 5000
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Patterns discovered from analysis of 1000 longest samples
# ---------------------------------------------------------------------------

# Revision markers that signal iterative refinement cycles
REVISION_MARKERS_RE = re.compile(
    r"^\s*\d+[\.\)]\s*(?:revisando|para la implementación|para el manejo|"
    r"revisemos|necesito|verificando|comprobando|analicemos|"
    r"para el código final|pensando en|revisando el esqueleto|"
    r"revisando el contexto|revisando las reglas|revisando las leyes|"
    r"revisando los requisitos|para el dataupdatecoordinator|"
    r"implementación final|para la implementación final|"
    r"revisando el blueprint|revisando el código)",
    re.IGNORECASE | re.MULTILINE,
)

# Code fence pattern
CODE_FENCE_RE = re.compile(r"```[\w]*\n([\s\S]*?)```", re.MULTILINE)

# Bullet/list item
BULLET_RE = re.compile(r"^\s*[-*•]\s+", re.MULTILINE)


# ---------------------------------------------------------------------------
# Similarity helpers
# ---------------------------------------------------------------------------

def _normalize_for_compare(text: str) -> str:
    """Lowercase, collapse whitespace, strip punctuation for comparison."""
    t = text.strip().lower()
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"[^\w\s]", "", t)
    return t


def _similarity(a: str, b: str) -> float:
    """Quick similarity ratio between two strings (0..1)."""
    if not a or not b:
        return 0.0
    # For very long strings, compare first 500 chars for speed
    a_cmp = _normalize_for_compare(a[:500])
    b_cmp = _normalize_for_compare(b[:500])
    if a_cmp == b_cmp:
        return 1.0
    return SequenceMatcher(None, a_cmp, b_cmp).ratio()


def _is_code_block(paragraph: str) -> bool:
    """Check if paragraph is predominantly a code block."""
    stripped = paragraph.strip()
    return stripped.startswith("```") or stripped.startswith("def ") or stripped.startswith("class ")


def _contains_hardware_or_file_analysis(paragraph: str) -> bool:
    """Detect paragraphs that specifically analyze hardware deps or filenames."""
    keywords = [
        r"\.py\b", r"\.yaml\b", r"\.json\b", r"manifest\.json",
        r"device_class", r"hardware", r"firmware", r"sensor\.",
        r"platform_schema", r"config_entry", r"runtime_data",
        r"webhook_id", r"entry\.data\[", r"hass\.data\[",
    ]
    text_lower = paragraph.lower()
    matches = sum(1 for kw in keywords if re.search(kw, text_lower))
    return matches >= 2


# ---------------------------------------------------------------------------
# Core distillation strategies
# ---------------------------------------------------------------------------

def _deduplicate_paragraphs(paragraphs: List[str], sim_threshold: float = 0.85) -> List[str]:
    """Remove near-duplicate paragraphs, keeping the LAST (most refined) occurrence.
    
    Strategy: For each paragraph, if a later paragraph is ≥sim_threshold similar,
    the earlier one is marked as redundant. This preserves the final refined version.
    """
    n = len(paragraphs)
    keep = [True] * n
    
    # Build normalized keys for fast comparison
    norm_keys = [_normalize_for_compare(p[:300]) for p in paragraphs]
    
    for i in range(n):
        if not keep[i]:
            continue
        if len(paragraphs[i].strip()) < 30:
            continue  # skip tiny paragraphs
            
        for j in range(i + 1, n):
            if not keep[j]:
                continue
            # Quick check: if normalized keys are very similar
            if norm_keys[i] == norm_keys[j]:
                keep[i] = False  # drop earlier, keep later
                break
            elif len(norm_keys[i]) > 20 and len(norm_keys[j]) > 20:
                sim = _similarity(paragraphs[i], paragraphs[j])
                if sim >= sim_threshold:
                    keep[i] = False  # drop earlier
                    break
    
    return [p for p, k in zip(paragraphs, keep) if k]


def _deduplicate_code_blocks(think_text: str) -> str:
    """Find duplicate code blocks within think text and keep only the last occurrence."""
    code_blocks = list(CODE_FENCE_RE.finditer(think_text))
    if len(code_blocks) < 2:
        return think_text
    
    # Group by normalized content
    block_groups: Dict[str, List[re.Match]] = {}
    for m in code_blocks:
        key = _normalize_for_compare(m.group(1)[:400])
        if len(key) < 20:
            continue  # Skip tiny code blocks
        block_groups.setdefault(key, []).append(m)
    
    # Find blocks to remove (all but last in each group)
    remove_spans = []
    for key, matches in block_groups.items():
        if len(matches) >= 2:
            # Check similarity more carefully
            for earlier in matches[:-1]:
                sim = _similarity(earlier.group(1), matches[-1].group(1))
                if sim >= 0.80:
                    remove_spans.append((earlier.start(), earlier.end()))
    
    if not remove_spans:
        return think_text
    
    # Sort by position descending to remove from end first
    remove_spans.sort(key=lambda x: x[0], reverse=True)
    result = think_text
    for start, end in remove_spans:
        # Remove the code block and any trailing whitespace
        result = result[:start].rstrip() + "\n\n" + result[end:].lstrip()
    
    return result


def _deduplicate_bullet_items(paragraph: str) -> str:
    """Within a paragraph containing bullet/numbered items, remove exact duplicates."""
    lines = paragraph.split("\n")
    seen_items = set()
    result_lines = []
    
    for line in lines:
        stripped = line.strip()
        # Check if it's a bullet/numbered item
        is_bullet = bool(re.match(r"^\s*[-*•]\s+", line)) or bool(re.match(r"^\s*\d+[\.\)]\s+", line))
        
        if is_bullet:
            normalized = _normalize_for_compare(stripped)
            if normalized in seen_items:
                continue  # skip duplicate bullet
            seen_items.add(normalized)
        
        result_lines.append(line)
    
    return "\n".join(result_lines)


def _collapse_consecutive_similar_lines(text: str, max_consecutive: int = 2) -> str:
    """If the same line appears consecutively more than max_consecutive times, collapse."""
    lines = text.split("\n")
    result = []
    prev_norm = None
    consecutive_count = 0
    
    for line in lines:
        norm = _normalize_for_compare(line)
        if norm == prev_norm and len(norm) > 15:
            consecutive_count += 1
            if consecutive_count <= max_consecutive:
                result.append(line)
            # else: skip
        else:
            consecutive_count = 1
            prev_norm = norm
            result.append(line)
    
    return "\n".join(result)


def _prune_iterative_revision_cycles(paragraphs: List[str], sim_threshold: float = 0.75) -> List[str]:
    """Detect and collapse iterative 'revision cycles' where the model restarts analysis.
    
    Pattern: numbered items that revisit the same analysis topics. We keep the last
    complete cycle and remove earlier ones.
    """
    # Detect revision cycle boundaries (numbered items that restart from 1 or similar)
    cycle_starts = []
    for i, p in enumerate(paragraphs):
        stripped = p.strip()
        # A cycle might restart with "1." or similar low numbers after high ones
        if re.match(r"^\s*1[\.\)]\s+", stripped):
            cycle_starts.append(i)
    
    if len(cycle_starts) < 2:
        return paragraphs  # no cycles detected
    
    # Check if cycles are similar (compare content of first cycle with subsequent)
    # If cycles are similar enough, keep only the last one
    cycles = []
    for ci, start in enumerate(cycle_starts):
        end = cycle_starts[ci + 1] if ci + 1 < len(cycle_starts) else len(paragraphs)
        cycle_text = "\n".join(paragraphs[start:end])
        cycles.append((start, end, cycle_text))
    
    if len(cycles) < 2:
        return paragraphs
    
    # Compare each cycle with the last one
    last_cycle_text = cycles[-1][2]
    redundant_ranges = []
    
    for cycle_start, cycle_end, cycle_text in cycles[:-1]:
        sim = _similarity(cycle_text, last_cycle_text)
        if sim >= sim_threshold:
            redundant_ranges.append((cycle_start, cycle_end))
    
    if not redundant_ranges:
        return paragraphs
    
    # Remove redundant cycles
    keep = [True] * len(paragraphs)
    for start, end in redundant_ranges:
        for i in range(start, end):
            keep[i] = False
    
    return [p for p, k in zip(paragraphs, keep) if k]


# ---------------------------------------------------------------------------
# Main distillation pipeline
# ---------------------------------------------------------------------------

def distill_think_block(think_text: str) -> Tuple[str, Dict[str, Any]]:
    """Apply all distillation strategies to a think block.
    
    Returns:
        (distilled_text, stats_dict) where stats_dict contains metrics about what was done.
    """
    original_len = len(think_text)
    stats = {
        "original_chars": original_len,
        "strategies_applied": [],
    }
    
    working = think_text
    
    # Strategy 1: Collapse consecutive duplicate lines
    before = len(working)
    working = _collapse_consecutive_similar_lines(working, max_consecutive=2)
    if len(working) < before:
        stats["strategies_applied"].append(f"consecutive_line_collapse: -{before - len(working)} chars")
    
    # Strategy 2: Deduplicate code blocks (keep last)
    before = len(working)
    working = _deduplicate_code_blocks(working)
    if len(working) < before:
        stats["strategies_applied"].append(f"code_block_dedup: -{before - len(working)} chars")
    
    # Strategy 3: Split into paragraphs and deduplicate
    paragraphs = [p for p in working.split("\n\n") if p.strip()]
    
    # Strategy 3a: Deduplicate bullet items within each paragraph
    before_total = sum(len(p) for p in paragraphs)
    paragraphs = [_deduplicate_bullet_items(p) for p in paragraphs]
    after_total = sum(len(p) for p in paragraphs)
    if after_total < before_total:
        stats["strategies_applied"].append(f"bullet_dedup: -{before_total - after_total} chars")
    
    # Strategy 3b: Prune iterative revision cycles
    before_count = len(paragraphs)
    paragraphs = _prune_iterative_revision_cycles(paragraphs, sim_threshold=0.70)
    if len(paragraphs) < before_count:
        stats["strategies_applied"].append(f"revision_cycle_prune: -{before_count - len(paragraphs)} paragraphs")
    
    # Strategy 3c: Paragraph-level deduplication (keep last)
    before_count = len(paragraphs)
    paragraphs = _deduplicate_paragraphs(paragraphs, sim_threshold=0.82)
    if len(paragraphs) < before_count:
        stats["strategies_applied"].append(f"paragraph_dedup: -{before_count - len(paragraphs)} paragraphs")
    
    # Reassemble
    working = "\n\n".join(paragraphs)
    
    # Final cleanup: remove excessive blank lines
    working = re.sub(r"\n{3,}", "\n\n", working)
    
    stats["distilled_chars"] = len(working)
    stats["reduction_pct"] = round((1 - len(working) / max(1, original_len)) * 100, 1)
    
    return working, stats


def extract_think_and_rest(content: str) -> Tuple[Optional[str], Optional[str]]:
    """Split assistant content into (think_text, rest_after_close_tag).
    
    The think block has NO opening <think> tag, but has a closing </think>.
    """
    idx = content.lower().find("</think>")
    if idx < 0:
        return None, None
    think_text = content[:idx]
    rest = content[idx:]  # includes </think> and everything after
    return think_text, rest


def distill_record(rec: Dict[str, Any]) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    """Distill a single record's think block.
    
    Returns:
        (modified_record, distillation_info) or (original_record, None) if not applicable.
    """
    conv = rec.get("conversation")
    if not isinstance(conv, list):
        return rec, None
    
    modified = False
    info = None
    
    for mi, m in enumerate(conv):
        if not (isinstance(m, dict) and m.get("role") == "assistant"):
            continue
        content = m.get("content", "")
        if not isinstance(content, str):
            continue
        
        think_text, rest = extract_think_and_rest(content)
        if think_text is None or len(think_text) < 100:
            continue
        
        # SACRED CONSTRAINT: rest (after </think>) is never modified
        distilled, stats = distill_think_block(think_text)
        
        if stats["reduction_pct"] > 0:
            # Rebuild content: distilled think + original rest (untouched)
            new_content = distilled + rest
            rec = dict(rec)  # shallow copy
            rec["conversation"] = list(conv)
            rec["conversation"][mi] = dict(m)
            rec["conversation"][mi]["content"] = new_content
            modified = True

            # ── Fix filter_text: it also contains the raw reasoning ──
            # Case A: filter_text starts with the original think text (normal mode)
            #         filter_text = reasoning + "\n\n" + post_think  (no </think> tag)
            # Case B: filter_text IS the full assistant content (theory mode)
            #         filter_text contains </think> inline
            ft = rec.get("filter_text")
            if isinstance(ft, str) and ft:
                if "</think>" in ft.lower():
                    # Case B: apply the same think-block distillation directly
                    ft_think, ft_rest = extract_think_and_rest(ft)
                    if ft_think and len(ft_think) >= 100:
                        ft_distilled, _ = distill_think_block(ft_think)
                        rec["filter_text"] = ft_distilled + ft_rest
                elif ft.startswith(think_text[:200]):
                    # Case A: replace the reasoning prefix with the distilled version
                    suffix = ft[len(think_text):]
                    rec["filter_text"] = distilled + suffix

            info = {
                "sample_id": rec.get("id", "unknown"),
                "original_think_length": stats["original_chars"],
                "distilled_think_length": stats["distilled_chars"],
                "reduction_pct": stats["reduction_pct"],
                "strategies": stats["strategies_applied"],
            }
        break  # only process first assistant message
    
    return rec, info


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Thought Distillation for SFT dataset")
    parser.add_argument("--input", "-i", required=True,
                        help="Input JSONL dataset")
    parser.add_argument("--output", "-o", default=None,
                        help="Output distilled JSONL (full mode). If omitted, no full output.")
    parser.add_argument("--health-report", default=None,
                        help="Health audit report JSON (to prioritise long samples)")
    parser.add_argument("--test-report", default="data/reports/distillation_test_report.json",
                        help="Output test report for dev samples")
    parser.add_argument("--min-think-chars", type=int, default=5000,
                        help="Only distill samples with think_length >= this value")
    parser.add_argument("--dev-samples", type=int, default=5,
                        help="Number of development samples to process in test mode")
    args = parser.parse_args(argv)

    # ---- Phase 1: Load health report to identify targets ----
    target_lines = set()
    if args.health_report and os.path.exists(args.health_report):
        with open(args.health_report) as f:
            hr = json.load(f)
        for s in hr.get("suspects", []):
            if s.get("think_length", 0) >= args.min_think_chars:
                target_lines.add(s["line"])
        print(f"[INFO] Health report loaded: {len(target_lines)} suspects with think >= {args.min_think_chars}")

    # ---- Phase 2: Scan dataset, collect all records with long think blocks ----
    print("[INFO] Scanning dataset for long think blocks...")
    candidates = []  # (line_num, sample_id, think_length, record_json_line)

    with open(args.input, "r", encoding="utf-8") as fin:
        for i, line in enumerate(fin, start=1):
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            
            rid = rec.get("id", f"line_{i}")
            conv = rec.get("conversation", [])
            
            for m in conv:
                if isinstance(m, dict) and m.get("role") == "assistant":
                    content = m.get("content", "")
                    if isinstance(content, str):
                        idx = content.lower().find("</think>")
                        if idx > 0 and idx >= args.min_think_chars:
                            candidates.append((i, rid, idx, line))
                    break

    print(f"[INFO] Found {len(candidates)} records with think >= {args.min_think_chars} chars")

    # Sort by think_length descending
    candidates.sort(key=lambda x: x[2], reverse=True)

    # ---- Phase 3: Select dev samples (top N by length) ----
    dev_candidates = candidates[:args.dev_samples]

    print(f"\n[INFO] Processing {len(dev_candidates)} development samples:")
    for line_num, rid, tlen, _ in dev_candidates:
        print(f"  - {rid} (line {line_num}, think_length={tlen})")

    # ---- Phase 4: Distill dev samples ----
    test_results = []

    for line_num, rid, tlen, raw_line in dev_candidates:
        rec = json.loads(raw_line)
        distilled_rec, info = distill_record(rec)

        if info:
            # Extract think text for comparison
            original_think, _ = extract_think_and_rest(
                next(m["content"] for m in rec["conversation"] if m.get("role") == "assistant")
            )
            distilled_think, _ = extract_think_and_rest(
                next(m["content"] for m in distilled_rec["conversation"] if m.get("role") == "assistant")
            )
            
            result = {
                "sample_id": rid,
                "line": line_num,
                "original_think_length": info["original_think_length"],
                "distilled_think_length": info["distilled_think_length"],
                "reduction_pct": info["reduction_pct"],
                "strategies_applied": info["strategies"],
                "comparison": {
                    "original_full": original_think or "",
                    "distilled_full": distilled_think or "",
                },
            }
            test_results.append(result)
            print(f"  [OK] {rid}: {info['original_think_length']} -> {info['distilled_think_length']} "
                  f"({info['reduction_pct']}% reduction)")
            for s in info["strategies"]:
                print(f"       - {s}")
        else:
            test_results.append({
                "sample_id": rid,
                "line": line_num,
                "original_think_length": tlen,
                "distilled_think_length": tlen,
                "reduction_pct": 0.0,
                "strategies_applied": [],
                "comparison": {},
            })
            print(f"  [SKIP] {rid}: no reduction applicable")

    # ---- Phase 5: Write test report ----
    os.makedirs(os.path.dirname(args.test_report), exist_ok=True)
    
    report = {
        "mode": "development_test",
        "input_file": args.input,
        "min_think_chars": args.min_think_chars,
        "dev_samples_requested": args.dev_samples,
        "dev_samples_processed": len(test_results),
        "total_candidates_in_dataset": len(candidates),
        "summary": {
            "avg_reduction_pct": round(
                sum(r["reduction_pct"] for r in test_results) / max(1, len(test_results)), 1
            ),
            "max_reduction_pct": max((r["reduction_pct"] for r in test_results), default=0),
            "min_reduction_pct": min((r["reduction_pct"] for r in test_results), default=0),
        },
        "samples": test_results,
    }

    with open(args.test_report, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n[DONE] Test report written: {args.test_report}")
    print(f"[DONE] Average reduction: {report['summary']['avg_reduction_pct']}%")

    # ---- Phase 6 (optional): Full dataset distillation ----
    if args.output:
        print(f"\n[INFO] Full distillation mode -> {args.output}")
        os.makedirs(os.path.dirname(args.output) if os.path.dirname(args.output) else ".", exist_ok=True)
        
        total = 0
        distilled_count = 0
        
        with open(args.input, "r", encoding="utf-8") as fin, \
             open(args.output, "w", encoding="utf-8") as fout:
            for i, line in enumerate(fin, start=1):
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    fout.write(line)
                    continue
                
                total += 1
                
                # Check if this record needs distillation
                needs_distill = False
                conv = rec.get("conversation", [])
                for m in conv:
                    if isinstance(m, dict) and m.get("role") == "assistant":
                        content = m.get("content", "")
                        if isinstance(content, str):
                            idx = content.lower().find("</think>")
                            if idx >= args.min_think_chars:
                                needs_distill = True
                        break
                
                if needs_distill:
                    distilled_rec, info = distill_record(rec)
                    fout.write(json.dumps(distilled_rec, ensure_ascii=False) + "\n")
                    if info and info["reduction_pct"] > 0:
                        distilled_count += 1
                else:
                    fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
        
        print(f"[DONE] Full distillation complete: {distilled_count}/{total} records modified")
        print(f"[DONE] Output: {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
