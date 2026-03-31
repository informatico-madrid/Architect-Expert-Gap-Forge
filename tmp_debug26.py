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

    # Create owner directory structure - files directly in owner_dir
    owner_dir = repo_root / "test_repo"
    owner_dir.mkdir(parents=True, exist_ok=True)

    # Create repository root files
    (owner_dir / "component.ts").write_text(TYPESCRIPT_SAMPLE)

    print('\n--- Directory structure ---')
    for item in sorted(repo_root.rglob('*')):
        if item.is_file():
            rel = item.relative_to(repo_root)
            print(f'  {rel}')
    print()

    # Process
    config = ProcessingConfig(
        base_dir=tmp_path,
        raw_subdir="test_repo",
        output_subdir="output",
        category="test_repo",
        profile="typescript",
    )
    processor = RepoProcessor(config)
    processor.run()

    # Check output
    output_dir = tmp_path / "output" / "test_repo"
    print('Output dir exists:', output_dir.exists())
    if output_dir.exists():
        bundle_files = list(output_dir.rglob("*.txt"))
        print('Bundle files found:', len(bundle_files))
        for f in bundle_files:
            content = f.read_text()
            if 'MODULE_BLUEPRINT' in content:
                print(f'  {f.name}: MODULE_BLUEPRINT')
            else:
                print(f'  {f.name}: (unknown)')

    # Check stats
    print('\nProcessor stats:')
    print(f'  TYPE1_FUNCTIONAL_UNIT: {processor._stats["TYPE1_FUNCTIONAL_UNIT"]}')
    print(f'  TYPE3_LOGIC_ONLY: {processor._stats["TYPE3_LOGIC_ONLY"]}')
    print(f'  TYPE4_MODULE_BLUEPRINT: {processor._stats["TYPE4_MODULE_BLUEPRINT"]}')
