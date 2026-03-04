# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""Minimal package initializer for the ``src.factory`` package.

Expose the primary pipeline modules as package attributes so callers may use
``from src.factory import production_v11`` or ``from src.factory import think_filter``.
"""

from . import agentic_gen, production_v11, think_filter

__all__ = ["agentic_gen", "production_v11", "think_filter"]
