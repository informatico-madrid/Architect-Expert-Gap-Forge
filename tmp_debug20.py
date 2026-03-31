from pathlib import Path
import tempfile
import json
import logging
from src.discovery import ProcessingConfig, RepoProcessor
from src.discovery.file_scanner import discover_modules, find_test, MIN_SIZE, MAX_SIZE_BACKEND
from src.discovery.fragment_parser import build_module

logging.basicConfig(level=logging.DEBUG)

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

    # Create component directory INSIDE the repo (owner/myrepo/custom_components)
    component = owner_dir / "custom_components" / "test_component"
    component.mkdir(parents=True, exist_ok=True)

    # Create manifest.json
    (component / "manifest.json").write_text(json.dumps({
        "domain": "test",
        "name": "Test",
        "version": "1.0",
        "dependencies": []
    }))

    # Create logic file
    logic_file = component / "logic.py"
    logic_file.write_text(PYTHON_LOGIC_WITH_TEST)
    print('Logic file size:', logic_file.stat().st_size)

    # Create tests directory INSIDE the repo at the same level as custom_components
    # This is the expected structure: owner/myrepo/tests/... and owner/myrepo/custom_components/...
    tests_dir = owner_dir / "tests" / "custom_components" / "test_component"
    tests_dir.mkdir(parents=True, exist_ok=True)

    # Create test file
    test_file = tests_dir / "test_logic.py"
    test_file.write_text(PYTHON_TEST_WITH_LOGIC)
    print('Test file size:', test_file.stat().st_size)

    print('\n--- Directory structure ---')
    print(f'owner_dir: {owner_dir}')
    print('owner_dir contents:')
    for item in sorted(owner_dir.iterdir()):
        print(f'  {item.name}: is_dir={item.is_dir()}')
        if item.is_dir():
            for sub in sorted(item.iterdir()):
                print(f'    {sub.name}: is_dir={sub.is_dir()}')

    # Discover modules from owner_dir
    print('\n--- Discovering modules from owner_dir ---')
    modules = discover_modules(
        root=owner_dir,
        strategy='manifest',
        ignore_patterns={'.git', '__pycache__', 'venv', 'node_modules', '.tox', 'eggs'},
        extensions={'.py', '.md'},
        anchor_filenames=set(),
        module_overrides=None,
        build_module_func=lambda mod_dir, anchor_type, manifest=None: build_module(
            mod_dir=mod_dir,
            anchor_type=anchor_type,
            extensions={'.py', '.md'},
            ignore_patterns={'.git', '__pycache__', 'venv', 'node_modules', '.tox', 'eggs'},
            manifest=manifest or {},
        ),
    )
    print(f'Modules found: {len(modules)}')
    for mod in modules:
        print(f'  Module: {mod.name}')
        print(f'    path: {mod.path}')
        print(f'    repo_root should be: {owner_dir}')
        print(f'    modules found path should be inside: {owner_dir}')

    # Process
    print('\n--- Processing ---')
    config = ProcessingConfig(
        base_dir=tmp_path,
        raw_subdir="test_repo",
        output_subdir="output",
        category="owner",
        profile="homeassistant",
    )
    processor = RepoProcessor(config)
    print(f'source_root: {processor.source_root}')
    print(f'target_root: {processor.target_root}')
    print(f'Iterating source_root:')
    for owner in sorted(processor.source_root.iterdir()):
        print(f'  {owner.name}: is_dir={owner.is_dir()}')
        if owner.is_dir():
            print(f'    list({owner.name}):')
            for repo in sorted(owner.iterdir()):
                print(f'      {repo.name}: is_dir={repo.is_dir()}')

    processor.run()

    # Check output
    output_dir = tmp_path / "output" / "owner"
    print('\nOutput dir exists:', output_dir.exists())
    if output_dir.exists():
        for p in sorted(output_dir.rglob('*')):
            if p.is_file():
                print(f'  {p.name}')
                content = p.read_text()
                if 'FUNCTIONAL_UNIT' in content:
                    print('    -> FOUND FUNCTIONAL_UNIT!')
                elif 'LOGIC_ONLY' in content:
                    print('    -> FOUND LOGIC_ONLY!')
                else:
                    print('    -> MODULE_BLUEPRINT')

    # Check stats
    print('\nProcessor stats:')
    print(f'  TYPE1_FUNCTIONAL_UNIT: {processor._stats["TYPE1_FUNCTIONAL_UNIT"]}')
    print(f'  TYPE3_LOGIC_ONLY: {processor._stats["TYPE3_LOGIC_ONLY"]}')
    print(f'  TYPE4_MODULE_BLUEPRINT: {processor._stats["TYPE4_MODULE_BLUEPRINT"]}')
    print(f'  skipped_size: {processor._stats["skipped_size"]}')
