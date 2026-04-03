# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Tests for Jinja adapter.
"""

from __future__ import annotations

import pytest
from pathlib import Path

from src.utils.extractors.jinja_adapter import JinjaAdapter


class TestJinjaAdapter:
    """Tests for JinjaAdapter."""

    @pytest.fixture
    def adapter(self):
        """Create a JinjaAdapter instance."""
        return JinjaAdapter()

    @pytest.fixture
    def template_jinja(self, fixtures_dir: Path) -> Path:
        """Get path to Jinja template fixture."""
        return fixtures_dir / "jinja_samples" / "template.jinja"

    def test_parse_file_returns_parse_result(self, adapter, template_jinja):
        """JinjaAdapter.parse_file returns ParseResult."""
        result = adapter.parse_file(template_jinja)

        assert result is not None
        assert result.file_path == template_jinja
        assert result.raw_content is not None
        assert result.dependencies is not None

    def test_extract_variables(self, adapter, template_jinja):
        """JinjaAdapter extracts template variables."""
        result = adapter.parse_file(template_jinja)

        # Check for state variables
        assert "states(" in result.raw_content
        assert "climate" in result.raw_content

    def test_extract_filters(self, adapter, template_jinja):
        """JinjaAdapter extracts filter patterns."""
        result = adapter.parse_file(template_jinja)

        # Check for filter patterns in content
        assert "| float" in result.raw_content
        assert "| round" in result.raw_content

    def test_extract_conditionals(self, adapter, template_jinja):
        """JinjaAdapter extracts conditional patterns."""
        result = adapter.parse_file(template_jinja)

        # Check for if/else patterns
        assert "{% if" in result.raw_content
        assert "{% elif" in result.raw_content
        assert "{% endif" in result.raw_content

    def test_extract_loops(self, adapter, template_jinja):
        """JinjaAdapter extracts loop patterns."""
        result = adapter.parse_file(template_jinja)

        # Check for for loop
        assert "{% for" in result.raw_content
        assert "{% endfor" in result.raw_content

    def test_extract_statements(self, adapter, template_jinja):
        """JinjaAdapter extracts statement patterns."""
        result = adapter.parse_file(template_jinja)

        # Check for set statement
        assert "{% set" in result.raw_content

    def test_detect_homeassistant_expressions(self, adapter, template_jinja):
        """JinjaAdapter detects Home Assistant specific expressions."""
        result = adapter.parse_file(template_jinja)

        # Check for states() calls
        assert "states(" in result.raw_content

    def test_extract_dependencies(self, adapter, template_jinja):
        """JinjaAdapter extracts entity dependencies."""
        dependencies = adapter.extract_dependencies(template_jinja)

        # Should extract entity references
        entity_deps = [d for d in dependencies if d.module_type == "entity"]
        assert len(entity_deps) > 0

        # Check for climate sensor
        entity_names = [d.name for d in dependencies if d.module_type == "entity"]
        assert any("climate" in name for name in entity_names)


class TestJinjaAdapterParsing:
    """Tests for Jinja parsing."""

    @pytest.fixture
    def adapter(self):
        """Create a JinjaAdapter instance."""
        return JinjaAdapter()

    def test_parse_valid_jinja(self, adapter, fixtures_dir: Path):
        """JinjaAdapter parses valid Jinja without errors."""
        template_jinja = fixtures_dir / "jinja_samples" / "template.jinja"
        result = adapter.parse_file(template_jinja)

        assert result is not None
        assert result.raw_content is not None
        assert len(result.raw_content) > 0

    def test_jinja_content_preserved(self, adapter, fixtures_dir: Path):
        """JinjaAdapter preserves template content."""
        template_jinja = fixtures_dir / "jinja_samples" / "template.jinja"
        result = adapter.parse_file(template_jinja)

        # Check that content is preserved
        assert "climate_temp" in result.raw_content
        assert "sensor_temperature" in result.raw_content or "sensor" in result.raw_content
