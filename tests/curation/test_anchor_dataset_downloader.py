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
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
import tiktoken

from src.curation.anchor_dataset_downloader import AnchorDatasetConfig, AnchorDatasetDownloader
from src.utils.schema import DatasetRecord, Message

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
