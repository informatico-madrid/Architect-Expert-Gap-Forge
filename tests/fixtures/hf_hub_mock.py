#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Architect-Expert-Gap-Forge (AEGF) - HuggingFace Hub Mock Utilities

Mock utilities for testing code that interacts with HuggingFace Hub and
the datasets library. Provides fake implementations for:
- huggingface_hub.list_repo_files
- huggingface_hub.hf_hub_download
- datasets.load_dataset

Location: tests/fixtures/hf_hub_mock.py
SPDX-License-Identifier: Apache-2.0
Copyright 2026 AEGF
"""

from __future__ import annotations

import importlib.machinery
import sys
import types
from typing import Any, Iterator


# =============================================================================
# REGISTRY FOR MOCK DATA
# =============================================================================

# Registry to store mock data per repository ID
_MOCK_DATA: dict[str, dict[str, Any]] = {}
_REGISTERED: list[str] = []


def register_mock_dataset(
    repo_id: str,
    files: dict[str, list[dict[str, Any]]],
) -> None:
    """Register mock data for a HuggingFace dataset.

    Args:
        repo_id: The HuggingFace repository ID (e.g., 'Salesforce/xlam-function-calling-60k')
        files: Dictionary mapping file names to lists of records
               Example: {"data.jsonl": [{"id": "1", "conversations": [...]}]}
    """
    _MOCK_DATA[repo_id] = files


def clear_mock_data() -> None:
    """Clear all registered mock data."""
    global _MOCK_DATA
    _MOCK_DATA = {}


# =============================================================================
# MOCK FUNCTIONS
# =============================================================================


def mock_list_repo_files(repo_id: str, repo_type: str = "dataset") -> list[str]:
    """Mock implementation of huggingface_hub.list_repo_files.

    Args:
        repo_id: The repository ID
        repo_type: The repository type (default: "dataset")

    Returns:
        List of file names in the repository
    """
    if repo_id in _MOCK_DATA:
        return list(_MOCK_DATA[repo_id].keys())
    return []


def mock_hf_hub_download(
    repo_id: str,
    filename: str,
    repo_type: str = "dataset",
    **kwargs: Any,
) -> str:
    """Mock implementation of huggingface_hub.hf_hub_download.

    Args:
        repo_id: The repository ID
        filename: The file name to download
        repo_type: The repository type (default: "dataset")
        **kwargs: Additional arguments (ignored in mock)

    Returns:
        A temporary file path containing the mock data (as JSON)

    Raises:
        FileNotFoundError: If the repo_id or filename is not registered
    """
    if repo_id not in _MOCK_DATA:
        raise FileNotFoundError(f"Repository not found: {repo_id}")

    if filename not in _MOCK_DATA[repo_id]:
        raise FileNotFoundError(f"File not found in {repo_id}: {filename}")

    # Return a special path that our mock file reader will intercept
    # Format: MOCK:repo_id:filename
    return f"MOCK:{repo_id}:{filename}"


def mock_load_dataset(
    path: str,
    name: str | None = None,
    split: str | None = None,
    streaming: bool = False,
    **kwargs: Any,
) -> Any:
    """Mock implementation of datasets.load_dataset.

    Args:
        path: The dataset path or name
        name: The dataset configuration name (optional)
        split: The split to load (optional)
        streaming: Whether to return an iterable (default: False)
        **kwargs: Additional arguments (ignored in mock)

    Returns:
        A mock dataset object with either __iter__ (for streaming) or data

    Raises:
        FileNotFoundError: If the dataset is not registered
    """
    if path not in _MOCK_DATA:
        raise FileNotFoundError(f"Dataset not found: {path}")

    files = _MOCK_DATA[path]

    # Combine all records from all files
    all_records = []
    for file_records in files.values():
        all_records.extend(file_records)

    if streaming:
        return MockStreamingDataset(all_records)
    else:
        return MockDataset(all_records)


# =============================================================================
# MOCK CLASSES
# =============================================================================


class MockStreamingDataset:
    """Mock streaming dataset for testing."""

    def __init__(self, records: list[dict[str, Any]]) -> None:
        self._records = records

    def __iter__(self) -> Iterator[dict[str, Any]]:
        return iter(self._records)

    def __len__(self) -> int:
        return len(self._records)


class MockDataset:
    """Mock dataset (non-streaming) for testing."""

    def __init__(self, records: list[dict[str, Any]]) -> None:
        self._records = records
        self._data = {"train": records} if records else {}

    def __getitem__(self, split: str) -> list[dict[str, Any]]:
        return self._data.get(split, [])

    def __iter__(self) -> Iterator[dict[str, Any]]:
        return iter(self._records)


# =============================================================================
# MODULE INJECTION
# =============================================================================


def enable_fake_huggingface() -> None:
    """Insert fake HuggingFace Hub modules into sys.modules.

    After calling this function, importing code that uses huggingface_hub
    and datasets will use the mock implementations.
    """
    global _REGISTERED

    # ---- huggingface_hub ----
    hf_hub = types.ModuleType("huggingface_hub")
    hf_hub.__spec__ = importlib.machinery.ModuleSpec(
        "huggingface_hub", hf_hub, origin="huggingface_hub.py"
    )

    hf_hub.list_repo_files = mock_list_repo_files
    hf_hub.hf_hub_download = mock_hf_hub_download

    # ---- datasets ----
    datasets = types.ModuleType("datasets")
    datasets.__spec__ = importlib.machinery.ModuleSpec(
        "datasets", datasets, origin="datasets.py"
    )

    datasets.load_dataset = mock_load_dataset

    # Register modules
    sys.modules["huggingface_hub"] = hf_hub
    sys.modules["datasets"] = datasets
    _REGISTERED.extend(["huggingface_hub", "datasets"])


def disable_fake_huggingface() -> None:
    """Remove previously injected fake modules from sys.modules."""
    global _REGISTERED

    for name in list(_REGISTERED):
        sys.modules.pop(name, None)
        _REGISTERED.remove(name)

    clear_mock_data()


# =============================================================================
# PYTEST FIXTURES
# =============================================================================


def create_xlam_fixture() -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Create fixture data for xlam-function-calling-60k dataset.

    Returns:
        Dictionary suitable for register_mock_dataset
    """
    return {
        "data.jsonl": [
            {
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
        ]
    }


def create_finetome_fixture() -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Create fixture data for FineTome-100k dataset.

    Returns:
        Dictionary suitable for register_mock_dataset
    """
    return {
        "train.json": [
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
        ]
    }


def create_magicoder_fixture() -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Create fixture data for Magicoder dataset.

    Returns:
        Dictionary suitable for register_mock_dataset
    """
    return {
        "train.json": [
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
        ]
    }


def create_openai_messages_fixture() -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Create fixture data for OpenAI Messages format dataset.

    Returns:
        Dictionary suitable for register_mock_dataset
    """
    return {
        "train.jsonl": [
            {
                "id": "openai-001",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "What is 2+2?"},
                    {"role": "assistant", "content": "2+2 equals 4."},
                ],
            },
            {
                "id": "openai-002",
                "messages": [
                    {"role": "system", "content": "You are a coding assistant."},
                    {"role": "user", "content": "Write hello world in Python"},
                    {
                        "role": "assistant",
                        "content": "```python\nprint('Hello, World!')\n```",
                    },
                ],
            },
        ]
    }


__all__ = [
    "register_mock_dataset",
    "clear_mock_data",
    "mock_list_repo_files",
    "mock_hf_hub_download",
    "mock_load_dataset",
    "MockStreamingDataset",
    "MockDataset",
    "enable_fake_huggingface",
    "disable_fake_huggingface",
    "create_xlam_fixture",
    "create_finetome_fixture",
    "create_magicoder_fixture",
    "create_openai_messages_fixture",
]
