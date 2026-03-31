# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License"):
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for ChatMLExporter.

Tests ChatML record generation, message structure, JSONL output,
and metadata fields for frontend knowledge extraction.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
import pytest

from src.export.chatml_exporter import (
    ChatMLExporter,
    ChatMLRecord,
    Message,
)
from src.utils.extractors.extractors.base import FrontendToken


class TestChatMLRecord:
    """Test suite for ChatMLRecord dataclass."""

    def test_chatml_record_creation(self):
        """Test basic ChatMLRecord creation with messages."""
        messages = [
            Message(role="system", content="You are helpful"),
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there"),
        ]
        record = ChatMLRecord(messages=messages)

        assert len(record.messages) == 3
        assert record.messages[0].role == "system"
        assert record.messages[1].role == "user"
        assert record.messages[2].role == "assistant"

    def test_chatml_record_to_dict(self):
        """Test ChatMLRecord serialization to dictionary."""
        messages = [
            Message(role="system", content="System prompt"),
            Message(role="user", content="User message"),
        ]
        record = ChatMLRecord(messages=messages)
        result = record.to_dict()

        assert "messages" in result
        assert len(result["messages"]) == 2
        assert result["messages"][0]["role"] == "system"
        assert result["messages"][0]["content"] == "System prompt"
        assert result["messages"][1]["role"] == "user"
        assert result["messages"][1]["content"] == "User message"

    def test_chatml_record_with_meta(self):
        """Test ChatMLRecord with metadata."""
        messages = [Message(role="user", content="Test")]
        meta = {"source": "lit_component", "file": "/path/to/component.ts"}
        record = ChatMLRecord(messages=messages, meta=meta)
        result = record.to_dict()

        assert "meta" in result
        assert result["meta"]["source"] == "lit_component"
        assert result["meta"]["file"] == "/path/to/component.ts"

    def test_chatml_record_meta_not_in_dict_when_none(self):
        """Test that meta is omitted when None."""
        messages = [Message(role="user", content="Test")]
        record = ChatMLRecord(messages=messages, meta=None)
        result = record.to_dict()

        assert "meta" not in result


class TestMessage:
    """Test suite for Message dataclass."""

    def test_message_creation(self):
        """Test Message creation with role and content."""
        msg = Message(role="assistant", content="Test response")

        assert msg.role == "assistant"
        assert msg.content == "Test response"

    def test_message_roles(self):
        """Test valid message roles."""
        for role in ["system", "user", "assistant"]:
            msg = Message(role=role, content="Test")
            assert msg.role == role


class TestChatMLExporter:
    """Test suite for ChatMLExporter."""

    @pytest.fixture
    def exporter(self) -> ChatMLExporter:
        """Create a ChatMLExporter instance for testing."""
        return ChatMLExporter()

    @pytest.fixture
    def sample_token(self) -> FrontendToken:
        """Create a sample FrontendToken for testing."""
        return FrontendToken(
            token_type="lit_component",
            data={
                "tag_name": "ha-dialog",
                "class_name": "HaDialog",
                "properties": ["open", "narrow"],
                "states": ["_loading"],
                "super_class": "LitElement",
                "observed_attributes": ["open"],
                "decorators": ["customElement", "property", "state"],
            },
            file_path=Path("src/components/ha-dialog.ts"),
            line_number=42,
        )

    @pytest.fixture
    def system_prompt(self) -> str:
        """Sample system prompt for testing."""
        return "You are a helpful assistant that extracts structured data."

    # --- ChatMLRecord format tests ---

    def test_export_single_token_returns_chatml_record(
        self, exporter, sample_token, system_prompt
    ):
        """Test that export yields ChatMLRecord for each token."""
        tokens = [sample_token]
        records = list(exporter.export(tokens, system_prompt))

        assert len(records) == 1
        assert isinstance(records[0], ChatMLRecord)

    def test_export_multiple_tokens_returns_multiple_records(
        self, exporter, system_prompt
    ):
        """Test that export yields one record per token."""
        tokens = [
            FrontendToken(
                token_type="lit_component",
                data={"tag_name": "ha-card"},
                file_path=Path("a.ts"),
                line_number=1,
            ),
            FrontendToken(
                token_type="i18n_key",
                data={"key": "ui.test"},
                file_path=Path("b.ts"),
                line_number=2,
            ),
        ]
        records = list(exporter.export(tokens, system_prompt))

        assert len(records) == 2

    # --- messages array structure tests ---

    def test_export_creates_three_messages(
        self, exporter, sample_token, system_prompt
    ):
        """Test that each record has system, user, and assistant messages."""
        tokens = [sample_token]
        records = list(exporter.export(tokens, system_prompt))

        assert len(records) == 1
        messages = records[0].messages
        assert len(messages) == 3

    def test_export_message_order(self, exporter, sample_token, system_prompt):
        """Test that messages are in correct order: system, user, assistant."""
        tokens = [sample_token]
        records = list(exporter.export(tokens, system_prompt))

        messages = records[0].messages
        assert messages[0].role == "system"
        assert messages[1].role == "user"
        assert messages[2].role == "assistant"

    def test_export_system_message_contains_prompt(
        self, exporter, sample_token, system_prompt
    ):
        """Test that system message contains the base prompt."""
        tokens = [sample_token]
        records = list(exporter.export(tokens, system_prompt))

        system_content = records[0].messages[0].content
        assert system_prompt in system_content

    def test_export_system_message_contains_schema_context(
        self, exporter, sample_token, system_prompt
    ):
        """Test that system message contains schema context for token type."""
        tokens = [sample_token]
        records = list(exporter.export(tokens, system_prompt))

        system_content = records[0].messages[0].content
        assert "lit_component" in system_content
        assert "Schema" in system_content

    def test_export_user_message_contains_source_info(
        self, exporter, sample_token, system_prompt
    ):
        """Test that user message contains source code and file info."""
        tokens = [sample_token]
        records = list(exporter.export(tokens, system_prompt))

        user_content = records[0].messages[1].content
        assert "ha-dialog.ts" in user_content
        assert "42" in user_content
        assert "lit_component" in user_content

    def test_export_user_message_contains_snippet(
        self, exporter, sample_token, system_prompt
    ):
        """Test that user message contains the token data as source snippet."""
        tokens = [sample_token]
        records = list(exporter.export(tokens, system_prompt))

        user_content = records[0].messages[1].content
        assert "tag_name" in user_content
        assert "ha-dialog" in user_content

    def test_export_assistant_message_is_json(
        self, exporter, sample_token, system_prompt
    ):
        """Test that assistant message is valid JSON."""
        tokens = [sample_token]
        records = list(exporter.export(tokens, system_prompt))

        assistant_content = records[0].messages[2].content
        # Should be valid JSON
        parsed = json.loads(assistant_content)
        assert parsed["tag_name"] == "ha-dialog"
        assert parsed["class_name"] == "HaDialog"

    # --- meta.source and meta.file fields tests ---

    def test_export_meta_source_is_token_type(
        self, exporter, sample_token, system_prompt
    ):
        """Test that meta.source equals token_type."""
        tokens = [sample_token]
        records = list(exporter.export(tokens, system_prompt))

        assert records[0].meta is not None
        assert records[0].meta["source"] == "lit_component"

    def test_export_meta_file_is_file_path(
        self, exporter, sample_token, system_prompt
    ):
        """Test that meta.file equals token file_path."""
        tokens = [sample_token]
        records = list(exporter.export(tokens, system_prompt))

        assert records[0].meta is not None
        assert records[0].meta["file"] == "src/components/ha-dialog.ts"

    def test_export_meta_differs_per_token(self, exporter, system_prompt):
        """Test that meta is correctly set for each different token."""
        tokens = [
            FrontendToken(
                token_type="lit_component",
                data={},
                file_path=Path("comp-a.ts"),
                line_number=1,
            ),
            FrontendToken(
                token_type="i18n_key",
                data={},
                file_path=Path("comp-b.ts"),
                line_number=5,
            ),
        ]
        records = list(exporter.export(tokens, system_prompt))

        assert records[0].meta["source"] == "lit_component"
        assert records[0].meta["file"] == "comp-a.ts"
        assert records[1].meta["source"] == "i18n_key"
        assert records[1].meta["file"] == "comp-b.ts"

    # --- JSONL output format tests ---

    def test_to_jsonl_writes_valid_jsonl(
        self, exporter, sample_token, system_prompt
    ):
        """Test that to_jsonl produces valid JSONL output."""
        tokens = [sample_token]
        records = exporter.export(tokens, system_prompt)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            output_path = Path(f.name)

        try:
            exporter.to_jsonl(records, output_path)

            with open(output_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            assert len(lines) == 1
            # Each line should be valid JSON
            parsed = json.loads(lines[0])
            assert "messages" in parsed
            assert len(parsed["messages"]) == 3
        finally:
            output_path.unlink(missing_ok=True)

    def test_to_jsonl_multiple_records(self, exporter, system_prompt):
        """Test that to_jsonl correctly writes multiple records."""
        tokens = [
            FrontendToken(
                token_type="lit_component",
                data={"tag_name": "ha-card"},
                file_path=Path("a.ts"),
                line_number=1,
            ),
            FrontendToken(
                token_type="i18n_key",
                data={"key": "ui.test"},
                file_path=Path("b.ts"),
                line_number=2,
            ),
        ]
        records = exporter.export(tokens, system_prompt)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            output_path = Path(f.name)

        try:
            exporter.to_jsonl(records, output_path)

            with open(output_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            assert len(lines) == 2
            for line in lines:
                parsed = json.loads(line)
                assert "messages" in parsed
                assert "meta" in parsed
        finally:
            output_path.unlink(missing_ok=True)

    def test_to_jsonl_creates_parent_directories(
        self, exporter, sample_token, system_prompt
    ):
        """Test that to_jsonl creates parent directories if needed."""
        tokens = [sample_token]
        records = exporter.export(tokens, system_prompt)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "nested" / "dir" / "output.jsonl"

            exporter.to_jsonl(records, output_path)

            assert output_path.exists()
            with open(output_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            assert len(lines) == 1

    def test_jsonl_record_structure(
        self, exporter, sample_token, system_prompt
    ):
        """Test the complete structure of a JSONL record."""
        tokens = [sample_token]
        records = exporter.export(tokens, system_prompt)
        record = next(records)

        record_dict = record.to_dict()

        # Top-level keys
        assert "messages" in record_dict
        assert "meta" in record_dict

        # Messages array
        assert len(record_dict["messages"]) == 3

        # Message structure
        for msg in record_dict["messages"]:
            assert "role" in msg
            assert "content" in msg
            assert msg["role"] in ("system", "user", "assistant")

        # Meta structure
        assert "source" in record_dict["meta"]
        assert "file" in record_dict["meta"]

    # --- different token type schema context tests ---

    def test_export_i18n_key_token_schema(
        self, exporter, system_prompt
    ):
        """Test schema context for i18n_key tokens."""
        token = FrontendToken(
            token_type="i18n_key",
            data={"key": "ui.card.door.lock", "context": "localize", "prefix": None},
            file_path=Path("test.ts"),
            line_number=10,
        )
        records = list(exporter.export([token], system_prompt))

        system_content = records[0].messages[0].content
        assert "i18n_key" in system_content
        assert "Schema" in system_content

        assistant_content = records[0].messages[2].content
        parsed = json.loads(assistant_content)
        assert parsed["key"] == "ui.card.door.lock"
        assert parsed["context"] == "localize"

    def test_export_service_call_token_schema(
        self, exporter, system_prompt
    ):
        """Test schema context for service_call tokens."""
        token = FrontendToken(
            token_type="service_call",
            data={
                "domain": "light",
                "service": "turn_on",
                "entity_ids": ["light.living_room"],
                "hass_prefix": "this.hass",
            },
            file_path=Path("test.ts"),
            line_number=20,
        )
        records = list(exporter.export([token], system_prompt))

        system_content = records[0].messages[0].content
        assert "service_call" in system_content

        assistant_content = records[0].messages[2].content
        parsed = json.loads(assistant_content)
        assert parsed["domain"] == "light"
        assert parsed["service"] == "turn_on"

    # --- edge cases ---

    def test_export_empty_tokens_list(self, exporter, system_prompt):
        """Test export with empty token list."""
        records = list(exporter.export([], system_prompt))
        assert len(records) == 0

    def test_export_unknown_token_type(self, exporter, system_prompt):
        """Test export with unknown token type uses fallback schema."""
        token = FrontendToken(
            token_type="unknown_type",
            data={"custom": "data"},
            file_path=Path("test.ts"),
            line_number=1,
        )
        records = list(exporter.export([token], system_prompt))

        assert len(records) == 1
        system_content = records[0].messages[0].content
        assert "unknown_type" in system_content

    def test_to_jsonl_empty_records(self, exporter):
        """Test to_jsonl with empty records iterator."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            output_path = Path(f.name)

        try:
            exporter.to_jsonl(iter([]), output_path)

            with open(output_path, "r", encoding="utf-8") as f:
                content = f.read()

            assert content == ""
        finally:
            output_path.unlink(missing_ok=True)


class TestChatMLExporterIntegration:
    """Integration tests for ChatMLExporter with realistic data."""

    def test_complete_lit_component_export(self):
        """Test complete export of a Lit component token."""
        exporter = ChatMLExporter()
        system_prompt = "Extract structured data from web components."

        token = FrontendToken(
            token_type="lit_component",
            data={
                "tag_name": "ha-paper-card",
                "class_name": "HaPaperCard",
                "properties": ["elevation", "animated"],
                "states": ["_clicked"],
                "super_class": "LitElement",
                "observed_attributes": ["elevation"],
                "decorators": [
                    "@customElement('ha-paper-card')",
                    "@property({ type: Boolean })",
                    "@state()",
                ],
            },
            file_path=Path("src/cards/ha-paper-card.ts"),
            line_number=38,
        )

        records = list(exporter.export([token], system_prompt))

        assert len(records) == 1
        record = records[0]

        # Verify meta
        assert record.meta["source"] == "lit_component"
        assert record.meta["file"] == "src/cards/ha-paper-card.ts"

        # Verify messages
        assert len(record.messages) == 3

        # System message has schema
        assert "Schema" in record.messages[0].content

        # User message has file/line info
        assert "ha-paper-card.ts" in record.messages[1].content
        assert "38" in record.messages[1].content

        # Assistant message is valid JSON
        parsed = json.loads(record.messages[2].content)
        assert parsed["tag_name"] == "ha-paper-card"
        assert parsed["class_name"] == "HaPaperCard"

    def test_jsonl_output_can_be_read_back(self):
        """Test that JSONL output can be parsed back correctly."""
        exporter = ChatMLExporter()

        tokens = [
            FrontendToken(
                token_type="lit_component",
                data={"tag_name": "ha-button"},
                file_path=Path("button.ts"),
                line_number=1,
            ),
            FrontendToken(
                token_type="i18n_key",
                data={"key": "ui.button.click", "context": "localize", "prefix": None},
                file_path=Path("button.ts"),
                line_number=5,
            ),
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            output_path = Path(f.name)

        try:
            exporter.to_jsonl(exporter.export(tokens, "Test prompt"), output_path)

            # Read back and parse
            with open(output_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            assert len(lines) == 2

            # Parse first record
            record1 = json.loads(lines[0])
            assert record1["meta"]["source"] == "lit_component"
            assert len(record1["messages"]) == 3

            # Parse second record
            record2 = json.loads(lines[1])
            assert record2["meta"]["source"] == "i18n_key"
            assert len(record2["messages"]) == 3

        finally:
            output_path.unlink(missing_ok=True)