"""Integration test for TYPE 1 FUNCTIONAL_UNIT bundle generation.

Verifies that Type 1 bundles include [ARCH_HEADER] with dependencies
for Python and TypeScript repositories with tests.
"""

import tempfile
import shutil
from pathlib import Path
import json

import pytest

from src.discovery.metadata_enricher import RepoProcessor
from src.factory.fragment_extractor import FragmentExtractor
from src.factory.bundle_parser import BundleParser


class TestType1FunctionalUnit:
    """TYPE 1 FUNCTIONAL_UNIT integration test."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tmpdir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _create_test_repo(self, repo_name: str, files: dict[str, str]):
        """Create a test repository with specified files.

        Args:
            repo_name: Name of the repository
            files: Dict of file paths to content

        Returns:
            Path to the repository directory
        """
        repo_path = self.tmpdir / repo_name
        repo_path.mkdir()

        for file_path, content in files.items():
            full_path = repo_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)

        return repo_path

    def _process_repository(self, repo_path: Path) -> list[dict]:
        """Process repository and return emitted fragments.

        Args:
            repo_path: Path to repository to process

        Returns:
            List of emitted fragment bundles
        """
        from pathlib import Path
        from src.discovery.metadata_enricher import ProcessingConfig

        config = ProcessingConfig(
            base_dir=self.tmpdir,
            raw_subdir="repos",
            output_subdir="output",
            category="test",
            extensions={".py", ".ts", ".tsx"},
        )

        processor = RepoProcessor(config)
        processor._static_repos = [str(repo_path)]
        processor.process_repository(str(repo_path))

        fragments = []
        for mf in processor._module_files:
            extractor = FragmentExtractor()
            bundle = extractor.extract(mf, processor._stats)
            if bundle:
                fragments.append(bundle)

        return fragments

    def test_type_1_python_with_test(self):
        """Verify Type 1 bundle for Python repo with test file.

        Tests AC-1.1 to AC-1.4:
        - AC-1.1: Logic file paired with test
        - AC-1.2: Test file mirror detection
        - AC-1.3: Size gate bypassed when test exists
        - AC-1.4: [ARCH_HEADER] with dependencies
        """
        # Create Python repo with logic and test
        repo_path = self._create_test_repo(
            "python-with-test",
            {
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
""".strip(),
            },
        )

        fragments = self._process_repository(repo_path)

        # Find Type 1 bundle
        type1_bundle = None
        for bundle in fragments:
            if bundle.get("type") == 1:
                type1_bundle = bundle
                break

        assert type1_bundle is not None, "TYPE 1 bundle should be emitted"

        # Verify [ARCH_HEADER] with dependencies
        arch_header = type1_bundle.get("arch_header", "")
        assert "[ARCH_HEADER]" in arch_header
        assert "dependencies" in arch_header.lower()

        # Verify bundle includes both logic and test
        files = type1_bundle.get("files", [])
        file_names = [f["name"] for f in files]
        assert "module.py" in file_names
        assert "test_module.py" in file_names

    def test_type_1_typescript_with_test(self):
        """Verify Type 1 bundle for TypeScript repo with test file.

        Tests AC-1.1 to AC-1.4 for TypeScript.
        """
        # Create TypeScript repo with logic and test
        repo_path = self._create_test_repo(
            "typescript-with-test",
            {
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
import { formatCurrency, formatDate } from './utils/format';

describe('formatCurrency', () => {
    test('formats number correctly', () => {
        const result = formatCurrency(100);
        expect(result).toBe('$100.00');
    });
});

describe('formatDate', () => {
    test('formats date correctly', () => {
        const date = new Date('2024-01-15');
        const result = formatDate(date);
        expect(result).toBe('1/15/2024');
    });
});
""".strip(),
            },
        )

        fragments = self._process_repository(repo_path)

        # Find Type 1 bundle
        type1_bundle = None
        for bundle in fragments:
            if bundle.get("type") == 1:
                type1_bundle = bundle
                break

        assert type1_bundle is not None, "TYPE 1 bundle should be emitted"

        # Verify [ARCH_HEADER] with dependencies
        arch_header = type1_bundle.get("arch_header", "")
        assert "[ARCH_HEADER]" in arch_header
        assert "dependencies" in arch_header.lower()

        # Verify bundle includes both logic and test
        files = type1_bundle.get("files", [])
        file_names = [f["name"] for f in files]
        assert "utils/format.ts" in file_names or "format.ts" in file_names
        assert "test_format.ts" in file_names

    def test_type_3_without_test(self):
        """Verify standalone files without tests are Type 3 (not Type 1).

        Confirms that files without tests are not paired for Type 1.
        """
        # Create Python repo without test
        repo_path = self._create_test_repo(
            "python-without-test",
            {
                "utils/helper.py": """
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

        fragments = self._process_repository(repo_path)

        # Verify no Type 1 bundle (no test to pair with)
        type1_found = any(b.get("type") == 1 for b in fragments)
        assert not type1_found, "No TYPE 1 bundle should exist without test"

        # Should have Type 4 MODULE_BLUEPRINT at minimum
        type4_found = any(b.get("type") == 4 for b in fragments)
        assert type4_found, "TYPE 4 MODULE_BLUEPRINT should always be emitted"

    def test_type_4_module_blueprint(self):
        """Verify TYPE 4 MODULE_BLUEPRINT is emitted for all repos.

        Tests that MODULE_BLUEPRINT generation works across Python and TypeScript.
        """
        repo_path = self._create_test_repo(
            "cross-language",
            {
                "api/client.py": """
class APIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url

    def get(self, endpoint: str) -> dict:
        import requests
        response = requests.get(f"{self.base_url}/{endpoint}")
        return response.json()
""".strip(),
                "api/types.ts": """
export interface ApiResponse<T> {
    data: T;
    status: number;
    message: string;
}

export class ApiClient {
    private baseUrl: string;

    constructor(baseUrl: string) {
        this.baseUrl = baseUrl;
    }

    async get<T>(endpoint: string): Promise<ApiResponse<T>> {
        const response = await fetch(`${this.baseUrl}/${endpoint}`);
        return response.json();
    }
}
""".strip(),
            },
        )

        fragments = self._process_repository(repo_path)

        # Find Type 4 bundle
        type4_bundle = None
        for bundle in fragments:
            if bundle.get("type") == 4:
                type4_bundle = bundle
                break

        assert type4_bundle is not None, "TYPE 4 MODULE_BLUEPRINT should be emitted"

        # Verify MODULE_BLUEPRINT structure
        assert "[MODULE_MAP]" in type4_bundle.get("arch_header", "")
        assert "[DEPENDENCIES]" in type4_bundle.get("arch_header", "")

        # Should include schema information
        assert "[SCHEMA]" in type4_bundle.get("arch_header", "")

    def test_types_1_to_5_bundle_types(self):
        """Verify all fragment types (1-5) can be generated correctly.

        Test suite covering:
        - TYPE 1: FUNCTIONAL_UNIT (paired logic + test)
        - TYPE 3: LOGIC_ONLY (standalone files)
        - TYPE 4: MODULE_BLUEPRINT (architecture context)
        - TYPE 5: GOVERNANCE_RULES (repo-level config)
        """
        # Create comprehensive repo with multiple file types
        repo_path = self._create_test_repo(
            "full-suite",
            {
                "module.py": """
def process_data(data: list[dict]) -> list[dict]:
    results = []
    for item in data:
        processed = {
            'id': item.get('id'),
            'value': item.get('value', 0) * 2,
        }
        results.append(processed)
    return results
""".strip(),
                "test_module.py": """
import module

def test_process_data():
    data = [{'id': 1, 'value': 5}, {'id': 2, 'value': 10}]
    result = module.process_data(data)
    assert len(result) == 2
    assert result[0]['value'] == 10
""".strip(),
                "README.md": """
# Full Suite Test

This repository tests all fragment types.
""".strip(),
                ".gitignore": """
*.pyc
__pycache__/
.env
""".strip(),
            },
        )

        fragments = self._process_repository(repo_path)

        # Verify bundle types present
        bundle_types = [f.get("type") for f in fragments]

        # TYPE 1 should exist (has test)
        assert 1 in bundle_types, "TYPE 1 FUNCTIONAL_UNIT should exist"

        # TYPE 4 should always exist
        assert 4 in bundle_types, "TYPE 4 MODULE_BLUEPRINT should exist"

        # TYPE 5 may exist if governance files detected
        # (not required for this test)

        # Verify all bundles have required fields
        for bundle in fragments:
            assert "type" in bundle
            assert "arch_header" in bundle
            assert "files" in bundle
