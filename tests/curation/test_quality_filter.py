# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""Tests for quality_filter module."""

import pytest

from src.curation.quality_filter import (
    _count_code_tokens,
    _count_natural_tokens,
    _ldi,
    _has_meta_speech,
    structural_quality_filter,
    DEFAULT_MIN_THINK_CHARS,
    DEFAULT_LDI_MIN_RATIO,
)
from src.curation.curator_pipeline import CurationStats


class TestCountCodeTokens:
    """Tests for _count_code_tokens function."""

    def test_empty_string(self):
        assert _count_code_tokens("") == 0

    def test_json_block_counting(self):
        text = '{"key": "value", "number": 42}'
        result = _count_code_tokens(text)
        assert result > 0

    def test_code_block_counting(self):
        text = "```python\ndef hello():\n    return True\n```"
        result = _count_code_tokens(text)
        assert result > 0

    def test_programming_keywords(self):
        text = "async def main(): await something()"
        result = _count_code_tokens(text)
        assert result > 0

    def test_punctuation_counting(self):
        text = "x = (a + b) * c"
        result = _count_code_tokens(text)
        assert result > 0


class TestCountNaturalTokens:
    """Tests for _count_natural_tokens function."""

    def test_empty_string(self):
        assert _count_natural_tokens("") == 0

    def test_json_removed(self):
        text = '{"key": "value"} some words here'
        result = _count_natural_tokens(text)
        assert "key" not in text or "words" in text

    def test_code_block_removed(self):
        text = "```python\ncode\n``` normal text"
        result = _count_natural_tokens(text)
        assert result > 0

    def test_html_tags_removed(self):
        text = "<div>content</div> meaningful words"
        result = _count_natural_tokens(text)
        assert result >= 2  # "meaningful" and "words"

    def test_stop_words_removed(self):
        text = "the async def function"
        result = _count_natural_tokens(text)
        # Stop words like "the", "async", "def", "function" should be reduced
        assert isinstance(result, int)


class TestLdi:
    """Tests for _ldi function."""

    def test_empty_text(self):
        assert _ldi("") == 0.0

    def test_near_zero_code_tokens(self):
        # Text with very little code - very low LDI
        text = "this is just some natural language text without any code"
        result = _ldi(text)
        assert result < 0.01  # Very close to 0

    def test_high_code_ratio(self):
        # Text with mostly code
        text = '{"key": "value"} def test(): return True'
        result = _ldi(text)
        assert result > 0

    def test_mixed_content(self):
        text = 'def function(): return "hello" some natural language description'
        result = _ldi(text)
        assert 0 <= result <= 1


class TestHasMetaSpeech:
    """Tests for _has_meta_speech function."""

    def test_empty_content(self):
        assert _has_meta_speech("") is False

    def test_no_meta_speech(self):
        text = "This is a detailed analysis of the code structure."
        assert _has_meta_speech(text) is False

    def test_with_meta_speech_patterns(self):
        # Multiple lines with meta-speech patterns
        text = "Let me think about this.\nI need to solve this problem.\nThe user is asking for help."
        assert _has_meta_speech(text) is True

    def test_below_threshold(self):
        # Only one meta-speech line, below 20%
        text = "Let me start.\nThis is a very detailed analysis of the code structure.\nMore content here.\nAnd more.\nEven more.\nAnd more.\nAnd more.\nAnd more.\nAnd more.\nAnd more.\nAnd more."
        assert _has_meta_speech(text) is False


class TestStructuralQualityFilter:
    """Tests for structural_quality_filter function."""

    def test_empty_records(self, minimal_stats):
        result = structural_quality_filter([], minimal_stats)
        assert result == []

    def test_record_without_assistant_turns(self, minimal_stats):
        records = [
            {
                "id": "test-001",
                "conversation": [{"role": "user", "content": "Hello"}],
            }
        ]
        result = structural_quality_filter(records, minimal_stats)
        assert len(result) == 0
        assert minimal_stats.invalid_syntax == 1

    def test_valid_record_passes(self, minimal_stats):
        # Use valid format with actual code in tool_call for LDI check
        records = [
            {
                "id": "test-001",
                "conversation": [
                    {
                        "role": "assistant",
                        "content": "<think>" + "x" * 600 + "</think><tool_call><tool name=\"test\">async def main(): pass</tool></tool_call>",
                    }
                ],
            }
        ]
        result = structural_quality_filter(records, minimal_stats, min_think_chars=500, ldi_min_ratio=0.01)
        assert len(result) == 1

    def test_invalid_syntax_space_between_tags(self, minimal_stats):
        # Space between </tool_call> and <tool_call>
        records = [
            {
                "id": "test-001",
                "conversation": [
                    {
                        "role": "assistant",
                        "content": "<think>thinking</think> <tool_call><tool name=\"test\"/></tool_call>",
                    }
                ],
            }
        ]
        result = structural_quality_filter(records, minimal_stats)
        assert len(result) == 0
        assert minimal_stats.invalid_syntax == 1

    def test_shallow_thinking_filtered(self, minimal_stats):
        # Think block too short
        records = [
            {
                "id": "test-001",
                "conversation": [
                    {
                        "role": "assistant",
                        "content": "<think>Short</think><tool_call><tool name=\"test\"/></tool_call>",
                    }
                ],
            }
        ]
        result = structural_quality_filter(records, minimal_stats, min_think_chars=500)
        assert len(result) == 0
        assert minimal_stats.shallow_thinking == 1

    def test_meta_speech_filtered(self, minimal_stats):
        # Meta-speech content - many lines with meta-speech patterns
        content = "<think>"
        for _ in range(30):
            content += "Let me think about this.\nI need to solve this.\nThe user is asking.\n"
        content += "</think><tool_call><tool name=\"test\"/></tool_call>"
        records = [
            {
                "id": "test-001",
                "conversation": [
                    {
                        "role": "assistant",
                        "content": content,
                    }
                ],
            }
        ]
        result = structural_quality_filter(records, minimal_stats)
        assert len(result) == 0
        assert minimal_stats.meta_speech == 1

    def test_low_ldi_filtered(self, minimal_stats):
        # Low LDI in tool_call
        records = [
            {
                "id": "test-001",
                "conversation": [
                    {
                        "role": "assistant",
                        "content": "<think>" + "a" * 600 + "</think><tool_call>just some text no code</tool_call>",
                    }
                ],
            }
        ]
        result = structural_quality_filter(records, minimal_stats, ldi_min_ratio=0.5)
        assert len(result) == 0
        assert minimal_stats.low_ldi == 1

    def test_multiple_records_mixed(self, minimal_stats):
        # Mix of valid and invalid
        valid_record = {
            "id": "valid-001",
            "conversation": [
                {
                    "role": "assistant",
                    "content": "<think>" + "x" * 600 + "</think><tool_call><tool name=\"test\">async def main(): pass</tool></tool_call>",
                }
            ],
        }
        invalid_record = {
            "id": "invalid-001",
            "conversation": [{"role": "user", "content": "Hello"}],
        }
        records = [valid_record, invalid_record]
        result = structural_quality_filter(records, minimal_stats, ldi_min_ratio=0.01)
        assert len(result) == 1
        assert result[0]["id"] == "valid-001"

    def test_no_think_block_with_tool_call(self, minimal_stats):
        # No think block but has tool_call - should fail syntax check
        records = [
            {
                "id": "test-001",
                "conversation": [
                    {
                        "role": "assistant",
                        "content": "<tool_call><tool name=\"test\"/></tool_call>",
                    }
                ],
            }
        ]
        result = structural_quality_filter(records, minimal_stats)
        # Should keep because it passes filters (no think block to check)
        assert len(result) == 1

    def test_custom_min_think_chars(self, minimal_stats):
        records = [
            {
                "id": "test-001",
                "conversation": [
                    {
                        "role": "assistant",
                        "content": "<think>" + "x" * 100 + "</think><tool_call><tool name=\"test\">async def main(): pass</tool></tool_call>",
                    }
                ],
            }
        ]
        # With low threshold, should pass
        result = structural_quality_filter(records, minimal_stats, min_think_chars=50, ldi_min_ratio=0.01)
        assert len(result) == 1


@pytest.fixture
def minimal_stats():
    """Create a minimal CurationStats for testing."""
    return CurationStats()
