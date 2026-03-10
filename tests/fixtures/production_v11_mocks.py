#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Helpers and fake clients for `production_v11` tests.

Provides small factories that produce AsyncOpenAI-like clients whose
`chat.completions.create(...)` coroutine returns controlled strings that
exercise `parse_raw_response`, `post_validate_output` and the retry logic.

Usage examples:
    from tests.fixtures.production_v11_mocks import (
        make_client_with_write_action, raw_tool_call, make_client_with_tool_call
    )

    client = make_client_with_write_action('/tmp/x.py', 'print(1)', reasoning='Reason')
    # pass `client` to generate_sample_async/process_fragment
"""

from __future__ import annotations

import json
import types
from typing import Any, Dict, List


def raw_write_action(path: str, content: str, reasoning: str = "") -> str:
    """Compose a <write_action> response with optional <think> reasoning."""
    think = f"<think>{reasoning}</think>" if reasoning else ""
    return (
        f"{think}<write_action>"
        f"<path>{path}</path>"
        f"<content>\n{content}\n</content>"
        f"</write_action>"
    )


def raw_tool_call(obj: Any, reasoning: str = "") -> str:
    """Compose a <tool_call> response with JSON payload (tool_call fallback)."""
    think = f"<think>{reasoning}</think>" if reasoning else ""
    payload = json.dumps(obj)
    return f"{think}<tool_call>{payload}</tool_call>"


class _FakeResponse:
    def __init__(self, text: str) -> None:
        # Keep the minimal shape expected by production_v11
        self.choices = [
            types.SimpleNamespace(message=types.SimpleNamespace(content=text))
        ]


class _FakeCompletions:
    def __init__(self, responses: List[str]) -> None:
        self._responses = list(responses)
        self._last = self._responses[-1] if self._responses else ""

    async def create(self, **_kwargs) -> _FakeResponse:
        if self._responses:
            text = self._responses.pop(0)
        else:
            text = self._last
        return _FakeResponse(text)


class _FakeChat:
    def __init__(self, responses: List[str]) -> None:
        self.completions = _FakeCompletions(responses)


class FakeClient:
    """Minimal AsyncOpenAI-like client with `chat.completions.create()`.

    The constructor accepts a list of response strings; each call to
    `create()` returns the next string (or the last repeatedly).
    """

    def __init__(self, responses: List[str]) -> None:
        self.chat = _FakeChat(responses)


def make_client_with_write_action(
    path: str, content: str, reasoning: str = ""
) -> FakeClient:
    return FakeClient([raw_write_action(path, content, reasoning)])


def make_client_with_tool_call(obj: Any, reasoning: str = "") -> FakeClient:
    return FakeClient([raw_tool_call(obj, reasoning)])


def make_client_sequence(responses: List[str]) -> FakeClient:
    """Create a fake client that returns a sequence of raw responses.

    Useful for exercising retry behaviour: pass a list where early entries
    are malformed and the final entry is valid.
    """
    return FakeClient(responses)


__all__ = [
    "raw_write_action",
    "raw_tool_call",
    "FakeClient",
    "make_client_with_write_action",
    "make_client_with_tool_call",
    "make_client_sequence",
]
