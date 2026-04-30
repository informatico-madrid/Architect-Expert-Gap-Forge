#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
AEGF Bits-Per-Byte Evaluation Module
====================================

This module provides utilities for computing and analyzing bits-per-byte (BPB)
metrics during model evaluation. BPB is a compression-based metric that
measures the quality of model generations by evaluating how well the model
predicts the target content.

Public API
----------
- ``calculate_bpb`` — Compute bits-per-byte for a generation.
- ``evaluate_bpb_scores`` — Evaluate BPB scores across multiple samples.
- ``aggregate_bpb_metrics`` — Aggregate BPB metrics for reporting.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


def calculate_bpb(predicted: str, target: str, vocab_size: int = 32000) -> float:
    """Calculate bits-per-byte for a predicted string against a target.

    Parameters
    ----------
    predicted : str
        The generated text from the model.
    target : str
        The reference/ground truth text.
    vocab_size : int
        Vocabulary size for log2 calculation (default: 32000 for GPT-style).

    Returns
    -------
    float
        The bits-per-byte score. Lower is better (more compressible = better).
    """
    if not target:
        raise ValueError("Target string cannot be empty")
    if not predicted:
        return float("inf")

    # Simple character-level cross-entropy approximation
    # In practice, this would use actual token probabilities
    num_bytes = len(target.encode("utf-8"))
    num_tokens = len(target)

    # Note: vocab_size is reserved for future token-level calculations
    # _ = np.log2(vocab_size)  # Uncomment when using token-level probs

    # Simple perplexity-like approximation
    # This is a simplified version - real implementation would use token logits
    if predicted == target:
        return 0.0  # Perfect prediction

    # Calculate character error rate as proxy
    min_len = min(len(predicted), len(target))
    if min_len > 0:
        matching = sum(1 for i in range(min_len) if predicted[i] == target[i])
        accuracy = matching / min_len
    else:
        accuracy = 0.0  # pragma: no cover - empty strings handled earlier

    # Convert accuracy to pseudo cross-entropy
    # Lower accuracy = higher cross-entropy = higher BPB
    epsilon = 1e-10
    ce = -np.log2(max(accuracy, epsilon))
    bpb = ce * (num_tokens / num_bytes) if num_bytes > 0 else float("inf")

    return bpb


def evaluate_bpb_scores(
    predictions: list[str],
    targets: list[str],
    vocab_size: int = 32000,
) -> list[float]:
    """Evaluate BPB scores for multiple prediction-target pairs.

    Parameters
    ----------
    predictions : list[str]
        List of generated texts.
    targets : list[str]
        List of reference texts.
    vocab_size : int
        Vocabulary size for BPB calculation.

    Returns
    -------
    list[float]
        List of BPB scores for each pair.
    """
    if len(predictions) != len(targets):
        raise ValueError(
            f"Predictions and targets must have same length: "
            f"{len(predictions)} != {len(targets)}"
        )

    scores = []
    for pred, tgt in zip(predictions, targets):
        try:
            score = calculate_bpb(pred, tgt, vocab_size)
            scores.append(score)
        except ValueError as e:
            logger.warning(f"Skipping sample due to error: {e}")
            scores.append(float("inf"))

    return scores


def aggregate_bpb_metrics(scores: list[float]) -> dict[str, Any]:
    """Aggregate BPB scores into summary metrics.

    Parameters
    ----------
    scores : list[float]
        List of BPB scores.

    Returns
    -------
    dict[str, Any]
        Dictionary containing mean, median, std, min, max, and valid count.
    """
    if not scores:
        return {
            "mean": float("nan"),
            "median": float("nan"),
            "std": float("nan"),
            "min": float("nan"),
            "max": float("nan"),
            "valid_count": 0,
            "total_count": 0,
        }

    # Filter out inf values for statistics
    valid_scores = [s for s in scores if s != float("inf")]

    if not valid_scores:
        return {
            "mean": float("inf"),
            "median": float("inf"),
            "std": 0.0,
            "min": float("inf"),
            "max": float("inf"),
            "valid_count": 0,
            "total_count": len(scores),
        }

    return {
        "mean": float(np.mean(valid_scores)),
        "median": float(np.median(valid_scores)),
        "std": float(np.std(valid_scores)),
        "min": float(np.min(valid_scores)),
        "max": float(np.max(valid_scores)),
        "valid_count": len(valid_scores),
        "total_count": len(scores),
    }
