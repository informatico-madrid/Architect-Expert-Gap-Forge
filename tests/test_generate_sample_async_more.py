#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Tests for async generation flows in `production_v11`.

These tests mock the minimal AsyncOpenAI client surface to exercise
`generate_sample_async` branches without external network calls.
"""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest

from src.factory import prompt_builder as pb_module
from src.factory.pipeline_runner import generate_sample_async, process_fragment


@pytest.fixture(autouse=True)
def stub_templates(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub prompt rendering and prompt lookup to avoid loading taxonomy files.

    Uses `monkeypatch` so modifications are reverted after each test module.
    """

    monkeypatch.setattr(pb_module, "_prompt", lambda key: f"<{key}>")
    monkeypatch.setattr(
        pb_module,
        "_render",
        lambda template, **subs: (
            template
            if not subs
            else template + " " + " ".join(f"{k}={v}" for k, v in subs.items())
        ),
    )
    monkeypatch.setattr(
        pb_module, "TOOLS_DEFINITION", [{"name": "tool"}], raising=False
    )
    monkeypatch.setattr(
        pb_module, "LEGACY_2023_PATTERNS", [{"legacy_code": "old_code"}], raising=False
    )
    monkeypatch.setattr(
        pb_module,
        "JINJA_LEGACY_2023_PATTERNS",
        [{"legacy_code": "old_template", "context_type": "jinja"}],
        raising=False,
    )


class FakeCompletions:
    def __init__(self, content: str):
        self._content = content

    async def create(self, *args, **kwargs):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self._content))]
        )


class FakeClient:
    def __init__(self, content: str):
        self.chat = SimpleNamespace(completions=FakeCompletions(content))


def make_frag(functional: bool = True) -> dict:
    return {
        "name": "fragX",
        "virtual_filename": "mod_frag.py",
        "original": "# original code",
        "context": "Some context for the fragment",
        "skeleton": "def stub(): pass",
        "test_original": "# test code",
        "test_filename": "tests/mod_frag_test.py",
        "subtype": "functional_unit" if functional else "code",
    }


def test_generate_sample_async_gold_injection():
    # Clean assistant output (no poison patterns) -> gold injection should occur
    tool_json = {
        "name": "write_to_file",
        "arguments": {"path": "mod_frag.py", "content": "generated_code"},
    }
    content = f"<think>reason</think><tool_call>{json.dumps(tool_json)}</tool_call>"
    client = FakeClient(content)

    frag = make_frag(functional=True)
    sem = asyncio.Semaphore(1)
    res = asyncio.run(
        generate_sample_async(
            client,
            "m",
            frag,
            "nominal",
            "easy",
            "master",
            "changelog",
            sem,
            has_legacy=False,
        )
    )

    assert res["status"] == "accepted"
    sample = res["sample"]
    assert sample["metadata"]["gold_injected"] is True
    assert "tool_call" in sample["conversation"][1]["content"]


def test_generate_sample_async_legacy_skip():
    # When has_legacy=True the gold injection is skipped and model output is preserved
    tool_json = {
        "name": "write_to_file",
        "arguments": {"path": "mod_frag.py", "content": "generated_code"},
    }
    content = f"<think>r</think><tool_call>{json.dumps(tool_json)}</tool_call>"
    client = FakeClient(content)
    frag = make_frag(functional=False)
    sem = asyncio.Semaphore(1)
    res = asyncio.run(
        generate_sample_async(
            client,
            "m",
            frag,
            "contrast",
            None,
            "master",
            "changelog",
            sem,
            has_legacy=True,
            legacy_patterns=["pat"],
        )
    )

    assert res["status"] == "accepted"
    sample = res["sample"]
    assert sample["metadata"]["gold_injected"] is False
    assert sample["metadata"]["legacy_detected"] is True


def test_generate_sample_async_ldi_fail_returns_rejected():
    # No <think> => reasoning length 0 -> LDI fail -> rejected after retries
    tool_json = {
        "name": "write_to_file",
        "arguments": {"path": "x.py", "content": "small"},
    }
    content = f"<tool_call>{json.dumps(tool_json)}</tool_call>"
    client = FakeClient(content)
    frag = make_frag(functional=False)
    sem = asyncio.Semaphore(1)
    res = asyncio.run(
        generate_sample_async(
            client,
            "m",
            frag,
            "nominal",
            "easy",
            "master",
            "changelog",
            sem,
            has_legacy=False,
        )
    )

    assert res["status"] == "rejected"


def test_process_fragment_integration_monkeypatched(monkeypatch):
    # Monkeypatch generate_sample_async to return an accepted sample
    sample = {
        "status": "accepted",
        "sample": {
            "id": "v11_nominal_abc",
            "conversation": [
                {"role": "user", "content": "u"},
                {
                    "role": "assistant",
                    "content": "<think>r</think><tool_call>[]</tool_call>",
                },
            ],
            "metadata": {
                "curation": {"kept": True},
                "checkpoint_key": "abc",
                "example_type": "nominal",
                "evol_difficulty": "easy",
                "gold_injected": True,
            },
            "filter_text": "f",
        },
    }

    async def fake_generate(*args, **kwargs):
        return sample

    monkeypatch.setattr(
        "src.factory.pipeline_runner.generate_sample_async", fake_generate
    )
    monkeypatch.setattr(
        "src.factory.ldi_validator.assign_example_type",
        lambda frag, has_legacy=False: ("nominal", "easy"),
    )

    class DummyWriter:
        def __init__(self):
            self.records = []

        async def write(self, record):
            self.records.append(record)

    class DummyTracker:
        def __init__(self):
            self.calls = []

        async def record(
            self, status, example_type, difficulty, gold_injected=True, has_legacy=False
        ):
            self.calls.append(
                (status, example_type, difficulty, gold_injected, has_legacy)
            )

    writer_ok = DummyWriter()
    writer_bad = DummyWriter()
    tracker = DummyTracker()

    frag = {
        "name": "testfrag",
        "virtual_filename": "f.py",
        "original": "orig",
        "subtype": "code",
        "context": "test context",
        "skeleton": "test skeleton",
    }

    class Args:
        think_filter = False
        think_filter_min_chars = 5000

    sem = asyncio.Semaphore(1)
    asyncio.run(
        process_fragment(
            FakeClient(""),
            "m",
            frag,
            "master",
            "changelog",
            sem,
            writer_ok,
            writer_bad,
            tracker,
            Args(),
        )
    )

    assert len(writer_ok.records) == 1
    assert tracker.calls and tracker.calls[0][0] == "accepted"
