# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for ServiceCallExtractor.

Tests hass.callService() extraction for Home Assistant service calls,
including domain/service extraction, entity_id parsing, and hass prefix handling.
"""

from __future__ import annotations

from pathlib import Path
import pytest

from src.utils.extractors.extractors.service_call import (
    ServiceCallExtractor,
)


class TestServiceCallExtractor:
    """Test suite for ServiceCallExtractor."""

    @pytest.fixture
    def extractor(self) -> ServiceCallExtractor:
        """Create a ServiceCallExtractor instance for testing."""
        return ServiceCallExtractor()

    # ========================================================================
    # Basic callService Detection Tests
    # ========================================================================

    def test_detects_simple_callservice(self, extractor: ServiceCallExtractor) -> None:
        """Test detection of simple hass.callService() call."""
        raw = """
        hass.callService('light', 'turn_on');
        """
        tokens = extractor.extract(None, raw)

        assert len(tokens) == 1
        token = tokens[0]
        assert token.token_type == "service_call"
        assert token.data["domain"] == "light"
        assert token.data["service"] == "turn_on"

    def test_detects_callservice_with_double_quotes(
        self, extractor: ServiceCallExtractor
    ) -> None:
        """Test detection with double-quoted strings."""
        raw = """
        hass.callService("cover", "open_cover");
        """
        tokens = extractor.extract(None, raw)

        assert len(tokens) == 1
        assert tokens[0].data["domain"] == "cover"
        assert tokens[0].data["service"] == "open_cover"

    # ========================================================================
    # Domain and Service Extraction Tests
    # ========================================================================

    def test_extracts_domain_and_service(self, extractor: ServiceCallExtractor) -> None:
        """Test extraction of domain and service name."""
        raw = """
        hass.callService('climate', 'set_temperature', { entity_id: 'climate.living_room' });
        """
        tokens = extractor.extract(None, raw)

        assert len(tokens) == 1
        token = tokens[0]
        assert token.data["domain"] == "climate"
        assert token.data["service"] == "set_temperature"

    def test_extracts_multiple_service_calls(
        self, extractor: ServiceCallExtractor
    ) -> None:
        """Test extraction of multiple service calls in same file."""
        raw = """
        hass.callService('light', 'turn_on', { entity_id: 'light.living_room' });
        hass.callService('light', 'turn_off', { entity_id: 'light.bedroom' });
        hass.callService('cover', 'open_cover', { entity_id: 'cover.garage' });
        """
        tokens = extractor.extract(None, raw)

        assert len(tokens) == 3
        assert tokens[0].data["domain"] == "light"
        assert tokens[0].data["service"] == "turn_on"
        assert tokens[1].data["domain"] == "light"
        assert tokens[1].data["service"] == "turn_off"
        assert tokens[2].data["domain"] == "cover"
        assert tokens[2].data["service"] == "open_cover"

    # ========================================================================
    # entity_id Extraction Tests
    # ========================================================================

    def test_extracts_single_entity_id(self, extractor: ServiceCallExtractor) -> None:
        """Test extraction of single entity_id from serviceData."""
        raw = """
        hass.callService('light', 'turn_on', { entity_id: 'light.living_room' });
        """
        tokens = extractor.extract(None, raw)

        assert len(tokens) == 1
        assert tokens[0].data["entity_ids"] == ["light.living_room"]

    def test_extracts_multiple_entity_ids_array(
        self, extractor: ServiceCallExtractor
    ) -> None:
        """Test extraction of multiple entity_ids from array in serviceData."""
        raw = """
        hass.callService('light', 'turn_on', {
            entity_id: ['light.living_room', 'light.bedroom', 'light.kitchen']
        });
        """
        tokens = extractor.extract(None, raw)

        assert len(tokens) == 1
        assert len(tokens[0].data["entity_ids"]) == 3
        assert "light.living_room" in tokens[0].data["entity_ids"]
        assert "light.bedroom" in tokens[0].data["entity_ids"]
        assert "light.kitchen" in tokens[0].data["entity_ids"]

    def test_extracts_entity_id_with_single_quotes(
        self, extractor: ServiceCallExtractor
    ) -> None:
        """Test extraction with single-quoted entity_id."""
        raw = """
        hass.callService('switch', 'turn_on', { entity_id: 'switch.ac_unit' });
        """
        tokens = extractor.extract(None, raw)

        assert len(tokens) == 1
        assert tokens[0].data["entity_ids"] == ["switch.ac_unit"]

    def test_extracts_no_entity_id_when_absent(
        self, extractor: ServiceCallExtractor
    ) -> None:
        """Test that entity_ids is empty when no entity_id in serviceData."""
        raw = """
        hass.callService('homeassistant', 'turn_on');
        """
        tokens = extractor.extract(None, raw)

        assert len(tokens) == 1
        assert tokens[0].data["entity_ids"] == []

    # ========================================================================
    # Hass Prefix Tests (this.hass, context._hass, hass)
    # ========================================================================

    def test_detects_plain_hass_prefix(self, extractor: ServiceCallExtractor) -> None:
        """Test detection with plain 'hass' prefix."""
        raw = """
        hass.callService('light', 'turn_on');
        """
        tokens = extractor.extract(None, raw)

        assert len(tokens) == 1
        assert tokens[0].data["hass_prefix"] == "hass"

    def test_detects_this_hass_prefix(self, extractor: ServiceCallExtractor) -> None:
        """Test detection with 'this.hass' prefix (TypeScript)."""
        raw = """
        this.hass.callService('light', 'turn_on', { entity_id: 'light.living_room' });
        """
        tokens = extractor.extract(None, raw)

        assert len(tokens) == 1
        assert tokens[0].data["hass_prefix"] == "this.hass"

    def test_detects_context_underscore_hass_prefix(
        self, extractor: ServiceCallExtractor
    ) -> None:
        """Test detection with 'context._hass' prefix (Bubble-Card JS)."""
        raw = """
        context._hass.callService('fan', 'turn_on', { entity_id: 'fan.ceiling' });
        """
        tokens = extractor.extract(None, raw)

        assert len(tokens) == 1
        assert tokens[0].data["hass_prefix"] == "context._hass"

    def test_mixed_hass_prefixes_in_file(self, extractor: ServiceCallExtractor) -> None:
        """Test extraction with mixed hass prefixes in same file."""
        raw = """
        this.hass.callService('light', 'turn_on', { entity_id: 'light.living_room' });
        hass.callService('light', 'turn_off', { entity_id: 'light.bedroom' });
        context._hass.callService('fan', 'toggle', { entity_id: 'fan.ceiling' });
        """
        tokens = extractor.extract(None, raw)

        assert len(tokens) == 3
        assert tokens[0].data["hass_prefix"] == "this.hass"
        assert tokens[1].data["hass_prefix"] == "hass"
        assert tokens[2].data["hass_prefix"] == "context._hass"

    # ========================================================================
    # Line Number Tests
    # ========================================================================

    def test_line_number_correct_for_single_call(
        self, extractor: ServiceCallExtractor
    ) -> None:
        """Test line number is correctly reported."""
        raw = """

        hass.callService('light', 'turn_on');
        """
        tokens = extractor.extract(None, raw)

        assert len(tokens) == 1
        assert tokens[0].line_number == 3

    def test_line_numbers_correct_for_multiple_calls(
        self, extractor: ServiceCallExtractor
    ) -> None:
        """Test line numbers for multiple calls."""
        raw = """
hass.callService('light', 'turn_on');
hass.callService('cover', 'open_cover');
        """
        tokens = extractor.extract(None, raw)

        assert len(tokens) == 2
        assert tokens[0].line_number == 2
        assert tokens[1].line_number == 3

    # ========================================================================
    # File Path Tests
    # ========================================================================

    def test_file_path_stored_in_token(self, extractor: ServiceCallExtractor) -> None:
        """Test that file_path is correctly stored in token."""
        raw = "hass.callService('light', 'turn_on');"
        file_path = Path("/path/to/test/file.ts")

        tokens = extractor.extract(None, raw, file_path)

        assert len(tokens) == 1
        assert tokens[0].file_path == file_path

    # ========================================================================
    # Service Domains Found in HomeAssistant Tests
    # ========================================================================

    def test_various_homeassistant_domains(
        self, extractor: ServiceCallExtractor
    ) -> None:
        """Test extraction for various HomeAssistant domains."""
        raw = """
        hass.callService('cover', 'open_cover');
        hass.callService('light', 'toggle');
        hass.callService('climate', 'set_temperature');
        hass.callService('media_player', 'volume_up');
        hass.callService('fan', 'oscillate');
        hass.callService('lock', 'lock');
        hass.callService('vacuum', 'start');
        hass.callService('humidifier', 'set_humidity');
        hass.callService('update', 'install');
        hass.callService('input_number', 'set_value');
        hass.callService('input_select', 'select_next');
        hass.callService('select', 'select_option');
        hass.callService('alarm_control_panel', 'alarm_arm_home');
        """
        tokens = extractor.extract(None, raw)

        assert len(tokens) == 13
        domains = [t.data["domain"] for t in tokens]
        assert "cover" in domains
        assert "light" in domains
        assert "climate" in domains
        assert "media_player" in domains
        assert "fan" in domains
        assert "lock" in domains
        assert "vacuum" in domains
        assert "humidifier" in domains
        assert "update" in domains
        assert "input_number" in domains
        assert "input_select" in domains
        assert "select" in domains
        assert "alarm_control_panel" in domains

    # ========================================================================
    # Complex ServiceData Tests
    # ========================================================================

    def test_service_data_with_multiple_properties(
        self, extractor: ServiceCallExtractor
    ) -> None:
        """Test extraction when serviceData has multiple properties."""
        raw = """
        hass.callService('climate', 'set_temperature', {
            entity_id: 'climate.living_room',
            temperature: 22,
            hvac_mode: 'heat'
        });
        """
        tokens = extractor.extract(None, raw)

        assert len(tokens) == 1
        assert tokens[0].data["entity_ids"] == ["climate.living_room"]
        assert tokens[0].data["domain"] == "climate"
        assert tokens[0].data["service"] == "set_temperature"

    def test_service_call_without_service_data(
        self, extractor: ServiceCallExtractor
    ) -> None:
        """Test extraction when callService has no serviceData argument."""
        raw = """
        hass.callService('homeassistant', 'restart');
        """
        tokens = extractor.extract(None, raw)

        assert len(tokens) == 1
        assert tokens[0].data["domain"] == "homeassistant"
        assert tokens[0].data["service"] == "restart"
        assert tokens[0].data["entity_ids"] == []

    # ========================================================================
    # Edge Cases
    # ========================================================================

    def test_no_callservice_returns_empty(
        self, extractor: ServiceCallExtractor
    ) -> None:
        """Test that no tokens are returned when no callService present."""
        raw = """
        const light = 'light.living_room';
        hass.turnOn(light);
        """
        tokens = extractor.extract(None, raw)

        assert len(tokens) == 0

    def test_callsevice_misspelled_returns_empty(
        self, extractor: ServiceCallExtractor
    ) -> None:
        """Test that misspelled callService is not matched."""
        raw = """
        hass.callServiceExtra('light', 'turn_on');
        """
        tokens = extractor.extract(None, raw)

        assert len(tokens) == 0

    def test_call_in_comment_matched_by_regex_fallback(
        self, extractor: ServiceCallExtractor
    ) -> None:
        """Test that callService in comments IS matched by regex fallback.

        Note: v1 regex fallback (~85% coverage) does not filter comments.
        This is a known limitation - AST parsing would be needed to exclude.
        """
        raw = """
        // hass.callService('light', 'turn_on');
        const x = 1;
        """
        tokens = extractor.extract(None, raw)

        # Regex fallback matches any occurrence in raw text
        assert len(tokens) == 1

    def test_call_in_string_matched_by_regex_fallback(
        self, extractor: ServiceCallExtractor
    ) -> None:
        """Test that callService in strings IS matched by regex fallback.

        Note: v1 regex fallback (~85% coverage) does not filter string literals.
        This is a known limitation - AST parsing would be needed to exclude.
        """
        raw = """
        const code = "hass.callService('light', 'turn_on');";
        """
        tokens = extractor.extract(None, raw)

        # Regex fallback matches any occurrence in raw text
        assert len(tokens) == 1

    # ========================================================================
    # Name Property Test
    # ========================================================================

    def test_extractor_has_name_property(self, extractor: ServiceCallExtractor) -> None:
        """Test that extractor has correct name property."""
        assert extractor.name == "ServiceCallExtractor"
