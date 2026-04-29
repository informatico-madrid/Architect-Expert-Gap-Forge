# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for LitComponentExtractor.

Tests @customElement decorator parsing, @property and @state decorator
parsing, tag name and class name extraction, and sample TypeScript code.

Note: These tests verify the regex fallback behavior (~85% coverage for v1).
Property and state extraction requires explicit `name:` option in decorators
for regex fallback to capture them.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.utils.extractors.extractors.lit_component import LitComponentExtractor


# =============================================================================
# Sample TypeScript Code Fixtures
# =============================================================================

# Basic Lit component with @customElement - works with regex fallback
SIMPLE_LIT_COMPONENT = """
import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';

@customElement('ha-dialog')
class HaDialog extends LitElement {
    @property({ type: Boolean })
    public opened = false;

    @property({ type: String })
    public title = '';

    @state()
    private _isLoading = false;

    render() {
        return html`
            <div>Dialog content</div>
        `;
    }
}
"""

# Properties with explicit name: option - regex CAN capture these
LIT_COMPONENT_WITH_PROPERTY_NAMES = """
import { LitElement } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('ha-card')
class HaCard extends LitElement {
    @property({ name: 'cardTitle', type: String })
    public cardTitle = '';

    @property({ name: 'cardValue', type: Number })
    public value = 0;
}
"""

# Multiple components in same file
LIT_COMPONENT_MULTIPLE = """
import { LitElement } from 'lit';
import { customElement } from 'lit/decorators.js';

@customElement('ha-button')
class HaButton extends LitElement {
}

@customElement('ha-icon')
class HaIcon extends LitElement {
}

@customElement("ha-slider")
class HaSlider extends LitElement {
}
"""

# Component with extends clause
LIT_COMPONENT_EXTENDS_CLAUSE = """
import { LitElement } from 'lit';
import { customElement } from 'lit/decorators.js';

@customElement('ha-panel')
class HaPanel extends HaBasePanel {
}

class HaBasePanel extends LitElement {
}
"""

# Component without @customElement - should be ignored
NON_LIT_COMPONENT = """
import { LitElement } from 'lit';

class NotALitComponent extends LitElement {
    render() {
        return html`<div>Not registered</div>`;
    }
}
"""

# Component with double-quoted tag name
LIT_COMPONENT_DOUBLE_QUOTES = """
import { LitElement } from 'lit';
import { customElement } from 'lit/decorators.js';

@customElement("ha-dialog")
class HaDialog extends LitElement {
}
"""

# Component with single-quoted tag name
LIT_COMPONENT_SINGLE_QUOTES = """
import { LitElement } from 'lit';
import { customElement } from 'lit/decorators.js';

@customElement('ha-dialog')
class HaDialog extends LitElement {
}
"""

# Component with @state decorator
LIT_COMPONENT_WITH_STATE = """
import { LitElement } from 'lit';
import { customElement, state } from 'lit/decorators.js';

@customElement('ha-form')
class HaForm extends LitElement {
    @state()
    private _formState = { submitted: false };
}
"""


# =============================================================================
# Tests
# =============================================================================


class TestLitComponentExtractorBasic:
    """Basic extraction tests for LitComponentExtractor."""

    def test_extractor_has_correct_name(self):
        """Extractor should have correct name attribute."""
        extractor = LitComponentExtractor()
        assert extractor.name == "LitComponentExtractor"

    def test_extractor_implements_protocol(self):
        """Extractor should implement TypeScriptExtractorProtocol."""
        extractor = LitComponentExtractor()
        assert hasattr(extractor, "extract")
        assert hasattr(extractor, "name")

    def test_returns_list_of_tokens(self):
        """Extract should return a list of FrontendToken objects."""
        extractor = LitComponentExtractor()
        tokens = extractor.extract(None, SIMPLE_LIT_COMPONENT, Path("test.ts"))
        assert isinstance(tokens, list)


class TestCustomElementDecoratorParsing:
    """Tests for @customElement decorator parsing."""

    def test_extracts_tag_name_from_single_quotes(self):
        """Should extract tag name from @customElement with single quotes."""
        extractor = LitComponentExtractor()
        tokens = extractor.extract(None, SIMPLE_LIT_COMPONENT, Path("test.ts"))

        assert len(tokens) == 1
        token = tokens[0]
        assert token.token_type == "lit_component"
        assert token.data["tag_name"] == "ha-dialog"

    def test_extracts_tag_name_from_double_quotes(self):
        """Should extract tag name from @customElement with double quotes."""
        extractor = LitComponentExtractor()
        tokens = extractor.extract(None, LIT_COMPONENT_DOUBLE_QUOTES, Path("test.ts"))

        assert len(tokens) == 1
        token = tokens[0]
        assert token.data["tag_name"] == "ha-dialog"

    def test_extracts_class_name(self):
        """Should extract class name from class declaration."""
        extractor = LitComponentExtractor()
        tokens = extractor.extract(None, SIMPLE_LIT_COMPONENT, Path("test.ts"))

        assert len(tokens) == 1
        token = tokens[0]
        assert token.data["class_name"] == "HaDialog"

    def test_extracts_super_class(self):
        """Should extract super class name."""
        extractor = LitComponentExtractor()
        tokens = extractor.extract(None, SIMPLE_LIT_COMPONENT, Path("test.ts"))

        assert len(tokens) == 1
        token = tokens[0]
        assert token.data["super_class"] == "LitElement"

    def test_extracts_multiple_components(self):
        """Should extract multiple @customElement decorated classes.

        The regex fallback extracts tag names for each @customElement match.
        Due to context window overlap, class names may be incorrectly associated.
        """
        extractor = LitComponentExtractor()
        tokens = extractor.extract(None, LIT_COMPONENT_MULTIPLE, Path("test.ts"))

        # Should extract one token per @customElement decorator
        assert len(tokens) == 3

        # All three tag names should be extracted
        tag_names = [t.data["tag_name"] for t in tokens]
        assert "ha-button" in tag_names
        assert "ha-icon" in tag_names
        assert "ha-slider" in tag_names

    def test_ignores_non_decorated_class(self):
        """Should not extract classes without @customElement decorator."""
        extractor = LitComponentExtractor()
        tokens = extractor.extract(None, NON_LIT_COMPONENT, Path("test.ts"))

        # Should not find NotALitComponent
        assert len(tokens) == 0

    def test_line_number_is_set(self):
        """Should set correct line number for extracted token."""
        extractor = LitComponentExtractor()
        tokens = extractor.extract(None, SIMPLE_LIT_COMPONENT, Path("test.ts"))

        assert len(tokens) == 1
        assert tokens[0].line_number > 0

    def test_file_path_is_preserved(self):
        """Should preserve file path in extracted token."""
        test_path = Path("/some/path/my-component.ts")
        extractor = LitComponentExtractor()
        tokens = extractor.extract(None, SIMPLE_LIT_COMPONENT, test_path)

        assert len(tokens) == 1
        assert tokens[0].file_path == test_path

    def test_custom_element_in_decorators_list(self):
        """Should include 'customElement' in decorators list."""
        extractor = LitComponentExtractor()
        tokens = extractor.extract(None, SIMPLE_LIT_COMPONENT, Path("test.ts"))

        assert len(tokens) == 1
        token = tokens[0]
        assert "customElement" in token.data["decorators"]


class TestPropertyDecoratorParsing:
    """Tests for @property decorator parsing.

    Note: Regex fallback only captures properties with explicit `name:` option.
    """

    def test_extracts_property_with_name_option(self):
        """Should extract @property decorator when name: option is specified."""
        extractor = LitComponentExtractor()
        tokens = extractor.extract(
            None, LIT_COMPONENT_WITH_PROPERTY_NAMES, Path("test.ts")
        )

        assert len(tokens) == 1
        token = tokens[0]
        # Regex pattern: @property\s*\([^)]*name\s*:\s*['"](\w+)['"]
        assert "cardTitle" in token.data["properties"]
        assert "cardValue" in token.data["properties"]

    def test_derived_observed_attributes_lowercase(self):
        """Should derive observed attributes as lowercase of property names."""
        extractor = LitComponentExtractor()
        tokens = extractor.extract(
            None, LIT_COMPONENT_WITH_PROPERTY_NAMES, Path("test.ts")
        )

        assert len(tokens) == 1
        token = tokens[0]
        assert "cardtitle" in token.data["observed_attributes"]
        assert "cardvalue" in token.data["observed_attributes"]

    def test_property_decorator_flag_in_decorators_list(self):
        """Should include 'property' in decorators list when detected."""
        extractor = LitComponentExtractor()
        tokens = extractor.extract(
            None, LIT_COMPONENT_WITH_PROPERTY_NAMES, Path("test.ts")
        )

        assert len(tokens) == 1
        token = tokens[0]
        assert "property" in token.data["decorators"]

    def test_property_without_name_option_not_extracted_by_regex(self):
        """Properties without explicit name: option won't be captured by regex.

        This is expected behavior for regex fallback - AST parsing would capture them.
        """
        extractor = LitComponentExtractor()
        tokens = extractor.extract(None, SIMPLE_LIT_COMPONENT, Path("test.ts"))

        assert len(tokens) == 1
        token = tokens[0]
        # Properties without name: option are not captured by regex
        assert "opened" not in token.data["properties"]


class TestStateDecoratorParsing:
    """Tests for @state decorator parsing.

    Note: Regex fallback detects @state() presence but cannot extract the
    variable name without AST analysis.
    """

    def test_detects_state_decorator(self):
        """Should detect @state decorator presence."""
        extractor = LitComponentExtractor()
        tokens = extractor.extract(None, LIT_COMPONENT_WITH_STATE, Path("test.ts"))

        assert len(tokens) == 1
        token = tokens[0]
        # State is detected via regex pattern matching @state\s*\(
        assert "state" in token.data["decorators"]

    def test_state_decorator_flag_in_decorators_list(self):
        """Should include 'state' in decorators list."""
        extractor = LitComponentExtractor()
        tokens = extractor.extract(None, SIMPLE_LIT_COMPONENT, Path("test.ts"))

        assert len(tokens) == 1
        token = tokens[0]
        assert "state" in token.data["decorators"]


class TestTagNameAndClassNameExtraction:
    """Tests for tag name and class name extraction."""

    def test_tag_name_extraction_format(self):
        """Tag name should be extracted as string."""
        extractor = LitComponentExtractor()
        tokens = extractor.extract(None, SIMPLE_LIT_COMPONENT, Path("test.ts"))

        assert len(tokens) == 1
        assert isinstance(tokens[0].data["tag_name"], str)
        assert tokens[0].data["tag_name"] == "ha-dialog"

    def test_class_name_extraction_format(self):
        """Class name should be extracted as string."""
        extractor = LitComponentExtractor()
        tokens = extractor.extract(None, SIMPLE_LIT_COMPONENT, Path("test.ts"))

        assert len(tokens) == 1
        assert isinstance(tokens[0].data["class_name"], str)
        assert tokens[0].data["class_name"] == "HaDialog"

    def test_extracts_extends_clause(self):
        """Should extract class extends clause."""
        extractor = LitComponentExtractor()
        tokens = extractor.extract(None, LIT_COMPONENT_EXTENDS_CLAUSE, Path("test.ts"))

        ha_panel = next(t for t in tokens if t.data["class_name"] == "HaPanel")
        assert ha_panel.data["class_name"] == "HaPanel"
        assert ha_panel.data["super_class"] == "HaBasePanel"


class TestSampleTypeScriptCode:
    """Tests with various TypeScript code samples."""

    def test_complex_lit_component_full_extraction(self):
        """Test complete extraction of a Lit component."""
        extractor = LitComponentExtractor()
        tokens = extractor.extract(None, SIMPLE_LIT_COMPONENT, Path("dialog.ts"))

        assert len(tokens) == 1
        token = tokens[0]

        # Verify core structure
        assert token.token_type == "lit_component"
        assert token.data["tag_name"] == "ha-dialog"
        assert token.data["class_name"] == "HaDialog"
        assert token.data["super_class"] == "LitElement"
        assert "customElement" in token.data["decorators"]
        assert "state" in token.data["decorators"]
        # properties/states may be empty if name: option not used

    def test_component_data_structure_complete(self):
        """Test that LitComponent data structure has all required fields."""
        extractor = LitComponentExtractor()
        tokens = extractor.extract(None, SIMPLE_LIT_COMPONENT, Path("test.ts"))

        assert len(tokens) == 1
        token = tokens[0]
        data = token.data

        # All required fields per LitComponent schema
        assert "tag_name" in data
        assert "class_name" in data
        assert "properties" in data
        assert "states" in data
        assert "super_class" in data
        assert "observed_attributes" in data
        assert "decorators" in data

        # Verify types
        assert isinstance(data["tag_name"], str)
        assert isinstance(data["class_name"], str)
        assert isinstance(data["properties"], list)
        assert isinstance(data["states"], list)
        assert isinstance(data["decorators"], list)


class TestEdgeCases:
    """Edge case tests for LitComponentExtractor."""

    def test_empty_source_returns_empty_list(self):
        """Empty source should return empty list."""
        extractor = LitComponentExtractor()
        tokens = extractor.extract(None, "", Path("empty.ts"))
        assert tokens == []

    def test_source_without_lit_returns_empty_list(self):
        """Source without @customElement should return empty list."""
        extractor = LitComponentExtractor()
        tokens = extractor.extract(None, "const x = 1;", Path("no-lit.ts"))
        assert tokens == []

    def test_regex_fallback_enabled_by_default(self):
        """Regex fallback should be enabled by default."""
        extractor = LitComponentExtractor()
        assert extractor.use_regex_fallback is True

    def test_regex_fallback_can_be_disabled(self):
        """Regex fallback can be disabled."""
        extractor = LitComponentExtractor(use_regex_fallback=False)
        assert extractor.use_regex_fallback is False


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
