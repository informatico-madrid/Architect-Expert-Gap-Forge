#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""Backtracking rewriter CLI entry point.

This module provides the command-line interface for the backtracking rewrite pipeline.

Public API
----------
main(argv) -- CLI entry point
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from .backtracking_config import BacktrackingConfig, load_backtracking_config
from .rewrite_engine import rewrite_pipeline

logger = logging.getLogger(__name__)

__all__ = ["main"]


def _build_arg_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="backtracking_rewriter",
        description=(
            "AEGF Stage 3.5 — Backtracking Alignment: rewrite <think> blocks "
            "to embed self-correction patterns into training data."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    # Required I/O
    io = parser.add_argument_group("I/O (required)")
    io.add_argument(
        "--input",
        "-i",
        required=True,
        type=Path,
        metavar="FILE",
        help="Source JSONL dataset.",
    )
    io.add_argument(
        "--output",
        "-o",
        required=True,
        type=Path,
        metavar="FILE",
        help="Destination JSONL dataset.",
    )
    # Config
    cfg_grp = parser.add_argument_group("Configuration")
    cfg_grp.add_argument(
        "--config",
        "-c",
        type=Path,
        default=None,
        metavar="FILE",
        help="YAML config (e.g. configs/stage_3_curation/backtracking_alignment.yaml).",
    )
    cfg_grp.add_argument(
        "--language",
        type=str,
        default=None,
        metavar="LANG",
        help=(
            "Force output language token (e.g. 'Spanish' or 'English'). "
            "When provided this overrides per-record detection."
        ),
    )
    # Inference overrides
    inf_grp = parser.add_argument_group(
        "Inference overrides (take priority over --config)"
    )
    inf_grp.add_argument(
        "--model",
        type=str,
        default=None,
        metavar="NAME",
        help="vLLM model name.",
    )
    inf_grp.add_argument(
        "--base-url",
        type=str,
        default=None,
        metavar="URL",
        help="vLLM API base URL.",
    )
    inf_grp.add_argument(
        "--temperature",
        type=float,
        default=None,
        metavar="FLOAT",
        help="Sampling temperature.",
    )
    inf_grp.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        metavar="N",
        help="Max context tokens filter (discard records exceeding this estimate).",
    )
    inf_grp.add_argument(
        "--max-generation-tokens",
        type=int,
        default=None,
        metavar="N",
        help="Max generation tokens per think-block rewrite.",
    )
    inf_grp.add_argument(
        "--batch-size",
        type=int,
        default=None,
        metavar="N",
        help="Progress log interval (number of eligible records between log lines).",
    )
    inf_grp.add_argument(
        "--workers",
        type=int,
        default=None,
        metavar="N",
        help="Number of concurrent vLLM requests (asyncio.Semaphore size).",
    )
    inf_grp.add_argument(
        "--audit-dir",
        type=Path,
        default=None,
        metavar="DIR",
        help=(
            "Directory to save full rewritten <think> blocks for auditing. "
            "When provided, per-record full texts are written under "
            "<audit-dir>/backtracking_YYYYmmdd_HHMMSS/<id>.txt"
        ),
    )
    inf_grp.add_argument(
        "--gap-dir",
        type=str,
        default=None,
        metavar="DIR",
        help=(
            "Directory containing HA_MASTER_GUIDE_2026.md for governance context "
            "injection.  Defaults to 'data/Gap'."
        ),
    )
    # Diagnostics
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for the backtracking rewriter pipeline.

    Usage example::

        python src/curation/backtracking_rewriter.py \\
            --input  data/synthetic/v11_DISTILLED.jsonl \\
            --output data/synthetic/v11_backtracking_aligned.jsonl \\
            --config configs/stage_3_curation/backtracking_alignment.yaml
    """
    from dataclasses import replace as dataclasses_replace

    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level, logging.INFO),
        format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Load base config from YAML (or fall back to defaults)
    cfg: BacktrackingConfig
    if args.config is not None:
        cfg = load_backtracking_config(args.config)
    else:
        cfg = BacktrackingConfig()

    # Apply any CLI overrides (frozen dataclass requires dataclasses.replace)
    overrides: dict[str, object] = {}
    if args.model is not None:
        overrides["vllm_model"] = args.model
    if args.base_url is not None:
        overrides["vllm_api_url"] = args.base_url
    if args.temperature is not None:
        overrides["temperature"] = args.temperature
    if args.max_tokens is not None:
        overrides["max_tokens"] = args.max_tokens
    if args.max_generation_tokens is not None:
        overrides["max_generation_tokens"] = args.max_generation_tokens
    if args.batch_size is not None:
        overrides["batch_size"] = args.batch_size
    if getattr(args, "workers", None) is not None:
        overrides["workers"] = args.workers
    if getattr(args, "audit_dir", None) is not None:
        # store as string in the frozen dataclass
        overrides["audit_dir"] = str(args.audit_dir)
    if getattr(args, "gap_dir", None) is not None:
        overrides["gap_dir"] = args.gap_dir
    if getattr(args, "language", None) is not None:
        overrides["language"] = args.language
    if overrides:
        cfg = dataclasses_replace(cfg, **overrides)

    logger.info(
        "Backtracking rewriter starting | input=%s output=%s model=%s temperature=%.2f",
        args.input,
        args.output,
        cfg.vllm_model,
        cfg.temperature,
    )

    report = asyncio.run(rewrite_pipeline(args.input, args.output, cfg))
    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
