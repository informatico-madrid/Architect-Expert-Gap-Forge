from pathlib import Path
import tempfile
import json
from src.discovery import ProcessingConfig, RepoProcessor
from src.discovery.file_scanner import discover_modules, find_test
from src.discovery.fragment_parser import build_module, make_arch_header
from src.discovery.fragment_parser import extract_local_imports

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
"""

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

    # Create manifest.json
    (component / 'manifest.json').write_text(json.dumps({
        'domain': 'test',
        'name': 'Test',
        'version': '1.0',
        'dependencies': []
    }))

    # Create logic file
    (component / 'logic.py').write_text(PYTHON_LOGIC_WITH_TEST)

    # Create tests directory
    tests_dir = owner_dir / 'tests' / 'custom_components' / 'test_component'
    tests_dir.mkdir(parents=True, exist_ok=True)
    (tests_dir / 'test_logic.py').write_text(PYTHON_TEST_WITH_LOGIC)

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

    print('Modules found:', len(modules))

    # Process each module like the processor does
    prefix = "myrepo"
    size_limit = 150000  # MAX_SIZE_BACKEND

    for mod in modules:
        print(f'\nModule: {mod.name}')
        for mf in mod.files:
            if mf.role == "test" or mf.path.name in ("manifest.json", "const.py", "services.yaml", "strings.json", "icons.json", "hacs.json", "__init__.py"):
                print(f'  Skipping {mf.path.name} (role={mf.role})')
                continue

            print(f'  Processing: {mf.path.name} (size={mf.size})')

            # Read content
            content = mf.path.read_text(encoding="utf-8", errors="ignore")
            print(f'    Content length: {len(content)}')

            # Find test
            test_file = find_test(mf.path, owner_dir, size_limit)
            print(f'    find_test result: {test_file}')

            if test_file:
                print(f'    -> Would emit FUNCTIONAL_UNIT!')
