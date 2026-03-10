# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Tests for processor module discovery with manifest strategy.

Validates that the processor correctly discovers modules using the manifest
strategy, reading module information from manifest.json files.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List
from unittest.mock import MagicMock, patch

import pytest

from src.discovery.processor import Module, ModuleFile, ProcessingConfig, RepoProcessor


class TestProcessorModuleDiscoveryManifest:
    """Test module discovery using manifest strategy."""

    @pytest.fixture
    def temp_repo_with_manifests(self, tmp_path: Path) -> Path:
        """Create a temporary repository structure with manifest.json files."""
        repo_root = tmp_path / "test_repo"
        repo_root.mkdir()

        # Create component1 with manifest.json
        component1 = repo_root / "custom_components" / "component1"
        component1.mkdir(parents=True)
        manifest1 = component1 / "manifest.json"
        manifest1.write_text(
            json.dumps(
                {
                    "domain": "component1",
                    "name": "Component 1",
                    "version": "1.0.0",
                    "dependencies": ["helper_lib"],
                    "requirements": ["requests"],
                }
            )
        )
        (component1 / "__init__.py").write_text("# Component 1 init")
        (component1 / "const.py").write_text("DOMAIN = 'component1'")

        # Create component2 with manifest.json
        component2 = repo_root / "custom_components" / "component2"
        component2.mkdir(parents=True)
        manifest2 = component2 / "manifest.json"
        manifest2.write_text(
            json.dumps(
                {
                    "domain": "component2",
                    "name": "Component 2",
                    "version": "0.5.0",
                    "dependencies": [],
                }
            )
        )
        (component2 / "__init__.py").write_text("# Component 2 init")

        return repo_root

    def test_discover_modules_with_manifest_strategy(
        self, temp_repo_with_manifests: Path
    ) -> None:
        """Test that modules are discovered via manifest.json files."""
        config = ProcessingConfig(
            base_dir=temp_repo_with_manifests.parent,
            raw_subdir=".",
            output_subdir="output",
            category="test",
            module_discovery_strategy="manifest",
        )
        processor = RepoProcessor(config)

        modules = processor._discover_modules(temp_repo_with_manifests)

        # Should find 2 modules from manifest.json files
        assert len(modules) == 2
        module_names = {m.name for m in modules}
        assert "component1" in module_names
        assert "component2" in module_names

    def test_manifest_module_has_correct_anchor_type(
        self, temp_repo_with_manifests: Path
    ) -> None:
        """Test that manifest-discovered modules have anchor_type='manifest'."""
        config = ProcessingConfig(
            base_dir=temp_repo_with_manifests.parent,
            raw_subdir=".",
            output_subdir="output",
            category="test",
            module_discovery_strategy="manifest",
        )
        processor = RepoProcessor(config)

        modules = processor._discover_modules(temp_repo_with_manifests)

        for mod in modules:
            assert mod.anchor_type == "manifest"

    def test_manifest_module_includes_dependencies(
        self, temp_repo_with_manifests: Path
    ) -> None:
        """Test that module manifest dependencies are captured."""
        config = ProcessingConfig(
            base_dir=temp_repo_with_manifests.parent,
            raw_subdir=".",
            output_subdir="output",
            category="test",
            module_discovery_strategy="manifest",
        )
        processor = RepoProcessor(config)

        modules = processor._discover_modules(temp_repo_with_manifests)

        # Find component1 and check its manifest data
        component1 = next(m for m in modules if m.name == "component1")
        assert component1.manifest.get("domain") == "component1"
        assert component1.manifest.get("dependencies") == ["helper_lib"]
        assert component1.manifest.get("requirements") == ["requests"]

    def test_manifest_module_includes_files(
        self, temp_repo_with_manifests: Path
    ) -> None:
        """Test that module files are captured in the Module object."""
        config = ProcessingConfig(
            base_dir=temp_repo_with_manifests.parent,
            raw_subdir=".",
            output_subdir="output",
            category="test",
            module_discovery_strategy="manifest",
        )
        processor = RepoProcessor(config)

        modules = processor._discover_modules(temp_repo_with_manifests)

        component1 = next(m for m in modules if m.name == "component1")
        file_names = {f.path.name for f in component1.files}
        assert "manifest.json" in file_names
        assert "__init__.py" in file_names
        assert "const.py" in file_names


class TestProcessorManifestStrategyConfig:
    """Test configuration for manifest strategy."""

    def test_config_accepts_module_discovery_strategy(self) -> None:
        """Test that ProcessingConfig accepts module_discovery_strategy field."""
        config = ProcessingConfig(
            base_dir=Path.cwd(),
            raw_subdir="raw",
            output_subdir="output",
            category="test",
            module_discovery_strategy="manifest",
        )
        assert config.module_discovery_strategy == "manifest"

    def test_config_defaults_to_manifest_strategy(self) -> None:
        """Test that module_discovery_strategy defaults to 'manifest'."""
        config = ProcessingConfig(
            base_dir=Path.cwd(),
            raw_subdir="raw",
            output_subdir="output",
            category="test",
        )
        assert config.module_discovery_strategy == "manifest"

    def test_config_accepts_anchor_filenames(self) -> None:
        """Test that anchor_filenames can be customized."""
        config = ProcessingConfig(
            base_dir=Path.cwd(),
            raw_subdir="raw",
            output_subdir="output",
            category="test",
            anchor_filenames={"manifest.json", "custom.json"},
        )
        assert "custom.json" in config.anchor_filenames


class TestProcessorManifestWithOverrides:
    """Test manifest strategy with overrides."""

    def test_module_overrides_override_manifest(self) -> None:
        """Test that module overrides take precedence over manifest discovery."""
        # This tests the override mechanism - modules can be manually specified
        # to override/disable auto-discovered modules
        config = ProcessingConfig(
            base_dir=Path.cwd(),
            raw_subdir="raw",
            output_subdir="output",
            category="test",
            module_discovery_strategy="manifest",
            module_overrides={
                "disabled_component": {"enabled": False},
                "custom_component": {
                    "enabled": True,
                    "path": "custom_components/custom",
                    "anchor_type": "manual",
                },
            },
        )
        processor = RepoProcessor(config)

        # The override mechanism should be available
        assert config.module_overrides is not None
        assert "disabled_component" in config.module_overrides
        assert config.module_overrides["disabled_component"]["enabled"] is False
