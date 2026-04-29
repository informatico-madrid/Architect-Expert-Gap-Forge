#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
ChatML Exporter for frontend knowledge extraction.

Generates ChatML JSONL training data from extracted FrontendTokens.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from typing import Iterator
from pathlib import Path
from typing import Any

from src.utils.extractors.extractors.base import FrontendToken

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """Single message in a ChatML conversation.

    Attributes:
        role: Message role - system, user, or assistant.
        content: Message content text.
    """

    role: str
    content: str


@dataclass
class ChatMLRecord:
    """A ChatML record containing messages for training.

    Attributes:
        messages: List of Message objects forming the conversation.
        meta: Optional metadata with source and file information.
    """

    messages: list[Message]
    meta: dict[str, str] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {"messages": [asdict(m) for m in self.messages]}
        if self.meta:
            result["meta"] = self.meta
        return result


class ChatMLExporter:
    """Exports FrontendTokens to ChatML JSONL format.

    Converts extracted frontend knowledge (Lit components, i18n keys,
    service calls) into ChatML-formatted training records.

    Example:
        >>> from src.export.chatml_exporter import ChatMLExporter
        >>> exporter = ChatMLExporter()
        >>> tokens = [FrontendToken(token_type="lit_component", data={...}, file_path=Path("test.ts"), line_number=1)]
        >>> for record in exporter.export(tokens, "You are a helpful assistant"):
        ...     print(record.to_dict())
    """

    def export(
        self,
        tokens: list[FrontendToken],
        system_prompt: str,
    ) -> Iterator[ChatMLRecord]:
        """Export FrontendTokens as ChatML records.

        Each token becomes a ChatML record with:
        - System message: schema context and extraction instructions
        - User message: source code snippet and extraction prompt
        - Assistant message: structured JSON output of the token

        Args:
            tokens: List of FrontendToken objects to export.
            system_prompt: Base system prompt for the conversation.

        Yields:
            ChatMLRecord objects for each token.
        """
        for token in tokens:
            # Build system message with schema context
            system_content = self._build_system_message(token, system_prompt)

            # Build user message with source snippet
            user_content = self._build_user_message(token)

            # Build assistant message with structured JSON output
            assistant_content = self._build_assistant_message(token)

            messages = [
                Message(role="system", content=system_content),
                Message(role="user", content=user_content),
                Message(role="assistant", content=assistant_content),
            ]

            meta = {
                "source": token.token_type,
                "file": str(token.file_path),
            }

            yield ChatMLRecord(messages=messages, meta=meta)

    def _build_system_message(
        self,
        token: FrontendToken,
        base_prompt: str,
    ) -> str:
        """Build system message with schema context.

        Args:
            token: The FrontendToken being exported.
            base_prompt: Base system prompt.

        Returns:
            Formatted system message with schema context.
        """
        schema_context = self._get_schema_context(token.token_type)
        return f"{base_prompt}\n\n{schema_context}"

    def _get_schema_context(self, token_type: str) -> str:
        """Get schema context for a token type.

        Args:
            token_type: Type of the token.

        Returns:
            Schema description string.
        """
        schemas = {
            "lit_component": """Schema for lit_component tokens:
{
  "tag_name": "string - HTML tag name (e.g., 'ha-dialog')",
  "class_name": "string - JavaScript/TypeScript class name",
  "properties": ["string] - Property decorator names",
  "states": ["string] - State decorator names",
  "super_class": "string | null - Super class (e.g., 'LitElement')",
  "observed_attributes": ["string] - Observed attribute names",
  "decorators": ["string] - All detected decorators"
}""",
            "i18n_key": """Schema for i18n_key tokens:
{
  "key": "string - Translation key (e.g., 'ui.card.door.lock')",
  "context": "literal['localize', 'hass.localize', 'template_literal']",
  "prefix": "string | null - Template literal prefix if context is 'template_literal'"
}""",
            "service_call": """Schema for service_call tokens:
{
  "domain": "string - Service domain (e.g., 'light', 'switch')",
  "service": "string - Service name (e.g., 'turn_on', 'toggle')",
  "entity_ids": ["string] - Entity IDs in service data",
  "hass_prefix": "string - How hass was referenced ('this.hass', 'context._hass', 'hass')"
}""",
        }
        return schemas.get(
            token_type,
            f"Schema for {token_type} tokens:\n{json.dumps(token_type, indent=2)}",
        )

    def _build_user_message(self, token: FrontendToken) -> str:
        """Build user message with source code snippet.

        Args:
            token: The FrontendToken being exported.

        Returns:
            Formatted user message with extraction prompt.
        """
        return f"""Extract structured information from this {token.token_type} at line {token.line_number} in {token.file_path}.

Source:
{token.data}

Provide the structured JSON output following the schema."""

    def _build_assistant_message(self, token: FrontendToken) -> str:
        """Build assistant message with structured JSON output.

        Args:
            token: The FrontendToken being exported.

        Returns:
            JSON string representation of the token data.
        """
        return json.dumps(token.data, indent=2)

    def to_jsonl(
        self,
        records: Iterator[ChatMLRecord],
        output: Path,
    ) -> None:
        """Write ChatML records to JSONL file.

        Args:
            records: Iterator of ChatMLRecord objects.
            output: Path to output JSONL file.
        """
        output.parent.mkdir(parents=True, exist_ok=True)

        with open(output, "w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")

        logger.info("Exported ChatML records to %s", output)


def to_jsonl(
    records: Iterator[ChatMLRecord],
    output: Path,
) -> None:
    """Convenience function to write ChatML records to JSONL.

    Args:
        records: Iterator of ChatMLRecord objects.
        output: Path to output JSONL file.
    """
    exporter = ChatMLExporter()
    exporter.to_jsonl(records, output)
