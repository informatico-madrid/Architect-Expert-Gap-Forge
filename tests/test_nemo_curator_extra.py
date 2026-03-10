#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Additional unit tests for `nemo_curator_suite` helpers.

Cover LDI, quality score, naive clustering fallback and I/O helpers.
"""

from __future__ import annotations

import os
from pathlib import Path
import json

import pytest

from src.curation import nemo_curator_suite as nc


def test_heuristic_quality_and_shingles():
    assert nc._heuristic_quality_score("") == 0.0
    s = "This is a unique and varied text with many tokens."
    q = nc._heuristic_quality_score(s)
    assert 0.0 <= q <= 1.0
    # Shingles
    sh = nc._char_shingles("abcdefg", k=3)
    assert isinstance(sh, set)
    assert any(len(item) >= 1 for item in sh)


def test_build_clusters_naive_and_semantic_dedup(tmp_path):
    stats = nc.CurationStats()
    # Create three records where first two are similar and third is different
    r1 = {"assistant": "The quick brown fox jumps over the lazy dog."}
    r2 = {"assistant": "The quick brown fox jumps over the lazy dog."}
    r3 = {"assistant": "Completely different content unrelated to foxes."}
    records = [r1, r2, r3]

    # Run semantic_dedup with low quality cutoff so all are candidates
    out = nc.semantic_dedup(
        records, stats, threshold=0.5, quality_cutoff=0.0, num_perm=1, shingle_k=3
    )
    # Expect at least two outputs (cluster keeps one of similar pair)
    assert isinstance(out, list)
    assert len(out) >= 2
    for item in out:
        assert "metadata" in item and "curation" in item["metadata"]


def test_load_and_write_jsonl_and_save_report(tmp_path):
    data = [{"a": 1}, {"b": 2}]
    out_file = tmp_path / "data.jsonl"
    n = nc.write_jsonl(str(out_file), data)
    assert n == 2
    loaded = nc.load_jsonl(str(out_file))
    assert isinstance(loaded, list) and len(loaded) == 2

    report = {"total_input": 2}
    rep_path = nc.save_report(report, str(tmp_path / "reports"), "r.json")
    assert os.path.exists(rep_path)


def test_structural_quality_filter_various_cases():
    stats = nc.CurationStats()
    # Case: empty conversation -> invalid syntax
    rec1 = {"conversation": []}
    out = nc.structural_quality_filter([rec1], stats)
    assert out == []
    assert stats.invalid_syntax >= 1

    # Case: short think -> shallow_thinking
    think = "<think>short</think><tool_call>code()</tool_call>"
    rec2 = {"conversation": [{"role": "assistant", "content": think}]}
    stats2 = nc.CurationStats()
    out2 = nc.structural_quality_filter(
        [rec2], stats2, min_think_chars=10, ldi_min_ratio=0.01
    )
    assert out2 == []
    assert stats2.shallow_thinking >= 1

    # Case: passing record
    long_think = (
        "<think>"
        + ("explain " * 50)
        + "</think><tool_call>def x():\n    return 1\n</tool_call>"
    )
    rec3 = {"conversation": [{"role": "assistant", "content": long_think}]}
    stats3 = nc.CurationStats()
    out3 = nc.structural_quality_filter(
        [rec3], stats3, min_think_chars=10, ldi_min_ratio=0.0
    )
    assert len(out3) == 1
