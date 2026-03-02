#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
AEGF Dataset Audit — Unified Quality Inspector
===============================================

    • Full-dataset legacy / blocking / contradiction scan
    • Gold-injection vs gold-skipping classification
    • Legacy breakdown by example_type and response location
    • Sampled five-pillar health score

Two operating modes
-------------------
  --mode report  (default)
      Stream the entire dataset. Detect every problematic record across five
      categories. Write a structured JSON report, per-category ID lists, a
      plain-text summary table, and a master summary update.
      **No data is modified.**

  --mode clean
      Read a previously generated audit report and write a *new* JSONL that
      excludes all flagged records. The original dataset file is never touched —
      a timestamped backup path is logged for reference. Use this mode only
      after you have reviewed and validated the report.
      **The original file is never deleted or overwritten.**

Problem categories detected
---------------------------
  legacy        Deprecated Home Assistant patterns present in the assistant
                response (hass.data[], TEMP_CELSIUS, async_forward_entry_setup,
                blocking requests.* / time.sleep / urllib.request, self._state).

  blocking_io   Synchronous I/O calls in the final write action when the code
                is expected to be async (requests., time.sleep(), urllib.request).

  contradiction Blocking I/O in the write action while the reasoning chain
                explicitly references async / non-blocking idioms — the model
                "thinks" async but "writes" sync (direct training poison).

  poison        Jinja / template rendering artifacts and structural placeholders
                that should never reach a training corpus.

  gold_problem  A record has gold_injected=True but the generated action text
                is empty, a stub, or still contains the original placeholder.

Gold-injection classification
------------------------------
  For each flagged record the audit records whether it was generated under:
    gold injection  → metadata.gold_injected == True
    gold skiping    → metadata.gold_injected == False  (or field absent)

Architecture
------------
  AuditConfig        Typed configuration dataclass (paths, toggles, thresholds).
  Detectors          Module-level pure functions. Each accepts raw text and
                     returns bool. No side-effects.
  RecordAnalysis     Frozen dataclass: per-record audit result (flags + metadata).
  DatasetAuditor     Main orchestrator. Streams the JSONL and applies every
                     detector. Accumulates RecordAnalysis objects.
  AuditReport        Post-processes DatasetAuditor results into structured JSON
                     + plain-text summaries.
  DatasetCleaner     Reads an existing audit report and produces a filtered JSONL.
  AEGFAuditCLI       Argument parsing and mode dispatch.

Usage
-----
  # Full audit report (no data modification):
  python diagnose/aegf_dataset_audit.py \\
      --input  data/synthetic/v11_diversified_*.jsonl \\
      --report-dir data/reports \\
      --mode   report

  # Produce cleaned dataset (requires prior report):
  python diagnose/aegf_dataset_audit.py \\
      --input  data/synthetic/v11_diversified_*.jsonl \\
      --output data/synthetic/v11_clean.jsonl \\
      --report-dir data/reports \\
      --mode   clean

  # Quick 5-pillar health score on a random sample:
  python diagnose/aegf_dataset_audit.py \\
      --input  data/synthetic/v11_diversified_*.jsonl \\
      --mode   report \\
      --health-sample 100
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime
import json
import random
import re
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Dict, FrozenSet, Iterator, List, Optional, Set, Tuple

# ─────────────────────────────────────────────────────────────────────────────
# 1.  CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

@dataclasses.dataclass
class AuditConfig:
    """All tunable parameters in one place."""

    # ── Detector: legacy patterns ──────────────────────────────────────────
    legacy_patterns: Tuple[str, ...] = (
        r"hass\.data\[",
        r"hass\.data\.setdefault",
        r"\bTEMP_CELSIUS\b|\bTEMP_FAHRENHEIT\b|\bTEMP_KELVIN\b",
        r"async_forward_entry_setup\b",
        r"requests\.get\(|requests\.post\(|requests\.put\(|requests\.delete\(",
        r"(?<!await\s)time\.sleep\(",
        r"urllib\.request\.urlopen",
        r"\bself\._state\s*=\b",
    )

    # ── Detector: blocking I/O ─────────────────────────────────────────────
    blocking_patterns: Tuple[str, ...] = (
        r"requests\.",
        r"time\.sleep\(",
        r"urllib\.request",
    )

    # ── Detector: async reasoning signal ──────────────────────────────────
    async_reasoning_patterns: Tuple[str, ...] = (
        r"\bawait\b",
        r"\basyncio\b",
        r"async_add_executor_job",
        r"no blocking",
        r"avoid blocking",
        r"non-blocking",
    )

    # ── Detector: poison / jinja artifacts ────────────────────────────────
    poison_patterns: Tuple[str, ...] = (
        r"\{\{-?\s*None\s*-?\}\}",
        r"\bas_timestamp\s*\(",
        r"platform:\s*template",
        r"^\s*trigger:\s*\n\s*-",
        r"^\s*condition:\s*\n\s*-",
        r"^\s*action:\s*\n\s*-",
        r"\{\{-?\s*func\s*\(",
        r"\{\{-?\s*_\w+\s*\(",
    )

    # ── Detector: HA terminology (health score) ────────────────────────────
    ha_keywords: Tuple[str, ...] = (
        "CoordinatorEntity",
        "entry.runtime_data",
        "async_forward_entry_setups",
        "async_add_executor_job",
        "await asyncio",
        "ConfigFlow",
        "EntityDescription",
    )

    # ── Gold-problem thresholds ────────────────────────────────────────────
    gold_min_action_chars: int = 180
    gold_placeholder_marker: str = "Expert HA 2026 Implementation"

    # ── Health-score sample ────────────────────────────────────────────────
    health_sample_size: int = 0          # 0 = disabled
    health_sample_seed: int = 42
    health_target_types: Tuple[str, ...] = ("nominal", "contrast", "error_recovery")


# ─────────────────────────────────────────────────────────────────────────────
# 2.  COMPILED PATTERN CACHE  (module-level, built once)
# ─────────────────────────────────────────────────────────────────────────────

class _PatternCache:
    """Lazily compile regex patterns and cache them against a config instance."""

    def __init__(self, cfg: AuditConfig) -> None:
        self.legacy_re   = [re.compile(p)                      for p in cfg.legacy_patterns]
        self.blocking_re = [re.compile(p)                      for p in cfg.blocking_patterns]
        self.async_re    = re.compile("|".join(cfg.async_reasoning_patterns), re.I)
        self.poison_re   = [re.compile(p, re.MULTILINE)        for p in cfg.poison_patterns]
        self.ha_kw_re    = [re.compile(re.escape(k), re.I)     for k in cfg.ha_keywords]

    def has_legacy(self, text: str) -> bool:
        return any(r.search(text) for r in self.legacy_re)

    def has_blocking(self, text: str) -> bool:
        return any(r.search(text) for r in self.blocking_re)

    def has_async_signal(self, text: str) -> bool:
        return bool(self.async_re.search(text))

    def count_poison(self, text: str) -> int:
        return sum(1 for r in self.poison_re if r.search(text))

    def count_ha_kw(self, text: str) -> int:
        return sum(1 for r in self.ha_kw_re if r.search(text))


# ─────────────────────────────────────────────────────────────────────────────
# 3.  TEXT EXTRACTION HELPERS
# ─────────────────────────────────────────────────────────────────────────────

_RE_TOOL_CALL    = re.compile(r"<tool_call>(.*?)</tool_call>",     re.DOTALL)
_RE_WRITE_ACTION = re.compile(r"<write_action>(.*?)</write_action>", re.DOTALL)
_RE_CONTENT      = re.compile(r"<content>(.*?)</content>",           re.DOTALL)
_RE_WRITE_FILE   = re.compile(
    r'"name"\s*:\s*"write_to_file".*?"content"\s*:\s*"(.*?)"(?=\s*[,}])',
    re.DOTALL,
)


def _extract_conversation_parts(rec: dict) -> Tuple[str, str]:
    """Return (user_text, assistant_raw) from the conversation list."""
    user_parts: List[str] = []
    assistant_raw = ""
    for msg in (rec.get("conversation") or []):
        role    = msg.get("role", "")
        content = msg.get("content", "") or ""
        if role == "user":
            user_parts.append(content)
        elif role == "assistant" and not assistant_raw:
            assistant_raw = content
    return "\n".join(user_parts), assistant_raw


def _extract_reasoning(assistant_raw: str) -> str:
    """Extract the <think>…</think> block (everything before </think>)."""
    if not assistant_raw:
        return ""
    if "<think>" in assistant_raw and "</think>" in assistant_raw:
        return assistant_raw.split("<think>", 1)[1].split("</think>", 1)[0].strip()
    if "</think>" in assistant_raw:
        return assistant_raw.split("</think>", 1)[0].strip()
    return ""


def _extract_action_text(assistant_raw: str, filter_text: str) -> str:
    """
    Extract the final write-action code from tool_call / write_action tags,
    including JSON arguments[@content] when present.
    Also appends the post-</think> narrative response if any.
    """
    combined = (assistant_raw or "") + "\n" + (filter_text or "")
    raw_blocks: List[str] = []
    for m in _RE_TOOL_CALL.finditer(combined):
        raw_blocks.append(m.group(1).strip())
    for m in _RE_WRITE_ACTION.finditer(combined):
        raw_blocks.append(m.group(1).strip())

    contents: List[str] = []
    for block in raw_blocks:
        try:
            obj = json.loads(block)
            items = obj if isinstance(obj, list) else [obj]
            for item in items:
                args = item.get("arguments", {})
                if isinstance(args, dict) and "content" in args:
                    contents.append(args["content"] or "")
        except Exception:
            cm = _RE_CONTENT.search(block)
            if cm:
                contents.append(cm.group(1).strip())
            else:
                contents.append(block)

    # Also include post-</think> narrative (non-tag response text)
    if "</think>" in assistant_raw:
        contents.append(assistant_raw.split("</think>", 1)[1])

    return "\n\n".join(contents)


# ─────────────────────────────────────────────────────────────────────────────
# 4.  PER-RECORD ANALYSIS  (frozen dataclass)
# ─────────────────────────────────────────────────────────────────────────────

@dataclasses.dataclass(frozen=True)
class RecordAnalysis:
    """Complete audit result for a single JSONL record."""

    # Identity
    record_id:    str
    example_type: str
    fragment_name: str
    source_file:   str
    checkpoint_key: str

    # Gold-injection origin
    gold_injected: bool

    # Problem flags
    flag_legacy:        bool
    flag_blocking:      bool
    flag_contradiction: bool
    flag_poison:        bool
    flag_gold_problem:  bool

    # Location details for legacy (where was the pattern found?)
    legacy_in_user:     bool     # pattern found in user message
    legacy_in_response: bool     # pattern found in assistant response / action

    # Gold-injection classification label
    gold_label: str  # "gold injection" | "gold skiping" | "unknown"

    # Health-score sub-metrics (used for sampled health report)
    reasoning_len:   int
    ha_kw_hits:      int
    filter_text_len: int
    alignment:       bool
    over_distilled:  bool
    poison_count:    int
    legacy_count:    int

    @property
    def is_flagged(self) -> bool:
        return (
            self.flag_legacy
            or self.flag_blocking
            or self.flag_contradiction
            or self.flag_poison
            or self.flag_gold_problem
        )

    @property
    def active_flags(self) -> List[str]:
        flags: List[str] = []
        if self.flag_legacy:        flags.append("legacy")
        if self.flag_blocking:      flags.append("blocking_io")
        if self.flag_contradiction: flags.append("contradiction")
        if self.flag_poison:        flags.append("poison")
        if self.flag_gold_problem:  flags.append("gold_problem")
        return flags


# ─────────────────────────────────────────────────────────────────────────────
# 5.  DATASET AUDITOR  (orchestrator)
# ─────────────────────────────────────────────────────────────────────────────

class DatasetAuditor:
    """
    Streams a JSONL dataset and applies all detectors to every record.
    Accumulates RecordAnalysis objects; does not modify any file.
    """

    def __init__(self, cfg: AuditConfig) -> None:
        self.cfg = cfg
        self._pc = _PatternCache(cfg)

    # ── public interface ───────────────────────────────────────────────────

    def run(self, input_path: Path) -> List[RecordAnalysis]:
        """Iterate over the dataset and return one RecordAnalysis per record."""
        results: List[RecordAnalysis] = []
        with input_path.open("r", encoding="utf-8") as fh:
            for lineno, raw in enumerate(fh, start=1):
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    rec = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                analysis = self._analyze(rec)
                results.append(analysis)
        return results

    # ── internal analysis ──────────────────────────────────────────────────

    def _analyze(self, rec: dict) -> RecordAnalysis:
        meta          = rec.get("metadata") or {}
        record_id     = rec.get("id") or "<no-id>"
        example_type  = (meta.get("example_type") or "unknown").lower()
        fragment_name = meta.get("fragment_name") or meta.get("section_name") or ""
        source_file   = meta.get("source_file") or ""
        ck_key        = meta.get("checkpoint_key") or ""
        gold_injected = bool(meta.get("gold_injected"))
        filter_text   = rec.get("filter_text") or ""

        user_text, assistant_raw = _extract_conversation_parts(rec)
        reasoning   = _extract_reasoning(assistant_raw)
        action_text = _extract_action_text(assistant_raw, filter_text)

        # ── detectors ─────────────────────────────────────────────────────
        flag_legacy_user = self._pc.has_legacy(user_text)
        flag_legacy_resp = self._pc.has_legacy(action_text)
        flag_legacy      = flag_legacy_resp  # only response-side matters for training

        flag_blocking      = self._pc.has_blocking(action_text)
        flag_contradiction = flag_blocking and self._pc.has_async_signal(reasoning)

        poison_count = self._pc.count_poison(action_text)
        flag_poison  = poison_count > 0

        flag_gold_problem = False
        if gold_injected:
            action_stripped = action_text.strip()
            if (
                len(action_stripped) < self.cfg.gold_min_action_chars
                or self.cfg.gold_placeholder_marker in action_stripped
                or action_stripped.startswith("...")
            ):
                flag_gold_problem = True

        # ── gold classification ────────────────────────────────────────────
        if "gold_injected" in meta:
            gold_label = "gold injection" if gold_injected else "gold skiping"
        else:
            # Heuristic fallback
            has_block = self._pc.has_blocking(action_text)
            has_async = self._pc.has_async_signal(action_text)
            if has_block:
                gold_label = "gold injection"
            elif has_async:
                gold_label = "gold skiping"
            else:
                gold_label = "unknown"

        # ── health-score sub-metrics ───────────────────────────────────────
        reasoning_len   = len(reasoning)
        ha_kw_hits      = self._pc.count_ha_kw(reasoning)
        filter_text_len = len(filter_text)
        alignment       = bool(
            (fragment_name and fragment_name.lower() in user_text.lower())
            or (source_file and source_file.lower() in user_text.lower())
        )
        over_distilled  = reasoning_len > 300 and filter_text_len < 80
        legacy_count    = sum(1 for r in self._pc.legacy_re if r.search(action_text))

        return RecordAnalysis(
            record_id    = record_id,
            example_type = example_type,
            fragment_name = fragment_name,
            source_file   = source_file,
            checkpoint_key = ck_key,
            gold_injected  = gold_injected,
            flag_legacy        = flag_legacy,
            flag_blocking      = flag_blocking,
            flag_contradiction = flag_contradiction,
            flag_poison        = flag_poison,
            flag_gold_problem  = flag_gold_problem,
            legacy_in_user     = flag_legacy_user,
            legacy_in_response = flag_legacy_resp,
            gold_label = gold_label,
            reasoning_len   = reasoning_len,
            ha_kw_hits      = ha_kw_hits,
            filter_text_len = filter_text_len,
            alignment       = alignment,
            over_distilled  = over_distilled,
            poison_count    = poison_count,
            legacy_count    = legacy_count,
        )


# ─────────────────────────────────────────────────────────────────────────────
# 6.  HEALTH SCORE  (AEGF Five-Pillar)
# ─────────────────────────────────────────────────────────────────────────────

def _compute_health_score(
    analyses: List[RecordAnalysis],
) -> Dict:
    """
    Five-pillar AEGF health score on a (sampled) list of RecordAnalysis.
    Each pillar contributes 0–20 points; total is 0–100.
    """
    n = len(analyses)
    if n == 0:
        return {"pillars": {}, "health_score": 0.0, "sample_size": 0}

    # Pillar 1 — Contextual Alignment
    p1 = round(sum(1 for a in analyses if a.alignment) / n * 20, 2)

    # Pillar 2 — Reasoning Quality
    def _r_score(a: RecordAnalysis) -> float:
        length_score = min(a.reasoning_len, 500) / 500
        kw_score     = min(a.ha_kw_hits / 3, 1.0)
        return 0.6 * length_score + 0.4 * kw_score
    p2 = round(mean(_r_score(a) for a in analyses) * 20, 2)

    # Pillar 3 — Gold Injection Integrity
    def _g_score(a: RecordAnalysis) -> float:
        if not a.gold_injected:
            return 1.0 if a.reasoning_len > 100 else 0.8
        return 0.0 if a.flag_gold_problem else 1.0
    p3 = round(mean(_g_score(a) for a in analyses) * 20, 2)

    # Pillar 4 — Distillation Efficacy
    def _d_score(a: RecordAnalysis) -> float:
        if a.reasoning_len == 0:
            return 0.3 if a.filter_text_len < 100 else 0.6
        ratio = min(a.filter_text_len / max(1, a.reasoning_len), 1.0)
        overlap = 1.0 if a.ha_kw_hits > 0 and a.filter_text_len > 0 else 0.0
        return 0.6 * ratio + 0.4 * overlap
    p4 = round(mean(_d_score(a) for a in analyses) * 20, 2)

    # Pillar 5 — 2026 Law Compliance
    def _l_score(a: RecordAnalysis) -> float:
        violations = a.poison_count + a.legacy_count
        return max(0.0, 1.0 - min(violations, 3) / 3.0)
    p5 = round(mean(_l_score(a) for a in analyses) * 20, 2)

    return {
        "pillars": {
            "contextual_alignment":     p1,
            "reasoning_quality":        p2,
            "gold_injection_integrity": p3,
            "distillation_efficacy":    p4,
            "law_2026_compliance":      p5,
        },
        "health_score": round(p1 + p2 + p3 + p4 + p5, 2),
        "sample_size":  n,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 7.  AUDIT REPORT  (serialization)
# ─────────────────────────────────────────────────────────────────────────────

class AuditReport:
    """
    Post-processes a list of RecordAnalysis objects into structured artifacts:
      • Full JSON report
      • Per-category ID lists (.txt files)
      • Plain-text summary table
      • Updated master problem_id_summary.json
    """

    CATEGORY_FLAGS = {
        "legacy":        "flag_legacy",
        "blocking_io":   "flag_blocking",
        "contradiction": "flag_contradiction",
        "poison":        "flag_poison",
        "gold_problem":  "flag_gold_problem",
    }

    def __init__(
        self,
        analyses: List[RecordAnalysis],
        cfg: AuditConfig,
        input_path: Path,
        report_dir: Path,
        health_sample_size: int = 0,
        health_sample_seed:  int = 42,
    ) -> None:
        self.analyses       = analyses
        self.cfg            = cfg
        self.input_path     = input_path
        self.report_dir     = report_dir
        self.health_sample  = health_sample_size
        self.health_seed    = health_sample_seed
        self._ts            = datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y%m%d_%H%M%S"
        )

    # ── public entry point ─────────────────────────────────────────────────

    def write(self) -> Path:
        """Build and persist all report artifacts. Returns path of main JSON report."""
        self.report_dir.mkdir(parents=True, exist_ok=True)

        by_cat = self._build_category_index()
        all_flagged = {
            a.record_id for a in self.analyses if a.is_flagged
        }

        # 1. Per-category txt + labeled txt
        for cat, ids in by_cat.items():
            self._write_id_list(cat, ids)

        # 2. Health score (optional sampled run)
        health = {}
        if self.health_sample > 0:
            health = self._compute_sampled_health()

        # 3. Legacy breakdown (AEGF deep-dive)
        legacy_breakdown = self._legacy_breakdown(by_cat.get("legacy", []))

        # 4. Full JSON report
        report = self._build_json_report(by_cat, all_flagged, health, legacy_breakdown)
        report_path = self.report_dir / "aegf_audit_report.json"
        report_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # 5. Plain-text summary
        summary_txt = self._build_summary_text(by_cat, all_flagged, health, legacy_breakdown)
        summary_path = self.report_dir / "aegf_audit_summary.txt"
        summary_path.write_text(summary_txt, encoding="utf-8")

        # 6. Master summary update
        self._update_master_summary(by_cat, all_flagged, report_path, summary_path, health)

        # Print to stdout
        print(summary_txt)
        print(f"\n[Report JSON]  {report_path}")
        print(f"[Summary TXT]  {summary_path}")

        return report_path

    # ── internal builders ──────────────────────────────────────────────────

    def _build_category_index(self) -> Dict[str, List[str]]:
        by_cat: Dict[str, List[str]] = {cat: [] for cat in self.CATEGORY_FLAGS}
        for a in self.analyses:
            for cat, flag_name in self.CATEGORY_FLAGS.items():
                if getattr(a, flag_name):
                    by_cat[cat].append(a.record_id)
        return by_cat

    def _write_id_list(self, category: str, ids: List[str]) -> None:
        # Plain list
        (self.report_dir / f"{category}_ids.txt").write_text(
            "\n".join(ids) + ("\n" if ids else ""),
            encoding="utf-8",
        )
        # Labeled TSV  (id <TAB> gold_label)
        id_set = {a.record_id: a.gold_label for a in self.analyses}
        lines = [f"{rid}\t{id_set.get(rid, 'unknown')}" for rid in ids]
        (self.report_dir / f"{category}_ids_labeled.txt").write_text(
            "\n".join(lines) + ("\n" if lines else ""),
            encoding="utf-8",
        )

    def _legacy_breakdown(self, legacy_ids: List[str]) -> Dict:
        """Break down legacy records by example_type and response location."""
        id_set = set(legacy_ids)
        buckets: Dict[str, Dict[str, List[str]]] = {
            "contrast": {
                "legacy_in_response":  [],
                "legacy_in_both":      [],
                "legacy_in_user_only": [],
            },
            "error_recovery": {
                "legacy_in_response":  [],
                "legacy_in_both":      [],
                "legacy_in_user_only": [],
            },
            "nominal": {
                "should_report": [],
                "user_only":     [],
            },
            "other": {
                "legacy_in_response":  [],
                "legacy_in_user_only": [],
            },
        }
        for a in self.analyses:
            if a.record_id not in id_set:
                continue
            et = a.example_type
            bucket_key = et if et in ("contrast", "error_recovery", "nominal") else "other"
            b = buckets[bucket_key]
            if et == "nominal":
                if a.legacy_in_response:
                    b["should_report"].append(a.record_id)
                else:
                    b["user_only"].append(a.record_id)
            else:
                if a.legacy_in_user and a.legacy_in_response:
                    b.get("legacy_in_both", b.get("legacy_in_response", [])).append(a.record_id)
                    if "legacy_in_both" in b:
                        pass  # already appended above
                    else:
                        b["legacy_in_response"].append(a.record_id)
                elif a.legacy_in_response:
                    b["legacy_in_response"].append(a.record_id)
                else:
                    b.get("legacy_in_user_only", b["legacy_in_user_only"]).append(a.record_id)

        real_problems = (
            len(buckets["nominal"]["should_report"])
            + len(buckets["contrast"]["legacy_in_response"])
            + len(buckets["contrast"]["legacy_in_both"])
            + len(buckets["error_recovery"]["legacy_in_response"])
            + len(buckets["error_recovery"]["legacy_in_both"])
            + len(buckets["other"]["legacy_in_response"])
        )
        return {
            "real_problem_total": real_problems,
            "user_only_total": (
                len(buckets["nominal"]["user_only"])
                + len(buckets["contrast"]["legacy_in_user_only"])
                + len(buckets["error_recovery"]["legacy_in_user_only"])
                + len(buckets["other"]["legacy_in_user_only"])
            ),
            "by_example_type": {k: {kk: len(vv) for kk, vv in v.items()} for k, v in buckets.items()},
        }

    def _compute_sampled_health(self) -> Dict:
        rng = random.Random(self.health_seed)
        per_type = max(1, self.health_sample // 3)
        by_type: Dict[str, List[RecordAnalysis]] = defaultdict(list)
        for a in self.analyses:
            by_type[a.example_type].append(a)

        sampled: List[RecordAnalysis] = []
        for t in self.cfg.health_target_types:
            pool = by_type.get(t, [])
            sampled.extend(rng.sample(pool, min(per_type, len(pool))))

        remaining = self.health_sample - len(sampled)
        sampled_set = set(id(a) for a in sampled)
        rest = [a for a in self.analyses if id(a) not in sampled_set]
        if remaining > 0 and rest:
            sampled.extend(rng.sample(rest, min(remaining, len(rest))))

        score = _compute_health_score(sampled)
        score["distribution"] = dict(Counter(a.example_type for a in sampled))
        score["critical_ids"] = [
            {"id": a.record_id, "flags": a.active_flags, "example_type": a.example_type}
            for a in sampled
            if a.is_flagged
        ]
        return score

    def _build_json_report(
        self,
        by_cat: Dict[str, List[str]],
        all_flagged: Set[str],
        health: Dict,
        legacy_breakdown: Dict,
    ) -> Dict:
        gold_label_map: Dict[str, Counter] = {}
        for cat, ids in by_cat.items():
            id_set = set(ids)
            ctr: Counter = Counter()
            for a in self.analyses:
                if a.record_id in id_set:
                    ctr[a.gold_label] += 1
            gold_label_map[cat] = dict(ctr)

        return {
            "__generated_utc": self._ts,
            "__tool": "aegf_dataset_audit.py",
            "__description": (
                "Unified dataset quality audit. Detects legacy, blocking I/O, "
                "contradictions, poison patterns, and gold-injection issues."
            ),
            "input_dataset": str(self.input_path),
            "total_records_checked":  len(self.analyses),
            "total_flagged_records":  len(all_flagged),
            "category_counts": {cat: len(ids) for cat, ids in by_cat.items()},
            "category_gold_label_breakdown": gold_label_map,
            "legacy_breakdown_by_example_type": legacy_breakdown,
            "health_score": health or None,
            "flagged_ids": {cat: ids for cat, ids in by_cat.items()},
        }

    def _build_summary_text(
        self,
        by_cat: Dict[str, List[str]],
        all_flagged: Set[str],
        health: Dict,
        legacy_breakdown: Dict,
    ) -> str:
        W = 68
        sep = "=" * W
        thin = "-" * W
        lines = [
            sep,
            " AEGF Dataset Audit — Quality Report",
            f" Generated : {self._ts} UTC",
            f" Input     : {self.input_path.name}",
            sep,
            "",
            f"  Total records checked  : {len(self.analyses):>7,}",
            f"  Total flagged records  : {len(all_flagged):>7,}",
            f"  Clean records          : {len(self.analyses) - len(all_flagged):>7,}",
            "",
            thin,
            " PROBLEM CATEGORY BREAKDOWN",
            thin,
        ]
        for cat, ids in by_cat.items():
            n = len(ids)
            label_ctr: Counter = Counter(
                a.gold_label for a in self.analyses if a.record_id in set(ids)
            )
            gi = label_ctr.get("gold injection", 0)
            gs = label_ctr.get("gold skiping",   0)
            lines.append(f"  {cat:<18} {n:>6,}   (gold injection: {gi:>5,} | gold skiping: {gs:>5,})")

        lines += [
            "",
            thin,
            " LEGACY BREAKDOWN BY EXAMPLE TYPE",
            thin,
        ]
        for et, sub in legacy_breakdown.get("by_example_type", {}).items():
            total_et = sum(sub.values())
            if total_et == 0:
                continue
            lines.append(f"  {et.upper()} ({total_et})")
            for k, v in sub.items():
                lines.append(f"    {k:<28} {v:>5,}")
        lines += [
            "",
            f"  Real problems (response-side)  : {legacy_breakdown.get('real_problem_total', '?'):>6,}",
            f"  User-only context (less severe): {legacy_breakdown.get('user_only_total', '?'):>6,}",
        ]

        if health:
            lines += [
                "",
                thin,
                f" FIVE-PILLAR HEALTH SCORE  (sample n={health.get('sample_size', '?')})",
                thin,
            ]
            for pillar, score in health.get("pillars", {}).items():
                lines.append(f"  {pillar:<32} {score:>5.2f} / 20.00")
            lines += [
                thin,
                f"  TOTAL HEALTH SCORE               {health.get('health_score', 0):>5.2f} / 100.00",
                f"  Critical records in sample       {len(health.get('critical_ids', [])):>6}",
            ]

        lines += ["", sep]
        return "\n".join(lines) + "\n"

    def _update_master_summary(
        self,
        by_cat: Dict[str, List[str]],
        all_flagged: Set[str],
        report_path: Path,
        summary_path: Path,
        health: Dict,
    ) -> None:
        master_path = self.report_dir / "problem_id_summary.json"
        if master_path.exists():
            try:
                master = json.loads(master_path.read_text(encoding="utf-8"))
            except Exception:
                master = {}
        else:
            master = {}

        master["__last_audit_utc"]       = self._ts
        master["__audit_tool"]           = "aegf_dataset_audit.py"
        master["input"]                  = str(self.input_path)
        master["total_records_checked"]  = len(self.analyses)
        master["total_flagged"]          = len(all_flagged)
        master["audit_report_file"]      = str(report_path.relative_to(self.report_dir.parent))
        master["audit_summary_file"]     = str(summary_path.relative_to(self.report_dir.parent))

        for cat, ids in by_cat.items():
            master[f"{cat}_count"] = len(ids)
            master[f"{cat}_file"]  = f"data/reports/{cat}_ids.txt"
            label_ctr = Counter(
                a.gold_label for a in self.analyses if a.record_id in set(ids)
            )
            master[f"{cat}_gold_injection_count"] = label_ctr.get("gold injection", 0)
            master[f"{cat}_gold_skiping_count"]   = label_ctr.get("gold skiping",   0)

        if health:
            master["health_score"]            = health.get("health_score")
            master["health_score_sample_size"] = health.get("sample_size")

        master_path.write_text(
            json.dumps(master, indent=2, ensure_ascii=False), encoding="utf-8"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 8.  DATASET CLEANER  (clean mode)
# ─────────────────────────────────────────────────────────────────────────────

class DatasetCleaner:
    """
    Reads an audit report to obtain the set of flagged record IDs, then
    streams the original JSONL and writes a *new* file that excludes those IDs.

    Rules:
      • The original dataset file is never modified.
      • A backup path is printed for reference (no copy is made — original is left intact).
      • The output file is written atomically (temp → rename).
    """

    def __init__(self, report_path: Path, input_path: Path, output_path: Path) -> None:
        self.report_path = report_path
        self.input_path  = input_path
        self.output_path = output_path

    def run(self) -> None:
        # Load flagged IDs from audit report
        report = json.loads(self.report_path.read_text(encoding="utf-8"))
        flagged: Set[str] = set()
        for ids_list in (report.get("flagged_ids") or {}).values():
            flagged.update(ids_list)

        if not flagged:
            print("[clean] No flagged IDs found in report. Nothing to filter.")
            return

        print(f"[clean] Loaded {len(flagged):,} flagged IDs from report.")
        print(f"[clean] Filtering '{self.input_path.name}' → '{self.output_path.name}'")
        print(f"[clean] Original file is NOT modified: {self.input_path}")

        kept = skipped = 0
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.output_path.with_suffix(".tmp")
        with self.input_path.open("r", encoding="utf-8") as fin, \
             tmp.open("w", encoding="utf-8") as fout:
            for raw in fin:
                raw_stripped = raw.strip()
                if not raw_stripped:
                    continue
                try:
                    rec = json.loads(raw_stripped)
                except json.JSONDecodeError:
                    kept += 1
                    fout.write(raw if raw.endswith("\n") else raw + "\n")
                    continue
                rid = rec.get("id") or ""
                if rid in flagged:
                    skipped += 1
                else:
                    kept += 1
                    fout.write(raw if raw.endswith("\n") else raw + "\n")

        tmp.replace(self.output_path)
        total = kept + skipped
        pct = round(skipped / total * 100, 1) if total else 0
        print(
            f"[clean] Done.  kept={kept:,}  removed={skipped:,}  "
            f"({pct}% of {total:,})  output={self.output_path}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 9.  CLI  (entry point)
# ─────────────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="aegf_dataset_audit.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Core I/O
    p.add_argument(
        "--input", required=True,
        help="Path to the JSONL dataset to audit.",
    )
    p.add_argument(
        "--output",
        help="Output JSONL path (required for --mode clean).",
    )
    p.add_argument(
        "--report-dir",
        default="data/reports",
        help="Directory where all report artefacts are written. Default: data/reports",
    )

    # Mode
    p.add_argument(
        "--mode",
        choices=["report", "clean"],
        default="report",
        help=(
            "report (default): audit the dataset; write reports. No data modified.\n"
            "clean: read existing audit report and write a filtered JSONL."
        ),
    )

    # Existing report (for clean mode)
    p.add_argument(
        "--audit-report",
        default=None,
        help=(
            "Path to an existing aegf_audit_report.json "
            "(required for --mode clean; defaults to <report-dir>/aegf_audit_report.json)."
        ),
    )

    # Health score
    p.add_argument(
        "--health-sample",
        type=int,
        default=0,
        help=(
            "Include a five-pillar health score computed on N randomly sampled "
            "records. 0 = disabled (default)."
        ),
    )
    p.add_argument(
        "--health-seed",
        type=int,
        default=42,
        help="Random seed for health-sample selection. Default: 42.",
    )

    return p


class AEGFAuditCLI:
    """Parse CLI args and dispatch to the appropriate mode."""

    def __init__(self) -> None:
        self.parser = _build_parser()

    def run(self, argv: Optional[List[str]] = None) -> int:  # noqa: C901
        args = self.parser.parse_args(argv)

        input_path  = Path(args.input)
        report_dir  = Path(args.report_dir)

        if not input_path.exists():
            print(f"[error] Input file not found: {input_path}", file=sys.stderr)
            return 2

        cfg = AuditConfig(
            health_sample_size = args.health_sample,
            health_sample_seed = args.health_seed,
        )

        # ── REPORT mode ───────────────────────────────────────────────────
        if args.mode == "report":
            print(f"[audit] Scanning dataset: {input_path}")
            auditor  = DatasetAuditor(cfg)
            analyses = auditor.run(input_path)
            print(f"[audit] Records read: {len(analyses):,}")

            report = AuditReport(
                analyses           = analyses,
                cfg                = cfg,
                input_path         = input_path,
                report_dir         = report_dir,
                health_sample_size = args.health_sample,
                health_sample_seed = args.health_seed,
            )
            report.write()
            return 0

        # ── CLEAN mode ────────────────────────────────────────────────────
        elif args.mode == "clean":
            if not args.output:
                print("[error] --output is required for --mode clean", file=sys.stderr)
                return 2

            audit_report_path = Path(args.audit_report) if args.audit_report else (
                report_dir / "aegf_audit_report.json"
            )
            if not audit_report_path.exists():
                print(
                    f"[error] Audit report not found: {audit_report_path}\n"
                    "Run --mode report first to generate it.",
                    file=sys.stderr,
                )
                return 2

            cleaner = DatasetCleaner(
                report_path = audit_report_path,
                input_path  = input_path,
                output_path = Path(args.output),
            )
            cleaner.run()
            return 0

        return 0  # unreachable


# ─────────────────────────────────────────────────────────────────────────────
# 10.  ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    raise SystemExit(AEGFAuditCLI().run())
