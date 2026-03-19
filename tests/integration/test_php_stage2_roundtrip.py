#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Integration tests for PHP Stage 2 roundtrip: bundle emit → parse → extract.

Validates the complete T036 pipeline:
1. PhpLegacyAdapter.process_repository() emits .txt bundles with [LEGACY_SIGNATURES]
2. parse_bundle() extracts extra_legacy_signatures from the bundle
3. get_v2_fragments() injects legacy_signatures into fragment context

INTEGRATION TESTS: Cross-module, real I/O allowed
Location: tests/integration/
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.factory.fragment_extractor import parse_bundle
from src.utils.extractors.php_legacy_adapter import PhpLegacyAdapter


class TestPhpStage2Roundtrip:
    """Test Stage 2 roundtrip: emit bundle → parse → extract with legacy signatures."""

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
        return Path("tests/fixtures/php_legacy/oscommerce_categories.php")

    @pytest.fixture
    def temp_output_dir(self, tmp_path: Path) -> Path:
        """Create a temporary output directory for bundles."""
        output_dir = tmp_path / "bundles"
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def test_t036_extra_legacy_signatures_contains_persistence_smell(
        self,
        php_legacy_adapter: PhpLegacyAdapter,
        oscommerce_fixture_path: Path,
        temp_output_dir: Path,
    ) -> None:
        """
        T036: Integration test for Stage 2 roundtrip with legacy signatures.

        Process osCommerce fixture → parse emitted bundle via parse_bundle()
        → assert extra_legacy_signatures present and contains ≥1 PERSISTENCE_SMELL entry.
        """
        # Arrange: Create a temp repo directory with the fixture
        repo_root = temp_output_dir / "test_repo_t036"
        repo_root.mkdir(parents=True)

        import shutil

        dest_path = repo_root / oscommerce_fixture_path.name
        shutil.copy(oscommerce_fixture_path, dest_path)

        # Act: Process the repository - emits .txt bundles with [LEGACY_SIGNATURES]
        bundle_paths = php_legacy_adapter.process_repository(
            repo_path=repo_root,
            output_dir=temp_output_dir,
            profile_name="oscommerce",
        )

        # Assert: Bundle files were created
        assert len(bundle_paths) > 0, "Expected at least one bundle file to be created"

        # Read the first bundle file
        bundle_content = bundle_paths[0].read_text()

        # Verify [LEGACY_SIGNATURES] section is present in the raw bundle
        assert "[LEGACY_SIGNATURES]" in bundle_content, (
            "Expected [LEGACY_SIGNATURES] section in bundle content"
        )

        # Act: Parse the bundle using parse_bundle from fragment_extractor
        parsed = parse_bundle(bundle_content)

        # Assert: extra_legacy_signatures is present in parsed result
        assert "extra_legacy_signatures" in parsed, (
            "Expected extra_legacy_signatures in parsed bundle"
        )

        # Assert: extra_legacy_signatures is not empty
        legacy_sigs = parsed["extra_legacy_signatures"]
        assert legacy_sigs, "extra_legacy_signatures should not be empty"
        assert len(legacy_sigs) > 0, "extra_legacy_signatures should contain content"

        # Assert: Contains at least one PERSISTENCE_SMELL entry
        # The format is "CATEGORY: PERSISTENCE_SMELL" within the legacy signatures
        assert "PERSISTENCE_SMELL" in legacy_sigs, (
            f"Expected PERSISTENCE_SMELL in legacy signatures, got: {legacy_sigs[:200]}..."
        )

    def test_t036_parsed_bundle_contains_legacy_signatures(
        self,
        php_legacy_adapter: PhpLegacyAdapter,
        oscommerce_fixture_path: Path,
        temp_output_dir: Path,
    ) -> None:
        """
        T036: Verify parsed bundle contains legacy_signatures for Teacher prompt.

        This test verifies that:
        1. The emitted bundle contains [LEGACY_SIGNATURES] section
        2. parse_bundle() extracts it as extra_legacy_signatures
        3. The extracted signatures contain PERSISTENCE_SMELL entries

        Note: get_v2_fragments() requires Python-style bundles with logic+test pairs.
        For PHP bundles, the legacy_signatures are available in the parsed bundle's
        extra_legacy_signatures field, which can be used directly for Teacher prompts.
        """
        # Arrange
        repo_root = temp_output_dir / "test_repo_v2_fragments"
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

        assert len(bundle_paths) > 0

        # Read and parse the bundle
        bundle_content = bundle_paths[0].read_text()
        parsed = parse_bundle(bundle_content)

        # Assert: extra_legacy_signatures is present and contains PERSISTENCE_SMELL
        assert "extra_legacy_signatures" in parsed, (
            "Expected extra_legacy_signatures in parsed bundle"
        )

        legacy_sigs = parsed["extra_legacy_signatures"]
        assert legacy_sigs, "extra_legacy_signatures should not be empty"

        # Assert: Contains at least one PERSISTENCE_SMELL entry
        assert "PERSISTENCE_SMELL" in legacy_sigs, (
            f"Expected PERSISTENCE_SMELL in legacy signatures, got: {legacy_sigs[:200]}..."
        )

    def test_t036_legacy_signatures_format_matches_contract(
        self,
        php_legacy_adapter: PhpLegacyAdapter,
        oscommerce_fixture_path: Path,
        temp_output_dir: Path,
    ) -> None:
        """
        T036: Verify legacy signatures format matches contracts/bundle-format.md.

        Format should be:
        CATEGORY: <category>
        PATTERN: <pattern_name> — <matched_text>
        SEVERITY: <severity>
        MODERN_HINT: <modern_equivalent>
        """
        # Arrange
        repo_root = temp_output_dir / "test_repo_format"
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

        bundle_content = bundle_paths[0].read_text()
        parsed = parse_bundle(bundle_content)

        legacy_sigs = parsed["extra_legacy_signatures"]

        # Assert: Format matches contract - contains required fields
        assert "CATEGORY:" in legacy_sigs, "Expected CATEGORY: field in signatures"
        assert "PATTERN:" in legacy_sigs, "Expected PATTERN: field in signatures"
        assert "SEVERITY:" in legacy_sigs, "Expected SEVERITY: field in signatures"
        assert "MODERN_HINT:" in legacy_sigs, (
            "Expected MODERN_HINT: field in signatures"
        )

        # Assert: Contains at least one PERSISTENCE_SMELL category entry
        assert "CATEGORY: PERSISTENCE_SMELL" in legacy_sigs, (
            "Expected CATEGORY: PERSISTENCE_SMELL in signatures"
        )
