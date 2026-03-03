#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""AEGF Audit Sampling — Stratified dataset sampling utilities.

Single Responsibility: load raw JSONL records and draw a balanced,
reproducible stratified sample grouped by ``example_type``.

Public API
----------
- ``load_dataset`` — parse a JSONL file into raw records.
- ``stratified_sample`` — draw a balanced sample from raw records.
"""
from __future__ import annotations

import json
import logging
import random
from collections import defaultdict
from typing import Any

from src.audit.schema import SampleRecord

__all__ = ["load_dataset", "stratified_sample"]

logger = logging.getLogger(__name__)


def load_dataset(path: str) -> list[dict[str, Any]]:
    """Load a JSONL dataset into memory.

    Skips malformed lines with a warning instead of aborting.

    Args:
        path: Filesystem path to the ``.jsonl`` file.

    Returns:
        List of raw record dicts.
    """
    records: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                logger.warning("Skipping malformed line %d: %s", line_no, exc)
    logger.info("Loaded %d records from %s", len(records), path)
    return records


def stratified_sample(
    records: list[dict[str, Any]],
    sample_size: int = 5,
    seed: int = 42,
) -> list[SampleRecord]:
    """Extract a balanced sample stratified by ``example_type``.

    Algorithm:
    1. Distribute ``sample_size // n_types`` to each type (capped by bucket size).
    2. Donate over-allocated slots (surplus) back to the pool.
    3. Redistribute surplus + remainder to the largest buckets first.

    Args:
        records: Raw record dicts as returned by ``load_dataset``.
        sample_size: Target number of records to return.
        seed: RNG seed for deterministic draws.

    Returns:
        List of :class:`~src.audit.schema.SampleRecord` instances.
    """
    rng = random.Random(seed)

    # Bucket by example_type
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for rec in records:
        et = rec.get("metadata", {}).get("example_type", "unknown")
        buckets[et].append(rec)

    present_types = sorted(buckets.keys())
    n_types = len(present_types)
    if n_types == 0 or sample_size == 0:
        return []

    base_quota = sample_size // n_types
    remainder = sample_size % n_types

    # First pass — allocate base quota (capped by bucket size)
    allocation: dict[str, int] = {}
    surplus = 0
    for et in present_types:
        avail = len(buckets[et])
        alloc = min(base_quota, avail)
        allocation[et] = alloc
        surplus += base_quota - alloc

    # Second pass — distribute surplus + remainder to largest buckets
    leftover = surplus + remainder
    for et in sorted(present_types, key=lambda t: len(buckets[t]), reverse=True):
        if leftover <= 0:
            break
        can_add = len(buckets[et]) - allocation[et]
        add = min(can_add, leftover)
        allocation[et] += add
        leftover -= add

    # Draw samples
    samples: list[SampleRecord] = []
    for et in present_types:
        pool = buckets[et]
        rng.shuffle(pool)
        for rec in pool[: allocation[et]]:
            meta = rec.get("metadata", {})
            conv = rec.get("conversation", []) or rec.get("conversations", []) or []
            user_msg = ""
            asst_msg = ""
            for t in conv:
                role = (t.get("role") or t.get("from") or "").lower()
                content = (t.get("content") or t.get("value") or "").strip()
                if not content:
                    continue
                if "user" in role and not user_msg:
                    user_msg = content
                if ("assistant" in role or "bot" in role) and not asst_msg:
                    asst_msg = content
                if user_msg and asst_msg:
                    break
            samples.append(
                SampleRecord(
                    id=rec.get("id", f"unknown_{len(samples)}"),
                    example_type=et,
                    evol_difficulty=meta.get("evol_difficulty", "unknown"),
                    fragment_name=meta.get("fragment_name", ""),
                    source_file=meta.get("source_file", ""),
                    user_prompt=user_msg,
                    reference_response=asst_msg,
                    gold_injected=meta.get("gold_injected", False),
                    ldi=meta.get("ldi", 0.0),
                    reference_standards=meta.get("reference_standards", ""),
                    gap_analysis=meta.get("gap_analysis", ""),
                )
            )

    missing_standards = [s.id for s in samples if not (s.reference_standards and s.reference_standards.strip())]
    missing_gaps = [s.id for s in samples if not (s.gap_analysis and s.gap_analysis.strip())]
    if missing_standards or missing_gaps:
        logger.info(
            "Sample contains records missing domain metadata; will inject later: "
            "reference_standards=%s; gap_analysis=%s",
            missing_standards or "-",
            missing_gaps or "-",
        )

    logger.info(
        "Sampled %d records — distribution: %s",
        len(samples),
        {et: allocation[et] for et in present_types},
    )
    return samples
