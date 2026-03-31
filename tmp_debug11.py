from pathlib import Path
import tempfile
from src.discovery.file_scanner import find_test, MIN_SIZE, MAX_SIZE_BACKEND

PYTHON_TEST_WITH_LOGIC = """# Test suite for test_logic module

import pytest


def test_add_numbers_basic():
    '''Test basic addition scenarios.'''
    assert add_numbers(2, 3) == 5
    assert add_numbers(0, 0) == 0
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

    # Create tests directory INSIDE owner/myrepo (the repo root)
    tests_dir = owner_dir / 'tests' / 'custom_components' / 'test_component'
    tests_dir.mkdir(parents=True, exist_ok=True)
    test_file = tests_dir / 'test_logic.py'
    test_file.write_text(PYTHON_TEST_WITH_LOGIC)
    print('Test file:', test_file)
    print('Test file size:', test_file.stat().st_size)

    # Call find_test with owner_dir as repo_root
    print('\nCalling find_test with repo_root=owner_dir')
    print('owner_dir:', owner_dir)
    result = find_test(logic_file, owner_dir, MAX_SIZE_BACKEND)
    print('Result:', result)

    # Debug: what path is find_test looking for?
    rel = logic_file.relative_to(owner_dir)
    print('\nRelative path:', rel)
    print('rel.parent:', rel.parent)
    test_name = f"test_{logic_file.name}"
    print('test_name:', test_name)
    expected_path = owner_dir / "tests" / rel.parent / test_name
    print('Expected path:', expected_path)
    print('Exists:', expected_path.exists())
    print('Is file:', expected_path.is_file() if expected_path.exists() else 'N/A')
    if expected_path.exists():
        print('Size:', expected_path.stat().st_size)
        print('MIN_SIZE:', MIN_SIZE)
        print('MAX_SIZE_BACKEND:', MAX_SIZE_BACKEND)
