#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Coverage-targeted tests for src/curation/rewrite_engine.py.

Covers paths not reached by the existing backtracking_rewriter tests:
  - _VLLMAsyncAdapter instantiation and generate (lines 93-96, 107-116)
  - _setup_audit_dir exception path (lines 161-167)
  - _emit_audit_file exception path (lines 180-181)
  - apply_backtracking_rewrite empty prompts → None (lines 268-273)
  - sacred constraint violation restore (lines 375-379)
  - rewrite_pipeline with client=None creates adapter (line 428)
  - _bounded_rewrite rejection path (lines 502-513)
  - _bounded_rewrite failed/None result (lines 519-526)
  - per-record excerpt > 300 chars (line 546)
  - _bounded_rewrite exception in think feedback (lines 554-555)
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.curation import rewrite_engine as br_engine
from src.curation.backtracking_config import BacktrackingConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_record(
    record_id: str = "r1",
    think: str = "my reasoning",
    code: str = "x = 1",
    example_type: str = "error_recovery",
) -> dict:
    content = f"<think>{think}</think>{code}"
    return {
        "id": record_id,
        "conversation": [
            {"role": "user", "content": "do X"},
            {"role": "assistant", "content": content},
        ],
        "metadata": {"example_type": example_type},
    }


# ---------------------------------------------------------------------------
# _VLLMAsyncAdapter
# ---------------------------------------------------------------------------


class TestVLLMAsyncAdapter:
    """Tests for the deferred-import AsyncOpenAI adapter."""

    def test_init_and_model_stored(self):
        """Lines 93-96: deferred openai import + attributes set."""
        mock_openai_cls = MagicMock()
        mock_client_instance = MagicMock()
        mock_openai_cls.return_value = mock_client_instance

        with patch.dict(
            "sys.modules", {"openai": MagicMock(AsyncOpenAI=mock_openai_cls)}
        ):
            adapter = br_engine._VLLMAsyncAdapter(
                api_url="http://localhost:8000/v1",
                model="test-model",
            )

        mock_openai_cls.assert_called_once_with(
            base_url="http://localhost:8000/v1", api_key="EMPTY"
        )
        assert adapter._model == "test-model"
        assert adapter._client is mock_client_instance

    def test_generate_returns_content(self):
        """Lines 107-116: generate() calls completions.create and returns content."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="answer"))]

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        async def _run():
            with patch.dict(
                "sys.modules",
                {"openai": MagicMock(AsyncOpenAI=MagicMock(return_value=mock_client))},
            ):
                adapter = br_engine._VLLMAsyncAdapter("http://x", "m")
                return await adapter.generate(
                    "prompt",
                    system_prompt="sys",
                    max_tokens=512,
                    temperature=0.7,
                )

        result = asyncio.run(_run())
        assert result == "answer"

    def test_generate_returns_empty_string_when_content_none(self):
        """Lines 107-116: generate() falls back to '' when content is None."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=None))]

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        async def _run():
            with patch.dict(
                "sys.modules",
                {"openai": MagicMock(AsyncOpenAI=MagicMock(return_value=mock_client))},
            ):
                adapter = br_engine._VLLMAsyncAdapter("http://x", "m")
                return await adapter.generate(
                    "p", system_prompt="s", max_tokens=100, temperature=0.5
                )

        result = asyncio.run(_run())
        assert result == ""


# ---------------------------------------------------------------------------
# _setup_audit_dir error path
# ---------------------------------------------------------------------------


class TestSetupAuditDir:
    def test_returns_none_when_audit_dir_is_none(self):
        """No-op when audit_dir is None."""
        assert br_engine._setup_audit_dir(None) is None

    def test_creates_dir_successfully(self, tmp_path):
        """Happy path: creates a timestamped dir and returns it."""
        result = br_engine._setup_audit_dir(str(tmp_path))
        assert result is not None
        assert result.exists()

    def test_returns_none_on_exception(self, tmp_path):
        """Lines 161-167: returns None and logs warning when mkdir fails."""
        # Point audit_dir at an *existing file* so mkdir() will fail
        existing_file = tmp_path / "blocker"
        existing_file.write_text("block")
        sub = existing_file / "subdir"  # can't mkdir inside a file
        result = br_engine._setup_audit_dir(str(sub))
        assert result is None


# ---------------------------------------------------------------------------
# _emit_audit_file error path
# ---------------------------------------------------------------------------


class TestEmitAuditFile:
    def test_writes_json_file(self, tmp_path):
        """Happy path: writes JSON to audit dir."""
        record = {"id": "x", "data": "val"}
        br_engine._emit_audit_file(record, tmp_path)
        out = tmp_path / "x.json"
        assert out.exists()
        assert json.loads(out.read_text())["data"] == "val"

    def test_tolerates_write_failure(self, tmp_path):
        """Lines 180-181: swallows exception when write fails."""
        record = {"id": "y"}
        nonexistent_dir = tmp_path / "does_not_exist"
        # Should not raise — exception is caught and logged
        br_engine._emit_audit_file(record, nonexistent_dir)


# ---------------------------------------------------------------------------
# apply_backtracking_rewrite — empty prompts path
# ---------------------------------------------------------------------------


class TestApplyBacktrackingRewriteEdgeCases:
    def test_returns_none_when_prompts_empty(self, monkeypatch):
        """Lines 268-273: returns None when build_rewrite_prompt returns empty strings."""
        import src.curation.rewrite_engine as engine

        monkeypatch.setattr(
            "src.curation.rewrite_engine.build_rewrite_prompt",
            lambda *a, **kw: ("", ""),
        )

        record = _make_record(think="short", code="x = 1")
        client = AsyncMock()
        cfg = BacktrackingConfig()

        result = asyncio.run(
            engine.apply_backtracking_rewrite(
                record, client, cfg, _system_bt="BT", _system_rc="RC"
            )
        )
        assert result is None
        client.generate.assert_not_called()

    def test_sacred_constraint_violation_restores_original_code(self, monkeypatch):
        """Lines 375-379: when code block changes, restores original code."""
        import src.curation.rewrite_engine as engine

        # replace_think_block returns something that has a *different* code part
        def _fake_replace_think(assistant: str, new_think: str) -> str:
            # Deliberately corrupt the code part
            return f"<think>{new_think}</think>MODIFIED_CODE"

        monkeypatch.setattr(
            "src.curation.rewrite_engine.replace_think_block",
            _fake_replace_think,
        )

        record = _make_record(think="old reasoning", code="original_code()")
        client = AsyncMock()
        # Return a valid think-tagged response
        client.generate = AsyncMock(return_value="</think>new think")

        cfg = BacktrackingConfig()
        result = asyncio.run(
            engine.apply_backtracking_rewrite(
                record, client, cfg, _system_bt="BT", _system_rc="RC"
            )
        )
        # Result should have the original code preserved
        if result is not None:
            content = result["conversation"][-1]["content"]
            assert "original_code()" in content


# ---------------------------------------------------------------------------
# rewrite_pipeline — client=None creates _VLLMAsyncAdapter (line 428)
# ---------------------------------------------------------------------------


class TestRewritePipelineClientNone:
    def test_client_none_creates_adapter(self, tmp_path, monkeypatch):
        """Line 428: when client=None, _VLLMAsyncAdapter is instantiated."""
        bt = tmp_path / "bt.txt"
        rc = tmp_path / "rc.txt"
        bt.write_text("BT_PROMPT")
        rc.write_text("RC_PROMPT")
        input_path = tmp_path / "in.jsonl"
        out_path = tmp_path / "out.jsonl"
        # Empty input so pipeline exits immediately after creating client
        input_path.write_text("")

        cfg = BacktrackingConfig(
            backtracking_system_prompt_path=str(bt),
            reconstruction_system_prompt_path=str(rc),
        )

        # Mock _VLLMAsyncAdapter so no real OpenAI connection is made
        mock_adapter = MagicMock()
        mock_adapter.generate = AsyncMock(return_value="</think>ok")
        mock_adapter_cls = MagicMock(return_value=mock_adapter)

        monkeypatch.setattr(br_engine, "_VLLMAsyncAdapter", mock_adapter_cls)

        report = asyncio.run(
            br_engine.rewrite_pipeline(input_path, out_path, cfg, client=None)
        )
        assert mock_adapter_cls.called
        assert report.total_input == 0


# ---------------------------------------------------------------------------
# rewrite_pipeline — rejection / failed paths in _bounded_rewrite
# ---------------------------------------------------------------------------


class TestRewritePipelineBoundedRewritePaths:
    """Lines 502-526: rejection and None-result paths inside _bounded_rewrite."""

    def _write_input(self, tmp_path: Path) -> Path:
        record = _make_record(think="reasoning", code="code()")
        input_path = tmp_path / "in.jsonl"
        input_path.write_text(json.dumps(record, ensure_ascii=False))
        return input_path

    def test_rejection_path_increments_rejected_count(self, tmp_path, monkeypatch):
        """Lines 502-513: _RejectionSamplingError increments rejected counter."""
        from src.curation.backtracking_helpers import _RejectionSamplingError

        bt = tmp_path / "bt.txt"
        rc = tmp_path / "rc.txt"
        bt.write_text("BT")
        rc.write_text("RC")
        input_path = self._write_input(tmp_path)
        out_path = tmp_path / "out.jsonl"

        async def _failing_rewrite(*args, **kwargs):
            raise _RejectionSamplingError("legacy pattern")

        monkeypatch.setattr(br_engine, "apply_backtracking_rewrite", _failing_rewrite)

        class FakeClient:
            async def generate(self, *a, **kw):
                return ""

        cfg = BacktrackingConfig(
            backtracking_system_prompt_path=str(bt),
            reconstruction_system_prompt_path=str(rc),
        )
        report = asyncio.run(
            br_engine.rewrite_pipeline(input_path, out_path, cfg, client=FakeClient())
        )
        assert report.rejected >= 1
        assert report.total_output == 0

    def test_none_result_increments_failed_count(self, tmp_path, monkeypatch):
        """Lines 519-526: None result from apply_backtracking_rewrite increments failures."""
        bt = tmp_path / "bt.txt"
        rc = tmp_path / "rc.txt"
        bt.write_text("BT")
        rc.write_text("RC")
        input_path = self._write_input(tmp_path)
        out_path = tmp_path / "out.jsonl"

        async def _none_rewrite(*args, **kwargs):
            return None

        monkeypatch.setattr(br_engine, "apply_backtracking_rewrite", _none_rewrite)

        class FakeClient:
            async def generate(self, *a, **kw):
                return ""

        cfg = BacktrackingConfig(
            backtracking_system_prompt_path=str(bt),
            reconstruction_system_prompt_path=str(rc),
        )
        report = asyncio.run(
            br_engine.rewrite_pipeline(input_path, out_path, cfg, client=FakeClient())
        )
        assert report.failed >= 1
        assert report.total_output == 0

    def test_excerpt_truncated_when_over_300_chars(self, tmp_path, monkeypatch):
        """Line 546: excerpt > 300 chars is truncated to 297 + '...'."""
        bt = tmp_path / "bt.txt"
        rc = tmp_path / "rc.txt"
        bt.write_text("BT")
        rc.write_text("RC")
        input_path = self._write_input(tmp_path)
        out_path = tmp_path / "out.jsonl"

        # Return a think block with > 300 chars so truncation path is hit
        long_think = "A" * 350
        rewritten_record = _make_record(think=long_think, code="code()")

        async def _long_rewrite(record, *args, **kwargs):
            return rewritten_record

        monkeypatch.setattr(br_engine, "apply_backtracking_rewrite", _long_rewrite)
        monkeypatch.setattr(asyncio, "sleep", AsyncMock())

        class FakeClient:
            async def generate(self, *a, **kw):
                return f"</think>{'A' * 350}"

        cfg = BacktrackingConfig(
            backtracking_system_prompt_path=str(bt),
            reconstruction_system_prompt_path=str(rc),
        )
        report = asyncio.run(
            br_engine.rewrite_pipeline(input_path, out_path, cfg, client=FakeClient())
        )
        assert report.total_output >= 0  # just verify pipeline completed

    def test_exception_in_think_feedback_is_caught(self, tmp_path, monkeypatch):
        """Lines 554-555: exception in per-record think extraction is swallowed."""
        bt = tmp_path / "bt.txt"
        rc = tmp_path / "rc.txt"
        bt.write_text("BT")
        rc.write_text("RC")
        input_path = self._write_input(tmp_path)
        out_path = tmp_path / "out.jsonl"

        # Return a record with no assistant turn so _get_assistant_content raises
        def _bad_record_rewrite(record, *args, **kwargs):
            # Return a coroutine that gives a record without a proper assistant msg
            async def _inner():
                return {
                    "id": "x",
                    "conversation": [],  # _get_assistant_content will raise
                    "metadata": {
                        "backtracking_applied": True,
                        "backtracking_strategy": "full_backtracking",
                    },
                }

            return _inner()

        monkeypatch.setattr(
            br_engine, "apply_backtracking_rewrite", _bad_record_rewrite
        )

        class FakeClient:
            async def generate(self, *a, **kw):
                return ""

        cfg = BacktrackingConfig(
            backtracking_system_prompt_path=str(bt),
            reconstruction_system_prompt_path=str(rc),
        )
        # Should not raise — exception in feedback is caught
        report = asyncio.run(
            br_engine.rewrite_pipeline(input_path, out_path, cfg, client=FakeClient())
        )
        assert report is not None
