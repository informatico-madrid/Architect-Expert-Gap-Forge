# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Mock utilities for HuggingFace Hub API.

Provides mock implementations for:
- huggingface_hub.list_repo_files
- huggingface_hub.snapshot_download
- datasets.load_dataset

Usage:
    from tests.utils.mocks import MockHuggingFaceHub
    mock_hf = MockHuggingFaceHub()
    mock_hf.setup_files(["data/train.jsonl", "data/test.jsonl"])
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch
from unittest.mock import patch as mock_patch


class MockHuggingFaceHub:
    """Mock implementation of HuggingFace Hub services for testing."""

    def __init__(self):
        """Initialize mock with default configurations."""
        self._files: list[str] = []
        self._downloaded_data: dict[str, list[dict[str, Any]]] = {}
        self._mock_list_repo_files: MagicMock | None = None
        self._mock_snapshot_download: MagicMock | None = None
        self._mock_load_dataset: MagicMock | None = None

    def setup_files(self, files: list[str]) -> None:
        """
        Configure the mock to return specific files.

        Args:
            files: List of file paths that the mock will return from list_repo_files
        """
        self._files = files

    def setup_download_data(
        self,
        train_data: list[dict[str, Any]] | None = None,
        test_data: list[dict[str, Any]] | None = None,
    ) -> None:
        """
        Configure mock download data.

        Args:
            train_data: Data to return for train split
            test_data: Data to return for test split
        """
        if train_data:
            self._downloaded_data["train"] = train_data
        if test_data:
            self._downloaded_data["test"] = test_data

    def create_patchers(self) -> dict[str, MagicMock]:
        """
        Create and return patchers for all HuggingFace services.

        Returns:
            Dictionary with patchers for:
            - 'list_repo_files': Mock for huggingface_hub.list_repo_files
            - 'snapshot_download': Mock for huggingface_hub.snapshot_download
            - 'load_dataset': Mock for datasets.load_dataset
        """
        # Create list_repo_files mock
        self._mock_list_repo_files = MagicMock(return_value=self._files)

        # Create snapshot_download mock - returns a temporary directory structure
        self._mock_snapshot_download = MagicMock()

        # Create load_dataset mock - returns a mock dataset object
        self._mock_load_dataset = MagicMock()

        return {
            "list_repo_files": self._mock_list_repo_files,
            "snapshot_download": self._mock_snapshot_download,
            "load_dataset": self._mock_load_dataset,
        }

    def patch_import(self, monkeypatch: Any) -> None:
        """
        Patch the __import__ function to raise ImportError for datasets.

        Args:
            monkeypatch: pytest monkeypatch fixture
        """

        def raise_import_error(name: str, *args: Any, **kwargs: Any) -> None:
            if name == "datasets":
                raise ImportError("No module named 'datasets'")
            # Use real import for other modules
            import __import__

            return __import__(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", raise_import_error)

    def setup_load_dataset_mock(
        self,
        train_data: list[dict[str, Any]] | None = None,
        test_data: list[dict[str, Any]] | None = None,
    ) -> MagicMock:
        """
        Setup load_dataset mock to return a mock dataset object.

        Args:
            train_data: Data for train split
            test_data: Data for test split

        Returns:
            Mock dataset object
        """
        mock_dataset = MagicMock()

        # Setup splits
        if train_data is not None:
            mock_dataset.__getitem__ = lambda key, idx: train_data[idx] if idx < len(train_data) else {}
            mock_dataset.keys = lambda: ["train"] if train_data else []
            mock_dataset["train"] = mock_dataset

        if test_data is not None:
            mock_dataset["test"] = mock_dataset

        self._mock_load_dataset.return_value = mock_dataset
        return mock_dataset


class MockHuggingFaceContext:
    """
    Context manager for HuggingFace mocking.

    Provides a clean way to set up and tear down mocks in tests.

    Example:
        with MockHuggingFaceContext() as mock_hf:
            mock_hf.setup_files(["data/train.jsonl"])
            # Your test code here
    """

    def __init__(self):
        """Initialize mock context."""
        self.mock_hub = MockHuggingFaceHub()
        self._patchers: dict[str, Any] = {}

    def __enter__(self) -> MockHuggingFaceContext:
        """Enter context and set up patches."""
        # Get patchers
        self._patchers = self.mock_hub.create_patchers()

        # Apply patches
        from huggingface_hub import list_repo_files, snapshot_download
        from datasets import load_dataset

        # Patch list_repo_files
        self._patchers["list_repo_files"].__enter__ = lambda self: None
        self._patchers["list_repo_files"].__exit__ = lambda self, *args: None

        # Patch snapshot_download
        self._patchers["snapshot_download"].__enter__ = lambda self: None
        self._patchers["snapshot_download"].__exit__ = lambda self, *args: None

        # Patch load_dataset
        self._patchers["load_dataset"].__enter__ = lambda self: None
        self._patchers["load_dataset"].__exit__ = lambda self, *args: None

        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context and clean up."""
        pass

    def setup_files(self, files: list[str]) -> None:
        """Configure mock to return specific files."""
        self.mock_hub.setup_files(files)

    def setup_download_data(
        self,
        train_data: list[dict[str, Any]] | None = None,
        test_data: list[dict[str, Any]] | None = None,
    ) -> None:
        """Configure mock download data."""
        self.mock_hub.setup_download_data(train_data, test_data)
