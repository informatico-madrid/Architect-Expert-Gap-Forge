#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0
"""Tests for the CLI argument parser and main() behaviour."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from infrastructure.anchor_dataset_builder import build_parser, main


# ---------------------------------------------------------------------------
# 1. --count 50 (default)
# ---------------------------------------------------------------------------


class TestCountDefault:
    def test_default_count_is_50(self):
        parser = build_parser()
        args = parser.parse_args([])
        assert args.count == 50

    def test_explicit_count_50(self):
        parser = build_parser()
        args = parser.parse_args(["--count", "50"])
        assert args.count == 50

    def test_custom_count(self):
        parser = build_parser()
        args = parser.parse_args(["--count", "10"])
        assert args.count == 10


# ---------------------------------------------------------------------------
# 2. --provider
# ---------------------------------------------------------------------------


class TestProvider:
    def test_default_provider(self):
        parser = build_parser()
        args = parser.parse_args([])
        assert args.provider == "vllm"

    def test_provider_openai(self):
        parser = build_parser()
        args = parser.parse_args(["--provider", "openai"])
        assert args.provider == "openai"

    def test_provider_gemini(self):
        parser = build_parser()
        args = parser.parse_args(["--provider", "gemini"])
        assert args.provider == "gemini"

    def test_provider_vllm(self):
        parser = build_parser()
        args = parser.parse_args(["--provider", "vllm"])
        assert args.provider == "vllm"

    def test_invalid_provider_rejected(self):
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--provider", "unknown"])


# ---------------------------------------------------------------------------
# 3. --dry-run writes nothing (to disk)
# ---------------------------------------------------------------------------


class TestDryRunWritesNothing:
    def test_dry_run_exits_0(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """dry-run should exit 0."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        output = main(["--dry-run", "--count", "1", "--output-dir", str(tmp_path)])
        assert output == 0

    def test_dry_run_produces_output(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """dry-run should print planned distribution."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        output = main(["--dry-run", "--count", "50", "--output-dir", str(tmp_path)])
        assert output == 0

    def test_dry_run_no_file_written(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """dry-run must not create any output files."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        main(["--dry-run", "--count", "1", "--output-dir", str(tmp_path)])
        files = list(tmp_path.iterdir())
        assert all(".jsonl" not in f.name for f in files)


# ---------------------------------------------------------------------------
# 4. --no-overwrite exits 1 when file exists
# ---------------------------------------------------------------------------


class TestNoOverwrite:
    def test_no_overwrite_exits_1(self, tmp_path: Path) -> None:
        """If output file exists and --no-overwrite is set, exit code is 1."""
        output_path = tmp_path / "anchor_dataset.jsonl"
        output_path.write_text("existing\n")
        exit_code = main(
            [
                "--count",
                "1",
                "--output-dir",
                str(tmp_path),
                "--no-overwrite",
            ]
        )
        assert exit_code == 1

    def test_no_overwrite_exits_0_when_missing(self, tmp_path: Path) -> None:
        """If output file does not exist, --no-overwrite does not block."""
        exit_code = main(
            [
                "--count",
                "1",
                "--output-dir",
                str(tmp_path),
                "--dry-run",
                "--no-overwrite",
            ]
        )
        assert exit_code == 0


# ---------------------------------------------------------------------------
# 5. --domain-distribution override
# ---------------------------------------------------------------------------


class TestDomainDistribution:
    def test_custom_domain_distribution(self):
        parser = build_parser()
        custom = json.dumps({"custom_domain": 0.5, "other": 0.5})
        args = parser.parse_args(["--domain-distribution", custom])
        assert args.domain_distribution == custom

    def test_custom_distribution_passed_to_config(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        custom = json.dumps({"foo": 0.5, "bar": 0.5})
        main(
            [
                "--dry-run",
                "--count",
                "10",
                "--domain-distribution",
                custom,
                "--output-dir",
                str(tmp_path),
            ]
        )


# ---------------------------------------------------------------------------
# 6. --difficulty-distribution override
# ---------------------------------------------------------------------------


class TestDifficultyDistribution:
    def test_custom_difficulty_distribution(self):
        parser = build_parser()
        custom = json.dumps({"easy": 0.5, "medium": 0.3, "hard": 0.2})
        args = parser.parse_args(["--difficulty-distribution", custom])
        assert args.difficulty_distribution == custom


# ---------------------------------------------------------------------------
# 7. Default values correct
# ---------------------------------------------------------------------------


class TestDefaultValues:
    def test_default_output_dir(self):
        parser = build_parser()
        args = parser.parse_args([])
        assert args.output_dir == "datasets/anchors/v1/"

    def test_default_vllm_url(self):
        parser = build_parser()
        args = parser.parse_args([])
        assert args.vllm_url == "http://localhost:8000"

    def test_default_temperature(self):
        parser = build_parser()
        args = parser.parse_args([])
        assert args.temperature == 0.4

    def test_default_max_tokens(self):
        parser = build_parser()
        args = parser.parse_args([])
        assert args.max_tokens == 8192

    def test_default_seed(self):
        parser = build_parser()
        args = parser.parse_args([])
        assert args.seed == 42

    def test_default_resume_false(self):
        parser = build_parser()
        args = parser.parse_args([])
        assert args.resume is False

    def test_default_no_overwrite_false(self):
        parser = build_parser()
        args = parser.parse_args([])
        assert args.no_overwrite is False

    def test_default_output_file(self):
        parser = build_parser()
        args = parser.parse_args([])
        assert args.output_file == "anchor_dataset.jsonl"

    def test_default_dry_run_false(self):
        parser = build_parser()
        args = parser.parse_args([])
        assert args.dry_run is False

    def test_custom_values_override_defaults(self):
        parser = build_parser()
        args = parser.parse_args(
            [
                "--count",
                "100",
                "--output-dir",
                "/tmp/out",
                "--temperature",
                "0.7",
                "--seed",
                "99",
                "--output-file",
                "custom.jsonl",
            ]
        )
        assert args.count == 100
        assert args.output_dir == "/tmp/out"
        assert args.temperature == 0.7
        assert args.seed == 99
        assert args.output_file == "custom.jsonl"
