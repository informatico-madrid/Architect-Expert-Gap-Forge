# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio
# SPDX-License-Identifier: Apache-2.0

"""Python repository fixture for testing Python processing."""

PYTHON_REPO_CODE = """
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
"""

PYTHON_TEST_CODE = """
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
"""

PYTHON_MANIFEST = """{
    "name": "Test Component",
    "version": "1.0.0",
    "domain": "test_component"
}
"""
