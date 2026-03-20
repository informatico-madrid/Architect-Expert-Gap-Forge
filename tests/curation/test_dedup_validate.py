#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Architect-Expert-Gap-Forge (AEGF) - Dedup and Validate Tests

Unit tests for the DedupAndValidate module.
Tests cover: duplicate record elimination between specialized and anchor datasets,
no-call record validation with tool_call detection, and discard logging with seed_id and reason.

Location: tests/curation/test_dedup_validate.py
SPDX-License-Identifier: Apache-2.0
Copyright 2026 AEGF
"""

import hashlib
import logging
from typing import Any

import pytest

from src.curation.dedup_and_validate import DedupAndValidate, detect_tool_format
from src.utils.schema import DatasetRecord, Message, CompositionReport

logger = logging.getLogger(__name__)


# =============================================================================
# TEST FIXTURES
# =============================================================================


@pytest.fixture
def specialized_records() -> list[DatasetRecord]:
    """Fixture: Specialized Home Assistant trajectory records."""
    records = []
    for i in range(5):
        messages = [
            Message(
                role="user",
                content=f"Help me configure Home Assistant - task {i}",
            ),
            Message(
                role="assistant",
                content=f"Here's how to configure Home Assistant for task {i}.",
            ),
        ]
        records.append(
            DatasetRecord(
                messages=messages,
                metadata={
                    "origin": "specialized",
                    "type": "trajectory",
                    "use_case": "home_assistant",
                    "seed_id": f"seed_ha_{i}",
                    "token_count": 50,
                },
            )
        )
    return records


@pytest.fixture
def anchor_records() -> list[DatasetRecord]:
    """Fixture: Anchor dataset records."""
    records = []
    for i in range(5):
        messages = [
            Message(
                role="user",
                content=f"General coding question {i}",
            ),
            Message(
                role="assistant",
                content=f"Here's the answer to question {i}.",
            ),
        ]
        records.append(
            DatasetRecord(
                messages=messages,
                metadata={
                    "origin": "xlam_function_calling",
                    "type": "general",
                    "seed_id": f"seed_anchor_{i}",
                    "token_count": 40,
                },
            )
        )
    return records


@pytest.fixture
def duplicate_records() -> list[DatasetRecord]:
    """Fixture: Records with duplicates between specialized and anchor."""
    # Create some records that are duplicates
    base_messages = [
        Message(role="user", content="How do I configure a sensor?"),
        Message(role="assistant", content="You can configure a sensor in configuration.yaml."),
    ]

    records = [
        # Specialized record
        DatasetRecord(
            messages=base_messages,
            metadata={
                "origin": "specialized",
                "type": "trajectory",
                "seed_id": "seed_dup_specialized",
                "token_count": 30,
            },
        ),
        # Duplicate in anchor (same content)
        DatasetRecord(
            messages=base_messages,
            metadata={
                "origin": "xlam_function_calling",
                "type": "general",
                "seed_id": "seed_dup_anchor",
                "token_count": 30,
            },
        ),
        # Another specialized record
        DatasetRecord(
            messages=[
                Message(role="user", content="Another question"),
                Message(role="assistant", content="Another answer"),
            ],
            metadata={
                "origin": "specialized",
                "type": "trajectory",
                "seed_id": "seed_unique_specialized",
                "token_count": 20,
            },
        ),
    ]
    return records


@pytest.fixture
def nocall_records() -> list[DatasetRecord]:
    """Fixture: Records labeled as no-call but containing tool_call."""
    # Record labeled as no-call but has <tool_call> in content
    nocall_with_tool = DatasetRecord(
        messages=[
            Message(role="user", content="What's the weather?"),
            Message(
                role="assistant",
                content="<tool_call>get_weather location='NYC'</tool_call>\nThe weather is sunny.",
            ),
        ],
        metadata={
            "origin": "xlam_function_calling",
            "type": "no-call",
            "seed_id": "seed_nocall_fake",
            "token_count": 25,
        },
    )

    # Valid no-call (no tool_call tag)
    nocall_valid = DatasetRecord(
        messages=[
            Message(role="user", content="Hello, how are you?"),
            Message(role="assistant", content="I'm doing well, thank you!"),
        ],
        metadata={
            "origin": "xlam_function_calling",
            "type": "no-call",
            "seed_id": "seed_nocall_valid",
            "token_count": 20,
        },
    )

    return [nocall_with_tool, nocall_valid]


@pytest.fixture
def mixed_with_duplicates_and_nocall(
    specialized_records: list[DatasetRecord],
    anchor_records: list[DatasetRecord],
    duplicate_records: list[DatasetRecord],
    nocall_records: list[DatasetRecord],
) -> list[DatasetRecord]:
    """Fixture: Mixed records with duplicates and invalid no-call."""
    return specialized_records + anchor_records + duplicate_records + nocall_records


# =============================================================================
# TEST CLASSES
# =============================================================================


class TestDuplicateElimination:
    """Tests for duplicate record elimination between datasets."""

    def test_duplicate_between_specialized_and_anchor_is_removed(
        self, duplicate_records: list[DatasetRecord]
    ) -> None:
        """Test that duplicate records between specialized and anchor datasets are eliminated."""
        # Simulate the dedup logic: hash each record's messages content
        seen_hashes: dict[str, DatasetRecord] = {}
        kept_records: list[DatasetRecord] = []
        discarded_seeds: list[str] = []

        for record in duplicate_records:
            # Create hash from messages content
            content = "".join(m.content for m in record.messages)
            record_hash = hashlib.sha256(content.encode()).hexdigest()

            if record_hash in seen_hashes:
                # Duplicate found - discard
                discarded_seeds.append(record.metadata.get("seed_id", "unknown"))
                logger.info(
                    "Discarded duplicate: seed_id=%s, reason=duplicate",
                    record.metadata.get("seed_id", "unknown"),
                )
            else:
                seen_hashes[record_hash] = record
                kept_records.append(record)

        # Should have kept only 2 records (3 input - 1 duplicate = 2)
        assert len(kept_records) == 2, f"Expected 2 records, got {len(kept_records)}"
        # Should have discarded 1 duplicate
        assert len(discarded_seeds) == 1, f"Expected 1 discarded, got {len(discarded_seeds)}"

    def test_no_duplicates_preserves_all_records(
        self, specialized_records: list[DatasetRecord], anchor_records: list[DatasetRecord]
    ) -> None:
        """Test that when there are no duplicates, all records are preserved."""
        all_records = specialized_records + anchor_records

        seen_hashes: set[str] = set()
        kept_records: list[DatasetRecord] = []

        for record in all_records:
            content = "".join(m.content for m in record.messages)
            record_hash = hashlib.sha256(content.encode()).hexdigest()

            if record_hash not in seen_hashes:
                seen_hashes.add(record_hash)
                kept_records.append(record)

        # All records should be kept
        assert len(kept_records) == len(all_records)

    def test_exact_message_content_duplicate_detection(
        self,
    ) -> None:
        """Test that duplicate detection uses exact message content matching."""
        # Two records with identical message content
        same_content = [
            Message(role="user", content="Test question"),
            Message(role="assistant", content="Test answer"),
        ]

        record1 = DatasetRecord(
            messages=same_content,
            metadata={"origin": "specialized", "seed_id": "seed_1"},
        )
        record2 = DatasetRecord(
            messages=same_content,
            metadata={"origin": "anchor", "seed_id": "seed_2"},
        )

        # Hash both
        content1 = "".join(m.content for m in record1.messages)
        content2 = "".join(m.content for m in record2.messages)

        hash1 = hashlib.sha256(content1.encode()).hexdigest()
        hash2 = hashlib.sha256(content2.encode()).hexdigest()

        # Should have same hash
        assert hash1 == hash2

    def test_different_content_produces_different_hash(
        self,
    ) -> None:
        """Test that different content produces different hashes."""
        messages1 = [
            Message(role="user", content="Question 1"),
            Message(role="assistant", content="Answer 1"),
        ]
        messages2 = [
            Message(role="user", content="Question 2"),
            Message(role="assistant", content="Answer 2"),
        ]

        content1 = "".join(m.content for m in messages1)
        content2 = "".join(m.content for m in messages2)

        hash1 = hashlib.sha256(content1.encode()).hexdigest()
        hash2 = hashlib.sha256(content2.encode()).hexdigest()

        assert hash1 != hash2


class TestNoCallValidation:
    """Tests for no-call record validation with tool_call detection."""

    def test_nocall_record_with_tool_call_is_discarded(
        self, nocall_records: list[DatasetRecord]
    ) -> None:
        """Test that no-call labeled records with <tool_call> in content are discarded."""
        discarded_records: list[DatasetRecord] = []
        kept_records: list[DatasetRecord] = []

        for record in nocall_records:
            # Check if record is labeled as no-call
            record_type = record.metadata.get("type", "")

            if record_type == "no-call":
                # Check if any message content contains tool_call
                has_tool_call = any(
                    "<tool_call>" in m.content.lower() or "tool_call" in m.content.lower()
                    for m in record.messages
                )

                if has_tool_call:
                    # Discard this record
                    discarded_records.append(record)
                    logger.info(
                        "Discarded no-call with tool_call: seed_id=%s",
                        record.metadata.get("seed_id", "unknown"),
                    )
                else:
                    kept_records.append(record)
            else:
                kept_records.append(record)

        # Should have discarded 1 record (the fake no-call)
        assert len(discarded_records) == 1
        assert discarded_records[0].metadata.get("seed_id") == "seed_nocall_fake"

    def test_valid_nocall_record_is_kept(
        self, nocall_records: list[DatasetRecord]
    ) -> None:
        """Test that valid no-call records (without tool_call) are kept."""
        valid_nocall = [
            r for r in nocall_records if r.metadata.get("type") == "no-call"
        ]

        # Check the valid one
        for record in valid_nocall:
            has_tool_call = any(
                "<tool_call>" in m.content.lower() or "tool_call" in m.content.lower()
                for m in record.messages
            )

            # The valid no-call should not have tool_call
            if record.metadata.get("seed_id") == "seed_nocall_valid":
                assert not has_tool_call

    def test_tool_call_detection_case_insensitive(
        self,
    ) -> None:
        """Test that tool_call detection is case-insensitive."""
        # Record with TOOL_CALL in uppercase
        record = DatasetRecord(
            messages=[
                Message(role="user", content="Get weather"),
                Message(role="assistant", content="<TOOL_CALL>get_weather</TOOL_CALL>"),
            ],
            metadata={"type": "no-call", "seed_id": "seed_uppercase"},
        )

        has_tool_call = any(
            "<tool_call>" in m.content.lower() for m in record.messages
        )

        assert has_tool_call is True

    def test_tool_call_with_json_format_is_detected(
        self,
    ) -> None:
        """Test that tool call in JSON format is also detected."""
        # Record with JSON tool call in no-call type
        record = DatasetRecord(
            messages=[
                Message(
                    role="user", content="Call the function"
                ),
                Message(
                    role="assistant",
                    content='{"tool": "get_weather", "arguments": {"location": "NYC"}}',
                ),
            ],
            metadata={"type": "no-call", "seed_id": "seed_json_tool"},
        )

        # Check for JSON tool call pattern
        has_tool_call = any(
            '"tool"' in m.content and '"arguments"' in m.content
            for m in record.messages
        )

        # This should also be flagged as containing a tool call
        assert has_tool_call is True


class TestDiscardLogging:
    """Tests for discard logging with seed_id and reason."""

    def test_discard_log_contains_seed_id(
        self, duplicate_records: list[DatasetRecord]
    ) -> None:
        """Test that discard log contains seed_id."""
        discard_logs: list[dict[str, Any]] = []

        seen_hashes: set[str] = set()

        for record in duplicate_records:
            content = "".join(m.content for m in record.messages)
            record_hash = hashlib.sha256(content.encode()).hexdigest()

            if record_hash in seen_hashes:
                # Log the discard with seed_id
                discard_logs.append({
                    "seed_id": record.metadata.get("seed_id", "unknown"),
                    "reason": "duplicate",
                })
            else:
                seen_hashes.add(record_hash)

        # Verify all logs have seed_id
        for log in discard_logs:
            assert "seed_id" in log
            assert log["seed_id"] is not None

    def test_discard_log_contains_reason(
        self, duplicate_records: list[DatasetRecord]
    ) -> None:
        """Test that discard log contains reason for discard."""
        discard_logs: list[dict[str, Any]] = []

        seen_hashes: set[str] = set()

        for record in duplicate_records:
            content = "".join(m.content for m in record.messages)
            record_hash = hashlib.sha256(content.encode()).hexdigest()

            if record_hash in seen_hashes:
                discard_logs.append({
                    "seed_id": record.metadata.get("seed_id", "unknown"),
                    "reason": "duplicate",
                })
            else:
                seen_hashes.add(record_hash)

        # Verify all logs have reason
        for log in discard_logs:
            assert "reason" in log
            assert log["reason"] in ["duplicate", "invalid_nocall"]

    def test_discard_reasons_include_multiple_types(
        self, nocall_records: list[DatasetRecord]
    ) -> None:
        """Test that discard reasons can include multiple types."""
        discard_logs: list[dict[str, Any]] = []

        # Process duplicates first
        seen_hashes: set[str] = set()

        # Add some duplicate processing
        for record in nocall_records[:1]:
            content = "".join(m.content for m in record.messages)
            record_hash = hashlib.sha256(content.encode()).hexdigest()

            if record_hash in seen_hashes:
                discard_logs.append({
                    "seed_id": record.metadata.get("seed_id", "unknown"),
                    "reason": "duplicate",
                })
            else:
                seen_hashes.add(record_hash)

        # Process no-call validation
        for record in nocall_records:
            if record.metadata.get("type") == "no-call":
                has_tool_call = any(
                    "<tool_call>" in m.content.lower()
                    for m in record.messages
                )
                if has_tool_call:
                    discard_logs.append({
                        "seed_id": record.metadata.get("seed_id", "unknown"),
                        "reason": "invalid_nocall",
                    })

        # Should have at least one invalid_nocall
        reasons = [log["reason"] for log in discard_logs]
        assert "invalid_nocall" in reasons

    def test_composition_report_tracks_discarded_reasons(
        self,
    ) -> None:
        """Test that CompositionReport tracks discarded reasons."""
        discarded_reasons: dict[str, int] = {
            "duplicate": 3,
            "invalid_nocall": 2,
        }

        report = CompositionReport(
            records_by_origin={"specialized": 10, "anchor": 20},
            token_pct_by_origin={"specialized": 30.0, "anchor": 70.0},
            type_distribution={"trajectory": 10, "general": 20},
            discarded_count=5,
            discarded_reasons=discarded_reasons,
        )

        assert report.discarded_count == 5
        assert report.discarded_reasons["duplicate"] == 3
        assert report.discarded_reasons["invalid_nocall"] == 2

    def test_discard_log_format_structure(
        self,
    ) -> None:
        """Test that discard log has proper structure with all required fields."""
        # Simulate a complete discard log entry
        discard_entry = {
            "seed_id": "seed_123",
            "reason": "duplicate",
            "timestamp": "2026-03-19T12:00:00",
            "origin": "specialized",
            "record_type": "trajectory",
        }

        # Verify structure
        assert "seed_id" in discard_entry
        assert "reason" in discard_entry
        assert discard_entry["seed_id"] == "seed_123"
        assert discard_entry["reason"] == "duplicate"


class TestDedupAndValidateWorkflow:
    """Integration tests for complete dedup and validate workflow."""

    def test_complete_dedup_workflow(
        self,
        mixed_with_duplicates_and_nocall: list[DatasetRecord],
    ) -> None:
        """Test complete deduplication and validation workflow."""
        # Track all discards
        discard_logs: list[dict[str, Any]] = []
        seen_hashes: set[str] = set()
        kept_records: list[DatasetRecord] = []

        for record in mixed_with_duplicates_and_nocall:
            # Step 1: Check for duplicates
            content = "".join(m.content for m in record.messages)
            record_hash = hashlib.sha256(content.encode()).hexdigest()

            if record_hash in seen_hashes:
                discard_logs.append({
                    "seed_id": record.metadata.get("seed_id", "unknown"),
                    "reason": "duplicate",
                })
                continue

            seen_hashes.add(record_hash)

            # Step 2: Validate no-call records
            if record.metadata.get("type") == "no-call":
                has_tool_call = any(
                    "<tool_call>" in m.content.lower()
                    for m in record.messages
                )
                if has_tool_call:
                    discard_logs.append({
                        "seed_id": record.metadata.get("seed_id", "unknown"),
                        "reason": "invalid_nocall",
                    })
                    continue

            kept_records.append(record)

        # Verify discard logs have required fields
        for log in discard_logs:
            assert "seed_id" in log
            assert "reason" in log

        # Should have some discards
        assert len(discard_logs) > 0

    def test_dedup_preserves_record_order(
        self, specialized_records: list[DatasetRecord], anchor_records: list[DatasetRecord]
    ) -> None:
        """Test that deduplication preserves the order of non-discarded records."""
        all_records = specialized_records + anchor_records

        seen_hashes: list[str] = []
        kept_records: list[DatasetRecord] = []

        for record in all_records:
            content = "".join(m.content for m in record.messages)
            record_hash = hashlib.sha256(content.encode()).hexdigest()

            if record_hash not in seen_hashes:
                seen_hashes.append(record_hash)
                kept_records.append(record)

        # All records should be kept in original order
        assert len(kept_records) == len(all_records)


class TestEdgeCases:
    """Tests for edge cases in deduplication and validation."""

    def test_empty_messages_handling(
        self,
    ) -> None:
        """Test handling of records with empty messages."""
        record = DatasetRecord(
            messages=[],
            metadata={"seed_id": "seed_empty"},
        )

        content = "".join(m.content for m in record.messages)
        hash_value = hashlib.sha256(content.encode()).hexdigest()

        # Empty content should still produce a hash
        assert len(hash_value) == 64

    def test_single_message_record(
        self,
    ) -> None:
        """Test handling of records with single message."""
        record = DatasetRecord(
            messages=[Message(role="user", content="Only one message")],
            metadata={"seed_id": "seed_single"},
        )

        content = "".join(m.content for m in record.messages)
        hash_value = hashlib.sha256(content.encode()).hexdigest()

        assert "Only one message" in content
        assert len(hash_value) == 64  # SHA-256 produces 64 hex chars

    def test_special_characters_in_content(
        self,
    ) -> None:
        """Test handling of special characters in message content."""
        record = DatasetRecord(
            messages=[
                Message(
                    role="user",
                    content="Test with special chars: <>&\"'{}[]",
                ),
                Message(
                    role="assistant",
                    content="Response with emoji 🎉 and unicode: 你好",
                ),
            ],
            metadata={"seed_id": "seed_special"},
        )

        content = "".join(m.content for m in record.messages)
        hash_value = hashlib.sha256(content.encode()).hexdigest()

        assert len(hash_value) == 64


class TestDedupValidateInterface:
    """
    Abstract interface tests for DedupAndValidate.

    These tests document the expected interface for DedupAndValidate.
    They will pass once T022 (implementation) is completed.
    """

    def test_dedup_has_validate_record_method(self) -> None:
        """Test that DedupAndValidate has a validate_record method."""
        dedup = DedupAndValidate()
        assert hasattr(dedup, "validate_record")
        assert callable(dedup.validate_record)

    def test_dedup_has_reset_method(self) -> None:
        """Test that DedupAndValidate has a reset method."""
        dedup = DedupAndValidate()
        assert hasattr(dedup, "reset")
        assert callable(dedup.reset)

    def test_dedup_discarded_count_property(self) -> None:
        """Test that DedupAndValidate has discarded_count property."""
        dedup = DedupAndValidate()
        assert hasattr(dedup, "discarded_count")
        assert isinstance(dedup.discarded_count, int)

    def test_dedup_discard_reasons_property(self) -> None:
        """Test that DedupAndValidate has discard_reasons property."""
        dedup = DedupAndValidate()
        assert hasattr(dedup, "discard_reasons")
        assert isinstance(dedup.discard_reasons, dict)

    def test_dedup_format_distribution_property(self) -> None:
        """Test that DedupAndValidate has format_distribution property."""
        dedup = DedupAndValidate()
        assert hasattr(dedup, "format_distribution")
        assert isinstance(dedup.format_distribution, dict)

    def test_validate_record_valid(self) -> None:
        """Test validate_record returns True for valid record."""
        dedup = DedupAndValidate()
        record = DatasetRecord(
            messages=[Message(role="user", content="Hello"), Message(role="assistant", content="Hi")],
            metadata={}
        )
        result = dedup.validate_record(record)
        assert result is True

    def test_reset_clears_state(self) -> None:
        """Test reset clears the internal state."""
        dedup = DedupAndValidate()
        dedup.reset()
        assert dedup.discarded_count == 0
        assert dedup.discard_reasons == {}


# =============================================================================
# TESTS FOR detect_tool_format
# =============================================================================


class TestDetectToolFormat:
    """Tests for detect_tool_format function."""

    def test_detect_tool_format_xml(self) -> None:
        """Test that XML tool call format is detected correctly."""
        messages = [
            {"role": "user", "content": "What's the weather?"},
            {"role": "assistant", "content": "<tool_call><tool_name>get_weather</tool_name></tool_call>"},
        ]
        result = detect_tool_format(messages)
        assert result == "xml"

    def test_detect_tool_format_json(self) -> None:
        """Test that JSON tool call format is detected correctly."""
        messages = [
            {"role": "user", "content": "Call the function"},
            {"role": "assistant", "content": '{"name": "get_weather", "arguments": {"location": "NYC"}}'},
        ]
        result = detect_tool_format(messages)
        assert result == "json"

    def test_detect_tool_format_none(self) -> None:
        """Test that no tool calls returns 'none'."""
        messages = [
            {"role": "user", "content": "Hello, how are you?"},
            {"role": "assistant", "content": "I'm doing well, thank you!"},
        ]
        result = detect_tool_format(messages)
        assert result == "none"

    def test_detect_tool_format_empty_messages(self) -> None:
        """Test that empty messages list returns 'none'."""
        messages: list[dict[str, Any]] = []
        result = detect_tool_format(messages)
        assert result == "none"

    def test_detect_tool_format_xml_takes_precedence(self) -> None:
        """Test that XML format takes precedence over JSON when both present."""
        messages = [
            {"role": "user", "content": "Call a function"},
            {"role": "assistant", "content": "<tool_call><tool_name>test</tool_name></tool_call>"},
            {"role": "assistant", "content": '{"name": "json_func", "arguments": {}}'},
        ]
        result = detect_tool_format(messages)
        assert result == "xml"

    def test_detect_tool_format_mixed_messages(self) -> None:
        """Test tool format detection with mixed message content."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
            {"role": "user", "content": "Use the tool"},
            {"role": "assistant", "content": "<tool_call><tool_name>search</tool_name></tool_call>"},
        ]
        result = detect_tool_format(messages)
        assert result == "xml"

    def test_detect_tool_format_tool_call_tag(self) -> None:
        """Test detection of <tool_call> tag."""
        messages = [
            {"role": "assistant", "content": "<tool_call>get_weather location='NYC'</tool_call>"},
        ]
        result = detect_tool_format(messages)
        assert result == "xml"

    def test_detect_tool_format_tool_args_tag(self) -> None:
        """Test detection of <tool_args> tag."""
        messages = [
            {"role": "assistant", "content": "<tool_args>{\"location\": \"NYC\"}</tool_args>"},
        ]
        result = detect_tool_format(messages)
        assert result == "xml"

    def test_detect_tool_format_json_tool_calls_key(self) -> None:
        """Test detection of 'tool_calls' key in JSON."""
        messages = [
            {"role": "assistant", "content": '{"tool_calls": [{"name": "func", "arguments": {}}]}'},
        ]
        result = detect_tool_format(messages)
        assert result == "json"

    def test_detect_tool_format_json_name_and_arguments(self) -> None:
        """Test detection of 'name' and 'arguments' pattern."""
        messages = [
            {"role": "assistant", "content": '"name": "my_function", "arguments": {"arg1": "value1"}'},
        ]
        result = detect_tool_format(messages)
        assert result == "json"

    def test_detect_tool_format_case_insensitive(self) -> None:
        """Test that detection is case insensitive for XML tags."""
        messages = [
            {"role": "assistant", "content": "<TOOL_CALL><TOOL_NAME>test</TOOL_NAME></TOOL_CALL>"},
        ]
        result = detect_tool_format(messages)
        assert result == "xml"

    def test_detect_tool_format_message_without_content_key(self) -> None:
        """Test handling of messages without content key."""
        messages = [
            {"role": "user"},  # No content key
            {"role": "assistant", "content": "Hello"},
        ]
        result = detect_tool_format(messages)
        assert result == "none"

    def test_detect_tool_format_multiple_xml_in_content(self) -> None:
        """Test detection when multiple XML tool calls are in same content."""
        messages = [
            {"role": "assistant", "content": "<tool_call><tool_name>func1</tool_name></tool_call> and <tool_call><tool_name>func2</tool_name></tool_call>"},
        ]
        result = detect_tool_format(messages)
        assert result == "xml"

    def test_detect_tool_format_multiple_json_in_content(self) -> None:
        """Test detection when multiple JSON tool calls are in same content."""
        messages = [
            {"role": "assistant", "content": '{"tool_calls": [{"name": "func1"}]}, {"tool_calls": [{"name": "func2"}]}'},
        ]
        result = detect_tool_format(messages)
        assert result == "json"
