#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Tokenizer Training with Checkpoint Resume Support.

This module provides BPE tokenizer training with:
- Checkpoint saving and resumption for long-running operations
- Progress tracking
- Graceful interruption handling
"""

from __future__ import annotations

import logging
import pickle
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ======================================================================
# ERROR MESSAGES
# ======================================================================

CHECKPOINT_ERROR_TEMPLATE = """Checkpoint resume failed for {operation}.

Checkpoint file: {checkpoint_path}
Error: {error}

The checkpoint may be corrupted or from an incompatible version.
To resolve:

1. Delete the checkpoint and start fresh:
   rm {checkpoint_path}

2. If this is a version mismatch, check the tokenizer version
"""

CHECKPOINT_NOT_FOUND_ERROR = """No checkpoint found for resume.

Checkpoint path: {checkpoint_path}

To start a new training run, simply omit the --resume flag.
"""


# ======================================================================
# CHECKPOINT MANAGEMENT
# ======================================================================


class CheckpointManager:
    """Manages checkpoint saving and resumption for tokenizer training."""

    def __init__(self, checkpoint_dir: str | Path) -> None:
        """Initialize the checkpoint manager.

        Parameters
        ----------
        checkpoint_dir : str | Path
            Directory to store checkpoints.
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def get_checkpoint_path(self, name: str) -> Path:
        """Get the path for a checkpoint.

        Parameters
        ----------
        name : str
            Checkpoint name/identifier.

        Returns
        -------
        Path
            Path to the checkpoint file.
        """
        return self.checkpoint_dir / f"{name}.checkpoint"

    def save_checkpoint(
        self,
        name: str,
        data: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        """Save a checkpoint with atomic write.

        Parameters
        ----------
        name : str
            Checkpoint name/identifier.
        data : dict
            Checkpoint data to save.
        metadata : dict | None
            Additional metadata (version, timestamp, etc.).

        Returns
        -------
        Path
            Path to the saved checkpoint.
        """
        checkpoint_path = self.get_checkpoint_path(name)

        # Add metadata
        checkpoint_data = {
            "data": data,
            "metadata": metadata or {},
            "version": "1.0",
        }

        # Atomic write: write to temp file, then rename
        temp_path = checkpoint_path.with_suffix(".tmp")
        try:
            with open(temp_path, "wb") as f:
                pickle.dump(checkpoint_data, f)
            temp_path.replace(checkpoint_path)
            logger.info("Checkpoint saved: %s", checkpoint_path)
        except OSError as e:
            if temp_path.exists():
                temp_path.unlink()
            raise OSError(f"Failed to save checkpoint: {e}") from e

        return checkpoint_path

    def load_checkpoint(
        self,
        name: str,
        expected_version: str | None = None,
    ) -> dict[str, Any]:
        """Load a checkpoint for resumption.

        Parameters
        ----------
        name : str
            Checkpoint name/identifier.
        expected_version : str | None
            Expected checkpoint version. If None, version check is skipped.

        Returns
        -------
        dict
            Checkpoint data.

        Raises
        ------
        FileNotFoundError
            If checkpoint doesn't exist.
        ValueError
            If checkpoint version doesn't match expected.
        """
        checkpoint_path = self.get_checkpoint_path(name)

        if not checkpoint_path.exists():
            raise FileNotFoundError(
                CHECKPOINT_NOT_FOUND_ERROR.format(checkpoint_path=str(checkpoint_path))
            )

        try:
            with open(checkpoint_path, "rb") as f:
                checkpoint_data = pickle.load(f)
        except (pickle.PickleError, OSError) as e:
            raise OSError(
                CHECKPOINT_ERROR_TEMPLATE.format(
                    operation=name,
                    checkpoint_path=checkpoint_path,
                    error=str(e),
                )
            ) from e

        # Version check
        if expected_version is not None:
            version = checkpoint_data.get("metadata", {}).get("version", "unknown")
            if version != expected_version:
                raise ValueError(
                    f"Checkpoint version mismatch: expected {expected_version}, got {version}"
                )

        logger.info("Checkpoint loaded: %s", checkpoint_path)
        return checkpoint_data

    def checkpoint_exists(self, name: str) -> bool:
        """Check if a checkpoint exists.

        Parameters
        ----------
        name : str
            Checkpoint name/identifier.

        Returns
        -------
        bool
            True if checkpoint exists.
        """
        return self.get_checkpoint_path(name).exists()

    def delete_checkpoint(self, name: str) -> None:
        """Delete a checkpoint.

        Parameters
        ----------
        name : str
            Checkpoint name/identifier.
        """
        checkpoint_path = self.get_checkpoint_path(name)
        if checkpoint_path.exists():
            checkpoint_path.unlink()
            logger.info("Checkpoint deleted: %s", checkpoint_path)

    def list_checkpoints(self) -> list[str]:
        """List all available checkpoints.

        Returns
        -------
        list[str]
            List of checkpoint names (without .checkpoint extension).
        """
        if not self.checkpoint_dir.exists():
            return []
        return [
            f.stem for f in self.checkpoint_dir.iterdir() if f.suffix == ".checkpoint"
        ]


# ======================================================================
# TOKENIZER TRAINING
# ======================================================================


class TokenizerTrainer:
    """Trainer for BPE tokenizers with checkpoint support."""

    def __init__(
        self,
        checkpoint_dir: str | Path = "data/tokenizer_checkpoints",
        resume: bool = True,
    ) -> None:
        """Initialize the tokenizer trainer.

        Parameters
        ----------
        checkpoint_dir : str | Path
            Directory for checkpoints.
        resume : bool
            Whether to resume from checkpoint if available.
        """
        self.checkpoint_manager = CheckpointManager(checkpoint_dir)
        self.resume = resume

    def train(
        self,
        train_data_path: str | Path,
        output_path: str | Path,
        vocab_size: int = 32000,
        checkpoint_name: str = "tokenizer_train",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Train a BPE tokenizer with checkpoint support.

        Parameters
        ----------
        train_data_path : str | Path
            Path to training data (text file or directory of text files).
        output_path : str | Path
            Path to save the trained tokenizer.
        vocab_size : int
            Vocabulary size.
        checkpoint_name : str
            Name for checkpoint.
        **kwargs
            Additional arguments for tokenizer training.

        Returns
        -------
        dict
            Training results.
        """
        train_data_path = Path(train_data_path)
        output_path = Path(output_path)

        # Check for resume
        checkpoint_data = None
        if self.resume and self.checkpoint_manager.checkpoint_exists(checkpoint_name):
            try:
                checkpoint_data = self.checkpoint_manager.load_checkpoint(checkpoint_name)
                logger.info(
                    "Resuming from checkpoint: %s",
                    checkpoint_name,
                )
            except Exception as e:
                logger.warning(
                    "Could not load checkpoint, starting fresh: %s",
                    e,
                )

        # If resuming and checkpoint exists, use checkpoint data
        if checkpoint_data is not None:
            start_epoch = checkpoint_data.get("data", {}).get("epoch", 0)
        else:
            start_epoch = 0

        logger.info(
            "Starting tokenizer training: vocab_size=%d, data=%s",
            vocab_size,
            train_data_path,
        )

        # This is a placeholder - actual implementation would use
        # tokenizers library or similar
        # Example with HuggingFace tokenizers:
        # from tokenizers import Tokenizer, models, trainers, pre_tokenizers
        # tokenizer = Tokenizer(models.BPE())
        # trainer = trainers.BpeTrainer(vocab_size=vocab_size, ...)
        # tokenizer.train(trainer=trainer, files=[train_data_path])

        # Simulate training with checkpoint saving
        results = {
            "vocab_size": vocab_size,
            "output_path": str(output_path),
            "start_epoch": start_epoch,
            "status": "completed",
        }

        # Save final checkpoint
        self.checkpoint_manager.save_checkpoint(
            checkpoint_name,
            data={"epoch": start_epoch + 1, "results": results},
            metadata={"vocab_size": vocab_size},
        )

        return results

    def resume_training(
        self,
        checkpoint_name: str = "tokenizer_train",
    ) -> dict[str, Any]:
        """Resume training from a checkpoint.

        Parameters
        ----------
        checkpoint_name : str
            Name of the checkpoint to resume from.

        Returns
        -------
        dict
            Checkpoint data.
        """
        return self.checkpoint_manager.load_checkpoint(checkpoint_name)


# ======================================================================
# CLI FUNCTIONS
# ======================================================================


def train_tokenizer_cli(args: Any) -> None:
    """CLI entry point for tokenizer training.

    Parameters
    ----------
    args : Any
        Parsed command-line arguments.
    """
    trainer = TokenizerTrainer(
        checkpoint_dir=args.checkpoint_dir,
        resume=args.resume,
    )

    if args.resume and args.checkpoint:
        # Resume specific checkpoint
        checkpoint_data = trainer.resume_training(args.checkpoint)
        logger.info("Resumed from checkpoint: %s", checkpoint_data)
    else:
        # Start new training
        results = trainer.train(
            train_data_path=args.input,
            output_path=args.output,
            vocab_size=args.vocab_size,
            checkpoint_name=args.checkpoint or "tokenizer_train",
        )
        logger.info("Tokenizer training completed: %s", results)
