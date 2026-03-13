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

from src.discovery.ingestor import DiscoveryConfig, RepoIngestor

# New submodules from processor.py split
from src.discovery.file_scanner import (
    MIN_SIZE,
    MAX_SIZE_BACKEND,
    MAX_SIZE_FRONTEND,
    BACKEND_REPOS,
    GOLD_PATTERNS,
    LOGIC_ONLY_MIN_CHARS,
    ANCHOR_FILENAMES,
    GOVERNANCE_FILENAMES,
    discover_modules,
    find_governance_files,
    find_readme,
    find_test,
    is_ignored,
)

from src.discovery.fragment_parser import (
    Module,
    ModuleFile,
    classify_role,
    extract_local_imports,
    build_module,
    make_arch_header,
)

from src.discovery.metadata_enricher import (
    RepoAbortError,
    ProcessingConfig,
    RepoProcessor,
)

from src.discovery.processor_cli import (
    configure_logger,
    parse_args,
    main,
)

__all__ = [
    # Original exports
    "RepoIngestor",
    "DiscoveryConfig",
    # New exports from processor.py split
    "MIN_SIZE",
    "MAX_SIZE_BACKEND",
    "MAX_SIZE_FRONTEND",
    "BACKEND_REPOS",
    "GOLD_PATTERNS",
    "LOGIC_ONLY_MIN_CHARS",
    "ANCHOR_FILENAMES",
    "GOVERNANCE_FILENAMES",
    "discover_modules",
    "find_governance_files",
    "find_readme",
    "find_test",
    "is_ignored",
    "Module",
    "ModuleFile",
    "classify_role",
    "extract_local_imports",
    "build_module",
    "make_arch_header",
    "RepoAbortError",
    "ProcessingConfig",
    "RepoProcessor",
    "configure_logger",
    "parse_args",
    "main",
]
