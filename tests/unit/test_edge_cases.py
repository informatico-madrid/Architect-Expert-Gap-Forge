#!/usr/bin/env python3
# Copyright 2026 Bunker AI
# SPDX-License-Identifier: Apache-2.0
# -*- coding: utf-8 -*-
"""
Edge case tests — defensive coding verification.

Tests:
1. 0 seeds for generic_domain → template generation produces valid samples
2. Very long trajectory (>10000 chars) not truncated
3. Malformed API responses handled gracefully
4. Empty seed file handled gracefully
5. KeyboardInterrupt saves checkpoint and exits 1

SPDX-License-Identifier: Apache-2.0
Copyright 2026 AEGF
"""

from __future__ import annotations

import datetime
import json
import os
import signal
import sys
from pathlib import Path
from unittest import mock

import pytest
import yaml

from infrastructure.anchor_dataset.anchor_dataset_schema import AnchorRecord
from infrastructure.anchor_dataset.anchor_providers import VLLMProvider
from infrastructure.anchor_dataset.checkpoint import CheckpointData, CheckpointManager
from infrastructure.anchor_dataset.seed_loader import load_seeds
from infrastructure.anchor_dataset.sample_generator import (
    PromptBuilder,
    SampleConfig,
    SampleConfigGenerator,
)


# ---------------------------------------------------------------------------
# 1. Zero seeds — generic_domain template generation
# ---------------------------------------------------------------------------


class TestZeroSeedsGenericDomain:
    """When no seeds are provided, generation and prompting still work."""

    def test_generator_produces_configs_with_empty_seeds(self):
        """SampleConfigGenerator with empty seeds still produces configs."""
        gen = SampleConfigGenerator(seeds=[])
        configs = gen.generate_configs(10)
        assert len(configs) == 10
        # All configs should be valid SampleConfig instances
        for cfg in configs:
            assert isinstance(cfg, SampleConfig)
            assert cfg.domain in ("home_assistant", "php_legacy", "generic_domain", "other")
            assert cfg.difficulty in ("easy", "medium", "hard")
            assert isinstance(cfg.turn_count, int)
            assert cfg.turn_count >= 1

    def test_generic_domain_configs_have_valid_fields(self):
        """generic_domain configs from empty seeds have all fields populated."""
        gen = SampleConfigGenerator(seeds=[])
        configs = gen.generate_configs(20)
        generic = [c for c in configs if c.domain == "generic_domain"]
        assert len(generic) > 0
        for cfg in generic:
            assert cfg.sample_id.startswith("anchor_")
            assert cfg.domain == "generic_domain"

    def test_prompt_builder_handles_empty_seeds(self):
        """PromptBuilder.build() with zero seeds produces valid prompts."""
        builder = PromptBuilder(seeds=[])
        cfg = SampleConfig(
            sample_id="anchor_001_00",
            domain="generic_domain",
            difficulty="easy",
            turn_count=3,
        )
        system, user = builder.build(cfg)
        assert isinstance(system, str)
        assert isinstance(user, str)
        assert len(system) > 0
        assert len(user) > 0
        # Template variables are filled with defaults
        assert "domain: generic_domain" in system.lower() or "DOMAIN: generic_domain" in system
        assert "turn_count: 3" in user or "Turn count: 3" in user

    def test_prompt_builder_default_category_and_complexity(self):
        """With no seeds, fallback category=general and complexity=nominal."""
        builder = PromptBuilder(seeds=[])
        cfg = SampleConfig(
            sample_id="anchor_001_01",
            domain="other",
            difficulty="hard",
            turn_count=5,
        )
        system, _ = builder.build(cfg)
        assert "category: general" in system.lower() or "CATEGORY: general" in system
        assert "complexity: nominal" in system.lower() or "COMPLEXITY: nominal" in system


# ---------------------------------------------------------------------------
# 2. Very long trajectory — not truncated
# ---------------------------------------------------------------------------


class TestLongTrajectoryNotTruncated:
    """Trajectories exceeding 10000 characters should pass validation."""

    def _long_trajectory(self, length: int = 15000) -> str:
        """Build a trajectory of approximately *length* chars."""
        base = "[ROLE:user]\nDo this step.\n\n[ROLE:assistant]\nI will do it.\n\n"
        repeat = (length // len(base)) + 2
        traj = base * repeat
        return traj[:length]  # Exact target length

    def test_long_trajectory_passes_schema_validation(self):
        """AnchorRecord accepts expected_trajectory >10000 chars."""
        traj = self._long_trajectory(15000)
        record = AnchorRecord(
            id="anchor_001_00",
            domain="home_assistant",
            difficulty="easy",
            turn_count=3,
            legacy_pattern="pattern",
            domain_context="context",
            expected_trajectory=traj,
            expected_coherence=0.9,
            expected_overall=0.85,
            expected_quality_score=0.8,
        )
        assert len(record.expected_trajectory) == len(traj)

    def test_10000_char_trajectory(self):
        """Exactly 10000 chars should pass."""
        traj = self._long_trajectory(10000)
        record = AnchorRecord(
            id="anchor_001_01",
            domain="php_legacy",
            difficulty="medium",
            turn_count=4,
            legacy_pattern="p",
            domain_context="c",
            expected_trajectory=traj,
            expected_coherence=0.8,
            expected_overall=0.8,
            expected_quality_score=0.8,
        )
        assert len(record.expected_trajectory) == 10000

    def test_20000_char_trajectory(self):
        """20000+ chars should also pass (no upper bound on schema)."""
        traj = self._long_trajectory(20000)
        record = AnchorRecord(
            id="anchor_001_02",
            domain="generic_domain",
            difficulty="hard",
            turn_count=5,
            legacy_pattern="p",
            domain_context="c",
            expected_trajectory=traj,
            expected_coherence=0.7,
            expected_overall=0.7,
            expected_quality_score=0.7,
        )
        assert len(record.expected_trajectory) == 20000


# ---------------------------------------------------------------------------
# 3. Malformed API responses — graceful handling
# ---------------------------------------------------------------------------


def _make_mock_response(json_body: dict) -> mock.Mock:
    """Build a mock requests.Response for provider tests."""
    resp = mock.Mock()
    resp.json.return_value = json_body
    resp.raise_for_status = mock.Mock()
    return resp


class TestMalformedAPIResponses:
    """VLLMProvider handles various malformed responses without raising."""

    def test_empty_choices_list(self):
        """Response with no choices returns None."""
        provider = VLLMProvider()
        mock_resp = _make_mock_response({"choices": []})
        with mock.patch("requests.post", return_value=mock_resp):
            result = provider.generate("sys", "user")
        assert result is None

    def test_choice_missing_message_key(self):
        """choices[0] has no 'message' key returns None."""
        provider = VLLMProvider()
        mock_resp = _make_mock_response({"choices": [{"not_message": "data"}]})
        with mock.patch("requests.post", return_value=mock_resp):
            result = provider.generate("sys", "user")
        assert result is None

    def test_message_missing_content_key(self):
        """message has no 'content' key returns None."""
        provider = VLLMProvider()
        mock_resp = _make_mock_response({"choices": [{"message": {"not_content": "x"}}]})
        with mock.patch("requests.post", return_value=mock_resp):
            result = provider.generate("sys", "user")
        assert result is None

    def test_content_is_not_json(self):
        """Message content is plain text, not JSON — returns None."""
        provider = VLLMProvider()
        mock_resp = _make_mock_response(
            {"choices": [{"message": {"content": "just text, not json at all"}}],}
        )
        with mock.patch("requests.post", return_value=mock_resp):
            result = provider.generate("sys", "user")
        assert result is None

    def test_content_is_invalid_json(self):
        """Message content is malformed JSON — returns None."""
        provider = VLLMProvider()
        mock_resp = _make_mock_response(
            {"choices": [{"message": {"content": "{invalid json:::"}}],}
        )
        with mock.patch("requests.post", return_value=mock_resp):
            result = provider.generate("sys", "user")
        assert result is None

    def test_response_body_missing_choices_key(self):
        """Response body has no 'choices' key at all."""
        provider = VLLMProvider()
        mock_resp = _make_mock_response({"status": "ok", "data": "nothing useful"})
        with mock.patch("requests.post", return_value=mock_resp):
            result = provider.generate("sys", "user")
        assert result is None

    def test_anchorecord_validation_fails(self):
        """Valid JSON but invalid AnchorRecord fields returns None."""
        provider = VLLMProvider()
        bad_record = {"id": "bad_id", "domain": "invalid", "difficulty": "easy"}
        mock_resp = _make_mock_response(
            {"choices": [{"message": {"content": json.dumps(bad_record)}}]}
        )
        with mock.patch("requests.post", return_value=mock_resp):
            result = provider.generate("sys", "user")
        assert result is None

    def test_response_500_error(self):
        """HTTP 500 error is captured and returns None."""
        provider = VLLMProvider()
        mock_resp = mock.Mock()
        mock_resp.raise_for_status.side_effect = Exception("500 Internal Server Error")
        with mock.patch("requests.post", return_value=mock_resp):
            result = provider.generate("sys", "user")
        assert result is None

    def test_all_retries_exhausted_on_connection_error(self):
        """Connection error exhausts retries and returns None."""
        import requests as req

        provider = VLLMProvider()
        with mock.patch(
            "requests.post",
            side_effect=req.exceptions.ConnectionError("Connection refused"),
        ) as post_fn:
            result = provider.generate("sys", "user")
        assert post_fn.call_count == provider.MAX_RETRIES
        assert result is None

    def test_all_retries_exhausted_on_timeout(self):
        """Timeout exhausts retries and returns None."""
        import requests as req

        provider = VLLMProvider()
        with mock.patch(
            "requests.post",
            side_effect=req.exceptions.Timeout("timed out"),
        ) as post_fn:
            result = provider.generate("sys", "user")
        assert post_fn.call_count == provider.MAX_RETRIES
        assert result is None


# ---------------------------------------------------------------------------
# 4. Empty seed file — graceful handling
# ---------------------------------------------------------------------------


class TestEmptySeedFile:
    """Seed loading handles empty and edge-case YAML files."""

    def test_empty_yaml_file_returns_empty_list(self, tmp_path: Path) -> None:
        """A YAML file with only whitespace returns []."""
        empty_file = tmp_path / "empty.yaml"
        empty_file.write_text("   \n\n  \n")
        result = load_seeds(seed_file=empty_file)
        assert result == []

    def test_null_yaml_file_returns_empty_list(self, tmp_path: Path) -> None:
        """A YAML file with only 'null' returns []."""
        null_file = tmp_path / "null.yaml"
        null_file.write_text("null\n")
        result = load_seeds(seed_file=null_file)
        assert result == []

    def test_yaml_with_empty_seeds_list(self, tmp_path: Path) -> None:
        """YAML with 'seeds: []' returns []."""
        file = tmp_path / "empty_seeds.yaml"
        file.write_text("seeds: []\n")
        result = load_seeds(seed_file=file)
        assert result == []

    def test_yaml_with_seeds_key_only(self, tmp_path: Path) -> None:
        """YAML with only 'seeds' key (no list items) returns []."""
        file = tmp_path / "seeds_only.yaml"
        file.write_text("seeds:\n")
        result = load_seeds(seed_file=file)
        assert result == []

    def test_yaml_with_whitespace_only_seeds(self, tmp_path: Path) -> None:
        """seeds key with only whitespace returns []."""
        file = tmp_path / "ws_seeds.yaml"
        file.write_text("seeds:   \n")
        result = load_seeds(seed_file=file)
        assert result == []

    def test_load_seeds_logs_info_on_missing_file(self, caplog) -> None:
        """Missing seed file logs INFO message."""
        import logging

        with caplog.at_level(logging.INFO):
            load_seeds(seed_file=Path("/nonexistent/path/seeds.yaml"))
        assert any("not found" in record.message.lower() for record in caplog.records)


# ---------------------------------------------------------------------------
# 5. KeyboardInterrupt — saves checkpoint and exits 1
# ---------------------------------------------------------------------------


class TestKeyboardInterruptCheckpoint:
    """KeyboardInterrupt during generation saves checkpoint and returns exit 1."""

    def test_keyboard_interrupt_saves_checkpoint_exits_1(self, tmp_path: Path) -> None:
        """When provider raises KeyboardInterrupt mid-loop, checkpoint is saved and main returns 1."""
        from infrastructure.anchor_dataset_builder import main

        output_file = tmp_path / "anchor_dataset.jsonl"
        output_dir = str(tmp_path)

        # Build a minimal seed fixture so the builder can load seeds
        seed_fixture = tmp_path / "seeds.yaml"
        seed_fixture.write_text(
            yaml.dump({
                "seeds": [
                    {
                        "seed_id": "test_001",
                        "category": "test",
                        "complexity": "nominal_easy",
                        "context": "test context",
                        "question": "test question",
                        "expected_patterns": ["pattern1"],
                    },
                ],
            })
        )

        # Create a test provider that raises KeyboardInterrupt after 2 successful calls
        call_count = {"n": 0}

        class TestProvider:
            """Provider that returns records then raises KeyboardInterrupt."""

            @property
            def name(self) -> str:
                return "test_provider"

            def generate(self, system_prompt: str, user_prompt: str, timeout: float = 30.0):
                call_count["n"] += 1
                if call_count["n"] <= 2:
                    return AnchorRecord(
                        id=f"anchor_001_{call_count['n']:02d}",
                        domain="home_assistant",
                        difficulty="easy",
                        turn_count=3,
                        legacy_pattern="test",
                        domain_context="test",
                        expected_trajectory="step 1\nstep 2\nstep 3\nstep 4",
                        expected_coherence=0.9,
                        expected_overall=0.85,
                        expected_quality_score=0.8,
                    )
                raise KeyboardInterrupt("test interrupt")

        with mock.patch(
            "infrastructure.anchor_dataset.anchor_providers.get_provider",
            return_value=TestProvider(),
        ):
            exit_code = main([
                "--count", "10",
                "--output-dir", output_dir,
                "--output-file", "anchor_dataset.jsonl",
                "--seed", "42",
            ])

        assert exit_code == 1

        # Verify checkpoint was saved
        cp_files = list(tmp_path.glob(".checkpoint_anchor_dataset*.json"))
        assert len(cp_files) > 0
        cp_file = cp_files[0]
        with open(cp_file) as f:
            cp_data = json.load(f)

        # Checkpoint should reflect the 2 successful completions
        assert "completed_ids" in cp_data
        assert "failed_ids" in cp_data
        assert "sample_counter" in cp_data
        assert cp_data["sample_counter"] == 2

        # The checkpoint file path should contain expected markers
        assert "checkpoint" in cp_file.name

    def test_keyboard_interrupt_without_checkpoint_data_exits_1(self, tmp_path: Path) -> None:
        """Even if no checkpoint data was created (interrupt at idx=0), exit is 1."""
        from infrastructure.anchor_dataset_builder import main

        output_dir = str(tmp_path)

        seed_fixture = tmp_path / "seeds.yaml"
        seed_fixture.write_text(
            yaml.dump({
                "seeds": [
                    {
                        "seed_id": "t001",
                        "category": "test",
                        "complexity": "nominal_easy",
                        "context": "ctx",
                        "question": "q",
                        "expected_patterns": ["p"],
                    },
                ],
            })
        )

        class InstantInterruptProvider:
            """Provider that raises KeyboardInterrupt immediately."""

            @property
            def name(self) -> str:
                return "instant"

            def generate(self, system_prompt: str, user_prompt: str, timeout: float = 30.0):
                raise KeyboardInterrupt("immediate interrupt")

        with mock.patch(
            "infrastructure.anchor_dataset.anchor_providers.get_provider",
            return_value=InstantInterruptProvider(),
        ):
            exit_code = main([
                "--count", "5",
                "--output-dir", output_dir,
                "--output-file", "anchor_dataset.jsonl",
                "--seed", "42",
            ])

        assert exit_code == 1
