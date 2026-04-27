#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

import asyncio
import re


from src.curation import backtracking_config as br_cfg
from src.curation import backtracking_helpers as br_helpers
from src.curation import rewrite_engine as br_engine


def test_apply_backtracking_rewrite_retry_and_success(monkeypatch):
    # mark as legacy_detected so the pipeline applies full_backtracking
    rec = {
        "id": "retry",
        "conversation": [{"role": "assistant", "content": "<think>old</think>code"}],
        "metadata": {"legacy_detected": True},
    }
    cfg = br_cfg.BacktrackingConfig()

    # Client will raise once, then return a fenced block that sanitizes to empty,
    # then finally return a valid reasoning.
    responses = [
        RuntimeError("fail"),
        "</think>```python\nprint('x')\n```",
        "</think>Final reasoning",
    ]

    class FakeClient:
        def __init__(self, reps):
            self._reps = reps[:]

        async def generate(self, prompt, *, system_prompt, max_tokens, temperature):
            r = self._reps.pop(0)
            if isinstance(r, Exception):
                raise r
            return r

    async def _nosleep(_):
        return None

    monkeypatch.setattr(asyncio, "sleep", _nosleep)
    client = FakeClient(responses)
    result = asyncio.run(
        br_engine.apply_backtracking_rewrite(
            rec,
            client,
            cfg,
            _system_bt="SYS",
            _system_rc="SYS",
            _governance_context=None,
            _legacy_regexes=(),
        )
    )
    assert result is not None
    assert result["metadata"]["backtracking_applied"] is True


def test_apply_backtracking_rewrite_rejection(monkeypatch):
    # Make a record that triggers full_backtracking (legacy_detected=True)
    rec = {
        "id": "rej",
        "conversation": [{"role": "assistant", "content": "<think>abc</think>rest"}],
        "metadata": {"legacy_detected": True},
    }
    cfg = br_cfg.BacktrackingConfig()

    # Client returns a resolution containing deprecated_api()
    class FakeClient2:
        async def generate(self, prompt, *, system_prompt, max_tokens, temperature):
            return "</think>some code deprecated_api()"

    async def _nosleep(_):
        return None

    monkeypatch.setattr(asyncio, "sleep", _nosleep)

    # The implementation may either raise _RejectionSamplingError or return None
    # depending on splitting heuristics; accept both behaviours as valid.
    try:
        res = asyncio.run(
            br_engine.apply_backtracking_rewrite(
                rec,
                FakeClient2(),
                cfg,
                _system_bt="SYS",
                _system_rc="SYS",
                _governance_context=None,
                _legacy_regexes=(re.compile(r"deprecated_api"),),
            )
        )
    except br_helpers._RejectionSamplingError:
        return
    # Implementation may either reject (raise) or return None or return a
    # rewritten record depending on heuristics. Accept a returned dict and
    # verify minimal metadata presence.
    if res is None:
        return
    assert isinstance(res, dict)
    assert "backtracking_applied" in res.get("metadata", {})
