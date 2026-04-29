#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Additional unit tests for curator submodules helpers.

Cover LDI, quality score, naive clustering fallback and I/O helpers.
"""

from __future__ import annotations


from src.curation.curator_pipeline import (
    CurationStats,
    load_jsonl,
    save_report,
    write_jsonl,
)
from src.curation.dedup_filter import (
    _char_shingles,
    _heuristic_quality_score,
    exact_dedup,
    semantic_dedup,
)
from src.curation.quality_filter import structural_quality_filter


def test_heuristic_quality_and_shingles():
    assert _heuristic_quality_score("") == 0.0
    s = "This is a unique and varied text with many tokens."
    q = _heuristic_quality_score(s)
    assert 0.0 <= q <= 1.0
    # Shingles
    sh = _char_shingles("abcdefg", k=3)
    assert isinstance(sh, set)
    assert any(len(item) >= 1 for item in sh)


def test_build_clusters_naive_and_semantic_dedup(tmp_path):
    stats = CurationStats()
    # Create three records where first two are similar and third is different
    r1 = {"assistant": "The quick brown fox jumps over the lazy dog."}
    r2 = {"assistant": "The quick brown fox jumps over the lazy dog."}
    r3 = {"assistant": "Completely different content unrelated to foxes."}
    records = [r1, r2, r3]
    # Use naive clustering which doesn't require datasketch
    out = semantic_dedup(records, stats, threshold=0.8, quality_cutoff=0.1)
    # Should keep at least one copy of the duplicate
    assert len(out) >= 2


def test_io_helpers(tmp_path):
    data = [{"id": "a"}, {"id": "b"}]
    out_file = tmp_path / "t.jsonl"
    n = write_jsonl(str(out_file), data)
    assert n == 2
    loaded = load_jsonl(str(out_file))
    assert len(loaded) == 2
    # Save report
    report = {"total_input": 10}
    rep_path = save_report(report, str(tmp_path / "reports"), "r.json")
    assert "r.json" in rep_path


def test_structural_quality_filter(tmp_path):
    # Valid record should pass
    rec1 = {
        "conversation": [
            {
                "role": "assistant",
                "content": "<think>"
                + "x" * 600
                + "</think><tool_call>code here</tool_call>",
            }
        ]
    }
    stats = CurationStats()
    out = structural_quality_filter([rec1], stats, min_think_chars=500, ldi_min_ratio=0)
    assert len(out) == 1

    # Invalid record (shallow thinking) should fail
    rec2 = {
        "conversation": [
            {
                "role": "assistant",
                "content": "<think>short</think><tool_call>c</tool_call>",
            }
        ]
    }
    stats2 = CurationStats()
    out2 = structural_quality_filter(
        [rec2], stats2, min_think_chars=500, ldi_min_ratio=0.1
    )
    assert len(out2) == 0
    assert stats2.shallow_thinking == 1


def test_exact_dedup(tmp_path):
    # Duplicate records
    rec = {"conversation": [{"role": "assistant", "content": "x"}]}
    stats = CurationStats()
    out = exact_dedup([rec.copy(), rec.copy()], stats)
    assert len(out) == 1
    assert stats.exact_duplicates == 1
