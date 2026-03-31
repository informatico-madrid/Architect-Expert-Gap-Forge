from pathlib import Path
import tempfile
import json
import logging
from src.discovery import ProcessingConfig, RepoProcessor

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

    print('--- Directory structure ---')
    for item in sorted(owner_dir.rglob('*')):
        if item.is_file():
            rel = item.relative_to(owner_dir)
            print(f'  {rel}')
    print(f'owner_dir: {owner_dir}')
    print(f'owner_dir.parent: {owner_dir.parent}')

    config = ProcessingConfig(
        base_dir=owner_dir.parent,
        raw_subdir=".",
        output_subdir="output",
        category="myrepo",
        profile="typescript",
    )
    print(f'module_discovery_strategy: {config.module_discovery_strategy}')
    print(f'extensions: {config.extensions}')
    print(f'raw_subdir: {config.raw_subdir}')

    processor = RepoProcessor(config)
    print(f'source_root: {processor.source_root}')
    print(f'source_root exists: {processor.source_root.exists()}')
    processor.run()

    # Check output
    output_dir = owner_dir.parent.parent / "output" / "myrepo"
    print(f'\nOutput dir exists: {output_dir.exists()}')
    if output_dir.exists():
        bundle_files = list(output_dir.rglob("*.txt"))
        print(f'Bundle files found: {len(bundle_files)}')
        for f in bundle_files:
            content = f.read_text()
            if 'MODULE_BLUEPRINT' in content:
                print(f'  {f.name}: MODULE_BLUEPRINT')

    print(f'\nProcessor stats:')
    print(f'  TYPE4_MODULE_BLUEPRINT: {processor._stats["TYPE4_MODULE_BLUEPRINT"]}')
