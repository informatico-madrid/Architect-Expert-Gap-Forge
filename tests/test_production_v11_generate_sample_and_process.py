#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for critical async generation and processing flows in production_v11.

These tests use lightweight fakes to exercise internal branches without
depending on external services or full taxonomy loading.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from src.factory import production_v11 as pv11


class _FakeCompletions:
    @staticmethod
    async def create(*args, **kwargs):
        # Default valid response: long reasoning + write_action with short content
        reason = "R" * 300
        content = "X" * 20
        raw = (
            f"<think>{reason}</think>"
            f"<write_action><path>module/file.py</path><content>{content}</content></write_action>"
        )

        class Msg:
            def __init__(self, content):
                self.content = content

        class Choice:
            def __init__(self, message):
                self.message = message

        class Resp:
            def __init__(self, content):
                self.choices = [Choice(Msg(content))]

        return Resp(raw)


class _FakeChat:
    completions = _FakeCompletions


class _FakeClient:
    def __init__(self):
        self.chat = _FakeChat()


def test_generate_sample_async_nominal_accepts_and_injects(monkeypatch):
    async def _run():
        # Simplify prompt rendering / taxonomy dependency
        monkeypatch.setattr(pv11, "_prompt", lambda key: "[P]", raising=False)
        monkeypatch.setattr(pv11, "_render", lambda s, **k: s, raising=False)
        monkeypatch.setattr(pv11, "TOOLS_DEFINITION", [], raising=False)

        client = _FakeClient()
        semaphore = asyncio.Semaphore(1)

        frag = {
            "name": "Sample",
            "original": "def foo():\n    return 1\n",
            "skeleton": "def foo():\n    pass\n",
            "context": "ctx",
            "virtual_filename": "pkg/sample.py",
            "subtype": "code",
        }

        result = await pv11.generate_sample_async(
            client,
            "model-x",
            frag,
            "nominal",
            "easy",
            master="M",
            changelog="C",
            semaphore=semaphore,
        )

        assert result["status"] == "accepted"
        sample = result["sample"]
        assert sample["metadata"]["example_type"] in (
            "nominal",
            "contrast",
            "error_recovery",
        )
        # For nominal non-functional fragments we expect gold_injected True when output is clean
        assert "gold_injected" in sample["metadata"]

    asyncio.run(_run())


def test_generate_sample_async_rejects_on_parse_failure(monkeypatch):
    async def _run():
        # Return an invalid raw response (no <write_action>) to force parse error
        class BadCompletions:
            @staticmethod
            async def create(*args, **kwargs):
                class Msg:
                    def __init__(self, content):
                        self.content = content

                class Choice:
                    def __init__(self, message):
                        self.message = message

                class Resp:
                    def __init__(self, content):
                        self.choices = [Choice(Msg(content))]

                return Resp("<think></think>NO_ACTION_HERE")

        class BadChat:
            completions = BadCompletions

        class BadClient:
            def __init__(self):
                self.chat = BadChat()

        monkeypatch.setattr(pv11, "_prompt", lambda key: "[P]", raising=False)
        monkeypatch.setattr(pv11, "_render", lambda s, **k: s, raising=False)

        client = BadClient()
        semaphore = asyncio.Semaphore(1)
        frag = {
            "name": "Broken",
            "original": "def x():\n  pass\n",
            "skeleton": "def x():\n  pass\n",
            "context": "ctx",
            "virtual_filename": "pkg/broken.py",
            "subtype": "code",
        }

        result = await pv11.generate_sample_async(
            client,
            "model-x",
            frag,
            "nominal",
            "easy",
            master="M",
            changelog="C",
            semaphore=semaphore,
        )

        assert result["status"] == "rejected"
        assert "No <write_action> or <tool_call> found" in result.get(
            "reason", ""
        ) or "Failed after" in result.get("reason", "")

    asyncio.run(_run())


def test_process_fragment_writes_to_ok_when_sample_kept(monkeypatch):
    async def _run():
        # Monkeypatch generate_sample_async to return an accepted sample
        async def fake_generate(
            client,
            model,
            frag,
            example_type,
            evol_difficulty,
            master,
            changelog,
            semaphore,
            **kwargs,
        ):
            return {
                "status": "accepted",
                "sample": {
                    "id": "v11_nominal_fake",
                    "conversation": [],
                    "metadata": {
                        "example_type": "nominal",
                        "evol_difficulty": "easy",
                        "checkpoint_key": "ck1",
                        "curation": {"kept": True},
                        "gold_injected": True,
                    },
                    "filter_text": "ft",
                },
            }

        monkeypatch.setattr(pv11, "generate_sample_async", fake_generate, raising=False)

        class FakeWriter:
            def __init__(self):
                self.records = []

            async def write(self, rec):
                self.records.append(rec)

        # Use a real tracker (small) — it prints but is safe
        tracker = pv11.ProgressTracker(total=1, mode="code")

        writer_ok = FakeWriter()
        writer_bad = FakeWriter()

        # Simple args namespace: disable think_filter to avoid optional dependency paths
        args = SimpleNamespace(think_filter=False, think_filter_min_chars=5000)

        frag = {
            "name": "Proc",
            "original": "def p():\n  pass\n",
            "skeleton": "def p():\n  pass\n",
            "context": "ctx",
            "virtual_filename": "pkg/proc.py",
            "subtype": "code",
        }

        await pv11.process_fragment(
            client=None,
            model="m",
            frag=frag,
            master="M",
            changelog="C",
            semaphore=asyncio.Semaphore(1),
            writer_ok=writer_ok,
            writer_bad=writer_bad,
            tracker=tracker,
            args=args,
        )

        assert len(writer_ok.records) == 1
        assert len(writer_bad.records) == 0

    asyncio.run(_run())
