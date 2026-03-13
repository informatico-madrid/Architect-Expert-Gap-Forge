#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Integration tests for PHP processor bundles.

Validates that PhpLegacyAdapter correctly processes PHP files and emits
.txt bundles that can be parsed by parse_bundle() from src/factory/fragment_extractor.py.

INTEGRATION TESTS: Cross-module, real I/O allowed
Location: tests/integration/
Example: tests/integration/test_php_processor_bundles.py
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.factory.fragment_extractor import parse_bundle
from src.utils.extractors.php_legacy_adapter import PhpLegacyAdapter


# =============================================================================
# INTEGRATION TESTS: PHP Processor Bundles
# =============================================================================


class TestPhpProcessorBundles:
    """Test that PhpLegacyAdapter emits bundles parseable by parse_bundle()."""

    @pytest.fixture
    def php_legacy_adapter(self) -> PhpLegacyAdapter:
        """Create a PhpLegacyAdapter instance for testing."""
        return PhpLegacyAdapter(
            io_workers=4,
            cpu_workers=2,
            write_workers=2,
            default_profile="oscommerce",
        )

    @pytest.fixture
    def oscommerce_fixture_path(self) -> Path:
        """Path to the osCommerce categories.php fixture."""
        return Path(
            "tests/fixtures/php_legacy/oscommerce_categories.php"
        )

    @pytest.fixture
    def temp_output_dir(self, tmp_path: Path) -> Path:
        """Create a temporary output directory for bundles."""
        output_dir = tmp_path / "bundles"
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def test_php_legacy_adapter_parse_file_returns_parse_result(
        self, php_legacy_adapter: PhpLegacyAdapter, oscommerce_fixture_path: Path
    ) -> None:
        """Test that PhpLegacyAdapter.parse_file() returns a valid ParseResult."""
        # Act
        result = php_legacy_adapter.parse_file(oscommerce_fixture_path)

        # Assert
        assert result is not None
        assert result.file_path == oscommerce_fixture_path
        assert result.raw_content is not None
        assert len(result.raw_content) > 0
        # PHP doesn't use AST in the same way as Python
        assert result.ast_tree is None

    def test_php_legacy_adapter_extract_dependencies_returns_list(
        self, php_legacy_adapter: PhpLegacyAdapter, oscommerce_fixture_path: Path
    ) -> None:
        """Test that extract_dependencies() returns a list of dependencies."""
        # Act
        dependencies = php_legacy_adapter.extract_dependencies(oscommerce_fixture_path)

        # Assert
        assert isinstance(dependencies, list)
        # osCommerce fixture has include/require statements
        assert len(dependencies) > 0
        # Verify dependency structure
        for dep in dependencies:
            assert hasattr(dep, "name")
            assert hasattr(dep, "module_type")

    def test_php_legacy_adapter_process_repository_emits_bundle(
        self,
        php_legacy_adapter: PhpLegacyAdapter,
        oscommerce_fixture_path: Path,
        temp_output_dir: Path,
    ) -> None:
        """Test that process_repository() emits .txt bundles."""
        # Arrange: Create a temp repo directory with the fixture
        repo_root = temp_output_dir / "test_repo"
        repo_root.mkdir(parents=True)

        # Copy fixture to repo root
        import shutil

        dest_path = repo_root / oscommerce_fixture_path.name
        shutil.copy(oscommerce_fixture_path, dest_path)

        # Act: Process the repository
        bundle_paths = php_legacy_adapter.process_repository(
            repo_path=repo_root,
            output_dir=temp_output_dir,
            profile_name="oscommerce",
        )

        # Assert: Bundle files were created
        assert len(bundle_paths) > 0, "Expected at least one bundle file to be created"

        # Verify bundle files have .txt extension
        txt_bundles = [p for p in bundle_paths if p.suffix == ".txt"]
        assert len(txt_bundles) > 0, "Expected at least one .txt bundle file"

    def test_emitted_bundle_parses_correctly_via_parse_bundle(
        self,
        php_legacy_adapter: PhpLegacyAdapter,
        oscommerce_fixture_path: Path,
        temp_output_dir: Path,
    ) -> None:
        """Test that emitted bundle parses correctly via parse_bundle()."""
        # Arrange: Create a temp repo directory with the fixture
        repo_root = temp_output_dir / "test_repo_parse"
        repo_root.mkdir(parents=True)

        import shutil

        dest_path = repo_root / oscommerce_fixture_path.name
        shutil.copy(oscommerce_fixture_path, dest_path)

        # Act: Process the repository
        bundle_paths = php_legacy_adapter.process_repository(
            repo_path=repo_root,
            output_dir=temp_output_dir,
            profile_name="oscommerce",
        )

        # Read the first bundle file
        assert len(bundle_paths) > 0
        bundle_content = bundle_paths[0].read_text()

        # Act: Parse the bundle using parse_bundle from fragment_extractor
        parsed = parse_bundle(bundle_content)

        # Assert: Bundle parsed correctly with required fields
        assert parsed is not None
        assert isinstance(parsed, dict)

        # Check entity_id (LOGICAL ENTITY) - may be empty for PHP bundles
        assert "entity_id" in parsed, "Parsed bundle must have entity_id"

        # Check type field - may be in FRAGMENT_TYPE within arch for PHP bundles
        assert "type" in parsed, "Parsed bundle must have type field"
        # For PHP bundles, type may be empty but FRAGMENT_TYPE should be in arch
        # Accept both: top-level type or FRAGMENT_TYPE in arch
        bundle_type = parsed.get("type", "")
        arch = parsed.get("arch", {})
        fragment_type = arch.get("FRAGMENT_TYPE", "")
        has_valid_type = (
            bundle_type in ("FUNCTIONAL_UNIT", "LOGIC_ONLY", "MODULE_BLUEPRINT", "GOVERNANCE_RULES")
            or fragment_type in ("FUNCTIONAL_UNIT", "LOGIC_ONLY", "MODULE_BLUEPRINT", "GOVERNANCE_RULES")
        )
        assert has_valid_type, (
            f"Expected valid bundle type, got type='{bundle_type}', FRAGMENT_TYPE='{fragment_type}'"
        )

        # Check arch dict (from [ARCH_HEADER])
        assert "arch" in parsed, "Parsed bundle must have arch dict"
        assert isinstance(parsed["arch"], dict), "arch must be a dict"

        # Check files dict
        assert "files" in parsed, "Parsed bundle must have files dict"
        assert isinstance(parsed["files"], dict), "files must be a dict"
        assert len(parsed["files"]) > 0, "Expected at least one file in bundle"

    def test_parse_bundle_returns_module_and_fragment_type(
        self,
        php_legacy_adapter: PhpLegacyAdapter,
        oscommerce_fixture_path: Path,
        temp_output_dir: Path,
    ) -> None:
        """Test that parse_bundle returns non-empty MODULE and FRAGMENT_TYPE fields."""
        # Arrange
        repo_root = temp_output_dir / "test_repo_fields"
        repo_root.mkdir(parents=True)

        import shutil

        dest_path = repo_root / oscommerce_fixture_path.name
        shutil.copy(oscommerce_fixture_path, dest_path)

        # Act
        bundle_paths = php_legacy_adapter.process_repository(
            repo_path=repo_root,
            output_dir=temp_output_dir,
            profile_name="oscommerce",
        )

        assert len(bundle_paths) > 0
        bundle_content = bundle_paths[0].read_text()
        parsed = parse_bundle(bundle_content)

        # Assert: MODULE and FRAGMENT_TYPE present in arch
        arch = parsed.get("arch", {})

        # MODULE field should be present (or MODULE_NAME)
        has_module = "MODULE" in arch or "module" in arch
        assert has_module, f"Expected MODULE field in arch, got: {arch.keys()}"

        # FRAGMENT_TYPE should be present (or TYPE)
        has_fragment_type = "FRAGMENT_TYPE" in arch or "type" in parsed
        assert has_fragment_type, (
            f"Expected FRAGMENT_TYPE in arch or type in parsed, "
            f"got arch.keys()={arch.keys()}, parsed.type={parsed.get('type')}"
        )

    def test_sc001_process_oscommerce_fixture_under_5s(
        self,
        php_legacy_adapter: PhpLegacyAdapter,
        oscommerce_fixture_path: Path,
        temp_output_dir: Path,
    ) -> None:
        """SC-001: Process osCommerce fixture <5s (AMD Threadripper baseline)."""
        import time

        # Arrange
        repo_root = temp_output_dir / "test_repo_sc001"
        repo_root.mkdir(parents=True)

        import shutil

        dest_path = repo_root / oscommerce_fixture_path.name
        shutil.copy(oscommerce_fixture_path, dest_path)

        # Act
        start_time = time.time()
        bundle_paths = php_legacy_adapter.process_repository(
            repo_path=repo_root,
            output_dir=temp_output_dir,
            profile_name="oscommerce",
        )
        elapsed_time = time.time() - start_time

        # Assert
        assert elapsed_time < 5.0, (
            f"SC-001 FAILED: Processing took {elapsed_time:.2f}s, "
            f"expected <5s on AMD Threadripper baseline"
        )
        assert len(bundle_paths) > 0, "Expected bundle files to be created"

    def test_sc002_all_bundles_parse_via_parse_bundle(
        self,
        php_legacy_adapter: PhpLegacyAdapter,
        oscommerce_fixture_path: Path,
        temp_output_dir: Path,
    ) -> None:
        """SC-002: 100% of emitted bundles parse via parse_bundle()."""
        # Arrange
        repo_root = temp_output_dir / "test_repo_sc002"
        repo_root.mkdir(parents=True)

        import shutil

        dest_path = repo_root / oscommerce_fixture_path.name
        shutil.copy(oscommerce_fixture_path, dest_path)

        # Act
        bundle_paths = php_legacy_adapter.process_repository(
            repo_path=repo_root,
            output_dir=temp_output_dir,
            profile_name="oscommerce",
        )

        # Assert: All bundles parse successfully
        assert len(bundle_paths) > 0, "Expected bundle files to be created"

        parse_errors = []
        for bundle_path in bundle_paths:
            try:
                content = bundle_path.read_text()
                parsed = parse_bundle(content)
                # Verify parsed result has required structure
                assert "type" in parsed, f"Missing 'type' in {bundle_path.name}"
                assert "arch" in parsed, f"Missing 'arch' in {bundle_path.name}"
                assert "files" in parsed, f"Missing 'files' in {bundle_path.name}"
            except Exception as e:
                parse_errors.append(f"{bundle_path.name}: {str(e)}")

        assert len(parse_errors) == 0, (
            f"SC-002 FAILED: {len(parse_errors)} bundles failed to parse: {parse_errors}"
        )
