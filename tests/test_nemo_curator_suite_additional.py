#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""Additional unit coverage for the NeMo curator helpers."""

from __future__ import annotations

import copy
import json
from pathlib import Path


from src.curation.curator_pipeline import (
    CurationStats,
    load_jsonl,
    save_report,
    write_jsonl,
)
from src.curation.dedup_filter import (
    _build_clusters_naive,
    _char_shingles,
    _extract_assistant_text,
    _heuristic_quality_score,
    exact_dedup,
    semantic_dedup,
)
from src.curation.quality_filter import (
    _count_code_tokens,
    _count_natural_tokens,
    _has_meta_speech,
    _ldi,
    structural_quality_filter,
)


RECORD_BASE = {
    "conversation": [
        {
            "role": "assistant",
            "content": '<think>Detailed reasoning about the problem.</think><tool_call>{"name": "alpha"}</tool_call>',
        }
    ]
}


def test_exact_dedup_tracks_duplicates() -> None:
    stats = CurationStats()
    record = {"conversation": [{"role": "assistant", "content": "answer"}]}
    kept = exact_dedup([copy.deepcopy(record), copy.deepcopy(record)], stats)
    assert len(kept) == 1
    assert stats.exact_duplicates == 1


def test_structural_quality_filter_detects_meta_speech() -> None:
    stats = CurationStats()
    content = '<think>Let me explain it first. I need to check carefully.</think><tool_call>{"name": "beta"}</tool_call>'
    record = {"conversation": [{"role": "assistant", "content": content}]}
    kept = structural_quality_filter(
        [record], stats, min_think_chars=1, ldi_min_ratio=0
    )
    assert not kept
    assert stats.meta_speech == 1


def test_structural_quality_filter_allows_valid_records() -> None:
    stats = CurationStats()
    content = (
        "<think>"
        + "Reasonable reasoning. " * 10
        + '</think><tool_call>{"name": "gamma"}</tool_call>'
    )
    record = {"conversation": [{"role": "assistant", "content": content}]}
    kept = structural_quality_filter(
        [record], stats, min_think_chars=5, ldi_min_ratio=0
    )
    assert kept
    assert stats.invalid_syntax == 0


def test_code_token_counter_includes_code() -> None:
    base = "plain text"
    code_text = base + " ```print('hi')``` {\"key\": 1}"
    assert _count_code_tokens(code_text) > _count_code_tokens(base)


def test_natural_token_counter_ignores_stop_words() -> None:
    stop_text = "async await def import return"
    assert _count_natural_tokens(stop_text) == 0
    natural_text = "architecture reasoning detailed"
    assert _count_natural_tokens(natural_text) > 0


def test_ldi_returns_zero_without_code_and_positive_with_code() -> None:
    assert _ldi("just text without braces") == 0.0
    assert _ldi('{"key": 1} def func()') > 0.0


def test_has_meta_speech_flagged_and_cleared() -> None:
    assert _has_meta_speech("let me write it down. i need to act now.")
    assert not _has_meta_speech("the reasoning is deep and novel")


def test_extract_assistant_text_variations() -> None:
    assert _extract_assistant_text({"assistant": "direct"}) == "direct"
    assert (
        _extract_assistant_text(
            {"conversation": [{"role": "assistant", "content": "dialog"}]}
        )
        == "dialog"
    )
    assert _extract_assistant_text({"thought_extracted": "thought"}) == "thought"
    assert _extract_assistant_text({}) == ""


def test_heuristic_quality_score_penalizes_repetition() -> None:
    repeated = "Repeat sentence. Repeat sentence. Repeat sentence."
    assert 0.0 <= _heuristic_quality_score(repeated) < 0.6


def test_char_shingles_returns_normalised_short_string() -> None:
    assert _char_shingles("Hi", k=5) == {"hi"}
    shingles = _char_shingles("alpha beta", k=3)
    assert any("_" in entry for entry in shingles)


def test_build_clusters_naive_groups_duplicates() -> None:
    texts = ["alpha beta", "alpha beta", "gamma delta"]
    clusters = _build_clusters_naive(texts, threshold=0.3, shingle_k=2)
    assert any(len(group) >= 2 for group in clusters)


def test_semantic_dedup_drops_similar_records(monkeypatch) -> None:
    monkeypatch.setattr("src.curation.curator_pipeline._DATASKETCH_AVAILABLE", False)
    stats = CurationStats()
    base = {"assistant": "Unique high quality reasoning."}
    dupe = {"assistant": "Unique high quality reasoning."}
    other = {"assistant": "Different text."}
    result = semantic_dedup(
        [base, dupe, other],
        stats,
        threshold=0.3,
        quality_cutoff=0.0,
        num_perm=2,
        shingle_k=2,
    )
    assert len(result) == 2
    assert stats.semantic_duplicates == 1
    assert all(r.get("metadata", {}).get("curation", {}).get("kept") for r in result)


def test_jsonl_io_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "sample.jsonl"
    records = [copy.deepcopy(RECORD_BASE), {"assistant": "second"}]
    wrote = write_jsonl(str(path), records)
    assert wrote == 2
    loaded = load_jsonl(str(path))
    assert len(loaded) == 2


def test_save_report_writes_file(tmp_path: Path) -> None:
    report = CurationStats().as_dict()
    out = save_report(report, str(tmp_path), "report.json")
    assert Path(out).is_file()
    with open(out, "r", encoding="utf-8") as fh:
        assert json.load(fh)["total_input"] == report["total_input"]
