#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Inject lightweight fake `nemo_curator` and `datasketch` modules into
`sys.modules` for unit tests that exercise guarded import paths.

Call `enable_fake_nemo()` before importing `src.curation.nemo_curator_suite`
or use `importlib.reload()` afterwards to ensure the suite detects the
availability flags at import time.
"""

from __future__ import annotations

import sys
import types
from typing import List


_REGISTERED: List[str] = []


def enable_fake_nemo() -> None:
    """Insert fake `nemo_curator` and `datasketch` packages into sys.modules.

    After calling this function, importing `src.curation.nemo_curator_suite`
    will find `nemo_curator` and `datasketch` and behave as if the
    optional dependencies are installed.
    """
    global _REGISTERED
    mods = {}

    # ---- datasketch ----
    datasketch = types.ModuleType("datasketch")

    class MinHash:
        def __init__(self, num_perm: int = 128):
            self.num_perm = num_perm

        def update(self, data: bytes) -> None:
            # No-op for tests
            return None

    class MinHashLSH:
        def __init__(self, threshold: float = 0.85, num_perm: int = 128):
            self.threshold = threshold
            self._store = {}

        def insert(self, key: str, m: MinHash) -> None:
            self._store[key] = m

        def query(self, m: MinHash) -> List[str]:
            # Return all inserted keys — sufficient for test clustering
            return list(self._store.keys())

    datasketch.MinHash = MinHash
    datasketch.MinHashLSH = MinHashLSH
    mods['datasketch'] = datasketch

    # ---- nemo_curator core.client ----
    core_client = types.ModuleType('nemo_curator.core.client')

    class RayClient:
        def start(self) -> None:
            return None

        def stop(self) -> None:
            return None

    core_client.RayClient = RayClient
    mods['nemo_curator.core.client'] = core_client

    # ---- nemo_curator.pipeline ----
    pipeline = types.ModuleType('nemo_curator.pipeline')

    class Pipeline:
        def __init__(self, name: str = "fake_pipeline") -> None:
            self.name = name
            self._stages = []

        def add_stage(self, stage: object) -> None:
            self._stages.append(stage)

        def run(self) -> None:
            # Run is a no-op in tests
            return None

    pipeline.Pipeline = Pipeline
    mods['nemo_curator.pipeline'] = pipeline

    # ---- nemo_curator.stages.text.io.reader/writer ----
    reader = types.ModuleType('nemo_curator.stages.text.io.reader')
    writer = types.ModuleType('nemo_curator.stages.text.io.writer')

    class JsonlReader:
        def __init__(self, file_paths: str) -> None:
            self.file_paths = file_paths

    class JsonlWriter:
        def __init__(self, path: str) -> None:
            self.path = path

    reader.JsonlReader = JsonlReader
    writer.JsonlWriter = JsonlWriter
    mods['nemo_curator.stages.text.io.reader'] = reader
    mods['nemo_curator.stages.text.io.writer'] = writer

    # ---- nemo_curator.stages.text.modules ----
    modules = types.ModuleType('nemo_curator.stages.text.modules')

    class ScoreFilter:
        def __init__(self, filter_obj: object, text_field: str = "filter_text") -> None:
            self.filter_obj = filter_obj
            self.text_field = text_field

    class Modify:
        def __init__(self, modifier_fn: object, input_fields: List[str], output_fields: List[str]) -> None:
            self.modifier_fn = modifier_fn
            self.input_fields = input_fields
            self.output_fields = output_fields

    modules.ScoreFilter = ScoreFilter
    modules.Modify = Modify
    mods['nemo_curator.stages.text.modules'] = modules

    # ---- nemo_curator.stages.text.filters (stubs) ----
    filters = types.ModuleType('nemo_curator.stages.text.filters')

    class _StubFilter:
        def __init__(self, *args, **kwargs) -> None:
            return None

    # Create named stubs used by the suite
    for name in [
        'WordCountFilter', 'RepeatingTopNGramsFilter', 'SymbolsToWordsFilter',
        'NonAlphaNumericFilter', 'PunctuationFilter', 'BoilerPlateStringFilter',
        'UrlsFilter', 'RepeatedLinesFilter'
    ]:
        setattr(filters, name, _StubFilter)

    mods['nemo_curator.stages.text.filters'] = filters

    # Register all created modules in sys.modules so normal imports work
    for fullname, module in mods.items():
        sys.modules[fullname] = module
        _REGISTERED.append(fullname)


def disable_fake_nemo() -> None:
    """Remove previously injected fake modules from `sys.modules`."""
    global _REGISTERED
    for name in list(_REGISTERED):
        sys.modules.pop(name, None)
        _REGISTERED.remove(name)


__all__ = ["enable_fake_nemo", "disable_fake_nemo"]
