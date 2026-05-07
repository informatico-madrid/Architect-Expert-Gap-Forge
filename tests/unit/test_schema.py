#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0
"""Tests for AnchorRecord schema validation."""

import json
import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from infrastructure.anchor_dataset.anchor_dataset_schema import (
    AnchorRecord,
    DSPY_FIELD_MAP,
    jsonl_to_dspy_examples,
)


# 1. Valid record passes validation
class TestValidRecord:
    def test_valid_record(self):
        record = AnchorRecord(
            id="anchor_001_00",
            domain="home_assistant",
            difficulty="easy",
            turn_count=3,
            legacy_pattern="HA config",
            domain_context="HA context",
            expected_trajectory="walk through",
            expected_coherence=0.9,
            expected_overall=0.85,
            expected_quality_score=0.8,
        )
        assert record.id == "anchor_001_00"
        assert record.domain == "home_assistant"
        assert record.difficulty == "easy"
        assert record.turn_count == 3


# 2. Out-of-range float raises
class TestOutOfRangeFloat:
    def test_out_of_range_float_raises(self):
        with pytest.raises(ValidationError):
            AnchorRecord(
                id="anchor_001_00",
                domain="home_assistant",
                difficulty="easy",
                turn_count=3,
                legacy_pattern="pattern",
                domain_context="context",
                expected_trajectory="trajectory",
                expected_coherence=1.5,  # > 1.0
                expected_overall=0.85,
                expected_quality_score=0.8,
            )


# 3. Invalid id pattern raises
class TestInvalidIdPattern:
    def test_invalid_id_pattern_raises(self):
        with pytest.raises(ValidationError):
            AnchorRecord(
                id="bad_id",
                domain="home_assistant",
                difficulty="easy",
                turn_count=3,
                legacy_pattern="pattern",
                domain_context="context",
                expected_trajectory="trajectory",
                expected_coherence=0.9,
                expected_overall=0.85,
                expected_quality_score=0.8,
            )


# 4. Extra field raises (model_config extra='forbid')
class TestExtraField:
    def test_extra_field_raises(self):
        with pytest.raises(ValidationError):
            AnchorRecord(
                id="anchor_001_00",
                domain="home_assistant",
                difficulty="easy",
                turn_count=3,
                legacy_pattern="pattern",
                domain_context="context",
                expected_trajectory="trajectory",
                expected_coherence=0.9,
                expected_overall=0.85,
                expected_quality_score=0.8,
                extra_unknown_field="unexpected",
            )


# 5. Round-trip model_dump_json -> model_validate works
class TestRoundTrip:
    def test_round_trip(self):
        original = AnchorRecord(
            id="anchor_001_00",
            domain="home_assistant",
            difficulty="easy",
            turn_count=3,
            legacy_pattern="pattern",
            domain_context="context",
            expected_trajectory="trajectory",
            expected_coherence=0.9,
            expected_overall=0.85,
            expected_quality_score=0.8,
        )
        json_str = original.model_dump_json()
        restored = AnchorRecord.model_validate_json(json_str)
        assert restored.id == original.id
        assert restored.domain == original.domain
        assert restored.difficulty == original.difficulty
        assert restored.turn_count == original.turn_count
        assert restored.legacy_pattern == original.legacy_pattern
        assert restored.expected_trajectory == original.expected_trajectory
        assert restored.expected_coherence == original.expected_coherence
        assert restored.expected_overall == original.expected_overall
        assert restored.expected_quality_score == original.expected_quality_score
        # Verify it's truly frozen / identical
        assert restored == original


# 6. DSPY_FIELD_MAP has correct keys and field counts
class TestDSPYFieldMap:
    def test_keys(self):
        assert set(DSPY_FIELD_MAP.keys()) == {"inputs", "labels"}

    def test_inputs_fields(self):
        assert DSPY_FIELD_MAP["inputs"] == ["legacy_pattern", "domain_context"]

    def test_labels_fields(self):
        assert len(DSPY_FIELD_MAP["labels"]) == 6

    def test_labels_content(self):
        expected = [
            "expected_trajectory",
            "expected_tool_usage_patterns",
            "expected_coherence",
            "expected_overall",
            "expected_quality_score",
            "expected_optimized_parameters",
        ]
        assert DSPY_FIELD_MAP["labels"] == expected


# 7. jsonl_to_dspy_examples: valid JSONL, empty file, invalid record
class TestJsonlToDspyExamples:
    def test_valid_jsonl(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            for i in range(3):
                record = {
                    "id": f"anchor_{i:03d}_00",
                    "domain": "home_assistant",
                    "difficulty": "easy",
                    "turn_count": 2,
                    "legacy_pattern": f"pattern_{i}",
                    "domain_context": f"context_{i}",
                    "expected_trajectory": f"trajectory_{i}",
                    "expected_coherence": 0.9,
                    "expected_overall": 0.85,
                    "expected_quality_score": 0.8,
                }
                f.write(json.dumps(record) + "\n")
            f_path = f.name
        try:
            examples = jsonl_to_dspy_examples(f_path)
            assert len(examples) == 3
        finally:
            Path(f_path).unlink()

    def test_empty_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f_path = f.name
        try:
            examples = jsonl_to_dspy_examples(f_path)
            assert examples == []
        finally:
            Path(f_path).unlink()

    def test_invalid_record(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write(json.dumps({"bad_field": "nope"}) + "\n")
            f_path = f.name
        try:
            with pytest.raises(ValidationError):
                jsonl_to_dspy_examples(f_path)
        finally:
            Path(f_path).unlink()
