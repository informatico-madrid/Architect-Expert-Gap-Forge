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

    # Create component directory
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

    # Create tests directory INSIDE the repo (owner/myrepo/tests)
    tests_dir = owner_dir / "tests" / "custom_components" / "test_component"
    tests_dir.mkdir(parents=True, exist_ok=True)
    test_file = tests_dir / "test_logic.py"
    test_file.write_text(PYTHON_TEST_WITH_LOGIC)
    print('Test file size:', test_file.stat().st_size)

    print('\n--- Directory structure ---')
    print(f'owner_dir: {owner_dir}')
    for item in sorted(owner_dir.rglob('*')):
        if item.is_file():
            rel = item.relative_to(owner_dir)
            print(f'  {rel}')

    # Discover modules
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

    print('\nModules found:', len(modules))
    for mod in modules:
        print(f'  Module: {mod.name}')
        for mf in mod.files:
            print(f'    - {mf.path.name} (role={mf.role}, size={mf.size})')

    # Find test for logic.py
    test_result = find_test(logic_file, owner_dir, MAX_SIZE_BACKEND)
    print(f'\nfind_test result: {test_result}')

    # Process
    config = ProcessingConfig(
        base_dir=tmp_path,
        raw_subdir="test_repo",
        output_subdir="output",
        category="owner",
        profile="homeassistant",
    )
    processor = RepoProcessor(config)
    processor.run()

    # Check output
    output_dir = tmp_path / "output" / "owner"
    print('\nOutput dir exists:', output_dir.exists())
    if output_dir.exists():
        bundle_files = list(output_dir.rglob("*.txt"))
        print('Bundle files found:', len(bundle_files))
        for f in bundle_files:
            content = f.read_text()
            if 'FUNCTIONAL_UNIT' in content:
                print(f'  {f.name}: FUNCTIONAL_UNIT')
            elif 'LOGIC_ONLY' in content:
                print(f'  {f.name}: LOGIC_ONLY')
            elif 'MODULE_BLUEPRINT' in content:
                print(f'  {f.name}: MODULE_BLUEPRINT')
            else:
                print(f'  {f.name}: (unknown)')
                print(f'    First 200 chars: {content[:200]}')

    # Check stats
    print('\nProcessor stats:')
    print(f'  TYPE1_FUNCTIONAL_UNIT: {processor._stats["TYPE1_FUNCTIONAL_UNIT"]}')
    print(f'  TYPE3_LOGIC_ONLY: {processor._stats["TYPE3_LOGIC_ONLY"]}')
    print(f'  TYPE4_MODULE_BLUEPRINT: {processor._stats["TYPE4_MODULE_BLUEPRINT"]}')
