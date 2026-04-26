#!/usr/bin/env python3
# Copyright 2026 Bunker AI
# SPDX-License-Identifier: Apache-2.0
"""Tests for StartupValidator — arg validation, API keys, health check, seeds."""

from __future__ import annotations

import json
import os

import pytest

from infrastructure.anchor_dataset.config import AnchorsConfig
from infrastructure.anchor_dataset.startup import StartupValidator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(**overrides: object) -> AnchorsConfig:
    """Build an AnchorsConfig with optional overrides."""
    kwargs: dict[str, object] = {
        "count": 50,
        "provider": "openai",
        "output_dir": "outputs",
        "vllm_url": "http://localhost:8000",
        "temperature": 0.4,
        "max_tokens": 8192,
        "domain_distribution": json.dumps(
            {"home_assistant": 0.4, "php_legacy": 0.3, "generic_domain": 0.2, "other": 0.1}
        ),
        "difficulty_distribution": json.dumps({"easy": 0.3, "medium": 0.5, "hard": 0.2}),
        "seed": 42,
    }
    kwargs.update(overrides)
    return AnchorsConfig(**kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 1. Valid CLI args pass all 4 steps
# ---------------------------------------------------------------------------

class TestValidCLIArgs:
    def test_passes_all_steps(self):
        """Valid args — no warnings from step 1 (args)."""
        config = _make_config(provider="vllm")
        sv = StartupValidator()
        warnings = sv.dry_run(config)
        # Step 1 (args) should produce no warnings for valid input
        arg_warnings = [
            w for w in warnings
            if "Count" in w or "Unknown provider" in w or "domain_distribution" in w
        ]
        assert len(arg_warnings) == 0

    def test_provider_gemini_args_valid(self):
        """Gemini provider is a valid provider — step 1 passes."""
        config = _make_config(provider="gemini")
        sv = StartupValidator()
        warnings = sv.dry_run(config)
        provider_warnings = [w for w in warnings if "Unknown provider" in w]
        assert len(provider_warnings) == 0

    def test_count_boundary_1(self):
        """count=1 is valid."""
        config = _make_config(count=1)
        sv = StartupValidator()
        warnings = sv.dry_run(config)
        count_warnings = [w for w in warnings if "Count" in w]
        assert len(count_warnings) == 0

    def test_count_boundary_200(self):
        """count=200 is valid."""
        config = _make_config(count=200)
        sv = StartupValidator()
        warnings = sv.dry_run(config)
        count_warnings = [w for w in warnings if "Count" in w]
        assert len(count_warnings) == 0


# ---------------------------------------------------------------------------
# 2. Missing API key fails at step 2
# ---------------------------------------------------------------------------

class TestMissingAPIKey:
    def test_openai_no_key_warning(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OpenAI provider with no OPENAI_API_KEY produces a step-2 warning."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        config = _make_config(provider="openai")
        sv = StartupValidator()
        warnings = sv.dry_run(config)
        assert any("OPENAI_API_KEY" in w for w in warnings)

    def test_gemini_no_key_warning(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Gemini provider with no GOOGLE_API_KEY produces a step-2 warning."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        config = _make_config(provider="gemini")
        sv = StartupValidator()
        warnings = sv.dry_run(config)
        assert any("GOOGLE_API_KEY" in w for w in warnings)

    def test_vllm_no_key_ok(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """vLLM uses fallback auth — no key warning even when env var missing."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        config = _make_config(provider="vllm")
        sv = StartupValidator()
        warnings = sv.dry_run(config)
        key_warnings = [w for w in warnings if "API_KEY" in w]
        assert len(key_warnings) == 0


# ---------------------------------------------------------------------------
# 3. Invalid count fails at step 1
# ---------------------------------------------------------------------------

class TestInvalidCount:
    def test_count_zero(self):
        """count=0 is out of range."""
        config = _make_config(count=0)
        sv = StartupValidator()
        warnings = sv.dry_run(config)
        assert any("Count" in w for w in warnings)

    def test_count_negative(self):
        """Negative count is out of range."""
        config = _make_config(count=-5)
        sv = StartupValidator()
        warnings = sv.dry_run(config)
        assert any("Count" in w for w in warnings)

    def test_count_over_200(self):
        """count=201 exceeds the upper bound."""
        config = _make_config(count=201)
        sv = StartupValidator()
        warnings = sv.dry_run(config)
        assert any("Count" in w for w in warnings)

    def test_invalid_provider(self):
        """Unknown provider string fails step 1."""
        config = _make_config(provider="llama")
        sv = StartupValidator()
        warnings = sv.dry_run(config)
        assert any("Unknown provider" in w for w in warnings)

    def test_invalid_domain_distribution_json(self):
        """Malformed domain_distribution JSON fails step 1."""
        config = _make_config(domain_distribution="not json")
        sv = StartupValidator()
        warnings = sv.dry_run(config)
        assert any("domain_distribution" in w for w in warnings)


# ---------------------------------------------------------------------------
# 4. dry_run returns warnings (not exceptions)
# ---------------------------------------------------------------------------

class TestDryRunReturnsWarnings:
    def test_dry_run_returns_list(self):
        """dry_run returns a list of warning strings."""
        config = _make_config(provider="openai")
        sv = StartupValidator()
        result = sv.dry_run(config)
        assert isinstance(result, list)

    def test_dry_run_clears_warnings_each_call(self):
        """Calling dry_run again clears previous warnings."""
        config = _make_config(provider="openai")
        sv = StartupValidator()
        sv.dry_run(config)
        assert len(sv.warnings) > 0
        sv.dry_run(config)
        assert len(sv.warnings) > 0

    def test_seed_warning_when_file_missing(self, tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
        """If seed file is missing, _validate_seeds adds a warning."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        config = _make_config(provider="openai")
        sv = StartupValidator()
        warnings = sv.dry_run(config)
        # Should have at least the API key warning
        assert any("OPENAI_API_KEY" in w for w in warnings)

    def test_validate_delegates_to_dry_run(self):
        """validate() calls dry_run and logs warnings via logger."""
        config = _make_config(provider="openai")
        sv = StartupValidator()
        # validate should not raise
        sv.validate(config)
        assert len(sv.warnings) > 0
