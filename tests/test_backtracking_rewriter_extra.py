#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.schemas.common import RawRecord


def _make_record(
    *,
    record_id: str = "r1",
    example_type: str = "contrast",
    gold_injected: bool = True,
    legacy_detected: bool = False,
    think_text: str = "Reasoning here",
    code_text: str = "```python\npass\n```",
) -> RawRecord:
    assistant_content = f"{think_text}</think>\n{code_text}"
    return {
        "id": record_id,
        "conversation": [
            {"role": "user", "content": "please implement"},
            {"role": "assistant", "content": assistant_content},
        ],
        "metadata": {
            "example_type": example_type,
            "gold_injected": gold_injected,
            "legacy_detected": legacy_detected,
        },
    }


def _make_jsonl(path: Path, records: list[RawRecord]) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def test_build_rewrite_prompt_error_and_contrast() -> None:
    from src.curation.backtracking_rewriter import build_rewrite_prompt

    r1 = _make_record(example_type="error_recovery", gold_injected=False)
    sys1, user1 = build_rewrite_prompt(r1, "error_first")
    assert sys1
    assert "error" in user1.lower() or "wrong" in user1.lower()

    r2 = _make_record(example_type="contrast", gold_injected=False)
    sys2, user2 = build_rewrite_prompt(r2, "contrast_backtracking")
    assert sys2
    assert "old" in user2.lower() or "approach" in user2.lower()


def test_apply_backtracking_rewrite_strips_think_and_preserves_code(tmp_path: Path) -> None:
    from src.curation.backtracking_rewriter import (
        BacktrackingConfig,
        apply_backtracking_rewrite,
    )

    rec = _make_record(record_id="striptest", legacy_detected=True, think_text="Old reasoning")
    # Simulate a thinking model (e.g. qwen3): meta-reasoning lives INSIDE <think>…</think>,
    # the real clean answer comes AFTER the closing tag.
    # Any code blocks accidentally included in the answer part must be sanitised.
    mock_client = AsyncMock()
    mock_client.generate.return_value = (
        "<think>Internal meta-reasoning about how to write the monologue.</think>"
        "New refined reasoning that is clean. ```python\nmalicious\n```"
    )

    out = asyncio.run(apply_backtracking_rewrite(rec, mock_client, BacktrackingConfig()))
    assert out is not None
    assistant = out["conversation"][-1]["content"]
    # Meta-reasoning noise (before </think>) must NOT appear
    assert "Internal meta-reasoning" not in assistant
    # Malicious code block injected in the answer must be stripped by sanitiser
    assert "malicious" not in assistant
    # Original training-record code (the Sacred section) must be preserved
    assert "```python\npass\n```" in assistant
    assert out["metadata"]["backtracking_applied"] is True


def test_rewrite_pipeline_with_mock_client(tmp_path: Path) -> None:
    from src.curation.backtracking_rewriter import (
        BacktrackingConfig,
        rewrite_pipeline,
    )

    # Prepare three records: one theory (filtered), one nominal (pass-through), one legacy (rewritten)
    rec1 = _make_record(record_id="t1", example_type="theory")
    rec2 = _make_record(record_id="t2", example_type="nominal", gold_injected=False)
    rec3 = _make_record(record_id="t3", legacy_detected=True)

    inp = tmp_path / "in.jsonl"
    out = tmp_path / "out.jsonl"
    _make_jsonl(inp, [rec1, rec2, rec3])

    mock_client = AsyncMock()
    mock_client.generate.return_value = "Rewritten reasoning for the legacy case."

    cfg = BacktrackingConfig(batch_size=2)
    report = asyncio.run(rewrite_pipeline(inp, out, cfg, client=mock_client))

    # One filtered (theory), two output records
    assert report.total_input == 3
    assert report.filtered_out == 1
    assert report.total_output == 2
    # Check strategy counts include pass_through and full_backtracking
    assert "pass_through" in report.strategy_counts
    assert "full_backtracking" in report.strategy_counts

    # Inspect output contents
    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------


def test_main_exits_zero_with_required_args(tmp_path: Path) -> None:
    """main() must return 0 when pipeline succeeds."""
    from src.curation.backtracking_rewriter import PipelineReport, main

    inp = tmp_path / "in.jsonl"
    out = tmp_path / "out.jsonl"
    _make_jsonl(inp, [_make_record(record_id="cli1")])

    fake_report = PipelineReport(
        total_input=1,
        filtered_out=0,
        rewritten=1,
        pass_through=0,
        failed=0,
        rejected=0,
        total_output=1,
        strategy_counts={"trace_reconstruction": 1},
    )

    with patch(
        "src.curation.backtracking_rewriter.rewrite_pipeline",
        new_callable=AsyncMock,
        return_value=fake_report,
    ) as mock_pipeline:
        exit_code = main(["--input", str(inp), "--output", str(out)])

    assert exit_code == 0
    mock_pipeline.assert_called_once()
    call_args = mock_pipeline.call_args
    assert call_args.args[0] == inp
    assert call_args.args[1] == out


def test_main_cli_overrides_are_applied(tmp_path: Path) -> None:
    """CLI flags --model, --temperature, --base-url must override config values."""
    from src.curation.backtracking_rewriter import BacktrackingConfig, PipelineReport, main

    inp = tmp_path / "in.jsonl"
    out = tmp_path / "out.jsonl"
    _make_jsonl(inp, [_make_record(record_id="cli2")])

    fake_report = PipelineReport(
        total_input=1, filtered_out=0, rewritten=1,
        pass_through=0, failed=0, rejected=0, total_output=1,
        strategy_counts={},
    )

    captured_cfg: list[BacktrackingConfig] = []

    def _capture(inp: Path, out: Path, cfg: BacktrackingConfig, **kw: Any) -> PipelineReport:
        captured_cfg.append(cfg)
        return fake_report

    with patch("src.curation.backtracking_rewriter.rewrite_pipeline", new_callable=AsyncMock, side_effect=_capture):
        exit_code = main([
            "--input", str(inp),
            "--output", str(out),
            "--model", "my-custom-model",
            "--temperature", "0.3",
            "--base-url", "http://custom:9000/v1",
            "--batch-size", "50",
        ])

    assert exit_code == 0
    assert len(captured_cfg) == 1
    cfg = captured_cfg[0]
    assert cfg.vllm_model == "my-custom-model"
    assert cfg.temperature == 0.3
    assert cfg.vllm_api_url == "http://custom:9000/v1"
    assert cfg.batch_size == 50


def test_main_loads_yaml_config(tmp_path: Path) -> None:
    """main() must load config values from a YAML file when --config is provided."""
    import yaml
    from src.curation.backtracking_rewriter import BacktrackingConfig, PipelineReport, main

    inp = tmp_path / "in.jsonl"
    out = tmp_path / "out.jsonl"
    _make_jsonl(inp, [_make_record(record_id="cli3")])

    cfg_file = tmp_path / "test_cfg.yaml"
    cfg_file.write_text(
        yaml.dump({"temperature": 0.1, "vllm_model": "yaml-model", "batch_size": 7}),
        encoding="utf-8",
    )

    fake_report = PipelineReport(
        total_input=1, filtered_out=0, rewritten=1,
        pass_through=0, failed=0, rejected=0, total_output=1,
        strategy_counts={},
    )
    captured_cfg: list[BacktrackingConfig] = []

    def _capture(inp: Path, out: Path, cfg: BacktrackingConfig, **kw: Any) -> PipelineReport:
        captured_cfg.append(cfg)
        return fake_report

    with patch("src.curation.backtracking_rewriter.rewrite_pipeline", new_callable=AsyncMock, side_effect=_capture):
        exit_code = main(["--input", str(inp), "--output", str(out), "--config", str(cfg_file)])

    assert exit_code == 0
    assert captured_cfg[0].temperature == 0.1
    assert captured_cfg[0].vllm_model == "yaml-model"
    assert captured_cfg[0].batch_size == 7


# ---------------------------------------------------------------------------
# Tests: _load_legacy_regexes
# ---------------------------------------------------------------------------


def test_load_legacy_regexes_from_yaml(tmp_path: Path) -> None:
    """Load compiled regex patterns from a well-formed YAML file."""
    import yaml
    from src.curation.backtracking_rewriter import _load_legacy_regexes

    patterns_file = tmp_path / "patterns.yaml"
    data = {
        "legacy_patterns": [
            {"pattern": r"\bhass\.data\b", "description": "hass.data"},
            {"pattern": r"\basync_forward_entry_setup\b(?!s)", "description": "singular setup"},
        ]
    }
    patterns_file.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")
    regexes = _load_legacy_regexes(str(patterns_file))
    assert len(regexes) == 2
    assert regexes[0].search("hass.data[DOMAIN]")
    assert not regexes[0].search("entry.runtime_data")


def test_load_legacy_regexes_missing_file() -> None:
    """Return empty tuple with a warning when the file does not exist."""
    from src.curation.backtracking_rewriter import _load_legacy_regexes

    regexes = _load_legacy_regexes("/nonexistent/patterns.yaml")
    assert regexes == ()


def test_load_legacy_regexes_invalid_regex(tmp_path: Path) -> None:
    """Skip invalid regex entries without aborting."""
    import yaml
    from src.curation.backtracking_rewriter import _load_legacy_regexes

    patterns_file = tmp_path / "bad.yaml"
    data = {
        "legacy_patterns": [
            {"pattern": "[invalid(", "description": "broken regex"},
            {"pattern": r"\bvalid_pattern\b", "description": "this one is fine"},
        ]
    }
    patterns_file.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")
    regexes = _load_legacy_regexes(str(patterns_file))
    assert len(regexes) == 1
    assert regexes[0].search("valid_pattern")


# ---------------------------------------------------------------------------
# Tests: _validate_resolution_no_legacy (Split Validation)
# ---------------------------------------------------------------------------


def test_validate_resolution_clean_second_half() -> None:
    """Legacy only in first half (Legacy Impulse) — should pass."""
    import re
    from src.curation.backtracking_rewriter import _validate_resolution_no_legacy

    regexes = (re.compile(r"\bhass\.data\b"),)
    # First half mentions legacy (intentional), second half is clean
    think = (
        "My first instinct is to use hass.data[DOMAIN] to store the coordinator. "
        "Wait, that's the old pattern. "
        "I should use entry.runtime_data with a typed dataclass instead, "
        "which is the modern HA 2026 approach."
    )
    code_rest = "\ncoordinator = entry.runtime_data.coordinator"
    passed, reason = _validate_resolution_no_legacy(think, code_rest, regexes)
    assert passed, f"Should have passed but got: {reason}"


def test_validate_resolution_legacy_in_second_half() -> None:
    """Legacy in second half (resolution) — should be rejected."""
    import re
    from src.curation.backtracking_rewriter import _validate_resolution_no_legacy

    regexes = (re.compile(r"\bhass\.data\b"),)
    # Legacy pattern appears in the resolution half (second half)
    think = (
        "Let me think about this integration setup. "
        "I need to configure the coordinator properly. "
        "So the final approach is to use hass.data[DOMAIN] "
        "to store the coordinator reference."
    )
    code_rest = "\ncoordinator = entry.runtime_data.coordinator"
    passed, reason = _validate_resolution_no_legacy(think, code_rest, regexes)
    assert not passed
    assert "hass.data" in reason


def test_validate_resolution_legacy_in_code_block() -> None:
    """Legacy in the sacred code block — should be rejected."""
    import re
    from src.curation.backtracking_rewriter import _validate_resolution_no_legacy

    regexes = (re.compile(r"\bhass\.data\b"),)
    think = "Clean reasoning without any legacy patterns at all."
    code_rest = "\nhass.data[DOMAIN] = coordinator"
    passed, reason = _validate_resolution_no_legacy(think, code_rest, regexes)
    assert not passed
    assert "code block" in reason


def test_validate_resolution_empty_regexes() -> None:
    """No regexes configured — always passes."""
    from src.curation.backtracking_rewriter import _validate_resolution_no_legacy

    passed, reason = _validate_resolution_no_legacy(
        "anything", "anything", ()
    )
    assert passed
    assert reason == ""


def test_validate_resolution_multiple_patterns() -> None:
    """Multiple patterns — reject if any match in resolution half."""
    import re
    from src.curation.backtracking_rewriter import _validate_resolution_no_legacy

    regexes = (
        re.compile(r"\bhass\.data\b"),
        re.compile(r"\basync_forward_entry_setup\b(?!s)"),
    )
    # Legacy Impulse in first half, but singular setup in second half
    think = (
        "First, I considered using hass.data for storage. "
        "But wait, that's legacy. Now I will set up platforms. "
        "I will call async_forward_entry_setup(entry, 'sensor') "
        "to register the sensor platform."
    )
    code_rest = "\nawait hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)"
    passed, reason = _validate_resolution_no_legacy(think, code_rest, regexes)
    assert not passed
    assert "async_forward_entry_setup" in reason


# ---------------------------------------------------------------------------
# Tests: apply_backtracking_rewrite with rejection sampling
# ---------------------------------------------------------------------------


def test_apply_rewrite_rejection_sampling_discards_legacy_resolution() -> None:
    """Record is discarded (raises) when resolution half has legacy patterns."""
    import re
    from src.curation.backtracking_rewriter import (
        BacktrackingConfig,
        _RejectionSamplingError,
        apply_backtracking_rewrite,
    )

    record = _make_record(
        record_id="reject_test",
        legacy_detected=True,
        think_text="Old reasoning",
        code_text="entry.runtime_data = coordinator",
    )
    mock_client = AsyncMock()
    # Model output: legacy appears in the SECOND half (resolution)
    mock_client.generate.return_value = (
        "I considered the modern approach but decided to just use "
        "hass.data[DOMAIN] to store the coordinator directly."
    )

    legacy_regexes = (re.compile(r"\bhass\.data\b"),)

    with pytest.raises(_RejectionSamplingError):
        asyncio.run(apply_backtracking_rewrite(
            record, mock_client, BacktrackingConfig(),
            _legacy_regexes=legacy_regexes,
        ))


def test_apply_rewrite_rejection_sampling_passes_clean_resolution() -> None:
    """Record passes when legacy is only in the first half (Legacy Impulse)."""
    import re
    from src.curation.backtracking_rewriter import (
        BacktrackingConfig,
        apply_backtracking_rewrite,
    )

    record = _make_record(
        record_id="pass_test",
        legacy_detected=True,
        think_text="Old reasoning",
        code_text="entry.runtime_data = coordinator",
    )
    mock_client = AsyncMock()
    # Legacy only in first half, resolution is clean
    mock_client.generate.return_value = (
        "My first instinct is to use hass.data[DOMAIN] to store data. "
        "Wait, that is the deprecated 2023 pattern. "
        "I should use entry.runtime_data with a frozen dataclass. "
        "This follows the HA 2026 architectural standard perfectly."
    )

    legacy_regexes = (re.compile(r"\bhass\.data\b"),)

    result = asyncio.run(apply_backtracking_rewrite(
        record, mock_client, BacktrackingConfig(),
        _legacy_regexes=legacy_regexes,
    ))
    assert result is not None
    assert result["metadata"]["backtracking_applied"] is True
