#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Integration-style tests for nemo_curator_suite main() CLI entrypoints.

These use small temporary JSONL inputs to exercise the control flow
without requiring the NeMo container or datasketch dependencies.
"""

from __future__ import annotations

from pathlib import Path
import json

from src.curation import nemo_curator_suite as ncs


def make_jsonl(path: Path, records: list) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def test_main_exact_dedup_dry_run(tmp_path: Path) -> None:
    inp = tmp_path / "in.jsonl"
    out = tmp_path / "out.jsonl"
    rec = {"conversation": [{"role": "assistant", "content": "x"}], "id": "1"}
    make_jsonl(inp, [rec, rec])

    # Dry-run (no --apply): should return 0 and not write output file
    rc = ncs.main(
        ["--input", str(inp), "--output", str(out), "--exact-dedup"]
    )  # no --apply -> dry-run
    assert rc == 0
    assert not out.exists()


def test_main_filter_not_installed_returns_error(tmp_path: Path) -> None:
    inp = tmp_path / "in2.jsonl"
    out = tmp_path / "out2.jsonl"
    make_jsonl(inp, [{"conversation": []}])

    # Request NeMo filter when environment lacks nemo-curator → error code 1
    rc = ncs.main(["--input", str(inp), "--output", str(out), "--filter"])
    assert rc == 1
