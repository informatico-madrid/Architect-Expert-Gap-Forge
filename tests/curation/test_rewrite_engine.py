# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""Tests for rewrite_engine module."""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.curation import rewrite_engine as re_module


class TestLoadJsonl:
    """Tests for load_jsonl function."""

    def test_load_empty_file(self, tmp_path):
        file_path = tmp_path / "empty.jsonl"
        file_path.write_text("")
        result = re_module.load_jsonl(file_path)
        assert result == []

    def test_load_single_record(self, tmp_path):
        file_path = tmp_path / "single.jsonl"
        record = {"id": "test-001", "content": "hello"}
        file_path.write_text(json.dumps(record))
        result = re_module.load_jsonl(file_path)
        assert len(result) == 1
        assert result[0]["id"] == "test-001"

    def test_load_multiple_records(self, tmp_path):
        file_path = tmp_path / "multi.jsonl"
        records = [{"id": f"test-{i}"} for i in range(3)]
        file_path.write_text("\n".join(json.dumps(r) for r in records))
        result = re_module.load_jsonl(file_path)
        assert len(result) == 3


class TestSaveJsonl:
    """Tests for save_jsonl function."""

    def test_save_single_record(self, tmp_path):
        file_path = tmp_path / "output.jsonl"
        records = [{"id": "test-001"}]
        re_module.save_jsonl(records, file_path)
        assert file_path.exists()
        content = file_path.read_text()
        assert "test-001" in content

    def test_save_multiple_records(self, tmp_path):
        file_path = tmp_path / "output.jsonl"
        records = [{"id": f"test-{i}"} for i in range(3)]
        re_module.save_jsonl(records, file_path)
        content = file_path.read_text()
        lines = content.strip().split("\n")
        assert len(lines) == 3


class TestSetupAuditDir:
    """Tests for _setup_audit_dir function."""

    def test_none_returns_none(self):
        result = re_module._setup_audit_dir(None)
        assert result is None

    def test_invalid_dir_returns_none(self):
        # Non-existent parent directory should return None
        result = re_module._setup_audit_dir("/nonexistent/path/audit")
        assert result is None


class TestEmitAuditFile:
    """Tests for _emit_audit_file function."""

    def test_emit_audit_file(self, tmp_path):
        result = {"id": "test-001", "content": "test"}
        re_module._emit_audit_file(result, tmp_path)
        # Should not raise - the function logs but doesn't raise on failure


class TestAsyncGenerateClient:
    """Tests for _AsyncGenerateClient protocol."""

    def test_protocol_check(self):
        # Test that the protocol works as expected
        mock_client = MagicMock()
        mock_client.generate = AsyncMock(return_value="test response")
        assert isinstance(mock_client, re_module._AsyncGenerateClient)


class TestVLLMAsyncAdapter:
    """Tests for _VLLMAsyncAdapter class."""

    @patch("openai.AsyncOpenAI")
    def test_init_deferred_client(self, mock_openai):
        adapter = re_module._VLLMAsyncAdapter("http://localhost:8000", "model-name")
        # Client should be created with correct params
        mock_openai.assert_called_once()
        assert adapter._model == "model-name"

    @patch("openai.AsyncOpenAI")
    @pytest.mark.asyncio
    async def test_generate_returns_content(self, mock_openai):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="test content"))]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        adapter = re_module._VLLMAsyncAdapter("http://localhost:8000", "test-model")
        result = await adapter.generate(
            "test prompt",
            system_prompt="system",
            max_tokens=100,
            temperature=0.7,
        )
        assert result == "test content"

    @patch("openai.AsyncOpenAI")
    @pytest.mark.asyncio
    async def test_generate_empty_content(self, mock_openai):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=None))]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        adapter = re_module._VLLMAsyncAdapter("http://localhost:8000", "test-model")
        result = await adapter.generate(
            "test prompt",
            system_prompt="system",
            max_tokens=100,
            temperature=0.7,
        )
        assert result == ""
