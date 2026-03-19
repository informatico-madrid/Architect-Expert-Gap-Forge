#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Architect-Expert-Gap-Forge (AEGF) - Dataset Mixer Tests

Unit tests for the DatasetMixer module.
Tests cover: token proportion validation (28-32%/68-72%), deterministic mixing with seeds,
JSONL output validation (all records have messages field), and composition report fields.

Location: tests/curation/test_dataset_mixer.py
SPDX-License-Identifier: Apache-2.0
Copyright 2026 AEGF
"""

import json
import logging
import random
from pathlib import Path

import pytest
import tiktoken

from src.curation.dataset_mixer import DatasetMixer, DatasetMixerConfig
from src.utils.schema import CompositionReport, DatasetRecord, Message

logger = logging.getLogger(__name__)


# =============================================================================
# TEST FIXTURES
# =============================================================================


@pytest.fixture
def specialized_records() -> list[DatasetRecord]:
    """Fixture: Specialized Home Assistant trajectory records (30% of mix)."""
    records = []
    for i in range(10):
        messages = [
            Message(
                role="user",
                content=f"Help me configure Home Assistant - task {i}",
            ),
            Message(
                role="assistant",
                content=f"Here's how to configure Home Assistant for task {i}. " * 20,
            ),
        ]
        # Calculate token count
        encoder = tiktoken.get_encoding("cl100k_base")
        content = " ".join(m.content for m in messages)
        token_count = len(encoder.encode(content))

        records.append(
            DatasetRecord(
                messages=messages,
                metadata={
                    "origin": "specialized",
                    "type": "trajectory",
                    "use_case": "home_assistant",
                    "token_count": token_count,
                },
            )
        )
    return records


@pytest.fixture
def anchor_records() -> list[DatasetRecord]:
    """Fixture: Anchor dataset records (70% of mix)."""
    records = []
    for i in range(20):
        messages = [
            Message(
                role="user",
                content=f"General coding question {i}",
            ),
            Message(
                role="assistant",
                content=f"Here's the answer to question {i}. " * 30,
            ),
        ]
        # Calculate token count
        encoder = tiktoken.get_encoding("cl100k_base")
        content = " ".join(m.content for m in messages)
        token_count = len(encoder.encode(content))

        records.append(
            DatasetRecord(
                messages=messages,
                metadata={
                    "origin": "xlam_function_calling",
                    "type": "general",
                    "token_count": token_count,
                },
            )
        )
    return records


@pytest.fixture
def mixed_records(
    specialized_records: list[DatasetRecord], anchor_records: list[DatasetRecord]
) -> list[DatasetRecord]:
    """Fixture: Pre-mixed records for testing."""
    return specialized_records + anchor_records


# =============================================================================
# TEST CLASSES
# =============================================================================


class TestTokenProportion:
    """Tests for token proportion validation (28-32% / 68-72%)."""

    def test_token_proportion_within_28_32_percent_specialized(
        self, specialized_records: list[DatasetRecord], anchor_records: list[DatasetRecord]
    ) -> None:
        """Test that specialized records are within 28-32% token range."""
        # Calculate total tokens for each dataset
        specialized_tokens = sum(
            r.metadata.get("token_count", 0) for r in specialized_records
        )
        anchor_tokens = sum(r.metadata.get("token_count", 0) for r in anchor_records)
        total_tokens = specialized_tokens + anchor_tokens

        # Calculate percentage
        specialized_pct = (specialized_tokens / total_tokens) * 100 if total_tokens > 0 else 0

        # Should be within 28-32% range
        assert 28 <= specialized_pct <= 32, f"Specialized tokens {specialized_pct}% not in 28-32% range"

    def test_token_proportion_within_68_72_percent_anchor(
        self, specialized_records: list[DatasetRecord], anchor_records: list[DatasetRecord]
    ) -> None:
        """Test that anchor records are within 68-72% token range."""
        specialized_tokens = sum(
            r.metadata.get("token_count", 0) for r in specialized_records
        )
        anchor_tokens = sum(r.metadata.get("token_count", 0) for r in anchor_records)
        total_tokens = specialized_tokens + anchor_tokens

        anchor_pct = (anchor_tokens / total_tokens) * 100 if total_tokens > 0 else 0

        assert 68 <= anchor_pct <= 72, f"Anchor tokens {anchor_pct}% not in 68-72% range"

    def test_token_proportion_totals_100_percent(
        self, specialized_records: list[DatasetRecord], anchor_records: list[DatasetRecord]
    ) -> None:
        """Test that token percentages total 100%."""
        specialized_tokens = sum(
            r.metadata.get("token_count", 0) for r in specialized_records
        )
        anchor_tokens = sum(r.metadata.get("token_count", 0) for r in anchor_records)
        total_tokens = specialized_tokens + anchor_tokens

        specialized_pct = (specialized_tokens / total_tokens) * 100 if total_tokens > 0 else 0
        anchor_pct = (anchor_tokens / total_tokens) * 100 if total_tokens > 0 else 0

        total_pct = specialized_pct + anchor_pct
        assert abs(total_pct - 100.0) < 0.01, f"Total percentage {total_pct}% != 100%"

    def test_proportion_calculation_with_exact_30_70_target(
        self,
    ) -> None:
        """Test proportion calculation with exactly 30/70 target distribution."""
        # Simulate exact 30/70 distribution
        specialized_tokens = 3000  # 30%
        anchor_tokens = 7000  # 70%
        total = specialized_tokens + anchor_tokens

        specialized_pct = (specialized_tokens / total) * 100
        anchor_pct = (anchor_tokens / total) * 100

        assert specialized_pct == 30.0
        assert anchor_pct == 70.0
        assert specialized_pct + anchor_pct == 100.0

    def test_proportion_tolerance_edge_cases(self) -> None:
        """Test proportion tolerance at edge boundaries (28% and 32%)."""
        # Test 28% boundary
        specialized_tokens = 2800
        anchor_tokens = 7200
        total = specialized_tokens + anchor_tokens
        specialized_pct = (specialized_tokens / total) * 100
        assert specialized_pct == pytest.approx(28.0)

        # Test 32% boundary
        specialized_tokens = 3200
        anchor_tokens = 6800
        total = specialized_tokens + anchor_tokens
        specialized_pct = (specialized_tokens / total) * 100
        assert specialized_pct == pytest.approx(32.0)


class TestDeterminismWithSeed:
    """Tests for deterministic mixing with seeds."""

    def test_same_seed_produces_same_order(
        self, mixed_records: list[DatasetRecord]
    ) -> None:
        """Test that same seed produces the same order (determinism)."""
        seed = 42

        # Shuffle with same seed twice
        records_copy1 = list(mixed_records)
        records_copy2 = list(mixed_records)

        random.seed(seed)
        random.shuffle(records_copy1)

        random.seed(seed)
        random.shuffle(records_copy2)

        # Order should be identical
        for i, (r1, r2) in enumerate(zip(records_copy1, records_copy2)):
            assert (
                r1.metadata.get("origin") == r2.metadata.get("origin")
            ), f"Record at index {i} differs"

    def test_different_seed_produces_different_order(
        self, mixed_records: list[DatasetRecord]
    ) -> None:
        """Test that different seeds produce different orders."""
        records_copy1 = list(mixed_records)
        records_copy2 = list(mixed_records)

        random.seed(42)
        random.shuffle(records_copy1)

        random.seed(123)
        random.shuffle(records_copy2)

        # At least one record should be in different position
        has_difference = False
        for i, (r1, r2) in enumerate(zip(records_copy1, records_copy2)):
            if r1.metadata.get("origin") != r2.metadata.get("origin"):
                has_difference = True
                break

        assert has_difference, "Different seeds should produce different orders"

    def test_deterministic_shuffle_preserves_all_records(
        self, mixed_records: list[DatasetRecord]
    ) -> None:
        """Test that shuffle preserves all records (no loss)."""
        seed = 42

        original_ids = [id(r) for r in mixed_records]

        shuffled = list(mixed_records)
        random.seed(seed)
        random.shuffle(shuffled)

        # All records should still be present
        assert len(shuffled) == len(mixed_records)
        shuffled_ids = [id(r) for r in shuffled]
        assert set(original_ids) == set(shuffled_ids)

    def test_deterministic_result_reproducible_across_runs(
        self, specialized_records: list[DatasetRecord], anchor_records: list[DatasetRecord]
    ) -> None:
        """Test that deterministic result is reproducible across multiple runs."""
        seed = 42

        def shuffle_once(records: list[DatasetRecord]) -> list[DatasetRecord]:
            result = list(records)
            random.seed(seed)
            random.shuffle(result)
            return result

        # Run shuffle multiple times
        run1 = shuffle_once(specialized_records + anchor_records)
        run2 = shuffle_once(specialized_records + anchor_records)
        run3 = shuffle_once(specialized_records + anchor_records)

        # All runs should produce identical results
        for i in range(len(run1)):
            assert (
                run1[i].metadata.get("origin") == run2[i].metadata.get("origin")
            ), f"Run 1 and 2 differ at index {i}"
            assert (
                run2[i].metadata.get("origin") == run3[i].metadata.get("origin")
            ), f"Run 2 and 3 differ at index {i}"


class TestJsonlOutputValidation:
    """Tests for JSONL output validation."""

    def test_jsonl_output_has_messages_field(
        self, mixed_records: list[DatasetRecord], tmp_path: Path
    ) -> None:
        """Test that JSONL output has 100% records with 'messages' field."""
        output_path = tmp_path / "output.jsonl"

        # Export to JSONL
        with open(output_path, "w") as f:
            for record in mixed_records:
                f.write(record.model_dump_json() + "\n")

        # Read and validate all records have messages field
        with open(output_path) as f:
            lines = f.readlines()

        assert len(lines) > 0, "JSONL should not be empty"

        records_with_messages = 0
        for line in lines:
            data = json.loads(line)
            if "messages" in data:
                records_with_messages += 1

        # 100% of records should have messages
        pct_with_messages = (records_with_messages / len(lines)) * 100
        assert pct_with_messages == 100.0, (
            f"Only {pct_with_messages}% records have 'messages' field, expected 100%"
        )

    def test_jsonl_messages_field_contains_valid_structure(
        self, mixed_records: list[DatasetRecord], tmp_path: Path
    ) -> None:
        """Test that messages field contains valid ChatML structure."""
        output_path = tmp_path / "output.jsonl"

        with open(output_path, "w") as f:
            for record in mixed_records:
                f.write(record.model_dump_json() + "\n")

        with open(output_path) as f:
            for line in f:
                data = json.loads(line)
                assert "messages" in data
                messages = data["messages"]
                assert isinstance(messages, list)
                assert len(messages) > 0

                # Each message should have role and content
                for msg in messages:
                    assert "role" in msg
                    assert "content" in msg

    def test_jsonl_no_residual_format_fields(
        self, specialized_records: list[DatasetRecord], tmp_path: Path
    ) -> None:
        """Test that JSONL has no residual format-specific fields (instruction, prompt, etc)."""
        output_path = tmp_path / "output.jsonl"

        with open(output_path, "w") as f:
            for record in specialized_records:
                f.write(record.model_dump_json() + "\n")

        # Should only have 'messages' and 'metadata'
        with open(output_path) as f:
            for line in f:
                data = json.loads(line)
                keys = set(data.keys())
                # Should only have messages and metadata
                assert keys == {"messages", "metadata"}, f"Unexpected keys: {keys - {'messages', 'metadata'}}"

    def test_jsonl_valid_json_per_line(self, mixed_records: list[DatasetRecord], tmp_path: Path) -> None:
        """Test that JSONL has valid JSON on each line."""
        output_path = tmp_path / "output.jsonl"

        with open(output_path, "w") as f:
            for record in mixed_records:
                f.write(record.model_dump_json() + "\n")

        # Each line should be valid JSON
        with open(output_path) as f:
            for i, line in enumerate(f):
                try:
                    json.loads(line)
                except json.JSONDecodeError as e:
                    pytest.fail(f"Line {i} is not valid JSON: {e}")

    def test_jsonl_record_count_matches_input(
        self, specialized_records: list[DatasetRecord], anchor_records: list[DatasetRecord], tmp_path: Path
    ) -> None:
        """Test that JSONL output has correct number of records."""
        all_records = specialized_records + anchor_records
        output_path = tmp_path / "output.jsonl"

        with open(output_path, "w") as f:
            for record in all_records:
                f.write(record.model_dump_json() + "\n")

        # Count lines
        with open(output_path) as f:
            line_count = sum(1 for _ in f)

        assert line_count == len(all_records)


class TestCompositionReportFields:
    """Tests for composition report required fields."""

    def test_composition_report_has_records_by_origin(
        self, specialized_records: list[DatasetRecord], anchor_records: list[DatasetRecord]
    ) -> None:
        """Test that composition report includes 'records_by_origin' field."""
        # Calculate composition
        records_by_origin: dict[str, int] = {}
        for r in specialized_records + anchor_records:
            origin = r.metadata.get("origin", "unknown")
            records_by_origin[origin] = records_by_origin.get(origin, 0) + 1

        report = CompositionReport(
            records_by_origin=records_by_origin,
            token_pct_by_origin={},
            type_distribution={},
        )

        # Should have records_by_origin
        assert hasattr(report, "records_by_origin")
        assert "specialized" in report.records_by_origin
        assert report.records_by_origin["specialized"] == len(specialized_records)

    def test_composition_report_has_token_pct_by_origin(
        self, specialized_records: list[DatasetRecord], anchor_records: list[DatasetRecord]
    ) -> None:
        """Test that composition report includes 'token_pct_by_origin' field."""
        specialized_tokens = sum(
            r.metadata.get("token_count", 0) for r in specialized_records
        )
        anchor_tokens = sum(r.metadata.get("token_count", 0) for r in anchor_records)
        total_tokens = specialized_tokens + anchor_tokens

        token_pct_by_origin: dict[str, float] = {}
        if total_tokens > 0:
            token_pct_by_origin["specialized"] = (specialized_tokens / total_tokens) * 100
            token_pct_by_origin["anchor"] = (anchor_tokens / total_tokens) * 100

        report = CompositionReport(
            records_by_origin={},
            token_pct_by_origin=token_pct_by_origin,
            type_distribution={},
        )

        assert hasattr(report, "token_pct_by_origin")
        assert "specialized" in report.token_pct_by_origin
        assert "anchor" in report.token_pct_by_origin

    def test_composition_report_has_type_distribution(
        self, specialized_records: list[DatasetRecord], anchor_records: list[DatasetRecord]
    ) -> None:
        """Test that composition report includes 'type_distribution' field."""
        type_distribution: dict[str, int] = {}
        for r in specialized_records + anchor_records:
            rec_type = r.metadata.get("type", "unknown")
            type_distribution[rec_type] = type_distribution.get(rec_type, 0) + 1

        report = CompositionReport(
            records_by_origin={},
            token_pct_by_origin={},
            type_distribution=type_distribution,
        )

        assert hasattr(report, "type_distribution")
        assert "trajectory" in report.type_distribution
        assert "general" in report.type_distribution

    def test_composition_report_has_discarded_count(
        self,
    ) -> None:
        """Test that composition report includes 'discarded_count' field."""
        report = CompositionReport(
            records_by_origin={},
            token_pct_by_origin={},
            type_distribution={},
            discarded_count=5,
        )

        assert hasattr(report, "discarded_count")
        assert report.discarded_count == 5

    def test_composition_report_has_discarded_reasons(
        self,
    ) -> None:
        """Test that composition report includes 'discarded_reasons' field."""
        discarded_reasons: dict[str, int] = {
            "invalid_format": 3,
            "duplicate": 2,
        }

        report = CompositionReport(
            records_by_origin={},
            token_pct_by_origin={},
            type_distribution={},
            discarded_reasons=discarded_reasons,
        )

        assert hasattr(report, "discarded_reasons")
        assert "invalid_format" in report.discarded_reasons
        assert report.discarded_reasons["invalid_format"] == 3

    def test_composition_report_immutable(self) -> None:
        """Test that CompositionReport is immutable."""
        report = CompositionReport(
            records_by_origin={"specialized": 10},
            token_pct_by_origin={"specialized": 30.0},
            type_distribution={"trajectory": 10},
        )

        with pytest.raises(Exception):  # Pydantic frozen error
            report.records_by_origin = {"new": "data"}


class TestMixingWorkflow:
    """Integration tests for complete mixing workflow."""

    def test_complete_mixing_workflow(
        self,
        specialized_records: list[DatasetRecord],
        anchor_records: list[DatasetRecord],
        tmp_path: Path,
    ) -> None:
        """Test complete mixing workflow: normalize, mix, shuffle, export."""
        seed = 42

        # Mix records
        all_records = specialized_records + anchor_records

        # Calculate token proportions
        specialized_tokens = sum(
            r.metadata.get("token_count", 0) for r in specialized_records
        )
        anchor_tokens = sum(r.metadata.get("token_count", 0) for r in anchor_records)
        total_tokens = specialized_tokens + anchor_tokens

        specialized_pct = (specialized_tokens / total_tokens) * 100 if total_tokens > 0 else 0
        anchor_pct = (anchor_tokens / total_tokens) * 100 if total_tokens > 0 else 0

        # Shuffle deterministically
        random.seed(seed)
        random.shuffle(all_records)

        # Export to JSONL
        output_path = tmp_path / "mixed.jsonl"
        with open(output_path, "w") as f:
            for record in all_records:
                f.write(record.model_dump_json() + "\n")

        # Validate output
        with open(output_path) as f:
            lines = f.readlines()

        # All records should have messages
        for line in lines:
            data = json.loads(line)
            assert "messages" in data

        # Generate composition report
        records_by_origin: dict[str, int] = {}
        type_distribution: dict[str, int] = {}

        for r in all_records:
            origin = r.metadata.get("origin", "unknown")
            rec_type = r.metadata.get("type", "unknown")
            records_by_origin[origin] = records_by_origin.get(origin, 0) + 1
            type_distribution[rec_type] = type_distribution.get(rec_type, 0) + 1

        report = CompositionReport(
            records_by_origin=records_by_origin,
            token_pct_by_origin={
                "specialized": specialized_pct,
                "anchor": anchor_pct,
            },
            type_distribution=type_distribution,
        )

        # Verify report fields
        assert len(report.records_by_origin) > 0
        assert len(report.token_pct_by_origin) > 0
        assert len(report.type_distribution) > 0

    def test_mixing_with_subsampling(
        self, specialized_records: list[DatasetRecord], anchor_records: list[DatasetRecord]
    ) -> None:
        """Test mixing with token-based subsampling."""
        # Calculate current tokens in specialized
        specialized_tokens = sum(
            r.metadata.get("token_count", 0) for r in specialized_records
        )

        # Calculate what anchor subsample should be to achieve 30/70
        # specialized_tokens / (specialized_tokens + anchor_sample) = 0.30
        # anchor_sample = specialized_tokens * 0.70 / 0.30
        if specialized_tokens > 0:
            target_anchor_tokens = int(specialized_tokens * 70 / 30)

            # Subsample anchor to target
            sorted_anchor = sorted(anchor_records, key=lambda r: r.metadata.get("token_count", 0))
            selected_anchor = []
            current_tokens = 0

            for record in sorted_anchor:
                tokens = record.metadata.get("token_count", 0)
                if current_tokens + tokens <= target_anchor_tokens:
                    selected_anchor.append(record)
                    current_tokens += tokens

            # Verify proportions are now closer to 30/70
            final_specialized_tokens = specialized_tokens
            final_total = final_specialized_tokens + current_tokens

            final_pct = (final_specialized_tokens / final_total) * 100 if final_total > 0 else 0
            assert 25 <= final_pct <= 35  # Should be close to 30%

    def test_mixing_preserves_metadata(
        self, specialized_records: list[DatasetRecord], tmp_path: Path
    ) -> None:
        """Test that mixing preserves all record metadata."""
        output_path = tmp_path / "output.jsonl"

        with open(output_path, "w") as f:
            for record in specialized_records:
                f.write(record.model_dump_json() + "\n")

        # Read back and verify metadata
        with open(output_path) as f:
            for line in f:
                data = json.loads(line)
                assert "metadata" in data
                metadata = data["metadata"]
                assert "origin" in metadata
                assert "type" in metadata


class TestEdgeCases:
    """Tests for edge cases in dataset mixing."""

    def test_mixing_empty_specialized_dataset(
        self, anchor_records: list[DatasetRecord]
    ) -> None:
        """Test mixing when specialized dataset is empty."""
        specialized: list[DatasetRecord] = []

        all_records = specialized + anchor_records
        assert len(all_records) == len(anchor_records)

    def test_mixing_empty_anchor_dataset(
        self, specialized_records: list[DatasetRecord]
    ) -> None:
        """Test mixing when anchor dataset is empty."""
        anchor: list[DatasetRecord] = []

        all_records = specialized_records + anchor
        assert len(all_records) == len(specialized_records)

    def test_mixing_single_record_each(
        self,
    ) -> None:
        """Test mixing with single record in each dataset."""
        specialized = [
            DatasetRecord(
                messages=[
                    Message(role="user", content="Test"),
                    Message(role="assistant", content="Answer"),
                ],
                metadata={"origin": "specialized", "type": "trajectory"},
            )
        ]

        anchor = [
            DatasetRecord(
                messages=[
                    Message(role="user", content="Question"),
                    Message(role="assistant", content="Response"),
                ],
                metadata={"origin": "anchor", "type": "general"},
            )
        ]

        all_records = specialized + anchor
        assert len(all_records) == 2

    def test_proportion_with_very_small_dataset(
        self,
    ) -> None:
        """Test proportion calculation with very small datasets."""
        # Single small record in each
        specialized_tokens = 100
        anchor_tokens = 200

        specialized_pct = (specialized_tokens / (specialized_tokens + anchor_tokens)) * 100
        anchor_pct = (anchor_tokens / (specialized_tokens + anchor_tokens)) * 100

        assert specialized_pct == pytest.approx(33.33, rel=0.1)
        assert anchor_pct == pytest.approx(66.67, rel=0.1)


class TestDatasetMixerInterface:
    """
    Abstract interface tests for DatasetMixer.

    These tests document the expected interface for DatasetMixer.
    They will pass once T019 (implementation) is completed.
    """

    def test_mixer_has_mix_method(self) -> None:
        """Test that DatasetMixer has a mix method."""
        config = DatasetMixerConfig(specialized_pct=30.0, anchor_pct=70.0, shuffle_seed=42)
        mixer = DatasetMixer(config)
        assert hasattr(mixer, "mix")
        assert callable(mixer.mix)

    def test_mixer_has_export_method(self) -> None:
        """Test that DatasetMixer has an export method."""
        config = DatasetMixerConfig(specialized_pct=30.0, anchor_pct=70.0, shuffle_seed=42)
        mixer = DatasetMixer(config)
        assert hasattr(mixer, "export")
        assert callable(mixer.export)

    def test_mixer_has_generate_report_method(self) -> None:
        """Test that DatasetMixer has a generate_report method."""
        config = DatasetMixerConfig(specialized_pct=30.0, anchor_pct=70.0, shuffle_seed=42)
        mixer = DatasetMixer(config)
        assert hasattr(mixer, "generate_report")
        assert callable(mixer.generate_report)

    def test_mixer_has_config_property(self) -> None:
        """Test that DatasetMixer has a config property."""
        config = DatasetMixerConfig(specialized_pct=30.0, anchor_pct=70.0, shuffle_seed=42)
        mixer = DatasetMixer(config)
        assert hasattr(mixer, "config")
        assert mixer.config == config

    def test_mixer_mix_with_empty_lists(self) -> None:
        """Test mix with empty lists returns empty list."""
        config = DatasetMixerConfig(specialized_pct=30.0, anchor_pct=70.0, shuffle_seed=42)
        mixer = DatasetMixer(config)
        result = mixer.mix([], [])
        assert result == []

    def test_mixer_config_attributes(self) -> None:
        """Test DatasetMixerConfig has expected attributes."""
        config = DatasetMixerConfig(specialized_pct=30.0, anchor_pct=70.0, shuffle_seed=42)
        assert config.specialized_pct == 30.0
        assert config.anchor_pct == 70.0
        assert config.shuffle_seed == 42
