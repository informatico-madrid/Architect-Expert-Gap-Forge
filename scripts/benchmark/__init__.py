# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0
"""Performance benchmarking scripts for Stage 1 Discovery."""

from scripts.benchmark.measure_performance import (
    benchmark_profile,
    check_targets,
    process_file_timed,
)
from scripts.benchmark.compare_baseline import compare_results

__all__ = [
    "benchmark_profile",
    "check_targets",
    "process_file_timed",
    "compare_results",
]
