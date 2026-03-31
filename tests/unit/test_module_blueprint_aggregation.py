# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Unit Tests for MODULE_BLUEPRINT Anchor Aggregation
===================================================

Tests anchor file aggregation for manifest.json, const.py, services.yaml.

Requirements: AC-3.1 to AC-3.7, FR-3
"""

from __future__ import annotations

from pathlib import Path

from src.discovery import ProcessingConfig, RepoProcessor


class TestAnchorAggregation:
    """Unit tests for MODULE_BLUEPRINT anchor aggregation."""

    def test_manifest_json_anchor(self, tmp_path: Path) -> None:
        """Test that manifest.json is used as anchor for MODULE_BLUEPRINT.

        AC-3.2: manifest.json should be detected as anchor file for Python.
        """
        repo_root = tmp_path / "test_repo"
        repo_root.mkdir()

        owner_dir = repo_root / "owner" / "myrepo"
        owner_dir.mkdir(parents=True)

        component = owner_dir / "custom_components" / "test_component"
        component.mkdir(parents=True)

        # Create manifest.json (anchor file)
        import json
        (component / "manifest.json").write_text(json.dumps({
            "domain": "test_component",
            "name": "Test Component",
            "version": "1.0.0",
            "dependencies": ["frontend", "http"],
        }))

        # Create component file
        (component / "component.py").write_text("""
DOMAIN = 'test_component'

def process_data(data):
    return data
""".strip())

        config = ProcessingConfig(
            base_dir=tmp_path,
            raw_subdir="test_repo",
            output_subdir="output",
            category="test_repo",
            profile="homeassistant",
        )
        processor = RepoProcessor(config)
        processor.run()

        # Verify bundle was created
        output_dir = tmp_path / "output" / "test_repo"
        bundle_files = list(output_dir.rglob("*.txt"))

        # Should have MODULE_BLUEPRINT referencing manifest.json
        blueprint_files = [
            f for f in bundle_files
            if 'MODULE_BLUEPRINT' in f.read_text()
        ]

        assert len(blueprint_files) > 0, (
            "MODULE_BLUEPRINT should be emitted"
        )

        # Verify manifest.json is referenced
        blueprint = blueprint_files[0].read_text()
        assert 'manifest.json' in blueprint, (
            "MODULE_BLUEPRINT should reference manifest.json as anchor"
        )

    def test_const_py_anchor(self, tmp_path: Path) -> None:
        """Test that const.py is used as anchor for MODULE_BLUEPRINT.

        AC-3.3: const.py should be detected as anchor file for vocabulary extraction.
        """
        repo_root = tmp_path / "test_repo"
        repo_root.mkdir()

        owner_dir = repo_root / "owner" / "myrepo"
        owner_dir.mkdir(parents=True)

        component = owner_dir / "custom_components" / "test_component"
        component.mkdir(parents=True)

        # Create manifest.json
        import json
        (component / "manifest.json").write_text(json.dumps({
            "domain": "test_component",
            "name": "Test Component",
            "version": "1.0.0",
        }))

        # Create const.py (anchor file with vocabulary)
        (component / "const.py").write_text("""
DOMAIN = 'test_component'
PLATFORMS = ['sensor', 'switch', 'light']
SERVICE_NAMES = ['refresh', 'update', 'sync']
CONSTANT_1 = 'value1'
CONSTANT_2 = 'value2'
""".strip())

        # Create component file
        (component / "component.py").write_text("""
from . import const

def process_data(data):
    return data
""".strip())

        config = ProcessingConfig(
            base_dir=tmp_path,
            raw_subdir="test_repo",
            output_subdir="output",
            category="test_repo",
            profile="homeassistant",
        )
        processor = RepoProcessor(config)
        processor.run()

        # Verify bundle was created
        output_dir = tmp_path / "output" / "test_repo"
        bundle_files = list(output_dir.rglob("*.txt"))

        # Should have MODULE_BLUEPRINT referencing const.py
        blueprint_files = [
            f for f in bundle_files
            if 'MODULE_BLUEPRINT' in f.read_text()
        ]

        assert len(blueprint_files) > 0, (
            "MODULE_BLUEPRINT should be emitted"
        )

        # Verify const.py is referenced
        blueprint = blueprint_files[0].read_text()
        assert 'const.py' in blueprint, (
            "MODULE_BLUEPRINT should reference const.py as anchor"
        )

    def test_services_yaml_anchor(self, tmp_path: Path) -> None:
        """Test that services.yaml is used as anchor for MODULE_BLUEPRINT.

        AC-3.4: services.yaml should be detected as anchor file for schema extraction.
        """
        repo_root = tmp_path / "test_repo"
        repo_root.mkdir()

        owner_dir = repo_root / "owner" / "myrepo"
        owner_dir.mkdir(parents=True)

        component = owner_dir / "custom_components" / "test_component"
        component.mkdir(parents=True)

        # Create manifest.json
        import json
        (component / "manifest.json").write_text(json.dumps({
            "domain": "test_component",
            "name": "Test Component",
            "version": "1.0.0",
        }))

        # Create services.yaml (anchor file with schema)
        (component / "services.yaml").write_text("""
refresh_data:
  name: Refresh Data
  description: Refreshes the data from the source
  target:
    entity_id:
      name: Entity ID
      description: The entity to refresh
  action:
    data:
      refresh_type:
        name: Refresh Type
        description: Type of refresh to perform
        required: true
        selector:
          select:
            options:
              - full
              - incremental

update_config:
  name: Update Configuration
  description: Updates the configuration
  action:
    data:
      config_file:
        name: Config File
        description: The configuration file to use
""".strip())

        # Create component file
        (component / "component.py").write_text("""
def process_data(data):
    return data
""".strip())

        config = ProcessingConfig(
            base_dir=tmp_path,
            raw_subdir="test_repo",
            output_subdir="output",
            category="test_repo",
            profile="homeassistant",
        )
        processor = RepoProcessor(config)
        processor.run()

        # Verify bundle was created
        output_dir = tmp_path / "output" / "test_repo"
        bundle_files = list(output_dir.rglob("*.txt"))

        # Should have MODULE_BLUEPRINT referencing services.yaml
        blueprint_files = [
            f for f in bundle_files
            if 'MODULE_BLUEPRINT' in f.read_text()
        ]

        assert len(blueprint_files) > 0, (
            "MODULE_BLUEPRINT should be emitted"
        )

        # Verify services.yaml is referenced
        blueprint = blueprint_files[0].read_text()
        assert 'services.yaml' in blueprint, (
            "MODULE_BLUEPRINT should reference services.yaml as anchor"
        )

    def test_multiple_anchors_aggregated(self, tmp_path: Path) -> None:
        """Test that multiple anchor files are aggregated in MODULE_BLUEPRINT.

        AC-3.5: Multiple anchors (manifest.json, const.py, services.yaml) should all be included.
        """
        repo_root = tmp_path / "test_repo"
        repo_root.mkdir()

        owner_dir = repo_root / "owner" / "myrepo"
        owner_dir.mkdir(parents=True)

        component = owner_dir / "custom_components" / "test_component"
        component.mkdir(parents=True)

        # Create manifest.json
        import json
        (component / "manifest.json").write_text(json.dumps({
            "domain": "test_component",
            "name": "Test Component",
            "version": "1.0.0",
            "dependencies": ["frontend"],
        }))

        # Create const.py
        (component / "const.py").write_text("""
DOMAIN = 'test_component'
PLATFORMS = ['sensor', 'switch']
""".strip())

        # Create services.yaml
        (component / "services.yaml").write_text("""
refresh:
  name: Refresh
  description: Refresh data
""".strip())

        # Create component file
        (component / "component.py").write_text("""
def process_data(data):
    return data
""".strip())

        config = ProcessingConfig(
            base_dir=tmp_path,
            raw_subdir="test_repo",
            output_subdir="output",
            category="test_repo",
            profile="homeassistant",
        )
        processor = RepoProcessor(config)
        processor.run()

        # Verify bundle was created
        output_dir = tmp_path / "output" / "test_repo"
        bundle_files = list(output_dir.rglob("*.txt"))

        # Should have MODULE_BLUEPRINT with all anchors
        blueprint_files = [
            f for f in bundle_files
            if 'MODULE_BLUEPRINT' in f.read_text()
        ]

        assert len(blueprint_files) > 0, (
            "MODULE_BLUEPRINT should be emitted"
        )

        blueprint = blueprint_files[0].read_text()

        # Verify all anchors are referenced
        assert 'manifest.json' in blueprint, (
            "MODULE_BLUEPRINT should reference manifest.json"
        )
        assert 'const.py' in blueprint, (
            "MODULE_BLUEPRINT should reference const.py"
        )
        assert 'services.yaml' in blueprint, (
            "MODULE_BLUEPRINT should reference services.yaml"
        )
