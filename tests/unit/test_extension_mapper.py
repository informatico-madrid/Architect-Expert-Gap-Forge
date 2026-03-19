# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for the Extension Mapper dispatch in fragment_extractor.py.

These tests verify that:
- .py files route to _ast_fragment_list
- .php files route to _php_fragment_list
- Unknown extensions return empty list (when allowed_extensions is set)
"""

from __future__ import annotations

from src.factory.fragment_extractor import (
    _EXTENSION_FRAGMENTERS,
    get_v2_fragments,
    _ast_fragment_list,
    _php_fragment_list,
)


class TestExtensionMapper:
    """Test suite for Extension Mapper dispatch functionality."""

    def test_extension_mapper_contains_py_and_php(self) -> None:
        """Extension Mapper should contain .py and .php mappings."""
        assert ".py" in _EXTENSION_FRAGMENTERS
        assert ".php" in _EXTENSION_FRAGMENTERS

    def test_py_routes_to_ast_fragment_list(self) -> None:
        """.py extension should route to _ast_fragment_list."""
        assert _EXTENSION_FRAGMENTERS[".py"] is _ast_fragment_list

    def test_php_routes_to_php_fragment_list(self) -> None:
        """.php extension should route to _php_fragment_list."""
        assert _EXTENSION_FRAGMENTERS[".php"] is _php_fragment_list


class TestExtensionMapperDispatch:
    """Test suite for get_v2_fragments extension dispatch."""

    def test_py_extension_routes_to_ast_fragment_list(self) -> None:
        """get_v2_fragments should use _ast_fragment_list for .py files."""
        bundle = {
            "type": "LOGIC_ONLY",
            "entity_id": "test_module",
            "context": "# Test context",
            "arch": {
                "MODULE": "test_module",
                "REPO_PREFIX": "repo",
                "LANGUAGE": "python",
                "LOCAL_IMPORTS": "[]",
            },
            "files": {
                "test_module.py": "def test_func():\n    pass\n\nclass TestClass:\n    pass"
            },
        }

        fragments = get_v2_fragments(bundle, {})

        assert len(fragments) > 0
        # Verify it's using python type (from AST fragmenter)
        assert fragments[0].get("type") == "python"

    def test_php_extension_routes_to_php_fragmenter(self) -> None:
        """get_v2_fragments should use _php_fragment_list for .php files."""
        bundle = {
            "type": "LOGIC_ONLY",
            "entity_id": "test_module",
            "context": "# Test context",
            "arch": {
                "MODULE": "test_module",
                "REPO_PREFIX": "repo",
                "LANGUAGE": "php",
                "LOCAL_IMPORTS": "[]",
            },
            "files": {
                "test_module.php": "<?php\nfunction test_func() {\n    return 'test';\n}\n?>"
            },
        }

        fragments = get_v2_fragments(bundle, {})

        assert len(fragments) > 0
        # Verify it's using php type (from PHP fragmenter)
        assert fragments[0].get("type") == "php"

    def test_unknown_extension_with_allowed_extensions_returns_empty(
        self,
    ) -> None:
        """Unknown extension should return empty list when allowed_extensions is set."""
        bundle = {
            "type": "LOGIC_ONLY",
            "entity_id": "test_module",
            "context": "# Test context",
            "arch": {
                "MODULE": "test_module",
                "REPO_PREFIX": "repo",
                "LANGUAGE": "unknown",
                "LOCAL_IMPORTS": "[]",
            },
            "files": {"test_module.unknown": "some content"},
        }

        # With allowed_extensions set, unknown extensions should return empty
        fragments = get_v2_fragments(
            bundle,
            {},
            allowed_extensions={".py", ".php"},
        )

        assert fragments == []

    def test_unknown_extension_without_allowed_extensions_fallback_to_ast(
        self,
    ) -> None:
        """Unknown extension should fallback to AST when allowed_extensions is not set."""
        bundle = {
            "type": "LOGIC_ONLY",
            "entity_id": "test_module",
            "context": "# Test context",
            "arch": {
                "MODULE": "test_module",
                "REPO_PREFIX": "repo",
                "LANGUAGE": "text",
                "LOCAL_IMPORTS": "[]",
            },
            "files": {"test_module.txt": "some content"},
        }

        # Without allowed_extensions, unknown extensions fallback to AST
        fragments = get_v2_fragments(bundle, {})

        # Should return fragments from AST fallback
        assert isinstance(fragments, list)

    def test_case_insensitive_extension_matching(self) -> None:
        """Extension matching should be case-insensitive."""
        # The implementation uses .suffix.lower() so .PY should work
        bundle_py_upper = {
            "type": "LOGIC_ONLY",
            "entity_id": "test_module",
            "context": "# Test",
            "arch": {
                "MODULE": "test_module",
                "REPO_PREFIX": "repo",
                "LANGUAGE": "python",
                "LOCAL_IMPORTS": "[]",
            },
            "files": {"test_module.PY": "def test():\n    pass"},
        }

        fragments = get_v2_fragments(bundle_py_upper, {})
        # Should work with uppercase extension
        assert len(fragments) > 0

    def test_php_with_php_fragment_list_returns_correct_structure(
        self,
    ) -> None:
        """_php_fragment_list should return proper FragmentTypedDict structure."""
        bundle = {
            "type": "LOGIC_ONLY",
            "entity_id": "test_module",
            "context": "# Context",
            "arch": {
                "MODULE": "test",
                "REPO_PREFIX": "repo",
                "LANGUAGE": "php",
                "LOCAL_IMPORTS": "[]",
            },
            "files": {"test.php": "<?php echo 'test'; ?>"},
        }

        fragments = get_v2_fragments(bundle, {})

        assert len(fragments) == 1
        fragment = fragments[0]
        # Verify required FragmentTypedDict keys
        assert "name" in fragment
        assert "skeleton" in fragment
        assert "original" in fragment
        assert "context" in fragment
        assert fragment["name"] == "test"

    def test_py_with_ast_fragment_list_returns_correct_structure(
        self,
    ) -> None:
        """_ast_fragment_list should return proper FragmentTypedDict structure."""
        bundle = {
            "type": "LOGIC_ONLY",
            "entity_id": "test_module",
            "context": "# Context",
            "arch": {
                "MODULE": "test",
                "REPO_PREFIX": "repo",
                "LANGUAGE": "python",
                "LOCAL_IMPORTS": "[]",
            },
            "files": {"test.py": "def test():\n    pass\n\nclass Test:\n    pass"},
        }

        fragments = get_v2_fragments(bundle, {})

        assert len(fragments) > 0
        fragment = fragments[0]
        # Verify required FragmentTypedDict keys
        assert "name" in fragment
        assert "skeleton" in fragment
        assert "original" in fragment
        assert "context" in fragment

    def test_extension_mapper_preserves_extra_fields(self) -> None:
        """Extension Mapper should preserve extra_fields from the bundle."""
        bundle = {
            "type": "LOGIC_ONLY",
            "entity_id": "test_module",
            "context": "# Context",
            "arch": {
                "MODULE": "test",
                "REPO_PREFIX": "repo",
                "LANGUAGE": "php",
                "PLATFORM": "wordpress",
                "LOCAL_IMPORTS": "[]",
            },
            "files": {"test.php": "<?php function test() {} ?>"},
            "extra_legacy_signatures": "PERSISTENCE_SMELL: mysql_query",
        }

        fragments = get_v2_fragments(bundle, {})

        assert len(fragments) > 0
        # Extra fields from bundle should be preserved in legacy_signatures
        assert "legacy_signatures" in fragments[0]


class TestExtensionMapperFunctionalUnit:
    """Test Extension Mapper dispatch for FUNCTIONAL_UNIT bundles."""

    def test_functional_unit_with_py_files(self) -> None:
        """FUNCTIONAL_UNIT with .py files should use AST fragmenter."""
        bundle = {
            "type": "FUNCTIONAL_UNIT",
            "entity_id": "test_unit",
            "context": "# Test context",
            "arch": {
                "MODULE": "test_unit",
                "REPO_PREFIX": "repo",
                "LANGUAGE": "python",
                "LOCAL_IMPORTS": "[]",
            },
            "files": {
                "module.py": "def func():\n    pass",
                "test_module.py": "def test_func():\n    pass",
            },
        }

        fragments = get_v2_fragments(bundle, {})

        assert len(fragments) > 0
        # FUNCTIONAL_UNIT should have python type
        assert fragments[0].get("type") == "python"
        assert fragments[0].get("subtype") == "functional_unit"


class TestExtensionMapperModuleBlueprint:
    """Test Extension Mapper dispatch for MODULE_BLUEPRINT bundles."""

    def test_module_blueprint_returns_empty(self) -> None:
        """MODULE_BLUEPRINT bundles should return empty (cached, no samples)."""
        bundle = {
            "type": "MODULE_BLUEPRINT",
            "entity_id": "test_module",
            "context": "# Context",
            "arch": {
                "MODULE": "test",
                "REPO_PREFIX": "repo",
                "LANGUAGE": "php",
                "LOCAL_IMPORTS": "[]",
            },
            "files": {"test.php": "<?php class Test {} ?>"},
        }

        fragments = get_v2_fragments(bundle, {})

        # MODULE_BLUEPRINT returns empty as per function docs
        assert fragments == []
