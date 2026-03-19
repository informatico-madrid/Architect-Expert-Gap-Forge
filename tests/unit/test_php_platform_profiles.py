# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for PHP platform profiles detection.

These tests verify that detect_platform correctly identifies PHP platforms
through marker files, marker patterns, and falls back to generic_php when
no platform is detected.

Author: Joao Maria Arranz Aparicio
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from src.discovery.php_platform_profiles import (
    PLATFORM_REGISTRY,
    detect_platform,
    get_platform_profile,
)


class TestDetectPlatformMarkerFiles:
    """Test suite for marker file detection in detect_platform."""

    def test_detects_oscommerce_via_marker_file(self, tmp_path: Path) -> None:
        """Should detect osCommerce when application_top.php is present."""
        # Create marker file
        (tmp_path / "catalog" / "includes").mkdir(parents=True)
        (tmp_path / "catalog" / "includes" / "application_top.php").touch()
        (tmp_path / "catalog" / "includes" / "functions").mkdir()
        (tmp_path / "catalog" / "includes" / "functions" / "database.php").touch()

        result = detect_platform(tmp_path)
        assert result.name == "oscommerce"

    def test_detects_oscommerce_admin_marker(self, tmp_path: Path) -> None:
        """Should detect osCommerce when admin marker file is present."""
        (tmp_path / "admin" / "includes").mkdir(parents=True)
        (tmp_path / "admin" / "includes" / "application_top.php").touch()
        (tmp_path / "admin" / "includes" / "functions").mkdir()
        (tmp_path / "admin" / "includes" / "functions" / "general.php").touch()

        result = detect_platform(tmp_path)
        assert result.name == "oscommerce"

    def test_detects_wordpress_via_wp_config(self, tmp_path: Path) -> None:
        """Should detect WordPress when wp-config.php is present."""
        (tmp_path / "wp-config.php").touch()
        (tmp_path / "wp-includes").mkdir(parents=True)
        (tmp_path / "wp-includes" / "functions.php").touch()

        result = detect_platform(tmp_path)
        assert result.name == "wordpress"

    def test_detects_wordpress_via_wp_load(self, tmp_path: Path) -> None:
        """Should detect WordPress when wp-load.php is present."""
        (tmp_path / "wp-load.php").touch()
        (tmp_path / "wp-content" / "themes" / "mytheme").mkdir(parents=True)
        (tmp_path / "wp-content" / "themes" / "mytheme" / "index.php").touch()

        result = detect_platform(tmp_path)
        assert result.name == "wordpress"

    def test_detects_zencart_via_configure(self, tmp_path: Path) -> None:
        """Should detect ZenCart when includes/configure.php is present."""
        (tmp_path / "includes").mkdir(parents=True)
        (tmp_path / "includes" / "configure.php").touch()
        (tmp_path / "includes" / "zen_cart_class.php").touch()

        result = detect_platform(tmp_path)
        assert result.name == "zencart"

    def test_detects_openmage_via_mage(self, tmp_path: Path) -> None:
        """Should detect OpenMage when app/Mage.php is present."""
        (tmp_path / "app").mkdir(parents=True)
        (tmp_path / "app" / "Mage.php").touch()
        (tmp_path / "app" / "code" / "core" / "Mage" / "Catalog" / "Model").mkdir(
            parents=True
        )
        (
            tmp_path
            / "app"
            / "code"
            / "core"
            / "Mage"
            / "Catalog"
            / "Model"
            / "Product.php"
        ).touch()

        result = detect_platform(tmp_path)
        assert result.name == "openmage"

    def test_detects_openmage_via_config(self, tmp_path: Path) -> None:
        """Should detect OpenMage when app/etc/config.php is present."""
        (tmp_path / "app" / "etc").mkdir(parents=True)
        (tmp_path / "app" / "etc" / "config.php").touch()
        (tmp_path / "app" / "code" / "community" / "Openwd" / "Review" / "Model").mkdir(
            parents=True
        )
        (
            tmp_path
            / "app"
            / "code"
            / "community"
            / "Openwd"
            / "Review"
            / "Model"
            / "Rating.php"
        ).touch()

        result = detect_platform(tmp_path)
        assert result.name == "openmage"

    def test_detects_prestashop_via_config_inc(self, tmp_path: Path) -> None:
        """Should detect PrestaShop when config/config.inc.php is present."""
        (tmp_path / "config").mkdir(parents=True)
        (tmp_path / "config" / "config.inc.php").touch()
        (tmp_path / "classes").mkdir(parents=True)
        (tmp_path / "classes" / "Product.php").touch()

        result = detect_platform(tmp_path)
        assert result.name == "prestashop"

    def test_detects_codeigniter_via_core(self, tmp_path: Path) -> None:
        """Should detect CodeIgniter when system/core/CodeIgniter.php is present."""
        (tmp_path / "system" / "core").mkdir(parents=True)
        (tmp_path / "system" / "core" / "CodeIgniter.php").touch()
        (tmp_path / "application" / "controllers").mkdir(parents=True)
        (tmp_path / "application" / "controllers" / "Welcome.php").touch()

        result = detect_platform(tmp_path)
        assert result.name == "codeigniter"

    def test_detects_codeigniter_via_config(self, tmp_path: Path) -> None:
        """Should detect CodeIgniter when application/config/config.php is present."""
        (tmp_path / "application" / "config").mkdir(parents=True)
        (tmp_path / "application" / "config" / "config.php").touch()
        (tmp_path / "application" / "models").mkdir(parents=True)
        (tmp_path / "application" / "models" / "User_model.php").touch()

        result = detect_platform(tmp_path)
        assert result.name == "codeigniter"

    def test_detects_suitecrm_via_entry_point(self, tmp_path: Path) -> None:
        """Should detect SuiteCRM when include/entryPoint.php is present."""
        (tmp_path / "include").mkdir(parents=True)
        (tmp_path / "include" / "entryPoint.php").touch()
        (tmp_path / "modules" / "Accounts").mkdir(parents=True)
        (tmp_path / "modules" / "Accounts" / "Account.php").touch()

        result = detect_platform(tmp_path)
        assert result.name == "suitecrm"

    def test_marker_file_partial_match(self, tmp_path: Path) -> None:
        """Should detect platform when marker is partial path match."""
        (tmp_path / "myproject" / "admin" / "includes").mkdir(parents=True)
        (tmp_path / "myproject" / "admin" / "includes" / "application_top.php").touch()
        (tmp_path / "myproject" / "includes" / "functions").mkdir(parents=True)
        (tmp_path / "myproject" / "includes" / "functions" / "html_output.php").touch()

        result = detect_platform(tmp_path)
        assert result.name == "oscommerce"


class TestDetectPlatformMarkerPatternFallback:
    """Test suite for marker pattern fallback detection."""

    def test_fallback_to_wordpress_via_pattern(self, tmp_path: Path) -> None:
        """Should detect WordPress via marker patterns when no marker files found."""
        # WordPress patterns: $wpdb->, add_action, add_filter, wp_
        (tmp_path / "wp-content" / "plugins" / "my-plugin").mkdir(parents=True)
        (tmp_path / "wp-content" / "plugins" / "my-plugin" / "main.php").write_text(
            "<?php\nadd_action('init', function() {});\n"
        )
        (tmp_path / "wp-content" / "themes" / "mytheme").mkdir(parents=True)
        (tmp_path / "wp-content" / "themes" / "mytheme" / "functions.php").write_text(
            "<?php\nadd_filter('the_content', 'my_filter');\n"
        )

        result = detect_platform(tmp_path)
        assert result.name == "wordpress"

    def test_fallback_requires_multiple_pattern_matches(self, tmp_path: Path) -> None:
        """Should require at least 2 pattern matches for fallback detection."""
        # Single pattern match should not detect platform
        (tmp_path / "some" / "path").mkdir(parents=True)
        (tmp_path / "some" / "path" / "wp_test.php").write_text(
            "<?php\n// Single wp_ pattern\n"
        )

        result = detect_platform(tmp_path)
        # With only 1 match, should fall back to generic_php
        assert result.name == "generic_php"

    def test_fallback_with_tep_patterns(self, tmp_path: Path) -> None:
        """Should detect osCommerce via tep_ patterns in fallback."""
        # osCommerce patterns: tep_db_query, tep_session_register, DIR_WS_INCLUDES
        (tmp_path / "catalog" / "functions").mkdir(parents=True)
        (tmp_path / "catalog" / "functions" / "tep_db_query_helper.php").write_text(
            "<?php\nfunction tep_db_query($sql) { return mysql_query($sql); }\n"
        )
        (
            tmp_path / "catalog" / "functions" / "tep_session_register_handler.php"
        ).write_text("<?php\nfunction tep_session_register($var) { return true; }\n")
        (tmp_path / "catalog" / "classes").mkdir(parents=True)
        (tmp_path / "catalog" / "classes" / "tep_database.php").write_text(
            "<?php\ndefine('DIR_WS_INCLUDES', 'includes/');\n"
        )

        result = detect_platform(tmp_path)
        # This should match osCommerce via pattern fallback
        assert result.name == "oscommerce"


class TestDetectPlatformGenericFallback:
    """Test suite for generic_php fallback detection."""

    def test_fallback_to_generic_php_empty_dir(self, tmp_path: Path) -> None:
        """Should return generic_php when no PHP files found."""
        # Empty directory
        result = detect_platform(tmp_path)
        assert result.name == "generic_php"

    def test_fallback_to_generic_php_no_markers(self, tmp_path: Path) -> None:
        """Should return generic_php when no platform markers found."""
        (tmp_path / "src" / "Controller").mkdir(parents=True)
        (tmp_path / "src" / "Controller" / "UserController.php").write_text(
            "<?php\nclass UserController {}\n"
        )
        (tmp_path / "src" / "Model").mkdir(parents=True)
        (tmp_path / "src" / "Model" / "User.php").write_text("<?php\nclass User {}\n")
        (tmp_path / "src" / "Service").mkdir(parents=True)
        (tmp_path / "src" / "Service" / "UserService.php").write_text(
            "<?php\nclass UserService {}\n"
        )

        result = detect_platform(tmp_path)
        assert result.name == "generic_php"

    def test_fallback_to_generic_php_unknown_files(self, tmp_path: Path) -> None:
        """Should return generic_php for unknown PHP files."""
        (tmp_path / "app" / "Http" / "Controllers").mkdir(parents=True)
        (tmp_path / "app" / "Http" / "Controllers" / "HomeController.php").write_text(
            "<?php\nclass HomeController {}\n"
        )
        (tmp_path / "vendor" / "some" / "package" / "src").mkdir(parents=True)
        (tmp_path / "vendor" / "some" / "package" / "src" / "Class.php").write_text(
            "<?php\nclass VendorClass {}\n"
        )

        result = detect_platform(tmp_path)
        assert result.name == "generic_php"


class TestDetectPlatformOsCommercePhoenix:
    """Test suite for osCommerce Phoenix detection."""

    def test_detects_oscommerce_phoenix(self, tmp_path: Path) -> None:
        """Should detect osCommerce Phoenix when OSC/OM/ is present."""
        (tmp_path / "includes" / "OSC" / "OM").mkdir(parents=True)
        (tmp_path / "includes" / "OSC" / "OM" / "Registry.php").touch()
        (tmp_path / "includes" / "OSC" / "OM" / "Modules").mkdir(parents=True)
        (
            tmp_path / "includes" / "OSC" / "OM" / "Modules" / "ModuleInterface.php"
        ).touch()

        result = detect_platform(tmp_path)
        assert result.name == "oscommerce_phoenix"


class TestGetPlatformProfile:
    """Test suite for get_platform_profile factory function."""

    def test_get_oscommerce_profile(self) -> None:
        """Should return osCommerce profile."""
        profile = get_platform_profile("oscommerce")
        assert profile.name == "oscommerce"
        assert "includes/application_top.php" in profile.marker_files

    def test_get_wordpress_profile(self) -> None:
        """Should return WordPress profile."""
        profile = get_platform_profile("wordpress")
        assert profile.name == "wordpress"
        assert "wp-config.php" in profile.marker_files

    def test_get_generic_php_profile(self) -> None:
        """Should return generic PHP profile."""
        profile = get_platform_profile("generic_php")
        assert profile.name == "generic_php"
        assert profile.marker_files == ()
        assert profile.marker_patterns == ()

    def test_get_all_platforms(self) -> None:
        """Should have all expected platforms in registry."""
        expected_platforms = {
            "oscommerce",
            "oscommerce_phoenix",
            "wordpress",
            "zencart",
            "openmage",
            "prestashop",
            "codeigniter",
            "suitecrm",
            "generic_php",
        }
        assert set(PLATFORM_REGISTRY.keys()) == expected_platforms


class TestPlatformProfileProperties:
    """Test suite for PlatformProfile properties."""

    def test_has_marker_files_true(self) -> None:
        """Should return True when profile has marker files."""
        profile = get_platform_profile("oscommerce")
        assert profile.has_marker_files is True

    def test_has_marker_files_false_for_generic(self) -> None:
        """Should return False for generic_php with no marker files."""
        profile = get_platform_profile("generic_php")
        assert profile.has_marker_files is False

    def test_has_marker_patterns_true(self) -> None:
        """Should return True when profile has marker patterns."""
        profile = get_platform_profile("oscommerce")
        assert profile.has_marker_patterns is True

    def test_has_marker_patterns_false_for_generic(self) -> None:
        """Should return False for generic_php with no marker patterns."""
        profile = get_platform_profile("generic_php")
        assert profile.has_marker_patterns is False


class TestPlatformProfileExclusion:
    """Test suite for is_excluded_path method."""

    def test_excludes_vendor_directory(self) -> None:
        """Should exclude paths in vendor/ directory."""
        profile = get_platform_profile("generic_php")
        assert profile.is_excluded_path("vendor/autoload.php") is True

    def test_excludes_node_modules(self) -> None:
        """Should exclude paths in node_modules/ directory."""
        profile = get_platform_profile("generic_php")
        assert profile.is_excluded_path("node_modules/package/index.js") is True

    def test_excludes_cache(self) -> None:
        """Should exclude paths in cache/ directory."""
        profile = get_platform_profile("generic_php")
        assert profile.is_excluded_path("cache/templates_c/index.php") is True

    def test_does_not_exclude_valid_path(self) -> None:
        """Should not exclude valid application paths."""
        profile = get_platform_profile("generic_php")
        assert profile.is_excluded_path("app/Controller/UserController.php") is False

    def test_excludes_wp_content_uploads(self) -> None:
        """Should exclude WordPress upload directories."""
        profile = get_platform_profile("wordpress")
        assert profile.is_excluded_path("wp-content/uploads/2024/01/image.jpg") is True

    def test_excludes_mage_var(self) -> None:
        """Should exclude Magento var directory."""
        profile = get_platform_profile("openmage")
        assert profile.is_excluded_path("var/log/system.log") is True

    def test_excludes_mage_skin(self) -> None:
        """Should exclude Magento skin directory."""
        profile = get_platform_profile("openmage")
        assert (
            profile.is_excluded_path("skin/frontend/default/mytheme/style.css") is True
        )
