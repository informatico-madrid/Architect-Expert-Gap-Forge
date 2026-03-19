#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Architect-Expert-Gap-Forge (AEGF) - Dedup and Validate Module

Deduplication and validation for DatasetRecord objects.
Provides SHA-256 based exact deduplication on normalized message content
and non-call validation to reject tool call artifacts.

Location: src/curation/dedup_and_validate.py

Why this module exists (vs dedup_filter.py):
- dedup_filter.py operates on RawRecord dicts (Phase 0/3 generic dedup)
- This module works with DatasetRecord type-safe models for the curated pipeline
- Adds validation layer for tool call rejection specific to chat datasets

SPDX-License-Identifier: Apache-2.0
Copyright 2026 AEGF
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from typing import Any

from src.utils.exceptions import DeduplicationError
from src.utils.schema import DatasetRecord

logger = logging.getLogger(__name__)

# Patterns to detect tool call artifacts in message content
TOOL_CALL_PATTERNS = [
    re.compile(r"<tool_call>", re.IGNORECASE),
    re.compile(r"</tool_call>", re.IGNORECASE),
    re.compile(r"<tool_calls>", re.IGNORECASE),
    re.compile(r"</tool_calls>", re.IGNORECASE),
    re.compile(r'"tool_calls"\s*:', re.IGNORECASE),
    re.compile(r'"name"\s*:\s*"[^"]+"\s*,\s*"arguments"', re.IGNORECASE),
]

# Patterns to detect XML format tool calls
XML_TOOL_CALL_PATTERNS = [
    re.compile(r"<tool_call>", re.IGNORECASE),
    re.compile(r"<tool_name>", re.IGNORECASE),
    re.compile(r"<tool_args>", re.IGNORECASE),
]

# Patterns to detect JSON format tool calls
JSON_TOOL_CALL_PATTERNS = [
    re.compile(r'"tool_calls"\s*:', re.IGNORECASE),
    re.compile(r'"name"\s*:\s*"[^"]+"\s*,\s*"arguments"', re.IGNORECASE),
    re.compile(r'{"name"\s*:\s*"[^"]+",\s*"arguments"\s*:', re.IGNORECASE),
]


def _normalize_for_hash(message_content: str) -> str:
    """Normalize message content for hashing.

    Removes extra whitespace and normalizes unicode to ensure
    consistent hashes for semantically identical content.

    Args:
        message_content: Raw message content string.

    Returns:
        Normalized content string suitable for hashing.
    """
    # Normalize whitespace: collapse multiple spaces to single space
    normalized = re.sub(r"\s+", " ", message_content.strip())
    # Normalize unicode: NFC normalization for consistent encoding
    import unicodedata

    normalized = unicodedata.normalize("NFC", normalized)
    return normalized


def _compute_message_hash(messages: list[dict[str, Any]]) -> str:
    """Compute SHA-256 hash from normalized message content.

    Args:
        messages: List of message dicts with 'role' and 'content' keys.

    Returns:
        Hexadecimal SHA-256 hash string.

    Raises:
        DeduplicationError: If hash computation fails.
    """
    try:
        # Normalize each message content and create deterministic representation
        normalized_messages = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            normalized_content = _normalize_for_hash(content)
            normalized_messages.append({"role": role, "content": normalized_content})

        # Sort keys for deterministic serialization
        content_str = json.dumps(normalized_messages, sort_keys=True, ensure_ascii=False)
        hash_obj = hashlib.sha256(content_str.encode("utf-8"))
        return hash_obj.hexdigest()
    except Exception as e:
        raise DeduplicationError(f"Failed to compute message hash: {e}") from e


def _contains_tool_call(content: str) -> bool:
    """Check if content contains tool call artifacts.

    Args:
        content: Message content string to check.

    Returns:
        True if tool call patterns are found, False otherwise.
    """
    for pattern in TOOL_CALL_PATTERNS:
        if pattern.search(content):
            return True
    return False


def _contains_xml_tool_call(content: str) -> bool:
    """Check if content contains XML format tool calls.

    Args:
        content: Message content string to check.

    Returns:
        True if XML tool call patterns are found, False otherwise.
    """
    for pattern in XML_TOOL_CALL_PATTERNS:
        if pattern.search(content):
            return True
    return False


def _contains_json_tool_call(content: str) -> bool:
    """Check if content contains JSON format tool calls.

    Args:
        content: Message content string to check.

    Returns:
        True if JSON tool call patterns are found, False otherwise.
    """
    for pattern in JSON_TOOL_CALL_PATTERNS:
        if pattern.search(content):
            return True
    return False


def detect_tool_format(messages: list[dict[str, Any]]) -> str:
    """Detect the tool format used in a record's messages.

    Analyzes all messages in a record to determine if they contain
    tool calls in XML format, JSON format, or no tool calls at all.

    Args:
        messages: List of message dicts with 'role' and 'content' keys.

    Returns:
        'xml' if XML tool calls are detected, 'json' if JSON tool calls
        are detected but not XML, 'none' if no tool calls are found.
    """
    has_xml = False
    has_json = False

    for msg in messages:
        content = msg.get("content", "")

        if _contains_xml_tool_call(content):
            has_xml = True
        elif _contains_json_tool_call(content):
            has_json = True

    if has_xml:
        return "xml"
    elif has_json:
        return "json"
    else:
        return "none"


class DedupAndValidate:
    """Deduplication and validation for DatasetRecord objects.

    Provides:
    - SHA-256 based exact deduplication on normalized message content
    - Non-call validation to reject tool call artifacts

    This class is designed for the curated dataset pipeline where
    DatasetRecord objects are used instead of raw dicts.
    """

    def __init__(self) -> None:
        """Initialize DedupAndValidate processor."""
        self._seen_hashes: set[str] = set()
        self._discarded_count: int = 0
        self._discard_reasons: dict[str, int] = {}
        self._format_distribution: dict[str, int] = {"json": 0, "xml": 0, "none": 0}

    def reset(self) -> None:
        """Reset internal state for new processing run."""
        self._seen_hashes.clear()
        self._discarded_count = 0
        self._discard_reasons.clear()
        self._format_distribution = {"json": 0, "xml": 0, "none": 0}

    @property
    def discarded_count(self) -> int:
        """Get total number of discarded records."""
        return self._discarded_count

    @property
    def discard_reasons(self) -> dict[str, int]:
        """Get counts of discards by reason."""
        return self._discard_reasons.copy()

    @property
    def format_distribution(self) -> dict[str, int]:
        """Get distribution of tool formats across processed records."""
        return self._format_distribution.copy()

    def _log_discard(self, reason: str, record: DatasetRecord) -> None:
        """Log a record discard with reason.

        Args:
            reason: Reason for discarding the record.
            record: The record that was discarded.
        """
        self._discarded_count += 1
        self._discard_reasons[reason] = self._discard_reasons.get(reason, 0) + 1

        # Log sample of first few discards per reason
        if self._discard_reasons[reason] <= 3:
            msg_preview = (
                record.messages[0].content[:50] + "..."
                if record.messages and len(record.messages[0].content) > 50
                else str(record.messages)
            )
            logger.debug("Discarded record (reason=%s): %s", reason, msg_preview)

    def validate_record(self, record: DatasetRecord) -> bool:
        """Validate a single record for tool call artifacts.

        Args:
            record: DatasetRecord to validate.

        Returns:
            True if record passes validation, False if it contains tool calls.
        """
        for idx, msg in enumerate(record.messages):
            if _contains_tool_call(msg.content):
                self._log_discard("tool_call_content", record)
                return False
        return True

    def deduplicate_record(self, record: DatasetRecord) -> bool:
        """Check if record is duplicate and register if unique.

        Args:
            record: DatasetRecord to check for duplicates.

        Returns:
            True if record is unique (not duplicate), False if it's a duplicate.
        """
        try:
            # Extract message dicts for hashing
            messages_data = [{"role": m.role, "content": m.content} for m in record.messages]
            hash_value = _compute_message_hash(messages_data)

            if hash_value in self._seen_hashes:
                self._log_discard("duplicate", record)
                return False

            self._seen_hashes.add(hash_value)
            return True

        except DeduplicationError:
            # If hashing fails, log error and keep the record
            logger.warning("Failed to compute hash for record, keeping it")
            return True

    def process_record(self, record: DatasetRecord) -> DatasetRecord | None:
        """Process a single record: validate and deduplicate.

        Args:
            record: DatasetRecord to process.

        Returns:
            The original record if it passes validation and is unique,
            None if it was discarded.
        """
        # Track format distribution for all processed records
        messages_data = [{"role": m.role, "content": m.content} for m in record.messages]
        tool_format = detect_tool_format(messages_data)
        self._format_distribution[tool_format] = self._format_distribution.get(tool_format, 0) + 1

        # First validate (check for tool calls)
        if not self.validate_record(record):
            logger.debug("Record rejected: contains tool call artifacts")
            return None

        # Then deduplicate
        if not self.deduplicate_record(record):
            logger.debug("Record rejected: duplicate")
            return None

        return record

    def process_batch(self, records: list[DatasetRecord]) -> list[DatasetRecord]:
        """Process a batch of records: validate and deduplicate.

        Args:
            records: List of DatasetRecord objects to process.

        Returns:
            List of records that passed validation and deduplication.
        """
        kept: list[DatasetRecord] = []

        for record in records:
            processed = self.process_record(record)
            if processed is not None:
                kept.append(processed)

        logger.info(
            "DedupAndValidate: %d/%d records kept (discarded: %d, reasons: %s)",
            len(kept),
            len(records),
            self._discarded_count,
            self._discard_reasons,
        )

        return kept
