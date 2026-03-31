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

        # Create an __init__.py to make this directory a discoverable module
        (repo / "__init__.py").write_text("")


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
            "extensions": {".py", ".md", ".ts", ".tsx"},
        }

        cfg = ProcessingConfig(**config_data, base_dir=tmp_path)
        processor = RepoProcessor(cfg)

        # Track if adapter.parse_file was called via per-file lookup
        adapter_called_files = []
        mock_adapter = MagicMock()
        mock_parse_result = MagicMock()
        mock_parse_result.dependencies = []
        mock_adapter.parse_file.return_value = mock_parse_result

        def track_get_adapter(extension):
            if extension in ('.ts', '.tsx'):
                return mock_adapter
            # Return a real adapter for other extensions to not break processing
            from src.utils.extractors import get_adapter as real_get_adapter
            return real_get_adapter(extension)

        with patch('src.discovery.metadata_enricher.get_adapter', side_effect=track_get_adapter):
            processor._process_repository("test_owner", repo_copy)

        # Verify TypeScript files were passed to adapter
        ts_calls = [call for call in mock_adapter.parse_file.call_args_list
                    if call[0][0].suffix == '.ts']
        assert len(ts_calls) > 0, (
            f"TypeScriptAdapter.parse_file() was never called for .ts files. "
            f"Adapter was called with: {[call[0][0].name for call in mock_adapter.parse_file.call_args_list]}"
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
            "extensions": {".py", ".md", ".ts", ".tsx"},
        }

        cfg = ProcessingConfig(**config_data, base_dir=tmp_path)
        processor = RepoProcessor(cfg)

        # Track if adapter.parse_file was called via per-file lookup
        adapter_called_files = []
        mock_adapter = MagicMock()
        mock_parse_result = MagicMock()
        mock_parse_result.dependencies = []
        mock_adapter.parse_file.return_value = mock_parse_result

        def track_get_adapter(extension):
            if extension in ('.ts', '.tsx'):
                adapter_called_files.append(extension)
                return mock_adapter
            # Return a real adapter for other extensions to not break processing
            from src.utils.extractors import get_adapter as real_get_adapter
            return real_get_adapter(extension)

        with patch('src.discovery.metadata_enricher.get_adapter', side_effect=track_get_adapter):
            processor._process_repository("test_owner", repo_copy)

        # Verify TSX files were passed to adapter
        tsx_calls = [call for call in mock_adapter.parse_file.call_args_list
                     if call[0][0].suffix == '.tsx']
        assert len(tsx_calls) > 0, (
            f"TypeScriptAdapter.parse_file() was never called for .tsx files. "
            f"Adapter was called with: {[call[0][0].name for call in mock_adapter.parse_file.call_args_list]}"
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
            "extensions": {".py", ".md", ".ts", ".tsx"},
        }

        cfg = ProcessingConfig(**config_data, base_dir=tmp_path)
        processor = RepoProcessor(cfg)

        # Track per-file adapter selection via mocking get_adapter
        adapter_selection_log = []
        mock_adapter = MagicMock()
        mock_parse_result = MagicMock()
        mock_parse_result.dependencies = []
        mock_adapter.parse_file.return_value = mock_parse_result

        def track_get_adapter(extension):
            adapter_selection_log.append(extension)
            if extension in ('.ts', '.tsx'):
                return mock_adapter
            # Return a real adapter for other extensions
            from src.utils.extractors import get_adapter as real_get_adapter
            return real_get_adapter(extension)

        with patch('src.discovery.metadata_enricher.get_adapter', side_effect=track_get_adapter):
            processor._process_repository("test_owner", repo_copy)

        # Verify .ts extension was passed to get_adapter (per-file selection)
        assert '.ts' in adapter_selection_log, (
            f"Per-file adapter selection not happening. "
            f"get_adapter was called with extensions: {adapter_selection_log}"
        )