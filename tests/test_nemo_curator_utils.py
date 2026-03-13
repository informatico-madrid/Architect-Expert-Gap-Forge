#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for small utilities in curator submodules."""

from __future__ import annotations

from src.curation.curator_pipeline import CurationStats, ConversationExtractor
from src.curation.dedup_filter import exact_dedup
from src.curation.quality_filter import _count_code_tokens, _count_natural_tokens


def test_exact_dedup_removes_duplicates() -> None:
    rec = {"conversation": [{"role": "assistant", "content": "x"}]}
    records = [rec, rec]
    stats = CurationStats()
    kept = exact_dedup(records, stats)
    assert len(kept) == 1
    assert stats.exact_duplicates == 1


def test_conversation_extractor_and_token_counts() -> None:
    extractor = ConversationExtractor()
    conv = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "first reply"},
        {"role": "assistant", "content": "second reply"},
    ]
    assert extractor(conv) == "first reply second reply"

    text = '{"k":1}```python\nprint(1)\n``` some async def f(): pass'
    ct = _count_code_tokens(text)
    nt = _count_natural_tokens(text)
    assert ct > 0
    assert nt > 0
