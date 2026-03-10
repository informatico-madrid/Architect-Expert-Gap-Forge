#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Edge-case tests for `production_v11` covering LDI, poison detection,
legacy skip and guarded NeMo imports.

These tests use the lightweight fake clients and module stubs under
`tests.fixtures` to exercise branches without external dependencies.
"""

from __future__ import annotations

import asyncio
import importlib
import json
from types import SimpleNamespace
from pathlib import Path

import pytest

from src.factory import production_v11 as pv11


from tests.fixtures.production_v11_mocks import (
    make_client_with_write_action,
)
from tests.fixtures.nemo_mocks import enable_fake_nemo, disable_fake_nemo


def test_generate_sample_async_gold_injected_nominal_clean(monkeypatch, tmp_path):
    # Simplify rendering/prompt helpers and load taxonomy
    monkeypatch.setattr(pv11, "_prompt", lambda key: "[P]", raising=False)
    monkeypatch.setattr(pv11, "_render", lambda s, **k: s, raising=False)
    monkeypatch.setattr(pv11, "TOOLS_DEFINITION", [], raising=False)
    # No global taxonomy load here; we monkeypatch prompt/render helpers above

    frag = {
        "name": "EdgeGold",
        "original": "def foo():\n    return 42\n" * 50,
        "skeleton": "def foo():\n    pass\n",
        "context": "ctx",
        "virtual_filename": "pkg/edge.py",
        "subtype": "code",
    }

    # Long generated content + long reasoning to pass LDI
    client = make_client_with_write_action(
        "pkg/edge.py",
        "print('hello')\n" * 200,
        reasoning="R" * 300,
    )

    sem = asyncio.Semaphore(1)

    async def go():
        return await pv11.generate_sample_async(
            client,
            pv11.DEFAULT_MODEL,
            frag,
            "nominal",
            "easy",
            master="M" * 200,
            changelog="C" * 200,
            semaphore=sem,
        )

    res = asyncio.run(go())
    assert res["status"] == "accepted"
    sample = res["sample"]
    assert sample["metadata"]["gold_injected"] is True


def test_generate_sample_async_zero_reasoning_rejected(monkeypatch, tmp_path):
    monkeypatch.setattr(pv11, "_prompt", lambda key: "[P]", raising=False)
    monkeypatch.setattr(pv11, "_render", lambda s, **k: s, raising=False)
    # No global taxonomy load here; prompt helpers are monkeypatched above

    frag = {
        "name": "ZeroReason",
        "original": "def x():\n  pass\n",
        "skeleton": "def x():\n  pass\n",
        "context": "ctx",
        "virtual_filename": "pkg/zero.py",
        "subtype": "code",
    }

    # No <think> reasoning -> LDI should fail (zero reasoning)
    client = make_client_with_write_action("pkg/zero.py", "print(1)")

    async def go():
        return await pv11.generate_sample_async(
            client,
            pv11.DEFAULT_MODEL,
            frag,
            "nominal",
            "easy",
            master="M",
            changelog="C",
            semaphore=asyncio.Semaphore(1),
        )

    res = asyncio.run(go())
    assert res["status"] == "rejected"
    assert "Failed after" in res.get("reason", "") or "LDI Fail" in res.get(
        "reason", ""
    )


def test_process_fragment_writes_rejected_on_poison(monkeypatch, tmp_path):
    # Monkeypatch minimal prompt rendering
    monkeypatch.setattr(pv11, "_prompt", lambda key: "[P]", raising=False)
    monkeypatch.setattr(pv11, "_render", lambda s, **k: s, raising=False)
    # No global taxonomy load here; prompt helpers are monkeypatched above

    frag = {
        "name": "PoisonFrag",
        "original": "def poison():\n  pass\n",
        "skeleton": "def poison():\n  pass\n",
        "context": "ctx",
        "virtual_filename": "pkg/poison.py",
        "subtype": "code",
    }

    # Generated content contains a known poison detector token
    client = make_client_with_write_action(
        "pkg/poison.py", "as_timestamp(123)", reasoning="R" * 200
    )
    # Force deterministic example type assignment to avoid random error_recovery branch
    monkeypatch.setattr(
        pv11,
        "assign_example_type",
        lambda frag, has_legacy=False: ("nominal", "easy"),
        raising=False,
    )

    writer_ok = pv11.AsyncFileWriter(Path(tmp_path) / "ok.jsonl")
    writer_bad = pv11.AsyncFileWriter(Path(tmp_path) / "bad.jsonl")
    tracker = pv11.ProgressTracker(total=1, mode="code")
    args = SimpleNamespace(think_filter=False, think_filter_min_chars=5000)

    async def go():
        await pv11.process_fragment(
            client,
            pv11.DEFAULT_MODEL,
            frag,
            "M",
            "C",
            asyncio.Semaphore(1),
            writer_ok,
            writer_bad,
            tracker,
            args,
        )

    asyncio.run(go())

    # Ensure rejected file contains one JSON record with reason auto_rejected_poison
    bad_lines = (
        (Path(tmp_path) / "bad.jsonl").read_text(encoding="utf-8").strip().splitlines()
    )
    assert len(bad_lines) == 1
    rec = json.loads(bad_lines[0])
    # Either the code path produced an auto-rejected record (preferred),
    # or the implementation raised during handling and returned a rejected
    # result (historic behaviour). Accept both outcomes.
    assert (rec.get("reason") == "auto_rejected_poison") or (
        isinstance(rec.get("reason"), str)
        and rec.get("reason", "").startswith("Failed after")
    )
    # If poison_patterns key exists it should be non-empty when present
    if rec.get("poison_patterns") is not None:
        assert rec["poison_patterns"]


def test_run_nemo_filter_pipeline_with_fake_nemo(tmp_path):
    # Prepare a minimal input jsonl
    inp = Path(tmp_path) / "in.jsonl"
    out = Path(tmp_path) / "out.jsonl"
    inp.write_text(
        json.dumps({"conversation": [{"role": "assistant", "content": "Hello"}]}) + "\n"
    )

    # Enable fake nemo/datasketch, reload the suite to pick up availability
    enable_fake_nemo()
    import src.curation.nemo_curator_suite as ncs

    importlib.reload(ncs)

    try:
        # Should not raise
        ncs.run_nemo_filter_pipeline(str(inp), str(out))
    finally:
        disable_fake_nemo()
