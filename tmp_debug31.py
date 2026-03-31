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

    # Create repository root files directly at repo_root
    (repo_root / "component.ts").write_text(TYPESCRIPT_SAMPLE)

    # Test config creation
    config = ProcessingConfig(
        base_dir=tmp_path,
        raw_subdir=".",
        output_subdir="output",
        category="test_repo",
        profile="typescript",
    )

    # Debug output
    print(f'module_discovery_strategy: {config.module_discovery_strategy}')
    print(f'extensions: {config.extensions}')
    print(f'profile: {config.profile}')

    # Verify the mapping
    profile_to_strategy = {
        "typescript": "typescript",
        "yaml": "yaml",
        "filesystem": "filesystem",
    }
    expected = profile_to_strategy.get(config.profile, "auto")
    print(f'Expected strategy: {expected}')
    print(f'Strategy matches: {config.module_discovery_strategy == expected}')
