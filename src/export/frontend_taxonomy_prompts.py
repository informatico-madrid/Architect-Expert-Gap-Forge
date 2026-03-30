#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Frontend taxonomy prompts for component extraction.

Contains system prompts and user prompts for extracting frontend component
information including Lit web components, i18n keys, and service calls.

SPDX-License-Identifier: Apache-2.0
Copyright 2026 AEGF
"""

from __future__ import annotations

from dataclasses import dataclass


# JSON Schema for component_summary output
COMPONENT_SUMMARY_SCHEMA = {
    "tag": "string - HTML custom element tag name",
    "class": "string - JavaScript/TypeScript class name",
    "file_path": "string - Relative path to the source file",
    "props": "array of string - Component property names",
    "events": "array of string - DOM event names the component fires",
    "service_calls": "array of objects with domain, service, entity_ids",
    "i18n_keys": "array of objects with key and context",
}


# System prompt for frontend component extraction
FRONTEND_COMPONENT_SYSTEM_PROMPT = """You are a frontend component analyzer specializing in Lit web components.

Your task is to extract structured information from TypeScript/JavaScript source code
and produce JSON output following the component_summary schema.

## Output Schema
{schema}

## Extraction Guidelines

### Lit Components
- Extract the @customElement decorator tag name
- Extract the class name
- Extract @property and @state decorator names as props
- Track DOM events (fire, fireEvent, dispatchEvent patterns)

### I18n Keys
- Extract localize() and hass.localize() calls
- Track template literal patterns with key prefixes
- Normalize keys to dot-notation (e.g., ui.card.door.lock)

### Service Calls
- Extract hass.callService() patterns
- Identify domain and service names
- Extract entity_id references from service data

## Important
- Keep prompts generic and framework-agnostic
- Do not assume HomeAssistant-specific behavior
- Use null for missing fields, empty arrays for missing lists
- Return ONLY the JSON object, no explanations""".format(
    schema="\n".join(f"  {k}: {v}" for k, v in COMPONENT_SUMMARY_SCHEMA.items())
)


# User prompt for component extraction
EXTRACT_COMPONENT_USER_PROMPT = """Extract the component information from the following source code.

Source file: {file_path}

```typescript
{source_code}
```

Provide a JSON object with the component summary following the schema."""


# System prompt for Lit component extraction specifically
LIT_COMPONENT_SYSTEM_PROMPT = """You are a Lit web component analyzer.

Extract Lit component information from TypeScript source code.

## Lit Component Schema
- tag_name: string - The @customElement tag name (e.g., 'ha-dialog')
- class_name: string - The component class name
- properties: string[] - @property decorator names
- states: string[] - @state decorator names
- super_class: string | null - Super class (usually LitElement)
- observed_attributes: string[] - Observed attribute names
- decorators: string[] - All detected decorators

## Example
```typescript
@customElement('ha-dialog')
@property({ type: Boolean }) public isOpen = false;
@state() private _myState = false;
export class HaDialog extends LitElement {
```

Should extract:
{{
  "tag_name": "ha-dialog",
  "class_name": "HaDialog",
  "properties": ["isOpen"],
  "states": ["_myState"],
  "super_class": "LitElement",
  "observed_attributes": [],
  "decorators": ["customElement", "property", "state"]
}}

Return ONLY the JSON object."""


# System prompt for i18n key extraction
I18N_KEY_SYSTEM_PROMPT = """You are an internationalization key analyzer for frontend code.

Extract i18n keys from TypeScript/JavaScript source code.

## I18n Key Schema
- key: string - Translation key in dot-notation
- context: 'localize' | 'hass.localize' | 'template_literal'
- prefix: string | null - Template literal prefix if applicable

## Extraction Patterns
- localize('key') → context: 'localize'
- hass.localize('key') → context: 'hass.localize'
- `${prefix}key` in template literal → context: 'template_literal'

Return ONLY the JSON array of found keys."""


# System prompt for service call extraction
SERVICE_CALL_SYSTEM_PROMPT = """You are a service call analyzer for frontend code.

Extract service call patterns from TypeScript/JavaScript source code.

## Service Call Schema
- domain: string - Service domain (e.g., 'light', 'switch')
- service: string - Service name (e.g., 'turn_on', 'toggle')
- entity_ids: string[] - Entity IDs found in service data
- hass_prefix: string - How hass was referenced ('this.hass', 'hass', etc.)

## Extraction Patterns
- hass.callService(domain, service, data) → extract domain, service, entity_ids
- this.hass.callService(...) → hass_prefix: 'this.hass'
- context._hass.callService(...) → hass_prefix: 'context._hass'

Return ONLY the JSON array of service calls."""


@dataclass
class FrontendTaxonomyPrompts:
    """Collection of prompt templates for frontend component extraction.

    Provides system prompts and user prompts for extracting:
    - Lit web components
    - I18n keys
    - Service calls

    Example:
        >>> from src.export.frontend_taxonomy_prompts import FrontendTaxonomyPrompts
        >>> prompts = FrontendTaxonomyPrompts()
        >>> print(prompts.component_system)
    """

    @property
    def component_system(self) -> str:
        """System prompt for general component extraction."""
        return FRONTEND_COMPONENT_SYSTEM_PROMPT

    @property
    def lit_component_system(self) -> str:
        """System prompt for Lit component extraction."""
        return LIT_COMPONENT_SYSTEM_PROMPT

    @property
    def i18n_key_system(self) -> str:
        """System prompt for i18n key extraction."""
        return I18N_KEY_SYSTEM_PROMPT

    @property
    def service_call_system(self) -> str:
        """System prompt for service call extraction."""
        return SERVICE_CALL_SYSTEM_PROMPT

    def extract_component_user(
        self,
        file_path: str,
        source_code: str,
    ) -> str:
        """Build user prompt for component extraction.

        Args:
            file_path: Path to the source file.
            source_code: Source code content.

        Returns:
            Formatted user prompt string.
        """
        return EXTRACT_COMPONENT_USER_PROMPT.format(
            file_path=file_path,
            source_code=source_code,
        )