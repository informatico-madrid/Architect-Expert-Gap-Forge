# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
LitComponentExtractor - TypeScript extractor for Lit web components.

This module provides extraction of Lit web components from TypeScript source
via @customElement decorator detection and related patterns.

Uses tree-sitter primarily for AST parsing, with regex fallback (~85% coverage)
for v1 as specified in the design.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional

from src.utils.extractors.extractors.base import (
    FrontendToken,
    LitComponent,
    TypeScriptExtractorProtocol,
)

logger = logging.getLogger(__name__)

# Regex patterns for fallback extraction (v1 ~85% coverage)
# Matches @customElement('tag-name') or @customElement("tag-name")
CUSTOM_ELEMENT_PATTERN = re.compile(
    r"@customElement\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", re.MULTILINE
)

# Matches class Foo extends LitElement
CLASS_EXTENDS_PATTERN = re.compile(
    r"class\s+(\w+)\s+extends\s+(\w+(?:\s+implements\s+\w+)?)", re.MULTILINE
)

# Matches @property decorator on class
PROPERTY_DECORATOR_PATTERN = re.compile(
    r"@property\s*\(\s*\{", re.MULTILINE
)

# Matches @state decorator
STATE_DECORATOR_PATTERN = re.compile(
    r"@state\s*\(\s*\{", re.MULTILINE
)

# Matches @customElement decorator on class declaration
DECORATOR_CLASS_PATTERN = re.compile(
    r"@(?:customElement|property|state)\s*(?:\([^)]*\))?\s*\n\s*class\s+(\w+)",
    re.MULTILINE
)


@dataclass
class LitComponentExtractor:
    """Extractor for Lit web components from TypeScript source.

    Extracts @customElement decorated classes, their tag names, properties,
    states, and superclass information.

    Attributes:
        name: Human-readable name for the extractor.
        use_regex_fallback: Whether to use regex fallback when tree-sitter
            parsing fails.
    """

    name: str = "LitComponentExtractor"
    use_regex_fallback: bool = True

    # Track aliased imports for decorator resolution
    _import_aliases: dict[str, str] = field(default_factory=dict)

    def extract(
        self, node: Any, raw: str, file_path: Optional[Path] = None
    ) -> List[FrontendToken]:
        """Extract LitComponent tokens from TypeScript source.

        Args:
            node: AST node from tree-sitter TypeScript parser (or raw string).
            raw: Raw source code string for context.
            file_path: Optional path to the source file.

        Returns:
            List of FrontendToken objects representing Lit components found.
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
        """Extract Lit components using tree-sitter AST traversal.

        Args:
            node: AST node from tree-sitter.
            raw: Raw source code string.
            file_path: Optional path to source file.

        Returns:
            List of FrontendToken objects.
        """
        tokens: List[FrontendToken] = []

        # Walk the tree to find class declarations with decorators
        # This method is called when tree-sitter is available
        try:
            tokens = self._walk_ast(node, raw, file_path or Path(""))
        except Exception as e:
            logger.debug(f"Tree-sitter extraction failed, falling back to regex: {e}")

        return tokens

    def _walk_ast(
        self, node: Any, raw: str, file_path: Path
    ) -> List[FrontendToken]:
        """Recursively walk AST to find Lit component declarations.

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

        # Handle class declarations
        if node_type == 'class_declaration':
            class_token = self._extract_class(node, raw, file_path)
            if class_token:
                tokens.append(class_token)

        # Handle decorator_attached_scopes (if available in tree-sitter)
        # Handle export statements that may contain classes
        if node_type == 'export_statement':
            children = getattr(node, 'children', [])
            for child in children:
                tokens.extend(self._walk_ast(child, raw, file_path))

        # Recurse into children
        children = getattr(node, 'children', [])
        for child in children:
            tokens.extend(self._walk_ast(child, raw, file_path))

        return tokens

    def _extract_class(
        self, node: Any, raw: str, file_path: Path
    ) -> Optional[FrontendToken]:
        """Extract Lit component from a class declaration node.

        Args:
            node: Class declaration AST node.
            raw: Raw source code.
            file_path: Source file path.

        Returns:
            FrontendToken if Lit component found, None otherwise.
        """
        # Get class name
        class_name = self._get_class_name(node)
        if not class_name:
            return None

        # Get superclass
        super_class = self._get_super_class(node)

        # Check for decorators
        decorators = self._get_decorators(node, raw)

        # Check if this is a Lit component via @customElement
        custom_element_tag = None
        properties: List[str] = []
        states: List[str] = []
        observed_attributes: List[str] = []

        for decorator in decorators:
            if decorator.get('type') == 'customElement':
                custom_element_tag = decorator.get('tag_name')
            elif decorator.get('type') == 'property':
                prop_name = decorator.get('name', '')
                if prop_name:
                    properties.append(prop_name)
            elif decorator.get('type') == 'state':
                state_name = decorator.get('name', '')
                if state_name:
                    states.append(state_name)

        if not custom_element_tag:
            return None

        # Determine observed attributes from properties
        observed_attributes = self._derive_observed_attributes(properties)

        # Build LitComponent data
        data: LitComponent = {
            'tag_name': custom_element_tag,
            'class_name': class_name,
            'properties': properties,
            'states': states,
            'super_class': super_class,
            'observed_attributes': observed_attributes,
            'decorators': [d.get('type', '') for d in decorators],
        }

        # Get line number
        line_number = getattr(node, 'start_point', (0, 0))[0] + 1

        return FrontendToken(
            token_type='lit_component',
            data=data,
            file_path=file_path,
            line_number=line_number,
        )

    def _get_class_name(self, node: Any) -> Optional[str]:
        """Extract class name from class declaration node.

        Args:
            node: Class declaration AST node.

        Returns:
            Class name string or None.
        """
        # tree-sitter class_declaration has 'name' attribute
        name = getattr(node, 'name', None)
        if name and hasattr(name, 'text'):
            return name.text
        if name and isinstance(name, str):
            return name

        # Try to get from child nodes
        if hasattr(node, 'children'):
            for child in node.children:
                if getattr(child, 'type', '') == 'identifier':
                    return getattr(child, 'text', None)

        return None

    def _get_super_class(self, node: Any) -> Optional[str]:
        """Extract superclass name from class declaration.

        Args:
            node: Class declaration AST node.

        Returns:
            Superclass name or None.
        """
        if hasattr(node, 'superclass'):
            superclass = node.superclass
            if superclass and hasattr(superclass, 'text'):
                return superclass.text
            if superclass and hasattr(superclass, 'name'):
                name = superclass.name
                if hasattr(name, 'text'):
                    return name.text
                return str(name) if name else None

        # Check children for extends clause
        if hasattr(node, 'children'):
            for child in node.children:
                child_type = getattr(child, 'type', '')
                if 'extends' in child_type.lower() or 'superclass' in child_type.lower():
                    if hasattr(child, 'text'):
                        return child.text
                    if hasattr(child, 'name'):
                        name = child.name
                        if hasattr(name, 'text'):
                            return name.text

        return None

    def _get_decorators(
        self, node: Any, raw: str
    ) -> List[dict[str, Any]]:
        """Extract decorators from class declaration.

        Args:
            node: Class declaration AST node.
            raw: Raw source code for context.

        Returns:
            List of decorator information dictionaries.
        """
        decorators: List[dict[str, Any]] = []

        # Look for decorator_attached_scopes or decorators as children
        if hasattr(node, 'decorators'):
            for dec in node.decorators:
                dec_info = self._parse_decorator(dec, raw)
                if dec_info:
                    decorators.append(dec_info)

        # Also scan for decorators in preceding siblings (decorators on same line)
        if hasattr(node, 'start_point') and hasattr(node, 'end_point'):
            start_line = node.start_point[0] if node.start_point else 0
            # Get preceding lines for decorators
            lines = raw.split('\n')
            search_start = max(0, start_line - 3)
            search_lines = lines[search_start:start_line + 1]
            context = '\n'.join(search_lines)

            # Parse decorators from context
            decorators.extend(self._extract_decorators_from_context(context))

        return decorators

    def _parse_decorator(
        self, node: Any, raw: str
    ) -> Optional[dict[str, Any]]:
        """Parse a single decorator node.

        Args:
            node: Decorator AST node.
            raw: Raw source for context.

        Returns:
            Decorator info dict or None.
        """
        dec_type = getattr(node, 'type', '')
        dec_name = getattr(node, 'text', '')

        if 'customElement' in dec_name or dec_name == 'customElement':
            # Extract tag name from arguments
            tag_name = self._extract_tag_from_decorator(node)
            return {'type': 'customElement', 'tag_name': tag_name}

        if dec_type == 'decorator' or 'property' in dec_name:
            # @property decorator
            name = self._extract_decorator_name(node, 'property')
            return {'type': 'property', 'name': name}

        if 'state' in dec_name:
            # @state decorator
            name = self._extract_decorator_name(node, 'state')
            return {'type': 'state', 'name': name}

        return None

    def _extract_tag_from_decorator(self, node: Any) -> Optional[str]:
        """Extract tag name from @customElement decorator.

        Args:
            node: Decorator node.

        Returns:
            Tag name string or None.
        """
        # Look for string literal arguments in decorator call
        if hasattr(node, 'children'):
            for child in node.children:
                child_type = getattr(child, 'type', '')
                if child_type == 'string':
                    return getattr(child, 'text', None).strip('"\'')
                if child_type == 'call_expression':
                    return self._extract_tag_from_decorator(child)

        # Check for identifier (constant reference) - mark as unresolved
        if hasattr(node, 'text'):
            text = node.text
            if '@customElement' in text:
                # Try to extract from string literal in the text
                match = re.search(r"['\"]([^'\"]+)['\"]", text)
                if match:
                    return match.group(1)

        return None

    def _extract_decorator_name(
        self, node: Any, decorator_type: str
    ) -> str:
        """Extract property/state name from decorator.

        Args:
            node: Decorator AST node.
            decorator_type: 'property' or 'state'.

        Returns:
            Property/state name.
        """
        # Try to get from node structure
        if hasattr(node, 'children'):
            for child in node.children:
                child_type = getattr(child, 'type', '')
                if child_type == 'property_identifier':
                    return getattr(child, 'text', '')
                if child_type == 'identifier':
                    return getattr(child, 'text', '')

        # Try text extraction
        if hasattr(node, 'text'):
            text = node.text
            if decorator_type == 'property':
                # Look for 'name' or 'attribute' key in options
                match = re.search(r"name\s*:\s*['\"](\w+)['\"]", text)
                if match:
                    return match.group(1)
            else:
                # For @state, name is usually a simple identifier after @state
                match = re.search(r"@state.*?(\w+)", text)
                if match:
                    return match.group(1)

        return ''

    def _extract_decorators_from_context(
        self, context: str
    ) -> List[dict[str, Any]]:
        """Extract decorators from surrounding context text.

        Args:
            context: Source code context.

        Returns:
            List of decorator info dictionaries.
        """
        decorators: List[dict[str, Any]] = []

        # Check for @customElement
        match = re.search(r"@customElement\s*\(\s*['\"]([^'\"]+)['\"]", context)
        if match:
            decorators.append({
                'type': 'customElement',
                'tag_name': match.group(1),
            })

        # Check for @property
        prop_matches = re.finditer(
            r"@property\s*\(\s*\{[^}]*name\s*:\s*['\"](\w+)['\"]",
            context
        )
        for match in prop_matches:
            decorators.append({
                'type': 'property',
                'name': match.group(1),
            })

        # Check for @state
        state_matches = re.finditer(r"@state\s*\(\s*\{[^}]*\}", context)
        for match in state_matches:
            # @state without options - extract variable name from following context
            # This is approximate - more precise parsing requires AST
            decorators.append({
                'type': 'state',
                'name': '',  # Requires AST for precise name
            })

        return decorators

    def _derive_observed_attributes(self, properties: List[str]) -> List[str]:
        """Derive observed attributes from property names.

        LitElement observes properties that are explicitly listed or derived
        from property names (lowercase by default).

        Args:
            properties: List of property names.

        Returns:
            List of observed attribute names.
        """
        return [prop.lower() for prop in properties if prop]

    def _extract_with_regex(
        self, raw: str, file_path: Optional[Path]
    ) -> List[FrontendToken]:
        """Extract Lit components using regex fallback.

        This provides ~85% coverage for v1 when tree-sitter is unavailable.

        Args:
            raw: Raw source code.
            file_path: Optional source file path.

        Returns:
            List of FrontendToken objects.
        """
        tokens: List[FrontendToken] = []
        fp = file_path or Path("")

        # Find all @customElement occurrences
        for match in CUSTOM_ELEMENT_PATTERN.finditer(raw):
            tag_name = match.group(1)
            line_number = raw[:match.start()].count('\n') + 1

            # Find the class that follows this decorator
            class_name = None
            super_class = None
            properties: List[str] = []
            states: List[str] = []
            decorators: List[str] = ['customElement']

            # Look backward for class declaration near the decorator
            context_start = max(0, match.start() - 200)
            context = raw[context_start:match.end() + 500]

            # Extract class name if follows decorator
            class_match = re.search(
                r"class\s+(\w+)\s+extends\s+(\w+)",
                context
            )
            if class_match:
                class_name = class_match.group(1)
                super_class = class_match.group(2)

            # Look for @property decorators in a wider window
            prop_context = raw[max(0, match.start() - 1000):match.end() + 2000]
            for prop_match in re.finditer(
                r"@property\s*\([^)]*name\s*:\s*['\"](\w+)['\"]",
                prop_context
            ):
                properties.append(prop_match.group(1))
                decorators.append('property')

            # Look for @state decorators
            for state_match in re.finditer(r"@state\s*\(", prop_context):
                states.append('')
                decorators.append('state')

            if class_name and tag_name:
                data: LitComponent = {
                    'tag_name': tag_name,
                    'class_name': class_name,
                    'properties': properties,
                    'states': states,
                    'super_class': super_class,
                    'observed_attributes': [p.lower() for p in properties],
                    'decorators': decorators,
                }

                tokens.append(FrontendToken(
                    token_type='lit_component',
                    data=data,
                    file_path=fp,
                    line_number=line_number,
                ))

        return tokens


# Protocol conformance check
# LitComponentExtractor implements TypeScriptExtractorProtocol
assert hasattr(LitComponentExtractor, 'extract')
assert hasattr(LitComponentExtractor, 'name')