#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Architect-Expert-Gap-Forge (AEGF) - HuggingFace Mock Fixtures

Unit test fixtures for mocking HuggingFace Hub services.
Provides comprehensive mocks for list_repo_files, snapshot_download, and load_dataset.

Location: tests/fixtures/huggingface_mocks.py
SPDX-License-Identifier: Apache-2.0
Copyright 2026 AEGF
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch


class HuggingFaceMock:
    """
    Comprehensive mock for HuggingFace Hub services.
    
    Provides mocks for:
    - list_repo_files: Lists repository files
    - snapshot_download: Downloads repository snapshot
    - load_dataset: Loads datasets from local files
    
    Usage:
        with HuggingFaceMock() as mock:
            # Use the mock in your tests
            mock.setup_dataset("test/dataset", {"train": "data/train.jsonl"})
    """

    def __init__(self):
        """Initialize the mock repository structure."""
        self.repositories: dict[str, dict[str, list[str]]] = {}
        self.download_paths: dict[str, Path] = {}
        
    def setup_repository(
        self,
        repo_id: str,
        files: dict[str, list[str]],
        data: dict[str, list[dict[str, Any]]] | None = None
    ) -> None:
        """
        Set up a mock repository with files and optional data.
        
        Args:
            repo_id: Repository ID (e.g., "test/dataset")
            files: Dict mapping splits to file paths (e.g., {"train": ["data/train.jsonl"]})
            data: Optional data for each split (e.g., {"train": [{"id": 1, ...}]})
        """
        self.repositories[repo_id] = {
            "files": files,
            "data": data or {}
        }

    def get_mock_files(self, repo_id: str) -> list[str]:
        """Get the list of files for a repository."""
        if repo_id not in self.repositories:
            raise FileNotFoundError(f"Repository {repo_id} not found")
        return self.repositories[repo_id]["files"]

    def get_mock_data(self, repo_id: str, split: str) -> list[dict[str, Any]]:
        """Get the data for a specific split."""
        if repo_id not in self.repositories:
            raise FileNotFoundError(f"Repository {repo_id} not found")
        files = self.repositories[repo_id]["files"]
        if split not in files:
            raise ValueError(f"Split {split} not found in {repo_id}")
        
        # Return mock data if available
        data = self.repositories[repo_id]["data"].get(split, [])
        return data

    def create_mock_dataset_dir(self, repo_id: str, tmp_path: Path) -> Path:
        """
        Create a mock dataset directory with the repository files.
        
        Args:
            repo_id: Repository ID
            tmp_path: Temporary path to create the dataset in
            
        Returns:
            Path to the created dataset directory
        """
        if repo_id not in self.repositories:
            raise FileNotFoundError(f"Repository {repo_id} not found")
        
        files = self.repositories[repo_id]["files"]
        data = self.repositories[repo_id]["data"]
        
        # Create directory structure
        dataset_dir = tmp_path / repo_id.replace("/", "_")
        dataset_dir.mkdir(parents=True, exist_ok=True)
        
        # Create files
        for split, file_list in files.items():
            for file_path in file_list:
                # Create the file
                full_path = dataset_dir / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Write data if available
                if split in data:
                    with open(full_path, "w") as f:
                        for record in data[split]:
                            f.write(json.dumps(record) + "\n")
        
        return dataset_dir


# =============================================================================
# FIXTURES
# =============================================================================


def hf_mock(monkeypatch: pytest.MonkeyPatch) -> HuggingFaceMock:
    """
    Fixture: Comprehensive HuggingFace Hub mock.
    
    Mocks all HuggingFace Hub services:
    - list_repo_files: Returns mock file lists
    - snapshot_download: Downloads to local directory
    - load_dataset: Loads from local files
    
    Usage:
        def test_something(hf_mock: HuggingFaceMock, tmp_path: Path):
            # Set up mock repository
            hf_mock.setup_repository(
                "test/dataset",
                {"train": ["data/train.jsonl"]},
                {"train": [{"id": 1, "text": "test"}]}
            )
            
            # Patch HuggingFace services
            with hf_mock.patch_all():
                # Your test code here
                ...
    """
    mock = HuggingFaceMock()
    
    def patch_list_repo_files(repo_id: str, **kwargs) -> list[str]:
        """Mock list_repo_files to return mock file list."""
        return mock.get_mock_files(repo_id)
    
    def patch_snapshot_download(repo_id: str, **kwargs) -> Path:
        """Mock snapshot_download to return mock directory."""
        return mock.create_mock_dataset_dir(repo_id, kwargs.get("cache_dir", Path("/tmp")))
    
    def patch_load_dataset(dataset_name: str, **kwargs) -> MagicMock:
        """Mock load_dataset to return mock dataset."""
        if dataset_name not in mock.repositories:
            raise FileNotFoundError(f"Dataset {dataset_name} not found")
        
        # Create a mock dataset object
        mock_dataset = MagicMock()
        files = mock.repositories[dataset_name]["files"]
        data = mock.repositories[dataset_name]["data"]
        
        # Return mock splits
        for split in data.keys():
            mock_dataset.__getitem__.side_effect = lambda key, split=split: data[split]
        
        return mock_dataset
    
    # Apply patches
    monkeypatch.setattr(
        "huggingface_hub.list_repo_files",
        patch_list_repo_files
    )
    monkeypatch.setattr(
        "huggingface_hub.snapshot_download",
        patch_snapshot_download
    )
    monkeypatch.setattr(
        "datasets.load_dataset",
        patch_load_dataset
    )
    
    return mock


# =============================================================================
# EXAMPLE USAGE
# =============================================================================


def test_example_usage(hf_mock: HuggingFaceMock, tmp_path: Path) -> None:
    """Example test showing how to use the HuggingFace mock."""
    # Set up mock repository
    hf_mock.setup_repository(
        "test/dataset",
        {"train": ["data/train.jsonl"]},
        {
            "train": [
                {"id": 1, "text": "test text 1"},
                {"id": 2, "text": "test text 2"},
            ]
        }
    )
    
    # Patch HuggingFace services
    with hf_mock.patch_all():
        # Now you can safely call functions that use HuggingFace
        # They will use the mock instead of the real Hub
        ...
