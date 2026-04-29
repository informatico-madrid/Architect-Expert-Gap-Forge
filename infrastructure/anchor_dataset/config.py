#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0
"""Configuration for the anchor dataset builder."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AnchorsConfig:
    """Frozen configuration for the anchor dataset builder."""

    total_samples: int = 50
    output_dir: str = "outputs"
    provider: str = "vllm"
    vllm_url: str = "http://localhost:8000"
    temperature: float = 0.4
    max_tokens: int = 8192
    count: int = 50
    domain_distribution: str = '{"home_assistant": 0.4, "php_legacy": 0.3, "generic_domain": 0.2, "other": 0.1}'
    difficulty_distribution: str = '{"easy": 0.3, "medium": 0.5, "hard": 0.2}'
    seed: int = 42
    resume: bool = False
    no_overwrite: bool = False
    output_file: str = "anchor_dataset.jsonl"

    def __post_init__(self) -> None:
        """Validate from env var overrides after construction."""
        if os.environ.get("ANCHORS_TOTAL_SAMPLES"):
            object.__setattr__(
                self, "total_samples", int(os.environ["ANCHORS_TOTAL_SAMPLES"])
            )
        if os.environ.get("ANCHORS_OUTPUT_DIR"):
            object.__setattr__(self, "output_dir", os.environ["ANCHORS_OUTPUT_DIR"])
        if os.environ.get("ANCHORS_PROVIDER"):
            object.__setattr__(self, "provider", os.environ["ANCHORS_PROVIDER"])
        if os.environ.get("ANCHORS_VLLM_URL"):
            object.__setattr__(self, "vllm_url", os.environ["ANCHORS_VLLM_URL"])
        if os.environ.get("ANCHORS_TEMPERATURE"):
            object.__setattr__(
                self, "temperature", float(os.environ["ANCHORS_TEMPERATURE"])
            )
        if os.environ.get("ANCHORS_MAX_TOKENS"):
            object.__setattr__(
                self, "max_tokens", int(os.environ["ANCHORS_MAX_TOKENS"])
            )
        if os.environ.get("ANCHORS_SEED"):
            object.__setattr__(self, "seed", int(os.environ["ANCHORS_SEED"]))


@dataclass
class QualitySettings:
    """Mutable quality-circuit-breaker settings."""

    check_threshold: float = 0.3
    cb_threshold: float = 0.2
    cb_batch_size: int = 10
    cb_consecutive_pass: int = 10


def apply_calibration(quality_score: float) -> float:
    """Return calibrated quality score.

    v0 POC: identity function. Replace with real calibration later.
    """
    return quality_score
