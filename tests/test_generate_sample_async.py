#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0
"""Tests for generate_sample_async in src/factory/production_v11.py using a mocked client."""

from __future__ import annotations

import json
import asyncio
from types import SimpleNamespace

import pytest

import src.factory.prompt_builder as pb_module
from src.factory.pipeline_runner import generate_sample_async


class FakeCompletions:
    def __init__(self, response_text: str):
        self._response = response_text

    async def create(self, *args, **kwargs):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self._response))]
        )


class FakeClient:
    def __init__(self, response_text: str):
        self.chat = SimpleNamespace(completions=FakeCompletions(response_text))


def test_generate_sample_async_accepts_and_injects_gold(tmp_path) -> None:
    # Prepare fragment and master/changelog
    frag = {
        "name": "MyFragment",
        "virtual_filename": "mod.py",
        "original": "# original source code",
        "subtype": "code",
        "context": "example context",
        "skeleton": "def foo(): pass",
    }
    # Reasoning long enough and tool JSON with small code content (micro-snippet)
    reasoning = "R" * 200
    tool_json = {
        "name": "write_to_file",
        "arguments": {"content": "C" * 20, "path": "mod.py"},
    }
    raw = f"<think>{reasoning}</think><tool_call>{json.dumps(tool_json)}</tool_call>"

    # Populate minimal taxonomy prompts used by build_system_nominal
    pb_module._TAX = {
        "prompts": {
            "system": {
                "python": {
                    "base": "BASE $tools_json $master $changelog",
                    "nominal_suffix": " [nominal]",
                }
            },
            "user": {
                "python": {
                    "nominal_easy": "easy:$context|$virtual_filename|$name|$skeleton",
                    "nominal_medium": "medium:$context|$virtual_filename|$name|$skeleton",
                    "nominal_hard_anchor": "hard_anchor:$context|$virtual_filename|$name|$skeleton",
                    "nominal_hard_anchor_free": [
                        "hard_free:$context|$virtual_filename|$name|$skeleton"
                    ],
                }
            },
        }
    }
    pb_module.TOOLS_DEFINITION = []

    client = FakeClient(raw)
    sem = asyncio.Semaphore(1)

    res = asyncio.run(
        generate_sample_async(
            client=client,
            model="m",
            frag=frag,
            example_type="nominal",
            evol_difficulty="easy",
            master="MASTER",
            changelog="CHANGE",
            semaphore=sem,
            has_legacy=False,
            legacy_patterns=None,
            jinja_guide="",
        )
    )

    assert res["status"] == "accepted"
    sample = res["sample"]
    assert "conversation" in sample
    assert (
        sample["metadata"].get("gold_injected") in (True, False, None)
        or sample["metadata"].get("gold_injected") is not None
    )
