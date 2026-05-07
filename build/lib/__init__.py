# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""AEGF Data Factory - Source Package.

This package provides professional-grade data harvesting and processing
capabilities for the Autonomous Enterprise-Grade Framework.
"""

__version__ = "1.0.0"

# Historically this package exposed a `harvester` module with various
# helper classes (HarvesterConfig, RepoHarvester, etc.). Those components
# have since been reorganized under the ``discovery`` subpackage.  The
# top‑level namespace is kept only for two purposes:
# 1. maintain a consistent version constant for tooling that queries it.
# 2. provide a very small set of convenience re‑exports so that existing
#    import paths continue to work for a short transition period.
#
# If you are writing new code, import directly from the subpackages:
# ``from data_factory.src.discovery.ingestor import RepoIngestor``.

# convenience re‑exports
from .discovery.ingestor import RepoIngestor, DiscoveryConfig  # type: ignore

__all__ = ["RepoIngestor", "DiscoveryConfig"]
