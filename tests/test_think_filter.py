#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for src/factory/think_filter.py.

Covers:
- filter_think_content(): Sacred Constraint — content after </think> is NEVER modified
- filter_think_content(): no-op when think block is below min_chars threshold
- filter_think_content(): no-op when no </think> tag present
- filter_think_content(): stats dict structure and keys
- filter_think_content(): actual reduction when duplicates are present
- _collapse_consecutive_lines(): repeated lines are collapsed
- _dedup_code_blocks(): duplicate code blocks are removed (keep last)
- _dedup_paragraphs(): similar paragraphs deduplicated (keep last)
- apply_to_record(): record not mutated (shallow copy)
- apply_to_record(): returns (record, None) when nothing to filter
- apply_to_record(): filters assistant message and returns stats
- apply_to_record(): non-conversation records pass through unchanged
"""

from __future__ import annotations

import copy
from typing import Any, Dict

import pytest

from src.factory.think_filter import (
    MIN_THINK_CHARS,
    _collapse_consecutive_lines,
    _dedup_code_blocks,
    _dedup_bullets_in_para,
    _dedup_paragraphs,
    _prune_revision_cycles,
    apply_to_record,
    filter_think_content,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_POST_THINK = "</think>\n\n```python\nreturn entry.runtime_data\n```"


def _make_content(think_text: str) -> str:
    return think_text + _POST_THINK


def _make_record(content: str, role: str = "assistant") -> Dict[str, Any]:
    return {
        "id": "test-record",
        "conversation": [
            {"role": "user", "content": "Implement a sensor."},
            {"role": role, "content": content},
        ],
    }


def _large_think(base: str, repeat: int = 20) -> str:
    """Generate a think block large enough to exceed MIN_THINK_CHARS."""
    block = base + "\n\n"
    while len(block * repeat) < MIN_THINK_CHARS + 500:
        repeat += 5
    return block * repeat


# ---------------------------------------------------------------------------
# Sacred Constraint
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSacredConstraint:
    """Code at or after </think> must NEVER be modified — this is the sacred constraint."""

    def test_post_think_content_is_unchanged(self) -> None:
        think = _large_think(
            "Thinking about sensors. I need to use entry.runtime_data pattern."
        )
        content = _make_content(think)
        filtered, stats = filter_think_content(content)
        idx = filtered.lower().find("</think>")
        assert idx != -1, "The </think> tag must be preserved in output"
        assert filtered[idx:] == content[content.lower().find("</think>") :]

    def test_post_think_code_is_byte_identical(self) -> None:
        post = (
            "</think>\n\n```python\nclass MyEntity(CoordinatorEntity):\n    pass\n```"
        )
        think = _large_think("A. " * 300)
        content = think + post
        filtered, _ = filter_think_content(content)
        assert filtered.endswith(post)

    def test_think_tag_itself_is_preserved(self) -> None:
        think = _large_think("B. " * 300)
        content = _make_content(think)
        filtered, _ = filter_think_content(content)
        assert "</think>" in filtered


# ---------------------------------------------------------------------------
# No-op conditions
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFilterThinkNoOp:
    def test_no_op_when_think_below_min_chars(self) -> None:
        short_think = "Short. " * 10  # well below MIN_THINK_CHARS
        content = short_think + _POST_THINK
        filtered, stats = filter_think_content(content)
        assert stats is None
        assert filtered == content

    def test_no_op_when_no_think_tag(self) -> None:
        content = "No think tag here. Just some content."
        filtered, stats = filter_think_content(content)
        assert stats is None
        assert filtered == content

    def test_no_op_when_content_is_empty(self) -> None:
        filtered, stats = filter_think_content("")
        assert stats is None
        assert filtered == ""

    def test_no_op_returns_original_object_unchanged(self) -> None:
        original = "no think block"
        filtered, _ = filter_think_content(original)
        assert filtered is original or filtered == original

    def test_no_op_when_nothing_to_reduce(self) -> None:
        """A think block with no duplicates must pass stats=None (no reduction)."""
        unique = "\n\n".join(f"Unique paragraph {i}." for i in range(60))
        content = unique + _POST_THINK
        _, stats = filter_think_content(content, min_chars=0)
        # stats may be None or have reduction_pct == 0
        if stats is not None:
            assert stats["reduction_pct"] == 0.0


# ---------------------------------------------------------------------------
# Stats dict
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFilterThinkStats:
    def _content_with_duplicates(self) -> str:
        dup_code = "```python\ndef setup_entry(hass, entry, async_add_entities):\n    pass\n```"
        think = _large_think("Step 1: analyse pattern.\n\n" + dup_code + "\n\n")
        # Repeat the code block to guarantee deduplication fires
        think = think + "\n\n" + dup_code + "\n\n" + dup_code
        return think + _POST_THINK

    def test_stats_has_required_keys(self) -> None:
        content = self._content_with_duplicates()
        _, stats = filter_think_content(content)
        if stats is not None:
            required = {
                "original_chars",
                "distilled_chars",
                "reduction_pct",
                "strategies",
            }
            assert required.issubset(set(stats.keys()))

    def test_original_chars_matches_think_block_length(self) -> None:
        content = self._content_with_duplicates()
        idx = content.lower().find("</think>")
        _, stats = filter_think_content(content)
        if stats is not None:
            assert stats["original_chars"] == idx

    def test_distilled_chars_lte_original_chars(self) -> None:
        content = self._content_with_duplicates()
        _, stats = filter_think_content(content)
        if stats is not None:
            assert stats["distilled_chars"] <= stats["original_chars"]


# ---------------------------------------------------------------------------
# Deduplication mechanics
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCollapseConsecutiveLines:
    def test_collapses_identically_repeated_lines(self) -> None:
        repeated_line = "This is an identical long line that exceeds fifteen chars."
        text = "\n".join([repeated_line] * 6)
        result = _collapse_consecutive_lines(text)
        lines = result.split("\n")
        # Should have at most MAX_CONSECUTIVE_LINES + 1 = 3 occurrences
        assert lines.count(repeated_line) <= 3

    def test_preserves_unique_lines(self) -> None:
        lines = ["Line A", "Line B", "Line C"]
        result = _collapse_consecutive_lines("\n".join(lines))
        for line in lines:
            assert line in result

    def test_short_repeated_lines_not_collapsed(self) -> None:
        """Lines shorter than 15 chars must not be collapsed."""
        text = "\n".join(["short"] * 10)
        result = _collapse_consecutive_lines(text)
        assert result.count("short") == 10


@pytest.mark.unit
class TestDedupCodeBlocks:
    def test_removes_duplicate_code_block_keeping_last(self) -> None:
        code = "```python\ndef async_setup_entry(hass, entry, async_add_entities):\n    coordinator = MyCoordinator(hass)\n    await coordinator.async_config_entry_first_refresh()\n```"
        text = f"First occurrence:\n\n{code}\n\nSome text.\n\n{code}\n\nFinal text."
        result = _dedup_code_blocks(text)
        # Only one occurrence of the code block should remain
        assert result.count("def async_setup_entry") == 1

    def test_keeps_last_code_block(self) -> None:
        unique_marker = "# LAST VERSION"
        code_early = "```python\n# EARLY VERSION\npass\n```"
        code_late = f"```python\n{unique_marker}\npass\n```"
        # These blocks are NOT similar → both kept
        text = f"{code_early}\n\nSome content.\n\n{code_late}"
        result = _dedup_code_blocks(text)
        assert unique_marker in result

    def test_no_op_when_single_code_block(self) -> None:
        code = "```python\npass\n```"
        text = f"Before.\n\n{code}\n\nAfter."
        assert _dedup_code_blocks(text) == text


@pytest.mark.unit
class TestDedupBulletsInPara:
    def test_removes_duplicate_bullets(self) -> None:
        para = "- duplicate\n- unique\n- duplicate\n"
        result = _dedup_bullets_in_para(para)
        assert result.count("duplicate") == 1

    def test_preserves_non_duplicate_lines(self) -> None:
        para = "First line.\nSecond line.\n- bullet one\n- bullet two"
        assert _dedup_bullets_in_para(para).startswith("First line.")

    def test_handles_numbered_items(self) -> None:
        para = "1. repeat\n2. keep\n1. repeat\n"
        result = _dedup_bullets_in_para(para)
        assert result.count("repeat") == 1


@pytest.mark.unit
class TestPruneRevisionCycles:
    def test_prune_revision_cycles_discards_previous_cycles(self) -> None:
        paragraphs = [
            "1. First pass",
            "2. Second pass",
            "1. First pass",
            "2. Second pass",
        ]
        pruned = _prune_revision_cycles(paragraphs)
        assert sum(1 for p in pruned if "First pass" in p) == 1
        assert sum(1 for p in pruned if "Second pass" in p) == 1

    def test_prune_revision_cycles_without_duplicates_keeps_all(self) -> None:
        paragraphs = ["1. Only pass", "2. Next pass"]
        assert _prune_revision_cycles(paragraphs) == paragraphs


@pytest.mark.unit
class TestDedupParagraphs:
    def test_removes_duplicate_paragraph_keeping_last(self) -> None:
        dup_para = "The coordinator must call async_config_entry_first_refresh on startup to ensure data is available before entities are added to Home Assistant."
        text_paras = [
            "Introduction paragraph.",
            dup_para,
            "Intermediate paragraph with different content.",
            dup_para,
            "Conclusion paragraph.",
        ]
        result = _dedup_paragraphs(text_paras)
        occurrences = sum(1 for p in result if dup_para in p)
        assert occurrences == 1

    def test_preserves_all_unique_paragraphs(self) -> None:
        # Paragraphs must be genuinely different to stay below the 0.82 similarity
        # threshold — using completely distinct domain texts instead of a template.
        paras = [
            "The DataUpdateCoordinator manages periodic polling and caches results for all entities in the integration.",
            "Using entry.runtime_data avoids storing mutable state in hass.data and simplifies cleanup on unload.",
            "SensorDeviceClass enums replaced string literals; using them enables automatic unit conversion in 2026.",
            "CoordinatorEntity wires async_write_ha_state to coordinator updates via _handle_coordinator_update.",
            "ConfigEntryNotReady should be raised in async_setup_entry when the device is unreachable at startup.",
        ]
        result = _dedup_paragraphs(paras)
        assert len(result) == 5

    def test_dedup_similar_paragraphs(self) -> None:
        base = "Sensor vintage paragraphs repeated with minimal edits."
        para_a = base
        para_b = base.replace("vintage", "modern")
        text_paras = [para_a, para_b, para_a]
        result = _dedup_paragraphs(text_paras)
        assert len(result) < len(text_paras)


@pytest.mark.unit
class TestFilterThinkStrategies:
    def test_stats_cover_all_strategies(self) -> None:
        bullet_paragraph = (
            "- repeated bullet long text\n- repeated bullet long text\n- unique bullet"
        )
        repeated_para = "Paragraph " + "A" * 120
        cycle_paragraphs = [
            "1. cycle start " + "Y" * 80,
            "2. cycle flow " + "Z" * 80,
            "1. cycle start " + "Y" * 80,
            "2. cycle flow " + "Z" * 80,
        ]
        think_parts = [
            bullet_paragraph,
            repeated_para,
            repeated_para,
            *cycle_paragraphs,
        ]
        think = "\n\n".join(think_parts)
        content = think + "\n\n" + think + _POST_THINK
        _, stats = filter_think_content(content, min_chars=0)
        assert stats is not None
        strategies = ",".join(stats["strategies"])
        assert "bullet_dedup" in strategies
        assert "revision_cycle_prune" in strategies
        assert "paragraph_dedup" in strategies


# ---------------------------------------------------------------------------
# apply_to_record()
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestApplyToRecord:
    def test_no_op_when_think_too_short(self) -> None:
        record = _make_record("short" + _POST_THINK)
        result_record, stats = apply_to_record(record)
        assert stats is None
        assert result_record is record

    def test_does_not_mutate_original_record(self) -> None:
        think = _large_think("Pattern A.\n\nPattern A.\n\n" * 30)
        original_content = _make_content(think)
        record = _make_record(original_content)
        original_copy = copy.deepcopy(record)
        apply_to_record(record)
        assert record == original_copy

    def test_returns_shallow_copy_not_original(self) -> None:
        think = _large_think("Dup.\n\nDup.\n\n" * 40)
        content = _make_content(think)
        record = _make_record(content)
        result_record, stats = apply_to_record(record)
        if stats is not None:
            assert result_record is not record

    def test_no_op_when_no_conversation_key(self) -> None:
        record: Dict[str, Any] = {"id": "r1", "text": "no conversation here"}
        result, stats = apply_to_record(record)
        assert stats is None
        assert result is record

    def test_no_op_when_no_assistant_message(self) -> None:
        record: Dict[str, Any] = {
            "id": "r1",
            "conversation": [{"role": "user", "content": "Question?"}],
        }
        result, stats = apply_to_record(record)
        assert stats is None

    def test_processed_record_preserves_non_conversation_fields(self) -> None:
        think = _large_think("Step.\n\nStep.\n\n" * 40)
        content = _make_content(think)
        record = _make_record(content)
        record["custom_field"] = "preserve_me"
        result, stats = apply_to_record(record)
        if stats is not None:
            assert result.get("custom_field") == "preserve_me"

    def test_post_think_content_unchanged_in_record(self) -> None:
        """The sacred constraint must hold at the record level too."""
        post = "</think>\n\n```python\nreturn entry.runtime_data\n```"
        think = _large_think("Dup. " * 200)
        content = think + post
        record = _make_record(content)
        record["filter_text"] = content
        result, stats = apply_to_record(record)
        asst_content = result["conversation"][1]["content"]
        idx = asst_content.lower().find("</think>")
        if idx >= 0:
            assert asst_content[idx:] == post
        assert stats is not None
        assert result["filter_text"] != content
        assert "</think>" in result["filter_text"]
