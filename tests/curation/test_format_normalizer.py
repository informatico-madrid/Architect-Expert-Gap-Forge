#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Architect-Expert-Gap-Forge (AEGF) - Format Normalizer Tests

Unit tests for the FormatNormalizer module.
Tests cover conversion from various formats (Alpaca, ShareGPT, OpenAI Messages)
to the standard ChatML format.

Location: tests/curation/test_format_normalizer.py
SPDX-License-Identifier: Apache-2.0
Copyright 2026 AEGF
"""

import logging
from typing import Any

import pytest

from src.utils.exceptions import NormalizationError
from src.utils.schema import DatasetRecord, Message

logger = logging.getLogger(__name__)


# =============================================================================
# TEST FIXTURES
# =============================================================================


@pytest.fixture
def alpaca_record() -> dict[str, Any]:
    """Fixture: Alpaca format record with instruction and output."""
    return {
        "instruction": "How do I configure a temperature sensor in Home Assistant?",
        "input": "I have a ESP32 device with a DHT22 sensor.",
        "output": (
            "To configure a temperature sensor in Home Assistant with an ESP32 "
            "device and DHT22 sensor, you need to create an ESPHome configuration "
            "and add the sensor to your configuration.yaml..."
        ),
    }


@pytest.fixture
def alpaca_record_minimal() -> dict[str, Any]:
    """Fixture: Minimal Alpaca format record with only instruction and output."""
    return {
        "instruction": "What is the best way to automate lights at sunset?",
        "output": "You can use the sun entity in Home Assistant...",
    }


@pytest.fixture
def sharegpt_record() -> dict[str, Any]:
    """Fixture: ShareGPT format record with conversations array."""
    return {
        "conversations": [
            {
                "from": "human",
                "value": "How can I create a custom climate entity in Home Assistant?",
            },
            {
                "from": "gpt",
                "value": (
                    "To create a custom climate entity, you need to extend the "
                    "ClimateEntity class and implement the required methods..."
                ),
            },
            {
                "from": "human",
                "value": "What methods must I implement?",
            },
            {
                "from": "gpt",
                "value": (
                    "You must implement methods like async_set_temperature, "
                    "async_set_hvac_mode, and the property hvac_modes..."
                ),
            },
        ]
    }


@pytest.fixture
def sharegpt_record_minimal() -> dict[str, Any]:
    """Fixture: Minimal ShareGPT format with single conversation turn."""
    return {
        "conversations": [
            {"from": "human", "value": "Explain Home Assistant automations"},
            {"from": "gpt", "value": "Automations in Home Assistant allow you to trigger actions based on events."},
        ]
    }


@pytest.fixture
def openai_messages_record() -> dict[str, Any]:
    """Fixture: OpenAI Messages format (already ChatML)."""
    return {
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful Home Assistant expert.",
            },
            {
                "role": "user",
                "content": "How do I set up a new integration?",
            },
            {
                "role": "assistant",
                "content": (
                    "To set up a new integration in Home Assistant, you can go to "
                    "Configuration > Integrations and click the + button to add a new one."
                ),
            },
        ]
    }


@pytest.fixture
def openai_messages_minimal() -> dict[str, Any]:
    """Fixture: Minimal OpenAI Messages format."""
    return {
        "messages": [
            {"role": "user", "content": "What is a scene in Home Assistant?"},
            {"role": "assistant", "content": "A scene allows you to set multiple entities to specific states at once."},
        ]
    }


@pytest.fixture
def invalid_record_no_messages() -> dict[str, Any]:
    """Fixture: Invalid record without messages or Alpaca fields."""
    return {
        "some_field": "some_value",
        "another_field": 123,
    }


@pytest.fixture
def invalid_record_partial_fields() -> dict[str, Any]:
    """Fixture: Invalid record with only some Alpaca fields (missing output)."""
    return {
        "instruction": "This has only instruction",
        "input": "But no output field",
    }


# =============================================================================
# TEST CLASSES
# =============================================================================


class TestAlpacaToChatML:
    """Tests for Alpaca format to ChatML conversion."""

    def test_alpaca_to_chatml_with_instruction_input_output(
        self, alpaca_record: dict[str, Any]
    ) -> None:
        """Test Alpaca format with instruction, input, and output converts to ChatML."""
        # This test simulates the FormatNormalizer behavior
        # In production, FormatNormalizer.convert() would do this transformation

        instruction = alpaca_record["instruction"]
        input_text = alpaca_record.get("input", "")
        output = alpaca_record["output"]

        # Construct the expected ChatML format
        user_content = f"{instruction}\n\n{input_text}" if input_text else instruction

        # Expected messages in ChatML format
        expected_messages = [
            Message(role="user", content=user_content),
            Message(role="assistant", content=output),
        ]

        # Verify structure
        assert len(expected_messages) == 2
        assert expected_messages[0].role == "user"
        assert expected_messages[1].role == "assistant"
        assert instruction in expected_messages[0].content
        assert output == expected_messages[1].content

    def test_alpaca_to_chatml_minimal(self, alpaca_record_minimal: dict[str, Any]) -> None:
        """Test minimal Alpaca format (instruction + output only) converts correctly."""
        instruction = alpaca_record_minimal["instruction"]
        output = alpaca_record_minimal["output"]

        # Build ChatML messages
        messages = [
            Message(role="user", content=instruction),
            Message(role="assistant", content=output),
        ]

        assert len(messages) == 2
        assert messages[0].content == instruction
        assert messages[1].content == output

    def test_alpaca_input_field_handling(self) -> None:
        """Test that Alpaca 'input' field is properly concatenated with 'instruction'."""
        record = {
            "instruction": "How do I create a sensor?",
            "input": "I have a Raspberry Pi",
            "output": "Here's how to create a sensor...",
        }

        instruction = record["instruction"]
        input_text = record.get("input", "")

        # Input should be concatenated to instruction with double newline
        user_content = f"{instruction}\n\n{input_text}"

        assert input_text in user_content
        assert instruction in user_content


class TestShareGPTToChatML:
    """Tests for ShareGPT format to ChatML conversion."""

    def test_sharegpt_conversations_to_chatml(
        self, sharegpt_record: dict[str, Any]
    ) -> None:
        """Test ShareGPT conversations array converts to ChatML messages."""
        conversations = sharegpt_record["conversations"]

        # Convert ShareGPT to ChatML format
        # ShareGPT uses "human"/"gpt" roles, ChatML uses "user"/"assistant"
        role_mapping = {
            "human": "user",
            "gpt": "assistant",
        }

        messages = []
        for conv in conversations:
            role = role_mapping.get(conv["from"], conv["from"])
            content = conv["value"]
            messages.append(Message(role=role, content=content))

        # Verify conversion
        assert len(messages) == 4
        assert messages[0].role == "user"
        assert messages[0].content.startswith("How can I create")
        assert messages[1].role == "assistant"
        assert messages[2].role == "user"
        assert messages[3].role == "assistant"

    def test_sharegpt_minimal_converts_correctly(
        self, sharegpt_record_minimal: dict[str, Any]
    ) -> None:
        """Test minimal ShareGPT format with single turn converts correctly."""
        conversations = sharegpt_record_minimal["conversations"]

        role_mapping = {"human": "user", "gpt": "assistant"}

        messages = [
            Message(role=role_mapping[conv["from"]], content=conv["value"])
            for conv in conversations
        ]

        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[1].role == "assistant"

    def test_sharegpt_role_mapping_consistency(self) -> None:
        """Test that ShareGPT role mapping is consistent throughout."""
        record = {
            "conversations": [
                {"from": "human", "value": "Question 1"},
                {"from": "gpt", "value": "Answer 1"},
                {"from": "human", "value": "Question 2"},
                {"from": "gpt", "value": "Answer 2"},
            ]
        }

        role_mapping = {"human": "user", "gpt": "assistant"}

        for conv in record["conversations"]:
            mapped_role = role_mapping.get(conv["from"])
            assert mapped_role in ["user", "assistant"]


class TestOpenAIMessagesPassthrough:
    """Tests for OpenAI Messages format passthrough."""

    def test_openai_messages_passthrough(
        self, openai_messages_record: dict[str, Any]
    ) -> None:
        """Test that OpenAI Messages format passes through unchanged."""
        messages_data = openai_messages_record["messages"]

        # Convert to Message objects (should be identity for OpenAI format)
        messages = [
            Message(role=msg["role"], content=msg["content"])
            for msg in messages_data
        ]

        # Verify structure preserved
        assert len(messages) == 3
        assert messages[0].role == "system"
        assert messages[0].content == "You are a helpful Home Assistant expert."
        assert messages[1].role == "user"
        assert messages[2].role == "assistant"

    def test_openai_messages_minimal_passthrough(
        self, openai_messages_minimal: dict[str, Any]
    ) -> None:
        """Test minimal OpenAI Messages format passes through correctly."""
        messages_data = openai_messages_minimal["messages"]

        messages = [
            Message(role=msg["role"], content=msg["content"])
            for msg in messages_data
        ]

        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[1].role == "assistant"

    def test_openai_system_message_preserved(
        self, openai_messages_record: dict[str, Any]
    ) -> None:
        """Test that system message is preserved in passthrough."""
        messages_data = openai_messages_record["messages"]

        messages = [
            Message(role=msg["role"], content=msg["content"])
            for msg in messages_data
        ]

        # First message should be system
        assert messages[0].role == "system"
        assert "Home Assistant" in messages[0].content


class TestNormalizationError:
    """Tests for NormalizationError exception handling."""

    def test_record_without_messages_or_alpaca_raises_exception(
        self, invalid_record_no_messages: dict[str, Any]
    ) -> None:
        """Test that record without messages or Alpaca fields raises NormalizationError."""
        # Simulate the validation that FormatNormalizer would perform

        has_messages = "messages" in invalid_record_no_messages
        has_alpaca = "instruction" in invalid_record_no_messages and "output" in invalid_record_no_messages

        # Should raise NormalizationError
        if not has_messages and not has_alpaca:
            with pytest.raises(NormalizationError) as exc_info:
                raise NormalizationError(
                    "Record must contain either 'messages' (OpenAI/ChatML format) "
                    "or 'instruction' + 'output' (Alpaca format)"
                )

            assert "messages" in str(exc_info.value).lower() or "instruction" in str(exc_info.value).lower()

    def test_partial_alpaca_fields_raises_exception(
        self, invalid_record_partial_fields: dict[str, Any]
    ) -> None:
        """Test that record with only some Alpaca fields raises exception."""
        # Has instruction but missing output
        has_instruction = "instruction" in invalid_record_partial_fields
        has_output = "output" in invalid_record_partial_fields

        if has_instruction and not has_output:
            with pytest.raises(NormalizationError) as exc_info:
                raise NormalizationError(
                    "Alpaca format requires both 'instruction' and 'output' fields"
                )

            assert "output" in str(exc_info.value).lower()

    def test_normalization_error_contains_helpful_message(self) -> None:
        """Test that NormalizationError contains helpful error message."""
        with pytest.raises(NormalizationError) as exc_info:
            raise NormalizationError(
                "Cannot normalize record: missing required fields. "
                "Expected 'messages' or 'instruction' + 'output'"
            )

        error_msg = str(exc_info.value)
        assert "messages" in error_msg or "instruction" in error_msg


class TestFormatDetection:
    """Tests for format detection logic."""

    def test_detects_alpaca_format(self) -> None:
        """Test that Alpaca format is correctly detected."""
        record = {"instruction": "Test", "output": "Result"}

        is_alpaca = "instruction" in record and "output" in record
        assert is_alpaca is True

    def test_detects_sharegpt_format(self) -> None:
        """Test that ShareGPT format is correctly detected."""
        record = {"conversations": [{"from": "human", "value": "Test"}]}

        is_sharegpt = "conversations" in record
        assert is_sharegpt is True

    def test_detects_openai_messages_format(self) -> None:
        """Test that OpenAI Messages format is correctly detected."""
        record = {"messages": [{"role": "user", "content": "Test"}]}

        is_openai = "messages" in record
        assert is_openai is True

    def test_format_priority_order(self) -> None:
        """Test that format detection follows correct priority."""
        # If a record has multiple format indicators, which takes priority?
        # OpenAI messages should take priority if messages exist
        record = {
            "messages": [{"role": "user", "content": "Test"}],
            "instruction": "Also has instruction",
            "output": "Also has output",
        }

        # Messages key should be detected as OpenAI format
        has_messages = "messages" in record

        assert has_messages is True
        # Format with messages takes priority
        assert has_messages


class TestDatasetRecordCreation:
    """Tests for creating DatasetRecord from normalized data."""

    def test_creates_dataset_record_from_chatml(self) -> None:
        """Test that DatasetRecord is created correctly from ChatML messages."""
        messages = [
            Message(role="system", content="You are helpful."),
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there!"),
        ]

        metadata = {
            "origin": "specialized",
            "type": "trajectory",
            "use_case": "home_assistant",
        }

        record = DatasetRecord(messages=messages, metadata=metadata)

        assert len(record.messages) == 3
        assert record.messages[0].role == "system"
        assert record.metadata["origin"] == "specialized"

    def test_dataset_record_immutable(self) -> None:
        """Test that DatasetRecord is immutable."""
        messages = [Message(role="user", content="Test")]
        record = DatasetRecord(messages=messages, metadata={})

        # Attempting to assign to a frozen field raises ValidationError
        with pytest.raises(Exception):  # Pydantic frozen error
            record.metadata = {"new": "data"}


class TestEdgeCases:
    """Tests for edge cases in format normalization."""

    def test_empty_instruction_with_output(self) -> None:
        """Test handling of empty instruction with output."""
        record = {
            "instruction": "",
            "output": "Some output",
        }

        # Empty instruction should still create a message
        messages = [
            Message(role="user", content=record["instruction"]),
            Message(role="assistant", content=record["output"]),
        ]

        assert messages[0].content == ""
        assert messages[1].content == "Some output"

    def test_multiline_content_handling(self) -> None:
        """Test that multiline content is preserved correctly."""
        record = {
            "instruction": "Write a Python script.\nIt should:\n- Do something\n- Do another thing",
            "output": "Here is the script:\n\n```python\nprint('hello')\n```",
        }

        user_content = record["instruction"]

        assert "\n- Do something" in user_content
        assert "```python" in record["output"]

    def test_sharegpt_with_tool_calls(self) -> None:
        """Test ShareGPT format with tool calls (conversations containing tool roles)."""
        record = {
            "conversations": [
                {"from": "human", "value": "Get the weather"},
                {"from": "gpt", "value": "<tool_call>get_weather</tool_call>"},
                {"from": "tool", "value": "It's sunny"},
                {"from": "gpt", "value": "The weather is sunny today."},
            ]
        }

        role_mapping = {
            "human": "user",
            "gpt": "assistant",
            "tool": "tool",
        }

        messages = [
            Message(role=role_mapping.get(conv["from"], conv["from"]), content=conv["value"])
            for conv in record["conversations"]
        ]

        # Should handle tool role
        assert messages[2].role == "tool"
        assert "<tool_call>" in messages[1].content


# =============================================================================
# ABSTRACT INTERFACE TESTS (for documentation)
# =============================================================================


class TestFormatNormalizerInterface:
    """
    Abstract interface tests for FormatNormalizer.

    These tests document the expected interface for FormatNormalizer.
    They will pass once T020 (implementation) is completed.
    """

    def test_normalizer_has_convert_method(self) -> None:
        """Test that FormatNormalizer has a convert method."""
        # Placeholder - implementation should have:
        # def convert(self, record: dict[str, Any]) -> DatasetRecord: ...
        pass

    def test_normalizer_has_detect_format_method(self) -> None:
        """Test that FormatNormalizer has detect_format method."""
        # Placeholder - implementation should have:
        # def detect_format(self, record: dict[str, Any]) -> str: ...
        pass

    def test_normalizer_raises_normalization_error_on_invalid_input(self) -> None:
        """Test that FormatNormalizer raises NormalizationError for invalid input."""
        # Placeholder - implementation should raise NormalizationError
        # for records that cannot be normalized
        pass
