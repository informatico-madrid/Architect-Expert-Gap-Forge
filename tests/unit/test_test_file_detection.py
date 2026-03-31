# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Unit Tests for Test File Detection
====================================

Tests test file mirror detection patterns:
- Exact name mirror: test_<logic_filename>.py
- tests/ directory: tests/<path>/test_<module>.py

Requirements: AC-1.2, FR-8
"""

from __future__ import annotations

from pathlib import Path

from src.discovery import ProcessingConfig, RepoProcessor


class TestTestFileDetection:
    """Unit tests for test file detection patterns."""

    def test_exact_mirror_detection(self, tmp_path: Path) -> None:
        """Test that test_<logic_filename>.py is detected as test for logic.py.

        AC-1.2: Test file must match exact mirror pattern.
        """
        repo_root = tmp_path / "test_repo"
        repo_root.mkdir()

        myrepo = repo_root / "myrepo"
        myrepo.mkdir()

        component = myrepo / "custom_components" / "test_component"
        component.mkdir(parents=True)

        # Create manifest.json
        import json
        (component / "manifest.json").write_text(json.dumps({
            "domain": "test_component",
            "name": "Test",
            "version": "1.0.0",
        }))

        # Create logic file
        (component / "utils.py").write_text("""
def calculate_total(items):
    total = 0
    for item in items:
        total += item.get('price', 0)
    return total
""".strip())

        # Create test file with exact mirror name - must be >= 300 bytes
        # Structure: component/tests/test_utils.py (tests at component level)
        (component / "tests").mkdir(parents=True, exist_ok=True)
        (component / "tests" / "test_utils.py").write_text("""import utils

def test_calculate_total():
    '''Test calculate_total with various scenarios.'''
    # Test with simple price list
    items = [{'price': 10}, {'price': 20}]
    result = utils.calculate_total(items)
    assert result == 30, f'Expected 30 but got {result}'

    # Test with empty list
    empty_result = utils.calculate_total([])
    assert empty_result == 0, f'Expected 0 for empty list'

    # Test with mixed price and cost keys
    mixed_items = [
        {'price': 100, 'cost': 50},
        {'cost': 200, 'price': 150}
    ]
    total = utils.calculate_total(mixed_items)
    assert total == 500, f'Expected 500 but got {total}'

    print('All tests passed')
""".strip())

        config = ProcessingConfig(
            base_dir=tmp_path,
            raw_subdir="test_repo",
            output_subdir="output",
            category="myrepo",
            module_discovery_strategy="manifest",
            extensions={".py"},
        )
        processor = RepoProcessor(config)
        processor.run()

        # Verify bundle was created
        output_dir = tmp_path / "output" / "myrepo"
        bundle_files = list(output_dir.rglob("*.txt"))

        # Should have FUNCTIONAL_UNIT bundle (TYPE 1)
        functional_unit_files = [
            f for f in bundle_files
            if 'FUNCTIONAL_UNIT' in f.read_text()
        ]

        assert len(functional_unit_files) > 0, (
            "Test file with exact mirror name should trigger TYPE 1 bundle"
        )

    def test_tests_directory_detection(self, tmp_path: Path) -> None:
        """Test that test files in tests/ directory are detected.

        AC-1.2: Test files in tests/ directory should be paired with logic files.
        """
        repo_root = tmp_path / "test_repo"
        repo_root.mkdir()

        myrepo = repo_root / "myrepo"
        myrepo.mkdir()

        component = myrepo / "custom_components" / "my_component"
        component.mkdir(parents=True)

        # Create manifest.json
        import json
        (component / "manifest.json").write_text(json.dumps({
            "domain": "my_component",
            "name": "My Component",
            "version": "1.0.0",
        }))

        # Create logic file
        (component / "processor.py").write_text("""
DOMAIN = 'my_component'

def process_data(data):
    return [item for item in data if item.get('active', True)]
""".strip())

        # Create test file in tests/ directory with mirror name - must be >= 300 bytes
        # Structure: component/tests/test_processor.py (tests at component level)
        (component / "tests").mkdir(parents=True, exist_ok=True)
        (component / "tests" / "test_processor.py").write_text("""import processor

def test_process_data():
    '''Test process_data with various scenarios.'''
    # Test with active items
    data = [{'active': True}, {'active': False}, {'active': True}]
    result = processor.process_data(data)
    assert len(result) == 2, f'Expected 2 active items but got {len(result)}'

    # Test with all active
    all_active = [{'active': True}, {'active': True}]
    result = processor.process_data(all_active)
    assert len(result) == 2, f'Expected 2 items but got {len(result)}'

    # Test with all inactive
    all_inactive = [{'active': False}, {'active': False}]
    result = processor.process_data(all_inactive)
    assert len(result) == 0, f'Expected 0 items but got {len(result)}'

    print('All tests passed')
""".strip())

        config = ProcessingConfig(
            base_dir=tmp_path,
            raw_subdir="test_repo",
            output_subdir="output",
            category="myrepo",
            module_discovery_strategy="manifest",
            extensions={".py"},
        )
        processor = RepoProcessor(config)
        processor.run()

        # Verify bundle was created
        output_dir = tmp_path / "output" / "myrepo"
        bundle_files = list(output_dir.rglob("*.txt"))

        # Should have FUNCTIONAL_UNIT bundle (TYPE 1)
        functional_unit_files = [
            f for f in bundle_files
            if 'FUNCTIONAL_UNIT' in f.read_text()
        ]

        assert len(functional_unit_files) > 0, (
            "Test file in tests/ directory should trigger TYPE 1 bundle"
        )

    def test_no_test_file_no_type1(self, tmp_path: Path) -> None:
        """Test that logic files without test files do not generate TYPE 1.

        Without a test file, the logic file should only generate TYPE 3
        (LOGIC_ONLY) if it's large enough, or TYPE 4 (MODULE_BLUEPRINT).
        """
        repo_root = tmp_path / "test_repo"
        repo_root.mkdir()

        myrepo = repo_root / "myrepo"
        myrepo.mkdir()

        component = myrepo / "custom_components" / "test_component"
        component.mkdir(parents=True)

        # Create manifest.json
        import json
        (component / "manifest.json").write_text(json.dumps({
            "domain": "test_component",
            "name": "Test",
            "version": "1.0.0",
        }))

        # Create logic file WITHOUT a test file
        (component / "processor.py").write_text("""
def process_data(data):
    return [item for item in data]
""".strip())

        config = ProcessingConfig(
            base_dir=tmp_path,
            raw_subdir="test_repo",
            output_subdir="output",
            category="myrepo",
            module_discovery_strategy="manifest",
            extensions={".py"},
        )
        processor = RepoProcessor(config)
        processor.run()

        # Verify bundle was created
        output_dir = tmp_path / "output" / "myrepo"
        bundle_files = list(output_dir.rglob("*.txt"))

        # Should NOT have FUNCTIONAL_UNIT bundle (TYPE 1)
        functional_unit_files = [
            f for f in bundle_files
            if 'FUNCTIONAL_UNIT' in f.read_text()
        ]

        assert len(functional_unit_files) == 0, (
            "Logic file without test file should not trigger TYPE 1 bundle"
        )

        # Should have MODULE_BLUEPRINT (TYPE 4)
        blueprint_files = [
            f for f in bundle_files
            if 'MODULE_BLUEPRINT' in f.read_text()
        ]

        assert len(blueprint_files) > 0, (
            "MODULE_BLUEPRINT should always be emitted"
        )

    def test_non_mirror_name_not_detected(self, tmp_path: Path) -> None:
        """Test that test files with non-mirror names are not paired.

        Only test_<logic_filename>.py pattern is detected as test.
        """
        repo_root = tmp_path / "test_repo"
        repo_root.mkdir()

        myrepo = repo_root / "myrepo"
        myrepo.mkdir()

        component = myrepo / "custom_components" / "test_component"
        component.mkdir(parents=True)

        # Create manifest.json
        import json
        (component / "manifest.json").write_text(json.dumps({
            "domain": "test_component",
            "name": "Test",
            "version": "1.0.0",
        }))

        # Create logic file
        (component / "utils.py").write_text("""
def calculate_total(items):
    total = 0
    for item in items:
        total += item.get('price', 0)
    return total
""".strip())

        # Create test file with non-mirror name - must be >= 300 bytes
        # Structure: component/tests/test_calculations.py (tests at component level)
        (component / "tests").mkdir(parents=True, exist_ok=True)
        (component / "tests" / "test_calculations.py").write_text("""import utils

def test_calculate_total():
    '''Test calculate_total with various scenarios.'''
    # Test with simple price list
    items = [{'price': 10}, {'price': 20}]
    result = utils.calculate_total(items)
    assert result == 30, f'Expected 30 but got {result}'

    # Test with empty list
    empty_result = utils.calculate_total([])
    assert empty_result == 0, f'Expected 0 for empty list'

    # Test with mixed price and cost keys
    mixed_items = [
        {'price': 100, 'cost': 50},
        {'cost': 200, 'price': 150}
    ]
    total = utils.calculate_total(mixed_items)
    assert total == 500, f'Expected 500 but got {total}'

    print('All tests passed')
""".strip())

        config = ProcessingConfig(
            base_dir=tmp_path,
            raw_subdir="test_repo",
            output_subdir="output",
            category="myrepo",
            module_discovery_strategy="manifest",
            extensions={".py"},
        )
        processor = RepoProcessor(config)
        processor.run()

        # Verify bundle was created
        output_dir = tmp_path / "output" / "myrepo"
        bundle_files = list(output_dir.rglob("*.txt"))

        # Should NOT have FUNCTIONAL_UNIT bundle (TYPE 1)
        functional_unit_files = [
            f for f in bundle_files
            if 'FUNCTIONAL_UNIT' in f.read_text()
        ]

        assert len(functional_unit_files) == 0, (
            "Test file with non-mirror name should not trigger TYPE 1 bundle"
        )
