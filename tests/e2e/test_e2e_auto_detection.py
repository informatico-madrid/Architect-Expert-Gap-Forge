#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""End-to-end verification of auto-detection POC flow.

This test verifies the complete auto-detection flow from:
_detect_strategy() -> discover_modules() routing -> module discovery results
"""

import pytest
from pathlib import Path
import tempfile
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from discovery.file_scanner import _detect_strategy, discover_modules


class TestE2EAutoDetectionYAML:
    """Test end-to-end auto-detection for YAML repositories."""

    def test_yaml_repo_auto_detection_flow(self):
        """Full POC flow: detect -> route -> discover -> verify."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create test YAML structure
            themes_dir = root / "themes" / "dark"
            themes_dir.mkdir(parents=True)
            (themes_dir / "config.yaml").write_text(
                "name: Dark Theme\nicon: theme-dark\n"
            )

            templates_dir = root / "templates" / "automations"
            templates_dir.mkdir(parents=True)
            (templates_dir / "automation.jinja").write_text("{{ 'test' }}")

            # 1. Detect strategy using _detect_strategy()
            detected = _detect_strategy(root)
            assert detected == "yaml", f"Expected 'yaml', got '{detected}'"

            # 2. Route to discover_modules() with detected strategy
            # Pass YAML extensions for YAML detection to work
            yaml_extensions = {".yaml", ".yml", ".jinja", ".jinja2"}
            modules = discover_modules(
                root=root,
                strategy="auto",
                ignore_patterns=set(),
                extensions=yaml_extensions,
                anchor_filenames=set(),
                build_module_func=None,
            )

            # 3. Verify discovery results
            assert len(modules) >= 1, f"Expected at least 1 module, got {len(modules)}"

            # 4. Verify modules have correct anchor_type
            for mod in modules:
                assert mod.anchor_type in ("yaml", "jinja"), (
                    f"Expected anchor_type 'yaml' or 'jinja', got '{mod.anchor_type}'"
                )

            print(f"✓ YAML detection: {detected}")
            print(f"  Found {len(modules)} module(s)")
            for mod in modules:
                print(f"  - {mod.name} (anchor: {mod.anchor_type})")

    def test_yaml_vs_typescript_priority(self):
        """YAML has priority over TypeScript in detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create both YAML and TypeScript files
            (root / "theme.yaml").write_text("name: Test")
            (root / "src").mkdir()
            (root / "src" / "button.ts").write_text("export {}")

            # Detect strategy
            detected = _detect_strategy(root)

            # YAML should be detected (has priority)
            assert detected == "yaml", (
                f"Expected 'yaml' (YAML priority), got '{detected}'"
            )
            print(f"✓ YAML priority test passed: detected '{detected}'")


class TestE2EAutoDetectionManifest:
    """Test end-to-end auto-detection for manifest-based repos."""

    def test_manifest_repo_auto_detection_flow(self):
        """Full POC flow for manifest-based repositories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create manifest.json structure
            mod_dir = root / "custom_component"
            mod_dir.mkdir()
            manifest_path = mod_dir / "manifest.json"
            manifest_path.write_text('{"domain": "test", "name": "Test Component"}')

            # 1. Detect strategy
            detected = _detect_strategy(root)
            assert detected == "manifest", f"Expected 'manifest', got '{detected}'"

            # 2. Discover modules with auto strategy
            # Pass manifest.json as extension for manifest detection
            modules = discover_modules(
                root=root,
                strategy="auto",
                ignore_patterns=set(),
                extensions={".json"},
                anchor_filenames={"manifest.json"},
            )

            # 3. Verify discovery
            assert len(modules) >= 1, f"Expected at least 1 module, got {len(modules)}"

            # 4. Verify manifest anchor_type
            for mod in modules:
                if mod_path := mod.path:
                    if (mod_path / "manifest.json").exists():
                        assert mod.anchor_type == "manifest", (
                            f"Expected 'manifest' anchor for manifest.json module, got '{mod.anchor_type}'"
                        )

            print(f"✓ Manifest detection: {detected}")
            print(f"  Found {len(modules)} module(s)")
            for mod in modules:
                print(f"  - {mod.name} (anchor: {mod.anchor_type})")


class TestE2EAutoDetectionInit:
    """Test end-to-end auto-detection for Python package repos."""

    def test_init_repo_auto_detection_flow(self):
        """Full POC flow for Python package repositories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create Python package structure
            pkg_dir = root / "mypackage"
            pkg_dir.mkdir()
            (pkg_dir / "__init__.py").write_text("# Python package\n")
            (pkg_dir / "module.py").write_text("def func(): pass\n")

            # 1. Detect strategy
            detected = _detect_strategy(root)
            assert detected == "init", f"Expected 'init', got '{detected}'"

            # 2. Discover modules
            # Pass __init__.py for init detection
            modules = discover_modules(
                root=root,
                strategy="auto",
                ignore_patterns=set(),
                extensions={".py"},
                anchor_filenames={"__init__.py"},
            )

            # 3. Verify discovery
            assert len(modules) >= 1, f"Expected at least 1 module, got {len(modules)}"

            print(f"✓ Init detection: {detected}")
            print(f"  Found {len(modules)} module(s)")


class TestE2EAutoDetectionTypeScript:
    """Test end-to-end auto-detection for TypeScript repos."""

    def test_typescript_repo_auto_detection_flow(self):
        """Full POC flow for TypeScript repositories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create TypeScript structure
            src_dir = root / "src"
            src_dir.mkdir()
            (src_dir / "button.ts").write_text("export function Button() {}\n")
            (src_dir / "card.tsx").write_text("export function Card() {}\n")

            # 1. Detect strategy
            detected = _detect_strategy(root)
            assert detected == "typescript", f"Expected 'typescript', got '{detected}'"

            # 2. Discover modules
            # Pass TypeScript extensions for TypeScript discovery
            modules = discover_modules(
                root=root,
                strategy="auto",
                ignore_patterns=set(),
                extensions={".ts", ".tsx"},
                anchor_filenames=set(),
            )

            # 3. Verify discovery
            assert len(modules) >= 1, f"Expected at least 1 module, got {len(modules)}"

            print(f"✓ TypeScript detection: {detected}")
            print(f"  Found {len(modules)} module(s)")


class TestE2EAutoDetectionDirectory:
    """Test end-to-end auto-detection for generic directory repos."""

    def test_directory_fallback_auto_detection_flow(self):
        """Full POC flow for directory fallback detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create generic directory structure (no recognizable patterns)
            (root / "directory1").mkdir()
            (root / "directory2").mkdir()
            (root / "config.txt").write_text("generic config")

            # 1. Detect strategy (should fallback to "directory")
            detected = _detect_strategy(root)
            assert detected == "directory", (
                f"Expected 'directory' fallback, got '{detected}'"
            )

            print(f"✓ Directory fallback detection: {detected}")


class TestE2EAutoDetectionExclusions:
    """Test end-to-end detection with excluded directories."""

    def test_excluded_dirs_not_detected(self):
        """Files in excluded dirs should not affect detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # TypeScript in node_modules should be excluded
            (root / "node_modules").mkdir()
            (root / "node_modules" / "test.ts").write_text("export {}")

            # YAML in themes should be detected
            (root / "themes").mkdir()
            (root / "themes" / "config.yaml").write_text("key: value")

            # Detect strategy
            detected = _detect_strategy(root)
            assert detected == "yaml", (
                f"Expected 'yaml' (excluded node_modules), got '{detected}'"
            )

            print(
                f"✓ Exclusion test passed: detected '{detected}' (node_modules excluded)"
            )


if __name__ == "__main__":
    # Run all tests
    pytest.main([__file__, "-v"])
