# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Integration tests for processor using the extractor adapter.

These tests verify that the processor correctly uses the adapter for
dependency extraction and handles parse errors according to the configured policy.
"""

from __future__ import annotations

from pathlib import Path
import pytest

from src.discovery import ProcessingConfig, RepoProcessor


class TestProcessorAdapterIntegration:
    """Integration tests for processor with adapter."""

    @pytest.fixture
    def temp_repo(self, tmp_path: Path) -> Path:
        """Create a temporary repository structure for testing."""
        repo = tmp_path / "test_owner" / "test_repo"
        repo.mkdir(parents=True)

        # Create a simple Python file with imports
        (repo / "test_module.py").write_text("""
from . import local_module
import os
import sys

def hello():
    pass
""")

        # Create an __init__.py to make it a module
        (repo / "__init__.py").write_text("")

        return repo

    def test_processor_uses_adapter_for_dependencies(
        self, temp_repo: Path, tmp_path: Path
    ) -> None:
        """Test that processor uses adapter to extract dependencies."""
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

        # Copy test file
        (repo_copy / "test_module.py").write_text("""
from . import local_module
import os
import sys

def hello():
    pass
""")
        (repo_copy / "__init__.py").write_text("")

        # Process
        processor = RepoProcessor(cfg)

        # Check adapter is initialized
        assert processor._adapter is not None

        # Verify adapter can extract dependencies
        deps = processor._adapter.extract_dependencies(repo_copy / "test_module.py")
        dep_names = [d.name for d in deps]

        # Should find local_module (relative), os (stdlib), sys (stdlib)
        assert "local_module" in dep_names or any("local" in n for n in dep_names)
        assert "os" in dep_names
        assert "sys" in dep_names

    def test_processor_handles_parse_error_abort(self, tmp_path: Path) -> None:
        """Test that processor aborts on parse error when policy is abort."""
        config_data = {
            "raw_subdir": "raw",
            "output_subdir": "output",
            "category": "test",
            "profile": "homeassistant",
            "on_parse_error": "abort",
        }

        cfg = ProcessingConfig(**config_data, base_dir=tmp_path)

        # Create the raw directory structure
        raw_dir = tmp_path / "raw" / "test"
        raw_dir.mkdir(parents=True)
        owner_dir = raw_dir / "test_owner"
        owner_dir.mkdir()
        repo_copy = owner_dir / "test_repo"
        repo_copy.mkdir()

        # Create a file with syntax error
        (repo_copy / "bad_syntax.py").write_text("""
def broken(
    # Missing closing paren and invalid syntax
    pass
""")

        # Create module directory
        (repo_copy / "__init__.py").write_text("")

        # Process
        processor = RepoProcessor(cfg)

        # Verify parse error stats
        assert processor._on_parse_error == "abort"
        assert "parse_errors" in processor._stats
        assert "parse_errors_aborted" in processor._stats

    def test_processor_on_parse_error_skip(self, tmp_path: Path) -> None:
        """Test that processor skips files on parse error when policy is skip."""
        config_data = {
            "raw_subdir": "raw",
            "output_subdir": "output",
            "category": "test",
            "profile": "homeassistant",
            "on_parse_error": "skip",
        }

        cfg = ProcessingConfig(**config_data, base_dir=tmp_path)
        processor = RepoProcessor(cfg)

        assert processor._on_parse_error == "skip"

    def test_processor_on_parse_error_fallback(self, tmp_path: Path) -> None:
        """Test that processor falls back on parse error when policy is fallback."""
        config_data = {
            "raw_subdir": "raw",
            "output_subdir": "output",
            "category": "test",
            "profile": "homeassistant",
            "on_parse_error": "fallback",
        }

        cfg = ProcessingConfig(**config_data, base_dir=tmp_path)
        processor = RepoProcessor(cfg)

        assert processor._on_parse_error == "fallback"

    def test_processor_abort_policy_aborts_repo_on_parse_error(
        self, tmp_path: Path
    ) -> None:
        """Test that abort policy aborts repository when parse error occurs.

        The RepoAbortError is caught internally and the repository is marked
        as aborted in the stats.
        """
        config_data = {
            "raw_subdir": "raw",
            "output_subdir": "output",
            "category": "test",
            "profile": "homeassistant",
            "on_parse_error": "abort",
        }

        cfg = ProcessingConfig(**config_data, base_dir=tmp_path)

        # Create the raw directory structure
        raw_dir = tmp_path / "raw" / "test"
        raw_dir.mkdir(parents=True)
        owner_dir = raw_dir / "test_owner"
        owner_dir.mkdir()
        repo_copy = owner_dir / "test_repo"
        repo_copy.mkdir()

        # Create a Python file with syntax error
        (repo_copy / "bad_syntax.py").write_text("""
def broken(
    # Missing closing paren and invalid syntax
    pass
""")

        # Create another valid file that should NOT be processed due to abort
        (repo_copy / "valid.py").write_text("import os\nprint('hello')")
        (repo_copy / "__init__.py").write_text("")

        # Process - the RepoAbortError is caught internally
        processor = RepoProcessor(cfg)
        processor._process_repository("test_owner", repo_copy)

        # Verify parse error was recorded and repo was aborted
        assert processor._stats["parse_errors"] == 1
        assert processor._stats["parse_errors_aborted"] == 1
        # The repo should be in needs_manual_review with reason parse_error_abort
        review_entry = processor._stats["needs_manual_review"][0]
        assert review_entry["repo"] == "test_repo"
        assert "bad_syntax.py" in review_entry["file"]
        assert review_entry["reason"] == "parse_error_abort"

    def test_processor_skip_policy_continues_on_parse_error(
        self, tmp_path: Path
    ) -> None:
        """Test that skip policy skips the file but continues processing."""
        config_data = {
            "raw_subdir": "raw",
            "output_subdir": "output",
            "category": "test",
            "profile": "homeassistant",
            "on_parse_error": "skip",
        }

        cfg = ProcessingConfig(**config_data, base_dir=tmp_path)

        # Create the raw directory structure
        raw_dir = tmp_path / "raw" / "test"
        raw_dir.mkdir(parents=True)
        owner_dir = raw_dir / "test_owner"
        owner_dir.mkdir()
        repo_copy = owner_dir / "test_repo"
        repo_copy.mkdir()

        # Create a Python file with syntax error
        (repo_copy / "bad_syntax.py").write_text("""
def broken(
    # Missing closing paren and invalid syntax
    pass
""")

        # Create another valid file that should still be processed
        (repo_copy / "valid.py").write_text("import os\nprint('hello')")
        (repo_copy / "__init__.py").write_text("")

        # Create output directory
        output_dir = tmp_path / "output" / "test" / "test_owner" / "test_repo"
        output_dir.mkdir(parents=True)

        # Process - should NOT raise, should skip bad file and process valid file
        processor = RepoProcessor(cfg)
        processor._process_repository("test_owner", repo_copy)

        # Verify parse error was recorded
        assert processor._stats["parse_errors"] == 1

    def test_processor_mark_and_continue_policy(self, tmp_path: Path) -> None:
        """Test that mark_and_continue policy marks file but continues processing."""
        config_data = {
            "raw_subdir": "raw",
            "output_subdir": "output",
            "category": "test",
            "profile": "homeassistant",
            "on_parse_error": "mark_and_continue",
        }

        cfg = ProcessingConfig(**config_data, base_dir=tmp_path)

        # Create the raw directory structure
        raw_dir = tmp_path / "raw" / "test"
        raw_dir.mkdir(parents=True)
        owner_dir = raw_dir / "test_owner"
        owner_dir.mkdir()
        repo_copy = owner_dir / "test_repo"
        repo_copy.mkdir()

        # Create a Python file with syntax error
        (repo_copy / "bad_syntax.py").write_text("""
def broken(
    # Missing closing paren and invalid syntax
    pass
""")

        # Create another valid file that should still be processed
        (repo_copy / "valid.py").write_text("import os\nprint('hello')")
        (repo_copy / "__init__.py").write_text("")

        # Create output directory
        output_dir = tmp_path / "output" / "test" / "test_owner" / "test_repo"
        output_dir.mkdir(parents=True)

        # Process - should NOT raise, should mark bad file for review
        processor = RepoProcessor(cfg)
        processor._process_repository("test_owner", repo_copy)

        # Verify parse error was recorded
        assert processor._stats["parse_errors"] == 1

        # Verify file was marked for manual review
        assert len(processor._stats["needs_manual_review"]) == 1
        review_entry = processor._stats["needs_manual_review"][0]
        assert "bad_syntax.py" in review_entry["file"]
        assert review_entry["reason"] == "parse_error_marked"

    def test_processor_profile_configuration(self, tmp_path: Path) -> None:
        """Test that processor accepts and uses profile configuration."""
        config_data = {
            "raw_subdir": "raw",
            "output_subdir": "output",
            "category": "test",
            "profile": "python",
            "on_parse_error": "abort",
        }

        cfg = ProcessingConfig(**config_data, base_dir=tmp_path)

        # Create the raw directory structure
        raw_dir = tmp_path / "raw" / "test"
        raw_dir.mkdir(parents=True)
        owner_dir = raw_dir / "test_owner"
        owner_dir.mkdir()
        repo_copy = owner_dir / "test_repo"
        repo_copy.mkdir()

        # Create test file
        (repo_copy / "test.py").write_text("import os")
        (repo_copy / "__init__.py").write_text("")

        processor = RepoProcessor(cfg)

        # Verify profile is set correctly
        assert cfg.profile == "python"
        assert processor._adapter is not None


class TestProcessorArchHeaderWithDependencies:
    """Tests for ARCH_HEADER including dependencies."""

    def test_arch_header_includes_dependencies(self) -> None:
        """Test that _make_arch_header includes dependencies."""
        from src.discovery import (
            Module,
            ModuleFile,
            RepoProcessor,
            ProcessingConfig,
        )
        from pathlib import Path

        config_data = {
            "raw_subdir": "raw",
            "output_subdir": "output",
            "category": "test",
            "profile": "homeassistant",
        }

        cfg = ProcessingConfig(**config_data)
        processor = RepoProcessor(cfg)

        mod = Module(
            name="test_module",
            path=Path("/fake/path"),
        )
        mf = ModuleFile(
            path=Path("/fake/path/test.py"),
            role="implementation",
        )

        header = processor._make_arch_header(
            mod,
            mf,
            local_imports=["helper.py"],
            ftype="LOGIC_ONLY",
            repo_prefix="owner_repo",
            dependencies=["os", "sys", "requests"],
        )

        assert "[ARCH_HEADER]" in header
        assert "LOCAL_IMPORTS: ['helper.py']" in header
        assert "DEPENDENCIES: ['os', 'sys', 'requests']" in header
        assert "NEIGHBORS: ()" in header
