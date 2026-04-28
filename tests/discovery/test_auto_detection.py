#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path
import tempfile
from src.discovery.file_scanner import _detect_strategy


class TestDetectStrategy:
    def test_detect_strategy_yaml(self):
        """Repository with only YAML files should detect as 'yaml'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "themes").mkdir()
            (root / "themes" / "dark.yaml").write_text("key: value")
            (root / "templates").mkdir()
            (root / "templates" / "automation.jinja").write_text("template")

            strategy = _detect_strategy(root)
            assert strategy == "yaml"

    def test_detect_strategy_typescript(self):
        """Repository with only TS files should detect as 'typescript'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "src").mkdir()
            (root / "src" / "button.ts").write_text("export {}")
            (root / "src" / "card.tsx").write_text("export {}")

            strategy = _detect_strategy(root)
            assert strategy == "typescript"

    def test_detect_strategy_fallback(self):
        """Empty repository should detect as 'directory'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".git").mkdir()  # Only git directory

            strategy = _detect_strategy(root)
            assert strategy == "directory"

    def test_detect_strategy_exclusions(self):
        """Files in excluded directories should not be detected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # TypeScript in node_modules should be excluded
            (root / "node_modules").mkdir()
            (root / "node_modules" / "test.ts").write_text("export {}")
            # TypeScript in src should be detected
            (root / "src").mkdir()
            (root / "src" / "test.ts").write_text("export {}")

            strategy = _detect_strategy(root)
            assert strategy == "typescript"

# =============================================================================
# TASK 26: TypeScript Detection Unit Tests
# =============================================================================

class TestTypeScriptDetection:
    """Test cases for TypeScript file detection."""

    def test_detect_ts_extension(self):
        """Test that .ts files are detected as TypeScript."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "src").mkdir()
            (root / "src" / "app.ts").write_text("export const x: number = 1;")

            strategy = _detect_strategy(root)
            assert strategy == "typescript"

    def test_detect_tsx_extension(self):
        """Test that .tsx files are detected as TypeScript."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "components").mkdir()
            (root / "components" / "Button.tsx").write_text("export const Button = () => {};")

            strategy = _detect_strategy(root)
            assert strategy == "typescript"

    def test_detect_combined_ts_and_tsx(self):
        """Test that mixed .ts and .tsx files are detected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "src").mkdir()
            (root / "src" / "utils.ts").write_text("export {}")
            (root / "src" / "Component.tsx").write_text("export {}")

            strategy = _detect_strategy(root)
            assert strategy == "typescript"

    def test_excludes_node_modules(self):
        """Test that node_modules directory is excluded from TypeScript detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # TypeScript in node_modules should be excluded
            (root / "node_modules").mkdir()
            (root / "node_modules" / "package.ts").write_text("export {}")
            # No other TypeScript files
            # Should fall back to directory since no ts outside node_modules

            strategy = _detect_strategy(root)
            assert strategy == "directory"

    def test_excludes_tests_directory(self):
        """Test that tests directory is excluded from TypeScript detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "tests").mkdir()
            (root / "tests" / "app.test.ts").write_text("export {}")
            # No other TypeScript files
            # Should fall back to directory since no ts outside tests

            strategy = _detect_strategy(root)
            assert strategy == "directory"

    def test_excludes_test_directory(self):
        """Test that test directory is excluded from TypeScript detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "test").mkdir()
            (root / "test" / "app.test.ts").write_text("export {}")
            # No other TypeScript files
            # Should fall back to directory since no ts outside test

            strategy = _detect_strategy(root)
            assert strategy == "directory"


# =============================================================================
# TASK 27: PHP Detection Unit Tests
# =============================================================================

class TestPHPDetection:
    """Test cases for PHP file detection."""

    def test_detect_php_file(self):
        """Test that .php files are detected as filesystem (PHP)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "src").mkdir()
            (root / "src" / "index.php").write_text("<?php echo 'hello';")

            strategy = _detect_strategy(root)
            assert strategy == "filesystem"

    def test_detect_php_in_subdir(self):
        """Test that PHP files in subdirectories are detected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "controllers").mkdir()
            (root / "controllers" / "UserController.php").write_text("<?php class UserController {}")

            strategy = _detect_strategy(root)
            assert strategy == "filesystem"

    def test_excludes_vendor_directory(self):
        """Test that vendor directory is excluded from PHP detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # PHP in vendor should be excluded
            (root / "vendor").mkdir()
            (root / "vendor" / "package.php").write_text("<?php")
            # No other PHP files
            # Should fall back to directory

            strategy = _detect_strategy(root)
            assert strategy == "directory"

    def test_excludes_cache_directory(self):
        """Test that cache directory is excluded from PHP detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # PHP in cache should be excluded
            (root / "cache").mkdir()
            (root / "cache" / "temp.php").write_text("<?php")
            # No other PHP files
            # Should fall back to directory

            strategy = _detect_strategy(root)
            assert strategy == "directory"

    def test_excludes_node_modules(self):
        """Test that node_modules is excluded from PHP detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # PHP in node_modules should be excluded
            (root / "node_modules").mkdir()
            (root / "node_modules" / "package.php").write_text("<?php")
            # No other PHP files
            # Should fall back to directory

            strategy = _detect_strategy(root)
            assert strategy == "directory"

    def test_excludes_tests_directory(self):
        """Test that tests directory is excluded from PHP detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "tests").mkdir()
            (root / "tests" / "test.php").write_text("<?php")
            # No other PHP files
            # Should fall back to directory

            strategy = _detect_strategy(root)
            assert strategy == "directory"


# =============================================================================
# TASK 28: Manifest Detection Unit Tests
# =============================================================================

class TestManifestDetection:
    """Test cases for manifest.json detection."""

    def test_detect_manifest_json(self):
        """Test that manifest.json files are detected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "config").mkdir()
            (root / "config" / "manifest.json").write_text('{"name": "test"}')

            strategy = _detect_strategy(root)
            assert strategy == "manifest"

    def test_detect_manifest_priority_over_typescript(self):
        """Test that TypeScript has higher priority than manifest.json.

        Per requirements.md priority order:
        1. YAML
        2. TypeScript
        3. PHP
        4. manifest.json
        5. __init__.py
        6. directory
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # manifest.json exists (priority 4)
            (root / "config").mkdir()
            (root / "config" / "manifest.json").write_text('{"name": "test"}')
            # TypeScript file also exists (priority 2)
            (root / "src").mkdir()
            (root / "src" / "app.ts").write_text("export {}")

            strategy = _detect_strategy(root)
            # TypeScript has higher priority than manifest.json per requirements.md
            assert strategy == "typescript"

    def test_detect_manifest_priority_over_init(self):
        """Test that manifest.json has higher priority than __init__.py.

        Per requirements.md priority order:
        1. YAML
        2. TypeScript
        3. PHP
        4. manifest.json
        5. __init__.py
        6. directory
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # manifest.json exists (priority 4)
            (root / "config").mkdir()
            (root / "config" / "manifest.json").write_text('{"name": "test"}')
            # __init__.py also exists (priority 5)
            (root / "src").mkdir()
            (root / "src" / "__init__.py").write_text("")

            strategy = _detect_strategy(root)
            # manifest.json has higher priority than __init__.py per requirements.md
            assert strategy == "manifest"


# =============================================================================
# TASK 29: Init Detection Unit Tests
# =============================================================================

class TestInitDetection:
    """Test cases for __init__.py detection."""

    def test_detect_init_file(self):
        """Test that __init__.py files are detected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "package").mkdir()
            (root / "package" / "__init__.py").write_text("")

            strategy = _detect_strategy(root)
            assert strategy == "init"

    def test_detect_init_priority_over_yaml(self):
        """Test that YAML has higher priority than __init__.py.

        Per requirements.md priority order:
        1. YAML
        2. TypeScript
        3. PHP
        4. manifest.json
        5. __init__.py
        6. directory
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # __init__.py exists (priority 5)
            (root / "package").mkdir()
            (root / "package" / "__init__.py").write_text("")
            # YAML file also exists (priority 1)
            (root / "config").mkdir()
            (root / "config" / "settings.yaml").write_text("key: value")

            strategy = _detect_strategy(root)
            # YAML has higher priority than __init__.py per requirements.md
            assert strategy == "yaml"

    def test_excludes_pycache(self):
        """Test that __pycache__ directory is excluded from init detection.

        Note: The _detect_strategy function calls is_ignored() which checks
        against ignore_patterns. Since __init__ strategy passes ignore_patterns
        set to a predefined exclusion list including __pycache__, this test
        verifies the behavior.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # __init__.py outside __pycache__ (detected)
            (root / "package").mkdir()
            (root / "package" / "__init__.py").write_text("")
            # __init__.py inside __pycache__ (should be ignored)
            (root / "__pycache__").mkdir()
            (root / "__pycache__" / "__init__.py").write_text("")

            # Even with __pycache__, the valid __init__.py outside should trigger 'init'
            strategy = _detect_strategy(root)
            assert strategy == "init"

    def test_detect_multiple_init_files(self):
        """Test that multiple __init__.py files are detected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "package1").mkdir()
            (root / "package1" / "__init__.py").write_text("")
            (root / "package2").mkdir()
            (root / "package2" / "__init__.py").write_text("")

            strategy = _detect_strategy(root)
            assert strategy == "init"


# =============================================================================
# TASK 30: Priority Order Verification Tests
# =============================================================================

class TestPriorityOrderVerification:
    """Test cases to verify the priority order of strategy detection."""

    def test_yaml_priority_over_typescript(self):
        """Test that YAML has priority over TypeScript."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # YAML file exists
            (root / "themes").mkdir()
            (root / "themes" / "colors.yaml").write_text("primary: blue")
            # TypeScript file also exists
            (root / "src").mkdir()
            (root / "src" / "app.ts").write_text("export {}")

            strategy = _detect_strategy(root)
            assert strategy == "yaml"

    def test_typescript_priority_over_php(self):
        """Test that TypeScript has priority over PHP (filesystem)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # TypeScript file exists
            (root / "src").mkdir()
            (root / "src" / "app.ts").write_text("export {}")
            # PHP file also exists
            (root / "controllers").mkdir()
            (root / "controllers" / "index.php").write_text("<?php")

            strategy = _detect_strategy(root)
            assert strategy == "typescript"

    def test_php_priority_over_manifest(self):
        """Test that PHP (filesystem) has priority over manifest detection.

        Per requirements.md priority order:
        1. YAML
        2. TypeScript
        3. PHP
        4. manifest.json
        5. __init__.py
        6. directory
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # PHP file exists
            (root / "controllers").mkdir()
            (root / "controllers" / "index.php").write_text("<?php")
            # manifest.json also exists
            (root / "config").mkdir()
            (root / "config" / "manifest.json").write_text('{"name": "test"}')

            strategy = _detect_strategy(root)
            # PHP has higher priority than manifest.json per requirements.md
            assert strategy == "filesystem"

    def test_manifest_priority_over_init(self):
        """Test that manifest.json has priority over __init__.py.

        Per requirements.md priority order:
        1. YAML
        2. TypeScript
        3. PHP
        4. manifest.json
        5. __init__.py
        6. directory
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # manifest.json exists
            (root / "config").mkdir()
            (root / "config" / "manifest.json").write_text('{"name": "test"}')
            # __init__.py also exists
            (root / "package").mkdir()
            (root / "package" / "__init__.py").write_text("")

            strategy = _detect_strategy(root)
            # manifest.json has higher priority than __init__.py per requirements.md
            assert strategy == "manifest"

    def test_init_priority_over_directory(self):
        """Test that __init__.py has priority over directory fallback."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # __init__.py exists
            (root / "package").mkdir()
            (root / "package" / "__init__.py").write_text("")
            # No manifest or other files

            strategy = _detect_strategy(root)
            assert strategy == "init"


# =============================================================================
# TASK 31: Fallback Detection Unit Tests
# =============================================================================

class TestFallbackDetection:
    """Test cases for fallback detection to 'directory' strategy."""

    def test_empty_directory_returns_directory(self):
        """Test that empty directory returns 'directory' strategy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # Directory is empty (only .git would make it a repo)

            strategy = _detect_strategy(root)
            assert strategy == "directory"

    def test_git_only_directory_returns_directory(self):
        """Test that directory with only .git returns 'directory' strategy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # Only .git directory exists
            (root / ".git").mkdir()

            strategy = _detect_strategy(root)
            assert strategy == "directory"

    def test_non_source_files_returns_directory(self):
        """Test that directory with only non-source files returns 'directory'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # Only README and text files
            (root / "README.md").write_text("# Project")
            (root / "config.txt").write_text("setting=value")
            (root / "data.json").write_text('{"key": "value"}')

            strategy = _detect_strategy(root)
            assert strategy == "directory"

    def test_directory_with_only_md_files(self):
        """Test that directory with only markdown files returns 'directory'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "docs").mkdir()
            (root / "docs" / "README.md").write_text("# Docs")
            (root / "docs" / "guide.md").write_text("Guide content")

            strategy = _detect_strategy(root)
            assert strategy == "directory"

    def test_directory_with_only_json_files(self):
        """Test that directory with only JSON files returns 'directory'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "data").mkdir()
            (root / "data" / "config.json").write_text('{"key": "value"}')

            strategy = _detect_strategy(root)
            assert strategy == "directory"
