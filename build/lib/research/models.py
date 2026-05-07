# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0
"""
Data models for rapid experimentation pipeline.

This module contains dataclasses for managing experiment variants, training runs,
and related experiment tracking.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class ExperimentVariant:
    """Unique combination of dataset parameters for experimentation.

    Attributes:
        name: Unique identifier (e.g., "dedup_0.95_gold_0.1")
        dedup_threshold: Fuzzy deduplication threshold (0.0-1.0)
        gold_injection_rate: Percentage of gold records to inject (0.0-1.0)
        min_length: Minimum sequence length
        sample_weighting: Weighting strategy ("uniform", "length-weighted", "quality-weighted")
        created_at: Timestamp of creation
        created_by: Creator identifier (e.g., "researcher@company.com")
        parent_variant: Parent variant name for iterative experiments
    """

    name: str
    dedup_threshold: float
    gold_injection_rate: float
    min_length: int
    sample_weighting: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    parent_variant: Optional[str] = None

    @property
    def description(self) -> str:
        """Human-readable description of the variant parameters."""
        return f"dedup={self.dedup_threshold:.2f},gold={self.gold_injection_rate:.2f},min_len={self.min_length}"


@dataclass(slots=True, frozen=True)
class TrainingRun:
    """Single training execution with metrics and artifacts.

    Attributes:
        run_id: Unique identifier (UUID or deterministic hash)
        variant_name: Parent ExperimentVariant name
        val_bpb: Validation bits per byte (lower is better)
        peak_vram_mb: Peak VRAM usage in MB
        mfu_percent: Model FLOPs Utilization percentage
        total_tokens_M: Total tokens processed in millions
        axolotl_config_path: Path to Axolotl YAML config
        tokenizer_path: Path to tokenizer files
        checkpoint_path: Path to model checkpoint
        started_at: Training start timestamp
        completed_at: Training completion timestamp
        duration_seconds: Training duration in seconds
        model_checkpoint: Path to model.safetensors
        tokenizer_files: List of tokenizer files (vocab.json, merges.txt, etc.)
    """

    run_id: str
    variant_name: str
    val_bpb: float
    peak_vram_mb: float
    mfu_percent: float
    total_tokens_M: float
    axolotl_config_path: str
    tokenizer_path: str
    checkpoint_path: str
    started_at: datetime
    completed_at: datetime
    duration_seconds: float
    model_checkpoint: str
    tokenizer_files: list[str] = field(default_factory=list)
    metrics: dict[str, object] = field(default_factory=dict)

    @property
    def efficiency_score(self) -> float:
        """Higher is better: low BPB, high MFU, low VRAM.

        Formula: (1.0 / val_bpb) * mfu_percent / (peak_vram_mb / 1000)
        """
        return (1.0 / self.val_bpb) * self.mfu_percent / (self.peak_vram_mb / 1000)


@dataclass
class ExperimentReport:
    """Represents an experiment run report.

    Attributes:
        experiment_name: Name of the experiment
        variant: Variant name used
        fast_mode: Whether fast mode was enabled
        status: Experiment status (started, running, completed, failed)
        start_time: Experiment start timestamp
        end_time: Experiment end timestamp
        training_run: Associated training run data
        evaluation_results: Dictionary of evaluation metrics
        artifacts: Dictionary of produced artifacts
        error: Error message if experiment failed
    """

    experiment_name: str
    variant: str
    fast_mode: bool
    status: str
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime | None = None
    training_run: Optional["TrainingRun"] = None
    evaluation_results: dict[str, object] = field(default_factory=dict)
    artifacts: dict[str, object] = field(default_factory=dict)
    error: Optional[str] = None
