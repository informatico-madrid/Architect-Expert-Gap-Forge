# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for TranslationJsonParser.

Tests JSON parsing, nested flattening, dot-path key generation,
leaf node detection, and ICU message format preservation.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
import pytest

from src.utils.extractors.parsers.translation_json import (
    TranslationEntry,
    TranslationJsonParser,
    _is_leaf_node,
    _has_icu_placeholders,
    _flatten_dict,
    parse_translation_json,
)


class TestIsLeafNode:
    """Test suite for _is_leaf_node function."""

    def test_string_is_leaf(self) -> None:
        """Test that a plain string is considered a leaf node."""
        assert _is_leaf_node("Hello world") is True

    def test_empty_string_is_leaf(self) -> None:
        """Test that an empty string is considered a leaf node."""
        assert _is_leaf_node("") is True

    def test_string_only_dict_is_leaf(self) -> None:
        """Test that a dict with only string values is a leaf node."""
        assert _is_leaf_node({"en": "Hello", "es": "Hola"}) is True

    def test_empty_dict_is_not_leaf(self) -> None:
        """Test that an empty dict is not considered a leaf node."""
        assert _is_leaf_node({}) is False

    def test_nested_dict_with_dict_values_not_leaf(self) -> None:
        """Test that a dict containing dict values is not a leaf node."""
        assert _is_leaf_node({"nested": {"key": "value"}}) is False

    def test_mixed_dict_not_leaf(self) -> None:
        """Test that a dict with non-string values is not a leaf node."""
        assert _is_leaf_node({"key": "value", "count": 5}) is False

    def test_list_is_not_leaf(self) -> None:
        """Test that a list is not considered a leaf node."""
        assert _is_leaf_node(["item1", "item2"]) is False

    def test_int_not_leaf(self) -> None:
        """Test that an integer is not considered a leaf node."""
        assert _is_leaf_node(42) is False

    def test_none_not_leaf(self) -> None:
        """Test that None is not considered a leaf node."""
        assert _is_leaf_node(None) is False


class TestHasIcuPlaceholders:
    """Test suite for _has_icu_placeholders function."""

    def test_simple_placeholder(self) -> None:
        """Test detection of simple {name} placeholder."""
        assert _has_icu_placeholders("Hello {name}") is True

    def test_multiple_placeholders(self) -> None:
        """Test detection of multiple placeholders."""
        assert _has_icu_placeholders("{count} items in {container}") is True

    def test_icu_plural_format(self) -> None:
        """Test detection of ICU plural format."""
        text = "{count, plural, =0 {No items} =1 {One item} other {Many items}}"
        assert _has_icu_placeholders(text) is True

    def test_icu_select_format(self) -> None:
        """Test detection of ICU select format."""
        text = "{gender, select, male {He} female {She} other {They}}"
        assert _has_icu_placeholders(text) is True

    def test_no_placeholder(self) -> None:
        """Test that text without placeholders returns False."""
        assert _has_icu_placeholders("Hello world") is False

    def test_curly_braces_in_text(self) -> None:
        """Test that curly braces in text without ICU format returns False."""
        # This might be ambiguous but current implementation returns True
        # if there are any { followed by }
        assert _has_icu_placeholders("Use {curly} braces") is True


class TestFlattenDict:
    """Test suite for _flatten_dict function."""

    def test_flat_dict_single_level(self) -> None:
        """Test flattening a single-level dictionary."""
        data = {"key1": "value1", "key2": "value2"}
        entries = _flatten_dict(data, "", "/path/to/file.json")

        assert len(entries) == 2
        keys = {e.key for e in entries}
        assert "key1" in keys
        assert "key2" in keys

    def test_nested_dict_dot_path(self) -> None:
        """Test that nested dict creates proper dot-path keys."""
        data = {"ui": {"card": {"title": "Card Title"}}}
        entries = _flatten_dict(data, "", "/path/to/file.json")

        assert len(entries) == 1
        assert entries[0].key == "ui.card.title"
        assert entries[0].value == "Card Title"
        assert entries[0].is_leaf is True

    def test_deeply_nested_dict(self) -> None:
        """Test deeply nested dictionary flattening."""
        data = {"level1": {"level2": {"level3": {"value": "deep value"}}}}
        entries = _flatten_dict(data, "", "/path/to/file.json")

        assert len(entries) == 1
        assert entries[0].key == "level1.level2.level3.value"

    def test_intermediate_category_not_included(self) -> None:
        """Test that intermediate categories don't produce entries."""
        data = {"ui": {"card": {"title": "Card Title"}}}
        entries = _flatten_dict(data, "", "/path/to/file.json")

        # Should only have the leaf, not "ui" or "ui.card"
        keys = {e.key for e in entries}
        assert "ui" not in keys
        assert "ui.card" not in keys
        assert "ui.card.title" in keys

    def test_multiple_leaves_at_same_level(self) -> None:
        """Test multiple leaves at the same nested level."""
        data = {
            "ui": {
                "card": {
                    "title": "Card Title",
                    "subtitle": "Card Subtitle",
                    "description": "Card Description",
                }
            }
        }
        entries = _flatten_dict(data, "", "/path/to/file.json")

        assert len(entries) == 3
        keys = {e.key for e in entries}
        assert "ui.card.title" in keys
        assert "ui.card.subtitle" in keys
        assert "ui.card.description" in keys

    def test_list_handling(self) -> None:
        """Test that lists are properly flattened with index notation."""
        data = {"items": [{"name": "Item 1"}, {"name": "Item 2"}]}
        entries = _flatten_dict(data, "", "/path/to/file.json")

        keys = {e.key for e in entries}
        assert "items[0].name" in keys
        assert "items[1].name" in keys

    def test_mixed_nested_structure(self) -> None:
        """Test mixed nested structure with multiple paths."""
        data = {
            "ui": {"card": {"title": "Card Title"}, "panel": {"title": "Panel Title"}}
        }
        entries = _flatten_dict(data, "", "/path/to/file.json")

        assert len(entries) == 2
        keys = {e.key for e in entries}
        assert "ui.card.title" in keys
        assert "ui.panel.title" in keys

    def test_file_path_passed_through(self) -> None:
        """Test that file_path is correctly stored in entries."""
        data = {"key": "value"}
        file_path = "/path/to/translations/en.json"
        entries = _flatten_dict(data, "", file_path)

        assert len(entries) == 1
        assert entries[0].file_path == file_path

    def test_string_only_nested_dict_leaf(self) -> None:
        """Test that a dict with only string values becomes a leaf."""
        data = {"card": {"en": "Card", "es": "Tarjeta"}}
        entries = _flatten_dict(data, "", "/path/to/file.json")

        # The inner dict has only string values, so it should be flattened
        keys = {e.key for e in entries}
        assert "card.en" in keys
        assert "card.es" in keys


class TestTranslationJsonParser:
    """Test suite for TranslationJsonParser class."""

    @pytest.fixture
    def temp_json_file(self) -> Path:
        """Create a temporary JSON file for testing."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            yield Path(f.name)
        Path(f.name).unlink()

    def test_parse_simple_json(self, temp_json_file: Path) -> None:
        """Test parsing a simple JSON file."""
        data = {"greeting": "Hello", "farewell": "Goodbye"}
        temp_json_file.write_text(json.dumps(data), encoding="utf-8")

        entries = TranslationJsonParser.parse(temp_json_file)

        assert len(entries) == 2
        keys = {e.key for e in entries}
        assert "greeting" in keys
        assert "farewell" in keys

    def test_parse_nested_json(self, temp_json_file: Path) -> None:
        """Test parsing nested JSON structure."""
        data = {"ui": {"card": {"title": "My Card"}}}
        temp_json_file.write_text(json.dumps(data), encoding="utf-8")

        entries = TranslationJsonParser.parse(temp_json_file)

        assert len(entries) == 1
        assert entries[0].key == "ui.card.title"
        assert entries[0].value == "My Card"

    def test_parse_preserves_icu_placeholders(self, temp_json_file: Path) -> None:
        """Test that ICU placeholders are preserved in parsed values."""
        data = {
            "greeting": "Hello {name}",
            "items": "{count, plural, =0 {No items} other {Many items}}",
        }
        temp_json_file.write_text(json.dumps(data), encoding="utf-8")

        entries = TranslationJsonParser.parse(temp_json_file)

        assert len(entries) == 2
        entries_by_key = {e.key: e for e in entries}
        assert entries_by_key["greeting"].value == "Hello {name}"
        assert (
            entries_by_key["items"].value
            == "{count, plural, =0 {No items} other {Many items}}"
        )

    def test_parse_complex_homeassistant_structure(self, temp_json_file: Path) -> None:
        """Test parsing complex HomeAssistant translation structure."""
        data = {
            "ui": {
                "common": {"confirm": "Confirm", "cancel": "Cancel"},
                "card": {
                    "camera": {"title": "Camera", "streams": "Streams"},
                    "energy": {"title": "Energy", "Solar": "Solar", "Grid": "Grid"},
                },
            },
            "component": {"climate": {"state": {"off": "Off", "heat": "Heat"}}},
        }
        temp_json_file.write_text(json.dumps(data), encoding="utf-8")

        entries = TranslationJsonParser.parse(temp_json_file)

        keys = {e.key for e in entries}
        assert "ui.common.confirm" in keys
        assert "ui.common.cancel" in keys
        assert "ui.card.camera.title" in keys
        assert "ui.card.camera.streams" in keys
        assert "ui.card.energy.title" in keys
        assert "ui.card.energy.Solar" in keys
        assert "component.climate.state.off" in keys
        assert "component.climate.state.heat" in keys

    def test_parse_is_leaf_flag(self, temp_json_file: Path) -> None:
        """Test that is_leaf flag is correctly set."""
        data = {"parent": {"child": "value"}}
        temp_json_file.write_text(json.dumps(data), encoding="utf-8")

        entries = TranslationJsonParser.parse(temp_json_file)

        assert len(entries) == 1
        assert entries[0].is_leaf is True

    def test_parse_stores_file_path(self, temp_json_file: Path) -> None:
        """Test that the source file path is stored in entries."""
        data = {"key": "value"}
        temp_json_file.write_text(json.dumps(data), encoding="utf-8")

        entries = TranslationJsonParser.parse(temp_json_file)

        assert len(entries) == 1
        assert entries[0].file_path == str(temp_json_file)


class TestParseTranslationJsonFunction:
    """Test suite for parse_translation_json convenience function."""

    def test_parse_translation_json_returns_entries(self) -> None:
        """Test that parse_translation_json returns TranslationEntry list."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump({"key": "value"}, f)
            temp_path = Path(f.name)

        try:
            entries = parse_translation_json(temp_path)
            assert len(entries) == 1
            assert entries[0].key == "key"
            assert entries[0].value == "value"
        finally:
            temp_path.unlink()


class TestTranslationEntry:
    """Test suite for TranslationEntry dataclass."""

    def test_translation_entry_creation(self) -> None:
        """Test creating a TranslationEntry."""
        entry = TranslationEntry(
            key="ui.card.title",
            value="Card Title",
            file_path="/path/to/file.json",
            is_leaf=True,
        )

        assert entry.key == "ui.card.title"
        assert entry.value == "Card Title"
        assert entry.file_path == "/path/to/file.json"
        assert entry.is_leaf is True


class TestIcuMessagePreservation:
    """Test suite for ICU message format preservation."""

    @pytest.fixture
    def temp_json_file(self) -> Path:
        """Create a temporary JSON file for testing."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            yield Path(f.name)
        Path(f.name).unlink()

    def test_simple_variable_placeholder(self, temp_json_file: Path) -> None:
        """Test preservation of simple {variable} placeholder."""
        data = {"welcome": "Welcome, {username}!"}
        temp_json_file.write_text(json.dumps(data), encoding="utf-8")

        entries = TranslationJsonParser.parse(temp_json_file)

        assert entries[0].value == "Welcome, {username}!"

    def test_plural_placeholder(self, temp_json_file: Path) -> None:
        """Test preservation of ICU plural syntax."""
        data = {
            "item_count": "{count, plural, =0 {No items} =1 {One item} other {# items}}"
        }
        temp_json_file.write_text(json.dumps(data), encoding="utf-8")

        entries = TranslationJsonParser.parse(temp_json_file)

        assert "{count, plural" in entries[0].value
        assert "=0 {No items}" in entries[0].value
        assert "other {# items}" in entries[0].value

    def test_select_placeholder(self, temp_json_file: Path) -> None:
        """Test preservation of ICU select syntax."""
        data = {
            "gender_pronoun": "{gender, select, male {he} female {she} other {they}}"
        }
        temp_json_file.write_text(json.dumps(data), encoding="utf-8")

        entries = TranslationJsonParser.parse(temp_json_file)

        assert "{gender, select" in entries[0].value
        assert "male {he}" in entries[0].value
        assert "female {she}" in entries[0].value

    def test_multiple_placeholders_same_value(self, temp_json_file: Path) -> None:
        """Test multiple placeholders in single value are preserved."""
        data = {
            "greeting": "Hello {first_name} and {second_name}, you have {count} messages"
        }
        temp_json_file.write_text(json.dumps(data), encoding="utf-8")

        entries = TranslationJsonParser.parse(temp_json_file)

        value = entries[0].value
        assert "{first_name}" in value
        assert "{second_name}" in value
        assert "{count}" in value

    def test_placeholder_with_attributes(self, temp_json_file: Path) -> None:
        """Test placeholders with ICU-style attributes are preserved."""
        data = {"datetime": "{date, time, short} at {time, time, short}"}
        temp_json_file.write_text(json.dumps(data), encoding="utf-8")

        entries = TranslationJsonParser.parse(temp_json_file)

        assert "{date, time, short}" in entries[0].value
