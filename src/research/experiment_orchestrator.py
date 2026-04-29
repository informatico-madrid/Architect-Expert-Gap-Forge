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
- Results registration in TSV format for experiment tracking
"""

from __future__ import annotations

import csv
import logging
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from src.research.models import ExperimentReport

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
    - Results registration in TSV format
    """

    def __init__(
        self,
        experiment_dir: str | Path | None = None,
        min_disk_space_gb: float = MIN_DISK_SPACE_GB,
        results_dir: str | Path | None = None,
    ) -> None:
        """Initialize the experiment orchestrator.

        Parameters
        ----------
        experiment_dir : str | Path | None
            Directory for experiment outputs. Defaults to AEGF_EXPERIMENT_DIR
            or "experiments".
        min_disk_space_gb : float
            Minimum required disk space in GB.
        results_dir : str | Path | None
            Directory for results TSV file. Defaults to experiment_dir.
        """
        self.experiment_dir = Path(
            experiment_dir or os.getenv("AEGF_EXPERIMENT_DIR", "experiments")
        )
        self.min_disk_space_gb = min_disk_space_gb
        self.results_dir = results_dir or self.experiment_dir
        self._ensure_experiment_dir()
        self._results_registry: ResultsRegistry | None = None

    @property
    def results_registry(self) -> ResultsRegistry:
        """Get or create the results registry.

        Returns
        -------
        ResultsRegistry
            Results registry instance.
        """
        if self._results_registry is None:
            self._results_registry = ResultsRegistry(results_dir=self.results_dir)
        return self._results_registry

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
    """Represents an in-progress model training run.

    Note: This is a mutable class for tracking ongoing training operations.
    For completed training runs with metrics, see src.research.models.TrainingRun.
    """

    variant: str
    fast_mode: bool
    status: str
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime | None = None
    checkpoint_path: str | None = None
    config_path: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


# ======================================================================
# RESULTS REGISTRY (TSV/DB)
# ======================================================================


class ResultsRegistry:
    """Registry for experiment results stored in TSV format.

    This class provides:
    - TSV-based storage for experiment results
    - Metadata tracking for each experiment variant
    - Query and export capabilities
    """

    DEFAULT_RESULTS_FILE = "experiment_results.tsv"

    def __init__(self, results_dir: str | Path | None = None) -> None:
        """Initialize the results registry.

        Parameters
        ----------
        results_dir : str | Path | None
            Directory for storing results. Defaults to AEGF_RESULTS_DIR
            or "experiments".
        """
        self.results_dir = Path(
            results_dir or os.getenv("AEGF_RESULTS_DIR", "experiments")
        )
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.results_file = self.results_dir / self.DEFAULT_RESULTS_FILE
        self._init_results_file()

    def _init_results_file(self) -> None:
        """Initialize the results TSV file with headers if it doesn't exist."""
        if not self.results_file.exists():
            headers = [
                "experiment_name",
                "variant",
                "fast_mode",
                "status",
                "start_time",
                "end_time",
                "duration_seconds",
                "val_bpb",
                "peak_vram_mb",
                "mfu_percent",
                "total_tokens_M",
                "num_epochs",
                "batch_size",
                "learning_rate",
                "max_steps",
                "train_samples",
                "eval_samples",
                "checkpoint_path",
                "error",
            ]
            with open(self.results_file, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=headers, delimiter="\t")
                writer.writeheader()

    def register_result(
        self,
        experiment_name: str,
        variant: str,
        fast_mode: bool,
        status: str,
        start_time: datetime,
        end_time: datetime | None = None,
        metrics: dict[str, Any] | None = None,
        config: dict[str, Any] | None = None,
        checkpoint_path: str | None = None,
        error: str | None = None,
    ) -> None:
        """Register an experiment result in the TSV file.

        Parameters
        ----------
        experiment_name : str
            Name of the experiment.
        variant : str
            Model variant tested.
        fast_mode : bool
            Whether fast mode was used.
        status : str
            Experiment status (completed, failed, running).
        start_time : datetime
            Experiment start time.
        end_time : datetime | None
            Experiment end time.
        metrics : dict | None
            Evaluation metrics (val_bpb, peak_vram_mb, mfu_percent, etc.).
        config : dict | None
            Training configuration used.
        checkpoint_path : str | None
            Path to model checkpoint.
        error : str | None
            Error message if failed.
        """
        # Calculate duration
        duration_seconds: float | None = None
        if end_time and start_time:
            duration_seconds = (end_time - start_time).total_seconds()

        # Extract metrics with defaults
        val_bpb = None
        peak_vram_mb = None
        mfu_percent = None
        total_tokens_M = None
        if metrics:
            val_bpb = metrics.get("val_bpb")
            peak_vram_mb = metrics.get("peak_vram_mb")
            mfu_percent = metrics.get("mfu_percent")
            total_tokens_M = metrics.get("total_tokens_M")

        # Extract config with defaults
        num_epochs = None
        batch_size = None
        learning_rate = None
        max_steps = None
        train_samples = None
        eval_samples = None
        if config:
            num_epochs = config.get("num_epochs")
            batch_size = config.get("batch_size")
            learning_rate = config.get("learning_rate")
            max_steps = config.get("max_steps")
            train_samples = config.get("train_samples")
            eval_samples = config.get("eval_samples")

        row = {
            "experiment_name": experiment_name,
            "variant": variant,
            "fast_mode": str(fast_mode),
            "status": status,
            "start_time": start_time.isoformat() if start_time else "",
            "end_time": end_time.isoformat() if end_time else "",
            "duration_seconds": duration_seconds
            if duration_seconds is not None
            else "",
            "val_bpb": val_bpb if val_bpb is not None else "",
            "peak_vram_mb": peak_vram_mb if peak_vram_mb is not None else "",
            "mfu_percent": mfu_percent if mfu_percent is not None else "",
            "total_tokens_M": total_tokens_M if total_tokens_M is not None else "",
            "num_epochs": num_epochs if num_epochs is not None else "",
            "batch_size": batch_size if batch_size is not None else "",
            "learning_rate": learning_rate if learning_rate is not None else "",
            "max_steps": max_steps if max_steps is not None else "",
            "train_samples": train_samples if train_samples is not None else "",
            "eval_samples": eval_samples if eval_samples is not None else "",
            "checkpoint_path": checkpoint_path if checkpoint_path else "",
            "error": error if error else "",
        }

        with open(self.results_file, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=row.keys(), delimiter="\t")
            writer.writerow(row)

        logger.info("Registered result for experiment: %s", experiment_name)

    def register_experiment_report(self, report: ExperimentReport) -> None:
        """Register an experiment report result.

        Parameters
        ----------
        report : ExperimentReport
            The experiment report to register.
        """
        # Extract metrics from evaluation results
        metrics = report.evaluation_results.get("metrics", {})

        # Extract config from training run
        config = None
        if report.training_run:
            config = report.training_run.metrics

        self.register_result(
            experiment_name=report.experiment_name,
            variant=report.variant,
            fast_mode=report.fast_mode,
            status=report.status,
            start_time=report.start_time,
            end_time=report.end_time,
            metrics=metrics,
            config=config,
            checkpoint_path=report.artifacts.get("checkpoint")
            if report.artifacts
            else None,
            error=report.error,
        )

    def register_training_run(self, run: TrainingRun) -> None:
        """Register a training run result.

        Parameters
        ----------
        run : TrainingRun
            The training run to register.
        """
        self.register_result(
            experiment_name=run.variant,
            variant=run.variant,
            fast_mode=run.fast_mode,
            status=run.status,
            start_time=run.start_time,
            end_time=run.end_time,
            metrics=run.metrics,
            config=run.metrics,
            checkpoint_path=run.checkpoint_path,
            error=run.error,
        )

    def query_results(
        self,
        variant: str | None = None,
        status: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Query experiment results from the TSV file.

        Parameters
        ----------
        variant : str | None
            Filter by variant name.
        status : str | None
            Filter by status.
        limit : int | None
            Maximum number of results to return.

        Returns
        -------
        list[dict]
            List of experiment result dictionaries.
        """
        if not self.results_file.exists():
            return []

        results = []
        with open(self.results_file, "r", newline="") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                # Apply filters
                if variant and row.get("variant") != variant:
                    continue
                if status and row.get("status") != status:
                    continue
                results.append(row)

        # Apply limit
        if limit:
            results = results[-limit:]

        return results

    def get_best_result(
        self,
        variant: str | None = None,
        metric: str = "val_bpb",
    ) -> dict[str, Any] | None:
        """Get the best result based on a metric.

        Parameters
        ----------
        variant : str | None
            Filter by variant name.
        metric : str
            Metric to optimize (default: val_bpb).

        Returns
        -------
        dict | None
            Best result dictionary or None if no results found.
        """
        results = self.query_results(variant=variant, status="completed")

        if not results:
            return None

        # Find best result (lowest for val_bpb, highest for others)
        best_result = None
        best_value = float("inf") if metric == "val_bpb" else float("-inf")

        for result in results:
            value_str = result.get(metric, "")
            if not value_str:
                continue
            try:
                value = float(value_str)
                if metric == "val_bpb":
                    if value < best_value:
                        best_value = value
                        best_result = result
                else:
                    if value > best_value:
                        best_value = value
                        best_result = result
            except ValueError:
                continue

        return best_result

    def export_to_csv(self, output_path: str | Path) -> None:
        """Export results to a CSV file.

        Parameters
        ----------
        output_path : str | Path
            Path to output CSV file.
        """
        output_path = Path(output_path)

        if not self.results_file.exists():
            logger.warning("No results file to export")
            return

        with open(self.results_file, "r") as infile:
            content = infile.read()

        # Convert tab-separated to comma-separated
        content = content.replace("\t", ",")

        with open(output_path, "w") as outfile:
            outfile.write(content)

        logger.info("Exported results to: %s", output_path)


def create_results_registry(
    results_dir: str | Path | None = None,
) -> ResultsRegistry:
    """Create a results registry instance.

    Parameters
    ----------
    results_dir : str | Path | None
        Directory for storing results.

    Returns
    -------
    ResultsRegistry
        Configured results registry.
    """
    return ResultsRegistry(results_dir=results_dir)


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

    # Register results in TSV
    try:
        registry = ResultsRegistry(results_dir=experiment_dir)
        registry.register_experiment_report(report)
    except Exception as e:
        logger.warning("Failed to register results: %s", e)

    logger.info(
        "Experiment completed: name=%s, variant=%s, status=%s",
        experiment_name,
        variant,
        report.status,
    )
    return report
