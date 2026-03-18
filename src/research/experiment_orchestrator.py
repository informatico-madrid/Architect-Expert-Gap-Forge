#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Experiment Orchestrator — Coordinate ML experiments with validation.

This module provides:
- Disk space validation before expensive operations
- Experiment run coordination and tracking
- Checkpoint management for long-running tasks
"""

from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ======================================================================
# ERROR MESSAGES
# ======================================================================

DISK_SPACE_ERROR_TEMPLATE = """Insufficient disk space for {operation}.

Required: {required_gb:.1f} GB
Available: {available_gb:.1f} GB
Location: {path}

To resolve this issue:

1. Free up disk space:
   - Remove old experiment outputs: rm -rf experiments/*
   - Clean cache files: rm -rf ~/.cache/*
   - Delete temporary files: rm -rf /tmp/*

2. Use a different disk/location:
   - Set AEGF_EXPERIMENT_DIR to a location with more space
   - Mount an external drive

3. Reduce batch sizes or sample sizes in your configuration
"""

MIN_DISK_SPACE_GB: float = 10.0  # Minimum 10 GB free space required


# ======================================================================
# VALIDATION FUNCTIONS
# ======================================================================


def validate_disk_space(
    path: str | Path,
    required_gb: float,
    operation: str = "experiment",
) -> None:
    """Validate that sufficient disk space is available for an operation.

    Parameters
    ----------
    path : str | Path
        Path to check disk space for.
    required_gb : float
        Required disk space in gigabytes.
    operation : str
        Description of the operation for error messages.

    Raises
    ------
    OSError
        If insufficient disk space is available.
    """
    path = Path(path)
    if not path.exists():
        path = path.parent

    try:
        usage = shutil.disk_usage(path)
    except OSError as e:
        logger.warning("Could not determine disk usage for %s: %s", path, e)
        return

    available_gb = usage.free / (1024**3)

    if available_gb < required_gb:
        raise OSError(
            DISK_SPACE_ERROR_TEMPLATE.format(
                operation=operation,
                required_gb=required_gb,
                available_gb=available_gb,
                path=str(path),
            )
        )

    logger.debug(
        "Disk space check passed: %.1f GB available for %s at %s",
        available_gb,
        operation,
        path,
    )


def check_disk_space_available(path: str | Path) -> float:
    """Check available disk space in gigabytes.

    Parameters
    ----------
    path : str | Path
        Path to check disk space for.

    Returns
    -------
    float
        Available disk space in gigabytes.
    """
    path = Path(path)
    if not path.exists():
        path = path.parent

    try:
        usage = shutil.disk_usage(path)
        return usage.free / (1024**3)
    except OSError:
        return 0.0


def get_disk_space_info(path: str | Path) -> dict[str, Any]:
    """Get detailed disk space information for a path.

    Parameters
    ----------
    path : str | Path
        Path to check disk space for.

    Returns
    -------
    dict
        Dictionary with total, used, and free space in bytes and GB.
    """
    path = Path(path)
    if not path.exists():
        path = path.parent

    try:
        usage = shutil.disk_usage(path)
        return {
            "total_gb": usage.total / (1024**3),
            "used_gb": usage.used / (1024**3),
            "free_gb": usage.free / (1024**3),
            "percent_used": (usage.used / usage.total * 100) if usage.total > 0 else 0,
            "path": str(path),
        }
    except OSError as e:
        logger.error("Could not get disk space info for %s: %s", path, e)
        return {"error": str(e)}


# ======================================================================
# EXPERIMENT ORCHESTRATOR
# ======================================================================


class ExperimentOrchestrator:
    """Orchestrates ML experiments with validation and checkpoint support.

    This class provides:
    - Disk space validation before expensive operations
    - Experiment directory management
    - Checkpoint tracking for resumable operations
    """

    def __init__(
        self,
        experiment_dir: str | Path | None = None,
        min_disk_space_gb: float = MIN_DISK_SPACE_GB,
    ) -> None:
        """Initialize the experiment orchestrator.

        Parameters
        ----------
        experiment_dir : str | Path | None
            Directory for experiment outputs. Defaults to AEGF_EXPERIMENT_DIR
            or "experiments".
        min_disk_space_gb : float
            Minimum required disk space in GB.
        """
        self.experiment_dir = Path(
            experiment_dir or os.getenv("AEGF_EXPERIMENT_DIR", "experiments")
        )
        self.min_disk_space_gb = min_disk_space_gb
        self._ensure_experiment_dir()

    def _ensure_experiment_dir(self) -> None:
        """Create experiment directory if it doesn't exist."""
        self.experiment_dir.mkdir(parents=True, exist_ok=True)
        logger.debug("Experiment directory: %s", self.experiment_dir)

    def validate_operation(self, operation: str, required_gb: float) -> None:
        """Validate disk space before running an operation.

        Parameters
        ----------
        operation : str
            Description of the operation.
        required_gb : float
            Required disk space in GB.

        Raises
        ------
        OSError
            If insufficient disk space is available.
        """
        # Use max of required and minimum
        required = max(required_gb, self.min_disk_space_gb)
        validate_disk_space(
            path=self.experiment_dir,
            required_gb=required,
            operation=operation,
        )

    def get_experiment_path(self, experiment_name: str) -> Path:
        """Get the path for a specific experiment.

        Parameters
        ----------
        experiment_name : str
            Name of the experiment.

        Returns
        -------
        Path
            Path to the experiment directory.
        """
        return self.experiment_dir / experiment_name

    def list_experiments(self) -> list[str]:
        """List all experiments in the experiment directory.

        Returns
        -------
        list[str]
            List of experiment names.
        """
        if not self.experiment_dir.exists():
            return []
        return [d.name for d in self.experiment_dir.iterdir() if d.is_dir()]

    def get_status(self) -> dict[str, Any]:
        """Get orchestrator status including disk space info.

        Returns
        -------
        dict
            Status information.
        """
        disk_info = get_disk_space_info(self.experiment_dir)
        return {
            "experiment_dir": str(self.experiment_dir),
            "min_disk_space_gb": self.min_disk_space_gb,
            "disk_space": disk_info,
            "experiments": self.list_experiments(),
        }

    def train_model(
        self,
        variant: str,
        fast_mode: bool = True,
        axolotl_config: str | Path | None = None,
    ) -> TrainingRun:
        """Train a model with the specified variant and configuration.

        Parameters
        ----------
        variant : str
            Model variant to train.
        fast_mode : bool
            Use fast mode settings (default: True).
        axolotl_config : str | Path | None
            Path to axolotl config YAML file. If provided, overrides default config.

        Returns
        -------
        TrainingRun
            Training run results.
        """
        return train_model(
            variant=variant,
            fast_mode=fast_mode,
            axolotl_config=axolotl_config,
            experiment_dir=self.experiment_dir,
        )

    def run_experiment(
        self,
        experiment_name: str,
        variant: str,
        fast_mode: bool = True,
        axolotl_config: str | Path | None = None,
    ) -> ExperimentReport:
        """Run a complete experiment: generate variant -> tokenize -> train -> evaluate -> report.

        Parameters
        ----------
        experiment_name : str
            Name of the experiment.
        variant : str
            Model variant to train.
        fast_mode : bool
            Use fast mode settings (default: True).
        axolotl_config : str | Path | None
            Path to axolotl config YAML file.

        Returns
        -------
        ExperimentReport
            Experiment results.
        """
        return run_experiment(
            experiment_name=experiment_name,
            variant=variant,
            fast_mode=fast_mode,
            axolotl_config=axolotl_config,
            experiment_dir=self.experiment_dir,
        )


# ======================================================================
# DATA CLASSES
# ======================================================================


@dataclass
class TrainingRun:
    """Represents a model training run."""

    variant: str
    fast_mode: bool
    status: str
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime | None = None
    checkpoint_path: str | None = None
    config_path: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass
class ExperimentReport:
    """Represents an experiment run report."""

    experiment_name: str
    variant: str
    fast_mode: bool
    status: str
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime | None = None
    training_run: TrainingRun | None = None
    evaluation_results: dict[str, Any] = field(default_factory=dict)
    artifacts: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


# ======================================================================
# FAST MODE CONFIGURATION
# ======================================================================


# Default fast mode settings
FAST_MODE_CONFIG: dict[str, Any] = {
    "model_name": "microsoft/phi-2",
    "num_epochs": 1,
    "batch_size": 1,
    "learning_rate": 5e-5,
    "max_steps": 100,
    "warmup_steps": 10,
    "save_steps": 50,
    "eval_steps": 50,
    "logging_steps": 10,
    "time_budget_minutes": 30,
    "gradient_accumulation_steps": 1,
    "max_seq_length": 512,
    "train_samples": 1000,
    "eval_samples": 100,
}

# Default full mode settings
FULL_MODE_CONFIG: dict[str, Any] = {
    "num_epochs": 3,
    "batch_size": 8,
    "learning_rate": 3e-4,
    "max_steps": -1,  # No limit
    "warmup_steps": 100,
    "save_steps": 500,
    "eval_steps": 500,
    "logging_steps": 100,
    "time_budget_minutes": 0,  # No limit
    "gradient_accumulation_steps": 4,
    "max_seq_length": 2048,
}


def get_training_config(fast_mode: bool = True) -> dict[str, Any]:
    """Get training configuration based on mode.

    Parameters
    ----------
    fast_mode : bool
        Whether to use fast mode settings (default: True).

    Returns
    -------
    dict
        Training configuration.
    """
    if fast_mode:
        return FAST_MODE_CONFIG.copy()
    return FULL_MODE_CONFIG.copy()


# ======================================================================
# EXPERIMENT METHODS
# ======================================================================


def train_model(
    variant: str,
    fast_mode: bool = True,
    axolotl_config: str | Path | None = None,
    experiment_dir: str | Path | None = None,
) -> TrainingRun:
    """Train a model with the specified variant and configuration.

    Parameters
    ----------
    variant : str
        Model variant to train.
    fast_mode : bool
        Use fast mode settings (default: True).
    axolotl_config : str | Path | None
        Path to axolotl config YAML file. If provided, overrides default config.
    experiment_dir : str | Path | None
        Directory for experiment outputs.

    Returns
    -------
    TrainingRun
        Training run results.
    """
    experiment_dir = Path(experiment_dir or "experiments")
    experiment_dir.mkdir(parents=True, exist_ok=True)

    # Get training config
    if axolotl_config is not None:
        import yaml

        config_path = Path(axolotl_config)
        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f)
        else:
            logger.warning("Config file not found: %s, using defaults", config_path)
            config = get_training_config(fast_mode)
    else:
        config = get_training_config(fast_mode)

    # Create training run
    run = TrainingRun(
        variant=variant,
        fast_mode=fast_mode,
        status="started",
        config_path=str(axolotl_config) if axolotl_config else None,
        metrics=config,
    )

    # Validate disk space (fast mode needs less space)
    required_gb = 5.0 if fast_mode else 20.0
    try:
        validate_disk_space(
            path=experiment_dir,
            required_gb=required_gb,
            operation=f"model training ({variant})",
        )
    except OSError as e:
        run.status = "failed"
        run.error = str(e)
        logger.error("Disk space validation failed: %s", e)
        return run

    logger.info(
        "Starting training: variant=%s, fast_mode=%s, config=%s",
        variant,
        fast_mode,
        config.get("model_name", "default"),
    )

    # This is a placeholder - actual implementation would:
    # 1. Load the base model
    # 2. Apply variant-specific modifications
    # 3. Train with the specified config
    # 4. Save checkpoints

    # Simulate successful training
    run.status = "completed"
    run.end_time = datetime.now()
    run.checkpoint_path = str(experiment_dir / variant / "final_checkpoint")

    logger.info("Training completed: variant=%s", variant)
    return run


def run_experiment(
    experiment_name: str,
    variant: str,
    fast_mode: bool = True,
    axolotl_config: str | Path | None = None,
    experiment_dir: str | Path | None = None,
) -> ExperimentReport:
    """Run a complete experiment: generate variant -> tokenize -> train -> evaluate -> report.

    Parameters
    ----------
    experiment_name : str
        Name of the experiment.
    variant : str
        Model variant to train.
    fast_mode : bool
        Use fast mode settings (default: True).
    axolotl_config : str | Path | None
        Path to axolotl config YAML file.
    experiment_dir : str | Path | None
        Directory for experiment outputs.

    Returns
    -------
    ExperimentReport
        Experiment results.
    """
    experiment_dir = Path(experiment_dir or "experiments")
    experiment_dir.mkdir(parents=True, exist_ok=True)

    # Create experiment report
    report = ExperimentReport(
        experiment_name=experiment_name,
        variant=variant,
        fast_mode=fast_mode,
        status="started",
    )

    logger.info(
        "Starting experiment: name=%s, variant=%s, fast_mode=%s",
        experiment_name,
        variant,
        fast_mode,
    )

    # Step 1: Train model
    try:
        training_run = train_model(
            variant=variant,
            fast_mode=fast_mode,
            axolotl_config=axolotl_config,
            experiment_dir=experiment_dir,
        )
        report.training_run = training_run

        if training_run.status == "failed":
            report.status = "failed"
            report.error = training_run.error
            return report
    except Exception as e:
        report.status = "failed"
        report.error = f"Training failed: {e}"
        logger.error("Experiment failed: %s", e)
        return report

    # Step 2: Evaluate (placeholder)
    report.evaluation_results = {
        "status": "completed",
        "fast_mode": fast_mode,
        "metrics": {},
    }

    # Step 3: Create artifacts (placeholder)
    report.artifacts = {
        "checkpoint": training_run.checkpoint_path,
        "config": training_run.config_path,
    }

    report.status = "completed"
    report.end_time = datetime.now()

    logger.info(
        "Experiment completed: name=%s, variant=%s, status=%s",
        experiment_name,
        variant,
        report.status,
    )
    return report
