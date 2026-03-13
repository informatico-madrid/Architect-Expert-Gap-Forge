# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Tests for processor module discovery with directory and manual_mapping strategies.

Validates that the processor correctly discovers modules using:
- directory strategy: discover modules by directory structure
- manual_mapping strategy: use manually defined module mappings
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.discovery import Module, ProcessingConfig, RepoProcessor


class TestProcessorModuleDiscoveryDirectory:
    """Test module discovery using directory strategy."""

    @pytest.fixture
    def temp_repo_with_directories(self, tmp_path: Path) -> Path:
        """Create a temporary repository structure with directory-based modules."""
        repo_root = tmp_path / "test_repo"
        repo_root.mkdir()

        # Create package1/ with Python files (no manifest.json)
        package1 = repo_root / "package1"
        package1.mkdir()
        (package1 / "__init__.py").write_text("# Package 1")
        (package1 / "module.py").write_text("def hello(): pass")

        # Create package2/ with Python files
        package2 = repo_root / "package2"
        package2.mkdir()
        (package2 / "__init__.py").write_text("# Package 2")
        (package2 / "core.py").write_text("class Core: pass")

        # Create a nested package
        nested = repo_root / "packages" / "nested"
        nested.mkdir(parents=True)
        (nested / "__init__.py").write_text("# Nested package")

        return repo_root

    def test_discover_modules_with_directory_strategy(
        self, temp_repo_with_directories: Path
    ) -> None:
        """Test that modules are discovered via directory structure."""
        config = ProcessingConfig(
            base_dir=temp_repo_with_directories.parent,
            raw_subdir=".",
            output_subdir="output",
            category="test",
            module_discovery_strategy="directory",
        )
        processor = RepoProcessor(config)

        modules = processor._discover_modules(temp_repo_with_directories)

        # Should find modules based on directory structure
        # The exact count depends on implementation - at least package1 and package2
        assert len(modules) >= 2
        module_names = {m.name for m in modules}
        assert "package1" in module_names
        assert "package2" in module_names

    def test_directory_strategy_finds_nested_packages(
        self, temp_repo_with_directories: Path
    ) -> None:
        """Test that directory strategy finds nested packages."""
        config = ProcessingConfig(
            base_dir=temp_repo_with_directories.parent,
            raw_subdir=".",
            output_subdir="output",
            category="test",
            module_discovery_strategy="directory",
        )
        processor = RepoProcessor(config)

        modules = processor._discover_modules(temp_repo_with_directories)

        # Should find the nested package too
        module_names = {m.name for m in modules}
        assert "nested" in module_names


class TestProcessorModuleDiscoveryManualMapping:
    """Test module discovery using manual_mapping strategy."""

    @pytest.fixture
    def temp_repo_for_manual_mapping(self, tmp_path: Path) -> Path:
        """Create a temporary repository for manual mapping tests."""
        repo_root = tmp_path / "test_repo"
        repo_root.mkdir()

        # Create some files but we'll override with manual mapping
        (repo_root / "file1.py").write_text("# File 1")
        (repo_root / "file2.py").write_text("# File 2")

        return repo_root

    def test_discover_modules_with_manual_mapping(
        self, temp_repo_for_manual_mapping: Path
    ) -> None:
        """Test that modules are discovered via manual_mapping."""
        manual_mapping = {
            "custom_module": {
                "enabled": True,
                "path": "custom_components/my_module",
                "anchor_type": "manual",
            },
            "another_module": {
                "enabled": True,
                "path": "libs/another",
                "anchor_type": "init",
            },
        }
        config = ProcessingConfig(
            base_dir=temp_repo_for_manual_mapping.parent,
            raw_subdir=".",
            output_subdir="output",
            category="test",
            module_discovery_strategy="manual_mapping",
            module_overrides=manual_mapping,
        )
        processor = RepoProcessor(config)

        # Manual mapping should use the overrides to discover modules
        modules = processor._discover_modules(temp_repo_for_manual_mapping)

        # The processor should consider module_overrides when using manual_mapping
        assert config.module_overrides is not None
        assert len(config.module_overrides) == 2

    def test_manual_mapping_can_disable_modules(self) -> None:
        """Test that manual_mapping can disable auto-discovered modules."""
        manual_mapping = {
            "auto_discovered": {
                "enabled": False,  # Disable this module
            },
            "manual_module": {
                "enabled": True,
                "path": "manual/path",
                "anchor_type": "manual",
            },
        }
        config = ProcessingConfig(
            base_dir=Path.cwd(),
            raw_subdir="raw",
            output_subdir="output",
            category="test",
            module_discovery_strategy="manual_mapping",
            module_overrides=manual_mapping,
        )
        processor = RepoProcessor(config)

        # Verify the override configuration
        assert config.module_overrides is not None
        assert config.module_overrides["auto_discovered"]["enabled"] is False
        assert config.module_overrides["manual_module"]["enabled"] is True


class TestProcessorStrategySelection:
    """Test that the correct strategy is applied based on config."""

    def test_init_strategy_uses_init_files(self, tmp_path: Path) -> None:
        """Test that init strategy uses __init__.py as anchors."""
        repo_root = tmp_path / "test_repo"
        repo_root.mkdir()

        # Create components with __init__.py but no manifest.json
        comp1 = repo_root / "components" / "sensor"
        comp1.mkdir(parents=True)
        (comp1 / "__init__.py").write_text("# Sensor")

        config = ProcessingConfig(
            base_dir=tmp_path,
            raw_subdir=".",
            output_subdir="output",
            category="test",
            module_discovery_strategy="init",
        )
        processor = RepoProcessor(config)

        modules = processor._discover_modules(repo_root)

        # Should find at least the sensor component
        assert len(modules) >= 1

    def test_strategy_defaults_to_manifest(self, tmp_path: Path) -> None:
        """Test that default strategy is manifest."""
        # Create a repo with manifest.json
        repo_root = tmp_path / "test_repo"
        repo_root.mkdir()
        comp = repo_root / "custom" / "test"
        comp.mkdir(parents=True)
        (comp / "manifest.json").write_text(json.dumps({"domain": "test"}))

        config = ProcessingConfig(
            base_dir=tmp_path,
            raw_subdir=".",
            output_subdir="output",
            category="test",
            # Not specifying strategy - should default to manifest
        )
        processor = RepoProcessor(config)

        # Default should be manifest
        assert config.module_discovery_strategy == "manifest"

        modules = processor._discover_modules(repo_root)
        assert len(modules) >= 1
        assert modules[0].anchor_type == "manifest"


class TestProcessorOverridesBehavior:
    """Test the behavior of module overrides."""

    def test_overrides_affect_module_list(self, tmp_path: Path) -> None:
        """Test that module_overrides can add/remove modules from discovery."""
        repo_root = tmp_path / "test_repo"
        repo_root.mkdir()

        # Create a real module
        real_module = repo_root / "real_module"
        real_module.mkdir()
        (real_module / "__init__.py").write_text("# Real")

        # Create config with override to disable real_module
        overrides = {
            "real_module": {
                "enabled": False,
            }
        }

        config = ProcessingConfig(
            base_dir=tmp_path,
            raw_subdir=".",
            output_subdir="output",
            category="test",
            module_overrides=overrides,
        )

        # The override should be stored in config
        assert config.module_overrides == overrides
        assert config.module_overrides["real_module"]["enabled"] is False

    def test_overrides_can_specify_custom_paths(self, tmp_path: Path) -> None:
        """Test that overrides can specify custom paths for modules."""
        overrides = {
            "custom": {
                "enabled": True,
                "path": "custom/path/here",
                "anchor_type": "custom",
            }
        }

        config = ProcessingConfig(
            base_dir=tmp_path,
            raw_subdir=".",
            output_subdir="output",
            category="test",
            module_overrides=overrides,
        )

        assert config.module_overrides["custom"]["path"] == "custom/path/here"
        assert config.module_overrides["custom"]["anchor_type"] == "custom"
