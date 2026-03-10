#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Small end-to-end smoke test for `production_v11.main_async`.

This test creates a minimal raw .txt bundle, stubs prompt rendering
and the AsyncOpenAI client, and runs `main_async` with a single
worker/test fragment to exercise the main two-pass pipeline.
"""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from pathlib import Path
import textwrap

import pytest

from src.factory import production_v11 as pv11


class FakeCompletions:
    def __init__(self, content: str):
        self._content = content

    async def create(self, *args, **kwargs):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self._content))]
        )


def make_fake_client_factory(content: str):
    class FakeClient:
        def __init__(self, *args, **kwargs):
            self.chat = SimpleNamespace(completions=FakeCompletions(content))

    return FakeClient


def test_main_async_minimal(tmp_path, monkeypatch):
    # Prepare minimal gap docs
    gap = tmp_path / "gap"
    gap.mkdir()
    (gap / pv11._MASTER_GUIDE_FILENAME).write_text(
        "# Master guide\nSome master content"
    )
    (gap / pv11._TECHNICAL_CHANGELOG_FILENAME).write_text(
        "# Changelog\nLots of changes"
    )
    (gap / pv11._JINJA_YAML_GUIDE_FILENAME).write_text("# Jinja Guide\nTemplate rules")

    # Prepare a raw .txt bundle (FUNCTIONAL_UNIT)
    raw = tmp_path / "raw"
    raw.mkdir()
    bundle = textwrap.dedent("""
        === LOGICAL ENTITY: sample_entity ===
        Context: Sample context
        Type: FUNCTIONAL_UNIT
        [ARCH_HEADER]
        MODULE: sample_module
        REPO_PREFIX: sample_repo
        LOCAL_IMPORTS: []

        --- FILE: module.py ---
        def foo():
            return 42

        --- FILE: test_module.py ---
        def test_foo():
            assert foo() == 42
    """)
    (raw / "bundle1.txt").write_text(bundle)

    # Stub prompt/template functions to avoid taxonomy dependency
    monkeypatch.setattr(pv11, "_prompt", lambda key: f"<{key}>")
    monkeypatch.setattr(
        pv11,
        "_render",
        lambda template, **subs: (
            template
            if not subs
            else template + " " + " ".join(f"{k}={v}" for k, v in subs.items())
        ),
    )
    monkeypatch.setattr(pv11, "TOOLS_DEFINITION", [{"name": "tool"}], raising=False)

    # Deterministic assignment of example type
    monkeypatch.setattr(
        pv11, "assign_example_type", lambda frag, has_legacy=False: ("nominal", "easy")
    )

    # Fake client returns a long reasoning and write_action with content
    reasoning = "R" * 300
    generated_code = "def foo():\n    return 42\n"
    content = f"<think>{reasoning}</think><write_action><path>module.py</path><content>{generated_code}</content></write_action>"
    FakeClient = make_fake_client_factory(content)
    monkeypatch.setattr(pv11, "AsyncOpenAI", FakeClient)

    # Ensure think_filter is disabled during test
    monkeypatch.setattr(pv11, "_think_filter_apply", None, raising=False)

    # Build args namespace for main_async
    class Args:
        test = 1
        limit = None
        workers = 1
        model = "m"
        base_url = "http://x"
        api_key = "k"
        output = str(tmp_path / "out.jsonl")
        seed = 42
        think_filter = False
        think_filter_min_chars = 5000
        resume = None
        raw_dir = str(raw)
        extensions = None
        _gap_dir = gap
        theory = False
        theory_reps = 3

    # Run main_async
    asyncio.run(pv11.main_async(Args()))

    # Validate output exists and contains JSON lines
    outp = Path(Args.output)
    assert outp.exists()
    lines = outp.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 1
    rec = json.loads(lines[0])
    assert rec.get("metadata") and rec["metadata"].get("checkpoint_key")
