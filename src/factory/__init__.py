#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0


"""Factory package initializer.

Exposes the public modules from `src.factory` used by training pipelines.
"""

from importlib import import_module
from types import ModuleType
from typing import Any

__all__ = ["agentic_gen", "production_v11", "think_filter"]


def __getattr__(name: str) -> ModuleType | Any:
    """Lazy-load package submodules on attribute access.

    When someone does ``from src.factory import production_v11`` or
    accesses `src.factory.production_v11`, this function imports the
    submodule on demand and caches it in the package globals.
    """
    if name in __all__:
        module = import_module(f"{__name__}.{name}")
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(list(globals().keys()) + __all__)
