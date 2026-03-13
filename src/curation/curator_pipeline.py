#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""AEGF — Curator Pipeline Module.

Orchestrator for the NeMo Curator Suite pipeline, including CurationStats,
I/O helpers, and the NeMo filter pipeline runner.
"""

from __future__ import annotations

import json
import logging
import os
import socket
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List

from src.schemas.common import RawRecord

logger = logging.getLogger(__name__)

# Default constants
DEFAULT_MIN_WORDS: int = 20
DEFAULT_MAX_SYMBOL_RATIO: float = 0.50
DEFAULT_MAX_NON_ALPHA_RATIO: float = 0.65
DEFAULT_MAX_URL_RATIO: float = 0.30
DEFAULT_MAX_NO_ENDMARK_RATIO: float = 0.99
DEFAULT_MAX_BOILERPLATE_RATIO: float = 0.85
DEFAULT_MAX_REPEATED_LINES: float = 0.90
DEFAULT_MAX_NGRAM_RATIO: float = 0.35
DEFAULT_NGRAM_SIZE: int = 3

DEFAULT_REPORTS_DIR: str = "data/reports"

# Optional dependency guards
_NEMO_AVAILABLE = False
_DATASKETCH_AVAILABLE = False

try:
    from datasketch import MinHash, MinHashLSH  # type: ignore

    _DATASKETCH_AVAILABLE = True
except ImportError:
    pass

try:
    from nemo_curator.core.client import RayClient  # type: ignore
    from nemo_curator.pipeline import Pipeline  # type: ignore
    from nemo_curator.stages.text.io.reader import JsonlReader  # type: ignore
    from nemo_curator.stages.text.io.writer import JsonlWriter  # type: ignore
    from nemo_curator.stages.text.modules import ScoreFilter, Modify  # type: ignore
    from nemo_curator.stages.text.filters import (  # type: ignore
        WordCountFilter,
        RepeatingTopNGramsFilter,
        SymbolsToWordsFilter,
        NonAlphaNumericFilter,
        PunctuationFilter,
        BoilerPlateStringFilter,
        UrlsFilter,
        RepeatedLinesFilter,
    )

    _NEMO_AVAILABLE = True
except ImportError:
    pass


# ===========================================================================
# CurationStats — tracks all removal reasons across phases
# ===========================================================================


@dataclass
class CurationStats:
    """Statistics accumulator for curation pipeline.

    Note: Not frozen because it requires explicit mutation during the curation
    lifecycle - counts are incremented as each phase processes records.
    This is an intentional mutable accumulator pattern, not a data record.
    """

    total_input: int = 0
    # Phase 0
    exact_duplicates: int = 0
    # Phase 1
    nemo_filtered: int = 0
    # Phase 2
    invalid_syntax: int = 0
    shallow_thinking: int = 0
    meta_speech: int = 0
    low_ldi: int = 0
    # Phase 3
    low_quality_score: int = 0
    semantic_duplicates: int = 0
    # Output
    total_output: int = 0

    def as_dict(self) -> Dict[str, Any]:
        total_removed = (
            self.exact_duplicates
            + self.nemo_filtered
            + self.invalid_syntax
            + self.shallow_thinking
            + self.meta_speech
            + self.low_ldi
            + self.low_quality_score
            + self.semantic_duplicates
        )
        retention = (
            round(100.0 * self.total_output / self.total_input, 2)
            if self.total_input
            else 0.0
        )
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "total_input": self.total_input,
            "removed": {
                "exact_duplicates": self.exact_duplicates,
                "nemo_filtered": self.nemo_filtered,
                "invalid_syntax": self.invalid_syntax,
                "shallow_thinking": self.shallow_thinking,
                "meta_speech": self.meta_speech,
                "low_ldi": self.low_ldi,
                "low_quality_score": self.low_quality_score,
                "semantic_duplicates": self.semantic_duplicates,
                "total": total_removed,
            },
            "total_output": self.total_output,
            "retention_pct": retention,
        }

    def print_report(self) -> None:
        d = self.as_dict()
        r = d["removed"]
        print("\n" + "=" * 70)
        print("  AEGF NeMo Curator Suite — Curation Report")
        print("=" * 70)
        print(f"  Input records  : {d['total_input']:>8,}")
        print(f"  -- Exact duplicates        : {r['exact_duplicates']:>6,}")
        print(f"  -- NeMo quality filter     : {r['nemo_filtered']:>6,}")
        print(f"  -- Invalid syntax          : {r['invalid_syntax']:>6,}")
        print(f"  -- Shallow think (<chars)  : {r['shallow_thinking']:>6,}")
        print(f"  -- Meta-speech reasoning   : {r['meta_speech']:>6,}")
        print(f"  -- Low LDI ratio           : {r['low_ldi']:>6,}")
        print(f"  -- Low heuristic quality   : {r['low_quality_score']:>6,}")
        print(f"  -- Semantic duplicates     : {r['semantic_duplicates']:>6,}")
        print(f"  Total removed  : {r['total']:>8,}")
        print(
            f"  Output records : {d['total_output']:>8,}  (retention {d['retention_pct']}%)"
        )
        print("=" * 70)


# ===========================================================================
# Phase 1 — NeMo Curator quality filtering (requires container)
# ===========================================================================


class ConversationExtractor:
    """NeMo Modifier: extract assistant turns into a side column ``filter_text``."""

    def __init__(self) -> None:
        self.__name__ = "ConversationExtractor"

    def __call__(self, conversation_list: Any) -> str:
        if not conversation_list or not isinstance(conversation_list, list):
            return ""
        return " ".join(
            m.get("content", "")
            for m in conversation_list
            if isinstance(m, dict) and m.get("role") == "assistant"
        )


def run_nemo_filter_pipeline(
    input_path: str,
    output_path: str,
    *,
    min_words: int = DEFAULT_MIN_WORDS,
    max_symbol_ratio: float = DEFAULT_MAX_SYMBOL_RATIO,
    max_non_alpha_ratio: float = DEFAULT_MAX_NON_ALPHA_RATIO,
    max_url_ratio: float = DEFAULT_MAX_URL_RATIO,
    max_no_endmark_ratio: float = DEFAULT_MAX_NO_ENDMARK_RATIO,
    max_boilerplate_ratio: float = DEFAULT_MAX_BOILERPLATE_RATIO,
    max_repeated_lines: float = DEFAULT_MAX_REPEATED_LINES,
    max_ngram_ratio: float = DEFAULT_MAX_NGRAM_RATIO,
    ngram_size: int = DEFAULT_NGRAM_SIZE,
) -> None:
    """Run the NeMo Curator distributed quality-filter pipeline.

    Requires nemo-curator + Ray (pre-installed in the aegf_curator container).
    """
    if not _NEMO_AVAILABLE:
        raise RuntimeError(
            "nemo-curator is not installed.\n"
            "Run inside the aegf_curator container:\n"
            "  cd deploy/docker && docker compose up -d curator\n"
            "  docker exec -it aegf_curator bash"
        )
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    logger.info("Phase 1 -- NeMo Curator filter pipeline: %s", input_path)
    client = RayClient()
    client.start()

    # Provide a helpful hint about the Ray dashboard addresses so users
    # running the script inside the `aegf_curator` container know how
    # to reach the UI from the host or another machine.
    def _detect_local_ip() -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.5)
            # doesn't actually send data; just determines outbound iface
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            try:
                return socket.gethostbyname(socket.gethostname())
            except Exception:
                return "127.0.0.1"

    container_ip = _detect_local_ip()
    logger.info("Ray dashboard (inside container): http://127.0.0.1:8265")
    logger.info("Ray dashboard (container IP): http://%s:8265", container_ip)
    if os.environ.get("RAY_DASHBOARD_HOST") == "0.0.0.0":
        logger.info(
            "If you need external access, publish port 8265 in docker-compose and use the server IP: http://<SERVER_IP>:8265"
        )
    else:
        logger.info(
            "If the dashboard is not reachable from outside, ensure RAY_DASHBOARD_HOST=0.0.0.0 and that port 8265 is published in docker-compose."
        )
    try:
        pipeline = Pipeline(name="aegf_curation_filter_v1")
        pipeline.add_stage(JsonlReader(file_paths=input_path))
        pipeline.add_stage(
            Modify(
                modifier_fn=ConversationExtractor(),
                input_fields=["conversation"],
                output_fields=["filter_text"],
            )
        )
        filter_stages = [
            ScoreFilter(
                filter_obj=WordCountFilter(min_words=min_words),
                text_field="filter_text",
            ),
            ScoreFilter(
                filter_obj=SymbolsToWordsFilter(
                    max_symbol_to_word_ratio=max_symbol_ratio
                ),
                text_field="filter_text",
            ),
            ScoreFilter(
                filter_obj=NonAlphaNumericFilter(
                    max_non_alpha_numeric_to_text_ratio=max_non_alpha_ratio
                ),
                text_field="filter_text",
            ),
            ScoreFilter(
                filter_obj=UrlsFilter(max_url_to_text_ratio=max_url_ratio),
                text_field="filter_text",
            ),
            ScoreFilter(
                filter_obj=PunctuationFilter(
                    max_num_sentences_without_endmark_ratio=max_no_endmark_ratio
                ),
                text_field="filter_text",
            ),
            ScoreFilter(
                filter_obj=BoilerPlateStringFilter(
                    max_boilerplate_string_ratio=max_boilerplate_ratio
                ),
                text_field="filter_text",
            ),
            ScoreFilter(
                filter_obj=RepeatedLinesFilter(
                    max_repeated_line_fraction=max_repeated_lines
                ),
                text_field="filter_text",
            ),
            ScoreFilter(
                filter_obj=RepeatingTopNGramsFilter(
                    n=ngram_size, max_repeating_ngram_ratio=max_ngram_ratio
                ),
                text_field="filter_text",
            ),
        ]
        for stage in filter_stages:
            pipeline.add_stage(stage)
        pipeline.add_stage(JsonlWriter(path=output_path))
        logger.info("Running NeMo pipeline (%d filter stages)", len(filter_stages))
        pipeline.run()
        logger.info("NeMo filter complete --> %s", output_path)
    except Exception as exc:
        logger.error("NeMo filter pipeline error: %s", exc)
        raise
    finally:
        client.stop()


# ===========================================================================
# I/O helpers
# ===========================================================================


def load_jsonl(path: str, sample: int = 0) -> List[RawRecord]:
    """Load a JSONL file; optionally limit to first ``sample`` records."""
    records: List[RawRecord] = []
    with open(path, "r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            if sample and len(records) >= sample:
                break
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                logger.debug("Skipping malformed JSON at line %d: %s", lineno, exc)
    return records


def write_jsonl(path: str, records: Iterable[RawRecord]) -> int:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    count = 0
    with open(path, "w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            count += 1
    return count


def save_report(report: Dict[str, Any], reports_dir: str, filename: str) -> str:
    os.makedirs(reports_dir, exist_ok=True)
    out = os.path.join(reports_dir, filename)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    return out
