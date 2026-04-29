#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Architect-Expert-Gap-Forge (AEGF) - Format Normalizer Module

Converts dataset records from various formats (Alpaca, ShareGPT, OpenAI Messages)
to the standard ChatML format with messages: [{role, content}].

Location: src/curation/format_normalizer.py
SPDX-License-Identifier: Apache-2.0
Copyright 2026 AEGF
"""

from __future__ import annotations

import logging
from typing import Any

from src.utils.exceptions import NormalizationError
from src.utils.schema import DatasetRecord, Message

logger = logging.getLogger(__name__)


class FormatNormalizer:
    """Normalizes dataset records from various formats to ChatML format.

    Supported input formats:
    - Alpaca: {instruction, input?, output}
    - ShareGPT: {conversations: [{from, value}]}
    - OpenAI Messages: {messages: [{role, content}]}

    Output: DatasetRecord with messages in ChatML format.
    """

    # Role mapping from ShareGPT to ChatML
    _SHAREGPT_ROLE_MAPPING: dict[str, str] = {
        "human": "user",
        "gpt": "assistant",
        "tool": "tool",
        "system": "system",
    }

    def detect_format(self, record: dict[str, Any]) -> str:
        """Detect the format of a dataset record.

        Args:
            record: A dataset record dictionary.

        Returns:
            One of: "alpaca", "sharegpt", "openai_messages", or "unknown".

        Examples:
            >>> normalizer = FormatNormalizer()
            >>> normalizer.detect_format({"instruction": "Q", "output": "A"})
            'alpaca'
            >>> normalizer.detect_format({"conversations": []})
            'sharegpt'
            >>> normalizer.detect_format({"messages": []})
            'openai_messages'
        """
        if "messages" in record and isinstance(record["messages"], list):
            return "openai_messages"

        if "conversations" in record and isinstance(record["conversations"], list):
            return "sharegpt"

        if "instruction" in record and "output" in record:
            return "alpaca"

        return "unknown"

    def _convert_alpaca(self, record: dict[str, Any]) -> list[Message]:
        """Convert Alpaca format to ChatML messages.

        Args:
            record: Alpaca format record with instruction, input?, output.

        Returns:
            List of Message objects in ChatML format.

        Raises:
            NormalizationError: If required fields are missing.
        """
        if "instruction" not in record or "output" not in record:
            raise NormalizationError(
                "Alpaca format requires both 'instruction' and 'output' fields"
            )

        instruction = record.get("instruction", "")
        input_text = record.get("input", "")
        output = record.get("output", "")

        # Concatenate instruction and input with double newline if input exists
        if input_text:
            user_content = f"{instruction}\n\n{input_text}"
        else:
            user_content = instruction

        messages = [
            Message(role="user", content=user_content),
            Message(role="assistant", content=output),
        ]

        return messages

    def _convert_sharegpt(self, record: dict[str, Any]) -> list[Message]:
        """Convert ShareGPT format to ChatML messages.

        Args:
            record: ShareGPT format record with conversations array.

        Returns:
            List of Message objects in ChatML format.

        Raises:
            NormalizationError: If conversations array is missing or invalid.
        """
        if "conversations" not in record:
            raise NormalizationError("ShareGPT format requires 'conversations' array")

        conversations = record["conversations"]

        if not isinstance(conversations, list):
            raise NormalizationError("ShareGPT 'conversations' must be a list")

        messages = []
        for conv in conversations:
            if "from" not in conv or "value" not in conv:
                raise NormalizationError(
                    "Each conversation turn must have 'from' and 'value' fields"
                )

            # Map ShareGPT role to ChatML role
            from_role = conv["from"]
            mapped_role = self._SHAREGPT_ROLE_MAPPING.get(from_role, from_role)
            content = conv["value"]

            messages.append(Message(role=mapped_role, content=content))

        return messages

    def _convert_openai_messages(self, record: dict[str, Any]) -> list[Message]:
        """Convert OpenAI Messages format to ChatML messages.

        This is essentially a passthrough since OpenAI Messages
        is already in ChatML format.

        Args:
            record: OpenAI Messages format record with messages array.

        Returns:
            List of Message objects in ChatML format.

        Raises:
            NormalizationError: If messages array is missing or invalid.
        """
        if "messages" not in record:
            raise NormalizationError("OpenAI Messages format requires 'messages' array")

        messages_data = record["messages"]

        if not isinstance(messages_data, list):
            raise NormalizationError("'messages' must be a list")

        messages = []
        for msg in messages_data:
            if "role" not in msg or "content" not in msg:
                raise NormalizationError(
                    "Each message must have 'role' and 'content' fields"
                )

            messages.append(Message(role=msg["role"], content=msg["content"]))

        return messages

    def convert(self, record: dict[str, Any]) -> DatasetRecord:
        """Convert a dataset record to ChatML format.

        Args:
            record: A dataset record in any supported format
                (Alpaca, ShareGPT, or OpenAI Messages).

        Returns:
            A DatasetRecord with messages in ChatML format.

        Raises:
            NormalizationError: If the record format is not recognized
                or conversion fails.

        Examples:
            >>> normalizer = FormatNormalizer()
            >>> result = normalizer.convert({
            ...     "instruction": "Hello",
            ...     "output": "Hi there"
            ... })
            >>> len(result.messages)
            2
            >>> result.messages[0].role
            'user'
        """
        format_type = self.detect_format(record)

        if format_type == "unknown":
            raise NormalizationError(
                "Cannot normalize record: missing required fields. "
                "Expected 'messages' (OpenAI/ChatML), 'conversations' (ShareGPT), "
                "or 'instruction' + 'output' (Alpaca)"
            )

        if format_type == "alpaca":
            messages = self._convert_alpaca(record)
        elif format_type == "sharegpt":
            messages = self._convert_sharegpt(record)
        elif format_type == "openai_messages":
            messages = self._convert_openai_messages(record)
        else:
            # This should never happen due to "unknown" check above
            raise NormalizationError(f"Unknown format type: {format_type}")

        # Preserve original metadata if present (excluding format-specific fields)
        metadata: dict[str, Any] = {}
        preserved_fields = {"origin", "type", "use_case", "token_count", "seed_id"}
        for key in preserved_fields:
            if key in record:
                metadata[key] = record[key]

        return DatasetRecord(messages=messages, metadata=metadata)
