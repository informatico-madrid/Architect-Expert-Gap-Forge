from pathlib import Path
import tempfile
import json
from src.discovery import ProcessingConfig, RepoProcessor
from src.discovery.file_scanner import discover_modules
from src.discovery.fragment_parser import build_module

PYTHON_LOGIC_WITH_TEST = """
def add_numbers(a: int, b: int) -> int:
    '''Add two numbers together.'''
    return a + b

def calculate_total(items: list) -> float:
    '''Calculate the total price of items.'''
    total = 0
    for item in items:
        total += item['price']
    return total

def process_data(data: dict) -> dict:
    '''Process data with multiple transformations.'''
    result = {}
    for key, value in data.items():
        if isinstance(value, dict):
            result[key] = process_nested_dict(value)
        elif isinstance(value, list):
            result[key] = process_list(value)
        else:
            result[key] = transform_scalar(value)
    return result

def process_nested_dict(nested: dict) -> dict:
    '''Recursively process nested dictionaries.'''
    output = {}
    for k, v in nested.items():
        if isinstance(v, dict):
            output[k] = process_nested_dict(v)
        elif isinstance(v, list):
            output[k] = [transform_scalar(item) for item in v]
        else:
            output[k] = transform_scalar(v)
    return output

def process_list(items: list) -> list:
    '''Process a list of items through transformation pipeline.'''
    result = []
    for item in items:
        if isinstance(item, dict):
            result.append(process_nested_dict(item))
        elif isinstance(item, list):
            result.extend(item)
        else:
            result.append(transform_scalar(item))
    return result

def transform_scalar(value) -> str:
    '''Transform a scalar value to string representation.'''
    if value is None:
        return 'null'
    elif isinstance(value, bool):
        return 'true' if value else 'false'
    elif isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, str):
        return value
    else:
        return str(value)
"""

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

    # Create manifest.json
    (component / 'manifest.json').write_text(json.dumps({
        'domain': 'test',
        'name': 'Test',
        'version': '1.0',
        'dependencies': []
    }))

    # Create logic file (use a proper name without "test" prefix)
    (component / 'logic.py').write_text(PYTHON_LOGIC_WITH_TEST)
    print('Logic file size:', (component / 'logic.py').stat().st_size)

    # Create tests directory INSIDE the repo
    tests_dir = owner_dir / 'tests' / 'custom_components' / 'test_component'
    tests_dir.mkdir(parents=True, exist_ok=True)
    (tests_dir / 'test_logic.py').write_text(PYTHON_TEST_WITH_LOGIC)
    print('Test file size:', (tests_dir / 'test_logic.py').stat().st_size)

    # Process
    config = ProcessingConfig(
        base_dir=tmp_path,
        raw_subdir='test_repo',
        output_subdir='output',
        category='owner',
        profile='homeassistant',
    )
    processor = RepoProcessor(config)
    processor.run()

    # Check output
    output_dir = tmp_path / 'output' / 'owner'
    print('Output dir exists:', output_dir.exists())
    if output_dir.exists():
        print('Files in output:')
        for p in sorted(output_dir.rglob('*')):
            if p.is_file():
                print(f'  {p.name}')
                if p.suffix == '.txt':
                    content = p.read_text()
                    if 'FUNCTIONAL_UNIT' in content:
                        print('    -> FOUND FUNCTIONAL_UNIT!')
                    elif 'LOGIC_ONLY' in content:
                        print('    -> FOUND LOGIC_ONLY!')
                    else:
                        print('    -> MODULE_BLUEPRINT only')
            else:
                print(f'  {p.name}/')
