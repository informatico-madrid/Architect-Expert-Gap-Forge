from pathlib import Path
import tempfile
import json
from src.discovery import ProcessingConfig, RepoProcessor
from src.discovery.file_scanner import discover_modules

PYTHON_LOGIC_WITH_TEST = """
def add_numbers(a: int, b: int) -> int:
    return a + b

def calculate_total(items: list) -> float:
    total = 0
    for item in items:
        total += item['price']
    return total
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

    # Create logic file
    logic_file = component / 'test_logic.py'
    logic_file.write_text(PYTHON_LOGIC_WITH_TEST)
    print('Logic file size:', logic_file.stat().st_size)

    # Create tests directory
    tests_dir = owner_dir / 'tests' / 'custom_components' / 'test_component'
    tests_dir.mkdir(parents=True, exist_ok=True)
    test_file = tests_dir / 'test_test_logic.py'
    test_file.write_text(PYTHON_TEST_WITH_LOGIC)

    # Discover modules manually
    modules = discover_modules(
        root=owner_dir,
        strategy='manifest',
        ignore_patterns={'.git', '__pycache__', 'venv', 'node_modules', '.tox', 'eggs'},
        extensions={'.py', '.md'},
        anchor_filenames=set(),
        module_overrides=None,
    )

    print('Modules found:', len(modules))
    for mod in modules:
        print(f'  Module: {mod.name}')
        print(f'    Path: {mod.path}')
        print(f'    Files: {len(mod.files)}')
        for mf in mod.files:
            print(f'      - {mf.path.name} (role={mf.role}, size={mf.size})')

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
    print('\nOutput dir exists:', output_dir.exists())
    if output_dir.exists():
        for p in sorted(output_dir.rglob('*')):
            rel_path = p.relative_to(tmp_path)
            if p.is_file():
                print(f'  {rel_path}')
                if p.suffix == '.txt':
                    content = p.read_text()
                    print(f'    -> {content[:300]}...')
            else:
                print(f'  {rel_path}/')
