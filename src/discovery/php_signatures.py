# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
PHP Legacy Signatures Module
=============================
Provides legacy pattern detection for PHP files using regex-based signature scanning.

This module defines the SIGNATURE_CATEGORY enum and LegacySignature dataclass
for representing detected technical debt patterns in legacy PHP code.

Author: Joao Maria Arranz Aparicio
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Tuple

if TYPE_CHECKING:
    from types import MappingProxyType

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class SignatureCategory(Enum):
    """
    Categories of legacy code signatures detected in PHP fragments.

    Each category represents a specific type of technical debt or
    modernization pattern found in legacy PHP codebases.
    """

    # Database access patterns
    PERSISTENCE_SMELL = "PERSISTENCE_SMELL"

    # Global state usage
    STATE_POLLUTION = "STATE_POLLUTION"

    # Include/require patterns
    MODULE_LINK_SMELL = "MODULE_LINK_SMELL"

    # Security vulnerabilities
    SECURITY_VULN = "SECURITY_VULN"

    # Hardcoded constants
    CONSTANT_POLLUTION = "CONSTANT_POLLUTION"

    # Modern PHP patterns (indicates partially modernized code)
    MODERN_HYBRID = "MODERN_HYBRID"


class Severity(Enum):
    """Severity levels for detected signatures."""

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


# ---------------------------------------------------------------------------
# Signature Pattern Library
# ---------------------------------------------------------------------------
# Maps category to list of (pattern_name, regex_pattern) tuples
SIGNATURE_PATTERNS: dict[str, list[tuple[str, str]]] = {
    "PERSISTENCE_SMELL": [
        ("mysql_query", r"mysql_query\s*\("),
        ("tep_db_query", r"tep_db_query\s*\("),
        ("wpdb_query", r"\$wpdb->query\s*\("),
        ("wpdb_prepare", r"\$wpdb->prepare\s*\("),
        ("wpdb_get_results", r"\$wpdb->get_results\s*\("),
        ("zen_db_perform", r"zen_db_perform\s*\("),
        ("Mage_getModel", r"Mage::getModel\s*\("),
        ("db_query", r"\$db->query\s*\("),
    ],
    "STATE_POLLUTION": [
        ("global_var", r"global\s+\$\w+"),
        ("session_access", r"\$_SESSION\s*\["),
        ("cookie_access", r"\$_COOKIE\s*\["),
        ("globals_access", r"\$GLOBALS\s*\["),
        ("tep_session_register", r"tep_session_register\s*\("),
        ("tep_redirect", r"\btep_redirect\s*\("),
        ("post_access", r"\$_POST\s*\["),
        ("get_access", r"\$_GET\s*\["),
        ("request_access", r"\$_REQUEST\s*\["),
    ],
    "MODULE_LINK_SMELL": [
        ("include", r"\binclude\b(?!_once)"),
        ("include_once", r"\binclude_once\b"),
        ("require", r"\brequire\b(?!_once)"),
        ("require_once", r"\brequire_once\b"),
        ("path_concat_include", r"include\s*\.\s*['\"]"),
    ],
    "SECURITY_VULN": [
        ("concat_sql", r"mysql_query\s*[^;]*\.\s*[\"']"),
        ("echo_get", r"echo\s+\$_(GET|POST|REQUEST)\s*\["),
        ("eval_usage", r"eval\s*\("),
        ("dynamic_include", r"include\s*\$\w+"),
        ("preg_replace_eval", r"preg_replace\s*\([^,]+,\s*/(e|eval)"),
        ("ajax_referer_no_die", r"\bcheck_ajax_referer\s*\("),
        ("unescaped_json_error", r"\bwp_send_json_error\s*\("),
    ],
    "CONSTANT_POLLUTION": [
        ("define", r"define\s*\("),
        ("dir_ws_constant", r"DIR_WS_\w+"),
        ("dir_fs_constant", r"DIR_FS_\w+"),
        ("table_constant", r"TABLE_\w+"),
    ],
    "MODERN_HYBRID": [
        ("namespace", r"namespace\s+\w+"),
        ("use_statement", r"^use\s+\w+"),
        ("class_extends", r"class\s+\w+\s+extends"),
        ("class_implements", r"class\s+\w+\s+implements"),
        ("php8_construct", r"->__construct\s*\("),
        ("add_action", r"\badd_action\s*\("),
        ("add_filter", r"\badd_filter\s*\("),
        ("apply_filters", r"\bapply_filters\s*\("),
        ("register_hook", r"\bregister_activation_hook\s*\("),
    ],
}


# Map category to default severity
CATEGORY_SEVERITY: dict[str, str] = {
    "SECURITY_VULN": "critical",
    "PERSISTENCE_SMELL": "warning",
    "STATE_POLLUTION": "warning",
    "MODULE_LINK_SMELL": "info",
    "CONSTANT_POLLUTION": "info",
    "MODERN_HYBRID": "info",
}


# Modern equivalent hints for each pattern
MODERN_EQUIVALENTS: dict[str, str] = {
    # Persistence
    "mysql_query": "Use PDO or Doctrine DBAL with prepared statements",
    "tep_db_query": "Use Doctrine QueryBuilder or Repository pattern",
    "wpdb_query": "Use $wpdb->prepare() with $wpdb->get_results() or Doctrine DBAL",
    "wpdb_prepare": "Use $wpdb->prepare() with placeholders for SQL injection prevention",
    "wpdb_get_results": "Use WP_Query or custom query with proper escaping",
    "zen_db_perform": "Use Doctrine ORM with entity managers",
    "Mage_getModel": "Use Magento 2 dependency injection with interfaces",
    "db_query": "Use ORM or Query Builder pattern",
    # State
    "global_var": "Use dependency injection or service container",
    "session_access": "Use Symfony Session or PSR-7 session handling",
    "cookie_access": "Use Symfony Cookie component with secure settings",
    "globals_access": "Avoid $GLOBALS, use proper parameter passing",
    "tep_session_register": "Use Symfony Session or PSR-7 session management",
    "tep_redirect": "Use Symfony HttpFoundation RedirectResponse",
    "post_access": "Validate and sanitize $_POST via request object abstraction",
    "get_access": "Validate and sanitize $_GET via request object abstraction",
    "request_access": "Validate and sanitize $_REQUEST via PSR-7 ServerRequest",
    # Module links
    "include": "Use PSR-4 autoloading with dependency injection",
    "include_once": "Use PSR-4 autoloading",
    "require": "Use PSR-4 autoloading with dependency injection",
    "require_once": "Use PSR-4 autoloading",
    "path_concat_include": "Use Composer autoloading with proper namespaces",
    # Security
    "concat_sql": "Use prepared statements/parameterized queries",
    "echo_get": "Use template engines with auto-escaping or htmlspecialchars()",
    "eval_usage": "Never use eval(), redesign the code logic",
    "dynamic_include": "Use dependency injection or service container",
    "preg_replace_eval": "Use preg_replace_callback() instead of /e modifier",
    "ajax_referer_no_die": "Use check_ajax_referer() with wp_die() or add true as third arg",
    "unescaped_json_error": "Sanitize error messages before returning to client",
    # Constants
    "define": "Use environment variables (.env) or configuration services",
    "dir_ws_constant": "Use Symfony parameter bag or .env files",
    "dir_fs_constant": "Use Symfony parameter bag or .env files",
    "table_constant": "Use Doctrine entity mappings or configuration",
    # Modern
    "namespace": "Good - continue modernization with Composer",
    "use_statement": "Good - continue modernization with proper imports",
    "class_extends": "Consider composition over inheritance",
    "class_implements": "Good - use interfaces for abstraction",
    "php8_construct": "Good - use constructor injection",
    "add_action": "Good - WordPress hook; consider Symfony EventDispatcher for DI-friendly alternative",
    "add_filter": "Good - WordPress hook; consider Symfony EventDispatcher for DI-friendly alternative",
    "apply_filters": "Good - WordPress filter; encapsulate in a service for testability",
    "register_hook": "Good - activation hook; consider Symfony bundle configuration",
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class LegacySignature:
    """
    Represents a legacy code signature detected in a PHP fragment.

    A signature is a specific pattern of technical debt or modernization
    marker found in the source code, such as deprecated database calls,
    global state usage, or security vulnerabilities.

    Attributes:
        pattern_name: Identifier for the specific pattern (e.g., 'tep_db_query')
        category: SIGNATURE_CATEGORY enum value (e.g., 'PERSISTENCE_SMELL')
        matched_text: The actual text matched from the source code
        line_number: Line number where the pattern was detected (1-indexed)
        severity: Impact level (critical|warning|info)
        modern_equivalent: Suggested modern replacement for this pattern
    """

    pattern_name: str
    category: str
    matched_text: str
    line_number: int
    severity: str
    modern_equivalent: str

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        # Validate category against enum values
        valid_categories = {cat.value for cat in SignatureCategory}
        if self.category not in valid_categories:
            raise ValueError(
                f"category must be one of {valid_categories}, got '{self.category}'"
            )

        # Validate severity against allowed values
        valid_severities = {sev.value for sev in Severity}
        if self.severity not in valid_severities:
            raise ValueError(
                f"severity must be one of {valid_severities}, got '{self.severity}'"
            )

        # Validate line_number is positive
        if self.line_number < 1:
            raise ValueError(
                f"line_number must be >= 1, got {self.line_number}"
            )

    @property
    def is_critical(self) -> bool:
        """Return True if this signature has critical severity."""
        return self.severity == Severity.CRITICAL.value

    @property
    def is_warning(self) -> bool:
        """Return True if this signature has warning severity."""
        return self.severity == Severity.WARNING.value

    @property
    def is_info(self) -> bool:
        """Return True if this signature has info severity."""
        return self.severity == Severity.INFO.value


# ---------------------------------------------------------------------------
# Type Aliases
# ---------------------------------------------------------------------------
LegacySignatureTuple = Tuple[LegacySignature, ...]


# ---------------------------------------------------------------------------
# Core Functions
# ---------------------------------------------------------------------------
def scan_signatures(
    content: str,
    platform_patterns: MappingProxyType | None = None
) -> list[LegacySignature]:
    """
    Scan PHP content for legacy code signatures.

    Args:
        content: The PHP source code to scan
        platform_patterns: Optional platform-specific patterns to include

    Returns:
        List of LegacySignature instances found in the content
    """
    signatures: list[LegacySignature] = []
    lines = content.split('\n')

    # Combine base patterns with platform-specific patterns
    all_patterns: dict[str, list[tuple[str, str]]] = SIGNATURE_PATTERNS.copy()

    if platform_patterns:
        # Add platform-specific patterns (these take precedence)
        for category, patterns in platform_patterns.items():
            if category in all_patterns:
                all_patterns[category].extend(patterns)
            else:
                all_patterns[category] = patterns

    # Scan each line for patterns
    for line_num, line in enumerate(lines, start=1):
        for category, pattern_list in all_patterns.items():
            for pattern_name, pattern_str in pattern_list:
                try:
                    if re.search(pattern_str, line):
                        severity = CATEGORY_SEVERITY.get(category, "info")
                        modern_equiv = MODERN_EQUIVALENTS.get(pattern_name, "Review and modernize")

                        sig = LegacySignature(
                            pattern_name=pattern_name,
                            category=category,
                            matched_text=line.strip(),
                            line_number=line_num,
                            severity=severity,
                            modern_equivalent=modern_equiv
                        )
                        signatures.append(sig)
                except re.error as e:
                    logger.warning(f"Invalid regex pattern '{pattern_str}': {e}")
                    continue

    return signatures


def format_legacy_signatures_section(
    sigs: list[LegacySignature]
) -> str:
    """
    Format legacy signatures for bundle output.

    Produces the multi-line key:value bundle-level format defined in
    contracts/bundle-format.md §[LEGACY_SIGNATURES].

    Args:
        sigs: List of LegacySignature instances to format

    Returns:
        Formatted signatures section string
    """
    if not sigs:
        return ""

    blocks: list[str] = []
    for sig in sigs:
        block = (
            f"CATEGORY: {sig.category}\n"
            f"PATTERN: {sig.pattern_name} — {sig.matched_text[:80]}\n"
            f"SEVERITY: {sig.severity}\n"
            f"MODERN_HINT: {sig.modern_equivalent}"
        )
        blocks.append(block)

    return "\n---\n".join(blocks)


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)
