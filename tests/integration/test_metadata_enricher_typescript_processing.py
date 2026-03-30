# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Integration tests for TypeScript file processing in metadata_enricher.

These tests verify that RepoProcessor correctly calls the TypeScriptAdapter
for .ts and .tsx files, not just Python files.

Bug: metadata_enricher.py uses cfg.profile (set once at init) not file extension
to select adapter, and only calls adapter for .py files.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from src.discovery import ProcessingConfig, RepoProcessor


class TestTypeScriptFileProcessing:
    """Test that RepoProcessor processes TypeScript files with TypeScriptAdapter."""

    @pytest.fixture
    def temp_typescript_repo(self, tmp_path: Path) -> Path:
        """Create a temporary repository with TypeScript files for testing."""
        repo = tmp_path / "test_owner" / "test_repo"
        repo.mkdir(parents=True)

        # Create a TypeScript file with a Lit component
        (repo / "ha_dialog.ts").write_text("""
import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('ha-dialog')
export class HaDialog extends LitElement {
  @property({ type: Boolean }) public open = false;

  render() {
    return html`
      <div>Hello Dialog</div>
    `;
  }
}
""")

        # Create another TypeScript file with i18n and service calls
        (repo / "service_handler.ts").write_text("""
import { HassService } from './types';

export class ServiceHandler {
  handleService(hass: any) {
    // Using hass.localize
    const greeting = hass.localize('ui.greeting');

    // Using callService
    hass.callService('light', 'turn_on', {
      entity_id: 'light.living_room'
    });
  }
}
""")

        # Create a TSX file
        (repo / "component.tsx").write_text("""
import { LitElement, html } from 'lit';
import { customElement } from 'lit/decorators.js';

@customElement('my-element')
export class MyElement extends LitElement {
  render() {
    return html`<div>Hello</div>`;
  }
}
""")

        return repo

    def _setup_raw_structure(self, tmp_path: Path, repo_path: Path) -> Path:
        """Set up the raw directory structure as RepoProcessor expects."""
        raw_dir = tmp_path / "raw" / "test"
        raw_dir.mkdir(parents=True)
        owner_dir = raw_dir / "test_owner"
        owner_dir.mkdir()
        repo_copy = owner_dir / "test_repo"
        repo_copy.mkdir()

        # Copy files to raw structure
        for f in repo_path.glob("*"):
            if f.is_file():
                (repo_copy / f.name).write_text(f.read_text())

        return repo_copy

    def test_typescript_adapter_is_called_for_ts_files(
        self, temp_typescript_repo: Path, tmp_path: Path
    ) -> None:
        """Test that TypeScriptAdapter.parse_file() is invoked for .ts files.

        This test verifies that when processing .ts files, the RepoProcessor
        calls the TypeScriptAdapter to parse the file. Without the fix,
        .ts files skip the adapter entirely.
        """
        # Set up raw directory structure
        repo_copy = self._setup_raw_structure(tmp_path, temp_typescript_repo)

        # Create minimal config with typescript profile
        config_data = {
            "raw_subdir": "raw",
            "output_subdir": "output",
            "category": "test",
            "profile": "typescript",
            "on_parse_error": "fallback",
        }

        cfg = ProcessingConfig(**config_data, base_dir=tmp_path)
        processor = RepoProcessor(cfg)

        # Track if adapter.parse_file was called
        adapter_called_files = []

        original_parse_file = processor._adapter.parse_file

        def track_parse_file(path):
            adapter_called_files.append(path)
            return original_parse_file(path)

        with patch.object(processor._adapter, 'parse_file', side_effect=track_parse_file):
            processor._process_repository("test_owner", repo_copy)

        # Verify TypeScript files were passed to adapter
        ts_files = [f for f in adapter_called_files if f.suffix == '.ts']
        assert len(ts_files) > 0, (
            f"TypeScriptAdapter.parse_file() was never called for .ts files. "
            f"Adapter was called for: {[f.name for f in adapter_called_files]}"
        )

    def test_typescript_adapter_is_called_for_tsx_files(
        self, temp_typescript_repo: Path, tmp_path: Path
    ) -> None:
        """Test that TypeScriptAdapter.parse_file() is invoked for .tsx files.

        This test verifies that when processing .tsx files, the RepoProcessor
        calls the TypeScriptAdapter to parse the file. Without the fix,
        .tsx files skip the adapter entirely.
        """
        # Set up raw directory structure
        repo_copy = self._setup_raw_structure(tmp_path, temp_typescript_repo)

        # Create minimal config with typescript profile
        config_data = {
            "raw_subdir": "raw",
            "output_subdir": "output",
            "category": "test",
            "profile": "typescript",
            "on_parse_error": "fallback",
        }

        cfg = ProcessingConfig(**config_data, base_dir=tmp_path)
        processor = RepoProcessor(cfg)

        # Track if adapter.parse_file was called
        adapter_called_files = []

        original_parse_file = processor._adapter.parse_file

        def track_parse_file(path):
            adapter_called_files.append(path)
            return original_parse_file(path)

        with patch.object(processor._adapter, 'parse_file', side_effect=track_parse_file):
            processor._process_repository("test_owner", repo_copy)

        # Verify TSX files were passed to adapter
        tsx_files = [f for f in adapter_called_files if f.suffix == '.tsx']
        assert len(tsx_files) > 0, (
            f"TypeScriptAdapter.parse_file() was never called for .tsx files. "
            f"Adapter was called for: {[f.name for f in adapter_called_files]}"
        )

    def test_adapter_selection_uses_file_extension_not_profile(
        self, temp_typescript_repo: Path, tmp_path: Path
    ) -> None:
        """Test that adapter is selected based on file extension, not cfg.profile.

        This test creates a RepoProcessor with 'python' profile but processes
        .ts files. The adapter should be selected per-file based on extension,
        not use the single adapter initialized at init time.
        """
        # Set up raw directory structure
        repo_copy = self._setup_raw_structure(tmp_path, temp_typescript_repo)

        # Create config with 'python' profile - but we're processing .ts files
        config_data = {
            "raw_subdir": "raw",
            "output_subdir": "output",
            "category": "test",
            "profile": "python",  # Python profile, but we have .ts files
            "on_parse_error": "fallback",
        }

        cfg = ProcessingConfig(**config_data, base_dir=tmp_path)
        processor = RepoProcessor(cfg)

        # Track if adapter.parse_file was called for .ts files
        adapter_called_files = []

        # We need to mock get_adapter to track per-file adapter selection
        original_get_adapter = None

        def track_get_adapter(extension):
            adapter_called_files.append(f"get_adapter:{extension}")
            # Return a mock that tracks parse_file calls
            mock_adapter = MagicMock()
            original_parse = processor._adapter.parse_file
            def track_parse(path):
                adapter_called_files.append(f"parse_file:{path.name}")
                return original_parse(path)
            mock_adapter.parse_file.side_effect = track_parse
            return mock_adapter

        from src.utils.extractors import factory
        with patch.object(factory, 'get_adapter', side_effect=track_get_adapter):
            processor._process_repository("test_owner", repo_copy)

        # The bug: with current code, get_adapter is called once with 'python' at init
        # and .ts files never trigger a new get_adapter call for '.ts' extension
        ts_adapter_calls = [f for f in adapter_called_files if '.ts' in f]
        assert len(ts_adapter_calls) > 0, (
            f"Per-file adapter selection not happening. "
            f"get_adapter was called with: {adapter_called_files}"
        )