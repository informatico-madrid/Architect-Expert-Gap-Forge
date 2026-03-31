"""Tests for extractors factory extension mapping."""

import pytest
from src.utils.extractors.factory import get_adapter
from src.utils.extractors.typescript_adapter import TypeScriptAdapter
from src.utils.extractors.python_ast_adapter import PythonAstAdapter


class TestFactoryExtensionMapping:
    """Test factory correctly maps file extensions to adapters."""

    def test_get_adapter_ts_returns_typescript_adapter(self):
        """Test that .ts extension maps to TypeScriptAdapter."""
        result = get_adapter(".ts")
        assert isinstance(result, TypeScriptAdapter)

    def test_get_adapter_tsx_returns_typescript_adapter(self):
        """Test that .tsx extension maps to TypeScriptAdapter."""
        result = get_adapter(".tsx")
        assert isinstance(result, TypeScriptAdapter)

    def test_get_adapter_py_returns_python_adapter(self):
        """Test that .py extension maps to PythonAstAdapter."""
        result = get_adapter(".py")
        assert isinstance(result, PythonAstAdapter)

    def test_get_adapter_unknown_returns_default(self):
        """Test that unknown extensions fall back to default adapter."""
        result = get_adapter(".unknown_ext")
        # Unknown extensions should return the default adapter (PythonAstAdapter)
        assert isinstance(result, PythonAstAdapter)
