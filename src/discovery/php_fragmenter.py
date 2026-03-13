# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
PHP Legacy Fragmenter Module
==============================
Provides PHP legacy code fragmentation functionality for the AEGF processor.
Handles extraction of PHP fragments from legacy PHP files (osCommerce, WordPress,
ZenCart, etc.) using regex-based heuristics.

This module defines the core dataclasses for representing PHP fragments and
their implicit dependencies, following the frozen dataclass pattern per
AEGF Constitution requirements.

Author: Joao Maria Arranz Aparicio
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Tuple

# Forward reference to avoid circular import - LegacySignature defined in php_signatures.py (T006)
if TYPE_CHECKING:
    from src.discovery.php_signatures import LegacySignature

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class FragmentType(Enum):
    """PHP fragment type classification based on code structure."""

    FUNCTION = "function"
    CLASS = "class"
    SWITCH_BLOCK = "switch_block"
    BOOTSTRAP = "bootstrap"
    MIXED_HTML = "mixed_html"
    CATCHALL = "catchall"


class LegacyAction(Enum):
    """LEGACY_ACTION names for switch/case blocks and bootstrap code."""

    # Generic actions
    INITIALIZE = "initialize"
    PROCESS = "process"
    DISPLAY = "display"
    SAVE = "save"
    DELETE = "delete"
    UPDATE = "update"
    LIST = "list"
    VIEW = "view"
    EDIT = "edit"
    ADD = "add"
    REMOVE = "remove"

    # osCommerce-specific
    OSC_CATEGORIES = "categories"
    OSC_PRODUCTS = "products"
    OSC_CUSTOMERS = "customers"
    OSC_ORDERS = "orders"
    OSC_CHECKOUT = "checkout"

    # WordPress-specific
    WP_AJAX = "wp_ajax"
    WP_REST = "wp_rest"
    WP_ADMIN = "wp_admin"
    WP_FRONTEND = "wp_frontend"

    # ZenCart-specific
    ZEN_CUSTOMERS = "zen_customers"
    ZEN_ORDERS = "zen_orders"
    ZEN_PRODUCTS = "zen_products"


class DependencyType(Enum):
    """Types of implicit dependencies detected in PHP fragments."""

    GLOBAL_VAR = "global_var"
    CONSTANT = "constant"
    FUNCTION_CALL = "function_call"
    CLASS_INSTANTIATION = "class_instantiation"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class ImplicitDependency:
    """
    Represents an implicit dependency detected in a PHP fragment.

    An implicit dependency is a variable or symbol used within a fragment
    that was not locally assigned, implying it comes from an external scope
    (global variables, included files, function parameters, etc.).

    Attributes:
        target_symbol: The symbol name (e.g., '$db', '$languages_id')
        dependency_type: Category of dependency (global_var|constant|function_call|
            class_instantiation)
        confidence: Confidence score from 0.0 to 1.0 based on detection method
    """

    target_symbol: str
    dependency_type: str
    confidence: float

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        # Validate confidence range
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"Confidence must be between 0.0 and 1.0, got {self.confidence}"
            )

        # Validate dependency_type against enum values
        valid_types = {dt.value for dt in DependencyType}
        if self.dependency_type not in valid_types:
            raise ValueError(
                f"dependency_type must be one of {valid_types}, "
                f"got '{self.dependency_type}'"
            )


@dataclass(frozen=True, slots=True)
class PhpFragment:
    """
    Represents a PHP code fragment extracted from a legacy PHP file.

    This is the core entity for PHP legacy extraction. Each fragment contains
    a portion of PHP code with associated metadata including source location,
    dependencies, signatures, and platform hints.

    Required fields:
        name: Identifier for this fragment
        fragment_type: Classification of the fragment (function|class|switch_block|
            bootstrap|mixed_html|catchall)
        source_file: Path to the source PHP file
        start_line: Starting line number in source file
        end_line: Ending line number in source file
        raw_content: The raw PHP code content of this fragment
        legacy_action: The LEGACY_ACTION name from switch/case or bootstrap
        preamble_ref: SHA-256 hex of preamble content or None for bootstrap fragments
        dependencies: Tuple of explicit dependency paths/identifiers
        platform_hints: Tuple of detected platform markers

    Default fields:
        file_style: Code style classification (LEGACY_PURE|LEGACY_MODERNIZED|HYBRID)
        implicit_deps: Tuple of implicit dependencies detected in fragment
        signatures: Tuple of legacy signatures detected in fragment
    """

    name: str
    fragment_type: str
    source_file: Path
    start_line: int
    end_line: int
    raw_content: str
    legacy_action: str
    preamble_ref: str | None
    dependencies: Tuple[str, ...]
    platform_hints: Tuple[str, ...]

    # Default fields
    file_style: str = "LEGACY_PURE"
    implicit_deps: Tuple[ImplicitDependency, ...] = field(default_factory=tuple)
    signatures: Tuple["LegacySignature", ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        # Validate fragment_type against enum values
        valid_types = {ft.value for ft in FragmentType}
        if self.fragment_type not in valid_types:
            raise ValueError(
                f"fragment_type must be one of {valid_types}, "
                f"got '{self.fragment_type}'"
            )

        # Validate file_style
        valid_styles = {"LEGACY_PURE", "LEGACY_MODERNIZED", "HYBRID"}
        if self.file_style not in valid_styles:
            raise ValueError(
                f"file_style must be one of {valid_styles}, "
                f"got '{self.file_style}'"
            )

        # Validate line numbers
        if self.start_line < 1:
            raise ValueError(f"start_line must be >= 1, got {self.start_line}")
        if self.end_line < self.start_line:
            raise ValueError(
                f"end_line must be >= start_line, got {self.end_line} < {self.start_line}"
            )

        # Validate preamble_ref format (SHA-256 hex is 64 characters)
        if self.preamble_ref is not None:
            if len(self.preamble_ref) != 64:
                raise ValueError(
                    f"preamble_ref must be 64-char SHA-256 hex or None, "
                    f"got length {len(self.preamble_ref)}"
                )
            # Validate hex characters
            try:
                int(self.preamble_ref, 16)
            except ValueError:
                raise ValueError(
                    f"preamble_ref must be valid hexadecimal, got '{self.preamble_ref}'"
                )

    @property
    def line_count(self) -> int:
        """Return the number of lines in this fragment."""
        return self.end_line - self.start_line + 1

    @property
    def has_implicit_deps(self) -> bool:
        """Return True if fragment has any implicit dependencies."""
        return len(self.implicit_deps) > 0

    @property
    def has_signatures(self) -> bool:
        """Return True if fragment has any legacy signatures."""
        return len(self.signatures) > 0

    def get_implicit_dep_symbols(self) -> Tuple[str, ...]:
        """Return tuple of implicit dependency symbol names."""
        return tuple(dep.target_symbol for dep in self.implicit_deps)

    def get_signature_categories(self) -> Tuple[str, ...]:
        """Return tuple of unique signature categories found in this fragment."""
        return tuple(set(sig.category for sig in self.signatures))


# ---------------------------------------------------------------------------
# Type Aliases (for forward compatibility)
# ---------------------------------------------------------------------------
# PhpFragmentTuple is a tuple of PhpFragment instances
PhpFragmentTuple = Tuple[PhpFragment, ...]

# ImplicitDependencyTuple is a tuple of ImplicitDependency instances
ImplicitDependencyTuple = Tuple[ImplicitDependency, ...]
