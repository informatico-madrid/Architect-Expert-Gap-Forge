from pathlib import Path
import tempfile
from src.discovery.file_scanner import find_test, MIN_SIZE, MAX_SIZE_BACKEND

PYTHON_TEST_WITH_LOGIC = """# Test suite for test_logic module
# This test file verifies the core functionality of the add_numbers
# and calculate_total functions with various input scenarios.

import pytest


def test_add_numbers_basic():
    '''Test basic addition scenarios.'''
    assert add_numbers(2, 3) == 5
    assert add_numbers(0, 0) == 0
    assert add_numbers(-1, 1) == 0
    assert add_numbers(100, 200) == 300


def test_calculate_total():
    '''Test total calculation with list of items.'''
    items = [{'price': 10}, {'price': 20}]
    assert calculate_total(items) == 30

    # Test with empty list
    assert calculate_total([]) == 0

    # Test with single item
    assert calculate_total([{'price': 100}]) == 100
"""

with tempfile.TemporaryDirectory() as tmp:
    tmp_path = Path(tmp)
    repo_root = tmp_path / 'test_repo'
    repo_root.mkdir()

    # Create owner directory structure
    owner_dir = repo_root / 'owner' / 'myrepo'
    owner_dir.mkdir(parents=True, exist_ok=True)

    # Create component directory
    component = owner_dir / 'custom_components' / 'test_component'
    component.mkdir(parents=True, exist_ok=True)

    # Create logic file
    logic_file = component / 'logic.py'
    logic_file.write_text('def add_numbers(a, b): return a + b')
    print('Logic file:', logic_file)
    print('Logic file size:', logic_file.stat().st_size)

    # Create tests directory
    tests_dir = owner_dir / 'tests' / 'custom_components' / 'test_component'
    tests_dir.mkdir(parents=True, exist_ok=True)
    test_file = tests_dir / 'test_logic.py'
    test_file.write_text(PYTHON_TEST_WITH_LOGIC)
    print('Test file:', test_file)
    print('Test file size:', test_file.stat().st_size)

    # Find test
    result = find_test(logic_file, owner_dir, MAX_SIZE_BACKEND)
    print('find_test result:', result)
    print('MIN_SIZE:', MIN_SIZE)
    print('MAX_SIZE_BACKEND:', MAX_SIZE_BACKEND)
