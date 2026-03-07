#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Curator package initializer.

This module exposes the public API of the `src.curation` package.
"""

from .nemo_curator_suite import CurationStats, exact_dedup, run_nemo_filter_pipeline

__all__ = [
    "CurationStats",
    "exact_dedup",
    "run_nemo_filter_pipeline",
]
