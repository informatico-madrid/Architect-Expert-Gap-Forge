#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0
"""Integration test for TYPE 1 FUNCTIONAL_UNIT bundle generation.

Verifies that Type 1 bundles include [ARCH_HEADER] with dependencies
for Python and TypeScript repositories with tests.

Uses the actual functional APIs: RepoProcessor, parse_bundle.
Requirements: AC-1.1 to AC-1.4
"""

import json
import tempfile
import shutil
from pathlib import Path

from src.discovery import ProcessingConfig, RepoProcessor
from src.factory.fragment_extractor import parse_bundle

# Processor iteration: source_root/owner_dir/repo_dir/
# source_root = base_dir / raw_subdir / category

_MANIFEST = {"domain": "test_domain", "name": "Test", "version": "1.0.0"}


class TestType1FunctionalUnit:
    """TYPE 1 FUNCTIONAL_UNIT integration test."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tmpdir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _create_test_repo(self, owner: str, repo_dir: str, files: dict[str, str]):
        """Create a test repo.

        Structure: base_dir/raw_subdir/category/owner_dir/repo_dir/
        source_root = base_dir / raw_subdir / category = base_dir/owner/owner
        repo lives at: base_dir/owner/owner/{owner}/{repo_dir}/
        """
        repo_path = self.tmpdir / owner / owner / owner / repo_dir
        repo_path.mkdir(parents=True, exist_ok=True)
        for file_path, content in files.items():
            full_path = repo_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)

    def _process_repository(self, owner: str):
        """Process repos under this owner using RepoProcessor."""
        config = ProcessingConfig(
            base_dir=self.tmpdir,
            raw_subdir=owner,
            output_subdir="output",
            category=owner,
            extensions={".py", ".ts", ".tsx"},
            module_discovery_strategy="manifest",
        )
        processor = RepoProcessor(config)
        processor.run()

        # Read output bundles and parse them
        # Output path: base_dir/output/category/owner_dir/repo_dir/
        output_dir = self.tmpdir / "output" / owner
        bundles = []
        for bundle_file in output_dir.rglob("*.txt"):
            txt = bundle_file.read_text()
            parsed = parse_bundle(txt)
            parsed["_raw"] = txt
            bundles.append(parsed)
        return bundles

    def test_type_1_python_with_test(self):
        """Verify Type 1 bundle for Python repo with test file.

        Tests AC-1.1 to AC-1.4:
        - AC-1.1: Logic file paired with test
        - AC-1.2: Test file mirror detection
        - AC-1.3: Size gate bypassed when test exists
        - AC-1.4: [ARCH_HEADER] with dependencies
        """
        self._create_test_repo(
            "owner1",
            "pyrepo",
            {
                "manifest.json": json.dumps(_MANIFEST),
                "module.py": """
def calculate_total(items):
    total = 0
    for item in items:
        total += item['price']
    return total

def apply_discount(total, discount_pct):
    return total * (1 - discount_pct / 100)
""".strip(),
                "test_module.py": """
import module

def test_calculate_total():
    items = [{'price': 10}, {'price': 20}]
    result = module.calculate_total(items)
    assert result == 30

def test_apply_discount():
    total = 100
    result = module.apply_discount(total, 10)
    assert result == 90
""",
            },
        )

        bundles = self._process_repository("owner1")

        # Find Type 1 bundle
        type1_bundle = None
        for bundle in bundles:
            if bundle.get("type") == "FUNCTIONAL_UNIT":
                type1_bundle = bundle
                break

        assert type1_bundle is not None, "TYPE 1 FUNCTIONAL_UNIT should be emitted"

        # Verify [ARCH_HEADER] with dependencies
        assert "[ARCH_HEADER]" in type1_bundle.get("_raw", ""), (
            "FUNCTIONAL_UNIT should have [ARCH_HEADER]"
        )
        arch_header = type1_bundle.get("_raw", "")
        assert "dependencies" in arch_header.lower()

        # Verify bundle includes both logic and test
        files_bundled = type1_bundle.get("files", {})
        file_names = list(files_bundled.keys())
        assert any("module" in f and not f.startswith("test_") for f in file_names)
        assert any("test_module" in f for f in file_names)

    def test_type_1_typescript_with_test(self):
        """Verify Type 1 bundle for TypeScript repo with test file.

        Tests AC-1.1 to AC-1.4 for TypeScript.
        """
        self._create_test_repo(
            "owner1",
            "tsrepo",
            {
                "manifest.json": json.dumps(_MANIFEST),
                "utils/format.ts": """
export function formatCurrency(amount: number): string {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
    }).format(amount);
}

export function formatDate(date: Date): string {
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
    });
}
""".strip(),
                "test_format.ts": """
import { formatCurrency } from './utils/format';

describe('formatCurrency', () => {
    it('formats number correctly', () => {
        const result = formatCurrency(100);
        expect(result).toBe('$100.00');
    });
});
""",
            },
        )

        bundles = self._process_repository("owner1")

        type1_bundle = None
        for bundle in bundles:
            if bundle.get("type") == "FUNCTIONAL_UNIT":
                type1_bundle = bundle
                break

        assert type1_bundle is not None, "TYPE 1 FUNCTIONAL_UNIT should be emitted"

        # Verify [ARCH_HEADER] with dependencies
        arch_header = type1_bundle.get("_raw", "")
        assert "[ARCH_HEADER]" in arch_header
        assert "dependencies" in arch_header.lower()

        # Verify bundle includes both logic and test
        files_bundled = type1_bundle.get("files", {})
        file_names = list(files_bundled.keys())
        assert any("format.ts" in f for f in file_names)
        assert any("test_format" in f for f in file_names)

    def test_type_3_without_test(self):
        """Verify standalone files without tests are Type 3 (not Type 1).

        Confirms that files without tests are not paired for Type 1.
        """
        self._create_test_repo(
            "owner1",
            "nottest",
            {
                "manifest.json": json.dumps(_MANIFEST),
                "helper.py": """
def get_env_variable(name: str, default: str = '') -> str:
    import os
    return os.environ.get(name, default)

def parse_int(value: str) -> int:
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0
""".strip(),
            },
        )

        bundles = self._process_repository("owner1")

        # Verify no Type 1 bundle (no test to pair with)
        type1_found = any(b.get("type") == "FUNCTIONAL_UNIT" for b in bundles)
        assert not type1_found, "No TYPE 1 FUNCTIONAL_UNIT should exist without test"

        # Should have Type 4 MODULE_BLUEPRINT at minimum
        type4_found = any(b.get("type") == "MODULE_BLUEPRINT" for b in bundles)
        assert type4_found, "TYPE 4 MODULE_BLUEPRINT should always be emitted"

    def test_type_4_module_blueprint(self):
        """Verify TYPE 4 MODULE_BLUEPRINT is emitted for all repos."""
        self._create_test_repo(
            "owner1",
            "crosslang",
            {
                "manifest.json": json.dumps(_MANIFEST),
                "api/client.py": """
class APIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url

    def get(self, endpoint: str) -> dict:
        import requests
        response = requests.get(f"{self.base_url}/{endpoint}")
        return response.json()
""",
                "api/types.ts": """
export interface ApiResponse<T> {
    data: T;
    status: number;
    message: string;
}
""".strip(),
            },
        )

        bundles = self._process_repository("owner1")

        type4_bundle = None
        for bundle in bundles:
            if bundle.get("type") == "MODULE_BLUEPRINT":
                type4_bundle = bundle
                break

        assert type4_bundle is not None, "TYPE 4 MODULE_BLUEPRINT should be emitted"

        # Verify MODULE_BLUEPRINT structure
        raw = type4_bundle.get("_raw", "")
        assert "[MODULE_MAP]" in raw
        assert "[DEPENDENCIES]" in raw

    def test_bundle_types_all_present(self):
        """Verify bundles have required fields."""
        self._create_test_repo(
            "owner1",
            "fullsuite",
            {
                "manifest.json": json.dumps(_MANIFEST),
                "module.py": """
def process_data(data: list) -> list:
    results = []
    for item in data:
        processed = {'id': item.get('id'), 'value': item.get('value', 0) * 2}
        results.append(processed)
    return results
""".strip(),
                "test_module.py": """
import module

def test_process_data():
    data = [{'id': 1, 'value': 5}]
    result = module.process_data(data)
    assert len(result) == 1
    assert result[0]['value'] == 10
""",
                "README.md": """
# Full Suite Test
This repository tests all fragment types.
""",
                ".gitignore": """
*.pyc
__pycache__/
.env
""".strip(),
            },
        )

        bundles = self._process_repository("owner1")

        # All bundles should have required fields
        for bundle in bundles:
            assert "type" in bundle
            assert "arch" in bundle
            assert "files" in bundle
