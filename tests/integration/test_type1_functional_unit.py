# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Integration tests for TYPE 1 FUNCTIONAL_UNIT bundle generation.

These tests verify that TYPE 1 bundles include [ARCH_HEADER] with:
- LOCAL_IMPORTS for relative imports
- DEPENDENCIES for external imports
- Proper file pairing (logic file + test file)

Requirements: FR-1, AC-1.1 to AC-1.4
- AC-1.1: Logic files with tests are paired as FUNCTIONAL_UNIT
- AC-1.2: Size gate bypassed for tested code
- AC-1.3: [ARCH_HEADER] includes local_imports and dependencies
- AC-1.4: Test files are included as context in the bundle
"""

from __future__ import annotations

from pathlib import Path
import pytest

from src.discovery import ProcessingConfig, RepoProcessor


class TestType1FunctionalUnitPython:
    """TYPE 1 FUNCTIONAL_UNIT tests for Python repositories."""

    @pytest.fixture
    def temp_repo(self, tmp_path: Path) -> Path:
        """Create a temporary Python repository with logic and test files."""
        repo = tmp_path / "test_owner" / "test_repo"
        repo.mkdir(parents=True)

        # Create a logic file (under MIN_SIZE but will bypass due to test pairing)
        (repo / "my_module.py").write_text("""
import os
import sys
from . import helper

def process_data(data):
    \"\"\"Process incoming data.\"\"\"
    result = []
    for item in data:
        if item > 0:
            result.append(item * 2)
    return result


def format_output(results):
    \"\"\"Format results for display.\"\"\"
    return \\', \\'.join(str(r) for r in results)
""")

        # Create an __init__.py
        (repo / "__init__.py").write_text("")

        # Create test file (exact name mirror)
        (repo / "test_my_module.py").write_text("""
import sys
sys.path.insert(0, \'\')

from my_module import process_data, format_output


def test_process_data():
    \"\"\"Test process_data function.\"\"\"
    data = [1, -2, 3, -4]
    result = process_data(data)
    assert result == [2, 6]


def test_format_output():
    \"\"\"Test format_output function.\"\"\"
    results = [1, 2, 3]
    output = format_output(results)
    assert output == "1, 2, 3"
""")

        # Create helper module
        (repo / "helper.py").write_text("""
def validate_input(data):
    \"\"\"Validate input data.\"\"\"
    return isinstance(data, list)
""")

        return repo

    def test_python_type1_bundle_includes_arch_header_with_dependencies(
        self, temp_repo: Path, tmp_path: Path
    ) -> None:
        """Test that Python TYPE 1 bundle includes [ARCH_HEADER] with dependencies.

        This test verifies AC-1.3: [ARCH_HEADER] includes:
        - LOCAL_IMPORTS: relative imports
        - DEPENDENCIES: external imports
        """
        # Create minimal config
        config_data = {
            "raw_subdir": "raw",
            "output_subdir": "output",
            "category": "test",
            "profile": "homeassistant",
            "on_parse_error": "fallback",
        }

        cfg = ProcessingConfig(**config_data, base_dir=tmp_path)

        # Create the raw directory structure
        raw_dir = tmp_path / "raw" / "test"
        raw_dir.mkdir(parents=True)
        owner_dir = raw_dir / "test_owner"
        owner_dir.mkdir()
        repo_copy = owner_dir / "test_repo"
        repo_copy.mkdir()

        # Copy test files
        (repo_copy / "my_module.py").write_text("""
import os
import sys
from . import helper

def process_data(data):
    pass
""")
        (repo_copy / "__init__.py").write_text("")
        (repo_copy / "test_my_module.py").write_text("""
from my_module import process_data

def test_process_data():
    result = process_data([1, 2])
    assert result is not None
""")
        (repo_copy / "helper.py").write_text("def helper_func(): pass")

        # Create output directory
        output_dir = tmp_path / "output" / "test" / "test_owner" / "test_repo"
        output_dir.mkdir(parents=True)

        # Process
        processor = RepoProcessor(cfg)
        processor._process_repository("test", repo_copy)

        # Verify TYPE 1 bundle was created
        func_unit_dir = output_dir / "test_owner_test_repo_my_module"
        assert func_unit_dir.exists(), "TYPE 1 FUNCTIONAL_UNIT directory not created"

        # Find the bundle file
        bundle_files = list(func_unit_dir.glob("*.txt"))
        assert len(bundle_files) == 1, f"Expected 1 bundle file, found {len(bundle_files)}"

        bundle_path = bundle_files[0]
        bundle_content = bundle_path.read_text(encoding="utf-8")

        # Verify [ARCH_HEADER] exists
        assert "[ARCH_HEADER]" in bundle_content, "Bundle missing [ARCH_HEADER]"

        # Verify LOCAL_IMPORTS is present
        assert "LOCAL_IMPORTS:" in bundle_content, "Bundle missing LOCAL_IMPORTS"
        assert "helper.py" in bundle_content, "Bundle missing relative import in header"

        # Verify DEPENDENCIES is present
        assert "DEPENDENCIES:" in bundle_content, "Bundle missing DEPENDENCIES"
        assert "os" in bundle_content, "Bundle missing os dependency in header"
        assert "sys" in bundle_content, "Bundle missing sys dependency in header"

        # Verify test file is included in bundle
        assert "test_my_module.py" in bundle_content, "Test file not included in TYPE 1 bundle"

        # Verify bundle type
        assert "FUNCTIONAL_UNIT" in bundle_content, "Bundle type not FUNCTIONAL_UNIT"

    def test_python_type1_bypasses_size_gate_for_tested_code(
        self, temp_repo: Path, tmp_path: Path
    ) -> None:
        """Test that TYPE 1 bundle is emitted even when file is below MIN_SIZE.

        This test verifies AC-1.2: Logic files under MIN_SIZE are still emitted
        when a test file exists (teaching tests is valuable).
        """
        # Create minimal config
        config_data = {
            "raw_subdir": "raw",
            "output_subdir": "output",
            "category": "test",
            "profile": "homeassistant",
            "on_parse_error": "fallback",
        }

        cfg = ProcessingConfig(**config_data, base_dir=tmp_path)

        # Create the raw directory structure
        raw_dir = tmp_path / "raw" / "test"
        raw_dir.mkdir(parents=True)
        owner_dir = raw_dir / "test_owner"
        owner_dir.mkdir()
        repo_copy = owner_dir / "test_repo"
        repo_copy.mkdir()

        # Create a VERY small logic file (under MIN_SIZE of 200 chars)
        (repo_copy / "small_module.py").write_text("""
def small_func():
    pass
""")
        (repo_copy / "__init__.py").write_text("")

        # Create test file - this should cause the small file to be emitted
        (repo_copy / "test_small_module.py").write_text("""
from small_module import small_func

def test_small():
    small_func()
""")

        # Create output directory
        output_dir = tmp_path / "output" / "test" / "test_owner" / "test_repo"
        output_dir.mkdir(parents=True)

        # Process
        processor = RepoProcessor(cfg)
        processor._process_repository("test", repo_copy)

        # Verify TYPE 1 bundle was created despite small size
        func_unit_dir = output_dir / "test_owner_test_repo_small_module"
        assert func_unit_dir.exists(), (
            "TYPE 1 FUNCTIONAL_UNIT not created for file under MIN_SIZE with test"
        )

        # Verify stats show type1 was emitted
        assert processor._stats["TYPE1_FUNCTIONAL_UNIT"] >= 1


class TestType1FunctionalUnitTypeScript:
    """TYPE 1 FUNCTIONAL_UNIT tests for TypeScript repositories."""

    @pytest.fixture
    def temp_ts_repo(self, tmp_path: Path) -> Path:
        """Create a temporary TypeScript repository with logic and test files."""
        repo = tmp_path / "ts_owner" / "ts_repo"
        repo.mkdir(parents=True)

        # Create a TypeScript logic file
        (repo / "buttonComponent.ts").write_text("""
import { customElement } from \'lit/decorators.js\';

@customElement(\'button-card\')
export class ButtonCard {
    private title: string;

    render() {
        return `<button>\${this.title}</button>`;
    }

    setConfig(config: { title: string }) {
        this.title = config.title;
    }
}
""")

        # Create test file in tests/ directory
        ts_tests_dir = repo / "tests"
        ts_tests_dir.mkdir()
        (ts_tests_dir / "test_buttonComponent.ts").write_text("""
import { ButtonCard } from \'./buttonComponent.js\';

describe(\'ButtonCard\', () => {
    it(\'should render button\', () => {
        const card = new ButtonCard();
        card.setConfig({ title: \'Test\' });
        const output = card.render();
        expect(output).toContain(\'button\');
    });
});
""")

        return repo

    def test_typescript_type1_bundle_includes_arch_header_with_dependencies(
        self, temp_ts_repo: Path, tmp_path: Path
    ) -> None:
        """Test that TypeScript TYPE 1 bundle includes [ARCH_HEADER] with dependencies.

        This test verifies AC-1.3: TypeScript bundles also include [ARCH_HEADER]
        with LOCAL_IMPORTS and DEPENDENCIES extracted by TypeScriptAdapter.
        """
        # Create minimal config
        config_data = {
            "raw_subdir": "raw",
            "output_subdir": "output",
            "category": "test",
            "profile": "typescript",
            "on_parse_error": "fallback",
        }

        cfg = ProcessingConfig(**config_data, base_dir=tmp_path)

        # Create the raw directory structure
        raw_dir = tmp_path / "raw" / "test"
        raw_dir.mkdir(parents=True)
        owner_dir = raw_dir / "ts_owner"
        owner_dir.mkdir()
        repo_copy = owner_dir / "ts_repo"
        repo_copy.mkdir()

        # Copy TypeScript files
        (repo_copy / "buttonComponent.ts").write_text("""
import { customElement } from \'lit/decorators.js\';

@customElement(\'button-card\')
export class ButtonCard {
    render() {
        return `<button>Hello</button>`;
    }
}
""")
        # Test file must be in tests/ directory for find_test to discover it
        ts_tests_dir = repo_copy / "tests"
        ts_tests_dir.mkdir()
        (ts_tests_dir / "test_buttonComponent.ts").write_text("""
import { ButtonCard } from \'./buttonComponent.js\';

describe(\'ButtonCard\', () => {
    it(\'should render\', () => {
        const card = new ButtonCard();
        const output = card.render();
        expect(output).toContain(\'button\');
    });
});
""")

        # Create output directory
        output_dir = tmp_path / "output" / "test" / "ts_owner" / "ts_repo"
        output_dir.mkdir(parents=True)

        # Process
        processor = RepoProcessor(cfg)
        processor._process_repository("test", repo_copy)

        # Verify TYPE 1 bundle was created
        func_unit_dir = output_dir / "ts_owner_ts_repo_buttonComponent"
        assert func_unit_dir.exists(), "TYPE 1 FUNCTIONAL_UNIT directory not created for TypeScript"

        # Find the bundle file
        bundle_files = list(func_unit_dir.glob("*.txt"))
        assert len(bundle_files) == 1, f"Expected 1 bundle file, found {len(bundle_files)}"

        bundle_path = bundle_files[0]
        bundle_content = bundle_path.read_text(encoding="utf-8")

        # Verify [ARCH_HEADER] exists
        assert "[ARCH_HEADER]" in bundle_content, "TypeScript bundle missing [ARCH_HEADER]"

        # Verify DEPENDENCIES is present (lit/decorators.js import)
        assert "DEPENDENCIES:" in bundle_content, "TypeScript bundle missing DEPENDENCIES"
        assert "lit" in bundle_content or "decorators" in bundle_content, (
            "TypeScript bundle missing lit dependency in header"
        )

        # Verify test file is included
        assert "test_buttonComponent.ts" in bundle_content, "TypeScript test file not included"

        # Verify bundle type
        assert "FUNCTIONAL_UNIT" in bundle_content, "TypeScript bundle type not FUNCTIONAL_UNIT"


class TestTypes1To5:
    """Unified test for all fragment types (1, 3, 4, 5)."""

    def test_types_1_to_5(self, tmp_path: Path) -> None:
        """Verify all fragment types (1, 3, 4, 5) are generated correctly.

        This test creates a repo with:
        - Logic file with test → TYPE 1 (FUNCTIONAL_UNIT)
        - Large logic file without test → TYPE 3 (LOGIC_ONLY)
        - Module with anchor files → TYPE 4 (MODULE_BLUEPRINT)
        - Root governance files → TYPE 5 (GOVERNANCE_RULES)
        """
        # Create minimal config
        config_data = {
            "raw_subdir": "raw",
            "output_subdir": "output",
            "category": "test",
            "profile": "homeassistant",
            "on_parse_error": "fallback",
        }

        cfg = ProcessingConfig(**config_data, base_dir=tmp_path)

        # Create the raw directory structure (matching processor_adapter_integration pattern)
        raw_dir = tmp_path / "raw" / "test"
        raw_dir.mkdir(parents=True)
        owner_dir = raw_dir / "mixed_repo"
        owner_dir.mkdir()
        repo_copy = owner_dir / "test_repo"
        repo_copy.mkdir()

        # TYPE 1: Logic file with test (must be >= MIN_SIZE 300 bytes)
        # Pattern: logic file + test file in tests/ directory
        (repo_copy / "my_module.py").write_text(
            """import os
import sys


def process_data(data):
    \"\"\"Process incoming data.

    This function takes data as an argument and returns processed results.
    It is used as a simple test case for testing the function output.
    \"\"\"
    result = []
    for item in data:
        if item > 0:
            result.append(item * 2)
    return result


def format_output(results):
    \"\"\"Format results for display.

    This function takes a list of results and formats them as a string.
    It is used for testing string formatting logic.
    \"\"\"
    return ", ".join(str(r) for r in results)
"""
        )
        # Test file must be in tests/ directory for find_test to find it
        # Test file must be >= MIN_SIZE (300 bytes) to be considered
        tests_dir = repo_copy / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_my_module.py").write_text("""
import sys
sys.path.insert(0, '')

from my_module import process_data, format_output


def test_process_data():
    \"\"\"Test process_data function with sample data.

    This test verifies that process_data correctly processes positive values.
    The assertion checks that the result matches expected output.
    \"\"\"
    data = [1, -2, 3, -4, 5]
    result = process_data(data)
    assert result == [2, 6, 10], f"Expected [2, 6, 10], got {result}"


def test_format_output():
    \"\"\"Test format_output function with sample results.

    This test verifies that format_output correctly formats results as a string.
    The assertion checks that the output matches expected format.
    \"\"\"
    results = [1, 2, 3]
    output = format_output(results)
    assert output == "1, 2, 3", f"Expected '1, 2, 3', got '{output}'"
""")

        # TYPE 3: Large logic file without test (> 1000 chars for LOGIC_ONLY)
        # Must include GOLD_PATTERN to pass the gold pattern filter for .py files
        # GOLD_PATTERNS = ["ConfigFlow", "DataUpdateCoordinator", "async_add_entities", ...]
        large_lines = []
        for i in range(60):
            large_lines.extend([
                f"# Line {i} of the large function file",
                f"# This line ensures the file exceeds the LOGIC_ONLY_MIN_CHARS threshold of 800 chars",
                f"class TestComponent_{i}:",
                f'    """A large class with many methods for testing purposes and documentation."""',
                f"    async def async_process_{i}(self, x, y, z):",
                f"        # This function does some processing with multiple parameters",
                f"        async_add_entities",  # GOLD_PATTERN - triggers content check
                f"        result = x + y + z + {i}",
                f"        # Return the calculated result",
                f"        return result",
                "",
                "",
            ])
        large_content = "\n".join(large_lines)
        assert len(large_content) > 1000, f"Large content should be > 1000 chars, got {len(large_content)}"
        large_file = repo_copy / "huge_processor.py"
        large_file.write_text(large_content)
        assert large_file.stat().st_size >= 1000, f"File size {large_file.stat().st_size} too small"
        # Verify file contains a GOLD_PATTERN
        gold_patterns = ["async_add_entities", "async_setup_entry", "async_setup_platform"]
        assert any(p in large_content for p in gold_patterns), "Large file must contain a GOLD_PATTERN"

        # TYPE 4: Module anchor files (init.py makes it a module)
        (repo_copy / "__init__.py").write_text(
            '"""Package init."""\n__version__ = "1.0.0"\n'
        )

        # TYPE 5: Root governance files (using recognized filenames)
        (repo_copy / "AGENTS.md").write_text("""# AGENTS.md

This repository follows specific agent guidelines.
""")
        (repo_copy / ".cursorrules").write_text("""# Cursor Rules

Development guidelines for this project.
""")

        # Process - "mixed_repo" is the repository name, repo_copy is the path
        processor = RepoProcessor(cfg)

        # Debug: Check files before processing
        import logging
        logging.getLogger().setLevel(logging.WARNING)  # Reduce noise
        processor._process_repository("mixed_repo", repo_copy)

        # Verify all fragment types were generated
        stats = processor._stats
        print(f"Stats: {stats}")

        # Check what files were processed
        print(f"Files in repo_copy:")
        for f in sorted(repo_copy.rglob("*.py")):
            print(f"  {f.relative_to(repo_copy)}: {f.stat().st_size} bytes")

        # TYPE 1: At least one FUNCTIONAL_UNIT
        assert stats["TYPE1_FUNCTIONAL_UNIT"] >= 1, (
            f"TYPE 1 not generated, stats: {stats}"
        )

        # TYPE 3: At least one LOGIC_ONLY (large file without test)
        assert stats["TYPE3_LOGIC_ONLY"] >= 1, (
            f"TYPE 3 not generated, stats: {stats}"
        )

        # TYPE 4: At least one MODULE_BLUEPRINT
        assert stats["TYPE4_MODULE_BLUEPRINT"] >= 1, (
            f"TYPE 4 not generated, stats: {stats}"
        )

        # TYPE 5: At least one GOVERNANCE_RULES
        assert stats["TYPE5_GOVERNANCE_RULES"] >= 1, (
            f"TYPE 5 not generated, stats: {stats}"
        )

        # Verify bundle directories exist
        # Bundles are created under target_root/{repo_name}/ for module-based bundles
        # and under target_root/_governance/ for governance rules
        repo_name = "test_repo"  # This is the directory name under mixed_repo
        repo_output_dir = processor.target_root / repo_name

        # TYPE 1
        type1_dir = repo_output_dir / "mixed_repo_test_repo_my_module"
        assert type1_dir.exists(), "TYPE 1 directory not created"

        # TYPE 3
        type3_dir = repo_output_dir / "mixed_repo_test_repo_huge_processor"
        assert type3_dir.exists(), "TYPE 3 directory not created"

        # TYPE 4
        type4_dir = repo_output_dir / "mixed_repo_test_repo_blueprint"
        assert type4_dir.exists(), "TYPE 4 directory not created"

        # TYPE 5 (governance is created at target_root/_governance/)
        type5_dir = processor.target_root / "_governance" / "mixed_repo_test_repo_governance"
        assert type5_dir.exists(), "TYPE 5 directory not created"

        # Verify bundle contents
        type1_bundle = list(type1_dir.glob("*.txt"))[0].read_text(encoding="utf-8")
        assert "FUNCTIONAL_UNIT" in type1_bundle
        assert "[ARCH_HEADER]" in type1_bundle

        type3_bundle = list(type3_dir.glob("*.txt"))[0].read_text(encoding="utf-8")
        assert "LOGIC_ONLY" in type3_bundle
        assert "[ARCH_HEADER]" in type3_bundle

        type4_bundle = list(type4_dir.glob("*.txt"))[0].read_text(encoding="utf-8")
        assert "MODULE_BLUEPRINT" in type4_bundle
        assert "[MODULE_MAP]" in type4_bundle

        type5_bundle = list(type5_dir.glob("*.txt"))[0].read_text(encoding="utf-8")
        assert "GOVERNANCE_RULES" in type5_bundle
        assert "[GOVERNANCE_HEADER]" in type5_bundle


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
