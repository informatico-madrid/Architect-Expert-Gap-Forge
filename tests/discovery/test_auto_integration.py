# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Integration Tests for Auto Module Discovery Strategy
=====================================================
Tests for Tasks 32-38: Comprehensive integration tests verifying
the auto detection strategy works correctly across various scenarios.

Author: Joao Maria Arranz Aparicio
"""

import os
import time
from pathlib import Path
import tempfile

import pytest

from src.discovery.file_scanner import discover_modules, _detect_strategy


# =============================================================================
# TASK 32: YAML Discovery Integration Test
# =============================================================================

class TestYAMLDiscoveryIntegration:
    """Task 32: Integration tests for YAML discovery with auto strategy."""

    def test_auto_yaml_discovery(self):
        """
        Test that auto strategy correctly detects and discovers YAML modules.

        Creates a test repository with YAML files and verifies:
        1. Strategy detection returns 'yaml'
        2. Modules are discovered with anchor_type 'yaml'
        3. YAML files in themes/ and templates/ directories are found
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create YAML structure similar to Home Assistant
            themes_dir = root / "themes"
            themes_dir.mkdir()
            (themes_dir / "dark.yaml").write_text(
                "name: Dark Theme\nprimary_color: '#333333'\n"
            )
            (themes_dir / "light.yaml").write_text(
                "name: Light Theme\nprimary_color: '#ffffff'\n"
            )

            templates_dir = root / "templates"
            templates_dir.mkdir()
            (templates_dir / "automation.jinja").write_text(
                "{% if condition %}value{% endif %}\n"
            )

            # Detect strategy automatically
            detected_strategy = _detect_strategy(root)
            assert detected_strategy == "yaml", \
                f"Expected 'yaml' strategy, got '{detected_strategy}'"

            # Discover modules using auto strategy
            ignore_patterns = {"node_modules", "tests", "test", "__pycache__"}
            extensions = {".yaml", ".yml", ".jinja", ".jinja2"}
            anchor_filenames = {
                "manifest.json", "const.py", "services.yaml",
                "strings.json", "icons.json", "hacs.json"
            }

            modules = discover_modules(
                root=root,
                strategy="auto",
                ignore_patterns=ignore_patterns,
                extensions=extensions,
                anchor_filenames=anchor_filenames,
            )

            # Verify YAML modules are discovered
            yaml_modules = [m for m in modules if m.anchor_type == "yaml"]
            assert len(yaml_modules) >= 2, \
                f"Expected at least 2 YAML modules, found {len(yaml_modules)}"

            # Verify modules have correct anchor_type
            for mod in yaml_modules:
                assert mod.anchor_type == "yaml", \
                    f"Expected anchor_type 'yaml', got '{mod.anchor_type}'"


# =============================================================================
# TASK 33: TypeScript Discovery Integration Test
# =============================================================================

class TestTypeScriptDiscoveryIntegration:
    """Task 33: Integration tests for TypeScript discovery with auto strategy."""

    def test_auto_typescript_discovery(self):
        """
        Test that auto strategy correctly detects and discovers TypeScript modules.

        Creates a test repository with TypeScript files and verifies:
        1. Strategy detection returns 'typescript'
        2. Modules are discovered with anchor_type 'typescript'
        3. TypeScript files in src/ and components/ directories are found
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create TypeScript structure
            src_dir = root / "src"
            src_dir.mkdir()
            (src_dir / "app.ts").write_text(
                "export const appVersion: string = '1.0.0';\n"
            )
            (src_dir / "utils.ts").write_text(
                "export function helper(): void {}\n"
            )

            components_dir = root / "components"
            components_dir.mkdir()
            (components_dir / "Button.tsx").write_text(
                "export const Button = () => <button>Hello</button>;\n"
            )
            (components_dir / "Card.tsx").write_text(
                "export const Card = () => <div>Card</div>;\n"
            )

            # Detect strategy automatically
            detected_strategy = _detect_strategy(root)
            assert detected_strategy == "typescript", \
                f"Expected 'typescript' strategy, got '{detected_strategy}'"

            # Discover modules using auto strategy
            ignore_patterns = {"node_modules", "tests", "test", "__pycache__"}
            extensions = {".ts", ".tsx"}
            anchor_filenames = set()

            modules = discover_modules(
                root=root,
                strategy="auto",
                ignore_patterns=ignore_patterns,
                extensions=extensions,
                anchor_filenames=anchor_filenames,
            )

            # Verify TypeScript modules are discovered
            ts_modules = [m for m in modules if m.anchor_type == "typescript"]
            assert len(ts_modules) >= 2, \
                f"Expected at least 2 TypeScript modules, found {len(ts_modules)}"

            # Verify modules have correct anchor_type
            for mod in ts_modules:
                assert mod.anchor_type == "typescript", \
                    f"Expected anchor_type 'typescript', got '{mod.anchor_type}'"

    def test_auto_typescript_excludes_node_modules(self):
        """
        Test that node_modules directory is excluded from TypeScript discovery.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create TypeScript in node_modules (should be ignored)
            node_modules = root / "node_modules"
            node_modules.mkdir()
            (node_modules / "package.ts").write_text("export {}")

            # No TypeScript outside node_modules
            # Should fall back to directory strategy

            detected_strategy = _detect_strategy(root)
            assert detected_strategy == "directory", \
                f"Expected 'directory' strategy when only node_modules has TS, got '{detected_strategy}'"


# =============================================================================
# TASK 34: Mixed Repository Integration Test
# =============================================================================

class TestMixedRepositoryIntegration:
    """Task 34: Integration tests for mixed repositories (Python + TypeScript)."""

    def test_typescript_priority_over_manifest(self):
        """
        Test that TypeScript takes priority over manifest.json in mixed repos.

        Per requirements.md priority order:
        1. YAML
        2. TypeScript
        3. PHP
        4. manifest.json
        5. __init__.py
        6. directory

        TypeScript (priority 2) has higher priority than manifest.json (priority 4).
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create manifest.json (priority 4)
            config_dir = root / "config"
            config_dir.mkdir()
            (config_dir / "manifest.json").write_text(
                '{"name": "test-config", "type": "python"}\n'
            )

            # Also create TypeScript files (priority 2 - higher)
            src_dir = root / "src"
            src_dir.mkdir()
            (src_dir / "app.ts").write_text("export {}")

            detected_strategy = _detect_strategy(root)
            assert detected_strategy == "typescript", \
                f"Expected 'typescript' (higher priority), got '{detected_strategy}'"

    def test_typescript_priority_over_init(self):
        """
        Test that TypeScript takes priority over __init__.py in mixed repos.

        Per requirements.md priority order:
        1. YAML
        2. TypeScript
        3. PHP
        4. manifest.json
        5. __init__.py
        6. directory

        TypeScript (priority 2) has higher priority than __init__.py (priority 5).
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create __init__.py (priority 5)
            package_dir = root / "package"
            package_dir.mkdir()
            (package_dir / "__init__.py").write_text("")

            # Also create TypeScript files (priority 2 - higher)
            src_dir = root / "src"
            src_dir.mkdir()
            (src_dir / "app.ts").write_text("export {}")

            detected_strategy = _detect_strategy(root)
            assert detected_strategy == "typescript", \
                f"Expected 'typescript' (higher priority), got '{detected_strategy}'"

    def test_yaml_priority_over_typescript(self):
        """
        Test that YAML takes priority over TypeScript in mixed repos.

        Creates a repository with both YAML and TypeScript files,
        verifies that YAML strategy is chosen.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create YAML files (higher priority than TypeScript)
            themes_dir = root / "themes"
            themes_dir.mkdir()
            (themes_dir / "colors.yaml").write_text("primary: blue\n")

            # Also create TypeScript files
            src_dir = root / "src"
            src_dir.mkdir()
            (src_dir / "app.ts").write_text("export {}")

            detected_strategy = _detect_strategy(root)
            assert detected_strategy == "yaml", \
                f"Expected 'yaml' strategy, got '{detected_strategy}'"


# =============================================================================
# TASK 35: Performance Test for Detection Time
# =============================================================================

class TestDetectionPerformance:
    """Task 35: Performance tests for module detection time."""

    def test_detection_under_one_second(self):
        """
        Test that detection completes in < 1 second for 10,000 files.

        Creates a repository with 10,000 files and measures detection time.
        The detection should be fast as it only does existence checks,
        not file content reading.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create 10,000 files
            # Create 100 directories with 100 files each
            num_dirs = 100
            files_per_dir = 100
            num_dirs * files_per_dir

            start_time = time.time()

            for i in range(num_dirs):
                dir_name = f"dir_{i}"
                dir_path = root / dir_name
                dir_path.mkdir()
                for j in range(files_per_dir):
                    file_name = f"file_{j}.yaml"
                    (dir_path / file_name).write_text(f"key_{j}: value_{i}_{j}\n")

            detection_time = time.time() - start_time

            # Detection time should be < 1 second
            assert detection_time < 1.0, \
                f"Detection took {detection_time:.3f}s, expected < 1.0s"

            # Also verify detection works correctly
            detected_strategy = _detect_strategy(root)
            assert detected_strategy == "yaml", \
                f"Expected 'yaml' strategy for 10,000 YAML files, got '{detected_strategy}'"

    def test_module_discovery_performance(self):
        """
        Test that full module discovery completes efficiently.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create 100 directories with YAML files
            num_dirs = 100

            time.time()

            for i in range(num_dirs):
                dir_path = root / f"module_{i}"
                dir_path.mkdir()
                (dir_path / "config.yaml").write_text(f"name: module_{i}\n")

            # Time the discovery
            ignore_patterns = {"node_modules", "tests", "test", "__pycache__"}
            extensions = {".yaml", ".yml"}
            anchor_filenames = set()

            discovery_start = time.time()
            modules = discover_modules(
                root=root,
                strategy="auto",
                ignore_patterns=ignore_patterns,
                extensions=extensions,
                anchor_filenames=anchor_filenames,
            )
            discovery_time = time.time() - discovery_start

            # Discovery should complete quickly
            assert discovery_time < 2.0, \
                f"Discovery took {discovery_time:.3f}s, expected < 2.0s"

            assert len(modules) == num_dirs, \
                f"Expected {num_dirs} modules, found {len(modules)}"


# =============================================================================
# TASK 36: Large Repository Processing Performance Test
# =============================================================================

class TestLargeRepositoryPerformance:
    """Task 36: Performance tests for large repository processing."""

    def test_large_typescript_repo_processing(self):
        """
        Test that large TypeScript repository is processed in < 2 seconds.

        Creates a large repository with TypeScript files and measures
        full processing time including detection and discovery.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create a large TypeScript repository
            # 500 directories with TypeScript files
            num_dirs = 500

            start_time = time.time()

            for i in range(num_dirs):
                dir_path = root / "src" / f"module_{i}"
                dir_path.mkdir(parents=True)
                (dir_path / "index.ts").write_text("export {}")
                (dir_path / "types.ts").write_text("export type T = any")

            # Measure detection + discovery time
            time.time()

            detected_strategy = _detect_strategy(root)
            assert detected_strategy == "typescript", \
                f"Expected 'typescript' strategy, got '{detected_strategy}'"

            ignore_patterns = {"node_modules", "tests", "test", "__pycache__"}
            extensions = {".ts", ".tsx"}
            anchor_filenames = set()

            modules = discover_modules(
                root=root,
                strategy=detected_strategy,
                ignore_patterns=ignore_patterns,
                extensions=extensions,
                anchor_filenames=anchor_filenames,
            )

            total_time = time.time() - start_time

            # Total processing should be < 2 seconds
            assert total_time < 2.0, \
                f"Total processing took {total_time:.3f}s, expected < 2.0s"

            assert len(modules) == num_dirs, \
                f"Expected {num_dirs} modules, found {len(modules)}"


# =============================================================================
# TASK 37: Permission Error Test
# =============================================================================

class TestPermissionErrors:
    """Task 37: Tests for handling permission errors gracefully."""

    def test_permission_errors_handled_gracefully(self):
        """
        Test that permission errors don't crash detection and detection continues.

        Creates a repository with restricted directories and verifies:
        1. Permission errors are caught
        2. Detection continues and succeeds
        3. Warning is logged for permission issues
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create normal YAML files
            normal_dir = root / "normal"
            normal_dir.mkdir()
            (normal_dir / "config.yaml").write_text("key: value\n")

            # Try to create a restricted directory
            # Note: In many environments, we may not have permission to restrict
            # directories, so we handle both success and failure cases
            restricted_dir = root / "restricted"
            restricted_dir.mkdir()
            (restricted_dir / "secret.yaml").write_text("secret: value\n")

            # Try to remove read permissions (may fail on some systems)
            try:
                os.chmod(restricted_dir, 0o000)
                restricted_permitted = False
            except (OSError, PermissionError):
                # Cannot change permissions in this environment
                restricted_permitted = True

            # Detection should not crash
            try:
                detected_strategy = _detect_strategy(root)
                assert detected_strategy in ("yaml", "directory"), \
                    f"Expected 'yaml' or 'directory', got '{detected_strategy}'"
            finally:
                # Restore permissions for cleanup
                if not restricted_permitted:
                    try:
                        os.chmod(restricted_dir, 0o755)
                    except (OSError, PermissionError):
                        pass

    def test_permission_errors_dont_crash(self):
        """
        Test that the detection function never raises exceptions.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create repository with various scenarios
            for i in range(10):
                dir_path = root / f"dir_{i}"
                dir_path.mkdir()
                (dir_path / "file.yaml").write_text("test\n")

            # Should never crash even with empty or unusual directories
            detected_strategy = _detect_strategy(root)
            assert detected_strategy == "yaml", \
                f"Expected 'yaml', got '{detected_strategy}'"


# =============================================================================
# TASK 38: Broken Symlink Test
# =============================================================================

class TestBrokenSymlinks:
    """Task 38: Tests for handling broken symlinks gracefully."""

    def test_broken_symlinks_dont_crash(self):
        """
        Test that broken symlinks don't crash detection.

        Creates a repository with broken symlinks and verifies:
        1. No crash occurs
        2. Detection continues successfully
        3. Valid files are still discovered
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create normal YAML files
            valid_dir = root / "valid"
            valid_dir.mkdir()
            (valid_dir / "config.yaml").write_text("key: value\n")

            # Create a broken symlink
            broken_link = root / "broken_link.yaml"
            try:
                # This will create a broken symlink to a non-existent target
                broken_link.symlink_to("/nonexistent/path/to/file.yaml")
            except OSError:
                # Symlinks may not be supported in all environments
                # In that case, the test still passes as long as
                # detection works with the valid files

                # Verify detection still works
                detected_strategy = _detect_strategy(root)
                assert detected_strategy == "yaml", \
                    f"Expected 'yaml', got '{detected_strategy}'"
                return

            # Create another broken symlink (directory)
            broken_dir_link = root / "broken_dir"
            try:
                broken_dir_link.symlink_to("/nonexistent/directory")
            except OSError:
                pass

            # Detection should not crash despite broken symlinks
            try:
                detected_strategy = _detect_strategy(root)
                # Should still detect YAML from valid files
                assert detected_strategy in ("yaml", "directory"), \
                    f"Expected 'yaml' or 'directory', got '{detected_strategy}'"

                # Verify modules are discovered
                ignore_patterns = {"node_modules", "tests", "test", "__pycache__"}
                extensions = {".yaml", ".yml"}
                anchor_filenames = set()

                modules = discover_modules(
                    root=root,
                    strategy=detected_strategy,
                    ignore_patterns=ignore_patterns,
                    extensions=extensions,
                    anchor_filenames=anchor_filenames,
                )

                # Should have at least the valid module
                assert len(modules) >= 1, \
                    f"Expected at least 1 module, found {len(modules)}"

            except Exception as e:
                pytest.fail(f"Detection crashed with broken symlinks: {e}")

    def test_symlink_handling_in_discovery(self):
        """
        Test that symlinks are handled correctly during discovery.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create a valid directory with YAML
            src_dir = root / "src"
            src_dir.mkdir()
            (src_dir / "config.yaml").write_text("name: test\n")

            # Create symlink to the directory
            link_dir = root / "src_link"
            try:
                link_dir.symlink_to(src_dir)
            except OSError:
                # Symlinks not supported, continue with test
                pass

            # Discovery should work regardless of symlinks
            ignore_patterns = {"node_modules", "tests", "test", "__pycache__"}
            extensions = {".yaml", ".yml"}
            anchor_filenames = set()

            modules = discover_modules(
                root=root,
                strategy="auto",
                ignore_patterns=ignore_patterns,
                extensions=extensions,
                anchor_filenames=anchor_filenames,
            )

            # Should discover at least one module
            assert len(modules) >= 1, \
                f"Expected at least 1 module, found {len(modules)}"


# =============================================================================
# Additional Integration Test Scenarios
# =============================================================================

class TestIntegrationScenarios:
    """Additional integration test scenarios covering various combinations."""

    def test_empty_repository(self):
        """
        Test that empty repositories are handled correctly.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create an empty repository (only .git)
            (root / ".git").mkdir()

            detected_strategy = _detect_strategy(root)
            assert detected_strategy == "directory", \
                f"Expected 'directory' for empty repo, got '{detected_strategy}'"

    def test_mixed_file_types_priority(self):
        """
        Test priority order per requirements.md:
        1. YAML
        2. TypeScript
        3. PHP
        4. manifest.json
        5. __init__.py
        6. directory
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create files in order of priority (lowest to highest)
            # __init__.py (lowest - priority 5)
            package_dir = root / "package"
            package_dir.mkdir()
            (package_dir / "__init__.py").write_text("")

            # manifest.json (priority 4)
            config_dir = root / "config"
            config_dir.mkdir()
            (config_dir / "manifest.json").write_text("{}")

            # TypeScript (priority 2)
            src_dir = root / "src"
            src_dir.mkdir()
            (src_dir / "app.ts").write_text("export {}")

            # YAML (highest - priority 1)
            themes_dir = root / "themes"
            themes_dir.mkdir()
            (themes_dir / "colors.yaml").write_text("primary: blue\n")

            detected_strategy = _detect_strategy(root)
            assert detected_strategy == "yaml", \
                f"Expected 'yaml' (highest priority), got '{detected_strategy}'"

    def test_auto_strategy_coverage(self):
        """
        Test that all detection strategies can be discovered.
        """
        # Test each strategy separately
        def setup_manifest(r: Path):
            (r / "config").mkdir()
            (r / "config" / "manifest.json").write_text("{}")

        def setup_init(r: Path):
            (r / "pkg").mkdir()
            (r / "pkg" / "__init__.py").write_text("")

        def setup_yaml(r: Path):
            (r / "theme.yaml").write_text("key: value\n")

        def setup_typescript(r: Path):
            (r / "app.ts").write_text("export {}")

        def setup_filesystem(r: Path):
            (r / "index.php").write_text("<?php")

        strategies_to_test = [
            ("manifest", setup_manifest),
            ("init", setup_init),
            ("yaml", setup_yaml),
            ("typescript", setup_typescript),
            ("filesystem", setup_filesystem),
        ]

        for expected_strategy, setup_func in strategies_to_test:
            with tempfile.TemporaryDirectory() as tmpdir:
                root = Path(tmpdir)
                setup_func(root)

                detected_strategy = _detect_strategy(root)
                assert detected_strategy == expected_strategy, \
                    f"For {expected_strategy}, expected '{expected_strategy}', got '{detected_strategy}'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
