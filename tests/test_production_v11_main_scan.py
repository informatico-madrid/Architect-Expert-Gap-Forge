#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Integration-style test for `main_async` pass1/pass2 scanning and task launch.

This test constructs a temporary raw_dir with a MODULE_BLUEPRINT, GOVERNANCE_RULES
and a FUNCTIONAL_UNIT bundle, then monkeypatches `process_fragment` to a lightweight
coroutine to exercise the two-pass cache and tasks creation without performing
real generation.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from pathlib import Path

import pytest

from src.factory.checkpoint import make_checkpoint_key
from src.factory.pipeline_runner import main_async


def _write_bundle(path: Path, content: str) -> None:
    path.write_text(content)


def test_main_async_two_pass_scan(tmp_path, monkeypatch, gap_dir):
    # Prepare raw_dir with three .txt bundles
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()

    # MODULE_BLUEPRINT
    bp = (
        "=== LOGICAL ENTITY: mod1_blueprint ===\n"
        "Type: MODULE_BLUEPRINT\n"
        "[MODULE_MAP]\nMODULE: mod1\n--- FILE: blueprint.txt ---\nBLUEPRINT"
    )
    _write_bundle(raw_dir / "bp.txt", bp)

    # GOVERNANCE_RULES
    gov = (
        "=== LOGICAL ENTITY: repo1_governance ===\n"
        "Type: GOVERNANCE_RULES\n"
        "[GOVERNANCE_HEADER]\nREPO_PREFIX: repo1\n--- FILE: gov.md ---\nRULES"
    )
    _write_bundle(raw_dir / "gov.txt", gov)

    # FUNCTIONAL_UNIT with a simple function + test
    fu = (
        "=== LOGICAL ENTITY: entity_fu ===\n"
        "Context: Some context\n"
        "Type: FUNCTIONAL_UNIT\n"
        "[ARCH_HEADER]\nMODULE: mod1\nREPO_PREFIX: repo1\n--- FILE: module.py ---\n"
        "def foo():\n    return 1\n--- FILE: test_module.py ---\n"
        "def test_foo():\n    assert foo()==1\n"
    )
    _write_bundle(raw_dir / "fu.txt", fu)

    # Create minimal gap docs for load_master_docs
    (tmp_path / "HA_MASTER_GUIDE_2026.md").write_text("# Guide\n" + "A" * 200)
    (tmp_path / "technical_changelog_2026.md").write_text("# Changelog\n" + "B" * 200)
    (tmp_path / "HA_JINJA_YAML_GUIDE_2026.md").write_text("# Jinja\n" + "C" * 200)

    # Monkeypatch process_fragment to a no-op that records calls
    calls = []

    async def fake_process_fragment(
        client,
        model,
        frag,
        master,
        changelog,
        semaphore,
        writer_ok,
        writer_bad,
        tracker,
        args,
        jinja_guide="",
        state=None,
    ):
        calls.append(frag.get("name"))
        # simulate writing accepted sample
        await writer_ok.write(
            {
                "id": f"fake_{frag.get('name')}",
                "metadata": {
                    "checkpoint_key": make_checkpoint_key(
                        frag.get("name"), frag.get("virtual_filename")
                    )
                },
            }
        )
        await tracker.record(
            "accepted", "nominal", "easy", gold_injected=True, has_legacy=False
        )

    monkeypatch.setattr(
        "src.factory.pipeline_runner.process_fragment", fake_process_fragment
    )

    # Prevent real AsyncOpenAI instantiation side-effects
    monkeypatch.setattr(
        "src.factory.pipeline_runner.AsyncOpenAI", lambda *a, **k: None, raising=False
    )

    args = SimpleNamespace(
        _gap_dir=tmp_path,
        raw_dir=str(raw_dir),
        workers=2,
        model="m",
        base_url="u",
        api_key="k",
        test=10,
        limit=None,
        extensions=None,
        resume=None,
        output=str(tmp_path / "out.jsonl"),
        seed=42,
        think_filter=False,
        think_filter_min_chars=5000,
        theory=False,
    )

    asyncio.run(main_async(args))

    # Ensure we called process_fragment for at least one fragment
    assert calls
