# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
I18nKeyExtractor - TypeScript extractor for i18n keys.

This module provides extraction of internationalization keys from TypeScript
source via localize() and hass.localize() call detection.

Uses tree-sitter primarily for AST parsing, with regex fallback (~85% coverage)
for v1 as specified in the design.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Literal, Optional

from src.utils.extractors.extractors.base import (
    FrontendToken,
    I18nKey,
    TypeScriptExtractorProtocol,
)

logger = logging.getLogger(__name__)

# Regex patterns for fallback extraction (v1 ~85% coverage)

# Matches localize('key') or localize("key")
LOCALIZE_CALL_PATTERN = re.compile(
    r"localize\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", re.MULTILINE
)

# Matches hass.localize('key') or hass.localize("key")
HASS_LOCALIZE_PATTERN = re.compile(
    r"hass\.localize\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", re.MULTILINE
)

# Matches template literal with i18n key: `ui.card.${action}`
TEMPLATE_LITERAL_PATTERN = re.compile(
    r"`([^`]*\$\{[^}]+\}[^`]*)`", re.MULTILINE
)

# Matches setupLocalize() or setupCustomlocalize() wrapper pattern
SETUP_LOCALIZE_PATTERN = re.compile(
    r"setup(?:Custom)?Localize\s*\(\s*\)", re.MULTILINE
)

# Context markers for template literal prefix extraction
TEMPLATE_PREFIX_CONTEXT = re.compile(
    r"(?:localize|hass\.localize)\s*\(\s*`([^`]+)", re.MULTILINE
)


@dataclass
class I18nKeyExtractor:
    """Extractor for i18n keys from TypeScript source.

    Extracts localize() and hass.localize() calls, tracking the context
    and extracting key prefixes for template literal dynamic keys.

    Attributes:
        name: Human-readable name for the extractor.
        use_regex_fallback: Whether to use regex fallback when tree-sitter
            parsing fails.
    """

    name: str = "I18nKeyExtractor"
    use_regex_fallback: bool = True

    def extract(
        self, node: Any, raw: str, file_path: Optional[Path] = None
    ) -> List[FrontendToken]:
        """Extract I18nKey tokens from TypeScript source.

        Args:
            node: AST node from tree-sitter TypeScript parser (or raw string).
            raw: Raw source code string for context.
            file_path: Optional path to the source file.

        Returns:
            List of FrontendToken objects representing i18n keys found.
        """
        tokens: List[FrontendToken] = []

        # Try tree-sitter parsing first if node has type attribute
        if hasattr(node, 'type') and node is not None:
            tokens = self._extract_from_ast(node, raw, file_path)
            if tokens:
                return tokens

        # Fall back to regex extraction for ~85% coverage
        if self.use_regex_fallback:
            tokens = self._extract_with_regex(raw, file_path)

        return tokens

    def _extract_from_ast(
        self, node: Any, raw: str, file_path: Optional[Path]
    ) -> List[FrontendToken]:
        """Extract i18n keys using tree-sitter AST traversal.

        Args:
            node: AST node from tree-sitter.
            raw: Raw source code string.
            file_path: Optional path to source file.

        Returns:
            List of FrontendToken objects.
        """
        tokens: List[FrontendToken] = []

        try:
            tokens = self._walk_ast(node, raw, file_path or Path(""))
        except Exception as e:
            logger.debug(f"Tree-sitter extraction failed, falling back to regex: {e}")

        return tokens

    def _walk_ast(
        self, node: Any, raw: str, file_path: Path
    ) -> List[FrontendToken]:
        """Recursively walk AST to find i18n key calls.

        Args:
            node: Current AST node.
            raw: Raw source code.
            file_path: Source file path.

        Returns:
            List of FrontendToken objects found.
        """
        tokens: List[FrontendToken] = []

        # Node type check - tree-sitter nodes have 'type' attribute
        if not hasattr(node, 'type'):
            return tokens

        node_type = getattr(node, 'type', None)

        # Handle call expressions that might be localize() calls
        if node_type == 'call_expression':
            token = self._extract_call(node, raw, file_path)
            if token:
                tokens.append(token)

        # Recurse into children
        children = getattr(node, 'children', [])
        for child in children:
            tokens.extend(self._walk_ast(child, raw, file_path))

        return tokens

    def _extract_call(
        self, node: Any, raw: str, file_path: Path
    ) -> Optional[FrontendToken]:
        """Extract i18n key from a call expression node.

        Args:
            node: Call expression AST node.
            raw: Raw source code.
            file_path: Source file path.

        Returns:
            FrontendToken if i18n key found, None otherwise.
        """
        # Get function being called
        func = getattr(node, 'function', None)
        if not func:
            return None

        func_text = getattr(func, 'text', '') or ''

        # Check for localize() or hass.localize()
        context: Literal["localize", "hass.localize", "template_literal"] = "localize"
        if func_text.startswith('hass.'):
            context = "hass.localize"

        # Extract the key argument
        key = self._extract_key_from_call(node, raw, context)

        if not key:
            return None

        # Build I18nKey data
        data: I18nKey = {
            'key': key,
            'context': context,
            'prefix': None,
        }

        # Get line number
        line_number = getattr(node, 'start_point', (0, 0))[0] + 1

        return FrontendToken(
            token_type='i18n_key',
            data=data,
            file_path=file_path,
            line_number=line_number,
        )

    def _extract_key_from_call(
        self, node: Any, raw: str, context: str
    ) -> Optional[str]:
        """Extract the i18n key from a call expression.

        Args:
            node: Call expression AST node.
            raw: Raw source code.
            context: The context (localize/hass.localize/template_literal).

        Returns:
            The extracted key string or None.
        """
        # Get arguments
        args = getattr(node, 'arguments', []) or []

        for arg in args:
            arg_type = getattr(arg, 'type', '')
            arg_text = getattr(arg, 'text', '') or ''

            # String literal argument - direct key
            if arg_type == 'string':
                # Extract string content
                text = arg_text.strip()
                if text.startswith(("'", '"')):
                    return text[1:-1]
                return text

            # Template literal - dynamic key
            if arg_type == 'template_literal' or '`' in arg_text:
                # Extract prefix from template literal
                prefix = self._extract_template_prefix(arg, raw)
                if prefix:
                    return prefix

        return None

    def _extract_template_prefix(
        self, node: Any, raw: str
    ) -> Optional[str]:
        """Extract prefix from template literal for dynamic keys.

        For `ui.card.${action}`, extracts 'ui.card.' as prefix.

        Args:
            node: Template literal AST node.
            raw: Raw source code.

        Returns:
            The extracted prefix or None.
        """
        # Get template literal text
        if hasattr(node, 'text'):
            template_text = node.text
        else:
            # Try to get from source
            template_text = raw

        # Use regex to extract prefix before ${...}
        match = re.search(r'`([^`]*?)\$\{[^}]+\}', template_text)
        if match:
            prefix = match.group(1)
            # Remove trailing characters that are part of the pattern
            return prefix.rstrip()

        return None

    def _extract_with_regex(
        self, raw: str, file_path: Optional[Path]
    ) -> List[FrontendToken]:
        """Extract i18n keys using regex fallback.

        This provides ~85% coverage for v1 when tree-sitter is unavailable.

        Args:
            raw: Raw source code.
            file_path: Optional source file path.

        Returns:
            List of FrontendToken objects.
        """
        tokens: List[FrontendToken] = []
        fp = file_path or Path("")

        # Extract setupLocalize() / setupCustomlocalize() wrapper markers
        # These indicate i18n is being configured but we track actual usage
        for match in SETUP_LOCALIZE_PATTERN.finditer(raw):
            line_number = raw[:match.start()].count('\n') + 1
            # Note: We don't emit tokens for setup calls, just track that
            # the file uses i18n. Actual keys come from localize() calls.

        # Find all localize('key') occurrences
        for match in LOCALIZE_CALL_PATTERN.finditer(raw):
            key = match.group(1)
            line_number = raw[:match.start()].count('\n') + 1

            data: I18nKey = {
                'key': key,
                'context': 'localize',
                'prefix': None,
            }

            tokens.append(FrontendToken(
                token_type='i18n_key',
                data=data,
                file_path=fp,
                line_number=line_number,
            ))

        # Find all hass.localize('key') occurrences
        for match in HASS_LOCALIZE_PATTERN.finditer(raw):
            key = match.group(1)
            line_number = raw[:match.start()].count('\n') + 1

            data: I18nKey = {
                'key': key,
                'context': 'hass.localize',
                'prefix': None,
            }

            tokens.append(FrontendToken(
                token_type='i18n_key',
                data=data,
                file_path=fp,
                line_number=line_number,
            ))

        # Find template literals used with localize calls
        # Pattern: localize(`prefix${dynamic}`)
        for match in TEMPLATE_PREFIX_CONTEXT.finditer(raw):
            template_content = match.group(1)
            line_number = raw[:match.start()].count('\n') + 1

            # Extract prefix before ${...}
            prefix_match = re.match(r'^([^$\{]+)', template_content)
            if prefix_match:
                prefix = prefix_match.group(1)

                data: I18nKey = {
                    'key': prefix,  # Prefix only for template literals
                    'context': 'template_literal',
                    'prefix': prefix,
                }

                tokens.append(FrontendToken(
                    token_type='i18n_key',
                    data=data,
                    file_path=fp,
                    line_number=line_number,
                ))

        return tokens


# Protocol conformance check
# I18nKeyExtractor implements TypeScriptExtractorProtocol
assert hasattr(I18nKeyExtractor, 'extract')
assert hasattr(I18nKeyExtractor, 'name')