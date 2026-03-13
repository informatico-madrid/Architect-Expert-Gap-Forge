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

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Tuple

# Forward reference to avoid circular import - LegacySignature defined in php_signatures.py (T006)
if TYPE_CHECKING:
    from src.discovery.php_signatures import LegacySignature

# Runtime import for scan_signatures function
from src.discovery.php_signatures import scan_signatures

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


# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------

def strip_html_markup(source: str) -> str:
    """
    Extract only PHP code blocks from a mixed PHP/HTML/JS file.

    This function parses source code containing PHP tags embedded in HTML/JavaScript
    and returns only the PHP content, stripping all HTML markup and plain JavaScript.

    Args:
        source: The raw source code potentially containing PHP, HTML, and JS.

    Returns:
        The concatenated PHP code blocks with original PHP tags preserved.
        Returns empty string if no PHP blocks are found.

    Examples:
        >>> source = '''<html><body><?php echo $var; ?></body></html>'''
        >>> strip_html_markup(source)
        '<?php echo $var; ?>'

        >>> source = '''<div><?php include('header.php'); ?>
        ... <?php if ($condition) { ?></div>'''
        >>> strip_html_markup(source)
        '''<?php include('header.php'); ?>
        <?php if ($condition) { ?>'''
    """
    import re

    # Regex to match PHP code blocks: <?php ... ?> or <? ... ?>
    # Handles both short tags (<?) and standard PHP tags (<?php)
    # The non-greedy match .*? ensures we match the smallest possible block
    # Pattern breakdown:
    # - <\? matches the opening <?
    # - (?:php\s|php$|) matches: "php " (with space), "php" at end, or empty (short tag)
    # - (.*?) captures the PHP content non-greedily
    # - \?> matches the closing ?>
    php_pattern = re.compile(
        r'<\?(?:php\s|php$|)(.*?)\?>',
        re.DOTALL | re.IGNORECASE
    )

    # Find all PHP blocks using finditer to get match positions
    matches = list(php_pattern.finditer(source))

    if not matches:
        return ""

    # Reconstruct with PHP tags preserved
    result_parts: list[str] = []
    for match in matches:
        # Get the full matched text to determine the opening tag type
        full_match_text = match.group(0)
        content = match.group(1)

        # Check if it was <?php or just <?
        if full_match_text[:5].lower() == '<?php':
            result_parts.append(f"<?php {content}?>")
        else:
            # Short tag - preserve as <? ... ?>
            result_parts.append(f"<? {content}?>")

    return "\n".join(result_parts)


def fast_brace_scan(source: str, open_pos: int) -> int:
    """
    Match closing brace for an opening brace at given position.

    Scans forward character-by-character to find the matching closing brace,
    handling nested braces correctly.

    Args:
        source: The source code string to scan.
        open_pos: Position of the opening brace '{' in the source.

    Returns:
        The position of the matching closing brace '}'.
        Returns -1 if no matching brace is found (unmatched brace).

    Note:
        This function performs a simple character-loop scan and is not
        optimized for extremely large files. For those cases, consider
        using a proper parser or the FastBraceScanner class.
    """
    if open_pos >= len(source) or source[open_pos] != '{':
        return -1

    depth = 1
    pos = open_pos + 1
    in_string = False
    string_char = ''

    while pos < len(source):
        char = source[pos]

        # Handle PHP string context (don't count braces in strings)
        if char in ('"', "'"):
            if not in_string:
                in_string = True
                string_char = char
            elif char == string_char and (pos == 0 or source[pos - 1] != '\\'):
                in_string = False
                string_char = ''

        # Skip brace counting inside strings
        if in_string:
            pos += 1
            continue

        # Handle comments and literals
        if pos + 1 < len(source):
            # Single-line comment
            if source[pos:pos + 2] == '//':
                # Skip to end of line
                while pos < len(source) and source[pos] != '\n':
                    pos += 1
                pos += 1
                continue
            # Multi-line comment
            if source[pos:pos + 2] == '/*':
                end = source.find('*/', pos + 2)
                if end == -1:
                    return -1
                pos = end + 2
                continue

        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                return pos

        pos += 1

    return -1


def read_php_file(path: Path) -> str:
    """
    Read a PHP file with proper encoding handling.

    Attempts UTF-8 first, falls back to latin-1 if UTF-8 fails.
    Logs a warning if fallback encoding is used.

    Args:
        path: Path to the PHP file to read.

    Returns:
        The file contents as a string.

    Raises:
        PhpReadError: If both UTF-8 and latin-1 encoding fail, or if the file
            appears to be binary (non-text content).
    """
    # Try UTF-8 first (most common)
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        logger.warning(
            "UTF-8 decode failed for %s, falling back to latin-1",
            path,
        )
        try:
            content = path.read_text(encoding="latin-1")
        except UnicodeDecodeError as e:
            raise PhpReadError(
                f"Failed to read {path} with UTF-8 or latin-1 encoding: {e}"
            ) from e

        # Check for binary content: if >30% of characters are non-printable
        # or control characters (excluding common ones like tab, newline, carriage return)
        non_printable = sum(
            1 for c in content
            if ord(c) < 32 and c not in '\t\n\r'
        )
        if len(content) > 0 and (non_printable / len(content)) > 0.30:
            raise PhpReadError(
                f"Failed to read {path}: file appears to be binary"
            )

        return content


class PhpReadError(Exception):
    """Exception raised when a PHP file cannot be read."""

    pass


# ---------------------------------------------------------------------------
# Preamble Extraction
# ---------------------------------------------------------------------------


def _extract_function_blocks(source: str, source_file: Path) -> list[tuple[int, int, str]]:
    r"""
    Extract standalone function blocks from PHP source.

    Uses regex detection `function\s+\w+\s*\(` to find function definitions.
    Uses fast_brace_scan to find the matching closing brace.
    On fast_brace_scan failure (-1), logs to needs_manual_review.json and skips the fragment.

    Args:
        source: The raw PHP source code to parse.
        source_file: Path to the source file (for logging purposes).

    Returns:
        A list of tuples (start_line, end_line, content) for each function block.
        Only standalone functions are extracted (not class methods).

    Examples:
        >>> source = '''<?php
        ... function getData($id) {
        ...     return $id;
        ... }
        ... '''
        >>> source_file = Path("/test/file.php")
        >>> blocks = _extract_function_blocks(source, source_file)
        >>> len(blocks)
        1
    """
    if not source:
        return []

    # Track positions we've already processed (to skip class methods)
    # Class methods are functions that appear after 'class' keyword and its opening brace
    class_regions: list[tuple[int, int]] = []

    # Find class definition regions to exclude methods
    # We need to find the opening brace of the class to properly mark the region
    class_pattern = re.compile(
        r'(?:^|\n)(?:abstract\s+|final\s+)?class\s+\w+',
        re.MULTILINE
    )

    for class_match in class_pattern.finditer(source):
        class_start = class_match.start()

        # Find the opening brace after 'class ClassName'
        brace_search_start = class_match.end()
        brace_pos = source.find('{', brace_search_start)

        if brace_pos != -1:
            # Use fast_brace_scan to find the class closing brace
            class_end = fast_brace_scan(source, brace_pos)
            if class_end != -1:
                class_regions.append((class_start, class_end))
            else:
                # If we can't find the class end, mark from class to end of file
                class_regions.append((class_start, len(source)))
        else:
            # No opening brace found - mark from class to end of file
            class_regions.append((class_start, len(source)))

    # Find all standalone function definitions
    # Pattern: function name(
    func_pattern = re.compile(
        r'function\s+(\w+)\s*\(',
        re.MULTILINE
    )

    blocks: list[tuple[int, int, str]] = []

    for match in func_pattern.finditer(source):
        func_name = match.group(1)
        func_start_pos = match.start()

        # Skip if this function is inside a class region
        is_class_method = any(
            class_start <= func_start_pos < class_end
            for class_start, class_end in class_regions
        )
        if is_class_method:
            continue

        # Find the opening brace after the function signature
        # Search from the match end forward
        brace_search_start = match.end()
        brace_pos = source.find('{', brace_search_start)

        if brace_pos == -1:
            # No opening brace found - log and skip
            logger.warning(
                "No opening brace found for function '%s' in %s - skipping (marking for manual review)",
                func_name,
                source_file,
            )
            _log_needs_manual_review(
                source_file=source_file,
                name=func_name,
                start_line=source[:match.start()].count('\n') + 1,
                reason="missing_opening_brace"
            )
            continue

        # Use fast_brace_scan to find matching closing brace
        close_pos = fast_brace_scan(source, brace_pos)

        if close_pos == -1:
            # No matching closing brace - log and skip
            logger.warning(
                "No matching closing brace for function '%s' in %s - skipping (marking for manual review)",
                func_name,
                source_file,
            )
            _log_needs_manual_review(
                source_file=source_file,
                name=func_name,
                start_line=source[:match.start()].count('\n') + 1,
                reason="unmatched_brace"
            )
            continue

        # Extract the function content (from start to after closing brace)
        # Include the function keyword and the braces
        content = source[match.start():close_pos + 1]

        # Calculate line numbers (1-indexed)
        start_line = source[:match.start()].count('\n') + 1
        end_line = source[:close_pos].count('\n') + 1

        blocks.append((start_line, end_line, content))

    return blocks


def _log_needs_manual_review(
    source_file: Path,
    name: str,
    start_line: int,
    reason: str
) -> None:
    """
    Log an entry to needs_manual_review.json.

    Args:
        source_file: Path to the source file.
        name: Name of the function or fragment.
        start_line: Line number where the issue starts.
        reason: Reason for manual review (missing_opening_brace, unmatched_brace, etc.)
    """
    # Determine the output directory (same as source_file's directory or cwd)
    output_dir = Path.cwd()

    review_file = output_dir / "needs_manual_review.json"

    # Load existing entries or create new list
    entries: list[dict] = []
    if review_file.exists():
        try:
            content = review_file.read_text()
            if content.strip():
                entries = json.loads(content)
        except (json.JSONDecodeError, OSError):
            entries = []

    # Add new entry
    entries.append({
        "source_file": str(source_file),
        "name": name,
        "start_line": start_line,
        "reason": reason,
    })

    # Write back
    try:
        review_file.write_text(json.dumps(entries, indent=2))
    except OSError as e:
        logger.warning("Failed to write needs_manual_review.json: %s", e)


def _extract_preamble(source: str) -> tuple[str, str]:
    """
    Extract the preamble (bootstrap code) from PHP source.

    The preamble is the portion of code that appears before the first function
    or class definition. It typically contains:
    - define() statements for constants
    - require/include statements
    - Global configuration setup

    Args:
        source: The raw PHP source code to parse.

    Returns:
        A tuple of (preamble_content, remaining_source).
        - preamble_content: All code before the first function/class definition
        - remaining_source: Code starting from the first function or class

    Examples:
        >>> source = '''<?php
        ... define('DIR_WS_INCLUDES', 'includes/');
        ... require_once('includes/database_tables.php');
        ...
        ... function processData($id) {
        ...     return $id * 2;
        ... }
        ... '''
        >>> preamble, remaining = _extract_preamble(source)
        >>> "define('DIR_WS_INCLUDES'" in preamble
        True
        >>> "function processData" in remaining
        True
    """
    import re

    if not source:
        return ("", "")

    # Find the first occurrence of function or class definition
    # Pattern matches:
    # - function name(
    # - class name
    # - abstract class name
    # - final class name
    # - interface name
    first_delimiter = re.search(
        r'(?:^|\n)(?:function\s+\w+\s*\(|(?:abstract\s+|final\s+)?class\s+\w+|interface\s+\w+)',
        source,
        re.MULTILINE
    )

    if first_delimiter is None:
        # No function or class found - no preamble, entire source is remaining
        return ("", source)

    # Split at the delimiter position
    delimiter_pos = first_delimiter.start()

    # Extract preamble (everything before the delimiter)
    raw_preamble = source[:delimiter_pos]

    # Strip PHP tags and whitespace from preamble
    # Remove <?php ... ?> blocks, including <?php without closing tag
    preamble = re.sub(r'<\?php[\s\S]*?\?>', '', raw_preamble)  # Remove <?php ... ?>
    preamble = re.sub(r'<\?[\s\S]*?\?>', '', preamble)  # Remove <? ... ?>
    preamble = re.sub(r'<\?php\s*', '', preamble)  # Remove <?php without ?>
    preamble = re.sub(r'<\?\s*', '', preamble)  # Remove <? without ?>
    preamble = preamble.strip()

    # If preamble is empty after stripping PHP tags, return empty
    if not preamble:
        preamble = ""

    # Extract remaining (from delimiter to end)
    remaining = source[delimiter_pos:]

    return (preamble, remaining)


def _extract_switch_cases(
    source: str, source_file: Path
) -> list[tuple[int, int, str, str]]:
    """
    Extract switch/case blocks from PHP source.

    Uses regex detection to find switch statements, then extracts individual
    cases. Cases >500 lines are sub-chunked while preserving the case header.

    Args:
        source: The raw PHP source code to parse.
        source_file: Path to the source file (for logging purposes).

    Returns:
        A list of tuples (start_line, end_line, raw_content, case_label) for each case.
        Returns empty list if no switch blocks are found.

    Examples:
        >>> source = '''<?php
        ... switch ($action) {
        ...     case 'add':
        ...         $result = 'added';
        ...         break;
        ... }
        ... '''
        >>> source_file = Path("/test/file.php")
        >>> cases = _extract_switch_cases(source, source_file)
        >>> len(cases) >= 1
        True
    """
    if not source:
        return []

    # Find all switch statements using regex
    # Pattern matches: switch ($variable) {
    switch_pattern = re.compile(
        r'switch\s*\(\s*\$[\w]+\s*\)\s*\{',
        re.MULTILINE
    )

    blocks: list[tuple[int, int, str, str]] = []

    for switch_match in switch_pattern.finditer(source):
        switch_start_pos = switch_match.start()

        # Find the opening brace after 'switch ($var) {'
        brace_search_start = switch_match.end() - 1  # Position of '{'
        brace_pos = source.find('{', brace_search_start)

        if brace_pos == -1:
            # No opening brace found - log and skip
            logger.warning(
                "No opening brace found for switch block in %s - skipping (marking for manual review)",
                source_file,
            )
            _log_needs_manual_review(
                source_file=source_file,
                name=f"switch_{source_file.stem}",
                start_line=source[:switch_start_pos].count('\n') + 1,
                reason="missing_opening_brace"
            )
            continue

        # Use fast_brace_scan to find matching closing brace
        close_pos = fast_brace_scan(source, brace_pos)

        if close_pos == -1:
            # No matching closing brace - log and abort entire switch block
            logger.warning(
                "No matching closing brace for switch block in %s - skipping (marking for manual review)",
                source_file,
            )
            _log_needs_manual_review(
                source_file=source_file,
                name=f"switch_{source_file.stem}",
                start_line=source[:switch_start_pos].count('\n') + 1,
                reason="unmatched_brace"
            )
            continue

        # Extract the switch block content
        switch_content = source[switch_start_pos:close_pos + 1]

        # Extract individual cases from the switch block
        # Pattern matches: case 'label': or case "label": or case label: or default:
        # Uses two patterns: one for case statements, one for default
        case_label_pattern = re.compile(
            r"case\s+(?:'([^']+)'|\"([^\"]+)\"|([\w\-_]+))\s*:",
            re.MULTILINE
        )
        default_pattern = re.compile(r'default\s*:', re.MULTILINE)

        # Find all case positions within the switch block
        case_matches = list(case_label_pattern.finditer(switch_content))
        default_matches = list(default_pattern.finditer(switch_content))

        # Combine and sort by position
        all_matches = case_matches + default_matches
        all_matches.sort(key=lambda m: m.start())

        if not all_matches:
            continue

        # Process each case
        for i, case_match in enumerate(all_matches):
            # Determine case label from the match
            # case_label_pattern has groups: 1=quoted single, 2=quoted double, 3=unquoted
            # default_pattern has no groups
            if case_match.re == case_label_pattern:
                case_label_raw = case_match.group(1) or case_match.group(2) or case_match.group(3)
                case_label = case_label_raw.strip("'\"") if case_label_raw else 'unknown'
            else:
                case_label = 'default'

            case_start_in_switch = case_match.start()

            # Determine where this case ends:
            # - Either at the next case keyword
            # - Or at the closing brace of the switch
            if i + 1 < len(all_matches):
                case_end_in_switch = all_matches[i + 1].start()
            else:
                # Last case goes until the closing brace
                case_end_in_switch = len(switch_content) - 1

            # Extract case content
            case_content = switch_content[case_start_in_switch:case_end_in_switch + 1]

            # Calculate actual line numbers in the source file
            # case_start_in_switch is relative to switch_content (starts at 0)
            # switch_start_pos is the position of the switch keyword in source
            # So case position in source = switch_start_pos + case_start_in_switch
            case_start_pos_in_source = switch_start_pos + case_start_in_switch
            case_end_pos_in_source = switch_start_pos + case_end_in_switch

            # Count newlines from source start to these positions
            case_start_line = source[:case_start_pos_in_source].count('\n') + 1
            case_end_line = source[:case_end_pos_in_source].count('\n') + 1

            # Calculate case line count
            case_line_count = case_content.count('\n') + 1

            # If case is >500 lines, sub-chunk it while preserving case header
            if case_line_count > 500:
                # Extract the case header (first few lines with case label)
                header_end = case_content.find('\n', case_content.find(':'))
                if header_end == -1:
                    header_end = len(case_content)
                case_header = case_content[:header_end + 1]

                # Split remaining content into chunks of ~500 lines
                remaining_content = case_content[header_end + 1:]
                chunk_size = 500

                # Create first chunk with header
                first_chunk = case_header + remaining_content[:chunk_size * 50]  # ~50 chars per line avg
                first_chunk_lines = first_chunk.count('\n') + 1

                blocks.append((
                    case_start_line,
                    case_start_line + first_chunk_lines - 1,
                    first_chunk,
                    case_label
                ))

                # Create additional chunks if needed
                offset = chunk_size * 50
                while offset < len(remaining_content):
                    chunk = remaining_content[offset:offset + chunk_size * 50]
                    chunk_lines = chunk.count('\n') + 1
                    chunk_start = case_start_line + first_chunk_lines + (offset // (chunk_size * 50)) * chunk_size

                    blocks.append((
                        chunk_start,
                        chunk_start + chunk_lines - 1,
                        chunk,
                        f"{case_label}_cont"
                    ))
                    offset += chunk_size * 50
            else:
                # Normal case - add as-is
                blocks.append((
                    case_start_line,
                    case_end_line,
                    case_content,
                    case_label
                ))

    return blocks


def _fragment_by_size(
    source: str, max_lines: int, overlap: int = 20
) -> list[tuple[int, int, str]]:
    r"""
    Size-based fallback fragmentation for files with no function/case delimiters.

    This function splits the source into chunks of max_lines, with optional
    overlap between consecutive chunks to preserve context at boundaries.

    Args:
        source: The raw PHP source code to fragment.
        max_lines: Maximum number of lines per fragment.
        overlap: Number of lines to overlap between fragments (default: 20).

    Returns:
        A list of tuples (start_line, end_line, content) for each fragment.
        Returns empty list if source is empty.

    Examples:
        >>> source = "\\n".join([f"line {i}" for i in range(100)])
        >>> fragments = _fragment_by_size(source, max_lines=30, overlap=5)
        >>> len(fragments) > 1
        True
        >>> # With overlap, fragments share boundary context
        >>> fragments[0][1] >= fragments[1][0] - overlap
        True

        >>> # Single fragment when source fits
        >>> source = "short source"
        >>> fragments = _fragment_by_size(source, max_lines=100)
        >>> len(fragments)
        1

        >>> _fragment_by_size("", max_lines=30)
        []
    """
    if not source:
        return []

    # Count total lines in source
    total_lines = source.count('\n')
    # Handle case where source doesn't end with newline
    if not source.endswith('\n'):
        total_lines += 1

    # If source fits in max_lines, return single fragment
    if total_lines <= max_lines:
        return [(1, total_lines, source)]

    # Calculate step size (max_lines minus overlap)
    step = max_lines - overlap
    if step <= 0:
        # If overlap >= max_lines, just use 1 as step
        step = 1

    fragments: list[tuple[int, int, str]] = []
    pos = 0

    while pos < len(source):
        # Calculate start line (1-indexed)
        start_line = source[:pos].count('\n') + 1

        # Calculate end position (pos + max_lines lines)
        # Find the position max_lines after current pos
        lines_remaining = max_lines
        end_pos = pos

        while end_pos < len(source) and lines_remaining > 0:
            if source[end_pos] == '\n':
                lines_remaining -= 1
            end_pos += 1

        # Ensure we don't go past the end
        end_pos = min(end_pos, len(source))

        # Calculate end line (1-indexed)
        end_line = source[:end_pos].count('\n') + 1

        # Extract content for this fragment
        content = source[pos:end_pos]

        fragments.append((start_line, end_line, content))

        # Move position forward by step (accounting for overlap)
        # Find the position of line (max_lines - overlap) to start next chunk
        next_pos = pos
        lines_to_skip = step

        while next_pos < len(source) and lines_to_skip > 0:
            if source[next_pos] == '\n':
                lines_to_skip -= 1
            next_pos += 1

        # If we're not making progress, break to avoid infinite loop
        if next_pos <= pos:
            break

        pos = next_pos

    return fragments


def _classify_file_style(source: str) -> str:
    """
    Classify PHP file style as LEGACY_PURE, LEGACY_MODERNIZED, or HYBRID.

    Implements Golden Rule (R-007): three sequential binary checks:
    1. Has namespace AND at least one constructor with typed parameters -> MODERNIZED
    2. Has a class AND includes mysql_query/tep_db_query/superglobals -> HYBRID
    3. Has 'global $db' or top-level functions without a class -> PURE
    4. Default -> PURE

    Args:
        source: The raw PHP source code to classify.

    Returns:
        "LEGACY_MODERNIZED" | "LEGACY_PURE" | "HYBRID"

    Examples:
        >>> # Modernized: namespace with typed constructor
        >>> source = "<?php namespace App\\Model; class User { public function __construct(int $id) {} }"
        >>> _classify_file_style(source)
        'LEGACY_MODERNIZED'

        >>> # Pure: global $db usage
        >>> source = "<?php global $db; function getData() { global $db; return $db->query(); }"
        >>> _classify_file_style(source)
        'LEGACY_PURE'

        >>> # Hybrid: class with legacy patterns
        >>> source = "<?php class Order { public function process() { global $db; mysql_query(...); } }"
        >>> _classify_file_style(source)
        'HYBRID'
    """
    if not source:
        return "LEGACY_PURE"

    # Check 1: LEGACY_MODERNIZED - namespace + constructor with typed parameters
    # Pattern: namespace declaration
    has_namespace = bool(re.search(r'\bnamespace\s+[\w\\]+', source))

    # Pattern: constructor with typed parameters (e.g., __construct(Type $param))
    has_typed_constructor = bool(re.search(
        r'function\s+__construct\s*\(\s*(?:int|float|string|array|bool|object|callable|mixed)\s+\$\w+',
        source
    ))

    if has_namespace and has_typed_constructor:
        return "LEGACY_MODERNIZED"

    # Check for class existence (simpler pattern)
    has_class = bool(re.search(r'\bclass\s+\w+', source))

    # Legacy patterns to check for HYBRID classification
    legacy_patterns = [
        r'mysql_query',           # old mysql extension
        r'tep_db_query',          # osCommerce
        r'\$wpdb->',              # WordPress
        r'zen_db_perform',        # ZenCart
        r'Mage::',                # Magento/OpenMage
        r'global\s+\$\w+',        # global variable access
        r'\$GLOBALS\s*\[',        # $GLOBALS access
        r'\$_(GET|POST|REQUEST|SERVER|COOKIE|FILES|SESSION)\s*\[',  # superglobals
    ]

    # Check 2: HYBRID - has class AND legacy patterns
    if has_class:
        for pattern in legacy_patterns:
            if re.search(pattern, source, re.IGNORECASE):
                return "HYBRID"

    # Check 3: LEGACY_PURE - global $db OR top-level functions without class
    # Pattern: global $db (common osCommerce pattern)
    has_global_db = bool(re.search(r'global\s+\$db\b', source))

    # Check for top-level functions (functions not inside a class)
    # Use simpler detection: if no class, all functions are top-level
    has_any_function = bool(re.search(r'\bfunction\s+\w+\s*\(', source))

    if not has_class:
        # No class means pure (unless it has modern patterns, which we already checked)
        if has_global_db or has_any_function:
            return "LEGACY_PURE"

    # If we have a class but no legacy patterns detected above, it's pure
    if has_class:
        return "LEGACY_PURE"

    # Default to PURE
    return "LEGACY_PURE"


# ---------------------------------------------------------------------------
# Main Processing Function (T020)
# ---------------------------------------------------------------------------


def process_php_file(path: Path, content: str, profile_name: str) -> list[PhpFragment]:
    """
    Process a PHP file and extract code fragments.

    This is the main orchestration function that:
    1. Extracts the preamble (bootstrap code) and computes its SHA-256 hash
    2. Extracts function blocks (standalone functions, not class methods)
    3. Extracts switch/case blocks
    4. Falls back to size-based fragmentation if no functions/cases found
    5. Classifies the file style (LEGACY_PURE, LEGACY_MODERNIZED, or HYBRID)
    6. Creates PhpFragment objects for each extracted block

    This function is a module-level function (not a lambda/closure) to ensure
    pickle compatibility with ProcessPoolExecutor for parallel processing.

    Args:
        path: Path to the PHP file being processed.
        content: The raw PHP source code content.
        profile_name: The platform profile name (e.g., "oscommerce", "wordpress",
            "zencart", "generic_php") for platform-specific hints.

    Returns:
        A list of PhpFragment objects representing the extracted code fragments.

    Examples:
        >>> from pathlib import Path
        >>> path = Path("includes/application_top.php")
        >>> content = "<?php define('DIR_WS_INCLUDES', 'includes/');\\nfunction process() { return true; }"
        >>> fragments = process_php_file(path, content, "oscommerce")
        >>> len(fragments) >= 1
        True
    """
    if not content:
        return []

    fragments: list[PhpFragment] = []

    # Step 1: Extract preamble and compute SHA-256 hash for preamble_ref
    # The preamble is the code before the first function/class definition
    preamble_content, remaining_source = _extract_preamble(content)
    preamble_ref: str | None = None

    if preamble_content:
        # Compute SHA-256 hex digest of preamble content
        preamble_ref = hashlib.sha256(preamble_content.encode()).hexdigest()
        logger.debug(
            "Extracted preamble for %s: %d chars, hash=%s",
            path.name,
            len(preamble_content),
            preamble_ref[:16] + "..." if len(preamble_ref) > 16 else preamble_ref,
        )

    # Step 2: Classify file style
    file_style = _classify_file_style(content)
    logger.debug(
        "Classified file style for %s: %s",
        path.name,
        file_style,
    )

    # Step 3: Extract function blocks (standalone functions, not class methods)
    function_blocks = _extract_function_blocks(remaining_source, path)

    # Step 4: Extract switch/case blocks
    switch_cases = _extract_switch_cases(remaining_source, path)

    # Step 5: Determine fragmentation strategy
    # Priority: functions > switch/cases > fallback by size
    has_functions = len(function_blocks) > 0
    has_switch_cases = len(switch_cases) > 0

    # Platform hints based on profile_name
    platform_hints: Tuple[str, ...] = (profile_name,)

    # Track the preamble content for bootstrap fragments
    # If no functions/cases found, we might need to create a bootstrap fragment
    # from the preamble + remaining source

    if has_functions:
        # Process each function block
        for start_line, end_line, func_content in function_blocks:
            # Determine legacy action from function name
            # Extract function name for LEGACY_ACTION
            func_match = re.search(r'function\s+(\w+)\s*\(', func_content)
            func_name = func_match.group(1) if func_match else f"function_{start_line}"

            # Determine fragment name
            fragment_name = f"{path.stem}_{func_name}"

            # Scan for legacy signatures in fragment content
            sigs = tuple(scan_signatures(func_content))

            # Create the fragment
            fragment = PhpFragment(
                name=fragment_name,
                fragment_type=FragmentType.FUNCTION.value,
                source_file=path,
                start_line=start_line,
                end_line=end_line,
                raw_content=func_content,
                legacy_action=func_name,
                preamble_ref=preamble_ref,
                dependencies=(),
                platform_hints=platform_hints,
                file_style=file_style,
                signatures=sigs,
            )
            fragments.append(fragment)

        logger.debug(
            "Extracted %d function blocks from %s",
            len(function_blocks),
            path.name,
        )

    if has_switch_cases:
        # Process each switch/case block
        for start_line, end_line, case_content, case_label in switch_cases:
            # Determine fragment name
            fragment_name = f"{path.stem}_action_{case_label}"

            # Scan for legacy signatures in fragment content
            sigs = tuple(scan_signatures(case_content))

            # Create the fragment
            fragment = PhpFragment(
                name=fragment_name,
                fragment_type=FragmentType.SWITCH_BLOCK.value,
                source_file=path,
                start_line=start_line,
                end_line=end_line,
                raw_content=case_content,
                legacy_action=case_label,
                preamble_ref=preamble_ref,
                dependencies=(),
                platform_hints=platform_hints,
                file_style=file_style,
                signatures=sigs,
            )
            fragments.append(fragment)

        logger.debug(
            "Extracted %d switch/case blocks from %s",
            len(switch_cases),
            path.name,
        )

    # Step 6: Fallback - size-based fragmentation if no functions or switch/cases found
    if not has_functions and not has_switch_cases:
        logger.debug(
            "No functions or switch/case blocks found in %s, using size-based fallback",
            path.name,
        )

        # Use size-based fragmentation with default max_lines=500
        size_fragments = _fragment_by_size(remaining_source, max_lines=500, overlap=20)

        if size_fragments:
            # If we have size fragments, create PhpFragment for each
            for start_line, end_line, frag_content in size_fragments:
                fragment_name = f"{path.stem}_chunk_{start_line}"

                # Scan for legacy signatures in fragment content
                sigs = tuple(scan_signatures(frag_content))

                fragment = PhpFragment(
                    name=fragment_name,
                    fragment_type=FragmentType.CATCHALL.value,
                    source_file=path,
                    start_line=start_line,
                    end_line=end_line,
                    raw_content=frag_content,
                    legacy_action=LegacyAction.PROCESS.value,
                    preamble_ref=preamble_ref,
                    dependencies=(),
                    platform_hints=platform_hints,
                    file_style=file_style,
                    signatures=sigs,
                )
                fragments.append(fragment)
        else:
            # Edge case: remaining source is empty but we have preamble
            # Create a bootstrap fragment from preamble only
            if preamble_content:
                # Calculate lines from preamble
                preamble_lines = preamble_content.count('\n') + 1

                # Scan for legacy signatures in preamble content
                sigs = tuple(scan_signatures(preamble_content))

                fragment = PhpFragment(
                    name=f"{path.stem}_bootstrap",
                    fragment_type=FragmentType.BOOTSTRAP.value,
                    source_file=path,
                    start_line=1,
                    end_line=preamble_lines,
                    raw_content=preamble_content,
                    legacy_action=LegacyAction.INITIALIZE.value,
                    preamble_ref=None,  # Bootstrap has no preamble_ref (it's the preamble itself)
                    dependencies=(),
                    platform_hints=platform_hints,
                    file_style=file_style,
                    signatures=sigs,
                )
                fragments.append(fragment)

    # Step 7: If we have preamble and at least one other fragment exists,
    # ensure we also emit the preamble as a bootstrap fragment if it contains
    # significant code (not just PHP tags)
    if preamble_content and len(fragments) > 0:
        # Check if preamble has meaningful content beyond just PHP tags
        # Strip PHP tags to check
        clean_preamble = re.sub(r'<\?php\s*|\?>', '', preamble_content).strip()
        if len(clean_preamble) > 20:  # More than just trivial content
            # Add bootstrap fragment for preamble
            preamble_lines = preamble_content.count('\n') + 1

            # Check if a bootstrap fragment already exists (from fallback case)
            has_bootstrap = any(
                f.fragment_type == FragmentType.BOOTSTRAP.value for f in fragments
            )

            if not has_bootstrap:
                # Scan for legacy signatures in preamble content
                sigs = tuple(scan_signatures(preamble_content))

                bootstrap_fragment = PhpFragment(
                    name=f"{path.stem}_bootstrap",
                    fragment_type=FragmentType.BOOTSTRAP.value,
                    source_file=path,
                    start_line=1,
                    end_line=preamble_lines,
                    raw_content=preamble_content,
                    legacy_action=LegacyAction.INITIALIZE.value,
                    preamble_ref=None,  # Bootstrap is the preamble, so no ref
                    dependencies=(),
                    platform_hints=platform_hints,
                    file_style=file_style,
                    signatures=sigs,
                )
                # Add at the beginning (preamble should come first)
                fragments.insert(0, bootstrap_fragment)

    logger.info(
        "Processed %s: %d fragments (functions=%d, switch_cases=%d, size_fragments=%d, bootstrap=%d)",
        path.name,
        len(fragments),
        sum(1 for f in fragments if f.fragment_type == FragmentType.FUNCTION.value),
        sum(1 for f in fragments if f.fragment_type == FragmentType.SWITCH_BLOCK.value),
        sum(1 for f in fragments if f.fragment_type == FragmentType.CATCHALL.value),
        sum(1 for f in fragments if f.fragment_type == FragmentType.BOOTSTRAP.value),
    )

    return fragments


# ---------------------------------------------------------------------------
# Archive Header Formatting (T021)
# ---------------------------------------------------------------------------


def format_arch_header(fragment: PhpFragment) -> str:
    """
    Format the architecture header for a PHP fragment.

    Produces all required fields per bundle-format contract:
    MODULE, REPO_PREFIX, FILE_ROLE, FRAGMENT_TYPE, LANGUAGE, PLATFORM,
    LOCAL_IMPORTS, DEPENDENCIES, NEIGHBORS, LEGACY_ACTION, IMPLICIT_DEPS,
    PREAMBLE_REF

    Args:
        fragment: The PhpFragment to format the header for.

    Returns:
        A formatted ARCH_HEADER string with all required fields.

    Examples:
        >>> from pathlib import Path
        >>> fragment = PhpFragment(
        ...     name="categories_get_function",
        ...     fragment_type="function",
        ...     source_file=Path("admin/categories.php"),
        ...     start_line=10,
        ...     end_line=50,
        ...     raw_content="function categories_get() { return []; }",
        ...     legacy_action="get_categories",
        ...     preamble_ref="abc123def456789012345678901234567890123456789012345678901234",
        ...     dependencies=("tep_db_query",),
        ...     platform_hints=("oscommerce",),
        ...     file_style="LEGACY_PURE",
        ... )
        >>> header = format_arch_header(fragment)
        >>> "MODULE: oscommerce/admin" in header
        True
        >>> "LANGUAGE: php" in header
        True
    """
    lines: list[str] = []

    # MODULE: <platform>/<directory_path>
    # Extract directory path from source_file, prepend platform from platform_hints
    platform = fragment.platform_hints[0] if fragment.platform_hints else "generic_php"
    source_path = fragment.source_file
    # Get directory path (parent), convert to forward slashes
    dir_path = source_path.parent
    module_path = f"{platform}/{dir_path}" if dir_path != Path(".") else platform
    lines.append(f"MODULE: {module_path}")

    # REPO_PREFIX: <repository_name>
    # Use the top-level directory name as repo prefix
    repo_prefix = source_path.parts[0] if source_path.parts else "unknown_repo"
    lines.append(f"REPO_PREFIX: {repo_prefix}")

    # FILE_ROLE: source
    lines.append("FILE_ROLE: source")

    # FRAGMENT_TYPE: FUNCTIONAL_UNIT
    # Map fragment_type to FRAGMENT_TYPE enum
    # function, class -> FUNCTIONAL_UNIT; switch_block -> SWITCH_BLOCK;
    # bootstrap -> BOOTSTRAP; mixed_html -> MIXED_HTML; catchall -> CATCHALL
    type_mapping = {
        "function": "FUNCTIONAL_UNIT",
        "class": "FUNCTIONAL_UNIT",
        "switch_block": "SWITCH_BLOCK",
        "bootstrap": "BOOTSTRAP",
        "mixed_html": "MIXED_HTML",
        "catchall": "CATCHALL",
    }
    frag_type = type_mapping.get(fragment.fragment_type, "FUNCTIONAL_UNIT")
    lines.append(f"FRAGMENT_TYPE: {frag_type}")

    # LANGUAGE: php
    lines.append("LANGUAGE: php")

    # PLATFORM: <detected_platform>
    lines.append(f"PLATFORM: {platform}")

    # LOCAL_IMPORTS: <include/require list, comma-separated>
    # Use dependencies field - these are explicit imports
    local_imports = ", ".join(fragment.dependencies) if fragment.dependencies else ""
    lines.append(f"LOCAL_IMPORTS: {local_imports}")

    # DEPENDENCIES: <external dependencies detected>
    # Use dependencies field (same as LOCAL_IMPORTS for now)
    deps = ", ".join(fragment.dependencies) if fragment.dependencies else ""
    lines.append(f"DEPENDENCIES: {deps}")

    # NEIGHBORS: <adjacent files from IncludeGraph>
    # Empty for now - populated by IncludeGraph in T044
    lines.append("NEIGHBORS: ")

    # LEGACY_ACTION: <LEGACY_ACTION enum value>
    lines.append(f"LEGACY_ACTION: {fragment.legacy_action}")

    # IMPLICIT_DEPS: ['$var1', '$var2'] - only if non-empty
    if fragment.implicit_deps:
        # Extract target_symbols from ImplicitDependency tuples
        symbols = [dep.target_symbol for dep in fragment.implicit_deps]
        # Format as JSON list string
        import json
        implicit_deps_str = json.dumps(symbols)
        lines.append(f"IMPLICIT_DEPS: {implicit_deps_str}")

    # PREAMBLE_REF: <64-char sha256 hex> - only if not None
    # Note: bootstrap fragments have preamble_ref=None by design
    if fragment.preamble_ref is not None:
        lines.append(f"PREAMBLE_REF: {fragment.preamble_ref}")

    return "\n".join(lines)


def write_bundle(fragment: PhpFragment, output_dir: Path) -> Path:
    """
    Write a PHP fragment bundle to a .txt file.

    Writes the fragment with the architecture header in the bundle format
    compatible with Stage 2's parse_bundle() function.

    Args:
        fragment: The PhpFragment to write.
        output_dir: Directory to write the bundle file to.

    Returns:
        Path to the written bundle file.

    Raises:
        FileNotFoundError: If output_dir does not exist.
        ValueError: If fragment name is empty.

    Examples:
        >>> from pathlib import Path
        >>> import tempfile
        >>> fragment = PhpFragment(
        ...     name="categories_get_function",
        ...     fragment_type=FragmentType.FUNCTION.value,
        ...     source_file=Path("admin/categories.php"),
        ...     start_line=10,
        ...     end_line=50,
        ...     raw_content="function categories_get() { return []; }",
        ...     legacy_action="get_categories",
        ...     preamble_ref="78588c6f34737b88a13c1cea280ae5e54d76d22a7998ae757f218c20885ce4bf",
        ...     dependencies=("tep_db_query",),
        ...     platform_hints=("oscommerce",),
        ...     file_style="LEGACY_PURE",
        ... )
        >>> with tempfile.TemporaryDirectory() as tmpdir:
        ...     output_path = write_bundle(fragment, Path(tmpdir))
        ...     content = output_path.read_text()
        ...     "[ARCH_HEADER]" in content
        True
        >>> with tempfile.TemporaryDirectory() as tmpdir:
        ...     output_path = write_bundle(fragment, Path(tmpdir))
        ...     output_path.name
        'categories_get_function.txt'
    """
    # Validate inputs
    if not output_dir.exists():
        raise FileNotFoundError(f"Output directory does not exist: {output_dir}")

    if not fragment.name:
        raise ValueError("Fragment name cannot be empty")

    # Generate header using format_arch_header
    header = format_arch_header(fragment)

    # Format the bundle content using the same delimiter as parse_bundle()
    # Format: [ARCH_HEADER]\n{header}\n--- FILE: {fragment_name} ({fragment_type}) ---\n{raw_content}
    bundle_content = (
        f"[ARCH_HEADER]\n"
        f"{header}\n"
        f"--- FILE: {fragment.name} ({fragment.fragment_type}) ---\n"
        f"{fragment.raw_content}"
    )

    # Generate output filename: <fragment_name>.txt
    output_filename = f"{fragment.name}.txt"
    output_path = output_dir / output_filename

    # Write the bundle file
    output_path.write_text(bundle_content, encoding="utf-8")

    logger.info("Written bundle to %s", output_path)

    return output_path
