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
import pytest
import tempfile
import os

from src.utils.extractors.typescript_adapter import TypeScriptAdapter
from src.utils.extractors.extractors.lit_component import LitComponentExtractor
from src.utils.extractors.extractors.i18n_key import I18nKeyExtractor
from src.utils.extractors.extractors.service_call import ServiceCallExtractor
from src.utils.extractors.base import ParseResult


# Sample TypeScript content with Lit component, i18n keys, and service calls
#
# NOTE: i18n pattern uses negative lookbehind (?<!) for dots, which means:
# - this.localize(...) is NOT matched (has dot before localize from 'this.')
# - hass.localize(...) is matched
# - plain localize(...) would be matched (without dot prefix)
SAMPLE_TYPESCRIPT_CONTENT = '''
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
'''


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
        assert 'lit' in dep_names
        assert any('lit/decorators' in d for d in dep_names)

    def test_lit_component_extractor_finds_components(
        self, sample_ts_file: Path
    ) -> None:
        """Test that LitComponentExtractor finds @customElement decorators."""
        extractor = LitComponentExtractor()
        raw_content = sample_ts_file.read_text()

        tokens = extractor.extract(None, raw_content, sample_ts_file)

        # Should find ha-dialog and bubble-card components
        lit_tokens = [t for t in tokens if t.token_type == 'lit_component']
        assert len(lit_tokens) >= 2

        tag_names = [t.data['tag_name'] for t in lit_tokens]
        assert 'ha-dialog' in tag_names
        assert 'bubble-card' in tag_names

    def test_i18n_key_extractor_finds_keys(
        self, sample_ts_file: Path
    ) -> None:
        """Test that I18nKeyExtractor finds localize() calls.

        Note: this.localize() is NOT captured by LOCALIZE_CALL_PATTERN due to
        the negative-lookbehind for dots. Only hass.localize() and template
        literals are matched.
        """
        extractor = I18nKeyExtractor()
        raw_content = sample_ts_file.read_text()

        tokens = extractor.extract(None, raw_content, sample_ts_file)

        # Should find i18n keys (hass.localize + template_literal)
        i18n_tokens = [t for t in tokens if t.token_type == 'i18n_key']
        assert len(i18n_tokens) >= 2

        # Check for specific keys
        keys = [t.data['key'] for t in i18n_tokens]
        assert 'ui.dialog.cancel' in keys
        # Template literal prefix should be captured
        assert any('ui.card.actions' in k for k in keys)

    def test_service_call_extractor_finds_calls(
        self, sample_ts_file: Path
    ) -> None:
        """Test that ServiceCallExtractor finds callService() calls."""
        extractor = ServiceCallExtractor()
        raw_content = sample_ts_file.read_text()

        tokens = extractor.extract(None, raw_content, sample_ts_file)

        # Should find service calls
        service_tokens = [t for t in tokens if t.token_type == 'service_call']
        assert len(service_tokens) >= 3

        # Check for specific domains/services
        domains = [t.data['domain'] for t in service_tokens]
        services = [t.data['service'] for t in service_tokens]

        assert 'dialog' in domains
        assert 'close' in services
        assert 'homeassistant' in domains
        assert 'turn_off' in services

    def test_adapter_with_all_extractors(
        self, sample_ts_file: Path
    ) -> None:
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
        assert 'lit_component' in token_types
        assert 'i18n_key' in token_types
        assert 'service_call' in token_types

        # Count tokens
        lit_count = sum(1 for t in all_tokens if t.token_type == 'lit_component')
        i18n_count = sum(1 for t in all_tokens if t.token_type == 'i18n_key')
        service_count = sum(1 for t in all_tokens if t.token_type == 'service_call')

        assert lit_count >= 2, f"Expected at least 2 lit components, got {lit_count}"
        # Note: this.localize is NOT captured, only hass.localize and template_literal
        assert i18n_count >= 2, f"Expected at least 2 i18n keys, got {i18n_count}"
        assert service_count >= 3, f"Expected at least 3 service calls, got {service_count}"

    def test_parse_file_does_not_crash_on_valid_typescript(
        self, adapter: TypeScriptAdapter, sample_ts_file: Path
    ) -> None:
        """Test that parse_file handles valid TypeScript without crashing."""
        # This should not raise any exceptions
        result = adapter.parse_file(sample_ts_file)

        assert result is not None
        assert isinstance(result, ParseResult)

    def test_adapter_handles_different_hass_prefixes(
        self, tmp_path: Path
    ) -> None:
        """Test that the adapter correctly identifies different hass prefixes."""
        ts_content = '''
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
        '''

        ts_file = tmp_path / "hass_prefixes.ts"
        ts_file.write_text(ts_content)

        extractor = ServiceCallExtractor()
        raw_content = ts_file.read_text()

        tokens = extractor.extract(None, raw_content, ts_file)
        service_tokens = [t for t in tokens if t.token_type == 'service_call']

        # Check we got all three prefixes
        prefixes = [t.data['hass_prefix'] for t in service_tokens]
        assert 'this.hass' in prefixes
        assert 'context._hass' in prefixes
        assert 'hass' in prefixes

    def test_adapter_extracts_entity_ids_from_service_data(
        self, tmp_path: Path
    ) -> None:
        """Test that entity IDs are correctly extracted from service data."""
        ts_content = '''
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
        '''

        ts_file = tmp_path / "entity_ids.ts"
        ts_file.write_text(ts_content)

        extractor = ServiceCallExtractor()
        raw_content = ts_file.read_text()

        tokens = extractor.extract(None, raw_content, ts_file)
        service_tokens = [t for t in tokens if t.token_type == 'service_call']

        # Find the single entity_id token
        single_entity = next(
            (t for t in service_tokens if 'light.living_room' in t.data['entity_ids']),
            None
        )
        assert single_entity is not None, "Should find single entity_id"
        assert single_entity.data['entity_ids'] == ['light.living_room']

    def test_i18n_context_tracking(
        self, tmp_path: Path
    ) -> None:
        """Test that i18n context (localize vs hass.localize) is tracked correctly.

        Note: The LOCALIZE_CALL_PATTERN does NOT match this.localize
        because the lookbehind sees the dot in 'this.'. Only hass.localize is matched
        for prefixed calls. Plain localize() without any prefix would be matched as 'localize'.
        """
        ts_content = '''
        class TestComponent extends HTMLElement {
            test1() {
                const a = localize('ui.key.1');
                const b = this.hass.localize('ui.key.2');
            }
        }
        '''

        ts_file = tmp_path / "i18n_context.ts"
        ts_file.write_text(ts_content)

        extractor = I18nKeyExtractor()
        raw_content = ts_file.read_text()

        tokens = extractor.extract(None, raw_content, ts_file)
        i18n_tokens = [t for t in tokens if t.token_type == 'i18n_key']

        # Find tokens by key
        key1_token = next((t for t in i18n_tokens if t.data['key'] == 'ui.key.1'), None)
        key2_token = next((t for t in i18n_tokens if t.data['key'] == 'ui.key.2'), None)

        # Plain localize() call is captured as 'localize' context
        assert key1_token is not None, "Should find ui.key.1"
        assert key1_token.data['context'] == 'localize', "ui.key.1 should be localize context"

        # hass.localize() is captured as 'hass.localize' context
        assert key2_token is not None, "Should find ui.key.2"
        assert key2_token.data['context'] == 'hass.localize', "ui.key.2 should be hass.localize context"

    def test_parse_file_with_fixture_file(
        self, tmp_path: Path
    ) -> None:
        """Test parsing using the actual fixture file."""
        # Create the fixture file
        fixture_dir = tmp_path / "fixtures"
        fixture_dir.mkdir()
        fixture_file = fixture_dir / "test_component.ts"
        fixture_file.write_text(SAMPLE_TYPESCRIPT_CONTENT)

        adapter = TypeScriptAdapter()
        result = adapter.parse_file(fixture_file)

        assert result.file_path == fixture_file
        assert 'HaDialog' in result.raw_content
        assert 'BubbleCard' in result.raw_content

    def test_adapter_returns_valid_parse_result_structure(
        self, adapter: TypeScriptAdapter, sample_ts_file: Path
    ) -> None:
        """Test that parse_file returns a properly structured ParseResult."""
        result = adapter.parse_file(sample_ts_file)

        # Check ParseResult structure
        assert hasattr(result, 'file_path')
        assert hasattr(result, 'ast_tree')
        assert hasattr(result, 'raw_content')
        assert hasattr(result, 'dependencies')

        # Verify types
        assert isinstance(result.file_path, Path)
        assert isinstance(result.raw_content, str)
        assert isinstance(result.dependencies, tuple)

    def test_lit_component_properties_and_states(
        self, tmp_path: Path
    ) -> None:
        """Test that LitComponentExtractor extracts properties and states.

        Note: The regex-based extractor requires explicit 'name:' option in property
        decorators to extract property names. The regex pattern for word characters only matches
        word characters, so hyphens in names are not supported.
        State extraction works via @state() detection.
        """
        ts_content = '''
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
        '''

        ts_file = tmp_path / "properties_test.ts"
        ts_file.write_text(ts_content)

        extractor = LitComponentExtractor()
        raw_content = ts_file.read_text()

        tokens = extractor.extract(None, raw_content, ts_file)
        lit_tokens = [t for t in tokens if t.token_type == 'lit_component']

        assert len(lit_tokens) >= 1
        my_card = next((t for t in lit_tokens if t.data['tag_name'] == 'my-card'), None)
        assert my_card is not None, "Should find my-card component"

        # Check properties - regex extracts from name: 'propertyName' in decorator
        # Note: regex (\w+) does NOT match names with hyphens like 'card-title'
        properties = my_card.data['properties']
        assert len(properties) >= 2, f"Expected at least 2 properties, got {len(properties)}"
        assert 'cardTitle' in properties
        assert 'loading' in properties

        # Check states - @state() decorator is detected
        states = my_card.data['states']
        assert len(states) >= 1, f"Expected at least 1 state, got {len(states)}"

        # Check observed attributes (derived from property names)
        observed = my_card.data['observed_attributes']
        assert len(observed) >= 2, f"Expected at least 2 observed attributes, got {len(observed)}"
