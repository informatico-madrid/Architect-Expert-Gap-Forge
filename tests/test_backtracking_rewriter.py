#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Tests for the backtracking alignment rewriter module.

TDD-first: these tests define the expected behaviour for
``src.curation.backtracking_rewriter`` before the implementation exists.
"""

from __future__ import annotations

import json
import asyncio
import textwrap
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.schemas.common import RawRecord


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_record(
    *,
    record_id: str = "v11_contrast_abc123",
    example_type: str = "contrast",
    gold_injected: bool = True,
    legacy_detected: bool = False,
    legacy_patterns: list[str] | None = None,
    ldi: float = 1.5,
    think_text: str = "Análisis técnico: debo usar la nueva API.",
    code_text: str = "```python\npass\n```",
    user_prompt: str = "Implementa async_setup_entry con HA 2026.",
    total_chars: int | None = None,
) -> RawRecord:
    """Build a synthetic RawRecord for testing."""
    assistant_content = f"{think_text}</think>\n{code_text}"
    if total_chars and len(assistant_content) + len(user_prompt) < total_chars:
        # Pad to reach approximate char count
        padding = "x" * (total_chars - len(assistant_content) - len(user_prompt))
        assistant_content = f"{think_text}{padding}</think>\n{code_text}"

    return {
        "id": record_id,
        "conversation": [
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": assistant_content},
        ],
        "metadata": {
            "example_type": example_type,
            "gold_injected": gold_injected,
            "legacy_detected": legacy_detected,
            "legacy_patterns": legacy_patterns or [],
            "ldi": ldi,
            "fragment_name": "Module: config_flow",
            "source_file": "acaia___init__.py",
            "curation": {"kept": True},
            "factory_version": "v10.0",
        },
        "filter_text": "",
    }


def _make_jsonl(path: Path, records: list[RawRecord]) -> None:
    """Write a list of records to a JSONL file."""
    with open(path, "w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Tests: extract_think_block / replace_think_block
# ---------------------------------------------------------------------------


class TestThinkBlockManipulation:
    """Test think-block extraction and replacement utilities."""

    def test_extract_splits_at_think_tag(self) -> None:
        from src.curation.backtracking_rewriter import extract_think_block

        content = "Some reasoning here</think>\n```python\npass\n```"
        think, rest = extract_think_block(content)
        assert think == "Some reasoning here"
        assert rest == "\n```python\npass\n```"

    def test_extract_handles_no_tag(self) -> None:
        from src.curation.backtracking_rewriter import extract_think_block

        content = "No think tag at all"
        think, rest = extract_think_block(content)
        assert think == ""
        assert rest == content

    def test_replace_preserves_code(self) -> None:
        from src.curation.backtracking_rewriter import replace_think_block

        original = "Old reasoning</think>\n```python\npass\n```"
        result = replace_think_block(original, "New reasoning with backtracking")
        assert result == "New reasoning with backtracking</think>\n```python\npass\n```"
        # Code after </think> is SACRED — byte-identical
        assert result.split("</think>")[1] == original.split("</think>")[1]

    def test_replace_with_empty_think(self) -> None:
        from src.curation.backtracking_rewriter import replace_think_block

        original = "</think>\ncode here"
        result = replace_think_block(original, "New think content")
        assert result.startswith("New think content</think>")
        assert result.endswith("\ncode here")


# ---------------------------------------------------------------------------
# Tests: classify_rewrite_strategy
# ---------------------------------------------------------------------------


class TestClassifyRewriteStrategy:
    """Test strategy classification logic."""

    def test_legacy_detected_gets_full_backtracking(self) -> None:
        from src.curation.backtracking_rewriter import classify_rewrite_strategy

        record = _make_record(legacy_detected=True, example_type="contrast")
        assert classify_rewrite_strategy(record) == "full_backtracking"

    def test_gold_injected_no_legacy_gets_trace_reconstruction(self) -> None:
        from src.curation.backtracking_rewriter import classify_rewrite_strategy

        record = _make_record(
            gold_injected=True, legacy_detected=False, example_type="nominal"
        )
        assert classify_rewrite_strategy(record) == "trace_reconstruction"

    def test_error_recovery_gets_error_first(self) -> None:
        from src.curation.backtracking_rewriter import classify_rewrite_strategy

        record = _make_record(
            gold_injected=False,
            legacy_detected=False,
            example_type="error_recovery",
        )
        assert classify_rewrite_strategy(record) == "error_first"

    def test_contrast_no_gold_no_legacy_gets_contrast(self) -> None:
        from src.curation.backtracking_rewriter import classify_rewrite_strategy

        record = _make_record(
            gold_injected=False,
            legacy_detected=False,
            example_type="contrast",
        )
        assert classify_rewrite_strategy(record) == "contrast_backtracking"

    def test_clean_nominal_gets_pass_through(self) -> None:
        from src.curation.backtracking_rewriter import classify_rewrite_strategy

        record = _make_record(
            gold_injected=False,
            legacy_detected=False,
            example_type="nominal",
        )
        assert classify_rewrite_strategy(record) == "pass_through"

    def test_theory_gets_skip(self) -> None:
        from src.curation.backtracking_rewriter import classify_rewrite_strategy

        record = _make_record(example_type="theory")
        assert classify_rewrite_strategy(record) == "skip"


# ---------------------------------------------------------------------------
# Tests: passes_backtracking_filter
# ---------------------------------------------------------------------------


class TestBacktrackingFilter:
    """Test filtering logic for backtracking eligibility."""

    def test_theory_excluded(self) -> None:
        from src.curation.backtracking_rewriter import (
            BacktrackingConfig,
            passes_backtracking_filter,
        )

        record = _make_record(example_type="theory")
        assert passes_backtracking_filter(record, BacktrackingConfig()) is False

    def test_over_token_limit_excluded(self) -> None:
        from src.curation.backtracking_rewriter import (
            BacktrackingConfig,
            passes_backtracking_filter,
        )

        # 4000 tokens ≈ 16000 chars; create a record with way more
        record = _make_record(total_chars=20000)
        assert passes_backtracking_filter(record, BacktrackingConfig()) is False

    def test_normal_record_passes(self) -> None:
        from src.curation.backtracking_rewriter import (
            BacktrackingConfig,
            passes_backtracking_filter,
        )

        record = _make_record(example_type="contrast", total_chars=4000)
        assert passes_backtracking_filter(record, BacktrackingConfig()) is True

    def test_no_think_tag_excluded(self) -> None:
        from src.curation.backtracking_rewriter import (
            BacktrackingConfig,
            passes_backtracking_filter,
        )

        record: RawRecord = {
            "id": "no_think",
            "conversation": [
                {"role": "user", "content": "prompt"},
                {"role": "assistant", "content": "no think tag here"},
            ],
            "metadata": {"example_type": "nominal"},
        }
        assert passes_backtracking_filter(record, BacktrackingConfig()) is False


# ---------------------------------------------------------------------------
# Tests: build_rewrite_prompt
# ---------------------------------------------------------------------------


class TestBuildRewritePrompt:
    """Test prompt construction for different strategies."""

    def test_full_backtracking_prompt_mentions_legacy(self) -> None:
        from src.curation.backtracking_rewriter import build_rewrite_prompt

        record = _make_record(
            legacy_detected=True,
            legacy_patterns=["hass.data[] dict pattern -> entry.runtime_data"],
        )
        system_prompt, user_prompt = build_rewrite_prompt(record, "full_backtracking")
        assert (
            "backtracking" in system_prompt.lower()
            or "self-evaluation" in system_prompt.lower()
        )
        assert "hass.data[]" in user_prompt or "legacy" in user_prompt.lower()

    def test_trace_reconstruction_includes_code(self) -> None:
        from src.curation.backtracking_rewriter import build_rewrite_prompt

        record = _make_record(
            gold_injected=True, code_text="```python\nclass MyEntity:\n    pass\n```"
        )
        system_prompt, user_prompt = build_rewrite_prompt(
            record, "trace_reconstruction"
        )
        assert "MyEntity" in user_prompt or "code" in user_prompt.lower()

    def test_pass_through_returns_empty(self) -> None:
        from src.curation.backtracking_rewriter import build_rewrite_prompt

        record = _make_record(example_type="nominal", gold_injected=False)
        system_prompt, user_prompt = build_rewrite_prompt(record, "pass_through")
        assert system_prompt == ""
        assert user_prompt == ""


# ---------------------------------------------------------------------------
# Tests: apply_backtracking_rewrite (integration with mocked vLLM)
# ---------------------------------------------------------------------------


class TestApplyBacktrackingRewrite:
    """Test the single-record rewrite with mocked inference."""

    def test_rewrite_replaces_think_block(self) -> None:
        from src.curation.backtracking_rewriter import (
            BacktrackingConfig,
            apply_backtracking_rewrite,
        )

        record = _make_record(
            legacy_detected=True,
            think_text="Old simple reasoning",
            code_text="```python\npass\n```",
        )
        mock_client = AsyncMock()
        mock_client.generate.return_value = (
            "Espera, mi primer instinto es usar hass.data[] pero eso es legacy. "
            "Según el changelog de HA 2026, debo usar entry.runtime_data."
        )

        result = asyncio.run(
            apply_backtracking_rewrite(
                record,
                mock_client,
                BacktrackingConfig(),
            )
        )
        assert result is not None
        assistant = result["conversation"][-1]["content"]
        # Code after </think> must be preserved
        assert "```python\npass\n```" in assistant
        # New think must contain the rewritten content
        assert "entry.runtime_data" in assistant
        # Metadata updated
        assert result["metadata"]["backtracking_applied"] is True

    def test_pass_through_returns_original(self) -> None:
        from src.curation.backtracking_rewriter import (
            BacktrackingConfig,
            apply_backtracking_rewrite,
        )

        record = _make_record(
            example_type="nominal",
            gold_injected=False,
            legacy_detected=False,
        )
        mock_client = AsyncMock()
        result = asyncio.run(
            apply_backtracking_rewrite(
                record,
                mock_client,
                BacktrackingConfig(),
            )
        )
        assert result is not None
        # Client should NOT have been called
        mock_client.generate.assert_not_called()
        assert result["metadata"]["backtracking_strategy"] == "pass_through"

    def test_inference_failure_returns_none(self) -> None:
        from src.curation.backtracking_rewriter import (
            BacktrackingConfig,
            apply_backtracking_rewrite,
        )

        record = _make_record(legacy_detected=True)
        mock_client = AsyncMock()
        mock_client.generate.side_effect = RuntimeError("vLLM down")

        # Patch asyncio.sleep so retry back-off does not slow the test suite
        with patch(
            "src.curation.backtracking_rewriter.asyncio.sleep", new_callable=AsyncMock
        ):
            result = asyncio.run(
                apply_backtracking_rewrite(
                    record,
                    mock_client,
                    BacktrackingConfig(),
                )
            )
        assert result is None

    def test_sacred_constraint_restores_original_code(self) -> None:
        """Verify sacred constraint: code after <filepath> must be preserved."""
        from src.curation.backtracking_rewriter import (
            BacktrackingConfig,
            apply_backtracking_rewrite,
        )

        # Original code with 4-space indentation
        original_code = 'class Test:\n    def method(self):\n        pass'
        record = _make_record(
            legacy_detected=True,
            think_text="Old reasoning",
            code_text=original_code,
        )
        mock_client = AsyncMock()
        mock_client.generate.return_value = "New backtracking reasoning."

        result = asyncio.run(
            apply_backtracking_rewrite(
                record,
                mock_client,
                BacktrackingConfig(),
            )
        )
        assert result is not None
        assistant = result["conversation"][-1]["content"]
        idx = assistant.find("</think>")
        code_after = assistant[idx + len("</think>"):]
        # The sacred code must be preserved exactly
        assert original_code in code_after


# ---------------------------------------------------------------------------
# Tests: I/O helpers
# ---------------------------------------------------------------------------


class TestIOHelpers:
    """Test JSONL load/save helpers."""

    def test_load_jsonl(self, tmp_path: Path) -> None:
        from src.curation.backtracking_rewriter import load_jsonl

        records = [_make_record(record_id=f"r{i}") for i in range(3)]
        path = tmp_path / "test.jsonl"
        _make_jsonl(path, records)

        loaded = load_jsonl(path)
        assert len(loaded) == 3
        assert loaded[0]["id"] == "r0"

    def test_save_jsonl(self, tmp_path: Path) -> None:
        from src.curation.backtracking_rewriter import save_jsonl

        records = [_make_record(record_id=f"r{i}") for i in range(2)]
        path = tmp_path / "output.jsonl"
        save_jsonl(records, path)

        with open(path) as fh:
            lines = fh.readlines()
        assert len(lines) == 2
        parsed = json.loads(lines[0])
        assert parsed["id"] == "r0"


# ---------------------------------------------------------------------------
# Tests: Config loading
# ---------------------------------------------------------------------------


class TestConfigLoading:
    """Test YAML config loading for BacktrackingConfig."""

    def test_default_config_values(self) -> None:
        from src.curation.backtracking_rewriter import BacktrackingConfig

        cfg = BacktrackingConfig()
        assert cfg.max_tokens == 4000
        assert "theory" in cfg.excluded_types
        assert cfg.temperature == 0.6

    def test_load_from_yaml(self, tmp_path: Path) -> None:
        from src.curation.backtracking_rewriter import load_backtracking_config

        yaml_content = textwrap.dedent("""\
            max_tokens: 3000
            temperature: 0.4
            excluded_types:
              - theory
              - nominal
        """)
        cfg_path = tmp_path / "config.yaml"
        cfg_path.write_text(yaml_content)

        cfg = load_backtracking_config(cfg_path)
        assert cfg.max_tokens == 3000
        assert cfg.temperature == 0.4
        assert "nominal" in cfg.excluded_types
