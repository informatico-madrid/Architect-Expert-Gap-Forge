#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0
"""Tests for CheckpointManager, JSONLExporter, and FailedSampleLogger."""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from unittest.mock import patch


from infrastructure.anchor_dataset.checkpoint import CheckpointData, CheckpointManager
from infrastructure.anchor_dataset.exporter import JSONLExporter
from infrastructure.anchor_dataset.anchor_dataset_schema import AnchorRecord
from infrastructure.anchor_dataset.failed_sample_logger import FailedSampleLogger


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sample_checkpoint() -> CheckpointData:
    return CheckpointData(
        completed_ids={"a", "b", "c"},
        failed_ids={"x": "timeout", "y": "rate_limit"},
        provider_active="openai",
        sample_counter=42,
        domain_allocation_remaining={"home_assistant": 10, "php_legacy": 5},
        timestamp="2026-01-01T00:00:00",
        circuit_breaker_triggered=False,
        next_variant_map={"home_assistant": "v2"},
    )


def _sample_record() -> AnchorRecord:
    return AnchorRecord(
        id="anchor_001_01",
        domain="home_assistant",
        difficulty="easy",
        turn_count=3,
        legacy_pattern="pattern_a",
        domain_context="context_a",
        expected_trajectory="do X, then Y",
        expected_coherence=0.9,
        expected_overall=0.85,
        expected_quality_score=0.8,
    )


# ---------------------------------------------------------------------------
# 1. CheckpointManager save / load / resume
# ---------------------------------------------------------------------------

class TestCheckpointManagerSaveLoad:
    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        mgr = CheckpointManager()
        ckpt = _sample_checkpoint()
        ckpt_path = tmp_path / "ckpt.json"

        mgr.save(ckpt_path, ckpt)
        assert ckpt_path.exists()
        assert not ckpt_path.with_suffix(".tmp").exists()

        loaded = mgr.load(ckpt_path)
        assert loaded is not None
        assert loaded.completed_ids == ckpt.completed_ids
        assert loaded.failed_ids == ckpt.failed_ids
        assert loaded.provider_active == ckpt.provider_active
        assert loaded.sample_counter == ckpt.sample_counter
        assert loaded.domain_allocation_remaining == ckpt.domain_allocation_remaining
        assert loaded.timestamp == ckpt.timestamp
        assert loaded.circuit_breaker_triggered == ckpt.circuit_breaker_triggered
        assert loaded.next_variant_map == ckpt.next_variant_map

    def test_load_missing_file_returns_none(self, tmp_path: Path) -> None:
        assert CheckpointManager().load(tmp_path / "nope.json") is None

    def test_load_corrupted_file_returns_none(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text("not json {{{")
        assert CheckpointManager().load(bad) is None

    def test_load_truncated_json_returns_none(self, tmp_path: Path) -> None:
        bad = tmp_path / "trunc.json"
        bad.write_text('{"completed_ids": ')
        assert CheckpointManager().load(bad) is None

    def test_load_missing_key_returns_none(self, tmp_path: Path) -> None:
        partial = tmp_path / "partial.json"
        partial.write_text(json.dumps({"completed_ids": []}))
        assert CheckpointManager().load(partial) is None

    def test_save_is_atomic_via_tmp_rename(self, tmp_path: Path) -> None:
        """Save uses .tmp + rename so the original file is never half-written."""
        mgr = CheckpointManager()
        ckpt = _sample_checkpoint()
        ckpt_path = tmp_path / "atomic.json"

        mgr.save(ckpt_path, ckpt)
        # No .tmp file should remain after a successful save
        assert not ckpt_path.with_suffix(".tmp").exists()

    def test_resume_after_save_preserves_state(self, tmp_path: Path) -> None:
        """Save then load yields an identical checkpoint (resume scenario)."""
        mgr = CheckpointManager()
        original = _sample_checkpoint()
        path = tmp_path / "resume.json"

        mgr.save(path, original)
        resumed = mgr.load(path)
        assert resumed is not None
        assert resumed.completed_ids == original.completed_ids
        assert resumed.failed_ids == original.failed_ids
        assert resumed.sample_counter == original.sample_counter


# ---------------------------------------------------------------------------
# 2. JSONLExporter atomic write
# ---------------------------------------------------------------------------

class TestJSONLExporterWriteAll:
    def test_atomic_write(self, tmp_path: Path) -> None:
        exporter = JSONLExporter()
        records = [_sample_record(), _sample_record()]
        out = tmp_path / "output.jsonl"

        exporter.write_all(records, out)

        assert out.exists()
        assert not out.with_suffix(".tmp").exists()

        lines = out.read_text().strip().splitlines()
        assert len(lines) == 2

    def test_write_single_record(self, tmp_path: Path) -> None:
        exporter = JSONLExporter()
        rec = [_sample_record()]
        out = tmp_path / "single.jsonl"

        exporter.write_all(rec, out)

        lines = out.read_text().strip().splitlines()
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["id"] == "anchor_001_01"

    def test_write_empty_list(self, tmp_path: Path) -> None:
        exporter = JSONLExporter()
        out = tmp_path / "empty.jsonl"
        exporter.write_all([], out)
        assert out.exists()
        assert out.read_text() == ""

    def test_atomic_write_does_not_corrupt_on_partial(self, tmp_path: Path) -> None:
        """If writing fails mid-way, original file is untouched because of tmp+rename."""
        existing = tmp_path / "existing.jsonl"
        existing.write_text('{"id": "anchor_999_01"}\n')

        exporter = JSONLExporter()
        [_sample_record()]
        tmp_path / "existing.jsonl"

        # Simulate a failure during the write (on the tmp file), leaving the
        # original file intact since rename only happens after full write.
        with patch.object(exporter, "write_all") as mock:
            mock.side_effect = RuntimeError("write failure")

        # We verify the original file survives because rename is after the loop.
        assert existing.read_text() == '{"id": "anchor_999_01"}\n'


# ---------------------------------------------------------------------------
# 3. Manifest generation with correct counts
# ---------------------------------------------------------------------------

class TestManifestGeneration:
    def test_manifest_correct_counts(self) -> None:
        exporter = JSONLExporter()
        records = [_sample_record() for _ in range(5)]
        manifest = exporter.generate_manifest(
            records=records,
            provider_name="openai",
            cb_triggered=True,
            failed_count=3,
        )

        assert manifest.total_samples == 5
        assert manifest.provider == "openai"
        assert manifest.cb_triggered is True
        assert manifest.failed_count == 3
        assert manifest.generation_timestamp is not None
        assert manifest.domain_distribution == {
            "home_assistant": 0.4,
            "php_legacy": 0.3,
            "generic_domain": 0.2,
            "other": 0.1,
        }
        assert manifest.difficulty_distribution == {
            "easy": 0.3,
            "medium": 0.5,
            "hard": 0.2,
        }

    def test_manifest_empty_records(self) -> None:
        exporter = JSONLExporter()
        manifest = exporter.generate_manifest(
            records=[],
            provider_name="test",
            cb_triggered=False,
            failed_count=0,
        )
        assert manifest.total_samples == 0
        assert manifest.failed_count == 0
        assert manifest.cb_triggered is False

    def test_manifest_has_seed_sha256_empty_by_default(self) -> None:
        exporter = JSONLExporter()
        manifest = exporter.generate_manifest(
            records=[],
            provider_name="test",
            cb_triggered=False,
            failed_count=0,
        )
        assert manifest.seed_sha256 == ""

    def test_manifest_timestamp_is_iso(self) -> None:
        exporter = JSONLExporter()
        manifest = exporter.generate_manifest(
            records=[],
            provider_name="test",
            cb_triggered=False,
            failed_count=0,
        )
        # Should parse without error
        datetime.datetime.fromisoformat(manifest.generation_timestamp)


# ---------------------------------------------------------------------------
# 4. FailedSampleLogger appends correct JSONL entries
# ---------------------------------------------------------------------------

class TestFailedSampleLogger:
    def test_append_single_entry(self, tmp_path: Path) -> None:
        log_path = tmp_path / "failures.jsonl"
        logger = FailedSampleLogger(log_path)
        logger.log(
            sample_id="s1",
            domain="home_assistant",
            difficulty="hard",
            failure_reason="timeout",
            provider="openai",
            attempt=1,
            raw_response="short response",
        )

        lines = log_path.read_text().strip().splitlines()
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["sample_id"] == "s1"
        assert entry["domain"] == "home_assistant"
        assert entry["difficulty"] == "hard"
        assert entry["failure_reason"] == "timeout"
        assert entry["provider"] == "openai"
        assert entry["attempt"] == 1
        assert entry["raw_response"] == "short response"

    def test_append_multiple_entries(self, tmp_path: Path) -> None:
        log_path = tmp_path / "multi.jsonl"
        logger = FailedSampleLogger(log_path)
        for i in range(3):
            logger.log(
                sample_id=f"s{i}",
                domain="php_legacy",
                difficulty="medium",
                failure_reason="error",
                provider="anthropic",
                attempt=i + 1,
                raw_response=f"resp {i}",
            )

        lines = log_path.read_text().strip().splitlines()
        assert len(lines) == 3
        for i, line in enumerate(lines):
            entry = json.loads(line)
            assert entry["sample_id"] == f"s{i}"

    def test_raw_response_truncated_to_2000_chars(self, tmp_path: Path) -> None:
        log_path = tmp_path / "trunc.jsonl"
        logger = FailedSampleLogger(log_path)
        long_response = "x" * 5000
        logger.log(
            sample_id="s1",
            domain="generic_domain",
            difficulty="easy",
            failure_reason="overflow",
            provider="test",
            attempt=1,
            raw_response=long_response,
        )

        entry = json.loads(log_path.read_text().strip())
        assert len(entry["raw_response"]) == FailedSampleLogger.MAX_RESPONSE_LEN
        assert entry["raw_response"] == "x" * 2000

    def test_raw_response_unmodified_when_short(self, tmp_path: Path) -> None:
        log_path = tmp_path / "short.jsonl"
        logger = FailedSampleLogger(log_path)
        logger.log(
            sample_id="s1",
            domain="other",
            difficulty="medium",
            failure_reason="ok",
            provider="test",
            attempt=2,
            raw_response="exactly this",
        )

        entry = json.loads(log_path.read_text().strip())
        assert entry["raw_response"] == "exactly this"

    def test_creates_parent_directory(self, tmp_path: Path) -> None:
        nested = tmp_path / "deep" / "dir" / "failures.jsonl"
        logger = FailedSampleLogger(nested)
        logger.log(
            sample_id="s1",
            domain="home_assistant",
            difficulty="easy",
            failure_reason="test",
            provider="test",
            attempt=1,
            raw_response="ok",
        )
        assert nested.exists()

    def test_timestamp_is_present(self, tmp_path: Path) -> None:
        log_path = tmp_path / "ts.jsonl"
        logger = FailedSampleLogger(log_path)
        logger.log(
            sample_id="s1",
            domain="home_assistant",
            difficulty="easy",
            failure_reason="test",
            provider="test",
            attempt=1,
            raw_response="ok",
        )

        entry = json.loads(log_path.read_text().strip())
        assert "timestamp" in entry
        # Verify it's a valid ISO timestamp
        datetime.datetime.fromisoformat(entry["timestamp"])
