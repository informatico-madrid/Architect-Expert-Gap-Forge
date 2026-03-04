# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""Minimal package initializer for the ``src.curation`` package.

Export a small public API from the NeMo curation suite.
"""

from .nemo_curator_suite import CurationStats, exact_dedup, run_nemo_filter_pipeline

__all__ = ["CurationStats", "exact_dedup", "run_nemo_filter_pipeline"]
