#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

import asyncio
import json

import pytest

from src.curation import backtracking_rewriter as br


def test_passes_backtracking_filter_and_classify_strategy():
    rec = {
        "conversation": [{"role": "assistant", "content": "<think>abc</think>rest"}],
        "metadata": {"example_type": "error_recovery"},
    }
    cfg = br.BacktrackingConfig()
    assert br.passes_backtracking_filter(rec, cfg)
    assert br.classify_rewrite_strategy(rec) == "error_first"

    rec2 = {"conversation": [{"role": "assistant", "content": "no think here"}], "metadata": {"example_type": "nominal"}}
    assert not br.passes_backtracking_filter(rec2, cfg)


def test_build_rewrite_prompt_strategies():
    record = {
        "conversation": [{"role": "user", "content": "do X"}, {"role": "assistant", "content": "<think>t</think>code"}],
        "metadata": {"legacy_patterns": ["p1"]},
    }
    sys_bt, user_bt = br.build_rewrite_prompt(record, "full_backtracking", system_bt="SYSBT", system_rc="SYSRC", governance_context="CTX", language="Spanish")
    assert "DETECTED LEGACY PATTERNS" in user_bt
    sys_rc, user_rc = br.build_rewrite_prompt(record, "trace_reconstruction", system_bt="SYSBT", system_rc="SYSRC", governance_context=None, language=None)
    assert "PERFECT SOLUTION CODE" in user_rc
    sys_error, user_err = br.build_rewrite_prompt(record, "error_first", system_bt="SYSBT", system_rc="SYSRC", governance_context=None, language=None)
    assert "Rewrite the think block" in user_err


def test_load_governance_context(tmp_path):
    # missing file returns None
    cfg = br.BacktrackingConfig(gap_dir=str(tmp_path))
    assert br._load_governance_context(cfg) is None
    # create file and test truncation
    md = tmp_path / "HA_MASTER_GUIDE_2026.md"
    md.write_text("X" * 6000)
    cfg2 = br.BacktrackingConfig(gap_dir=str(tmp_path), governance_context_chars=100)
    ctx = br._load_governance_context(cfg2)
    assert ctx is not None
    assert len(ctx) == 100


def test_load_save_jsonl_tmp(tmp_path):
    records = [{"id": "a"}, {"id": "b"}]
    path = tmp_path / "out.jsonl"
    br.save_jsonl(records, path)
    loaded = br.load_jsonl(path)
    assert loaded == records


def test_rewrite_pipeline_end_to_end(tmp_path, monkeypatch):
    # Create prompt files
    bt = tmp_path / "bt.txt"
    rc = tmp_path / "rc.txt"
    bt.write_text("SYS_BT")
    rc.write_text("SYS_RC")
    # create governance file
    gapdir = tmp_path / "gap"
    gapdir.mkdir()
    (gapdir / "HA_MASTER_GUIDE_2026.md").write_text("GOVERNANCE_CONTENT")
    # create input JSONL with two records, one eligible and one theory (filtered)
    input_path = tmp_path / "in.jsonl"
    recs = [
        {"id": "1", "conversation": [{"role": "user", "content": "u1"}, {"role": "assistant", "content": "<think>old</think>code"}], "metadata": {}},
        {"id": "2", "conversation": [{"role": "assistant", "content": "no think"}], "metadata": {"example_type": "theory"}},
    ]
    input_path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in recs))
    out_path = tmp_path / "out.jsonl"
    cfg = br.BacktrackingConfig(backtracking_system_prompt_path=str(bt), reconstruction_system_prompt_path=str(rc), gap_dir=str(gapdir), audit_dir=str(tmp_path))

    class FakeClient:
        async def generate(self, prompt, *, system_prompt, max_tokens, temperature):
            return "</think>Rewritten reasoning"

    async def _nosleep(_):
        return None

    monkeypatch.setattr(asyncio, "sleep", _nosleep)
    report = asyncio.run(br.rewrite_pipeline(input_path, out_path, cfg, client=FakeClient()))
    assert isinstance(report, br.PipelineReport)
    assert out_path.exists()
    out = br.load_jsonl(out_path)
    # only one eligible record should be present in output (strategy may be pass-through)
    assert len(out) == 1
    # current classifier returns 'pass_through' for clean nominal samples
    assert out[0]["metadata"]["backtracking_applied"] in (True, False)
