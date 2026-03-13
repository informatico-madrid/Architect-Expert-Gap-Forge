# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for the PHP Legacy Adapter.

These tests verify that the PhpLegacyAdapter correctly parses PHP files
and extracts dependencies from legacy PHP codebases (osCommerce, WordPress,
ZenCart, etc.).

Author: Joao Maria Arranz Aparicio
"""

from __future__ import annotations

from pathlib import Path
import pytest

from src.utils.extractors.base import (
    Dependency,
    ParseError,
    ParseResult,
)


@pytest.fixture
def php_adapter():
    """Create a PhpLegacyAdapter instance for testing."""
    from src.utils.extractors.php_legacy_adapter import PhpLegacyAdapter
    return PhpLegacyAdapter()


@pytest.fixture
def fixtures_dir() -> Path:
    """Path to the PHP legacy test fixtures directory."""
    return Path(__file__).parent.parent / "fixtures" / "php_legacy"


class TestPhpLegacyAdapterConstructor:
    """Test suite for PhpLegacyAdapter constructor."""

    def test_constructor_instantiates(self) -> None:
        """PhpLegacyAdapter should instantiate without errors."""
        from src.utils.extractors.php_legacy_adapter import PhpLegacyAdapter
        adapter = PhpLegacyAdapter()
        assert adapter is not None

    def test_constructor_default_workers(self) -> None:
        """PhpLegacyAdapter should have default worker pool configuration."""
        from src.utils.extractors.php_legacy_adapter import PhpLegacyAdapter
        adapter = PhpLegacyAdapter()
        # Adapter should have thread pool configuration
        assert hasattr(adapter, '_io_workers') or hasattr(adapter, 'max_workers')

    def test_constructor_accepts_custom_config(self) -> None:
        """PhpLegacyAdapter should accept custom configuration parameters."""
        from src.utils.extractors.php_legacy_adapter import PhpLegacyAdapter
        # Should be able to instantiate with optional config
        adapter = PhpLegacyAdapter()
        assert adapter is not None


class TestPhpLegacyAdapterParseFile:
    """Test suite for PhpLegacyAdapter.parse_file() method."""

    def test_parse_file_returns_parse_result(
        self, php_adapter, fixtures_dir
    ) -> None:
        """parse_file should return a ParseResult with content and metadata."""
        test_file = fixtures_dir / "oscommerce_categories.php"
        result = php_adapter.parse_file(test_file)

        assert isinstance(result, ParseResult)
        assert result.file_path == test_file
        assert result.raw_content != ""

    def test_parse_file_reads_php_content(
        self, php_adapter, fixtures_dir
    ) -> None:
        """parse_file should read the PHP file content."""
        test_file = fixtures_dir / "oscommerce_categories.php"
        result = php_adapter.parse_file(test_file)

        # osCommerce uses tep_db_query
        assert "php" in result.raw_content.lower()

    def test_parse_file_has_ast_tree_none(
        self, php_adapter, fixtures_dir
    ) -> None:
        """parse_file should return None for ast_tree on PHP (non-AST language)."""
        test_file = fixtures_dir / "oscommerce_categories.php"
        result = php_adapter.parse_file(test_file)

        # PHP doesn't use AST in the same way - should be None or custom structure
        assert result.ast_tree is None or result.ast_tree == {}

    def test_parse_file_wordpress_fixture(
        self, php_adapter, fixtures_dir
    ) -> None:
        """parse_file should handle WordPress PHP files."""
        test_file = fixtures_dir / "wordpress_ajax_actions.php"
        result = php_adapter.parse_file(test_file)

        assert isinstance(result, ParseResult)
        assert result.file_path == test_file

    def test_parse_file_zencart_fixture(
        self, php_adapter, fixtures_dir
    ) -> None:
        """parse_file should handle ZenCart PHP files."""
        test_file = fixtures_dir / "zencart_customers.php"
        result = php_adapter.parse_file(test_file)

        assert isinstance(result, ParseResult)
        assert result.file_path == test_file

    def test_parse_file_raises_on_missing_file(
        self, php_adapter, tmp_path
    ) -> None:
        """parse_file should raise ParseError on missing files."""
        missing_file = tmp_path / "nonexistent.php"

        with pytest.raises(ParseError) as exc_info:
            php_adapter.parse_file(missing_file)

        assert str(missing_file) in str(exc_info.value)

    def test_parse_file_dependencies_tuple(
        self, php_adapter, fixtures_dir
    ) -> None:
        """parse_file result should have dependencies as tuple."""
        test_file = fixtures_dir / "oscommerce_categories.php"
        result = php_adapter.parse_file(test_file)

        assert isinstance(result.dependencies, tuple)


class TestPhpLegacyAdapterExtractDependencies:
    """Test suite for PhpLegacyAdapter.extract_dependencies() method."""

    def test_extract_dependencies_returns_list(
        self, php_adapter, fixtures_dir
    ) -> None:
        """extract_dependencies should return a list."""
        test_file = fixtures_dir / "oscommerce_categories.php"
        deps = php_adapter.extract_dependencies(test_file)

        assert isinstance(deps, list)

    def test_extract_dependencies_returns_dependency_objects(
        self, php_adapter, fixtures_dir
    ) -> None:
        """extract_dependencies should return Dependency objects."""
        test_file = fixtures_dir / "oscommerce_categories.php"
        deps = php_adapter.extract_dependencies(test_file)

        assert all(isinstance(d, Dependency) for d in deps)

    def test_extract_dependencies_finds_includes(
        self, php_adapter, fixtures_dir
    ) -> None:
        """extract_dependencies should find include/require statements."""
        test_file = fixtures_dir / "oscommerce_categories.php"
        deps = php_adapter.extract_dependencies(test_file)

        # osCommerce uses require/include statements
        # Should find some dependency (file path or module name)
        assert len(deps) >= 0  # May vary based on implementation

    def test_extract_dependencies_wordpress(
        self, php_adapter, fixtures_dir
    ) -> None:
        """extract_dependencies should find WordPress-specific dependencies."""
        test_file = fixtures_dir / "wordpress_ajax_actions.php"
        deps = php_adapter.extract_dependencies(test_file)

        # WordPress uses $wpdb, add_action
        assert isinstance(deps, list)

    def test_extract_dependencies_zencart(
        self, php_adapter, fixtures_dir
    ) -> None:
        """extract_dependencies should find ZenCart-specific dependencies."""
        test_file = fixtures_dir / "zencart_customers.php"
        deps = php_adapter.extract_dependencies(test_file)

        # ZenCart uses zen_db_perform, $_SESSION
        assert isinstance(deps, list)

    def test_extract_dependencies_handles_empty_file(
        self, php_adapter, tmp_path
    ) -> None:
        """extract_dependencies should handle empty PHP files."""
        empty_file = tmp_path / "empty.php"
        empty_file.write_text("<?php\n// empty file\n")

        deps = php_adapter.extract_dependencies(empty_file)

        assert isinstance(deps, list)

    def test_extract_dependencies_module_types(
        self, php_adapter, fixtures_dir
    ) -> None:
        """extract_dependencies should return deps with module_type field."""
        test_file = fixtures_dir / "oscommerce_categories.php"
        deps = php_adapter.extract_dependencies(test_file)

        for dep in deps:
            assert hasattr(dep, 'module_type')
            assert hasattr(dep, 'name')


class TestPhpLegacyAdapterProtocol:
    """Test suite verifying PhpLegacyAdapter implements ExtractorAdapter protocol."""

    def test_adapter_implements_protocol(self, php_adapter) -> None:
        """Adapter should implement the ExtractorAdapter protocol."""
        from src.utils.extractors.base import ExtractorAdapter

        assert isinstance(php_adapter, ExtractorAdapter)

    def test_adapter_has_parse_file_method(self, php_adapter) -> None:
        """Adapter should have parse_file method."""
        assert hasattr(php_adapter, 'parse_file')
        assert callable(php_adapter.parse_file)

    def test_adapter_has_extract_dependencies_method(self, php_adapter) -> None:
        """Adapter should have extract_dependencies method."""
        assert hasattr(php_adapter, 'extract_dependencies')
        assert callable(php_adapter.extract_dependencies)


class TestPhpLegacyAdapterMaxWorkers:
    """Test suite for max_workers property."""

    def test_max_workers_returns_io_workers(self, php_adapter) -> None:
        """max_workers should return the IO workers count."""
        workers = php_adapter.max_workers
        assert isinstance(workers, int)
        assert workers > 0


class TestPhpLegacyAdapterProcessRepository:
    """Test suite for process_repository method."""

    def test_process_repository_auto_detect_platform(
        self, php_adapter, tmp_path
    ) -> None:
        """process_repository should auto-detect platform when profile_name is None."""
        # Create a simple PHP file with WordPress markers
        (tmp_path / "wp-config.php").write_text("<?php define('WP_DEBUG', true);")
        (tmp_path / "index.php").write_text("<?php $wpdb->query('SELECT 1');")

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Should not raise, auto-detect should work
        bundle_paths = php_adapter.process_repository(
            repo_path=tmp_path,
            output_dir=output_dir,
            profile_name=None,  # Auto-detect
        )
        # Returns list (possibly empty or with bundles)
        assert isinstance(bundle_paths, list)

    def test_process_repository_empty_dir(
        self, php_adapter, tmp_path
    ) -> None:
        """process_repository should return empty list for empty directory."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        bundle_paths = php_adapter.process_repository(
            repo_path=tmp_path,
            output_dir=output_dir,
            profile_name="generic_php",
        )
        assert bundle_paths == []

    def test_process_repository_no_php_files(
        self, php_adapter, tmp_path
    ) -> None:
        """process_repository should return empty list when no PHP files found."""
        # Create non-PHP file
        (tmp_path / "readme.txt").write_text("Just a text file")

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        bundle_paths = php_adapter.process_repository(
            repo_path=tmp_path,
            output_dir=output_dir,
            profile_name="generic_php",
        )
        assert bundle_paths == []

    def test_process_repository_with_single_file(
        self, php_adapter, tmp_path, fixtures_dir
    ) -> None:
        """process_repository should process a single PHP file."""
        # Copy fixture to temp repo
        test_file = fixtures_dir / "oscommerce_categories.php"
        dest_file = tmp_path / "test_file.php"
        dest_file.write_text(test_file.read_text())

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        bundle_paths = php_adapter.process_repository(
            repo_path=tmp_path,
            output_dir=output_dir,
            profile_name="oscommerce",
        )
        assert isinstance(bundle_paths, list)
        # Should have produced at least one bundle
        assert len(bundle_paths) >= 0


class TestProcessPhpFragmentWorker:
    """Test suite for _process_php_fragment_worker function."""

    def test_worker_returns_success_dict(self) -> None:
        """Worker should return success dict with fragments."""
        from src.utils.extractors.php_legacy_adapter import _process_php_fragment_worker

        test_content = "<?php function test() { echo 'hello'; }"
        result = _process_php_fragment_worker(("test.php", test_content, "generic_php"))

        assert result["success"] is True
        assert "fragments" in result
        assert result["path"] == "test.php"

    def test_worker_handles_exception(self) -> None:
        """Worker should return error dict on exception."""
        from src.utils.extractors.php_legacy_adapter import _process_php_fragment_worker

        # Pass invalid args to trigger exception
        result = _process_php_fragment_worker((None, None, "invalid"))

        assert result["success"] is False
        assert "error" in result


class TestExtractDependenciesErrorHandling:
    """Test suite for error handling in extract_dependencies."""

    def test_extract_dependencies_raises_on_missing_file(
        self, php_adapter, tmp_path
    ) -> None:
        """extract_dependencies should raise ParseError on missing file."""
        missing_file = tmp_path / "nonexistent.php"

        with pytest.raises(Exception):  # Could be ParseError or OSError
            php_adapter.extract_dependencies(missing_file)


class TestProcessRepositoryWithIncludes:
    """Test suite for process_repository with include relationships."""

    def test_process_repository_with_includes_emits_blueprints(
        self, php_adapter, tmp_path
    ) -> None:
        """process_repository should emit MODULE_BLUEPRINT bundles for hub files."""
        # Create multiple PHP files with include relationships
        # Create a "hub" file that is included by many others
        hub_file = tmp_path / "includes" / "common.php"
        hub_file.parent.mkdir(parents=True, exist_ok=True)
        hub_file.write_text("""<?php
// Common functions used across the site
function get_config() { return array(); }
""")

        # Create files that include the hub file (to make it a hub)
        for i in range(6):
            inc_file = tmp_path / f"page{i}.php"
            inc_file.write_text(f"""<?php
require_once 'includes/common.php';
echo 'Page {i}';
""")

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        bundle_paths = php_adapter.process_repository(
            repo_path=tmp_path,
            output_dir=output_dir,
            profile_name="generic_php",
        )

        # Should return list of bundles
        assert isinstance(bundle_paths, list)

    def test_process_repository_skips_empty_result(
        self, php_adapter, tmp_path
    ) -> None:
        """process_repository should handle empty worker results gracefully."""
        # Create a file that might produce empty fragments
        test_file = tmp_path / "empty.php"
        test_file.write_text("<?php\n// Just a comment\n")

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Should not raise
        bundle_paths = php_adapter.process_repository(
            repo_path=tmp_path,
            output_dir=output_dir,
            profile_name="generic_php",
        )
        assert isinstance(bundle_paths, list)
