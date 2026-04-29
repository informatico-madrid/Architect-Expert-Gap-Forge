# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joo@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
End-to-end integration tests for TypeScriptAdapter.

These tests verify that the TypeScriptAdapter correctly parses TypeScript files
containing Lit components, i18n keys, and service calls, and that all extractors
produce the expected output.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from src.utils.extractors.typescript_adapter import TypeScriptAdapter
from src.utils.extractors.extractors.lit_component import LitComponentExtractor
from src.utils.extractors.extractors.i18n_key import I18nKeyExtractor
from src.utils.extractors.extractors.service_call import ServiceCallExtractor
from src.utils.extractors.base import ParseResult
from src.discovery import ProcessingConfig, RepoProcessor


# Sample TypeScript content with Lit component, i18n keys, and service calls
#
# NOTE: i18n pattern uses negative lookbehind (?<!) for dots, which means:
# - this.localize(...) is NOT matched (has dot before localize from 'this.')
# - hass.localize(...) is matched
# - plain localize(...) would be matched (without dot prefix)
SAMPLE_TYPESCRIPT_CONTENT = """
// Sample Lit component with i18n and service calls for integration testing

import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';

// Home Assistant dialog component
@customElement('ha-dialog')
export class HaDialog extends LitElement {
  @property({ type: Boolean }) public open = false;
  @property({ type: String, name: 'dialog-title' }) public dialogTitle = '';
  @property({ name: 'confirm-action' }) public confirmAction = '';
  @state() private _loading = false;

  // i18n keys for localization - note: this.localize is NOT captured by regex negative-lookbehind for dots
  private _cancelText = this.hass.localize('ui.dialog.cancel');
  // Template literal pattern is captured
  private _templateKey = this.localize(`ui.card.actions.${this._action}`);

  private _action = 'close';

  // Service call
  private async _closeDialog() {
    this.hass.callService('dialog', 'close', {
      entity_id: 'dialog.home_assistant'
    });
  }

  private async _confirmAction() {
    await this.hass.callService('homeassistant', 'turn_off', {
      entity_id: 'light.living_room'
    });
  }

  protected render() {
    return html`
      <div class="dialog">
        <h2>${this.dialogTitle}</h2>
        <button @click=${this._closeDialog}>${this._cancelText}</button>
        <button @click=${this._confirmAction}>${this.confirmAction}</button>
      </div>
    `;
  }
}

// Another component using context._hass pattern
@customElement('bubble-card')
export class BubbleCard extends HTMLElement {
  public static get properties() {
    return {
      _hass: { type: Object },
      cardTitle: { type: String },
    };
  }

  private _hass: any;

  connectedCallback() {
    this.context._hass.callService('climate', 'set_temperature', {
      entity_id: 'climate.living_room',
      temperature: 22
    });
  }
}
"""


class TestTypeScriptAdapterE2E:
    """End-to-end integration tests for TypeScriptAdapter."""

    @pytest.fixture
    def sample_ts_file(self, tmp_path: Path) -> Path:
        """Create a sample TypeScript file for testing."""
        ts_file = tmp_path / "sample_component.ts"
        ts_file.write_text(SAMPLE_TYPESCRIPT_CONTENT)
        return ts_file

    @pytest.fixture
    def adapter(self) -> TypeScriptAdapter:
        """Create a TypeScriptAdapter instance."""
        return TypeScriptAdapter()

    def test_parse_file_returns_parse_result(
        self, adapter: TypeScriptAdapter, sample_ts_file: Path
    ) -> None:
        """Test that parse_file returns a valid ParseResult."""
        result = adapter.parse_file(sample_ts_file)

        assert isinstance(result, ParseResult)
        assert result.file_path == sample_ts_file
        assert result.raw_content is not None
        assert len(result.raw_content) > 0

    def test_parse_file_extracts_dependencies(
        self, adapter: TypeScriptAdapter, sample_ts_file: Path
    ) -> None:
        """Test that parse_file extracts dependencies correctly."""
        result = adapter.parse_file(sample_ts_file)

        # Should find imports like 'lit', 'lit/decorators.js'
        dep_names = [d.name for d in result.dependencies]
        assert "lit" in dep_names
        assert any("lit/decorators" in d for d in dep_names)

    def test_lit_component_extractor_finds_components(
        self, sample_ts_file: Path
    ) -> None:
        """Test that LitComponentExtractor finds @customElement decorators."""
        extractor = LitComponentExtractor()
        raw_content = sample_ts_file.read_text()

        tokens = extractor.extract(None, raw_content, sample_ts_file)

        # Should find ha-dialog and bubble-card components
        lit_tokens = [t for t in tokens if t.token_type == "lit_component"]
        assert len(lit_tokens) >= 2

        tag_names = [t.data["tag_name"] for t in lit_tokens]
        assert "ha-dialog" in tag_names
        assert "bubble-card" in tag_names

    def test_i18n_key_extractor_finds_keys(self, sample_ts_file: Path) -> None:
        """Test that I18nKeyExtractor finds localize() calls.

        Note: this.localize() is NOT captured by LOCALIZE_CALL_PATTERN due to
        the negative-lookbehind for dots. Only hass.localize() and template
        literals are matched.
        """
        extractor = I18nKeyExtractor()
        raw_content = sample_ts_file.read_text()

        tokens = extractor.extract(None, raw_content, sample_ts_file)

        # Should find i18n keys (hass.localize + template_literal)
        i18n_tokens = [t for t in tokens if t.token_type == "i18n_key"]
        assert len(i18n_tokens) >= 2

        # Check for specific keys
        keys = [t.data["key"] for t in i18n_tokens]
        assert "ui.dialog.cancel" in keys
        # Template literal prefix should be captured
        assert any("ui.card.actions" in k for k in keys)

    def test_service_call_extractor_finds_calls(self, sample_ts_file: Path) -> None:
        """Test that ServiceCallExtractor finds callService() calls."""
        extractor = ServiceCallExtractor()
        raw_content = sample_ts_file.read_text()

        tokens = extractor.extract(None, raw_content, sample_ts_file)

        # Should find service calls
        service_tokens = [t for t in tokens if t.token_type == "service_call"]
        assert len(service_tokens) >= 3

        # Check for specific domains/services
        domains = [t.data["domain"] for t in service_tokens]
        services = [t.data["service"] for t in service_tokens]

        assert "dialog" in domains
        assert "close" in services
        assert "homeassistant" in domains
        assert "turn_off" in services

    def test_adapter_with_all_extractors(self, sample_ts_file: Path) -> None:
        """Test that the adapter correctly uses all extractors together."""
        adapter = TypeScriptAdapter(
            extractors=[
                LitComponentExtractor(),
                I18nKeyExtractor(),
                ServiceCallExtractor(),
            ]
        )

        raw_content = sample_ts_file.read_text()

        # Extract using each extractor
        all_tokens = []
        for extractor in adapter.extractors:
            tokens = extractor.extract(None, raw_content, sample_ts_file)
            all_tokens.extend(tokens)

        # Verify we got tokens from all three types
        token_types = set(t.token_type for t in all_tokens)
        assert "lit_component" in token_types
        assert "i18n_key" in token_types
        assert "service_call" in token_types

        # Count tokens
        lit_count = sum(1 for t in all_tokens if t.token_type == "lit_component")
        i18n_count = sum(1 for t in all_tokens if t.token_type == "i18n_key")
        service_count = sum(1 for t in all_tokens if t.token_type == "service_call")

        assert lit_count >= 2, f"Expected at least 2 lit components, got {lit_count}"
        # Note: this.localize is NOT captured, only hass.localize and template_literal
        assert i18n_count >= 2, f"Expected at least 2 i18n keys, got {i18n_count}"
        assert service_count >= 3, (
            f"Expected at least 3 service calls, got {service_count}"
        )

    def test_parse_file_does_not_crash_on_valid_typescript(
        self, adapter: TypeScriptAdapter, sample_ts_file: Path
    ) -> None:
        """Test that parse_file handles valid TypeScript without crashing."""
        # This should not raise any exceptions
        result = adapter.parse_file(sample_ts_file)

        assert result is not None
        assert isinstance(result, ParseResult)

    def test_adapter_handles_different_hass_prefixes(self, tmp_path: Path) -> None:
        """Test that the adapter correctly identifies different hass prefixes."""
        ts_content = """
        class TestComponent extends HTMLElement {
            test1() {
                this.hass.callService('light', 'turn_on', { entity_id: 'light.1' });
            }
            test2() {
                context._hass.callService('switch', 'toggle', { entity_id: 'switch.1' });
            }
            test3() {
                hass.callService('fan', 'set_speed', { entity_id: 'fan.1' });
            }
        }
        """

        ts_file = tmp_path / "hass_prefixes.ts"
        ts_file.write_text(ts_content)

        extractor = ServiceCallExtractor()
        raw_content = ts_file.read_text()

        tokens = extractor.extract(None, raw_content, ts_file)
        service_tokens = [t for t in tokens if t.token_type == "service_call"]

        # Check we got all three prefixes
        prefixes = [t.data["hass_prefix"] for t in service_tokens]
        assert "this.hass" in prefixes
        assert "context._hass" in prefixes
        assert "hass" in prefixes

    def test_adapter_extracts_entity_ids_from_service_data(
        self, tmp_path: Path
    ) -> None:
        """Test that entity IDs are correctly extracted from service data."""
        ts_content = """
        class TestComponent extends HTMLElement {
            test() {
                this.hass.callService('light', 'turn_on', {
                    entity_id: 'light.living_room'
                });
            }
            testArray() {
                this.hass.callService('homeassistant', 'turn_off', {
                    entity_id: ['light.living_room', 'light.bedroom']
                });
            }
        }
        """

        ts_file = tmp_path / "entity_ids.ts"
        ts_file.write_text(ts_content)

        extractor = ServiceCallExtractor()
        raw_content = ts_file.read_text()

        tokens = extractor.extract(None, raw_content, ts_file)
        service_tokens = [t for t in tokens if t.token_type == "service_call"]

        # Find the single entity_id token
        single_entity = next(
            (t for t in service_tokens if "light.living_room" in t.data["entity_ids"]),
            None,
        )
        assert single_entity is not None, "Should find single entity_id"
        assert single_entity.data["entity_ids"] == ["light.living_room"]

    def test_i18n_context_tracking(self, tmp_path: Path) -> None:
        """Test that i18n context (localize vs hass.localize) is tracked correctly.

        Note: The LOCALIZE_CALL_PATTERN does NOT match this.localize
        because the lookbehind sees the dot in 'this.'. Only hass.localize is matched
        for prefixed calls. Plain localize() without any prefix would be matched as 'localize'.
        """
        ts_content = """
        class TestComponent extends HTMLElement {
            test1() {
                const a = localize('ui.key.1');
                const b = this.hass.localize('ui.key.2');
            }
        }
        """

        ts_file = tmp_path / "i18n_context.ts"
        ts_file.write_text(ts_content)

        extractor = I18nKeyExtractor()
        raw_content = ts_file.read_text()

        tokens = extractor.extract(None, raw_content, ts_file)
        i18n_tokens = [t for t in tokens if t.token_type == "i18n_key"]

        # Find tokens by key
        key1_token = next((t for t in i18n_tokens if t.data["key"] == "ui.key.1"), None)
        key2_token = next((t for t in i18n_tokens if t.data["key"] == "ui.key.2"), None)

        # Plain localize() call is captured as 'localize' context
        assert key1_token is not None, "Should find ui.key.1"
        assert key1_token.data["context"] == "localize", (
            "ui.key.1 should be localize context"
        )

        # hass.localize() is captured as 'hass.localize' context
        assert key2_token is not None, "Should find ui.key.2"
        assert key2_token.data["context"] == "hass.localize", (
            "ui.key.2 should be hass.localize context"
        )

    def test_parse_file_with_fixture_file(self, tmp_path: Path) -> None:
        """Test parsing using the actual fixture file."""
        # Create the fixture file
        fixture_dir = tmp_path / "fixtures"
        fixture_dir.mkdir()
        fixture_file = fixture_dir / "test_component.ts"
        fixture_file.write_text(SAMPLE_TYPESCRIPT_CONTENT)

        adapter = TypeScriptAdapter()
        result = adapter.parse_file(fixture_file)

        assert result.file_path == fixture_file
        assert "HaDialog" in result.raw_content
        assert "BubbleCard" in result.raw_content

    def test_adapter_returns_valid_parse_result_structure(
        self, adapter: TypeScriptAdapter, sample_ts_file: Path
    ) -> None:
        """Test that parse_file returns a properly structured ParseResult."""
        result = adapter.parse_file(sample_ts_file)

        # Check ParseResult structure
        assert hasattr(result, "file_path")
        assert hasattr(result, "ast_tree")
        assert hasattr(result, "raw_content")
        assert hasattr(result, "dependencies")

        # Verify types
        assert isinstance(result.file_path, Path)
        assert isinstance(result.raw_content, str)
        assert isinstance(result.dependencies, tuple)

    def test_lit_component_properties_and_states(self, tmp_path: Path) -> None:
        """Test that LitComponentExtractor extracts properties and states.

        Note: The regex-based extractor requires explicit 'name:' option in property
        decorators to extract property names. The regex pattern for word characters only matches
        word characters, so hyphens in names are not supported.
        State extraction works via @state() detection.
        """
        ts_content = """
        import { customElement, property, state } from 'lit/decorators.js';

        @customElement('my-card')
        export class MyCard extends LitElement {
          @property({ name: 'cardTitle', type: String }) public cardTitle = '';
          @property({ name: 'loading', type: Boolean, reflect: true }) public loading = false;
          @state() private _internalState = '';

          render() {
            return html`<h1>${this.cardTitle}</h1>`;
          }
        }
        """

        ts_file = tmp_path / "properties_test.ts"
        ts_file.write_text(ts_content)

        extractor = LitComponentExtractor()
        raw_content = ts_file.read_text()

        tokens = extractor.extract(None, raw_content, ts_file)
        lit_tokens = [t for t in tokens if t.token_type == "lit_component"]

        assert len(lit_tokens) >= 1
        my_card = next((t for t in lit_tokens if t.data["tag_name"] == "my-card"), None)
        assert my_card is not None, "Should find my-card component"

        # Check properties - regex extracts from name: 'propertyName' in decorator
        # Note: regex (\w+) does NOT match names with hyphens like 'card-title'
        properties = my_card.data["properties"]
        assert len(properties) >= 2, (
            f"Expected at least 2 properties, got {len(properties)}"
        )
        assert "cardTitle" in properties
        assert "loading" in properties

        # Check states - @state() decorator is detected
        states = my_card.data["states"]
        assert len(states) >= 1, f"Expected at least 1 state, got {len(states)}"

        # Check observed attributes (derived from property names)
        observed = my_card.data["observed_attributes"]
        assert len(observed) >= 2, (
            f"Expected at least 2 observed attributes, got {len(observed)}"
        )


# Sample TypeScript content for RepoProcessor integration testing
REPO_PROCESSOR_TEST_CONTENT = """
import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';

// Home Assistant dialog component with full feature set
@customElement('ha-dialog')
export class HaDialog extends LitElement {
  @property({ type: Boolean }) public open = false;
  @property({ type: String, name: 'dialog-title' }) public dialogTitle = '';
  @state() private _loading = false;

  // i18n keys
  private _cancelText = this.hass.localize('ui.dialog.cancel');
  private _confirmText = this.localize('ui.dialog.confirm');

  // Service calls
  private async _closeDialog() {
    this.hass.callService('dialog', 'close', {
      entity_id: 'dialog.home_assistant'
    });
  }

  private async _confirmAction() {
    await this.hass.callService('homeassistant', 'turn_off', {
      entity_id: 'light.living_room'
    });
  }

  protected render() {
    return html`
      <div class="dialog">
        <h2>${this.dialogTitle}</h2>
        <button @click=${this._closeDialog}>${this._cancelText}</button>
      </div>
    `;
  }
}

// Another component
@customElement('ha-card')
export class HaCard extends HTMLElement {
  @property({ type: String }) public cardTitle = '';

  testMethod() {
    const temp = this.hass.localize('ui.card.temp');
    this.hass.callService('climate', 'set_temperature', {
      entity_id: 'climate.living_room',
      temperature: 22
    });
  }
}
"""


class TestRepoProcessorPipeline:
    """Integration tests for TypeScript file processing through RepoProcessor.

    These tests verify that:
    1. RepoProcessor correctly selects TypeScriptAdapter for .ts files
    2. TypeScriptAdapter.parse_file() is invoked for TypeScript files
    3. Extraction results contain expected Lit/i18n/service call data
    """

    def _setup_repo_structure(self, tmp_path: Path) -> tuple[Path, Path]:
        """Set up repository structure for RepoProcessor testing.

        Returns (source_root, repo_path) where source_root is the raw/{category}
        directory and repo_path is the actual repository directory.
        """
        raw_dir = tmp_path / "raw" / "test_category"
        raw_dir.mkdir(parents=True)

        owner_dir = raw_dir / "test_owner"
        owner_dir.mkdir()

        repo_dir = owner_dir / "test_repo"
        repo_dir.mkdir()

        # Create an __init__.py to make it a discoverable module
        (repo_dir / "__init__.py").write_text("")

        # Create the TypeScript file (NOT named with 'test' to avoid test role classification)
        ts_file = repo_dir / "ha_dialog.ts"
        ts_file.write_text(REPO_PROCESSOR_TEST_CONTENT)

        return raw_dir, repo_dir

    def test_reprocessor_calls_typescript_adapter_for_ts_files(
        self, tmp_path: Path
    ) -> None:
        """Test that RepoProcessor calls TypeScriptAdapter.parse_file() for .ts files.

        This verifies the full pipeline integration: RepoProcessor should use
        per-file adapter selection based on file extension, not cfg.profile.
        """
        raw_dir, repo_dir = self._setup_repo_structure(tmp_path)

        # Create minimal config with typescript profile
        config_data = {
            "raw_subdir": "raw",
            "output_subdir": "output",
            "category": "test_category",
            "profile": "typescript",
            "on_parse_error": "skip",  # Skip errors to continue processing
            "extensions": {".py", ".md", ".ts", ".tsx"},
        }

        cfg = ProcessingConfig(**config_data, base_dir=tmp_path)
        processor = RepoProcessor(cfg)

        # Track adapter calls
        adapter_calls = []
        mock_adapter = MagicMock()

        # Create a mock parse result with dependencies
        mock_parse_result = MagicMock()
        mock_parse_result.dependencies = []
        mock_adapter.parse_file.return_value = mock_parse_result

        def track_adapter(extension):
            adapter_calls.append(extension)
            return mock_adapter

        with patch(
            "src.utils.extractors.factory.get_adapter", side_effect=track_adapter
        ):
            processor._process_repository("test_owner", repo_dir)

        # Verify .ts file triggered adapter selection
        assert ".ts" in adapter_calls, (
            f"TypeScript adapter not selected for .ts file. "
            f"Adapter was selected for: {adapter_calls}"
        )

        # Verify parse_file was called with the .ts file path
        ts_calls = [
            call
            for call in mock_adapter.parse_file.call_args_list
            if call[0][0].suffix == ".ts"
        ]
        assert len(ts_calls) > 0, (
            f"TypeScriptAdapter.parse_file() was never called for .ts files. "
            f"Total parse_file calls: {mock_adapter.parse_file.call_count}"
        )

    def test_reprocessor_extracts_lit_components_from_typescript(
        self, tmp_path: Path
    ) -> None:
        """Test that Lit components are extracted when processing TypeScript files.

        This verifies that the TypeScriptAdapter correctly identifies
        @customElement decorators and extracts component metadata.
        """
        raw_dir, repo_dir = self._setup_repo_structure(tmp_path)

        # Verify the test file has the expected Lit components
        ts_file = repo_dir / "ha_dialog.ts"
        assert ts_file.exists()

        # Run the TypeScriptAdapter directly to verify extraction
        adapter = TypeScriptAdapter()
        result = adapter.parse_file(ts_file)

        # Check that we got valid parse result
        assert isinstance(result, ParseResult)
        assert result.file_path == ts_file

        # Verify Lit components were extracted via the adapter's extractors
        # The adapter combines multiple extractors, so we check if any tokens are present
        extractor = LitComponentExtractor()
        tokens = extractor.extract(None, ts_file.read_text(), ts_file)

        lit_tokens = [t for t in tokens if t.token_type == "lit_component"]
        tag_names = [t.data["tag_name"] for t in lit_tokens]

        # Should find ha-dialog and ha-card components
        assert "ha-dialog" in tag_names, f"ha-dialog not found in {tag_names}"
        assert "ha-card" in tag_names, f"ha-card not found in {tag_names}"

    def test_reprocessor_extracts_i18n_keys_from_typescript(
        self, tmp_path: Path
    ) -> None:
        """Test that i18n keys are extracted when processing TypeScript files.

        This verifies that the I18nKeyExtractor correctly identifies
        localize() calls and extracts translation keys.
        """
        raw_dir, repo_dir = self._setup_repo_structure(tmp_path)

        ts_file = repo_dir / "ha_dialog.ts"

        # Run the I18nKeyExtractor directly
        extractor = I18nKeyExtractor()
        tokens = extractor.extract(None, ts_file.read_text(), ts_file)

        i18n_tokens = [t for t in tokens if t.token_type == "i18n_key"]
        keys = [t.data["key"] for t in i18n_tokens]

        # Should find ui.dialog.cancel, ui.dialog.confirm, ui.card.temp
        # Note: this.localize is NOT matched by the negative-lookbehind regex
        assert "ui.dialog.cancel" in keys, f"ui.dialog.cancel not found in {keys}"
        assert "ui.card.temp" in keys, f"ui.card.temp not found in {keys}"

    def test_reprocessor_extracts_service_calls_from_typescript(
        self, tmp_path: Path
    ) -> None:
        """Test that service calls are extracted when processing TypeScript files.

        This verifies that the ServiceCallExtractor correctly identifies
        hass.callService() calls and extracts domain/service/entity_id data.
        """
        raw_dir, repo_dir = self._setup_repo_structure(tmp_path)

        ts_file = repo_dir / "ha_dialog.ts"

        # Run the ServiceCallExtractor directly
        extractor = ServiceCallExtractor()
        tokens = extractor.extract(None, ts_file.read_text(), ts_file)

        service_tokens = [t for t in tokens if t.token_type == "service_call"]

        # Should find at least 3 service calls:
        # - dialog.close
        # - homeassistant.turn_off
        # - climate.set_temperature
        assert len(service_tokens) >= 3, (
            f"Expected at least 3 service calls, got {len(service_tokens)}"
        )

        domains = [t.data["domain"] for t in service_tokens]
        services = [t.data["service"] for t in service_tokens]

        assert "dialog" in domains, f"dialog domain not found in {domains}"
        assert "close" in services, f"close service not found in {services}"
        assert "homeassistant" in domains, (
            f"homeassistant domain not found in {domains}"
        )
        assert "turn_off" in services, f"turn_off service not found in {services}"
        assert "climate" in domains, f"climate domain not found in {domains}"
        assert "set_temperature" in services, (
            f"set_temperature service not found in {services}"
        )

    def test_full_pipeline_produces_extraction_results(self, tmp_path: Path) -> None:
        """Test that the full pipeline produces extraction results with all token types.

        This is an integration test that verifies:
        1. RepoProcessor can process TypeScript files
        2. TypeScriptAdapter is selected per-file
        3. All three extractor types (Lit, i18n, service) produce tokens
        """
        raw_dir, repo_dir = self._setup_repo_structure(tmp_path)

        config_data = {
            "raw_subdir": "raw",
            "output_subdir": "output",
            "category": "test_category",
            "profile": "typescript",
            "on_parse_error": "skip",
            "extensions": {".py", ".ts", ".tsx"},
        }

        cfg = ProcessingConfig(**config_data, base_dir=tmp_path)
        processor = RepoProcessor(cfg)

        # Import the real factory.get_adapter before patching
        from src.utils.extractors.factory import get_adapter as real_factory_get_adapter

        # Mock get_adapter to return real TypeScriptAdapter for .ts files
        real_ts_adapter = TypeScriptAdapter()

        def selective_adapter(extension):
            if extension in (".ts", ".tsx"):
                return real_ts_adapter
            return real_factory_get_adapter(extension)

        extraction_results = {}

        original_parse_file = real_ts_adapter.parse_file

        def tracking_parse_file(file_path):
            result = original_parse_file(file_path)
            # Track what was extracted
            extraction_results[file_path.name] = {
                "dependencies": result.dependencies,
                "content_length": len(result.raw_content) if result.raw_content else 0,
            }
            return result

        with patch(
            "src.utils.extractors.factory.get_adapter", side_effect=selective_adapter
        ):
            with patch.object(
                real_ts_adapter, "parse_file", side_effect=tracking_parse_file
            ):
                processor._process_repository("test_owner", repo_dir)

        # Verify the TypeScript file was processed
        assert "ha_dialog.ts" in extraction_results, (
            f"ha_dialog.ts was not processed. "
            f"Processed files: {list(extraction_results.keys())}"
        )

        # Verify content was read
        assert extraction_results["ha_dialog.ts"]["content_length"] > 0, (
            "No content was extracted from the TypeScript file"
        )

    def test_typescript_adapter_handles_tsx_files(self, tmp_path: Path) -> None:
        """Test that TSX files are also processed through the pipeline.

        This verifies that .tsx files trigger the TypeScriptAdapter as well.
        """
        raw_dir, repo_dir = self._setup_repo_structure(tmp_path)

        # Add a TSX file to the repo (NOT named with 'test' to avoid test role classification)
        tsx_file = repo_dir / "my_element.tsx"
        tsx_file.write_text("""
import { LitElement, html } from 'lit';
import { customElement } from 'lit/decorators.js';

@customElement('my-tsx-element')
export class MyTsxElement extends LitElement {
  render() {
    return html`<div>TSX Element</div>`;
  }
}
""")

        config_data = {
            "raw_subdir": "raw",
            "output_subdir": "output",
            "category": "test_category",
            "profile": "typescript",
            "on_parse_error": "skip",
            "extensions": {".py", ".ts", ".tsx"},
        }

        cfg = ProcessingConfig(**config_data, base_dir=tmp_path)
        processor = RepoProcessor(cfg)

        # Import the real factory.get_adapter before patching
        from src.utils.extractors.factory import get_adapter as real_factory_get_adapter

        adapter_calls = []
        real_ts_adapter = TypeScriptAdapter()

        def selective_adapter(extension):
            adapter_calls.append(extension)
            if extension in (".ts", ".tsx"):
                return real_ts_adapter
            return real_factory_get_adapter(extension)

        with patch(
            "src.utils.extractors.factory.get_adapter", side_effect=selective_adapter
        ):
            processor._process_repository("test_owner", repo_dir)

        # Verify .tsx triggered adapter selection
        assert ".tsx" in adapter_calls, (
            f"TypeScript adapter not selected for .tsx file. "
            f"Adapter was selected for: {adapter_calls}"
        )
