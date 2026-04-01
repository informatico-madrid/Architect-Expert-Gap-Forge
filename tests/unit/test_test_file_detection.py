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
        # Create repo structure: tmp_path/owner/myrepo/
        # Tests go at tmp_path/owner/tests/ (at repo root, not owner/myrepo/tests/)
        repo_root = tmp_path / "owner" / "myrepo"
        repo_root.mkdir(parents=True)

        component = repo_root / "custom_components" / "test_component"
        component.mkdir(parents=True)

        # Create manifest.json
        import json
        (component / "manifest.json").write_text(json.dumps({
            "domain": "test_component",
            "name": "Test",
            "version": "1.0.0",
        }))

        # Create logic file - must be >= 300 bytes to be processed
        (component / "utils.py").write_text("""
def calculate_total(items):
    '''Calculate total price from a list of items with price or cost keys.'''
    total = 0
    for item in items:
        if isinstance(item, dict):
            price = item.get('price', 0)
            cost = item.get('cost', 0)
            total += max(price, cost)
        elif isinstance(item, (int, float)):
            total += item
    return total

def calculate_discounted_total(items, discount_rate):
    '''Calculate total with discount applied.'''
    total = calculate_total(items)
    discount = total * discount_rate
    return total - discount

def validate_items(items):
    '''Validate that all items have required keys.'''
    for item in items:
        if not isinstance(item, dict):
            return False
        if 'price' not in item and 'cost' not in item:
            return False
    return True

def format_currency(amount):
    '''Format amount as currency string.'''
    return f"${amount:.2f}"

def parse_currency(string):
    '''Parse currency string back to float.'''
    return float(string.replace('$', '').replace(',', ''))
""".strip())

        # Create test file at repo root's tests/ directory (owner/tests/, not owner/myrepo/tests/)
        # Structure: tmp_path/owner/tests/custom_components/test_component/test_utils.py
        (repo_root.parent / "tests").mkdir(parents=True, exist_ok=True)
        (repo_root.parent / "tests" / "custom_components" / "test_component").mkdir(parents=True, exist_ok=True)
        (repo_root.parent / "tests" / "custom_components" / "test_component" / "test_utils.py").write_text("""import utils

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

def test_calculate_discount():
    '''Test calculate_total with discounts.'''
    items = [{'price': 100, 'discount': 10}]
    result = utils.calculate_total(items)
    assert result == 100, f'Expected 100 but got {result}'

def test_calculate_tax():
    '''Test calculate_total with tax.'''
    items = [{'price': 50}]
    result = utils.calculate_total(items)
    assert result == 50, f'Expected 50 but got {result}'

def test_edge_cases():
    '''Test edge cases for calculate_total.'''
    # Test with single item
    single_item = [{'price': 42}]
    result = utils.calculate_total(single_item)
    assert result == 42, f'Expected 42 but got {result}'

    # Test with many items
    many_items = [{'price': i} for i in range(100)]
    result = utils.calculate_total(many_items)
    assert result == sum(range(100)), f'Expected sum of 0-99 but got {result}'

def test_validation():
    '''Validate input types.'''
    try:
        utils.calculate_total(['invalid'])
    except (KeyError, TypeError):
        pass

def test_logging():
    '''Test logging functionality.'''
    import logging
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    logger.debug('Test logging works')
""".strip())

        config = ProcessingConfig(
            base_dir=tmp_path,
            raw_subdir=".",
            output_subdir="output",
            category="owner",  # Use 'owner' so source_root includes both myrepo/ and tests/
            module_discovery_strategy="manifest",
            extensions={".py"},
        )
        processor = RepoProcessor(config)
        processor.run()

        # Verify bundle was created
        output_dir = tmp_path / "output" / "owner"
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
        # Create repo structure: tmp_path/owner/myrepo/
        # Tests go at tmp_path/owner/tests/ (at repo root, not owner/myrepo/tests/)
        repo_root = tmp_path / "owner" / "myrepo"
        repo_root.mkdir(parents=True)

        component = repo_root / "custom_components" / "my_component"
        component.mkdir(parents=True)

        # Create manifest.json
        import json
        (component / "manifest.json").write_text(json.dumps({
            "domain": "my_component",
            "name": "My Component",
            "version": "1.0.0",
        }))

        # Create logic file - must be >= 300 bytes to be processed
        (component / "processor.py").write_text("""
DOMAIN = 'my_component'

def process_data(data):
    '''Process incoming data and filter by active status.'''
    result = []
    for item in data:
        if isinstance(item, dict):
            active = item.get('active', True)
            if active:
                result.append(item)
        elif isinstance(item, (int, float, str)):
            result.append({'value': item, 'active': True})
    return result

def validate_data(data):
    '''Validate that data is a list of valid items.'''
    if not isinstance(data, list):
        return False
    for item in data:
        if not isinstance(item, (dict, int, float, str)):
            return False
    return True

def transform_data(data, transform_func):
    '''Apply a transformation function to each item.'''
    return [transform_func(item) for item in data if item is not None]

def aggregate_data(data, key='active'):
    '''Aggregate data by a specific key.'''
    result = {}
    for item in data:
        if isinstance(item, dict):
            k = item.get(key, 'unknown')
            result[k] = result.get(k, 0) + 1
    return result

def filter_by_criteria(data, criteria):
    '''Filter data by matching criteria dictionary.'''
    return [
        item for item in data
        if isinstance(item, dict)
        and all(item.get(k) == v for k, v in criteria.items())
    ]

def sort_data(data, key='active', reverse=False):
    '''Sort data by a specific key.'''
    return sorted(data, key=lambda x: x.get(key, False), reverse=reverse)
""".strip())

        # Create test file at repo root's tests/ directory
        # Structure: tmp_path/owner/tests/custom_components/my_component/test_processor.py
        (repo_root.parent / "tests").mkdir(parents=True, exist_ok=True)
        (repo_root.parent / "tests" / "custom_components" / "my_component").mkdir(parents=True, exist_ok=True)
        (repo_root.parent / "tests" / "custom_components" / "my_component" / "test_processor.py").write_text("""import processor

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

def test_process_empty():
    '''Test process_data with empty list.'''
    result = processor.process_data([])
    assert result == [], f'Expected empty list but got {result}'

def test_process_none():
    '''Test process_data validation.'''
    try:
        processor.process_data(None)
    except (TypeError, AttributeError):
        pass

def test_process_invalid():
    '''Test process_data with invalid input.'''
    try:
        processor.process_data('invalid')
    except (TypeError, AttributeError):
        pass

def test_logging():
    '''Test logging functionality.'''
    import logging
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    logger.debug('Test logging works')

def test_edge_cases():
    '''Test edge cases for process_data.'''
    # Test with single item
    single = [{'active': True}]
    result = processor.process_data(single)
    assert len(result) == 1

    # Test with many items
    many = [{'active': i % 2 == 0} for i in range(100)]
    result = processor.process_data(many)
    assert len(result) == 50
""".strip())

        config = ProcessingConfig(
            base_dir=tmp_path,
            raw_subdir=".",
            output_subdir="output",
            category="owner",  # Use 'owner' so source_root includes both myrepo/ and tests/
            module_discovery_strategy="manifest",
            extensions={".py"},
        )
        processor = RepoProcessor(config)
        processor.run()

        # Verify bundle was created
        output_dir = tmp_path / "output" / "owner"
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
        # Create repo structure: tmp_path/owner/myrepo/
        repo_root = tmp_path / "owner" / "myrepo"
        repo_root.mkdir(parents=True)

        component = repo_root / "custom_components" / "test_component"
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
            raw_subdir=".",
            output_subdir="output",
            category="owner",  # Use 'owner' so source_root includes both myrepo/ and tests/
            module_discovery_strategy="manifest",
            extensions={".py"},
        )
        processor = RepoProcessor(config)
        processor.run()

        # Verify bundle was created
        output_dir = tmp_path / "output" / "owner"
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
        # Create repo structure: tmp_path/owner/myrepo/
        repo_root = tmp_path / "owner" / "myrepo"
        repo_root.mkdir(parents=True)

        component = repo_root / "custom_components" / "test_component"
        component.mkdir(parents=True)

        # Create manifest.json
        import json
        (component / "manifest.json").write_text(json.dumps({
            "domain": "test_component",
            "name": "Test",
            "version": "1.0.0",
        }))

        # Create logic file - must be >= 300 bytes to be processed
        (component / "utils.py").write_text("""
def calculate_total(items):
    '''Calculate total price from a list of items with price or cost keys.'''
    total = 0
    for item in items:
        if isinstance(item, dict):
            price = item.get('price', 0)
            cost = item.get('cost', 0)
            total += max(price, cost)
        elif isinstance(item, (int, float)):
            total += item
    return total

def calculate_discounted_total(items, discount_rate):
    '''Calculate total with discount applied.'''
    total = calculate_total(items)
    discount = total * discount_rate
    return total - discount

def validate_items(items):
    '''Validate that all items have required keys.'''
    for item in items:
        if not isinstance(item, dict):
            return False
        if 'price' not in item and 'cost' not in item:
            return False
    return True

def format_currency(amount):
    '''Format amount as currency string.'''
    return f"${amount:.2f}"

def parse_currency(string):
    '''Parse currency string back to float.'''
    return float(string.replace('$', '').replace(',', ''))
""".strip())

        # Create test file with non-mirror name at repo root's tests/ directory
        # Structure: tmp_path/owner/tests/custom_components/test_component/test_calculations.py
        (repo_root.parent / "tests").mkdir(parents=True, exist_ok=True)
        (repo_root.parent / "tests" / "custom_components" / "test_component").mkdir(parents=True, exist_ok=True)
        (repo_root.parent / "tests" / "custom_components" / "test_component" / "test_calculations.py").write_text("""import utils

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
            raw_subdir=".",
            output_subdir="output",
            category="owner",  # Use 'owner' so source_root includes both myrepo/ and tests/
            module_discovery_strategy="manifest",
            extensions={".py"},
        )
        processor = RepoProcessor(config)
        processor.run()

        # Verify bundle was created
        output_dir = tmp_path / "output" / "owner"
        bundle_files = list(output_dir.rglob("*.txt"))

        # Should NOT have FUNCTIONAL_UNIT bundle (TYPE 1)
        functional_unit_files = [
            f for f in bundle_files
            if 'FUNCTIONAL_UNIT' in f.read_text()
        ]

        assert len(functional_unit_files) == 0, (
            "Test file with non-mirror name should not trigger TYPE 1 bundle"
        )
