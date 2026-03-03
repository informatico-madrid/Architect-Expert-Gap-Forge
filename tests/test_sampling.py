#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the stratified_sample() function in src/audit/sampling.py.

Covers:
- Total sample count equals requested sample_size
- Each example_type present in the input is represented
- Sample is bounded by available records per type (no over-sampling)
- Determinism: same seed → same sample
- Reproducibility across calls with same inputs
- Edge: sample_size == 0 → empty list
- Edge: sample_size > total records → bounded by available records
- Edge: single type in dataset → all quota goes to that type
- Edge: sample_size == 1 → exactly one record returned
- SampleRecord fields are correctly populated from raw dict
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

from src.audit.sampling import stratified_sample
from src.audit.schema import EXAMPLE_TYPES, SampleRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_raw(
    type_counts: Dict[str, int],
    base_ldi: float = 0.7,
) -> List[Dict[str, Any]]:
    """Build a raw-records list with the given number of records per type."""
    records: List[Dict[str, Any]] = []
    for et, count in type_counts.items():
        for j in range(count):
            records.append(
                {
                    "id": f"{et}-{j:03d}",
                    "metadata": {
                        "example_type": et,
                        "evol_difficulty": "medium",
                        "fragment_name": f"frag_{j}",
                        "source_file": f"components/{et}/{j}.py",
                        "gold_injected": True,
                        "ldi": base_ldi + j * 0.01,
                        "ha_standards": "Use entry.runtime_data.",
                        "gap_analysis": "Legacy pattern detected.",
                    },
                    "conversation": [
                        {"role": "user", "content": f"Implement {et} sensor {j}."},
                        {
                            "role": "assistant",
                            "content": f"<think>OK</think>\n```python\npass\n```",
                        },
                    ],
                }
            )
    return records


# ---------------------------------------------------------------------------
# Basic correctness
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestStratifiedSampleBasic:
    def test_returns_list_of_sample_records(self, raw_records: List[Dict[str, Any]]) -> None:
        samples = stratified_sample(raw_records, sample_size=4)
        assert isinstance(samples, list)
        assert all(isinstance(s, SampleRecord) for s in samples)

    def test_sample_size_respected(self, raw_records: List[Dict[str, Any]]) -> None:
        """Total returned records must equal the requested sample_size."""
        samples = stratified_sample(raw_records, sample_size=8)
        assert len(samples) == 8

    def test_all_requested_types_represented(
        self, raw_records: List[Dict[str, Any]]
    ) -> None:
        """Every example_type present in the input must appear in the sample."""
        samples = stratified_sample(raw_records, sample_size=4, seed=42)
        returned_types = {s.example_type for s in samples}
        input_types = {
            r["metadata"]["example_type"]
            for r in raw_records
            if r.get("metadata", {}).get("example_type")
        }
        assert returned_types == input_types

    def test_no_over_sampling_per_type(self, raw_records: List[Dict[str, Any]]) -> None:
        """Never return more records of a type than the available pool."""
        type_counts: Dict[str, int] = {}
        for r in raw_records:
            et = r["metadata"]["example_type"]
            type_counts[et] = type_counts.get(et, 0) + 1

        samples = stratified_sample(raw_records, sample_size=100, seed=42)
        sampled_counts: Dict[str, int] = {}
        for s in samples:
            sampled_counts[s.example_type] = sampled_counts.get(s.example_type, 0) + 1

        for et, count in sampled_counts.items():
            assert count <= type_counts[et], (
                f"Over-sampled type '{et}': got {count}, only {type_counts[et]} available"
            )


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestStratifiedSampleDeterminism:
    def test_same_seed_same_result(self, raw_records: List[Dict[str, Any]]) -> None:
        a = stratified_sample(raw_records, sample_size=8, seed=42)
        b = stratified_sample(raw_records, sample_size=8, seed=42)
        assert [s.id for s in a] == [s.id for s in b]

    def test_different_seeds_different_results(
        self, raw_records: List[Dict[str, Any]]
    ) -> None:
        a = stratified_sample(raw_records, sample_size=8, seed=1)
        b = stratified_sample(raw_records, sample_size=8, seed=9999)
        # Different seeds are very unlikely to produce identical ordering on 16-record pool
        assert [s.id for s in a] != [s.id for s in b]

    def test_result_does_not_mutate_input(self, raw_records: List[Dict[str, Any]]) -> None:
        import copy
        original = copy.deepcopy(raw_records)
        stratified_sample(raw_records, sample_size=8)
        assert [r["id"] for r in raw_records] == [r["id"] for r in original]


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestStratifiedSampleEdgeCases:
    def test_sample_size_zero_returns_empty_list(
        self, raw_records: List[Dict[str, Any]]
    ) -> None:
        samples = stratified_sample(raw_records, sample_size=0)
        assert samples == []

    def test_sample_size_one_returns_exactly_one_record(
        self, raw_records: List[Dict[str, Any]]
    ) -> None:
        samples = stratified_sample(raw_records, sample_size=1)
        assert len(samples) == 1

    def test_sample_size_larger_than_pool_bounded_by_total_records(self) -> None:
        """When sample_size > total records, return all available records."""
        small_pool = _make_raw({"nominal": 2, "contrast": 1})
        samples = stratified_sample(small_pool, sample_size=100)
        assert len(samples) <= 3

    def test_single_type_gets_all_quota(self) -> None:
        records = _make_raw({"nominal": 10})
        samples = stratified_sample(records, sample_size=5)
        assert len(samples) == 5
        assert all(s.example_type == "nominal" for s in samples)

    def test_unbalanced_pool_fills_from_large_buckets(self) -> None:
        """When some types have few records, surplus quota fills from larger buckets."""
        records = _make_raw({"nominal": 10, "contrast": 1, "error_recovery": 1, "theory": 1})
        samples = stratified_sample(records, sample_size=8, seed=42)
        assert len(samples) == 8

    def test_empty_records_returns_empty_list(self) -> None:
        samples = stratified_sample([], sample_size=5)
        assert samples == []


# ---------------------------------------------------------------------------
# SampleRecord field population
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestStratifiedSampleFieldPopulation:
    def test_id_populated(self, raw_records: List[Dict[str, Any]]) -> None:
        samples = stratified_sample(raw_records, sample_size=4)
        assert all(s.id for s in samples)

    def test_example_type_populated(self, raw_records: List[Dict[str, Any]]) -> None:
        samples = stratified_sample(raw_records, sample_size=4)
        assert all(s.example_type for s in samples)

    def test_user_prompt_extracted_from_conversation(
        self, raw_records: List[Dict[str, Any]]
    ) -> None:
        samples = stratified_sample(raw_records, sample_size=4)
        assert all(s.user_prompt for s in samples)

    def test_reference_response_extracted_from_conversation(
        self, raw_records: List[Dict[str, Any]]
    ) -> None:
        samples = stratified_sample(raw_records, sample_size=4)
        assert all(s.reference_response for s in samples)

    def test_ldi_populated(self, raw_records: List[Dict[str, Any]]) -> None:
        samples = stratified_sample(raw_records, sample_size=4)
        assert all(isinstance(s.ldi, float) for s in samples)

    def test_gold_injected_is_bool(self, raw_records: List[Dict[str, Any]]) -> None:
        samples = stratified_sample(raw_records, sample_size=4)
        assert all(isinstance(s.gold_injected, bool) for s in samples)

    def test_missing_id_gets_fallback(self) -> None:
        records = _make_raw({"nominal": 2})
        for r in records:
            del r["id"]  # Remove id to trigger fallback
        samples = stratified_sample(records, sample_size=2)
        assert all(s.id for s in samples)  # fallback id must be non-empty

    def test_missing_metadata_fields_use_defaults(self) -> None:
        records: List[Dict[str, Any]] = [
            {
                "id": "bare-001",
                "metadata": {"example_type": "nominal"},  # minimal metadata
                "conversation": [
                    {"role": "user", "content": "Q"},
                    {"role": "assistant", "content": "<think>ok</think>\nA"},
                ],
            }
        ]
        samples = stratified_sample(records, sample_size=1)
        assert len(samples) == 1
        s = samples[0]
        assert s.evol_difficulty == "unknown"
        assert s.fragment_name == ""
        assert s.ldi == 0.0


# ---------------------------------------------------------------------------
# load_dataset
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLoadDataset:
    def test_loads_valid_jsonl(self, tmp_path: Path) -> None:
        from src.audit.sampling import load_dataset

        jsonl = tmp_path / "data.jsonl"
        lines = [{"id": f"r-{i}", "metadata": {}} for i in range(5)]
        jsonl.write_text("\n".join(__import__("json").dumps(r) for r in lines))
        records = load_dataset(str(jsonl))
        assert len(records) == 5
        assert records[0]["id"] == "r-0"

    def test_skips_malformed_lines(self, tmp_path: Path) -> None:
        from src.audit.sampling import load_dataset

        jsonl = tmp_path / "data.jsonl"
        jsonl.write_text('{"id": "ok"}\nnot-json\n{"id": "also-ok"}\n')
        records = load_dataset(str(jsonl))
        assert len(records) == 2
        assert records[1]["id"] == "also-ok"

    def test_skips_blank_lines(self, tmp_path: Path) -> None:
        from src.audit.sampling import load_dataset

        jsonl = tmp_path / "data.jsonl"
        jsonl.write_text('{"id": "x"}\n\n\n{"id": "y"}\n')
        records = load_dataset(str(jsonl))
        assert len(records) == 2

    def test_empty_file_returns_empty_list(self, tmp_path: Path) -> None:
        from src.audit.sampling import load_dataset

        jsonl = tmp_path / "empty.jsonl"
        jsonl.write_text("")
        records = load_dataset(str(jsonl))
        assert records == []


# ---------------------------------------------------------------------------
# Conversation parsing edge cases
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestConvParsing:
    def test_empty_content_turns_are_skipped(self) -> None:
        """Conversation turns with empty/null content must not be assigned to user/asst."""
        records = [
            {
                "id": "edge-empty-content",
                "metadata": {"example_type": "nominal"},
                "conversation": [
                    {"role": "user", "content": ""},          # empty — skipped
                    {"role": "user", "content": "Real question"},
                    {"role": "assistant", "content": "Real answer"},
                ],
            }
        ]
        samples = stratified_sample(records, sample_size=1)
        assert len(samples) == 1
        assert samples[0].user_prompt == "Real question"
        assert samples[0].reference_response == "Real answer"
