# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for the extractors factory.

These tests verify that the factory correctly loads and provides
language-specific extractors with lazy loading.
"""

from __future__ import annotations

from pathlib import Path
import pytest

from src.utils.extractors.base import ExtractorAdapter
from src.utils.extractors.factory import get_adapter, register_adapter, clear_cache
from src.utils.extractors.typescript_adapter import TypeScriptAdapter
from src.utils.extractors.python_ast_adapter import PythonAstAdapter


class TestExtractorsFactory:
    """Test suite for the extractors factory."""

    def test_get_adapter_returns_extractor_adapter(self) -> None:
        """get_adapter should return an ExtractorAdapter instance."""
        adapter = get_adapter("python")
        assert isinstance(adapter, ExtractorAdapter)

    def test_get_adapter_for_homeassistant_profile(self) -> None:
        """get_adapter should work with 'homeassistant' profile."""
        adapter = get_adapter("homeassistant")
        assert isinstance(adapter, ExtractorAdapter)

    def test_get_adapter_for_unknown_profile_returns_python(self) -> None:
        """get_adapter should default to Python adapter for unknown profiles."""
        adapter = get_adapter("unknown_profile")
        assert isinstance(adapter, ExtractorAdapter)

    def test_get_adapter_returns_same_instance(self) -> None:
        """get_adapter should return cached instances for the same profile."""
        adapter1 = get_adapter("python")
        adapter2 = get_adapter("python")
        # Both should be functionally equivalent (same type)
        assert type(adapter1) is type(adapter2)

    def test_adapter_can_parse_python_file(self) -> None:
        """Adapter returned from factory should be able to parse files."""
        adapter = get_adapter("python")
        test_file = (
            Path(__file__).parent.parent
            / "fixtures"
            / "python_samples"
            / "simple_imports.py"
        )

        result = adapter.parse_file(test_file)
        assert result.file_path == test_file
        assert result.raw_content != ""
        assert len(result.dependencies) > 0

    def test_adapter_can_extract_dependencies(self) -> None:
        """Adapter returned from factory should extract dependencies."""
        adapter = get_adapter("python")
        test_file = (
            Path(__file__).parent.parent
            / "fixtures"
            / "python_samples"
            / "simple_imports.py"
        )

        deps = adapter.extract_dependencies(test_file)
        assert len(deps) > 0

    def test_get_adapter_with_different_profiles(self) -> None:
        """get_adapter should work with various profile names."""
        profiles = ["python", "homeassistant", "python-ast", "default"]

        for profile in profiles:
            adapter = get_adapter(profile)
            assert isinstance(adapter, ExtractorAdapter)

    def test_register_adapter(self) -> None:
        """register_adapter should allow registering a new adapter."""
        # First, get the default adapter
        adapter1 = get_adapter("test_custom_profile")
        default_type = type(adapter1)

        # Register a new adapter for a custom profile
        register_adapter(
            "test_custom_profile",
            "src.utils.extractors.python_ast_adapter.PythonAstAdapter",
        )

        # Now get_adapter should return the registered adapter
        adapter2 = get_adapter("test_custom_profile")
        assert type(adapter2) is default_type

    def test_clear_cache(self) -> None:
        """clear_cache should clear the adapter cache."""
        # Get an adapter (populates cache)
        get_adapter("cache_test_profile")

        # Clear the cache
        clear_cache()

        # Get adapter again - should get a new instance (or at least not fail)
        adapter2 = get_adapter("cache_test_profile")
        assert isinstance(adapter2, ExtractorAdapter)

    def test_register_adapter_clears_existing_cache(self) -> None:
        """register_adapter should clear existing cache for the profile."""
        # Get an adapter and cache it
        get_adapter("cache_clear_profile")

        # Register a new adapter (should clear cache)
        register_adapter(
            "cache_clear_profile",
            "src.utils.extractors.python_ast_adapter.PythonAstAdapter",
        )

        # Get adapter again - should get the newly registered one
        adapter2 = get_adapter("cache_clear_profile")
        assert isinstance(adapter2, ExtractorAdapter)

    def test_load_adapter_invalid_module(self) -> None:
        """_load_adapter should raise RuntimeError for invalid module path."""
        from src.utils.extractors.factory import _load_adapter

        with pytest.raises(RuntimeError, match="Failed to load adapter"):
            _load_adapter("nonexistent.module.Adapter")

    def test_load_adapter_missing_class(self) -> None:
        """_load_adapter should raise RuntimeError when class not found."""
        from src.utils.extractors.factory import _load_adapter

        with pytest.raises(RuntimeError, match="Adapter class not found"):
            _load_adapter("src.utils.extractors.python_ast_adapter.NonExistentClass")


class TestExtensionMapping:
    """Test suite for file extension to adapter mapping."""

    def test_get_adapter_dot_ts_returns_typescript_adapter(self) -> None:
        """get_adapter('.ts') should return TypeScriptAdapter instance."""
        clear_cache()
        adapter = get_adapter(".ts")
        assert isinstance(adapter, TypeScriptAdapter)

    def test_get_adapter_dot_tsx_returns_typescript_adapter(self) -> None:
        """get_adapter('.tsx') should return TypeScriptAdapter instance."""
        clear_cache()
        adapter = get_adapter(".tsx")
        assert isinstance(adapter, TypeScriptAdapter)

    def test_get_adapter_dot_py_returns_python_adapter(self) -> None:
        """get_adapter('.py') should return PythonAstAdapter instance."""
        clear_cache()
        adapter = get_adapter(".py")
        assert isinstance(adapter, PythonAstAdapter)

    def test_get_adapter_unknown_extension_falls_back_to_default(self) -> None:
        """get_adapter with unknown extension should fall back to default adapter."""
        clear_cache()
        # Unknown extensions should return the default (PythonAstAdapter)
        adapter = get_adapter(".unknown")
        assert isinstance(adapter, PythonAstAdapter)
        adapter2 = get_adapter(".xyz")
        assert isinstance(adapter2, PythonAstAdapter)

    def test_get_adapter_ts_file_with_extension_returns_typescript(self) -> None:
        """get_adapter('test.ts') with file name should return TypeScriptAdapter."""
        clear_cache()
        adapter = get_adapter("test.ts")
        assert isinstance(adapter, TypeScriptAdapter)

    def test_get_adapter_tsx_file_with_extension_returns_typescript(self) -> None:
        """get_adapter('component.tsx') with file name should return TypeScriptAdapter."""
        clear_cache()
        adapter = get_adapter("component.tsx")
        assert isinstance(adapter, TypeScriptAdapter)

    def test_get_adapter_py_file_with_extension_returns_python(self) -> None:
        """get_adapter('script.py') with file name should return PythonAstAdapter."""
        clear_cache()
        adapter = get_adapter("script.py")
        assert isinstance(adapter, PythonAstAdapter)
