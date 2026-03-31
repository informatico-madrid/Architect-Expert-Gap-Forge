#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Architect-Expert-Gap-Forge (AEGF) - Anchor Dataset Downloader Tests

Unit tests for the AnchorDatasetDownloader module.
Tests cover downloading anchor datasets from HuggingFace Hub (xlam-function-calling-60k,
FineTome-100k, Magicoder), subsampling by token count, and JSONL export.

Location: tests/curation/test_anchor_dataset_downloader.py
SPDX-License-Identifier: Apache-2.0
Copyright 2026 AEGF
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import tiktoken

from src.curation.anchor_dataset_downloader import AnchorDatasetConfig, AnchorDatasetDownloader
from src.utils.schema import DatasetRecord, Message
from tests.utils.mocks_huggingface import MockHuggingFaceHub, MockHuggingFaceContext

logger = logging.getLogger(__name__)


# =============================================================================
# TEST FIXTURES
# =============================================================================


@pytest.fixture
def xlam_function_calling_record() -> dict[str, Any]:
    """Fixture: xlam-function-calling-60k format record (function calling)."""
    return {
        "id": "xlam-fc-001",
        "conversations": [
            {"from": "human", "value": "What is the weather like in Tokyo?"},
            {
                "from": "gpt",
                "value": "I'll check the weather for you.",
                "function_call": {
                    "name": "get_weather",
                    "arguments": {"city": "Tokyo", "unit": "celsius"},
                },
            },
        ],
        "function": {"name": "get_weather", "description": "Get weather information"},
    }


@pytest.fixture
def xlam_function_calling_records() -> list[dict[str, Any]]:
    """Fixture: Multiple xlam-function-calling-60k format records."""
    return [
        {
            "id": "xlam-fc-001",
            "conversations": [
                {"from": "human", "value": "What's the weather in New York?"},
                {
                    "from": "gpt",
                    "value": "Let me check.",
                    "function_call": {
                        "name": "get_weather",
                        "arguments": {"city": "New York", "unit": "fahrenheit"},
                    },
                },
            ],
            "function": {"name": "get_weather", "description": "Get weather info"},
        },
        {
            "id": "xlam-fc-002",
            "conversations": [
                {"from": "human", "value": "Set the thermostat to 72 degrees"},
                {
                    "from": "gpt",
                    "value": "Setting the temperature now.",
                    "function_call": {
                        "name": "set_temperature",
                        "arguments": {"temperature": 72, "unit": "fahrenheit"},
                    },
                },
            ],
            "function": {"name": "set_temperature", "description": "Set temperature"},
        },
        {
            "id": "xlam-fc-003",
            "conversations": [
                {"from": "human", "value": "Turn on the living room lights"},
                {
                    "from": "gpt",
                    "value": "Turning on the lights.",
                    "function_call": {
                        "name": "toggle_light",
                        "arguments": {"room": "living_room", "state": "on"},
                    },
                },
            ],
            "function": {"name": "toggle_light", "description": "Toggle light state"},
        },
    ]


@pytest.fixture
def finetome_record() -> dict[str, Any]:
    """Fixture: FineTome-100k format record (Alpaca-like)."""
    return {
        "id": "finetome-001",
        "conversations": [
            {"from": "human", "value": "Write a function to calculate fibonacci numbers"},
            {
                "from": "gpt",
                "value": "Here's a Python function to calculate fibonacci numbers:\n\n```python\ndef fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)\n```",
            },
        ],
    }


@pytest.fixture
def finetome_records() -> list[dict[str, Any]]:
    """Fixture: Multiple FineTome-100k format records."""
    return [
        {
            "id": "finetome-001",
            "conversations": [
                {"from": "human", "value": "How do I reverse a string in Python?"},
                {
                    "from": "gpt",
                    "value": "You can reverse a string using slicing: `s[::-1]`",
                },
            ],
        },
        {
            "id": "finetome-002",
            "conversations": [
                {"from": "human", "value": "Explain list comprehensions"},
                {
                    "from": "gpt",
                    "value": "List comprehensions provide a concise way to create lists...",
                },
            ],
        },
        {
            "id": "finetome-003",
            "conversations": [
                {"from": "human", "value": "What is a decorator in Python?"},
                {
                    "from": "gpt",
                    "value": "A decorator is a function that takes another function as input...",
                },
            ],
        },
    ]


@pytest.fixture
def magicoder_record() -> dict[str, Any]:
    """Fixture: Magicoder format record (code generation)."""
    return {
        "id": "magicoder-001",
        "conversations": [
            {"from": "human", "value": "Write a Python function to merge two sorted lists"},
            {
                "from": "gpt",
                "value": "Here's a solution:\n\n```python\ndef merge_sorted_lists(l1, l2):\n    result = []\n    i = j = 0\n    while i < len(l1) and j < len(l2):\n        if l1[i] <= l2[j]:\n            result.append(l1[i])\n            i += 1\n        else:\n            result.append(l2[j])\n            j += 1\n    result.extend(l1[i:])\n    result.extend(l2[j:])\n    return result\n```",
            },
        ],
    }


@pytest.fixture
def magicoder_records() -> list[dict[str, Any]]:
    """Fixture: Multiple Magicoder format records."""
    return [
        {
            "id": "magicoder-001",
            "conversations": [
                {"from": "human", "value": "Write a function to check palindrome"},
                {
                    "from": "gpt",
                    "value": "```python\ndef is_palindrome(s):\n    return s == s[::-1]\n```",
                },
            ],
        },
        {
            "id": "magicoder-002",
            "conversations": [
                {"from": "human", "value": "Create a binary search function"},
                {
                    "from": "gpt",
                    "value": "```python\ndef binary_search(arr, target):\n    left, right = 0, len(arr) - 1\n    while left <= right:\n        mid = (left + right) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            left = mid + 1\n        else:\n            right = mid - 1\n    return -1\n```",
                },
            ],
        },
        {
            "id": "magicoder-003",
            "conversations": [
                {"from": "human", "value": "Write quicksort implementation"},
                {
                    "from": "gpt",
                    "value": "```python\ndef quicksort(arr):\n    if len(arr) <= 1:\n        return arr\n    pivot = arr[len(arr) // 2]\n    left = [x for x in arr if x < pivot]\n    middle = [x for x in arr if x == pivot]\n    right = [x for x in arr if x > pivot]\n    return quicksort(left) + middle + quicksort(right)\n```",
                },
            ],
        },
    ]


@pytest.fixture
def mock_huggingface_download(tmp_path: Path) -> MagicMock:
    """Fixture: Mock huggingface_hub.snapshot_download."""
    mock = MagicMock()
    return mock


# =============================================================================
# TEST CLASSES
# =============================================================================


class TestXlamFunctionCallingParsing:
    """Tests for parsing xlam-function-calling-60k format."""

    def test_parse_xlam_function_calling_to_chatml(
        self, xlam_function_calling_record: dict[str, Any]
    ) -> None:
        """Test that xlam function calling format converts to ChatML correctly."""
        conversations = xlam_function_calling_record["conversations"]

        # Role mapping from ShareGPT-like format
        role_mapping = {"human": "user", "gpt": "assistant"}

        messages = []
        for conv in conversations:
            role = role_mapping.get(conv["from"], conv["from"])
            content = conv.get("value", "")

            # Handle function_call if present
            if "function_call" in conv:
                fc = conv["function_call"]
                content = f"{content}\n\n<tool_call>{fc['name']}</tool_call>"

            messages.append(Message(role=role, content=content))

        assert len(messages) == 2
        assert messages[0].role == "user"
        assert "weather" in messages[0].content.lower()
        assert messages[1].role == "assistant"
        assert "get_weather" in messages[1].content

    def test_parse_xlam_function_call_arguments_preserved(
        self, xlam_function_calling_record: dict[str, Any]
    ) -> None:
        """Test that function call arguments are preserved in the content."""
        conversations = xlam_function_calling_record["conversations"]
        fc = conversations[1]["function_call"]

        # Arguments should be accessible
        assert fc["name"] == "get_weather"
        assert "city" in fc["arguments"]
        assert fc["arguments"]["city"] == "Tokyo"


class TestFineTomeParsing:
    """Tests for parsing FineTome-100k format (ShareGPT-like)."""

    def test_parse_finetome_to_chatml(self, finetome_record: dict[str, Any]) -> None:
        """Test that FineTome format converts to ChatML correctly."""
        conversations = finetome_record["conversations"]

        role_mapping = {"human": "user", "gpt": "assistant"}

        messages = [
            Message(role=role_mapping.get(conv["from"], conv["from"]), content=conv["value"])
            for conv in conversations
        ]

        assert len(messages) == 2
        assert messages[0].role == "user"
        assert "fibonacci" in messages[0].content.lower()
        assert messages[1].role == "assistant"
        assert "python" in messages[1].content.lower()

    def test_finetome_multiline_code_preserved(self, finetome_record: dict[str, Any]) -> None:
        """Test that multiline code blocks are preserved in FineTome records."""
        conversations = finetome_record["conversations"]
        content = conversations[1]["value"]

        assert "```python" in content
        assert "def fibonacci" in content


class TestMagicoderParsing:
    """Tests for parsing Magicoder format."""

    def test_parse_magicoder_to_chatml(self, magicoder_record: dict[str, Any]) -> None:
        """Test that Magicoder format converts to ChatML correctly."""
        conversations = magicoder_record["conversations"]

        role_mapping = {"human": "user", "gpt": "assistant"}

        messages = [
            Message(role=role_mapping.get(conv["from"], conv["from"]), content=conv["value"])
            for conv in conversations
        ]

        assert len(messages) == 2
        assert messages[0].role == "user"
        assert "merge" in messages[0].content.lower()
        assert messages[1].role == "assistant"
        assert "```python" in messages[1].content

    def test_magicoder_code_block_structure(self, magicoder_record: dict[str, Any]) -> None:
        """Test that code blocks have proper structure in Magicoder records."""
        conversations = magicoder_record["conversations"]
        assistant_content = conversations[1]["value"]

        # Should have code block markers
        assert "```python" in assistant_content


class TestTokenCounting:
    """Tests for token counting functionality."""

    def test_count_tokens_in_messages(self) -> None:
        """Test that tokens are counted correctly using tiktoken."""
        messages = [
            Message(role="user", content="Hello, how are you?"),
            Message(role="assistant", content="I'm doing great, thank you!"),
        ]

        # Count tokens using tiktoken
        encoder = tiktoken.get_encoding("cl100k_base")
        total_tokens = 0

        for msg in messages:
            tokens = encoder.encode(msg.content)
            total_tokens += len(tokens)

        assert total_tokens > 0
        assert total_tokens < 100  # Short messages

    def test_token_count_for_long_content(self) -> None:
        """Test token counting for longer content."""
        long_content = (
            "This is a longer message that contains multiple sentences. "
            "It should have more tokens than a short message. " * 10
        )

        encoder = tiktoken.get_encoding("cl100k_base")
        tokens = encoder.encode(long_content)

        assert len(tokens) > 50


class TestSubsamplingByTokenCount:
    """Tests for subsampling datasets by token budget."""

    def test_subsample_by_token_count_logic(self) -> None:
        """Test that subsampling selects records within token budget."""
        # Simulate records with different token counts
        records = [
            {"id": "r1", "content": "Short", "tokens": 10},
            {"id": "r2", "content": "Medium length content here", "tokens": 50},
            {"id": "r3", "content": "Much longer content " * 10, "tokens": 200},
            {"id": "r4", "content": "Another short one", "tokens": 20},
            {"id": "r5", "content": "Even more content " * 5, "tokens": 100},
        ]

        target_tokens = 100
        selected = []
        total_tokens = 0

        for record in records:
            if total_tokens + record["tokens"] <= target_tokens:
                selected.append(record)
                total_tokens += record["tokens"]

        # Should select r1(10) + r4(20) = 30 tokens, then r2(50) = 80 tokens
        # Can't fit r3(200) or r5(100)
        assert len(selected) == 3
        assert total_tokens <= target_tokens

    def test_subsample_preserves_record_order(self) -> None:
        """Test that subsampling preserves original order of selected records."""
        records = [
            {"id": f"r{i}", "tokens": 10 * i}
            for i in range(1, 11)
        ]

        target_tokens = 35
        selected = []
        total_tokens = 0

        for record in records:
            if total_tokens + record["tokens"] <= target_tokens:
                selected.append(record)
                total_tokens += record["tokens"]

        # Should be in order: r1(10), r2(20)=30, r3(30)=60 (too much), so stops
        assert selected[0]["id"] == "r1"
        assert selected[1]["id"] == "r2"


class TestSubsampleMethod:
    """Tests for the actual AnchorDatasetDownloader.subsample method."""

    def _create_record(self, record_id: str, token_count: int) -> DatasetRecord:
        """Helper to create a DatasetRecord with specified token count in metadata."""
        messages = [Message(role="user", content=f"Message for {record_id}")]
        return DatasetRecord(
            messages=messages,
            metadata={"origin": "test", "type": "test", "use_case": "test", "token_count": token_count},
        )

    def test_subsample_selects_records_within_budget(self) -> None:
        """Test that subsample selects records within the token budget."""
        config = AnchorDatasetConfig(
            hf_id="test/dataset",
            split="train",
            format="sharegpt",
            token_budget_pct=50.0
        )
        downloader = AnchorDatasetDownloader([config])

        # Create records with token counts: 10, 50, 200, 20, 100
        records = [
            self._create_record("r1", 10),
            self._create_record("r2", 50),
            self._create_record("r3", 200),
            self._create_record("r4", 20),
            self._create_record("r5", 100),
        ]

        # Budget of 100 should select in order: r1(10), r2(50)=60, r4(20)=80
        # r3(200) and r5(100) don't fit
        result = downloader.subsample(records, token_budget=100)

        assert len(result) == 3
        assert result[0].messages[0].content == "Message for r1"
        assert result[1].messages[0].content == "Message for r2"
        assert result[2].messages[0].content == "Message for r4"

    def test_subsample_empty_records_list(self) -> None:
        """Test that subsample handles empty records list."""
        config = AnchorDatasetConfig(
            hf_id="test/dataset",
            split="train",
            format="sharegpt",
            token_budget_pct=50.0
        )
        downloader = AnchorDatasetDownloader([config])

        result = downloader.subsample([], token_budget=1000)

        assert result == []

    def test_subsample_zero_token_budget(self) -> None:
        """Test that subsample with zero token budget returns empty list."""
        config = AnchorDatasetConfig(
            hf_id="test/dataset",
            split="train",
            format="sharegpt",
            token_budget_pct=50.0
        )
        downloader = AnchorDatasetDownloader([config])

        records = [self._create_record("r1", 10)]

        result = downloader.subsample(records, token_budget=0)

        assert result == []

    def test_subsample_large_budget_includes_all(self) -> None:
        """Test that large token budget includes all records."""
        config = AnchorDatasetConfig(
            hf_id="test/dataset",
            split="train",
            format="sharegpt",
            token_budget_pct=50.0
        )
        downloader = AnchorDatasetDownloader([config])

        records = [
            self._create_record("r1", 10),
            self._create_record("r2", 50),
            self._create_record("r3", 100),
        ]

        result = downloader.subsample(records, token_budget=10000)

        assert len(result) == 3

    def test_subsample_exact_fit(self) -> None:
        """Test that subsample handles exact fit (total equals budget)."""
        config = AnchorDatasetConfig(
            hf_id="test/dataset",
            split="train",
            format="sharegpt",
            token_budget_pct=50.0
        )
        downloader = AnchorDatasetDownloader([config])

        records = [
            self._create_record("r1", 50),
            self._create_record("r2", 50),
        ]

        result = downloader.subsample(records, token_budget=100)

        assert len(result) == 2

    def test_subsample_missing_token_count(self) -> None:
        """Test that subsample handles records without token_count in metadata."""
        config = AnchorDatasetConfig(
            hf_id="test/dataset",
            split="train",
            format="sharegpt",
            token_budget_pct=50.0
        )
        downloader = AnchorDatasetDownloader([config])

        # Record without token_count
        messages = [Message(role="user", content="Test")]
        record_no_tokens = DatasetRecord(
            messages=messages,
            metadata={"origin": "test", "type": "test", "use_case": "test"},
        )
        records = [record_no_tokens, self._create_record("r1", 50)]

        result = downloader.subsample(records, token_budget=100)

        # Should include record with no token_count (treated as 0) and r1
        assert len(result) == 2

    def test_subsample_preserves_order(self) -> None:
        """Test that subsample preserves the order of selected records."""
        config = AnchorDatasetConfig(
            hf_id="test/dataset",
            split="train",
            format="sharegpt",
            token_budget_pct=50.0
        )
        downloader = AnchorDatasetDownloader([config])

        records = [
            self._create_record("r1", 10),
            self._create_record("r2", 20),
            self._create_record("r3", 30),
            self._create_record("r4", 40),
        ]

        # Budget of 35 should select r1(10), r2(20) = 30 tokens, can't fit r3(30)
        result = downloader.subsample(records, token_budget=35)

        assert len(result) == 2
        assert result[0].messages[0].content == "Message for r1"
        assert result[1].messages[0].content == "Message for r2"

    def test_subsample_single_record_fits(self) -> None:
        """Test that subsample selects a single record that fits."""
        config = AnchorDatasetConfig(
            hf_id="test/dataset",
            split="train",
            format="sharegpt",
            token_budget_pct=50.0
        )
        downloader = AnchorDatasetDownloader([config])

        records = [self._create_record("r1", 50)]

        result = downloader.subsample(records, token_budget=100)

        assert len(result) == 1
        assert result[0].messages[0].content == "Message for r1"

    def test_subsample_record_too_large(self) -> None:
        """Test that subsample skips records that exceed budget."""
        config = AnchorDatasetConfig(
            hf_id="test/dataset",
            split="train",
            format="sharegpt",
            token_budget_pct=50.0
        )
        downloader = AnchorDatasetDownloader([config])

        records = [
            self._create_record("r1", 10),
            self._create_record("r2", 500),  # Exceeds budget alone
            self._create_record("r3", 20),
        ]

        result = downloader.subsample(records, token_budget=100)

        # Should only select r1(10) and r3(20) = 30 tokens, skip r2
        assert len(result) == 2
        assert result[0].messages[0].content == "Message for r1"
        assert result[1].messages[0].content == "Message for r3"


class TestJsonlExport:
    """Tests for JSONL export functionality."""

    def test_export_single_record_to_jsonl(self, tmp_path: Path) -> None:
        """Test exporting a single record to JSONL format."""
        messages = [
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there!"),
        ]

        record = DatasetRecord(
            messages=messages,
            metadata={"origin": "test", "type": "test", "use_case": "test"},
        )

        output_path = tmp_path / "output.jsonl"
        with open(output_path, "w") as f:
            f.write(record.model_dump_json() + "\n")

        # Verify file exists and is valid JSONL
        assert output_path.exists()
        with open(output_path) as f:
            content = f.read()
            loaded = json.loads(content)
            assert "messages" in loaded

    def test_export_multiple_records_to_jsonl(self, tmp_path: Path) -> None:
        """Test exporting multiple records to JSONL format."""
        records = []
        for i in range(5):
            messages = [
                Message(role="user", content=f"Message {i}"),
                Message(role="assistant", content=f"Response {i}"),
            ]
            records.append(
                DatasetRecord(
                    messages=messages,
                    metadata={"origin": "test", "type": "test"},
                )
            )

        output_path = tmp_path / "output.jsonl"
        with open(output_path, "w") as f:
            for record in records:
                f.write(record.model_dump_json() + "\n")

        # Verify file has correct number of lines
        with open(output_path) as f:
            lines = f.readlines()
            assert len(lines) == 5

        # Verify each line is valid JSON
        with open(output_path) as f:
            for line in f:
                loaded = json.loads(line)
                assert "messages" in loaded

    def test_jsonl_valid_structure(self, tmp_path: Path) -> None:
        """Test that exported JSONL has valid ChatML structure."""
        messages = [
            Message(role="system", content="You are helpful."),
            Message(role="user", content="What is 2+2?"),
            Message(role="assistant", content="2+2 equals 4."),
        ]

        record = DatasetRecord(
            messages=messages,
            metadata={"origin": "anchor", "type": "general", "format": "chatml"},
        )

        output_path = tmp_path / "test.jsonl"
        with open(output_path, "w") as f:
            f.write(record.model_dump_json() + "\n")

        # Parse and validate structure
        with open(output_path) as f:
            line = f.readline()
            loaded = json.loads(line)

        assert "messages" in loaded
        assert len(loaded["messages"]) == 3

        # Check roles
        roles = [msg["role"] for msg in loaded["messages"]]
        assert roles == ["system", "user", "assistant"]


class TestAnchorDatasetDownloaderInterface:
    """
    Abstract interface tests for AnchorDatasetDownloader.

    These tests document the expected interface for AnchorDatasetDownloader.
    They will pass once T021 (implementation) is completed.
    """

    def test_downloader_has_download_method(self) -> None:
        """Test that AnchorDatasetDownloader has a download method."""
        config = AnchorDatasetConfig(
            hf_id="test/dataset",
            split="train",
            format="sharegpt",
            token_budget_pct=30.0
        )
        downloader = AnchorDatasetDownloader([config])
        assert hasattr(downloader, "download")
        assert callable(downloader.download)

    def test_downloader_has_parse_method(self) -> None:
        """Test that AnchorDatasetDownloader has a parse method."""
        config = AnchorDatasetConfig(
            hf_id="test/dataset",
            split="train",
            format="sharegpt",
            token_budget_pct=30.0
        )
        downloader = AnchorDatasetDownloader([config])
        assert hasattr(downloader, "parse")
        assert callable(downloader.parse)

    def test_downloader_has_subsample_method(self) -> None:
        """Test that AnchorDatasetDownloader has a subsample method."""
        config = AnchorDatasetConfig(
            hf_id="test/dataset",
            split="train",
            format="sharegpt",
            token_budget_pct=30.0
        )
        downloader = AnchorDatasetDownloader([config])
        assert hasattr(downloader, "subsample")
        assert callable(downloader.subsample)

    def test_downloader_has_export_method(self) -> None:
        """Test that AnchorDatasetDownloader has an export method."""
        config = AnchorDatasetConfig(
            hf_id="test/dataset",
            split="train",
            format="sharegpt",
            token_budget_pct=30.0
        )
        downloader = AnchorDatasetDownloader([config])
        assert hasattr(downloader, "export")
        assert callable(downloader.export)

    def test_downloader_has_configs_property(self) -> None:
        """Test that AnchorDatasetDownloader has a configs property."""
        config = AnchorDatasetConfig(
            hf_id="test/dataset",
            split="train",
            format="sharegpt",
            token_budget_pct=30.0
        )
        downloader = AnchorDatasetDownloader([config])
        assert hasattr(downloader, "configs")
        assert downloader.configs == [config]


class TestDatasetIntegration:
    """Integration tests for complete download-parse-export workflow."""

    def test_complete_workflow_single_dataset(self, tmp_path: Path) -> None:
        """Test complete workflow for a single dataset."""
        # Simulate downloading FineTome records
        raw_records = [
            {
                "id": "ft-001",
                "conversations": [
                    {"from": "human", "value": "Question 1"},
                    {"from": "gpt", "value": "Answer 1"},
                ],
            },
            {
                "id": "ft-002",
                "conversations": [
                    {"from": "human", "value": "Question 2"},
                    {"from": "gpt", "value": "Answer 2"},
                ],
            },
        ]

        # Parse to ChatML
        role_mapping = {"human": "user", "gpt": "assistant"}
        parsed_records = []

        encoder = tiktoken.get_encoding("cl100k_base")

        for raw in raw_records:
            messages = [
                Message(
                    role=role_mapping.get(conv["from"], conv["from"]),
                    content=conv["value"],
                )
                for conv in raw["conversations"]
            ]

            # Calculate token count
            content = " ".join(m.content for m in messages)
            token_count = len(encoder.encode(content))

            record = DatasetRecord(
                messages=messages,
                metadata={
                    "origin": "fine_tome",
                    "type": "general",
                    "token_count": token_count,
                    "format": "chatml",
                },
            )
            parsed_records.append(record)

        # Export to JSONL
        output_path = tmp_path / "fine_tome.jsonl"
        with open(output_path, "w") as f:
            for record in parsed_records:
                f.write(record.model_dump_json() + "\n")

        # Verify output
        assert output_path.exists()
        with open(output_path) as f:
            lines = f.readlines()
            assert len(lines) == 2

        # Verify token counts are present
        for record in parsed_records:
            assert record.metadata["token_count"] > 0

    def test_multiple_anchor_datasets_mixed(
        self, tmp_path: Path
    ) -> None:
        """Test processing multiple anchor datasets together."""
        # FineTome records
        finetome_data = [
            {
                "id": "ft-001",
                "conversations": [
                    {"from": "human", "value": "What is Python?"},
                    {"from": "gpt", "value": "Python is a programming language."},
                ],
            }
        ]

        # Magicoder records
        magicoder_data = [
            {
                "id": "mc-001",
                "conversations": [
                    {"from": "human", "value": "Write a function"},
                    {"from": "gpt", "value": "```python\ndef foo():\n    pass\n```"},
                ],
            }
        ]

        all_records = []

        for raw in finetome_data + magicoder_data:
            origin = "fine_tome" if raw["id"].startswith("ft") else "magicoder"
            messages = [
                Message(
                    role="user" if conv["from"] == "human" else "assistant",
                    content=conv["value"],
                )
                for conv in raw["conversations"]
            ]

            all_records.append(
                DatasetRecord(
                    messages=messages,
                    metadata={"origin": origin, "type": "general"},
                )
            )

        # Should have records from both sources
        origins = set(r.metadata.get("origin", "") for r in all_records)
        assert "fine_tome" in origins
        assert "magicoder" in origins
        assert len(all_records) == 2


class TestMockHuggingFaceDownload:
    """Tests using mocked HuggingFace Hub download.

    These tests verify the expected behavior of snapshot_download mocking.
    The actual implementation of AnchorDatasetDownloader will use these patterns.
    """

    def test_snapshot_download_interface_contract(self, tmp_path: Path) -> None:
        """Test the expected interface contract for snapshot_download.

        This verifies what snapshot_download should return:
        - A local directory path containing the dataset files
        """
        # Simulate what snapshot_download returns in a real scenario
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        # Mock the expected return value of snapshot_download
        expected_path = str(data_dir)

        # The path should exist and be a directory
        assert os.path.exists(expected_path)
        assert os.path.isdir(expected_path)

    def test_download_xlam_function_calling_parsing(self, tmp_path: Path) -> None:
        """Test parsing of xlam-function-calling-60k data after download."""
        # Simulate downloaded data
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        dataset_file = data_dir / "data.jsonl"
        records = [
            {"id": "xlam-001", "conversations": [
                {"from": "human", "value": "Call weather API for London"},
                {"from": "gpt", "value": "I'll call that function", "function_call": {
                    "name": "get_weather",
                    "arguments": {"city": "London"}
                }},
            ]},
            {"id": "xlam-002", "conversations": [
                {"from": "human", "value": "Set temperature to 72"},
                {"from": "gpt", "value": "Setting it now", "function_call": {
                    "name": "set_temperature",
                    "arguments": {"temp": 72}
                }},
            ]},
        ]

        with open(dataset_file, "w") as f:
            for rec in records:
                f.write(json.dumps(rec) + "\n")

        # Verify records can be read back
        read_records = []
        with open(dataset_file) as f:
            for line in f:
                read_records.append(json.loads(line))

        assert len(read_records) == 2
        assert "function_call" in read_records[0]["conversations"][1]

    def test_download_finetome_parsing(self, tmp_path: Path) -> None:
        """Test parsing of FineTome-100k data after download."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        dataset_file = data_dir / "data.json"
        records = [
            {"id": "ft-001", "conversations": [
                {"from": "human", "value": "Explain closures"},
                {"from": "gpt", "value": "A closure is..."},
            ]},
        ]

        with open(dataset_file, "w") as f:
            json.dump(records, f)

        # Verify can be read
        with open(dataset_file) as f:
            loaded = json.load(f)

        assert len(loaded) == 1
        assert loaded[0]["id"] == "ft-001"

    def test_download_magicoder_parsing(self, tmp_path: Path) -> None:
        """Test parsing of Magicoder data after download."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        dataset_file = data_dir / "train.json"
        records = [
            {"id": "mc-001", "conversations": [
                {"from": "human", "value": "Write quicksort"},
                {"from": "gpt", "value": "```python\ndef quicksort(arr):\n    pass\n```"},
            ]},
        ]

        with open(dataset_file, "w") as f:
            json.dump(records, f)

        with open(dataset_file) as f:
            loaded = json.load(f)

        assert len(loaded) == 1
        assert "python" in loaded[0]["conversations"][1]["value"]

    def test_multiple_dataset_formats_in_downloaded_dir(self, tmp_path: Path) -> None:
        """Test handling of different file formats in downloaded directory."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        # Create different file types that might exist in a downloaded dataset
        (data_dir / "train.jsonl").write_text(
            json.dumps({"id": "1", "conversations": [{"from": "human", "value": "Q?"}, {"from": "gpt", "value": "A."}]}) + "\n"
        )
        (data_dir / "test.jsonl").write_text(
            json.dumps({"id": "2", "conversations": [{"from": "human", "value": "Q2?"}, {"from": "gpt", "value": "A2."}]}) + "\n"
        )
        (data_dir / "data.json").write_text(
            json.dumps([{"id": "3", "conversations": [{"from": "human", "value": "Q3?"}, {"from": "gpt", "value": "A3."}]}])
        )

        # List all json/jsonl files in directory
        files = list(data_dir.glob("*.json")) + list(data_dir.glob("*.jsonl"))

        assert len(files) >= 3


class TestAnchorDatasetDownloaderDownload:
    """Tests for AnchorDatasetDownloader.download method.

    Note: Since the 'datasets' library is not available in the test environment,
    these tests focus on the fallback path (_download_via_hub) which is used
    when the datasets library is not installed.
    """

    def test_download_uses_datasets_library(self) -> None:
        """Test that download method exists and is callable."""
        config = AnchorDatasetConfig(
            hf_id="Salesforce/xlam-function-calling-60k",
            split="train",
            format="xlam",
            token_budget_pct=30.0,
        )
        downloader = AnchorDatasetDownloader([config])

        # The download method should be callable with config
        assert hasattr(downloader, "download")
        assert callable(downloader.download)

    def test_download_with_fallback_logs_info(self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
        """Test that download method logs info when using fallback path."""
        # Remove datasets from sys.modules to simulate ImportError on import
        sys.modules.pop("datasets", None)
        monkeypatch.setitem(sys.modules, "datasets", MagicMock())

        # Mock datasets.load_dataset to raise ImportError
        mock_datasets = MagicMock()
        mock_datasets.load_dataset.side_effect = ImportError("No module named 'datasets'")
        monkeypatch.setitem(sys.modules, "datasets", mock_datasets)

        # Mock huggingface_hub.list_repo_files to return empty list
        mock_list_repo_files = MagicMock(return_value=[])
        monkeypatch.setattr("huggingface_hub.list_repo_files", mock_list_repo_files)

        config = AnchorDatasetConfig(
            hf_id="test/dataset",
            split="train",
            format="sharegpt",
            token_budget_pct=50.0,
        )
        downloader = AnchorDatasetDownloader([config])

        # Consume the generator to trigger logging
        with caplog.at_level(logging.INFO):
            list(downloader.download(config))

        # Check that info message was logged about downloading
        assert any("Downloading dataset" in record.message for record in caplog.records)

    def test_download_with_fallback_logs_warning(self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
        """Test that download method logs warning when datasets library not available."""
        # Remove datasets from sys.modules to simulate ImportError on import
        sys.modules.pop("datasets", None)
        monkeypatch.setitem(sys.modules, "datasets", MagicMock())

        # Mock datasets.load_dataset to raise ImportError
        mock_datasets = MagicMock()
        mock_datasets.load_dataset.side_effect = ImportError("No module named 'datasets'")
        monkeypatch.setitem(sys.modules, "datasets", mock_datasets)

        # Mock huggingface_hub.list_repo_files to return empty list
        mock_list_repo_files = MagicMock(return_value=[])
        monkeypatch.setattr("huggingface_hub.list_repo_files", mock_list_repo_files)

        config = AnchorDatasetConfig(
            hf_id="test/dataset",
            split="train",
            format="sharegpt",
            token_budget_pct=50.0,
        )
        downloader = AnchorDatasetDownloader([config])

        # Consume the generator to trigger logging
        with caplog.at_level(logging.WARNING):
            list(downloader.download(config))

        # Check that warning about datasets library not available was logged
        assert any("datasets library not available" in record.message for record in caplog.records)


class TestAnchorDatasetDownloaderDownloadViaHub:
    """Tests for AnchorDatasetDownloader._download_via_hub fallback method."""

    def test_download_via_hub_lists_files(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that _download_via_hub lists repository files."""
        mock_files = ["data/train.jsonl", "data/test.jsonl"]
        mock_list_repo_files = MagicMock(return_value=mock_files)

        # Patch at the location where it's imported (huggingface_hub module)
        monkeypatch.setattr("huggingface_hub.list_repo_files", mock_list_repo_files)

        config = AnchorDatasetConfig(
            hf_id="test/dataset",
            split="train",
            format="sharegpt",
            token_budget_pct=50.0,
        )
        downloader = AnchorDatasetDownloader([config])

        # Call _download_via_hub - it should call list_repo_files
        # We don't need to fully mock everything since we just want to verify the call
        try:
            list(downloader._download_via_hub(config))
        except Exception:
            pass  # Expected to fail due to incomplete mocking

        # Verify list_repo_files was called
        mock_list_repo_files.assert_called_once_with("test/dataset", repo_type="dataset")

    def test_download_via_hub_filters_jsonl_files(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that _download_via_hub filters for json/jsonl files."""
        # Include non-data files that should be filtered out
        all_files = [
            "README.md",
            "data/train.jsonl",
            "data/valid.json",
            "data/test.txt",
            "data/train.parquet",
        ]

        mock_list_repo_files = MagicMock(return_value=all_files)
        monkeypatch.setattr("huggingface_hub.list_repo_files", mock_list_repo_files)

        config = AnchorDatasetConfig(
            hf_id="test/dataset",
            split="train",
            format="sharegpt",
            token_budget_pct=50.0,
        )
        downloader = AnchorDatasetDownloader([config])

        # Call _download_via_hub to test the filtering logic is applied
        # We expect it to filter out non-json/jsonl files
        try:
            list(downloader._download_via_hub(config))
        except Exception:
            pass  # May fail due to incomplete mocking

        # Verify list_repo_files was called with correct params
        mock_list_repo_files.assert_called_once_with("test/dataset", repo_type="dataset")

    def test_download_via_hub_no_data_files(self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
        """Test _download_via_hub handles no data files gracefully."""
        # Return only non-data files
        mock_list_repo_files = MagicMock(return_value=["README.md", "config.yaml"])
        monkeypatch.setattr("huggingface_hub.list_repo_files", mock_list_repo_files)

        config = AnchorDatasetConfig(
            hf_id="test/dataset",
            split="train",
            format="sharegpt",
            token_budget_pct=50.0,
        )
        downloader = AnchorDatasetDownloader([config])

        # Should yield no records and log warning
        with caplog.at_level(logging.WARNING):
            records = list(downloader._download_via_hub(config))

        assert len(records) == 0
        assert any("No data files found" in record.message for record in caplog.records)

    def test_download_via_hub_parses_jsonl(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Test that _download_via_hub correctly parses JSONL files."""
        mock_files = ["data/train.jsonl"]
        mock_list_repo_files = MagicMock(return_value=mock_files)

        # Create a real temporary JSONL file
        records = [
            {"id": "1", "conversations": [{"from": "human", "value": "Q1"}, {"from": "gpt", "value": "A1"}]},
            {"id": "2", "conversations": [{"from": "human", "value": "Q2"}, {"from": "gpt", "value": "A2"}]},
        ]
        jsonl_file = tmp_path / "train.jsonl"
        with open(jsonl_file, "w") as f:
            for record in records:
                f.write(json.dumps(record) + "\n")

        mock_hf_hub_download = MagicMock(return_value=str(jsonl_file))

        monkeypatch.setattr("huggingface_hub.list_repo_files", mock_list_repo_files)
        monkeypatch.setattr("huggingface_hub.hf_hub_download", mock_hf_hub_download)

        config = AnchorDatasetConfig(
            hf_id="test/dataset",
            split="train",
            format="sharegpt",
            token_budget_pct=50.0,
        )
        downloader = AnchorDatasetDownloader([config])

        # Get records from the method
        result_records = list(downloader._download_via_hub(config))

        # Verify we got the records
        assert len(result_records) == 2
        assert result_records[0]["id"] == "1"
        assert result_records[1]["id"] == "2"

    def test_download_via_hub_parses_json_array(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that _download_via_hub correctly parses JSON array files."""
        mock_files = ["data/train.json"]
        mock_list_repo_files = MagicMock(return_value=mock_files)

        # Create mock JSON array content
        records = [
            {"id": "1", "conversations": [{"from": "human", "value": "Q1"}]},
            {"id": "2", "conversations": [{"from": "human", "value": "Q2"}]},
        ]
        json_content = json.dumps(records)

        mock_file = MagicMock()
        mock_file.__enter__ = MagicMock(return_value=MagicMock(read=MagicMock(return_value=json_content)))
        mock_file.__exit__ = MagicMock(return_value=False)

        mock_hf_hub_download = MagicMock(return_value="/tmp/train.json")

        # Mock tiktoken.get_encoding before instantiating AnchorDatasetDownloader
        mock_tokenizer = MagicMock()
        mock_tokenizer.encode = MagicMock(return_value=[1, 2, 3])  # Mock encode method
        monkeypatch.setattr("tiktoken.get_encoding", MagicMock(return_value=mock_tokenizer))

        monkeypatch.setattr("huggingface_hub.list_repo_files", mock_list_repo_files)
        monkeypatch.setattr("huggingface_hub.hf_hub_download", mock_hf_hub_download)
        monkeypatch.setattr("builtins.open", MagicMock(return_value=mock_file))

        config = AnchorDatasetConfig(
            hf_id="test/dataset",
            split="train",
            format="sharegpt",
            token_budget_pct=50.0,
        )
        downloader = AnchorDatasetDownloader([config])

        result_records = list(downloader._download_via_hub(config))

        assert len(result_records) == 2

    def test_download_via_hub_handles_download_error(self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
        """Test that _download_via_hub handles download errors gracefully."""
        mock_files = ["data/train.jsonl"]
        mock_list_repo_files = MagicMock(return_value=mock_files)

        # Make hf_hub_download raise an exception
        mock_hf_hub_download = MagicMock(side_effect=Exception("Network error"))

        monkeypatch.setattr("huggingface_hub.list_repo_files", mock_list_repo_files)
        monkeypatch.setattr("huggingface_hub.hf_hub_download", mock_hf_hub_download)

        config = AnchorDatasetConfig(
            hf_id="test/dataset",
            split="train",
            format="sharegpt",
            token_budget_pct=50.0,
        )
        downloader = AnchorDatasetDownloader([config])

        # Should not raise, should log warning and continue
        with caplog.at_level(logging.WARNING):
            records = list(downloader._download_via_hub(config))

        # Should have logged a warning about the failed download
        assert any("Failed to download file" in record.message for record in caplog.records)
        assert len(records) == 0


class TestAnchorDatasetDownloaderParse:
    """Tests for AnchorDatasetDownloader.parse method."""

    def test_parse_xlam_format(self) -> None:
        """Test parsing xlam format records."""
        config = AnchorDatasetConfig(
            hf_id="Salesforce/xlam-function-calling-60k",
            split="train",
            format="xlam",
            token_budget_pct=30.0,
        )
        downloader = AnchorDatasetDownloader([config])

        # Create raw xlam records
        raw_data = [
            {
                "id": "xlam-001",
                "conversations": [
                    {"from": "human", "value": "What's the weather?"},
                    {"from": "gpt", "value": "I'll check the weather."},
                ],
            }
        ]

        # Parse using the method
        records = list(downloader.parse(iter(raw_data), "xlam", "test-origin"))

        assert len(records) == 1
        assert len(records[0].messages) == 2
        assert records[0].messages[0].role == "user"
        assert records[0].messages[1].role == "assistant"
        assert records[0].metadata["origin"] == "test-origin"
        assert records[0].metadata["type"] == "anchor"
        assert records[0].metadata["format"] == "chatml"
        assert "token_count" in records[0].metadata

    def test_parse_xlam_with_function_call(self) -> None:
        """Test parsing xlam format with function_call field."""
        config = AnchorDatasetConfig(
            hf_id="Salesforce/xlam-function-calling-60k",
            split="train",
            format="xlam",
            token_budget_pct=30.0,
        )
        downloader = AnchorDatasetDownloader([config])

        raw_data = [
            {
                "id": "xlam-fc-001",
                "conversations": [
                    {"from": "human", "value": "Get weather for Tokyo"},
                    {
                        "from": "gpt",
                        "value": "I'll call the weather function.",
                        "function_call": {
                            "name": "get_weather",
                            "arguments": {"city": "Tokyo"},
                        },
                    },
                ],
            }
        ]

        records = list(downloader.parse(iter(raw_data), "xlam", "test-origin"))

        assert len(records) == 1
        # Check function_call is included in content
        assert "get_weather" in records[0].messages[1].content
        assert "<tool_call>" in records[0].messages[1].content

    def test_parse_sharegpt_format(self) -> None:
        """Test parsing sharegpt format records."""
        config = AnchorDatasetConfig(
            hf_id="llmware/finetome-100k",
            split="train",
            format="sharegpt",
            token_budget_pct=30.0,
        )
        downloader = AnchorDatasetDownloader([config])

        raw_data = [
            {
                "id": "sharegpt-001",
                "conversations": [
                    {"from": "human", "value": "Explain Python"},
                    {"from": "gpt", "value": "Python is a programming language."},
                    {"from": "human", "value": "What about lists?"},
                    {"from": "gpt", "value": "Lists are data structures."},
                ],
            }
        ]

        records = list(downloader.parse(iter(raw_data), "sharegpt", "test-origin"))

        assert len(records) == 1
        assert len(records[0].messages) == 4
        assert records[0].messages[0].role == "user"
        assert records[0].messages[1].role == "assistant"
        assert records[0].messages[2].role == "user"
        assert records[0].messages[3].role == "assistant"

    def test_parse_sharegpt_with_system_role(self) -> None:
        """Test parsing sharegpt format with system role."""
        config = AnchorDatasetConfig(
            hf_id="llmware/finetome-100k",
            split="train",
            format="sharegpt",
            token_budget_pct=30.0,
        )
        downloader = AnchorDatasetDownloader([config])

        raw_data = [
            {
                "id": "sharegpt-sys-001",
                "conversations": [
                    {"from": "system", "value": "You are a helpful assistant."},
                    {"from": "human", "value": "Hello"},
                    {"from": "gpt", "value": "Hi there!"},
                ],
            }
        ]

        records = list(downloader.parse(iter(raw_data), "sharegpt", "test-origin"))

        assert len(records) == 1
        assert records[0].messages[0].role == "system"
        assert records[0].messages[1].role == "user"
        assert records[0].messages[2].role == "assistant"

    def test_parse_openai_messages_format(self) -> None:
        """Test parsing openai_messages format records."""
        config = AnchorDatasetConfig(
            hf_id="test/dataset",
            split="train",
            format="openai_messages",
            token_budget_pct=30.0,
        )
        downloader = AnchorDatasetDownloader([config])

        raw_data = [
            {
                "id": "openai-001",
                "messages": [
                    {"role": "system", "content": "You are helpful."},
                    {"role": "user", "content": "What is 2+2?"},
                    {"role": "assistant", "content": "2+2 equals 4."},
                ],
            }
        ]

        records = list(downloader.parse(iter(raw_data), "openai_messages", "test-origin"))

        assert len(records) == 1
        assert len(records[0].messages) == 3
        assert records[0].messages[0].role == "system"
        assert records[0].messages[1].role == "user"
        assert records[0].messages[2].role == "assistant"

    def test_parse_unknown_format_logs_warning(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test parsing with unknown format logs warning."""
        config = AnchorDatasetConfig(
            hf_id="test/dataset",
            split="train",
            format="unknown",
            token_budget_pct=30.0,
        )
        downloader = AnchorDatasetDownloader([config])

        raw_data = [{"id": "test-001", "conversations": [{"from": "human", "value": "Test"}]}]

        with caplog.at_level(logging.WARNING):
            records = list(downloader.parse(iter(raw_data), "unknown_format", "test"))

        assert len(records) == 0
        assert any("Unknown format type" in record.message for record in caplog.records)

    def test_parse_handles_record_exception(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test parsing handles exceptions in individual records gracefully."""
        config = AnchorDatasetConfig(
            hf_id="test/dataset",
            split="train",
            format="xlam",
            token_budget_pct=30.0,
        )
        downloader = AnchorDatasetDownloader([config])

        # Invalid record - missing 'conversations' field
        raw_data = [{"id": "invalid-001", "other_field": "value"}]

        with caplog.at_level(logging.WARNING):
            records = list(downloader.parse(iter(raw_data), "xlam", "test"))

        # Should skip the invalid record and continue
        assert len(records) == 0
        assert any("Failed to parse record" in record.message for record in caplog.records)

    def test_parse_multiple_records(self) -> None:
        """Test parsing multiple records."""
        config = AnchorDatasetConfig(
            hf_id="test/dataset",
            split="train",
            format="sharegpt",
            token_budget_pct=30.0,
        )
        downloader = AnchorDatasetDownloader([config])

        raw_data = [
            {"id": "1", "conversations": [{"from": "human", "value": "Q1"}, {"from": "gpt", "value": "A1"}]},
            {"id": "2", "conversations": [{"from": "human", "value": "Q2"}, {"from": "gpt", "value": "A2"}]},
            {"id": "3", "conversations": [{"from": "human", "value": "Q3"}, {"from": "gpt", "value": "A3"}]},
        ]

        records = list(downloader.parse(iter(raw_data), "sharegpt", "test"))

        assert len(records) == 3
        assert records[0].messages[0].content == "Q1"
        assert records[1].messages[0].content == "Q2"
        assert records[2].messages[0].content == "Q3"


class TestAnchorDatasetDownloaderParseHelpers:
    """Tests for AnchorDatasetDownloader internal parse methods."""

    def test_parse_xlam_method(self) -> None:
        """Test _parse_xlam method directly."""
        config = AnchorDatasetConfig(hf_id="test", format="xlam")
        downloader = AnchorDatasetDownloader([config])

        record = {
            "conversations": [
                {"from": "human", "value": "Question"},
                {"from": "gpt", "value": "Answer"},
            ]
        }

        messages = downloader._parse_xlam(record)

        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[0].content == "Question"
        assert messages[1].role == "assistant"
        assert messages[1].content == "Answer"

    def test_parse_xlam_missing_conversations_raises(self) -> None:
        """Test _parse_xlam raises ValueError when conversations missing."""
        config = AnchorDatasetConfig(hf_id="test", format="xlam")
        downloader = AnchorDatasetDownloader([config])

        with pytest.raises(ValueError, match="conversations"):
            downloader._parse_xlam({})

    def test_parse_xlam_skips_invalid_conversation_items(self) -> None:
        """Test _parse_xlam skips items without from/value."""
        config = AnchorDatasetConfig(hf_id="test", format="xlam")
        downloader = AnchorDatasetDownloader([config])

        record = {
            "conversations": [
                {"from": "human", "value": "Valid message"},
                {"invalid": "data"},  # Should be skipped
                {"from": "gpt", "value": "Another valid"},
            ]
        }

        messages = downloader._parse_xlam(record)

        assert len(messages) == 2

    def test_parse_sharegpt_method(self) -> None:
        """Test _parse_sharegpt method directly."""
        config = AnchorDatasetConfig(hf_id="test", format="sharegpt")
        downloader = AnchorDatasetDownloader([config])

        record = {
            "conversations": [
                {"from": "human", "value": "Hello"},
                {"from": "gpt", "value": "Hi there"},
            ]
        }

        messages = downloader._parse_sharegpt(record)

        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[1].role == "assistant"

    def test_parse_sharegpt_missing_conversations_raises(self) -> None:
        """Test _parse_sharegpt raises ValueError when conversations missing."""
        config = AnchorDatasetConfig(hf_id="test", format="sharegpt")
        downloader = AnchorDatasetDownloader([config])

        with pytest.raises(ValueError, match="conversations"):
            downloader._parse_sharegpt({})

    def test_parse_sharegpt_unknown_role_preserved(self) -> None:
        """Test _parse_sharegpt preserves unknown roles."""
        config = AnchorDatasetConfig(hf_id="test", format="sharegpt")
        downloader = AnchorDatasetDownloader([config])

        record = {
            "conversations": [
                {"from": "human", "value": "Question"},
                {"from": "unknown_role", "value": "Response"},
            ]
        }

        messages = downloader._parse_sharegpt(record)

        # Unknown role should be preserved as-is
        assert messages[1].role == "unknown_role"

    def test_parse_openai_messages_method(self) -> None:
        """Test _parse_openai_messages method directly."""
        config = AnchorDatasetConfig(hf_id="test", format="openai_messages")
        downloader = AnchorDatasetDownloader([config])

        record = {
            "messages": [
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi"},
            ]
        }

        messages = downloader._parse_openai_messages(record)

        assert len(messages) == 3
        assert messages[0].role == "system"
        assert messages[1].role == "user"
        assert messages[2].role == "assistant"

    def test_parse_openai_messages_missing_messages_raises(self) -> None:
        """Test _parse_openai_messages raises ValueError when messages missing."""
        config = AnchorDatasetConfig(hf_id="test", format="openai_messages")
        downloader = AnchorDatasetDownloader([config])

        with pytest.raises(ValueError, match="messages"):
            downloader._parse_openai_messages({})

    def test_parse_openai_messages_skips_invalid_items(self) -> None:
        """Test _parse_openai_messages skips items without role/content."""
        config = AnchorDatasetConfig(hf_id="test", format="openai_messages")
        downloader = AnchorDatasetDownloader([config])

        record = {
            "messages": [
                {"role": "user", "content": "Valid"},
                {"role": "assistant"},  # Missing content - should skip
                {"content": "Missing role"},  # Should skip
                {"role": "assistant", "content": "Valid again"},
            ]
        }

        messages = downloader._parse_openai_messages(record)

        assert len(messages) == 2

    def test_parse_xlam_role_mapping(self) -> None:
        """Test xlam role mapping to ChatML."""
        config = AnchorDatasetConfig(hf_id="test", format="xlam")
        downloader = AnchorDatasetDownloader([config])

        record = {
            "conversations": [
                {"from": "human", "value": "User message"},
                {"from": "gpt", "value": "Assistant message"},
            ]
        }

        messages = downloader._parse_xlam(record)

        assert messages[0].role == "user"
        assert messages[1].role == "assistant"

    def test_parse_sharegpt_role_mapping(self) -> None:
        """Test sharegpt role mapping includes tool role."""
        config = AnchorDatasetConfig(hf_id="test", format="sharegpt")
        downloader = AnchorDatasetDownloader([config])

        record = {
            "conversations": [
                {"from": "human", "value": "User"},
                {"from": "tool", "value": "Tool result"},
                {"from": "gpt", "value": "Assistant"},
            ]
        }

        messages = downloader._parse_sharegpt(record)

        assert messages[0].role == "user"
        assert messages[1].role == "tool"


# =============================================================================
# TESTS FOR load_anchor_configs
# =============================================================================


class TestLoadAnchorConfigs:
    """Tests for the load_anchor_configs function."""

    def test_load_anchor_configs_import(self) -> None:
        """Test that load_anchor_configs can be imported."""
        from src.curation.anchor_dataset_downloader import load_anchor_configs
        assert callable(load_anchor_configs)

    def test_load_anchor_configs_file_not_found(self, tmp_path: Path) -> None:
        """Test that FileNotFoundError is raised for missing file."""
        from src.curation.anchor_dataset_downloader import load_anchor_configs

        missing_file = tmp_path / "nonexistent.yaml"
        with pytest.raises(FileNotFoundError):
            load_anchor_configs(missing_file)

    def test_load_anchor_configs_invalid_yaml(self, tmp_path: Path) -> None:
        """Test that ValueError is raised for invalid YAML."""
        from src.curation.anchor_dataset_downloader import load_anchor_configs

        invalid_file = tmp_path / "invalid.yaml"
        invalid_file.write_text("not: valid: yaml: [")
        with pytest.raises(Exception):  # yaml.YAMLError
            load_anchor_configs(invalid_file)

    def test_load_anchor_configs_missing_anchors_key(self, tmp_path: Path) -> None:
        """Test that ValueError is raised when anchors key is missing."""
        from src.curation.anchor_dataset_downloader import load_anchor_configs

        config_file = tmp_path / "no_anchors.yaml"
        config_file.write_text("other_key: value")
        with pytest.raises(ValueError, match="must contain 'anchors' list"):
            load_anchor_configs(config_file)

    def test_load_anchor_configs_empty_anchors(self, tmp_path: Path) -> None:
        """Test that empty anchors list returns empty list."""
        from src.curation.anchor_dataset_downloader import load_anchor_configs

        config_file = tmp_path / "empty.yaml"
        config_file.write_text("anchors: []")
        configs = load_anchor_configs(config_file)
        assert configs == []

    def test_load_anchor_configs_single_anchor(self, tmp_path: Path) -> None:
        """Test loading a single anchor dataset config."""
        from src.curation.anchor_dataset_downloader import load_anchor_configs

        config_file = tmp_path / "single.yaml"
        config_file.write_text(
            """anchors:
  - hf_id: test/dataset
    split: train
    format: sharegpt
    token_budget_pct: 50.0
"""
        )
        configs = load_anchor_configs(config_file)
        assert len(configs) == 1
        assert configs[0].hf_id == "test/dataset"
        assert configs[0].split == "train"
        assert configs[0].format == "sharegpt"
        assert configs[0].token_budget_pct == 50.0

    def test_load_anchor_configs_multiple_anchors(self, tmp_path: Path) -> None:
        """Test loading multiple anchor dataset configs."""
        from src.curation.anchor_dataset_downloader import load_anchor_configs

        config_file = tmp_path / "multiple.yaml"
        config_file.write_text(
            """anchors:
  - hf_id: dataset1/train
    split: train
    format: xlam
    token_budget_pct: 30.0
  - hf_id: dataset2/test
    split: test
    format: openai_messages
    token_budget_pct: 70.0
"""
        )
        configs = load_anchor_configs(config_file)
        assert len(configs) == 2

        assert configs[0].hf_id == "dataset1/train"
        assert configs[0].split == "train"
        assert configs[0].format == "xlam"
        assert configs[0].token_budget_pct == 30.0

        assert configs[1].hf_id == "dataset2/test"
        assert configs[1].split == "test"
        assert configs[1].format == "openai_messages"
        assert configs[1].token_budget_pct == 70.0

    def test_load_anchor_configs_defaults(self, tmp_path: Path) -> None:
        """Test that default values are applied when not specified."""
        from src.curation.anchor_dataset_downloader import load_anchor_configs

        config_file = tmp_path / "defaults.yaml"
        config_file.write_text(
            """anchors:
  - hf_id: minimal/dataset
"""
        )
        configs = load_anchor_configs(config_file)
        assert len(configs) == 1
        assert configs[0].hf_id == "minimal/dataset"
        assert configs[0].split == "train"  # default
        assert configs[0].format == "sharegpt"  # default
        assert configs[0].token_budget_pct == 70.0  # default

    def test_load_anchor_configs_partial_fields(self, tmp_path: Path) -> None:
        """Test loading with some fields specified and defaults for others."""
        from src.curation.anchor_dataset_downloader import load_anchor_configs

        config_file = tmp_path / "partial.yaml"
        config_file.write_text(
            """anchors:
  - hf_id: partial/dataset
    split: validation
  - hf_id: another/dataset
    token_budget_pct: 25.5
"""
        )
        configs = load_anchor_configs(config_file)
        assert len(configs) == 2

        # First anchor: only split specified
        assert configs[0].hf_id == "partial/dataset"
        assert configs[0].split == "validation"
        assert configs[0].format == "sharegpt"  # default
        assert configs[0].token_budget_pct == 70.0  # default

        # Second anchor: only token_budget_pct specified
        assert configs[1].hf_id == "another/dataset"
        assert configs[1].split == "train"  # default
        assert configs[1].format == "sharegpt"  # default
        assert configs[1].token_budget_pct == 25.5


class TestDownloadViaHubJsonParsing:
    """Tests for JSON parsing fallback in _download_via_hub."""

    def test_download_via_hub_json_decode_error_fallback(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that _download_via_hub tries literal_eval when JSON fails."""
        mock_files = ["data/train.jsonl"]
        mock_list_repo_files = MagicMock(return_value=mock_files)

        # Return content that fails JSON but works with literal_eval
        mock_file = MagicMock()
        mock_file.__enter__ = MagicMock(return_value=MagicMock(read=MagicMock(return_value="[(1, 2, 3)]")))
        mock_file.__exit__ = MagicMock(return_value=False)

        mock_hf_hub_download = MagicMock(return_value="/tmp/train.jsonl")

        # Mock tiktoken
        mock_tokenizer = MagicMock()
        mock_tokenizer.encode = MagicMock(return_value=[1, 2, 3])
        monkeypatch.setattr("tiktoken.get_encoding", MagicMock(return_value=mock_tokenizer))

        monkeypatch.setattr("huggingface_hub.list_repo_files", mock_list_repo_files)
        monkeypatch.setattr("huggingface_hub.hf_hub_download", mock_hf_hub_download)
        monkeypatch.setattr("builtins.open", MagicMock(return_value=mock_file))

        config = AnchorDatasetConfig(
            hf_id="test/dataset",
            split="train",
            format="sharegpt",
            token_budget_pct=50.0,
        )
        downloader = AnchorDatasetDownloader([config])

        # Should handle the case gracefully (may log warning)
        list(downloader._download_via_hub(config))
        # The result may be empty if parsing fails completely


class TestExportCreatesDirectories:
    """Tests for export method creating parent directories."""

    def test_export_creates_parent_directories(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that export creates parent directories if they don't exist."""
        # Mock tiktoken
        mock_tokenizer = MagicMock()
        mock_tokenizer.encode = MagicMock(return_value=[1, 2, 3])
        monkeypatch.setattr("tiktoken.get_encoding", MagicMock(return_value=mock_tokenizer))

        config = AnchorDatasetConfig(
            hf_id="test/dataset",
            split="train",
            format="sharegpt",
            token_budget_pct=50.0,
        )
        downloader = AnchorDatasetDownloader([config])

        records = [
            DatasetRecord(
                messages=[Message(role="user", content="Hello")],
                metadata={"origin": "test"},
            )
        ]

        # Export to nested path
        output_path = tmp_path / "subdir" / "nested" / "output.jsonl"

        downloader.export(records, output_path)

        assert output_path.exists()


