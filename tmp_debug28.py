from pathlib import Path
import tempfile
import json
import logging
from src.discovery import ProcessingConfig, RepoProcessor
from src.discovery.file_scanner import discover_modules, MIN_SIZE, MAX_SIZE_BACKEND
from src.discovery.fragment_parser import build_module

logging.basicConfig(level=logging.DEBUG)

TYPESCRIPT_SAMPLE = """
interface User {
    id: number;
    name: string;
}

function getUser(id: number): User {
    return { id, name: "Test" };
}
"""

with tempfile.TemporaryDirectory() as tmp:
    tmp_path = Path(tmp)
    repo_root = tmp_path / "test_repo"
    repo_root.mkdir()

    # Create repository root files directly at repo_root
    (repo_root / "component.ts").write_text(TYPESCRIPT_SAMPLE)

    print('\n--- Directory structure ---')
    for item in sorted(repo_root.rglob('*')):
        if item.is_file():
            rel = item.relative_to(repo_root)
            print(f'  {rel}')

    # Discover modules with typescript strategy
    modules = discover_modules(
        root=repo_root,
        strategy='typescript',
        ignore_patterns={'.git', '__pycache__', 'venv', 'node_modules', '.tox', 'eggs'},
        extensions={'.ts', '.tsx', '.py', '.md'},
        anchor_filenames=set(),
        module_overrides=None,
        build_module_func=lambda mod_dir, anchor_type, manifest=None: build_module(
            mod_dir=mod_dir,
            anchor_type=anchor_type,
            extensions={'.ts', '.tsx', '.py', '.md'},
            ignore_patterns={'.git', '__pycache__', 'venv', 'node_modules', '.tox', 'eggs'},
            manifest=manifest or {},
        ),
    )

    print('\nModules found:', len(modules))
    for mod in modules:
        print(f'  Module: {mod.name}')
        for mf in mod.files:
            print(f'    - {mf.path.name} (role={mf.role}, size={mf.size})')
