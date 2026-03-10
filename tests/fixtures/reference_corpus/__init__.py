# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0
"""
Reference corpus fixtures for recall measurement.

This module provides gold-standard test fixtures for measuring
extractor recall. Each profile directory contains sample repositories
with known dependencies in gold_dependencies.json.
"""

from pathlib import Path

# Base path for reference corpus fixtures
REFERENCE_CORPUS_PATH = Path(__file__).parent
