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

    # Create owner directory structure
    owner_dir = repo_root / "owner" / "myrepo"
    owner_dir.mkdir(parents=True, exist_ok=True)

    # Create repository root files in owner/myrepo
    (owner_dir / "component.ts").write_text(TYPESCRIPT_SAMPLE)

    config = ProcessingConfig(
        base_dir=owner_dir.parent,
        raw_subdir=".",
        output_subdir="output",
        category="myrepo",
        profile="typescript",
    )

    processor = RepoProcessor(config)
    print(f'source_root: {processor.source_root}')

    # Discover modules manually
    modules = discover_modules(
        root=processor.source_root,
        strategy=config.module_discovery_strategy,
        ignore_patterns=config.ignore_patterns,
        extensions=config.extensions,
        anchor_filenames=config.anchor_filenames,
        module_overrides=None,
        build_module_func=processor._build_module,
    )

    print(f'Modules found: {len(modules)}')
    for mod in modules:
        print(f'  Module: {mod.name}')
        for mf in mod.files:
            print(f'    - {mf.path.name} (role={mf.role}, size={mf.size})')
