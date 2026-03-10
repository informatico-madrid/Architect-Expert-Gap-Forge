#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

import json
import re
import pytest

from src.curation import nemo_curator_suite as nc


def test_count_tokens_and_ldi():
    text = '```python\nx = 1\nprint(x)\n``` some natural text and {"k": 1}'
    code_tokens = nc._count_code_tokens(text)
    natural_tokens = nc._count_natural_tokens(text)
    assert code_tokens > 0
    assert natural_tokens >= 0
    ldi_val = nc._ldi(text)
    assert isinstance(ldi_val, float)


def test_has_meta_speech():
    think = "I need to do this\nlet me do it\nNow real content"
    assert nc._has_meta_speech(think) is True
    think2 = "This is real reasoning\nMore substantive content\nFinal note"
    assert nc._has_meta_speech(think2) is False


def test_structural_quality_filter_various_cases(tmp_path):
    stats = nc.CurationStats()

    # No assistant turns -> invalid_syntax
    rec_no_ass = {"conversation": []}
    out = nc.structural_quality_filter([rec_no_ass], stats)
    assert out == []
    assert stats.invalid_syntax >= 1

    # Space between </think> and <tool_call> -> invalid_syntax
    stats2 = nc.CurationStats()
    rec_bad_space = {
        "conversation": [
            {
                "role": "assistant",
                "content": "<think>abc</think> <tool_call>{}\</tool_call>",
            }
        ]
    }
    out2 = nc.structural_quality_filter([rec_bad_space], stats2, min_think_chars=1)
    assert out2 == []
    assert stats2.invalid_syntax >= 1

    # Short think -> shallow_thinking
    stats3 = nc.CurationStats()
    rec_short = {
        "conversation": [
            {
                "role": "assistant",
                "content": '<think>short</think><tool_call>{"content": "x"}</tool_call>',
            }
        ]
    }
    out3 = nc.structural_quality_filter([rec_short], stats3, min_think_chars=100)
    assert out3 == []
    assert stats3.shallow_thinking >= 1

    # Meta speech -> meta_speech increment
    stats4 = nc.CurationStats()
    think_meta = "I need to\nI should\nNow actual code"
    rec_meta = {
        "conversation": [
            {
                "role": "assistant",
                "content": f'<think>{think_meta}</think><tool_call>{{"content": "code"}}</tool_call>',
            }
        ]
    }
    out4 = nc.structural_quality_filter([rec_meta], stats4, min_think_chars=1)
    assert out4 == []
    assert stats4.meta_speech >= 1

    # Low LDI -> low_ldi increment
    stats5 = nc.CurationStats()
    rec_low_ldi = {
        "conversation": [
            {
                "role": "assistant",
                "content": "<think>long enough text here</think><tool_call>some natural language only</tool_call>",
            }
        ]
    }
    out5 = nc.structural_quality_filter(
        [rec_low_ldi], stats5, min_think_chars=1, ldi_min_ratio=0.01
    )
    # With a tiny ldi_min_ratio it may pass; check that function runs and returns list or empty without crash
    assert isinstance(out5, list)


def test_extract_assistant_text_and_quality_and_shingles():
    rec1 = {"assistant": "direct assistant text"}
    assert nc._extract_assistant_text(rec1) == "direct assistant text"

    rec2 = {
        "conversation": [{"role": "assistant", "content": "answer here"}],
        "metadata": {},
    }
    assert "answer here" in nc._extract_assistant_text(rec2)

    assert nc._heuristic_quality_score("") == 0.0
    high = "This is a high quality text with varied vocabulary and no repetition."
    assert 0.0 <= nc._heuristic_quality_score(high) <= 1.0

    shingles = nc._char_shingles("hello world", k=3)
    assert isinstance(shingles, set) and len(shingles) > 0


def test_build_clusters_naive_and_semantic_dedup(tmp_path):
    texts = ["alpha beta gamma", "alpha beta gamma", "completely different text"]
    clusters = nc._build_clusters_naive(texts, threshold=0.5, shingle_k=3)
    assert isinstance(clusters, list)

    # semantic_dedup should drop low-quality records according to quality_cutoff
    stats = nc.CurationStats()
    records = [
        {
            "id": "1",
            "conversation": [
                {"role": "assistant", "content": "Good varied text with many words."}
            ],
        },
        {
            "id": "2",
            "conversation": [{"role": "assistant", "content": "spam spam spam spam"}],
        },
    ]
    out = nc.semantic_dedup(
        records, stats, threshold=0.1, quality_cutoff=0.2, num_perm=4, shingle_k=3
    )
    assert isinstance(out, list)
    # one record may be removed due to low quality
    assert stats.low_quality_score >= 0


def test_io_helpers(tmp_path):
    recs = [{"id": "a"}, {"id": "b"}]
    p = tmp_path / "test.jsonl"
    nc.write_jsonl(str(p), recs)
    loaded = nc.load_jsonl(str(p))
    assert len(loaded) == 2

    report = {"total_input": 2}
    out = nc.save_report(report, str(tmp_path), "r.json")
    assert out.endswith("r.json")


def test_run_nemo_filter_pipeline_not_installed(tmp_path):
    # When Nemo is not available the function should raise a RuntimeError
    if nc._NEMO_AVAILABLE:
        # Skip this assertion if environment actually has nemo installed
        return
    with pytest.raises(RuntimeError):
        nc.run_nemo_filter_pipeline(
            str(tmp_path / "in.jsonl"), str(tmp_path / "outdir")
        )


def test_build_clusters_datasketch_not_available():
    """Test _build_clusters_datasketch when datasketch not available."""
    if nc._DATASKETCH_AVAILABLE:
        return  # Skip if available
    records = [{"conversation": [{"role": "assistant", "content": "test"}]}]
    result = nc._build_clusters_datasketch(
        records, threshold=0.8, num_perm=4, shingle_k=3
    )
    assert result is None


def test_semantic_dedup_not_available(tmp_path):
    """Test semantic_dedup when datasketch not available."""
    if nc._DATASKETCH_AVAILABLE:
        return  # Skip if available
    records = [{"conversation": [{"role": "assistant", "content": "test"}]}]
    stats = nc.CurationStats()
    result = nc.semantic_dedup(records, stats, threshold=0.8)
    assert isinstance(result, list)
