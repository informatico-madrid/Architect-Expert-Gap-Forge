# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
PHP Platform Profiles Module
===========================
Provides platform-specific profile definitions for PHP legacy code detection.

This module defines the PlatformProfile dataclass for representing platform-
specific patterns and markers used to identify and classify PHP legacy codebases
(osCommerce, WordPress, ZenCart, OpenMage, PrestaShop, CodeIgniter, SuiteCRM).

Author: Joao Maria Arranz Aparicio
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# Platform Profile Registry
# ---------------------------------------------------------------------------
# Predefined platform profiles for common PHP legacy platforms
# These profiles contain marker files, patterns, and signature patterns
# specific to each platform

# osCommerce profile - classic e-commerce platform
OSCOMMERCE_PROFILE = {
    "name": "oscommerce",
    "marker_files": (
        "includes/application_top.php",
        "admin/includes/application_top.php",
    ),
    "marker_patterns": (r"tep_db_query", r"tep_session_register", r"DIR_WS_INCLUDES"),
    "exclude_dirs": (
        "vendor/",
        "node_modules/",
        "cache/",
        "images/",
        "includes/languages/",
    ),
    "snippet_path": "configs/stage_2_factory/taxonomy/php_legacy/snippets/oscommerce.md",
    "signature_patterns": {
        "PERSISTENCE_SMELL": [
            ("tep_db_query", r"tep_db_query\s*\("),
            ("tep_db_perform", r"tep_db_perform\s*\("),
            ("tep_session_find", r"tep_session_find\s*\("),
        ],
        "STATE_POLLUTION": [
            ("tep_session_register", r"tep_session_register\s*\("),
            ("global_cart", r"global\s+\$cart"),
            ("global_customer", r"global\s+\$customer"),
        ],
    },
}

# osCommerce Phoenix (modernized fork)
OSCOMMERCE_PHOENIX_PROFILE = {
    "name": "oscommerce_phoenix",
    "marker_files": ("includes/OSC/OM/",),
    "marker_patterns": (r"OSC\\OM\\Registry", r"use OSC\\OM"),
    "exclude_dirs": ("vendor/", "node_modules/", "cache/"),
    "snippet_path": "configs/stage_2_factory/taxonomy/php_legacy/snippets/oscommerce.md",
    "signature_patterns": {
        "MODERN_HYBRID": [
            ("OSC_OM_Registry", r"OSC\\OM\\Registry"),
            ("use_statement", r"use OSC\\OM"),
        ],
    },
}

# WordPress profile
WORDPRESS_PROFILE = {
    "name": "wordpress",
    "marker_files": ("wp-config.php", "wp-load.php"),
    "marker_patterns": (r"\$wpdb->", r"add_action", r"add_filter", r"wp_"),
    "exclude_dirs": ("vendor/", "node_modules/", "cache/", "wp-content/uploads/"),
    "snippet_path": "configs/stage_2_factory/taxonomy/php_legacy/snippets/wordpress.md",
    "signature_patterns": {
        "PERSISTENCE_SMELL": [
            ("wpdb_query", r"\$wpdb->query\s*\("),
            ("wpdb_prepare", r"\$wpdb->prepare\s*\("),
            ("wpdb_get_results", r"\$wpdb->get_results\s*\("),
        ],
        "STATE_POLLUTION": [
            ("wp_session", r"\$_SESSION\s*\["),
        ],
    },
}

# ZenCart profile
ZENCART_PROFILE = {
    "name": "zencart",
    "marker_files": ("includes/configure.php",),
    "marker_patterns": (r"\bzen_", r"DIR_WS_INCLUDES", r"DIR_FS_CATALOG"),
    "exclude_dirs": ("vendor/", "node_modules/", "cache/", "images/"),
    "snippet_path": "configs/stage_2_factory/taxonomy/php_legacy/snippets/zencart.md",
    "signature_patterns": {
        "PERSISTENCE_SMELL": [
            ("zen_db_perform", r"zen_db_perform\s*\("),
            ("zen_db_query", r"zen_db_query\s*\("),
        ],
        "STATE_POLLUTION": [
            ("zen_redirect", r"zen_redirect\s*\("),
            ("zen_session", r"zen_session_\w+\s*\("),
        ],
    },
}

# OpenMage (Magento 1 fork)
OPENMAGE_PROFILE = {
    "name": "openmage",
    "marker_files": ("app/Mage.php", "app/etc/config.php"),
    "marker_patterns": (r"Mage::", r"Varien_", r"Mage_"),
    "exclude_dirs": ("vendor/", "node_modules/", "var/", "skin/", "media/"),
    "snippet_path": "configs/stage_2_factory/taxonomy/php_legacy/snippets/openmage.md",
    "signature_patterns": {
        "PERSISTENCE_SMELL": [
            ("Mage_getModel", r"Mage::getModel\s*\("),
            ("Mage_getSingleton", r"Mage::getSingleton\s*\("),
            ("Mage_getResourceModel", r"Mage::getResourceModel\s*\("),
        ],
        "STATE_POLLUTION": [
            ("Mage_register", r"Mage::register\s*\("),
            ("Mage_unregister", r"Mage::unregister\s*\("),
        ],
    },
}

# PrestaShop profile
PRESTASHOP_PROFILE = {
    "name": "prestashop",
    "marker_files": ("config/config.inc.php",),
    "marker_patterns": (
        r"PS_VERSION",
        r"Db::getInstance",
        r"Context::getContext",
        r"Tools::",
    ),
    "exclude_dirs": ("vendor/", "node_modules/", "cache/", "modules/"),
    "snippet_path": "configs/stage_2_factory/taxonomy/php_legacy/snippets/prestashop.md",
    "signature_patterns": {
        "PERSISTENCE_SMELL": [
            ("Db_getInstance", r"Db::getInstance\s*\("),
            ("Db_Execute", r"Db::getInstance\s*->\s*execute"),
        ],
        "STATE_POLLUTION": [
            ("Context_getContext", r"Context::getContext\s*\("),
        ],
    },
}

# CodeIgniter profile
CODEIGNITER_PROFILE = {
    "name": "codeigniter",
    "marker_files": ("system/core/CodeIgniter.php", "application/config/config.php"),
    "marker_patterns": (r"CI_Controller", r"CI_Model", r"\$this->db"),
    "exclude_dirs": ("vendor/", "node_modules/", "cache/", "system/"),
    "snippet_path": "configs/stage_2_factory/taxonomy/php_legacy/snippets/codeigniter.md",
    "signature_patterns": {
        "PERSISTENCE_SMELL": [
            ("CI_db_query", r"\$this->db->query\s*\("),
            ("CI_db_select", r"\$this->db->select\s*\("),
        ],
        "STATE_POLLUTION": [
            ("CI_session", r"\$this->session\s*\("),
        ],
    },
}

# SuiteCRM profile
SUITECRM_PROFILE = {
    "name": "suitecrm",
    "marker_files": ("include/entryPoint.php", "config.php"),
    "marker_patterns": (r"SugarBean", r"DBManager", r"BeanFactory"),
    "exclude_dirs": ("vendor/", "node_modules/", "cache/", "upload/"),
    "snippet_path": "configs/stage_2_factory/taxonomy/php_legacy/snippets/suitecrm.md",
    "signature_patterns": {
        "PERSISTENCE_SMELL": [
            ("SugarBean_retrieve", r"SugarBean::retrieve\s*\("),
            ("DBManager_query", r"DBManager\s*::\s*query"),
        ],
        "STATE_POLLUTION": [
            ("BeanFactory_getBean", r"BeanFactory::getBean\s*\("),
        ],
    },
}

# Generic PHP fallback profile
GENERIC_PHP_PROFILE = {
    "name": "generic_php",
    "marker_files": (),
    "marker_patterns": (),
    "exclude_dirs": ("vendor/", "node_modules/", "cache/"),
    "snippet_path": "configs/stage_2_factory/taxonomy/php_legacy/snippets/generic_php.md",
    "signature_patterns": {
        "PERSISTENCE_SMELL": [
            ("mysql_query", r"mysql_query\s*\("),
            ("mysqli_query", r"mysqli_query\s*\("),
            ("pg_query", r"pg_query\s*\("),
        ],
        "STATE_POLLUTION": [
            ("global_var", r"global\s+\$\w+"),
            ("session_access", r"\$_SESSION\s*\["),
        ],
    },
}


# Registry of all platform profiles
PLATFORM_REGISTRY: dict[str, dict] = {
    "oscommerce": OSCOMMERCE_PROFILE,
    "oscommerce_phoenix": OSCOMMERCE_PHOENIX_PROFILE,
    "wordpress": WORDPRESS_PROFILE,
    "zencart": ZENCART_PROFILE,
    "openmage": OPENMAGE_PROFILE,
    "prestashop": PRESTASHOP_PROFILE,
    "codeigniter": CODEIGNITER_PROFILE,
    "suitecrm": SUITECRM_PROFILE,
    "generic_php": GENERIC_PHP_PROFILE,
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class PlatformProfile:
    """
    Represents a platform-specific profile for PHP legacy code detection.

    A platform profile contains marker files, regex patterns, and signature
    patterns specific to a PHP platform (osCommerce, WordPress, ZenCart, etc.)
    used for auto-detection and platform-specific pattern matching.

    Attributes:
        name: Platform identifier (e.g., 'oscommerce', 'wordpress')
        marker_files: Tuple of file paths that indicate this platform
        marker_patterns: Tuple of regex patterns for platform detection
        exclude_dirs: Tuple of directory patterns to exclude from processing
        snippet_path: Path to the platform-specific doctrine snippet
        signature_patterns: Dict mapping categories to pattern tuples,
            coerced to MappingProxyType at runtime for immutability
    """

    name: str
    marker_files: tuple[str, ...]
    marker_patterns: tuple[str, ...]
    exclude_dirs: tuple[str, ...]
    snippet_path: str
    signature_patterns: dict[str, str]

    def __post_init__(self) -> None:
        """Validate fields and coerce signature_patterns to MappingProxyType."""
        # Validate name is not empty
        if not self.name:
            raise ValueError("name must be a non-empty string")

        # Coerce signature_patterns dict to MappingProxyType for immutability at runtime
        # Using object.__setattr__ to bypass frozen dataclass restriction
        if not isinstance(self.signature_patterns, MappingProxyType):
            object.__setattr__(
                self, "signature_patterns", MappingProxyType(self.signature_patterns)
            )

    @property
    def has_marker_files(self) -> bool:
        """Return True if this profile has marker files defined."""
        return len(self.marker_files) > 0

    @property
    def has_marker_patterns(self) -> bool:
        """Return True if this profile has marker patterns defined."""
        return len(self.marker_patterns) > 0

    def is_excluded_path(self, path: str) -> bool:
        """
        Check if a path should be excluded based on exclude_dirs.

        Args:
            path: The file path to check

        Returns:
            True if the path matches any exclude pattern
        """
        for exclude_pattern in self.exclude_dirs:
            if exclude_pattern.rstrip("/") in path:
                return True
        return False


# ---------------------------------------------------------------------------
# Platform Profile Factory
# ---------------------------------------------------------------------------
def get_platform_profile(name: str) -> PlatformProfile:
    """
    Get a platform profile by name.

    Args:
        name: Platform name (e.g., 'oscommerce', 'wordpress')

    Returns:
        PlatformProfile instance for the specified platform

    Raises:
        KeyError: If platform name is not found in registry
    """
    profile_dict = PLATFORM_REGISTRY[name]
    return PlatformProfile(
        name=profile_dict["name"],
        marker_files=profile_dict["marker_files"],
        marker_patterns=profile_dict["marker_patterns"],
        exclude_dirs=profile_dict["exclude_dirs"],
        snippet_path=profile_dict["snippet_path"],
        signature_patterns=profile_dict["signature_patterns"],
    )


def get_all_platform_names() -> tuple[str, ...]:
    """
    Get names of all available platforms.

    Returns:
        Tuple of platform names
    """
    return tuple(PLATFORM_REGISTRY.keys())


# ---------------------------------------------------------------------------
# Platform Detection
# ---------------------------------------------------------------------------
def detect_platform(repo_path: Path) -> PlatformProfile:
    """
    Detect the platform for a PHP repository.

    Checks marker files first, then falls back to marker pattern scanning
    on top 20 PHP files by content. Defaults to generic_php if no platform detected.

    Args:
        repo_path: Root path of the repository (Path object)

    Returns:
        Detected PlatformProfile instance
    """
    import re

    from src.discovery.php_fragmenter import read_php_file

    # Find all PHP files in the repository
    php_file_paths: list[Path] = []
    try:
        php_file_paths = list(repo_path.rglob("*.php"))
    except (OSError, PermissionError) as e:
        logger.warning("Could not scan for PHP files in %s: %s", repo_path, e)

    # Convert to relative paths for marker file detection
    php_files_relative: list[str] = [
        str(p.relative_to(repo_path)) for p in php_file_paths
    ]

    # First pass: check for marker files
    for platform_name, profile_dict in PLATFORM_REGISTRY.items():
        if platform_name == "generic_php":
            continue  # Skip generic in first pass

        marker_files = profile_dict.get("marker_files", ())
        for marker in marker_files:
            # Check in the php_files list (they are relative paths)
            for php_file in php_files_relative:
                if marker in php_file or php_file.endswith(marker):
                    return get_platform_profile(platform_name)

    # Second pass: scan for marker patterns in file content (limit to top 20 files)
    for platform_name, profile_dict in PLATFORM_REGISTRY.items():
        if platform_name == "generic_php":
            continue

        marker_patterns = profile_dict.get("marker_patterns", ())
        if not marker_patterns:
            continue

        # Sort by file size (smallest first) to get consistent results
        # and take top 20
        sorted_files = sorted(
            php_file_paths, key=lambda p: p.stat().st_size if p.exists() else 0
        )
        files_to_scan = sorted_files[:20]

        match_count = 0
        for php_file in files_to_scan:
            if not php_file.exists():
                continue

            try:
                content = read_php_file(php_file)
            except Exception as e:
                logger.warning("Could not read PHP file %s: %s", php_file, e)
                continue

            for pattern in marker_patterns:
                if re.search(pattern, content):
                    match_count += 1
                    if match_count >= 2:  # Require at least 2 pattern matches
                        return get_platform_profile(platform_name)

    # Default to generic_php
    return get_platform_profile("generic_php")


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)
