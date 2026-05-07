#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Curator package initializer.

This module exposes the public API of the `src.curation` package.
"""

from .backtracking_config import (
    BacktrackingConfig,
    PipelineReport,
    load_backtracking_config,
)
from .backtracking_helpers import extract_think_block, replace_think_block
from .backtrack_strategy import (
    classify_rewrite_strategy,
    build_rewrite_prompt,
    passes_backtracking_filter,
)
from .rewrite_engine import (
    apply_backtracking_rewrite,
    rewrite_pipeline,
    load_jsonl,
    save_jsonl,
)
from .rewrite_cli import main
from .curator_pipeline import (
    CurationStats,
    ConversationExtractor,
    run_nemo_filter_pipeline,
    load_jsonl as pipeline_load_jsonl,
    write_jsonl as pipeline_write_jsonl,
    save_report,
)
from .dedup_filter import exact_dedup, semantic_dedup
from .quality_filter import structural_quality_filter
from .curator_cli import build_parser, main as cli_main

__all__ = [
    # Backtracking rewriter exports
    "BacktrackingConfig",
    "PipelineReport",
    "load_backtracking_config",
    "extract_think_block",
    "replace_think_block",
    "classify_rewrite_strategy",
    "build_rewrite_prompt",
    "passes_backtracking_filter",
    "apply_backtracking_rewrite",
    "rewrite_pipeline",
    "load_jsonl",
    "save_jsonl",
    "main",
    # Curator pipeline exports (new submodules)
    "CurationStats",
    "ConversationExtractor",
    "run_nemo_filter_pipeline",
    "exact_dedup",
    "semantic_dedup",
    "structural_quality_filter",
    "build_parser",
    "cli_main",
    # Backward compatibility - load_jsonl, write_jsonl, save_report from pipeline
    "pipeline_load_jsonl",
    "pipeline_write_jsonl",
    "save_report",
]
