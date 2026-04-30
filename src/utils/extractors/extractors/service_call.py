# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
ServiceCallExtractor - TypeScript extractor for Home Assistant service calls.

This module provides extraction of Home Assistant service calls from TypeScript
source via hass.callService() call detection.

Uses tree-sitter primarily for AST parsing, with regex fallback (~85% coverage)
for v1 as specified in the design.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional

from src.utils.extractors.extractors.base import (
    FrontendToken,
    ServiceCall,
    TypeScriptExtractorProtocol,
)

logger = logging.getLogger(__name__)

# Regex patterns for fallback extraction (v1 ~85% coverage)

# Matches hass.callService(domain, service, data) with various prefixes
# Supports: hass, this.hass, context._hass
# Pattern: (?:this\.)?hass matches 'this.hass' or 'hass'
# Pattern: context\._hass matches 'context._hass'
# Combined with | for alternation
CALLSERVICE_PATTERN = re.compile(
    r"(?:(?:this\.)?hass|context\._hass)\.callService\s*\(\s*"
    r"['\"]([^'\"]+)['\"]\s*,\s*"
    r"['\"]([^'\"]+)['\"]\s*,?\s*"
    r"(\{[^}]*\})?",
    re.MULTILINE | re.DOTALL
)

# Standalone hass.callService pattern (no prefix variants)
HASS_CALLSERVICE_PATTERN = re.compile(
    r"(?:(?:this\.)?hass|context\._hass)\.callService\s*\(\s*"
    r"['\"]([^'\"]+)['\"]\s*,\s*"
    r"['\"]([^'\"]+)['\"]\s*,?\s*"
    r"(\{[^}]*\})?",
    re.MULTILINE | re.DOTALL
)

# Extract entity_id from service data: entity_id: 'light.living_room'
ENTITY_ID_PATTERN = re.compile(
    r"entity_id\s*:\s*['\"]([^'\"]+)['\"]",
    re.MULTILINE
)

# Extract entity_id array: entity_id: ['light.living_room', 'light.bedroom']
ENTITY_ID_ARRAY_PATTERN = re.compile(
    r"entity_id\s*:\s*\[\s*([^]]+)\]",
    re.MULTILINE
)


@dataclass
class ServiceCallExtractor:
    """Extractor for Home Assistant service calls from TypeScript source.

    Extracts hass.callService(domain, service, data) calls, tracking the
    domain, service name, entity_ids from service data, and hass prefix.

    Attributes:
        name: Human-readable name for the extractor.
        use_regex_fallback: Whether to use regex fallback when tree-sitter
            parsing fails.
    """

    name: str = "ServiceCallExtractor"
    use_regex_fallback: bool = True

    def extract(
        self, node: Any, raw: str, file_path: Optional[Path] = None
    ) -> List[FrontendToken]:
        """Extract ServiceCall tokens from TypeScript source.

        Args:
            node: AST node from tree-sitter TypeScript parser (or raw string).
            raw: Raw source code string for context.
            file_path: Optional path to the source file.

        Returns:
            List of FrontendToken objects representing service calls found.
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
        """Extract service calls using tree-sitter AST traversal.

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
        """Recursively walk AST to find callService calls.

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

        # Handle call expressions that might be callService calls
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
        """Extract service call from a call expression node.

        Args:
            node: Call expression AST node.
            raw: Raw source code.
            file_path: Source file path.

        Returns:
            FrontendToken if service call found, None otherwise.
        """
        # Get function being called
        func = getattr(node, 'function', None)
        if not func:
            return None

        func_text = getattr(func, 'text', '') or ''

        # Check if this is a callService call
        if not self._is_call_service(func_text):
            return None

        # Extract hass prefix
        hass_prefix = self._extract_hass_prefix(func_text)

        # Extract domain, service, and data from arguments
        args = getattr(node, 'arguments', []) or []
        domain, service, entity_ids = self._extract_arguments(args, raw)

        if not domain or not service:
            return None

        # Build ServiceCall data
        data: ServiceCall = {
            'domain': domain,
            'service': service,
            'entity_ids': entity_ids,
            'hass_prefix': hass_prefix,
        }

        # Get line number
        line_number = getattr(node, 'start_point', (0, 0))[0] + 1

        return FrontendToken(
            token_type='service_call',
            data=data,
            file_path=file_path,
            line_number=line_number,
        )

    def _is_call_service(self, func_text: str) -> bool:
        """Check if function text is a callService call.

        Args:
            func_text: The function text (e.g., 'hass.callService').

        Returns:
            True if this is a callService call.
        """
        return 'callService' in func_text

    def _extract_hass_prefix(self, func_text: str) -> str:
        """Extract the hass prefix from function text.

        Args:
            func_text: The function text (e.g., 'this.hass.callService').

        Returns:
            The hass prefix ('this.hass', 'context._hass', or 'hass').
        """
        if 'this.hass' in func_text:
            return 'this.hass'
        elif 'context._hass' in func_text or '_hass' in func_text:
            return 'context._hass'
        return 'hass'

    def _extract_arguments(
        self, args: list, raw: str
    ) -> tuple[Optional[str], Optional[str], List[str]]:
        """Extract domain, service, and entity_ids from call arguments.

        Args:
            args: List of AST argument nodes.
            raw: Raw source code for fallback extraction.

        Returns:
            Tuple of (domain, service, entity_ids).
        """
        domain: Optional[str] = None
        service: Optional[str] = None
        entity_ids: List[str] = []

        for i, arg in enumerate(args):
            arg_type = getattr(arg, 'type', '')
            arg_text = getattr(arg, 'text', '') or ''

            # First arg: domain (string literal)
            if i == 0 and arg_type == 'string':
                domain = arg_text.strip()
                if domain and domain.startswith(("'", '"')):
                    domain = domain[1:-1]

            # Second arg: service (string literal)
            elif i == 1 and arg_type == 'string':
                service = arg_text.strip()
                if service and service.startswith(("'", '"')):
                    service = service[1:-1]

            # Third arg: service data (object literal)
            elif i == 2 and (arg_type == 'object' or '{' in arg_text):
                entity_ids = self._extract_entity_ids_from_data(arg, raw)

        return domain, service, entity_ids

    def _extract_entity_ids_from_data(
        self, data_node: Any, raw: str
    ) -> List[str]:
        """Extract entity_ids from service data object.

        Args:
            data_node: The service data AST node.
            raw: Raw source code for fallback extraction.

        Returns:
            List of entity_id strings.
        """
        entity_ids: List[str] = []

        # Try to get from AST properties
        if hasattr(data_node, 'children'):
            for child in data_node.children:
                if getattr(child, 'type', '') == 'property':
                    key = getattr(child, 'text', '') or ''
                    if 'entity_id' in key:
                        # Extract value
                        value_node = getattr(child, 'value', None)
                        if value_node:
                            value_text = getattr(value_node, 'text', '') or ''
                            # Handle array or single value
                            if '[' in value_text:
                                # Array: ['id1', 'id2']
                                entity_ids = self._extract_ids_from_array(value_text)
                            else:
                                # Single value: 'entity_id'
                                entity_id = value_text.strip()
                                if entity_id.startswith(("'", '"')):
                                    entity_id = entity_id[1:-1]
                                if entity_id:
                                    entity_ids.append(entity_id)

        # Fallback: extract from raw text
        if not entity_ids and hasattr(data_node, 'text'):
            entity_ids = self._extract_ids_from_raw_text(data_node.text)

        return entity_ids

    def _extract_ids_from_array(self, array_text: str) -> List[str]:
        """Extract entity IDs from array text.

        Args:
            array_text: Text like "['light.living_room', 'light.bedroom']".

        Returns:
            List of entity ID strings.
        """
        entity_ids: List[str] = []
        # Find all quoted strings in the array
        matches = re.findall(r"['\"]([^'\"]+)['\"]", array_text)
        for match in matches:
            if match and not match.startswith('['):
                entity_ids.append(match)
        return entity_ids

    def _extract_ids_from_raw_text(self, text: str) -> List[str]:
        """Extract entity IDs from raw text using regex.

        Args:
            text: Raw text of the service data object.

        Returns:
            List of entity ID strings.
        """
        entity_ids: List[str] = []

        # Try single entity_id first
        for match in ENTITY_ID_PATTERN.finditer(text):
            entity_id = match.group(1)
            if entity_id:
                entity_ids.append(entity_id)

        # Try array form
        if not entity_ids:
            for match in ENTITY_ID_ARRAY_PATTERN.finditer(text):
                array_content = match.group(1)
                # Extract individual IDs from array
                ids = re.findall(r"['\"]([^'\"]+)['\"]", array_content)
                entity_ids.extend(ids)

        return entity_ids

    def _extract_with_regex(
        self, raw: str, file_path: Optional[Path]
    ) -> List[FrontendToken]:
        """Extract service calls using regex fallback.

        This provides ~85% coverage for v1 when tree-sitter is unavailable.

        Args:
            raw: Raw source code.
            file_path: Optional source file path.

        Returns:
            List of FrontendToken objects.
        """
        tokens: List[FrontendToken] = []
        fp = file_path or Path("")

        # Pattern to match callService calls with various hass prefixes
        # Matches: hass.callService('domain', 'service', {entity_id: 'light.living_room'})
        # Also matches: this.hass.callService, context._hass.callService

        # Find all callService occurrences
        for match in HASS_CALLSERVICE_PATTERN.finditer(raw):
            domain = match.group(1)
            service = match.group(2)
            data_text = match.group(3) if match.group(3) else ''

            # Determine hass prefix from context
            # Find what prefix is used before .callService
            prefix_match = re.search(
                r"(this\.hass|context\._hass|this\.hass)\.callService",
                raw[max(0, match.start() - 20):match.end()]
            )
            hass_prefix = 'hass'
            if prefix_match:
                prefix = prefix_match.group(1)
                if prefix == 'this.hass':
                    hass_prefix = 'this.hass'
                elif prefix == 'context._hass':
                    hass_prefix = 'context._hass'

            # Extract entity_ids from data
            entity_ids: List[str] = []

            # Check for entity_id: 'single_id' pattern
            entity_id_match = re.search(
                r"entity_id\s*:\s*['\"]([^'\"]+)['\"]",
                data_text
            )
            if entity_id_match:
                entity_ids.append(entity_id_match.group(1))
            else:
                # Check for entity_id: ['id1', 'id2'] pattern
                array_match = re.search(
                    r"entity_id\s*:\s*\[\s*([^\]]+)\]",
                    data_text
                )
                if array_match:
                    array_content = array_match.group(1)
                    ids = re.findall(r"['\"]([^'\"]+)['\"]", array_content)
                    entity_ids.extend(ids)

            line_number = raw[:match.start()].count('\n') + 1

            data: ServiceCall = {
                'domain': domain,
                'service': service,
                'entity_ids': entity_ids,
                'hass_prefix': hass_prefix,
            }

            tokens.append(FrontendToken(
                token_type='service_call',
                data=data,
                file_path=fp,
                line_number=line_number,
            ))

        return tokens


# Protocol conformance check
# ServiceCallExtractor implements TypeScriptExtractorProtocol
assert hasattr(ServiceCallExtractor, 'extract')
assert hasattr(ServiceCallExtractor, 'name')