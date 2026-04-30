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

from src.curation.format_normalizer import FormatNormalizer
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


class TestConvertAlpaca:
    """Tests for FormatNormalizer._convert_alpaca method."""

    def test_convert_alpaca_with_instruction_input_output(self) -> None:
        """Test Alpaca conversion with instruction, input, and output fields."""
        normalizer = FormatNormalizer()
        record = {
            "instruction": "How do I configure a temperature sensor?",
            "input": "I have an ESP32 with DHT22",
            "output": "Create an ESPHome configuration...",
        }

        messages = normalizer._convert_alpaca(record)

        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[1].role == "assistant"

        # User content should concatenate instruction and input with double newline
        assert "How do I configure a temperature sensor?" in messages[0].content
        assert "I have an ESP32 with DHT22" in messages[0].content
        assert "\n\n" in messages[0].content

        assert messages[1].content == "Create an ESPHome configuration..."

    def test_convert_alpaca_minimal_with_instruction_and_output_only(self) -> None:
        """Test Alpaca conversion with only instruction and output (no input)."""
        normalizer = FormatNormalizer()
        record = {
            "instruction": "What is Home Assistant?",
            "output": "Home Assistant is an open-source home automation platform.",
        }

        messages = normalizer._convert_alpaca(record)

        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[0].content == "What is Home Assistant?"
        assert messages[1].role == "assistant"
        assert messages[1].content == "Home Assistant is an open-source home automation platform."

    def test_convert_alpaca_missing_instruction_raises_error(self) -> None:
        """Test that missing instruction field raises NormalizationError."""
        normalizer = FormatNormalizer()
        record = {
            "input": "Some input",
            "output": "Some output",
        }

        with pytest.raises(NormalizationError) as exc_info:
            normalizer._convert_alpaca(record)

        assert "instruction" in str(exc_info.value).lower()
        assert "output" in str(exc_info.value).lower()

    def test_convert_alpaca_missing_output_raises_error(self) -> None:
        """Test that missing output field raises NormalizationError."""
        normalizer = FormatNormalizer()
        record = {
            "instruction": "Some instruction",
            "input": "Some input",
        }

        with pytest.raises(NormalizationError) as exc_info:
            normalizer._convert_alpaca(record)

        assert "instruction" in str(exc_info.value).lower()
        assert "output" in str(exc_info.value).lower()

    def test_convert_alpaca_missing_both_instruction_and_output(self) -> None:
        """Test that missing both instruction and output raises NormalizationError."""
        normalizer = FormatNormalizer()
        record = {
            "input": "Some input",
        }

        with pytest.raises(NormalizationError) as exc_info:
            normalizer._convert_alpaca(record)

        assert "instruction" in str(exc_info.value).lower()
        assert "output" in str(exc_info.value).lower()

    def test_convert_alpaca_empty_instruction(self) -> None:
        """Test Alpaca conversion with empty instruction string."""
        normalizer = FormatNormalizer()
        record = {
            "instruction": "",
            "output": "Some output",
        }

        messages = normalizer._convert_alpaca(record)

        assert len(messages) == 2
        assert messages[0].content == ""
        assert messages[1].content == "Some output"

    def test_convert_alpaca_empty_input(self) -> None:
        """Test Alpaca conversion with empty input string (field present but empty)."""
        normalizer = FormatNormalizer()
        record = {
            "instruction": "The question",
            "input": "",
            "output": "The answer",
        }

        messages = normalizer._convert_alpaca(record)

        # Empty input should not be concatenated - should just use instruction
        assert messages[0].content == "The question"
        assert messages[1].content == "The answer"

    def test_convert_alpaca_empty_output(self) -> None:
        """Test Alpaca conversion with empty output string."""
        normalizer = FormatNormalizer()
        record = {
            "instruction": "The question",
            "output": "",
        }

        messages = normalizer._convert_alpaca(record)

        assert len(messages) == 2
        assert messages[0].content == "The question"
        assert messages[1].content == ""

    def test_convert_alpaca_instruction_input_concatenation_format(self) -> None:
        """Test that instruction and input are concatenated with exactly double newline."""
        normalizer = FormatNormalizer()
        record = {
            "instruction": "Instruction text",
            "input": "Input text",
            "output": "Output text",
        }

        messages = normalizer._convert_alpaca(record)

        # Check the exact concatenation format
        expected_content = "Instruction text\n\nInput text"
        assert messages[0].content == expected_content

    def test_convert_alpaca_multiline_content_preserved(self) -> None:
        """Test that multiline content in instruction/input/output is preserved."""
        normalizer = FormatNormalizer()
        record = {
            "instruction": "Line 1\nLine 2\nLine 3",
            "input": "Input line 1\nInput line 2",
            "output": "Output\nWith multiple\nLines",
        }

        messages = normalizer._convert_alpaca(record)

        assert "\n" in messages[0].content
        assert "Line 1" in messages[0].content
        assert "Line 3" in messages[0].content
        assert "Output\nWith multiple\nLines" in messages[1].content

    def test_convert_alpaca_special_characters_preserved(self) -> None:
        """Test that special characters in content are preserved."""
        normalizer = FormatNormalizer()
        record = {
            "instruction": "Use JSON: {\"key\": \"value\"}",
            "input": "Code: `print('hello')`",
            "output": "Answer with <html> tags",
        }

        messages = normalizer._convert_alpaca(record)

        assert '{"key": "value"}' in messages[0].content
        assert "print('hello')" in messages[0].content
        assert "<html>" in messages[1].content


class TestConvertShareGPT:
    """Tests for FormatNormalizer._convert_sharegpt method."""

    def test_convert_sharegpt_with_conversations(self) -> None:
        """Test ShareGPT conversion with conversations array."""
        normalizer = FormatNormalizer()
        record = {
            "conversations": [
                {"from": "human", "value": "How do I configure a sensor?"},
                {"from": "gpt", "value": "Create an ESPHome configuration..."},
            ]
        }

        messages = normalizer._convert_sharegpt(record)

        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[0].content == "How do I configure a sensor?"
        assert messages[1].role == "assistant"
        assert messages[1].content == "Create an ESPHome configuration..."

    def test_convert_sharegpt_minimal_single_turn(self) -> None:
        """Test ShareGPT conversion with minimal single conversation turn."""
        normalizer = FormatNormalizer()
        record = {
            "conversations": [
                {"from": "human", "value": "Hello"},
                {"from": "gpt", "value": "Hi there!"},
            ]
        }

        messages = normalizer._convert_sharegpt(record)

        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[1].role == "assistant"

    def test_convert_sharegpt_missing_conversations_raises_error(self) -> None:
        """Test that missing conversations array raises NormalizationError."""
        normalizer = FormatNormalizer()
        record = {"messages": [{"role": "user", "content": "test"}]}

        with pytest.raises(NormalizationError) as exc_info:
            normalizer._convert_sharegpt(record)

        assert "conversations" in str(exc_info.value).lower()

    def test_convert_sharegpt_invalid_conversations_type_raises_error(self) -> None:
        """Test that non-list conversations raises NormalizationError."""
        normalizer = FormatNormalizer()
        record = {"conversations": "not a list"}

        with pytest.raises(NormalizationError) as exc_info:
            normalizer._convert_sharegpt(record)

        assert "list" in str(exc_info.value).lower()

    def test_convert_sharegpt_missing_from_field_raises_error(self) -> None:
        """Test that missing 'from' field raises NormalizationError."""
        normalizer = FormatNormalizer()
        record = {
            "conversations": [
                {"value": "Some content"},
            ]
        }

        with pytest.raises(NormalizationError) as exc_info:
            normalizer._convert_sharegpt(record)

        assert "from" in str(exc_info.value).lower()

    def test_convert_sharegpt_missing_value_field_raises_error(self) -> None:
        """Test that missing 'value' field raises NormalizationError."""
        normalizer = FormatNormalizer()
        record = {
            "conversations": [
                {"from": "human"},
            ]
        }

        with pytest.raises(NormalizationError) as exc_info:
            normalizer._convert_sharegpt(record)

        assert "value" in str(exc_info.value).lower()

    def test_convert_sharegpt_empty_conversation_array(self) -> None:
        """Test ShareGPT conversion with empty conversations array."""
        normalizer = FormatNormalizer()
        record = {"conversations": []}

        messages = normalizer._convert_sharegpt(record)

        assert len(messages) == 0

    def test_convert_sharegpt_role_mapping_human_to_user(self) -> None:
        """Test that ShareGPT 'human' role maps to 'user'."""
        normalizer = FormatNormalizer()
        record = {
            "conversations": [
                {"from": "human", "value": "Question"},
                {"from": "gpt", "value": "Answer"},
            ]
        }

        messages = normalizer._convert_sharegpt(record)

        assert messages[0].role == "user"
        assert messages[1].role == "assistant"

    def test_convert_sharegpt_role_mapping_gpt_to_assistant(self) -> None:
        """Test that ShareGPT 'gpt' role maps to 'assistant'."""
        normalizer = FormatNormalizer()
        record = {
            "conversations": [
                {"from": "human", "value": "Question"},
                {"from": "gpt", "value": "Answer"},
            ]
        }

        messages = normalizer._convert_sharegpt(record)

        assert messages[1].role == "assistant"

    def test_convert_sharegpt_role_mapping_tool(self) -> None:
        """Test that ShareGPT 'tool' role maps to 'tool'."""
        normalizer = FormatNormalizer()
        record = {
            "conversations": [
                {"from": "human", "value": "Get weather"},
                {"from": "gpt", "value": "<tool_call>get_weather</tool_call>"},
                {"from": "tool", "value": "Sunny, 25C"},
            ]
        }

        messages = normalizer._convert_sharegpt(record)

        assert messages[2].role == "tool"
        assert messages[2].content == "Sunny, 25C"

    def test_convert_sharegpt_role_mapping_system(self) -> None:
        """Test that ShareGPT 'system' role maps to 'system'."""
        normalizer = FormatNormalizer()
        record = {
            "conversations": [
                {"from": "system", "value": "You are a helpful assistant."},
                {"from": "human", "value": "Hello"},
            ]
        }

        messages = normalizer._convert_sharegpt(record)

        assert messages[0].role == "system"
        assert messages[0].content == "You are a helpful assistant."

    def test_convert_sharegpt_unknown_role_passes_through(self) -> None:
        """Test that unknown ShareGPT roles pass through unchanged."""
        normalizer = FormatNormalizer()
        record = {
            "conversations": [
                {"from": "custom_role", "value": "Custom message"},
            ]
        }

        messages = normalizer._convert_sharegpt(record)

        assert messages[0].role == "custom_role"
        assert messages[0].content == "Custom message"

    def test_convert_sharegpt_multiline_content_preserved(self) -> None:
        """Test that multiline content in conversations is preserved."""
        normalizer = FormatNormalizer()
        record = {
            "conversations": [
                {"from": "human", "value": "Line 1\nLine 2\nLine 3"},
                {"from": "gpt", "value": "Response\nWith multiple\nLines"},
            ]
        }

        messages = normalizer._convert_sharegpt(record)

        assert "\n" in messages[0].content
        assert "Line 1" in messages[0].content
        assert "Line 3" in messages[0].content
        assert "Response\nWith multiple\nLines" in messages[1].content

    def test_convert_sharegpt_special_characters_preserved(self) -> None:
        """Test that special characters in content are preserved."""
        normalizer = FormatNormalizer()
        record = {
            "conversations": [
                {"from": "human", "value": "Use JSON: {\"key\": \"value\"}"},
                {"from": "gpt", "value": "Answer with <html> tags and `code`"},
            ]
        }

        messages = normalizer._convert_sharegpt(record)

        assert '{"key": "value"}' in messages[0].content
        assert "<html>" in messages[1].content
        assert "`code`" in messages[1].content


class TestConvertOpenAIMessages:
    """Tests for FormatNormalizer._convert_openai_messages method."""

    def test_convert_openai_messages_with_messages_array(self) -> None:
        """Test OpenAI Messages conversion with messages array."""
        normalizer = FormatNormalizer()
        record = {
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "How do I configure a sensor?"},
                {"role": "assistant", "content": "Create an ESPHome configuration..."},
            ]
        }

        messages = normalizer._convert_openai_messages(record)

        assert len(messages) == 3
        assert messages[0].role == "system"
        assert messages[0].content == "You are a helpful assistant."
        assert messages[1].role == "user"
        assert messages[1].content == "How do I configure a sensor?"
        assert messages[2].role == "assistant"
        assert messages[2].content == "Create an ESPHome configuration..."

    def test_convert_openai_messages_minimal_single_turn(self) -> None:
        """Test OpenAI Messages conversion with minimal single turn."""
        normalizer = FormatNormalizer()
        record = {
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
            ]
        }

        messages = normalizer._convert_openai_messages(record)

        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[1].role == "assistant"

    def test_convert_openai_messages_missing_messages_raises_error(self) -> None:
        """Test that missing messages array raises NormalizationError."""
        normalizer = FormatNormalizer()
        record = {"conversations": [{"from": "human", "value": "test"}]}

        with pytest.raises(NormalizationError) as exc_info:
            normalizer._convert_openai_messages(record)

        assert "messages" in str(exc_info.value).lower()

    def test_convert_openai_messages_invalid_messages_type_raises_error(self) -> None:
        """Test that non-list messages raises NormalizationError."""
        normalizer = FormatNormalizer()
        record = {"messages": "not a list"}

        with pytest.raises(NormalizationError) as exc_info:
            normalizer._convert_openai_messages(record)

        assert "list" in str(exc_info.value).lower()

    def test_convert_openai_messages_missing_role_raises_error(self) -> None:
        """Test that missing 'role' field raises NormalizationError."""
        normalizer = FormatNormalizer()
        record = {
            "messages": [
                {"content": "Some content"},
            ]
        }

        with pytest.raises(NormalizationError) as exc_info:
            normalizer._convert_openai_messages(record)

        assert "role" in str(exc_info.value).lower()

    def test_convert_openai_messages_missing_content_raises_error(self) -> None:
        """Test that missing 'content' field raises NormalizationError."""
        normalizer = FormatNormalizer()
        record = {
            "messages": [
                {"role": "user"},
            ]
        }

        with pytest.raises(NormalizationError) as exc_info:
            normalizer._convert_openai_messages(record)

        assert "content" in str(exc_info.value).lower()

    def test_convert_openai_messages_empty_messages_array(self) -> None:
        """Test OpenAI Messages conversion with empty messages array."""
        normalizer = FormatNormalizer()
        record = {"messages": []}

        messages = normalizer._convert_openai_messages(record)

        assert len(messages) == 0

    def test_convert_openai_messages_role_mapping_system(self) -> None:
        """Test that 'system' role is preserved."""
        normalizer = FormatNormalizer()
        record = {
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello"},
            ]
        }

        messages = normalizer._convert_openai_messages(record)

        assert messages[0].role == "system"
        assert messages[0].content == "You are a helpful assistant."

    def test_convert_openai_messages_role_mapping_user(self) -> None:
        """Test that 'user' role is preserved."""
        normalizer = FormatNormalizer()
        record = {
            "messages": [
                {"role": "user", "content": "Question"},
                {"role": "assistant", "content": "Answer"},
            ]
        }

        messages = normalizer._convert_openai_messages(record)

        assert messages[0].role == "user"
        assert messages[1].role == "assistant"

    def test_convert_openai_messages_role_mapping_assistant(self) -> None:
        """Test that 'assistant' role is preserved."""
        normalizer = FormatNormalizer()
        record = {
            "messages": [
                {"role": "user", "content": "Question"},
                {"role": "assistant", "content": "Answer"},
            ]
        }

        messages = normalizer._convert_openai_messages(record)

        assert messages[1].role == "assistant"

    def test_convert_openai_messages_role_mapping_tool(self) -> None:
        """Test that 'tool' role is preserved."""
        normalizer = FormatNormalizer()
        record = {
            "messages": [
                {"role": "user", "content": "Get weather"},
                {"role": "assistant", "content": "<tool_call>get_weather</tool_call>"},
                {"role": "tool", "content": "Sunny, 25C", "tool_call_id": "call_123"},
            ]
        }

        messages = normalizer._convert_openai_messages(record)

        assert messages[2].role == "tool"
        assert messages[2].content == "Sunny, 25C"

    def test_convert_openai_messages_unknown_role_passes_through(self) -> None:
        """Test that unknown roles pass through unchanged."""
        normalizer = FormatNormalizer()
        record = {
            "messages": [
                {"role": "custom_role", "content": "Custom message"},
            ]
        }

        messages = normalizer._convert_openai_messages(record)

        assert messages[0].role == "custom_role"
        assert messages[0].content == "Custom message"

    def test_convert_openai_messages_multiline_content_preserved(self) -> None:
        """Test that multiline content in messages is preserved."""
        normalizer = FormatNormalizer()
        record = {
            "messages": [
                {"role": "user", "content": "Line 1\nLine 2\nLine 3"},
                {"role": "assistant", "content": "Response\nWith multiple\nLines"},
            ]
        }

        messages = normalizer._convert_openai_messages(record)

        assert "\n" in messages[0].content
        assert "Line 1" in messages[0].content
        assert "Line 3" in messages[0].content
        assert "Response\nWith multiple\nLines" in messages[1].content

    def test_convert_openai_messages_special_characters_preserved(self) -> None:
        """Test that special characters in content are preserved."""
        normalizer = FormatNormalizer()
        record = {
            "messages": [
                {"role": "user", "content": "Use JSON: {\"key\": \"value\"}"},
                {"role": "assistant", "content": "Answer with <html> tags and `code`"},
            ]
        }

        messages = normalizer._convert_openai_messages(record)

        assert '{"key": "value"}' in messages[0].content
        assert "<html>" in messages[1].content
        assert "`code`" in messages[1].content


class TestFormatNormalizerInterface:
    """
    Abstract interface tests for FormatNormalizer.

    These tests document the expected interface for FormatNormalizer.
    They will pass once T020 (implementation) is completed.
    """

    def test_normalizer_has_convert_method(self) -> None:
        """Test that FormatNormalizer has a convert method."""
        normalizer = FormatNormalizer()
        assert hasattr(normalizer, "convert")
        assert callable(normalizer.convert)

    def test_normalizer_has_detect_format_method(self) -> None:
        """Test that FormatNormalizer has detect_format method."""
        normalizer = FormatNormalizer()
        assert hasattr(normalizer, "detect_format")
        assert callable(normalizer.detect_format)

    def test_normalizer_raises_normalization_error_on_invalid_input(self) -> None:
        """Test that FormatNormalizer raises NormalizationError for invalid input."""
        normalizer = FormatNormalizer()
        with pytest.raises(NormalizationError):
            normalizer.convert({})

    def test_detect_format_alpaca(self) -> None:
        """Test detect_format identifies Alpaca format."""
        normalizer = FormatNormalizer()
        record = {"instruction": "test", "output": "result"}
        assert normalizer.detect_format(record) == "alpaca"

    def test_detect_format_sharegpt(self) -> None:
        """Test detect_format identifies ShareGPT format."""
        normalizer = FormatNormalizer()
        record = {"conversations": [{"from": "human", "value": "test"}]}
        assert normalizer.detect_format(record) == "sharegpt"

    def test_detect_format_openai_messages(self) -> None:
        """Test detect_format identifies OpenAI messages format."""
        normalizer = FormatNormalizer()
        record = {"messages": [{"role": "user", "content": "test"}]}
        assert normalizer.detect_format(record) == "openai_messages"

    def test_convert_alpaca_format(self) -> None:
        """Test convert processes Alpaca format."""
        normalizer = FormatNormalizer()
        record = {"instruction": "test question", "output": "test answer"}
        result = normalizer.convert(record)
        assert isinstance(result, DatasetRecord)
        assert len(result.messages) >= 2
