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

    config = ProcessingConfig(
        base_dir=owner_dir.parent,  # tmp/test_repo/owner
        raw_subdir=".",
        output_subdir="output",
        category="myrepo",
        profile="typescript",
    )

    processor = RepoProcessor(config)
    print(f'source_root: {processor.source_root}')
    print(f'target_root: {processor.target_root}')
    print(f'module_discovery_strategy: {config.module_discovery_strategy}')
    print(f'extensions: {config.extensions}')
    processor.run()

    # Check output
    print(f'\ntarget_root exists: {processor.target_root.exists()}')
    if processor.target_root.exists():
        bundle_files = list(processor.target_root.rglob("*.txt"))
        print(f'Bundle files found: {len(bundle_files)}')
        for f in bundle_files:
            content = f.read_text()
            if 'MODULE_BLUEPRINT' in content:
                print(f'  {f.name}: MODULE_BLUEPRINT')
