# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Tests for YAML/Jinja adapter factory registration.
"""

from __future__ import annotations


from src.utils.extractors.factory import get_adapter
from src.utils.extractors.yaml_adapter import YamlAdapter
from src.utils.extractors.jinja_adapter import JinjaAdapter
from src.utils.extractors.python_ast_adapter import PythonAstAdapter


class TestFactoryYamlJinjaRegistration:
    """Tests for YAML/Jinja adapter factory registration."""

    def test_get_adapter_yaml_returns_yaml_adapter(self):
        """get_adapter(".yaml") returns YamlAdapter."""
        adapter = get_adapter(".yaml")
        assert isinstance(adapter, YamlAdapter)

    def test_get_adapter_yml_returns_yaml_adapter(self):
        """get_adapter(".yml") returns YamlAdapter."""
        adapter = get_adapter(".yml")
        assert isinstance(adapter, YamlAdapter)

    def test_get_adapter_jinja_returns_jinja_adapter(self):
        """get_adapter(".jinja") returns JinjaAdapter."""
        adapter = get_adapter(".jinja")
        assert isinstance(adapter, JinjaAdapter)

    def test_get_adapter_jinja2_returns_jinja_adapter(self):
        """get_adapter(".jinja2") returns JinjaAdapter."""
        adapter = get_adapter(".jinja2")
        assert isinstance(adapter, JinjaAdapter)

    def test_get_adapter_python_returns_python_adapter(self):
        """get_adapter(".py") returns PythonAstAdapter."""
        adapter = get_adapter(".py")
        assert isinstance(adapter, PythonAstAdapter)

    def test_get_adapter_ts_returns_typescript_adapter(self):
        """get_adapter(".ts") returns TypeScriptAdapter."""
        from src.utils.extractors.typescript_adapter import TypeScriptAdapter

        adapter = get_adapter(".ts")
        assert isinstance(adapter, TypeScriptAdapter)

    def test_get_adapter_unknown_returns_default(self):
        """Unknown extensions fall back to default (PythonAstAdapter)."""
        adapter = get_adapter(".unknown")
        # Should fall back to PythonAstAdapter
        assert isinstance(adapter, PythonAstAdapter)

    def test_adapter_caching(self):
        """Adapters are cached and reused."""
        adapter1 = get_adapter(".yaml")
        adapter2 = get_adapter(".yaml")
        assert adapter1 is adapter2

    def test_multiple_extensions_same_adapter(self):
        """.yaml and .yml return the same adapter type."""
        adapter_yaml = get_adapter(".yaml")
        adapter_yml = get_adapter(".yml")
        assert type(adapter_yaml) is type(adapter_yml)
        assert isinstance(adapter_yaml, YamlAdapter)

    def test_yaml_adapter_has_required_methods(self):
        """YamlAdapter has required methods from ExtractorAdapter protocol."""
        adapter = get_adapter(".yaml")
        assert hasattr(adapter, "parse_file")
        assert hasattr(adapter, "extract_dependencies")

    def test_jinja_adapter_has_required_methods(self):
        """JinjaAdapter has required methods from ExtractorAdapter protocol."""
        adapter = get_adapter(".jinja")
        assert hasattr(adapter, "parse_file")
        assert hasattr(adapter, "extract_dependencies")
