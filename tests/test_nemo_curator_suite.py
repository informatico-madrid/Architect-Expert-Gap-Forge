#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for src/curation/ submodules.

All four curation phases tested with pure (no NeMo / no Ray / no datasketch):
  Phase 0  — exact_dedup
  Phase 1  — run_nemo_filter_pipeline (error paths only; NeMo not installed)
  Phase 2  — structural_quality_filter + helpers (_ldi, _has_meta_speech, etc.)
  Phase 3  — semantic_dedup (naive fallback; datasketch not required)

Also covers:
  CurationStats / ConversationExtractor
  _extract_assistant_text / _heuristic_quality_score / _char_shingles
  load_jsonl / write_jsonl / save_report
"""

from __future__ import annotations

import json
import os
import socket
from pathlib import Path
from typing import Any, Dict, List

import pytest

# Import from new submodules
from src.curation.curator_pipeline import (
    ConversationExtractor,
    CurationStats,
    _NEMO_AVAILABLE,
    load_jsonl,
    run_nemo_filter_pipeline,
    save_report,
    write_jsonl,
)
from src.curation.dedup_filter import (
    _build_clusters_naive,
    _char_shingles,
    _extract_assistant_text,
    _heuristic_quality_score,
    exact_dedup,
    semantic_dedup,
)
from src.curation.quality_filter import (
    _count_code_tokens,
    _count_natural_tokens,
    _has_meta_speech,
    _ldi,
    structural_quality_filter,
)

# Import curator_pipeline module for monkeypatching (tests patch module-level vars)
import src.curation.curator_pipeline as ncs


# ===========================================================================
# Helpers
# ===========================================================================


def _make_agentic_record(
    rec_id: str,
    think: str = "",
    tool_call_code: str = "",
    extra_assistant_content: str = "",
) -> Dict[str, Any]:
    """Build a minimal agentic JSONL record (multi-turn with tool_call grammar)."""
    if think:
        tc = f"<tool_call>{tool_call_code}</tool_call>" if tool_call_code else ""
        assistant_content = f"<think>{think}</think>{tc}"
    else:
        assistant_content = extra_assistant_content
    return {
        "id": rec_id,
        "conversation": [
            {"role": "user", "content": "Implement a sensor."},
            {"role": "assistant", "content": assistant_content},
        ],
        "metadata": {"example_type": "nominal"},
    }


def _long_think(n: int = 200) -> str:
    """Return a technical (non-meta) think block of at least n characters."""
    base = (
        "The CoordinatorEntity pattern in Home Assistant 2026 uses DataUpdateCoordinator. "
        "Inject entry.runtime_data instead of hass.data. "
        "Use async_added_to_hass and native_value property. "
    )
    return (base * (n // len(base) + 2))[: max(n, 600)]


def _code_tool_call(size: str = "large") -> str:
    """Return a tool_call JSON string with code content for LDI >= default."""
    if size == "small":
        # minimal — likely fails LDI
        return json.dumps(
            {"name": "write_to_file", "arguments": {"path": "a.py", "content": "pass"}}
        )
    # large — enough code tokens to pass default LDI threshold
    code = (
        "class MySensor(CoordinatorEntity):\\n"
        "    def __init__(self, coordinator: DataUpdateCoordinator) -> None:\\n"
        "        super().__init__(coordinator)\\n"
        "        self._attr_name = 'My Sensor'\\n"
        "        self._attr_unique_id = 'my_sensor_unique'\\n"
        "    @property\\n"
        "    def native_value(self) -> float:\\n"
        "        return self.coordinator.data.value\\n"
        "    async def async_added_to_hass(self) -> None:\\n"
        "        await super().async_added_to_hass()\\n"
        "        self.async_on_remove(\\n"
        "            self.coordinator.async_add_listener(self.async_write_ha_state)\\n"
        "        )\\n"
        "async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,\\n"
        "    async_add_entities: AddEntitiesCallback) -> None:\\n"
        "    coordinator = MySensorCoordinator(hass, entry)\\n"
        "    await coordinator.async_config_entry_first_refresh()\\n"
        "    async_add_entities([MySensor(coordinator)], True)\\n"
    )
    return json.dumps(
        {
            "name": "write_to_file",
            "arguments": {"path": "sensor/sensor.py", "content": code},
        }
    )


# ===========================================================================
# CurationStats
# ===========================================================================


class TestCurationStats:
    def test_defaults_all_zero(self) -> None:
        s = CurationStats()
        d = s.as_dict()
        assert d["total_input"] == 0
        assert d["total_output"] == 0
        assert d["removed"]["total"] == 0

    def test_retention_is_zero_on_empty(self) -> None:
        s = CurationStats()
        assert s.as_dict()["retention_pct"] == 0.0

    def test_retention_calculated_correctly(self) -> None:
        s = CurationStats(total_input=100, total_output=75)
        assert s.as_dict()["retention_pct"] == 75.0

    def test_total_removed_sums_all_categories(self) -> None:
        s = CurationStats(
            total_input=10,
            exact_duplicates=1,
            nemo_filtered=1,
            invalid_syntax=1,
            shallow_thinking=1,
            meta_speech=1,
            low_ldi=1,
            low_quality_score=1,
            semantic_duplicates=1,
            total_output=2,
        )
        assert s.as_dict()["removed"]["total"] == 8

    def test_as_dict_has_timestamp(self) -> None:
        s = CurationStats()
        d = s.as_dict()
        assert "timestamp" in d
        assert d["timestamp"].endswith("Z")

    def test_print_report_does_not_raise(self, capsys: pytest.CaptureFixture) -> None:
        s = CurationStats(total_input=10, total_output=8)
        s.print_report()
        out = capsys.readouterr().out
        assert "Curation Report" in out


# ===========================================================================
# ConversationExtractor
# ===========================================================================


class TestConversationExtractor:
    def setup_method(self) -> None:
        self.extractor = ConversationExtractor()

    def test_extracts_single_assistant_turn(self) -> None:
        conv = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
        result = self.extractor(conv)
        assert "Hi there" in result

    def test_skips_non_assistant_roles(self) -> None:
        conv = [
            {"role": "user", "content": "A"},
            {"role": "system", "content": "B"},
            {"role": "assistant", "content": "C"},
        ]
        result = self.extractor(conv)
        assert "A" not in result
        assert "B" not in result
        assert "C" in result

    def test_empty_list_returns_empty_string(self) -> None:
        assert self.extractor([]) == ""

    def test_none_returns_empty_string(self) -> None:
        assert self.extractor(None) == ""

    def test_non_list_returns_empty_string(self) -> None:
        assert self.extractor("not a list") == ""

    def test_multiple_assistant_turns_joined(self) -> None:
        conv = [
            {"role": "assistant", "content": "turn1"},
            {"role": "user", "content": "q"},
            {"role": "assistant", "content": "turn2"},
        ]
        result = self.extractor(conv)
        assert "turn1" in result
        assert "turn2" in result


# ===========================================================================
# Phase 0 — exact_dedup
# ===========================================================================


class TestExactDedup:
    def test_keeps_unique_records(self) -> None:
        stats = CurationStats()
        records = [
            {"id": "a", "conversation": [{"role": "user", "content": "A"}]},
            {"id": "b", "conversation": [{"role": "user", "content": "B"}]},
        ]
        kept = exact_dedup(records, stats)
        assert len(kept) == 2
        assert stats.exact_duplicates == 0

    def test_removes_exact_duplicate(self) -> None:
        stats = CurationStats()
        conversation = [{"role": "user", "content": "same content"}]
        records = [
            {"id": "r1", "conversation": conversation},
            {"id": "r2", "conversation": conversation},  # identical conversation
        ]
        kept = exact_dedup(records, stats)
        assert len(kept) == 1
        assert stats.exact_duplicates == 1

    def test_keeps_first_occurrence(self) -> None:
        stats = CurationStats()
        conversation = [{"role": "user", "content": "dup"}]
        records = [
            {"id": "first", "conversation": conversation},
            {"id": "second", "conversation": conversation},
        ]
        kept = exact_dedup(records, stats)
        assert kept[0]["id"] == "first"

    def test_empty_list(self) -> None:
        stats = CurationStats()
        assert exact_dedup([], stats) == []


# ===========================================================================
# Phase 1 — run_nemo_filter_pipeline (error paths)
# ===========================================================================


class TestRunNemoFilterPipeline:
    def test_raises_runtime_error_when_not_installed(self, tmp_path: Path) -> None:
        """When nemo-curator is not installed, raises RuntimeError immediately."""
        if _NEMO_AVAILABLE:
            pytest.skip(
                "nemo-curator is installed; this test covers the missing-dep path"
            )
        with pytest.raises(RuntimeError, match="nemo-curator is not installed"):
            run_nemo_filter_pipeline(
                str(tmp_path / "in.jsonl"), str(tmp_path / "out.jsonl")
            )


# ===========================================================================
# Helpers for Phase 2
# ===========================================================================


class TestLdi:
    def test_zero_code_tokens_returns_zero(self) -> None:
        result = _ldi("only natural language words here no code at all")
        assert result == 0.0

    def test_code_heavy_text_returns_positive(self) -> None:
        code = """
```python
class MySensor(CoordinatorEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator)
    @property
    def native_value(self):
        return self.coordinator.data.value
```
"""
        assert _ldi(code) > 0.0

    def test_empty_text_returns_zero(self) -> None:
        assert _ldi("") == 0.0

    def test_json_with_code_content(self) -> None:
        payload = json.dumps(
            {
                "name": "write_to_file",
                "arguments": {
                    "path": "sensor.py",
                    "content": "async def async_setup_entry(hass, entry):\n    coordinator = DataUpdateCoordinator(hass)\n    await coordinator.async_config_entry_first_refresh()\n",
                },
            }
        )
        score = _ldi(payload)
        assert isinstance(score, float)
        assert score >= 0.0


class TestHasMetaSpeech:
    def test_clean_technical_content_is_false(self) -> None:
        content = (
            "The CoordinatorEntity pattern requires DataUpdateCoordinator. "
            "Configure the async_setup_entry function to inject entry.runtime_data. "
            "The native_value property should return coordinator.data.value. "
        ) * 5
        assert not _has_meta_speech(content)

    def test_meta_speech_dominated_content_is_true(self) -> None:
        content = "\n".join(
            [
                "The user is asking me about sensor implementation.",
                "I need to think about the coordinator approach.",
                "Let me analyze the requirements carefully.",
                "I should implement using the modern pattern.",
                "I will now proceed with writing the code.",
            ]
        )
        assert _has_meta_speech(content)

    def test_empty_string_is_false(self) -> None:
        # empty → no lines after split → returns False
        assert not _has_meta_speech("")


class TestTokenCounting:
    def test_count_code_tokens_detects_code_and_json(self) -> None:
        text = (
            "```python\nasync def foo(hass):\n    return hass.data[]\n```\n"
            '{"name": "foo", "arguments": {"content": "pass"}}'
        )
        tokens = _count_code_tokens(text)
        assert tokens > 5

    def test_count_natural_tokens_ignores_keywords(self) -> None:
        narrative = "Home Assistant 2026 recommends using entry.runtime_data instead of hass.data[] to keep data clean."
        tokens = _count_natural_tokens(narrative)
        assert tokens >= 10


class TestNaiveClustering:
    def test_build_clusters_naive_groups_similar_texts(self) -> None:
        texts = [
            "Duplicate content used as reference.",
            "Duplicate content used as reference.",
            "Completely different narration about automations.",
        ]
        clusters = _build_clusters_naive(texts, threshold=0.5, shingle_k=3)
        assert any(len(cluster) > 1 for cluster in clusters)

    def test_build_clusters_naive_returns_separate_when_distinct(self) -> None:
        texts = [
            "A unique paragraph about sensors.",
            "Another unrelated paragraph about automations.",
        ]
        clusters = _build_clusters_naive(texts, threshold=0.9, shingle_k=3)
        assert all(len(cluster) == 1 for cluster in clusters)


# ===========================================================================
# Phase 2 — structural_quality_filter
# ===========================================================================


class TestStructuralQualityFilter:
    def test_passes_clean_record(self) -> None:
        """A well-formed record with long think and code-heavy tool_call passes all checks."""
        stats = CurationStats()
        think = _long_think(600)
        tc = _code_tool_call("large")
        record = _make_agentic_record("clean", think=think, tool_call_code=tc)
        kept = structural_quality_filter(
            [record],
            stats,
            min_think_chars=500,
        )
        assert len(kept) == 1

    def test_filters_invalid_syntax_whitespace_between_tags(self) -> None:
        """</think> followed by whitespace then <tool_call> is invalid."""
        stats = CurationStats()
        tc = _code_tool_call("large")
        record = {
            "id": "bad_syntax",
            "conversation": [
                {"role": "user", "content": "q"},
                {
                    "role": "assistant",
                    "content": f"<think>reasoning</think> <tool_call>{tc}</tool_call>",
                },
            ],
        }
        kept = structural_quality_filter([record], stats)
        assert len(kept) == 0
        assert stats.invalid_syntax == 1

    def test_filters_shallow_thinking(self) -> None:
        """Think block shorter than min_think_chars is rejected."""
        stats = CurationStats()
        short_think = "short"  # < 500 chars
        tc = _code_tool_call("large")
        record = _make_agentic_record("shallow", think=short_think, tool_call_code=tc)
        kept = structural_quality_filter([record], stats, min_think_chars=500)
        assert len(kept) == 0
        assert stats.shallow_thinking == 1

    def test_filters_meta_speech(self) -> None:
        """A think block dominated by meta-speech phrases is rejected."""
        stats = CurationStats()
        meta = (
            "\n".join(
                [
                    "The user is asking about a sensor.",
                    "I need to implement this feature.",
                    "Let me think about the approach to use.",
                    "I should follow the modern pattern.",
                    "I will now write the code for this task.",
                ]
            )
            * 4
        )  # enough for > 500 chars when repeated
        tc = _code_tool_call("large")
        record = _make_agentic_record("meta", think=meta * 2, tool_call_code=tc)
        kept = structural_quality_filter([record], stats, min_think_chars=500)
        assert len(kept) == 0
        assert stats.meta_speech == 1

    def test_filters_missing_think_tags_as_invalid_syntax(self) -> None:
        """A think block that cannot be parsed (open without close) is invalid."""
        stats = CurationStats()
        record = {
            "id": "no_close",
            "conversation": [
                {"role": "user", "content": "q"},
                {
                    "role": "assistant",
                    "content": "<think>unclosed think block without closing tag",
                },
            ],
        }
        kept = structural_quality_filter([record], stats)
        assert len(kept) == 0
        assert stats.invalid_syntax >= 1

    def test_passes_record_without_think_block(self) -> None:
        """Records without think tags pass filters 2-4 but still pass filter 1."""
        stats = CurationStats()
        record = {
            "id": "no_think",
            "conversation": [
                {"role": "user", "content": "q"},
                {"role": "assistant", "content": "direct answer without think block"},
            ],
        }
        kept = structural_quality_filter([record], stats)
        # records without <think> are passed through (first_think_turn is None)
        assert len(kept) == 1

    def test_record_without_assistant_turn_is_invalid(self) -> None:
        stats = CurationStats()
        record = {
            "id": "no_assistant",
            "conversation": [{"role": "user", "content": "q"}],
        }
        kept = structural_quality_filter([record], stats)
        assert len(kept) == 0
        assert stats.invalid_syntax == 1

    def test_empty_records_list(self) -> None:
        stats = CurationStats()
        kept = structural_quality_filter([], stats)
        assert kept == []


# ===========================================================================
# _heuristic_quality_score
# ===========================================================================


class TestHeuristicQualityScore:
    def test_empty_string_returns_zero(self) -> None:
        assert _heuristic_quality_score("") == 0.0

    def test_score_in_valid_range(self) -> None:
        text = "The CoordinatorEntity pattern in Home Assistant 2026 leverages modern async architecture."
        score = _heuristic_quality_score(text)
        assert 0.0 <= score <= 1.0

    def test_repeated_sentences_get_low_score(self) -> None:
        sentence = "This is bad content. "
        repeated = sentence * 20
        normal_score = _heuristic_quality_score(
            "The coordinator pattern provides clean API. Modern approach works well."
        )
        repeated_score = _heuristic_quality_score(repeated)
        assert repeated_score < normal_score

    def test_no_words_returns_zero(self) -> None:
        assert _heuristic_quality_score("123 456 789") == pytest.approx(0.0, abs=0.05)


# ===========================================================================
# _char_shingles
# ===========================================================================


class TestCharShingles:
    def test_returns_set(self) -> None:
        assert isinstance(_char_shingles("hello world"), set)

    def test_empty_text_returns_empty_set(self) -> None:
        assert _char_shingles("") == set()

    def test_short_text_shorter_than_k(self) -> None:
        result = _char_shingles("ab", k=5)
        # shorter than k → returns the normalised string as single shingle
        assert len(result) >= 1

    def test_shingles_have_correct_length(self) -> None:
        shingles = _char_shingles("hello world", k=3)
        for s in shingles:
            assert len(s) == 3

    def test_different_texts_produce_different_shingles(self) -> None:
        sa = _char_shingles("abcdefgh")
        sb = _char_shingles("zyxwvuts")
        # Almost certainly no overlap for completely different characters
        overlap = sa & sb
        assert len(overlap) == 0 or len(overlap) < len(sa)


# ===========================================================================
# _extract_assistant_text
# ===========================================================================


class TestExtractAssistantText:
    def test_extracts_from_conversation_role(self) -> None:
        rec = {
            "conversation": [
                {"role": "user", "content": "q"},
                {"role": "assistant", "content": "answer content"},
            ]
        }
        assert "answer content" in _extract_assistant_text(rec)

    def test_falls_back_to_assistant_key(self) -> None:
        rec = {"assistant": "direct assistant text"}
        assert "direct assistant text" in _extract_assistant_text(rec)

    def test_falls_back_to_response_key(self) -> None:
        rec = {"response": "response text"}
        assert "response text" in _extract_assistant_text(rec)

    def test_empty_record_returns_empty_string(self) -> None:
        assert _extract_assistant_text({}) == ""

    def test_multiple_assistant_turns_joined(self) -> None:
        rec = {
            "conversation": [
                {"role": "assistant", "content": "part1"},
                {"role": "user", "content": "q"},
                {"role": "assistant", "content": "part2"},
            ]
        }
        text = _extract_assistant_text(rec)
        assert "part1" in text and "part2" in text


# ===========================================================================
# Phase 3 — semantic_dedup
# ===========================================================================


class TestSemanticDedup:
    def _make_record(self, rec_id: str, content: str) -> Dict[str, Any]:
        return {
            "id": rec_id,
            "conversation": [{"role": "assistant", "content": content}],
            "metadata": {},
        }

    def test_keeps_unique_records(self) -> None:
        stats = CurationStats()
        records = [
            self._make_record(
                "a", "The coordinator handles data updates via async refresh pattern."
            ),
            self._make_record(
                "b",
                "Triggers in 2026 use the plural triggers: key for all automations.",
            ),
        ]
        kept = semantic_dedup(records, stats, quality_cutoff=0.0)
        assert len(kept) == 2

    def test_removes_low_quality_records(self) -> None:
        stats = CurationStats()
        # Very low quality: empty content
        records = [
            self._make_record("empty1", ""),
            self._make_record("empty2", ""),
        ]
        kept = semantic_dedup(records, stats, quality_cutoff=0.20)
        assert stats.low_quality_score >= 2

    def test_removes_near_duplicates(self) -> None:
        stats = CurationStats()
        # Identical content → same shingles → Jaccard = 1.0 > any threshold
        text = (
            "The coordinator entity pattern uses DataUpdateCoordinator and entry runtime data. "
            * 20
        )
        records = [
            self._make_record("r1", text),
            self._make_record("r2", text),
        ]
        kept = semantic_dedup(records, stats, threshold=0.8, quality_cutoff=0.0)
        assert len(kept) == 1
        assert stats.semantic_duplicates == 1

    def test_output_records_have_quality_score_in_metadata(self) -> None:
        stats = CurationStats()
        records = [
            self._make_record(
                "x", "Some reasonable sensor implementation content for test."
            ),
        ]
        kept = semantic_dedup(records, stats, quality_cutoff=0.0)
        if kept:
            assert "curation" in kept[0]["metadata"]
            assert "quality_score" in kept[0]["metadata"]["curation"]

    def test_empty_records_list(self) -> None:
        stats = CurationStats()
        assert semantic_dedup([], stats) == []


# ===========================================================================
# I/O helpers
# ===========================================================================


class TestLoadWriteJsonl:
    def test_write_and_load_round_trip(self, tmp_path: Path) -> None:
        path = str(tmp_path / "test.jsonl")
        records = [{"id": "r1", "val": 1}, {"id": "r2", "val": 2}]
        count = write_jsonl(path, records)
        assert count == 2
        loaded = load_jsonl(path)
        assert len(loaded) == 2
        assert loaded[0]["id"] == "r1"
        assert loaded[1]["id"] == "r2"

    def test_load_respects_sample_limit(self, tmp_path: Path) -> None:
        path = str(tmp_path / "big.jsonl")
        records = [{"id": f"r{i}"} for i in range(20)]
        write_jsonl(path, records)
        loaded = load_jsonl(path, sample=5)
        assert len(loaded) == 5

    def test_load_skips_malformed_lines(self, tmp_path: Path) -> None:
        path = str(tmp_path / "malformed.jsonl")
        Path(path).write_text(
            "NOT JSON\n" + json.dumps({"id": "good"}) + "\n",
            encoding="utf-8",
        )
        loaded = load_jsonl(path)
        assert len(loaded) == 1
        assert loaded[0]["id"] == "good"

    def test_write_creates_parent_directories(self, tmp_path: Path) -> None:
        path = str(tmp_path / "nested" / "dir" / "out.jsonl")
        write_jsonl(path, [{"id": "x"}])
        assert os.path.exists(path)


class TestSaveReport:
    def test_writes_json_file(self, tmp_path: Path) -> None:
        report = {"status": "ok", "count": 42}
        out = save_report(report, str(tmp_path / "reports"), "test_report.json")
        assert os.path.exists(out)
        with open(out, encoding="utf-8") as fh:
            loaded = json.load(fh)
        assert loaded["status"] == "ok"
        assert loaded["count"] == 42

    def test_creates_reports_directory(self, tmp_path: Path) -> None:
        reports_dir = str(tmp_path / "new_reports")
        save_report({"data": "x"}, reports_dir, "r.json")
        assert os.path.isdir(reports_dir)


class _DummyStage:
    def __init__(self, *args: object, **kwargs: object) -> None:
        self.args = args
        self.kwargs = kwargs


class _DummyPipeline:
    last_instance: "_DummyPipeline" | None = None

    def __init__(self, name: str) -> None:
        self.name = name
        self.stages: list[object] = []
        self.ran = False
        _DummyPipeline.last_instance = self

    def add_stage(self, stage: object) -> None:
        self.stages.append(stage)

    def run(self) -> None:
        self.ran = True


class _DummyRayClient:
    def __init__(self) -> None:
        self.started = False
        self.stopped = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True


class _DummySocket:
    def settimeout(self, _: float) -> None:
        pass

    def connect(self, _: tuple[str, int]) -> None:
        pass

    def getsockname(self) -> tuple[str, int]:
        return ("127.0.0.1", 12345)

    def close(self) -> None:
        pass


class TestRunNemoFilterPipelineMocked:
    def test_pipeline_runs_with_mocked_dependencies(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(ncs, "_NEMO_AVAILABLE", True)
        dummy_client = _DummyRayClient()
        monkeypatch.setattr(ncs, "RayClient", lambda: dummy_client, raising=False)
        monkeypatch.setattr(ncs, "Pipeline", _DummyPipeline, raising=False)
        for attr in (
            "JsonlReader",
            "JsonlWriter",
            "Modify",
            "ScoreFilter",
            "WordCountFilter",
            "SymbolsToWordsFilter",
            "NonAlphaNumericFilter",
            "PunctuationFilter",
            "BoilerPlateStringFilter",
            "UrlsFilter",
            "RepeatedLinesFilter",
            "RepeatingTopNGramsFilter",
        ):
            monkeypatch.setattr(ncs, attr, _DummyStage, raising=False)
        monkeypatch.setattr(
            socket, "socket", lambda *args, **kwargs: _DummySocket()
        )

        input_path = tmp_path / "in.jsonl"
        input_path.write_text("{}", encoding="utf-8")
        output = tmp_path / "out"
        run_nemo_filter_pipeline(str(input_path), str(output))

        assert dummy_client.started
        assert dummy_client.stopped
        assert _DummyPipeline.last_instance is not None
        assert _DummyPipeline.last_instance.ran
        assert _DummyPipeline.last_instance.stages


class _DummyMinHash:
    def __init__(self, num_perm: int) -> None:
        self.num_perm = num_perm
        self.data: list[bytes] = []

    def update(self, value: bytes) -> None:
        self.data.append(value)


class _DummyMinHashLSH:
    def __init__(self, threshold: float, num_perm: int) -> None:
        self.threshold = threshold
        self.num_perm = num_perm
        self.keys: list[str] = []

    def insert(self, key: str, _: _DummyMinHash) -> None:
        self.keys.append(key)

    def query(self, _: _DummyMinHash) -> list[str]:
        return list(self.keys)


class TestSemanticDedupWithDatasketch:
    def test_datasketch_path_handles_duplicates(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(ncs, "_DATASKETCH_AVAILABLE", True)
        monkeypatch.setattr(ncs, "MinHash", _DummyMinHash, raising=False)
        monkeypatch.setattr(ncs, "MinHashLSH", _DummyMinHashLSH, raising=False)

        records = [{"assistant": "alpha alpha"}, {"assistant": "alpha alpha"}]
        stats = CurationStats()
        curated = semantic_dedup(
            records,
            stats,
            threshold=0.0,
            quality_cutoff=0.0,
            num_perm=2,
            shingle_k=3,
        )

        assert stats.semantic_duplicates == 1
        assert len(curated) == 1
