#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Checkpoint and Progress Tracking Module
=========================================
Handles checkpoint/resume functionality and async-safe progress tracking
for the data factory pipeline.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from tqdm import tqdm

if TYPE_CHECKING:
    from typing import Any

from src.schemas.common import FragmentTypedDict

logger = logging.getLogger(__name__)


# ======================================================================
# TYPE ALIASES
# ======================================================================


CheckpointSet = frozenset[str]


# ======================================================================
# CHECKPOINT / RESUME
# ======================================================================


def make_checkpoint_key(
    frag: FragmentTypedDict | str, virtual_filename: str = "", rep: int | None = None
) -> str:
    """Generate deterministic checkpoint key for a fragment.

    Does NOT depend on example_type or evol_difficulty (which are random).
    This way, when resuming, the same fragment always generates the same key
    regardless of what type it was assigned before the crash.

    Args:
        frag: Fragment dictionary with 'name' and 'virtual_filename' keys, OR
              a string (frag_name) if virtual_filename is provided separately.
        virtual_filename: Optional virtual filename (used if frag is a string).
        rep: Optional repetition number for multi-sample generation.

    Returns:
        A 16-character MD5 hash suitable for use as a checkpoint key.
    """
    # Handle both old signature (frag_name, virtual_filename) and new (frag_dict)
    if isinstance(frag, str):
        frag_name = frag
    else:
        frag_name = frag.get("name", "")
        virtual_filename = frag.get("virtual_filename", "")
    raw = f"{frag_name}::{virtual_filename}"
    if rep is not None:
        raw += f"::rep{rep}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def load_checkpoint(output_path: Path, rejected_path: Path) -> CheckpointSet:
    """Load checkpoint keys from existing JSONL files.

    Scans both the output (accepted) and rejected files to avoid
    reprocessing either.

    Args:
        output_path: Path to the accepted samples JSONL file.
        rejected_path: Path to the rejected samples JSONL file.

    Returns:
        Frozenset of already-processed checkpoint keys.
    """
    done_keys: set[str] = set()
    for path in [output_path, rejected_path]:
        if not path.exists():
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        # Accepted: metadata.checkpoint_key
                        ck = record.get("metadata", {}).get("checkpoint_key")
                        # Rejected: checkpoint_key at top level
                        if not ck:
                            ck = record.get("checkpoint_key")
                        if ck:
                            done_keys.add(ck)
                    except json.JSONDecodeError:
                        logger.warning(
                            "Checkpoint: invalid JSON at %s line %d", path, line_num
                        )
        except Exception as e:
            logger.warning("Checkpoint: error reading %s: %s", path, e)
    return frozenset(done_keys)


# ======================================================================
# ASYNC-SAFE FILE WRITERS
# ======================================================================


class AsyncFileWriter:
    """Thread-safe JSONL writer with asyncio lock."""

    def __init__(self, path: Path) -> None:
        """Initialize the async file writer.

        Args:
            path: Path to the output JSONL file.
        """
        self.path = path
        self._lock = asyncio.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    async def write(self, record: dict[str, Any]) -> None:
        """Write a record to the JSONL file.

        Args:
            record: Dictionary to write as JSON line.
        """
        async with self._lock:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ======================================================================
# PROGRESS TRACKER
# ======================================================================


class ProgressTracker:
    """Async-safe progress tracker with tqdm."""

    def __init__(self, total: int, mode: str = "code") -> None:
        """Initialize the progress tracker.

        Args:
            total: Total number of samples to process.
            mode: Either "code" or "theory" for different progress display.
        """
        self.total = total
        self.mode = mode
        self.accepted = 0
        self.rejected = 0
        self.by_type: dict[str, int] = {
            "nominal": 0,
            "contrast": 0,
            "error_recovery": 0,
            "theory": 0,
        }
        self.by_difficulty: dict[str, int] = {"easy": 0, "medium": 0, "hard": 0}
        self.legacy_detected = 0
        self.gold_injected = 0
        self.gold_skipped = 0
        self._lock = asyncio.Lock()
        desc = "V11 Theory" if mode == "theory" else "V11 Generating"
        self.pbar = tqdm(
            total=total, desc=desc, unit="sample", ncols=220, dynamic_ncols=False
        )

    async def record(
        self,
        status: str,
        example_type: str,
        difficulty: str | None,
        gold_injected: bool = True,
        has_legacy: bool = False,
    ) -> None:
        """Record a sample result.

        Args:
            status: Either "accepted" or "rejected".
            example_type: Type of example (nominal, contrast, error_recovery, theory).
            difficulty: Evol-instruct difficulty level (easy, medium, hard) or None.
            gold_injected: Whether gold code was injected.
            has_legacy: Whether legacy patterns were detected.
        """
        async with self._lock:
            if status == "accepted":
                self.accepted += 1
                self.by_type[example_type] = self.by_type.get(example_type, 0) + 1
                if difficulty:
                    self.by_difficulty[difficulty] = (
                        self.by_difficulty.get(difficulty, 0) + 1
                    )
                if has_legacy:
                    self.legacy_detected += 1
                if gold_injected:
                    self.gold_injected += 1
                else:
                    self.gold_skipped += 1
            else:
                self.rejected += 1
            self.pbar.update(1)
            self.pbar.set_postfix_str(
                f"OK={self.accepted}, KO={self.rejected}, "
                f"N={self.by_type.get('nominal', 0)}, "
                f"C={self.by_type.get('contrast', 0)}, "
                f"E={self.by_type.get('error_recovery', 0)}, "
                f"T={self.by_type.get('theory', 0)}, "
                f"GI={self.gold_injected}, GS={self.gold_skipped}"
            )

    def close(self) -> None:
        """Close the progress bar."""
        self.pbar.close()

    def summary(self) -> str:
        """Generate a summary report.

        Returns:
            Formatted string with progress statistics.
        """
        lines = [
            f"\n{'=' * 60}",
            f"SUMMARY V10.0 {'THEORY' if self.mode == 'theory' else 'ASYNC DIVERSIFIED'}",
            f"{'=' * 60}",
            f"  Total processed: {self.accepted + self.rejected}",
            f"  Accepted:        {self.accepted}",
            f"  Rejected:        {self.rejected}",
            "",
            "  By type:",
            f"    Nominal (Evol):   {self.by_type.get('nominal', 0)}",
            f"    Contrast 23->26:  {self.by_type.get('contrast', 0)}",
            f"    Error Recovery:   {self.by_type.get('error_recovery', 0)}",
            f"    Theory (Doctrine):{self.by_type.get('theory', 0)}",
        ]
        if self.mode != "theory":
            lines += [
                "",
                "  Evol-Instruct breakdown:",
                f"    Easy:   {self.by_difficulty.get('easy', 0)}",
                f"    Medium: {self.by_difficulty.get('medium', 0)}",
                f"    Hard:   {self.by_difficulty.get('hard', 0)}",
                "",
                "  ANTI-SCHIZOPHRENIA FILTER:",
                f"    Legacy detected in: {self.legacy_detected} fragments",
                f"    Gold Injection OK:  {self.gold_injected} (clean 2026 code)",
                f"    Gold Injection SKIP:{self.gold_skipped} (legacy -> model generates 2026)",
            ]
        lines.append(f"{'=' * 60}")
        return "\n".join(lines)
