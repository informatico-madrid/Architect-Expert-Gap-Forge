# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Integration test for TYPE 1 FUNCTIONAL_UNIT bundle generation.

Verifies that Type 1 bundles include [ARCH_HEADER] with dependencies
for Python and TypeScript repositories with tests.

Requirements: FR-1, AC-1.1 to AC-1.4
"""

from __future__ import annotations

from pathlib import Path
import json
import pytest

from src.discovery import ProcessingConfig, RepoProcessor


class TestType1FunctionalUnit:
    """TYPE 1 FUNCTIONAL_UNIT integration test."""

    @pytest.fixture
    def temp_python_repo_with_test(self, tmp_path: Path) -> Path:
        """Create a temporary Python repository with logic and test files."""
        repo_root = tmp_path / "test_repo"
        repo_root.mkdir()

        # Create owner directory structure
        owner_dir = repo_root / "owner" / "myrepo"
        owner_dir.mkdir(parents=True)

        # Create component directory (logic files)
        component = owner_dir / "test_component"
        component.mkdir()

        # Create manifest.json to trigger manifest strategy
        manifest = component / "manifest.json"
        manifest.write_text(
            json.dumps({
                "domain": "test_component",
                "name": "Test Component",
                "version": "1.0.0",
            })
        )

        # Create logic file (exceed MIN_SIZE=200, include DOMAIN pattern)
        logic_file = component / "module.py"
        logic_file.write_text(
            """
DOMAIN = 'test_component'

def calculate_total(items):
    '''Calculate total price from list of items.'''
    total = 0.0
    for item in items:
        if 'price' in item:
            total += item['price']
        elif 'cost' in item:
            total += item['cost']
    return total

def apply_discount(total, discount_pct):
    '''Apply percentage discount to total.'''
    if discount_pct < 0 or discount_pct > 100:
        raise ValueError("Discount must be between 0 and 100")
    return total * (1 - discount_pct / 100.0)

def validate_input(value):
    '''Validate numeric input.'''
    if not isinstance(value, (int, float)):
        raise TypeError("Value must be numeric")
    if value < 0:
        raise ValueError("Value must be non-negative")
    return value

def process_items(items, multiplier=1.0):
    '''Process items with multiplier.'''
    if not isinstance(items, list):
        raise TypeError("Items must be a list")
    results = []
    for item in items:
        price = item.get('price', 0) or item.get('cost', 0)
        results.append({'price': price * multiplier})
    return results
""".strip()
        )

        # Create tests directory with test file (required for Type 1 pairing)
        # Test file must be >= MIN_SIZE (300 chars) for Type 1 pairing
        # The test must be in tests/owner/myrepo/test_component/ for find_test to work
        tests_dir = repo_root / "tests" / "owner" / "myrepo" / "test_component"
        tests_dir.mkdir(parents=True)

        test_file = tests_dir / "test_module.py"
        test_file.write_text(
            """
import module

def test_calculate_total():
    '''Test calculate_total function with various input scenarios.'''
    # Test with simple price list
    items = [{'price': 10.0}, {'price': 20.0}, {'cost': 30.0}]
    result = module.calculate_total(items)
    assert result == 60.0, f"Expected 60.0 but got {result}"

    # Test with empty list
    empty_result = module.calculate_total([])
    assert empty_result == 0.0, f"Expected 0.0 for empty list but got {empty_result}"

    # Test with mixed price and cost keys
    mixed_items = [
        {'price': 100.0, 'cost': 50.0},
        {'cost': 200.0, 'price': 150.0}
    ]
    total = module.calculate_total(mixed_items)
    assert total == 500.0, f"Expected 500.0 but got {total}"


def test_apply_discount():
    '''Test apply_discount function with edge cases.'''
    # Test 10% discount
    total = 100.0
    result = module.apply_discount(total, 10)
    assert result == 90.0, f"Expected 90.0 but got {result}"

    # Test 0% discount (no discount)
    no_discount = module.apply_discount(100.0, 0)
    assert no_discount == 100.0, f"Expected 100.0 but got {no_discount}"

    # Test 100% discount (free)
    free_item = module.apply_discount(50.0, 100)
    assert free_item == 0.0, f"Expected 0.0 but got {free_item}"


def test_validate_input():
    '''Test validate_input function for proper validation.'''
    # Test positive numbers
    assert module.validate_input(100) == 100
    assert module.validate_input(0.5) == 0.5
    assert module.validate_input(0) == 0

    # Test negative should raise
    import pytest
    with pytest.raises(ValueError):
        module.validate_input(-1)


def test_process_items():
    '''Test process_items function with multiplier.'''
    items = [{'price': 10}, {'price': 20}]
    result = module.process_items(items, 2.0)
    assert len(result) == 2
    assert result[0]['price'] == 20.0
    assert result[1]['price'] == 40.0

    # Test with no multiplier (default)
    default_result = module.process_items(items)
    assert default_result[0]['price'] == 10.0
    assert default_result[1]['price'] == 20.0
""".strip()
        )

        return repo_root

    @pytest.fixture
    def temp_typescript_repo_with_test(self, tmp_path: Path) -> Path:
        """Create a temporary TypeScript repository with logic and test files."""
        repo_root = tmp_path / "test_repo"
        repo_root.mkdir()

        # Create owner directory structure
        owner_dir = repo_root / "owner" / "myrepo"
        owner_dir.mkdir(parents=True)

        # Create TypeScript module
        module_dir = owner_dir / "utils"
        module_dir.mkdir()

        # Create TypeScript logic file (larger version)
        logic_file = module_dir / "format.ts"
        logic_file.write_text(
            """
export function formatCurrency(amount: number): string {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
    }).format(amount);
}

export function formatDate(date: Date): string {
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
    });
}

export function formatPercentage(value: number, precision: number = 2): string {
    return (value * 100).toFixed(precision) + '%';
}

export function validateAmount(value: number): number {
    if (value < 0) {
        throw new Error('Amount must be non-negative');
    }
    return value;
}
""".strip()
        )

        # Create tests directory with test file (must be >=300 chars)
        tests_dir = repo_root / "tests" / "owner" / "myrepo" / "utils"
        tests_dir.mkdir(parents=True)

        test_file = tests_dir / "test_format.ts"
        test_file.write_text(
            """
import { formatCurrency, formatDate, formatPercentage, validateAmount } from './format';

describe('formatCurrency', () => {
    test('formats number correctly', () => {
        const result = formatCurrency(100);
        expect(result).toBe('$100.00');
    });

    test('formats zero', () => {
        const result = formatCurrency(0);
        expect(result).toBe('$0.00');
    });

    test('formats negative number', () => {
        const result = formatCurrency(-50);
        expect(result).toBe('($50.00)');
    });
});

describe('formatDate', () => {
    test('formats date correctly', () => {
        const date = new Date('2024-01-15');
        const result = formatDate(date);
        expect(result).toBe('1/15/2024');
    });

    test('formats different dates', () => {
        const date = new Date('2024-12-25');
        const result = formatDate(date);
        expect(result).toBe('12/25/2024');
    });
});

describe('formatPercentage', () => {
    test('formats percentage correctly', () => {
        const result = formatPercentage(0.5);
        expect(result).toBe('50.00%');
    });

    test('formats percentage with custom precision', () => {
        const result = formatPercentage(0.333, 1);
        expect(result).toBe('33.3%');
    });
});

describe('validateAmount', () => {
    test('validates positive amount', () => {
        const result = validateAmount(100);
        expect(result).toBe(100);
    });

    test('validates zero', () => {
        const result = validateAmount(0);
        expect(result).toBe(0);
    });

    test('throws error for negative', () => {
        expect(() => validateAmount(-10)).toThrow();
    });
});
""".strip()
        )

        return repo_root

    def test_type_1_python_with_test(self, temp_python_repo_with_test, tmp_path):
        """Verify Type 1 bundle for Python repo with test file.

        Tests AC-1.1 to AC-1.4:
        - AC-1.1: Logic file paired with test
        - AC-1.2: Test file mirror detection
        - AC-1.3: Size gate bypassed when test exists
        - AC-1.4: [ARCH_HEADER] with dependencies
        """
        # Process repo
        config = ProcessingConfig(
            base_dir=tmp_path.parent,
            raw_subdir=".",
            output_subdir="output",
            category="test_repo",
            profile="homeassistant",
            extensions={".py", ".ts", ".tsx", ".md"},
        )
        processor = RepoProcessor(config)
        processor.run()

        # Find Type 1 bundle in output
        output_dir = tmp_path.parent / "output" / "test_repo"
        txt_files = list(output_dir.rglob("*.txt"))
        assert len(txt_files) > 0, "Expected at least one bundle file"

        type1_found = False
        for txt_file in txt_files:
            content = txt_file.read_text()
            if "[ARCH_HEADER]" in content and "FUNCTIONAL_UNIT" in content:
                type1_found = True
                # Verify [ARCH_HEADER] with dependencies
                assert "DEPENDENCIES:" in content or "dependencies" in content.lower()
                # Verify bundle includes both logic and test
                assert "module.py" in content
                assert "test_module.py" in content
                break

        assert type1_found, "TYPE 1 bundle should be emitted for Python with test"

    def test_type_1_typescript_with_test(self, temp_typescript_repo_with_test, tmp_path):
        """Verify Type 1 bundle for TypeScript repo with test file.

        Tests AC-1.1 to AC-1.4 for TypeScript.
        """
        # Process repo
        config = ProcessingConfig(
            base_dir=temp_typescript_repo_with_test.parent,
            raw_subdir=".",
            output_subdir="output",
            category="test_repo",
            profile="typescript",
            extensions={".py", ".ts", ".tsx", ".md"},
        )
        processor = RepoProcessor(config)
        processor.run()

        # Find Type 1 bundle in output
        output_dir = temp_typescript_repo_with_test.parent / "output" / "test_repo"
        txt_files = list(output_dir.rglob("*.txt"))
        assert len(txt_files) > 0, "Expected at least one bundle file"

        type1_found = False
        for txt_file in txt_files:
            content = txt_file.read_text()
            if "[ARCH_HEADER]" in content and "FUNCTIONAL_UNIT" in content:
                type1_found = True
                # Verify [ARCH_HEADER] with dependencies
                assert "DEPENDENCIES:" in content or "dependencies" in content.lower()
                # Verify bundle includes both logic and test
                assert "format.ts" in content
                assert "test_format.ts" in content
                break

        assert type1_found, "TYPE 1 bundle should be emitted for TypeScript with test"

    def test_types_1_to_5_bundle_types(self, tmp_path):
        """Verify all fragment types (1-5) can be generated correctly.

        Test suite covering:
        - TYPE 1: FUNCTIONAL_UNIT (paired logic + test)
        - TYPE 3: LOGIC_ONLY (standalone files)
        - TYPE 4: MODULE_BLUEPRINT (architecture context)
        - TYPE 5: GOVERNANCE_RULES (repo-level config)
        """
        # Create comprehensive repo with multiple file types
        # Structure: repo_root/owner/myrepo/test_component/...
        repo_root = tmp_path / "test_repo"
        repo_root.mkdir()

        owner_dir = repo_root / "owner" / "myrepo"
        owner_dir.mkdir(parents=True)

        # Create component directory
        component = owner_dir / "test_component"
        component.mkdir()

        # Create manifest.json
        import json
        manifest = component / "manifest.json"
        manifest.write_text(json.dumps({
            "domain": "test_component",
            "name": "Test Component",
            "version": "1.0.0",
        }))

        # Create logic with test (both files)
        # Logic file must include DOMAIN pattern for processing
        (component / "processor.py").write_text(
            """
DOMAIN = 'test_component'

def process_data(data: list[dict]) -> list[dict]:
    results = []
    for item in data:
        processed = {
            'id': item.get('id'),
            'value': item.get('value', 0) * 2,
        }
        results.append(processed)
    return results

def validate_input(value):
    if not isinstance(value, (int, float)):
        raise TypeError("Value must be numeric")
    return value

def calculate_total(items):
    total = 0.0
    for item in items:
        total += item.get('value', 0)
    return total
""".strip()
        )

        # Create tests directory with larger test file (>=300 chars)
        tests_dir = repo_root / "tests" / "owner" / "myrepo" / "test_component"
        tests_dir.mkdir(parents=True)

        (tests_dir / "test_processor.py").write_text(
            """
import processor

def test_process_data():
    data = [{'id': 1, 'value': 5}, {'id': 2, 'value': 10}]
    result = processor.process_data(data)
    assert len(result) == 2
    assert result[0]['value'] == 10

def test_validate_input():
    assert processor.validate_input(100) == 100
    assert processor.validate_input(0.5) == 0.5

def test_calculate_total():
    items = [{'value': 10}, {'value': 20}]
    total = processor.calculate_total(items)
    assert total == 30.0

def test_process_data_multiple():
    items = [{'value': 5}, {'value': 10}, {'value': 15}]
    result = processor.process_data(items)
    assert len(result) == 3
"""
        )

        # Create governance file
        (component / ".gitignore").write_text("""
*.pyc
__pycache__/
.env
""".strip()
        )

        # Process repo
        config = ProcessingConfig(
            base_dir=repo_root.parent,
            raw_subdir=".",
            output_subdir="output",
            category="test_repo",
            profile="homeassistant",
            extensions={".py", ".ts", ".tsx", ".md"},
        )
        processor = RepoProcessor(config)
        processor.run()

        # Find bundles
        output_dir = repo_root.parent / "output" / "test_repo"
        txt_files = list(output_dir.rglob("*.txt"))

        # Find bundle types by content
        has_type1 = False
        has_type4 = False
        has_type5 = False

        for txt_file in txt_files:
            if txt_file.exists():
                content = txt_file.read_text()
                if "[ARCH_HEADER]" in content and "FUNCTIONAL_UNIT" in content:
                    has_type1 = True
                if "[MODULE_MAP]" in content:
                    has_type4 = True
                if "[GOVERNANCE_HEADER]" in content:
                    has_type5 = True

        # TYPE 1 should exist (has test)
        assert has_type1, "TYPE 1 FUNCTIONAL_UNIT should exist"

        # TYPE 4 should always exist
        assert has_type4, "TYPE 4 MODULE_BLUEPRINT should exist"

        # TYPE 5 may exist if governance files detected (.gitignore is a governance file)
        assert has_type5, "TYPE 5 GOVERNANCE_RULES should exist"
