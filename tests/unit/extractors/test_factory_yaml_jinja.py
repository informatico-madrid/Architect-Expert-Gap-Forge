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
from src.utils.extractors.python_ast_adapter import PythonAstAdapter


class TestFactoryYamlJinjaRegistration:
    """Tests for YAML/Jinja adapter factory registration."""

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

    def test_yaml_adapter_has_required_methods(self):
        """Default adapter has required methods from ExtractorAdapter protocol."""
        adapter = get_adapter(".yaml")
        assert hasattr(adapter, "parse_file")
        assert hasattr(adapter, "extract_dependencies")

    def test_jinja_adapter_has_required_methods(self):
        """JinjaAdapter has required methods from ExtractorAdapter protocol."""
        adapter = get_adapter(".jinja")
        assert hasattr(adapter, "parse_file")
        assert hasattr(adapter, "extract_dependencies")
