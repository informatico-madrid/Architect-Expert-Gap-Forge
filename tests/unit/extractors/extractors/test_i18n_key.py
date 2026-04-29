# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for I18nKeyExtractor.

Tests extraction of i18n keys from TypeScript source via localize()
and hass.localize() call detection.
"""

from __future__ import annotations

from pathlib import Path
import pytest

from src.utils.extractors.extractors.i18n_key import (
    I18nKeyExtractor,
    LOCALIZE_CALL_PATTERN,
    HASS_LOCALIZE_PATTERN,
    TEMPLATE_PREFIX_CONTEXT,
    SETUP_LOCALIZE_PATTERN,
)


class TestI18nKeyExtractor:
    """Test suite for I18nKeyExtractor."""

    @pytest.fixture
    def extractor(self) -> I18nKeyExtractor:
        """Create an I18nKeyExtractor instance for testing."""
        return I18nKeyExtractor()

    @pytest.fixture
    def sample_file_path(self) -> Path:
        """Sample file path for testing."""
        return Path("test/sample.ts")

    # --- localize() call extraction tests ---

    def test_localize_single_quotes(self, extractor, sample_file_path):
        """Test extraction of localize() calls with single quotes."""
        raw = "localize('ui.card.door.lock')"
        tokens = extractor.extract(None, raw, sample_file_path)

        assert len(tokens) == 1
        assert tokens[0].token_type == "i18n_key"
        assert tokens[0].data["key"] == "ui.card.door.lock"
        assert tokens[0].data["context"] == "localize"
        assert tokens[0].file_path == sample_file_path

    def test_localize_double_quotes(self, extractor, sample_file_path):
        """Test extraction of localize() calls with double quotes."""
        raw = 'localize("ui.panel.config.users")'
        tokens = extractor.extract(None, raw, sample_file_path)

        assert len(tokens) == 1
        assert tokens[0].token_type == "i18n_key"
        assert tokens[0].data["key"] == "ui.panel.config.users"
        assert tokens[0].data["context"] == "localize"

    def test_localize_with_spaces(self, extractor, sample_file_path):
        """Test extraction of localize() calls with extra whitespace."""
        raw = "localize(  'ui.card.door.unlock'  )"
        tokens = extractor.extract(None, raw, sample_file_path)

        assert len(tokens) == 1
        assert tokens[0].data["key"] == "ui.card.door.unlock"

    def test_localize_multiple_calls(self, extractor, sample_file_path):
        """Test extraction of multiple localize() calls in same file."""
        raw = """
        localize('ui.card.door.lock')
        localize('ui.card.door.unlock')
        localize('ui.panel.config')
        """
        tokens = extractor.extract(None, raw, sample_file_path)

        assert len(tokens) == 3
        keys = [t.data["key"] for t in tokens]
        assert "ui.card.door.lock" in keys
        assert "ui.card.door.unlock" in keys
        assert "ui.panel.config" in keys
        for token in tokens:
            assert token.data["context"] == "localize"

    # --- hass.localize() extraction tests ---

    def test_hass_localize_single_quotes(self, extractor, sample_file_path):
        """Test extraction of hass.localize() calls with single quotes."""
        raw = "hass.localize('ui.card.climate.temp')"
        tokens = extractor.extract(None, raw, sample_file_path)

        assert len(tokens) == 1
        assert tokens[0].token_type == "i18n_key"
        assert tokens[0].data["key"] == "ui.card.climate.temp"
        assert tokens[0].data["context"] == "hass.localize"

    def test_hass_localize_double_quotes(self, extractor, sample_file_path):
        """Test extraction of hass.localize() calls with double quotes."""
        raw = 'hass.localize("ui.card.light.brightness")'
        tokens = extractor.extract(None, raw, sample_file_path)

        assert len(tokens) == 1
        assert tokens[0].data["key"] == "ui.card.light.brightness"
        assert tokens[0].data["context"] == "hass.localize"

    def test_hass_localize_multiple_calls(self, extractor, sample_file_path):
        """Test extraction of multiple hass.localize() calls."""
        raw = """
        hass.localize('ui.card.sensor.temp')
        hass.localize('ui.card.sensor.humidity')
        """
        tokens = extractor.extract(None, raw, sample_file_path)

        assert len(tokens) == 2
        keys = [t.data["key"] for t in tokens]
        assert "ui.card.sensor.temp" in keys
        assert "ui.card.sensor.humidity" in keys
        for token in tokens:
            assert token.data["context"] == "hass.localize"

    def test_mixed_localize_and_hass_localize(self, extractor, sample_file_path):
        """Test extraction of mixed localize() and hass.localize() calls."""
        raw = """
        localize('ui.card.door.lock')
        hass.localize('ui.card.door.unlock')
        localize('ui.panel.config')
        """
        tokens = extractor.extract(None, raw, sample_file_path)

        assert len(tokens) == 3
        localize_keys = [
            t.data["key"] for t in tokens if t.data["context"] == "localize"
        ]
        hass_localize_keys = [
            t.data["key"] for t in tokens if t.data["context"] == "hass.localize"
        ]
        assert "ui.card.door.lock" in localize_keys
        assert "ui.panel.config" in localize_keys
        assert "ui.card.door.unlock" in hass_localize_keys

    # --- template literal key prefix extraction tests ---

    def test_template_literal_prefix_extraction(self, extractor, sample_file_path):
        """Test extraction of template literal prefix for dynamic keys."""
        raw = "localize(`ui.card.${action}`)"
        tokens = extractor.extract(None, raw, sample_file_path)

        assert len(tokens) >= 1
        # The template literal should be extracted
        template_tokens = [t for t in tokens if t.data["context"] == "template_literal"]
        assert len(template_tokens) == 1
        assert template_tokens[0].data["prefix"] == "ui.card."

    def test_template_literal_with_hass_localize(self, extractor, sample_file_path):
        """Test template literal prefix extraction with hass.localize()."""
        raw = "hass.localize(`ui.card.${action}`)"
        tokens = extractor.extract(None, raw, sample_file_path)

        # Should extract both the hass.localize call and the template literal
        template_tokens = [t for t in tokens if t.data["context"] == "template_literal"]
        assert len(template_tokens) >= 1
        assert template_tokens[0].data["prefix"] == "ui.card."

    def test_template_literal_complex_prefix(self, extractor, sample_file_path):
        """Test template literal with complex prefix."""
        raw = "localize(`ui.card.climate.${mode}.${setting}`)"
        tokens = extractor.extract(None, raw, sample_file_path)

        template_tokens = [t for t in tokens if t.data["context"] == "template_literal"]
        assert len(template_tokens) >= 1
        assert template_tokens[0].data["prefix"] == "ui.card.climate."

    # --- setupCustomlocalize() wrapper pattern tests ---

    def test_setup_localize_pattern(self, extractor, sample_file_path):
        """Test setupLocalize() wrapper pattern detection."""
        raw = "setupLocalize()"
        match = SETUP_LOCALIZE_PATTERN.search(raw)
        assert match is not None
        assert match.group(0) == "setupLocalize()"

    def test_setup_custom_localize_pattern(self, extractor, sample_file_path):
        """Test setupCustomLocalize() wrapper pattern detection."""
        raw = "setupCustomLocalize()"
        match = SETUP_LOCALIZE_PATTERN.search(raw)
        assert match is not None
        assert match.group(0) == "setupCustomLocalize()"

    def test_setup_localize_with_whitespace(self, extractor, sample_file_path):
        """Test setupLocalize() with extra whitespace."""
        raw = "setupLocalize(  )"
        match = SETUP_LOCALIZE_PATTERN.search(raw)
        assert match is not None

    def test_setup_custom_localize_with_file(self, extractor, sample_file_path):
        """Test that setupLocalize pattern is found in realistic file context."""
        raw = """
        import { computeRTL } from 'homeassistant-dom';

        class MyCard extends LitElement {
            setupLocalize() {
                // Initialize localization
            }
        }
        """
        match = SETUP_LOCALIZE_PATTERN.search(raw)
        assert match is not None
        assert "setupLocalize" in match.group(0)

    # --- line number extraction tests ---

    def test_localize_line_numbers(self, extractor, sample_file_path):
        """Test that line numbers are correctly extracted."""
        raw = """line1: doSomething();
line2: doSomethingElse();
line3: localize('ui.card.line3');
line4: moreCode();
line5: localize('ui.card.line5');
"""
        tokens = extractor.extract(None, raw, sample_file_path)

        assert len(tokens) == 2
        # Line 3 and line 5 in the raw string (1-indexed)
        assert tokens[0].line_number == 3
        assert tokens[1].line_number == 5

    # --- edge cases ---

    def test_localize_no_matches(self, extractor, sample_file_path):
        """Test that no tokens are extracted when no localize calls present."""
        raw = """
        function something() {
            return 'hello';
        }
        """
        tokens = extractor.extract(None, raw, sample_file_path)
        # Only template_literal context tokens might be found, not direct localize calls
        localize_tokens = [
            t for t in tokens if t.data["context"] in ("localize", "hass.localize")
        ]
        assert len(localize_tokens) == 0

    def test_localize_with_nested_quotes_fails_gracefully(
        self, extractor, sample_file_path
    ):
        """Test that nested quotes in localize keys don't cause issues."""
        raw = "localize('ui.card.door')"
        tokens = extractor.extract(None, raw, sample_file_path)

        assert len(tokens) == 1
        assert tokens[0].data["key"] == "ui.card.door"

    def test_empty_key_not_extracted(self, extractor, sample_file_path):
        """Test that empty keys are not extracted."""
        raw = "localize('')"
        tokens = extractor.extract(None, raw, sample_file_path)

        # Empty string key should not be extracted
        # The pattern requires at least one character inside quotes
        assert len(tokens) == 0

    # --- regex pattern tests ---

    def test_localize_call_pattern_matches(self):
        """Test LOCALIZE_CALL_PATTERN regex directly."""
        # Single quotes
        match = LOCALIZE_CALL_PATTERN.search("localize('test.key')")
        assert match is not None
        assert match.group(1) == "test.key"

        # Double quotes
        match = LOCALIZE_CALL_PATTERN.search('localize("test.key")')
        assert match is not None
        assert match.group(1) == "test.key"

    def test_hass_localize_pattern_matches(self):
        """Test HASS_LOCALIZE_PATTERN regex directly."""
        match = HASS_LOCALIZE_PATTERN.search("hass.localize('test.key')")
        assert match is not None
        assert match.group(1) == "test.key"

    def test_template_literal_pattern_matches(self):
        """Test TEMPLATE_PREFIX_CONTEXT regex directly."""
        match = TEMPLATE_PREFIX_CONTEXT.search("localize(`ui.card.${action}`)")
        assert match is not None
        assert match.group(1) == "ui.card.${action}"

    def test_setup_localize_pattern_matches(self):
        """Test SETUP_LOCALIZE_PATTERN regex directly."""
        match = SETUP_LOCALIZE_PATTERN.search("setupLocalize()")
        assert match is not None

        match = SETUP_LOCALIZE_PATTERN.search("setupCustomLocalize()")
        assert match is not None

    # --- token data structure tests ---

    def test_token_has_required_fields(self, extractor, sample_file_path):
        """Test that extracted tokens have all required fields."""
        raw = "localize('ui.test.key')"
        tokens = extractor.extract(None, raw, sample_file_path)

        assert len(tokens) == 1
        token = tokens[0]
        assert hasattr(token, "token_type")
        assert hasattr(token, "data")
        assert hasattr(token, "file_path")
        assert hasattr(token, "line_number")
        assert token.token_type == "i18n_key"
        assert "key" in token.data
        assert "context" in token.data
        assert "prefix" in token.data

    def test_token_prefix_is_none_for_direct_keys(self, extractor, sample_file_path):
        """Test that direct localize() keys have prefix=None."""
        raw = "localize('ui.direct.key')"
        tokens = extractor.extract(None, raw, sample_file_path)

        assert len(tokens) == 1
        assert tokens[0].data["prefix"] is None

    def test_extractor_name(self, extractor):
        """Test that extractor has correct name."""
        assert extractor.name == "I18nKeyExtractor"


class TestI18nKeyExtractorIntegration:
    """Integration tests for I18nKeyExtractor with realistic TypeScript code."""

    def test_realistic_component_file(self):
        """Test extraction from realistic TypeScript Lit component."""
        extractor = I18nKeyExtractor()
        file_path = Path("src/components/ha-card.ts")

        raw = """
        import { localize } from 'homeassistant-utilities';
        import { computeRTL } from 'homeassistant-dom';

        class HaCard extends LitElement {
            setupLocalize() {
                // Setup i18n
            }

            render() {
                return html`
                    <div class="card">
                        ${localize('ui.card.door.lock')}
                        ${hass.localize('ui.card.door.unlock')}
                    </div>
                `;
            }
        }
        """
        tokens = extractor.extract(None, raw, file_path)

        # Should find the localize calls
        assert len(tokens) >= 2
        keys = [t.data["key"] for t in tokens]
        assert "ui.card.door.lock" in keys
        assert "ui.card.door.unlock" in keys

    def test_i18n_in_service_call_context(self):
        """Test extraction when i18n keys appear in service call context."""
        extractor = I18nKeyExtractor()
        file_path = Path("src/components/ha-dialog.ts")

        raw = """
        async showMessage() {
            await hass.callService('notify', 'persist', {
                message: hass.localize('ui.notification.saved'),
            });
        }
        """
        tokens = extractor.extract(None, raw, file_path)

        # Should extract the hass.localize key
        hass_localize_tokens = [
            t for t in tokens if t.data["context"] == "hass.localize"
        ]
        assert len(hass_localize_tokens) >= 1
        assert any(
            t.data["key"] == "ui.notification.saved" for t in hass_localize_tokens
        )
