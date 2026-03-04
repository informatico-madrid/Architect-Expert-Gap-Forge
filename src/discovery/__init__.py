# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""Minimal package initializer for the ``src.discovery`` package.

Exports a small, stable public API so callers can import key types from
``src.discovery`` directly (e.g. ``from src.discovery import RepoIngestor``).
"""

from .ingestor import RepoIngestor, DiscoveryConfig
from .processor import RepoProcessor, ProcessingConfig

__all__ = [
    "RepoIngestor",
    "DiscoveryConfig",
    "RepoProcessor",
    "ProcessingConfig",
]
