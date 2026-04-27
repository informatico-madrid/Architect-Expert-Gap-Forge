#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0


"""Factory package initializer.

Exposes the public modules from `src.factory` used by training pipelines.
"""

# Public API exports - explicit re-exports from submodules
from src.factory.backtracking_detector import BacktrackingDetector
from src.factory.checkpoint import AsyncFileWriter, ProgressTracker, load_checkpoint
from src.factory.config import GeneratedSample, TaxonomyState
from src.factory.fragment_extractor import get_fragments
from src.factory.ldi_validator import (
    ExampleTypeAssignment,
    LDIResult,
    assign_example_type,
    validate_ldi,
)
from src.factory.prompt_builder import (
    build_user_contrast,
    build_user_error_recovery,
    build_user_error_recovery_jinja,
    build_user_nominal,
    load_taxonomy,
)
from src.factory.trajectory_signature import TrajectorySignature

__all__ = [
    # Submodules for lazy loading
    "agentic_prompt_builder",
    "agentic_runner",
    "agentic_cli",
    "think_filter",
    # Public API exports
    "load_taxonomy",
    "build_user_nominal",
    "build_user_contrast",
    "build_user_error_recovery",
    "build_user_error_recovery_jinja",
    "get_fragments",
    "validate_ldi",
    "assign_example_type",
    "load_checkpoint",
    "AsyncFileWriter",
    "ProgressTracker",
    "TaxonomyState",
    "GeneratedSample",
    "LDIResult",
    "ExampleTypeAssignment",
    "BacktrackingDetector",
    "TrajectorySignature",
]


from importlib import import_module
from types import ModuleType
from typing import Any


def __getattr__(name: str) -> ModuleType | Any:
    """Lazy-load package submodules on attribute access.

    When someone accesses a submodule attribute like
    `src.factory.think_filter`, this function imports the
    submodule on demand and caches it in the package globals.
    """
    if name in __all__:
        # Skip re-exported names (they're already in globals)
        if name in globals():
            return globals()[name]
        module = import_module(f"{__name__}.{name}")
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(list(globals().keys()) + __all__)
