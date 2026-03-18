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
            experiment_dir
            or os.getenv("AEGF_EXPERIMENT_DIR", "experiments")
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
