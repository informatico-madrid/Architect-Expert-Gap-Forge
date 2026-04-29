# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Base types and interfaces for TypeScript extractors.

This module defines the core abstractions for TypeScript-specific extractors:
- TypeScriptExtractorProtocol: Protocol for TypeScript extractors
- FrontendToken: Base dataclass for extracted tokens
- LitComponent: TypedDict for Lit web component tokens
- I18nKey: TypedDict for i18n key tokens
- ServiceCall: TypedDict for service call tokens
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Literal, Protocol, runtime_checkable

logger = logger = __import__("logging").getLogger(__name__)


@runtime_checkable
class TypeScriptExtractorProtocol(Protocol):
    """Protocol defining the interface for TypeScript-specific extractors.

    All TypeScript extractors must implement this protocol to provide
    consistent token extraction across different TypeScript patterns.

    Attributes:
        name: Human-readable name for the extractor.
    """

    name: str

    def extract(self, node: Any, raw: str) -> List["FrontendToken"]:
        """Extract FrontendTokens from a TypeScript AST node.

        Args:
            node: AST node from tree-sitter TypeScript parser.
            raw: Raw source code string for context.

        Returns:
            List of FrontendToken objects found in the node.
        """
        ...


@dataclass
class FrontendToken:
    """Base dataclass representing an extracted token from TypeScript source.

    Attributes:
        token_type: Classification of the token type
            (e.g., "lit_component", "i18n_key", "service_call").
        data: TypedDict containing token-specific data.
        file_path: Path to the source file where the token was found.
        line_number: Line number where the token was found (1-indexed).
    """

    token_type: str
    data: dict[str, Any]
    file_path: Path
    line_number: int


# Output schema for LitComponent tokens
class LitComponent(dict):
    """TypedDict representing a Lit web component token.

    Schema:
        tag_name: str - The HTML tag name (e.g., 'ha-dialog').
        class_name: str - The JavaScript/TypeScript class name.
        properties: List[str] - Property decorator names.
        states: List[str] - State decorator names.
        super_class: str | None - The super class (e.g., 'LitElement').
        observed_attributes: List[str] - Observed attribute names.
        decorators: List[str] - All detected decorators.
    """

    tag_name: str
    class_name: str
    properties: List[str]
    states: List[str]
    super_class: str | None
    observed_attributes: List[str]
    decorators: List[str]


# Output schema for I18nKey tokens
class I18nKey(dict):
    """TypedDict representing an internationalization key token.

    Schema:
        key: str - The translation key (e.g., 'ui.card.door.lock').
        context: Literal['localize', 'hass.localize', 'template_literal'] -
            How the key was accessed.
        prefix: str | None - Template literal prefix if context is 'template_literal'.
    """

    key: str
    context: Literal["localize", "hass.localize", "template_literal"]
    prefix: str | None


# Output schema for ServiceCall tokens
class ServiceCall(dict):
    """TypedDict representing a Home Assistant service call token.

    Schema:
        domain: str - The service domain (e.g., 'light', 'switch').
        service: str - The service name (e.g., 'turn_on', 'toggle').
        entity_ids: List[str] - Entity IDs in the service data.
        hass_prefix: str - How hass was referenced ('this.hass', 'context._hass', 'hass').
    """

    domain: str
    service: str
    entity_ids: List[str]
    hass_prefix: str
