from pathlib import Path
import tempfile
from src.discovery.file_scanner import find_test, MIN_SIZE, MAX_SIZE_BACKEND

PYTHON_LOGIC_WITH_TEST = """
def add_numbers(a: int, b: int) -> int:
    '''Add two numbers together.'''
    return a + b
"""

PYTHON_TEST_WITH_LOGIC = """# Comprehensive test suite for logic module
# This test file verifies the core functionality of the add_numbers
# and calculate_total functions with various input scenarios.

import pytest


def test_add_numbers_basic():
    '''Test basic addition scenarios with various inputs.'''
    assert add_numbers(2, 3) == 5
    assert add_numbers(0, 0) == 0
    assert add_numbers(-1, 1) == 0
    assert add_numbers(100, 200) == 300
    assert add_numbers(-50, -50) == -100
    assert add_numbers(1, 1) == 2
    assert add_numbers(999, 1) == 1000
"""

with tempfile.TemporaryDirectory() as tmp:
    tmp_path = Path(tmp)
    repo_root = tmp_path / "test_repo"
    repo_root.mkdir()

    # Create owner directory structure
    owner_dir = repo_root / "owner" / "myrepo"
    owner_dir.mkdir(parents=True, exist_ok=True)

    # Create component directory
    component = owner_dir / "custom_components" / "test_component"
    component.mkdir(parents=True, exist_ok=True)

    # Create logic file
    logic_file = component / "logic.py"
    logic_file.write_text(PYTHON_LOGIC_WITH_TEST)
    print('Logic file:', logic_file)
    print('Logic file size:', logic_file.stat().st_size)

    # Create tests directory INSIDE owner/myrepo (the repo root)
    tests_dir = owner_dir / "tests" / "custom_components" / "test_component"
    tests_dir.mkdir(parents=True, exist_ok=True)
    test_file = tests_dir / "test_logic.py"
    test_file.write_text(PYTHON_TEST_WITH_LOGIC)
    print('Test file:', test_file)
    print('Test file size:', test_file.stat().st_size)

    # Call find_test with owner_dir as repo_root
    print('\nCalling find_test with repo_root=owner_dir')
    result = find_test(logic_file, owner_dir, MAX_SIZE_BACKEND)
    print(f'Result: {result}')

    # Debug: check if file exists at expected path
    rel = logic_file.relative_to(owner_dir)
    print(f'\nRelative path: {rel}')
    test_name = f"test_{logic_file.name}"
    print(f'Test name: {test_name}')
    expected = owner_dir / "tests" / rel.parent / test_name
    print(f'Expected path: {expected}')
    print(f'Exists: {expected.exists()}')

    # Check _ok function
    print(f'\n_min_size <= {test_file.stat().st_size} <= {MAX_SIZE_BACKEND}')
    print(f'{MIN_SIZE} <= {test_file.stat().st_size} <= {MAX_SIZE_BACKEND}')
    print(f'Result: {MIN_SIZE} <= {test_file.stat().st_size} and {test_file.stat().st_size} <= {MAX_SIZE_BACKEND}')
    print(f'Check: {MIN_SIZE <= test_file.stat().st_size <= MAX_SIZE_BACKEND}')
