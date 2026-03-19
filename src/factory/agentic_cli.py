#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
AEGF V10-MT CLI — Multi-Turn Diversified Architect Edition
==========================================================
[STATUS: EXPERIMENTAL]
Command-line interface for multi-turn agentic training data generation.
"""

import argparse
import logging
import random
from pathlib import Path

# ══════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════
DEFAULT_BASE_URL = "http://localhost:8000/v1"
DEFAULT_API_KEY = "sk-master-bunker-2026"
DEFAULT_MODEL = "qwen3-30b-a3b-thinking-fp8"
DEFAULT_WORKERS = 8

# ══════════════════════════════════════════════════════════════════════
# LOGGER
# ══════════════════════════════════════════════════════════════════════
logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="AEGF (Architect-Expert-Gap-Forge) V10-MT — Multi-Turn Diversified Architect",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test mode: 3 fragments, 4 workers
  python -m src.factory.agentic_cli --test 3 --workers 4

  # Full production: 16 workers for Blackwell
  python -m src.factory.agentic_cli --workers 16

  # Limit to 10 raw files
  python -m src.factory.agentic_cli --limit 10 --workers 8

  # RESUME interrupted execution
  python -m src.factory.agentic_cli --resume data/synthetic/v10mt_diversified_20260223.jsonl --workers 16

  # Custom model and output
  python -m src.factory.agentic_cli --model qwen3-32b --output data/my_dataset.jsonl
        """,
    )
    parser.add_argument(
        "--test",
        type=int,
        default=None,
        metavar="N",
        help="\U0001f9ea Test mode: process only N fragments",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Limit to N raw input files",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        metavar="W",
        help=f"Async parallel workers (default: {DEFAULT_WORKERS})",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help=f"Inference model (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default=DEFAULT_BASE_URL,
        help=f"vLLM server URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=DEFAULT_API_KEY,
        help="Server API key",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        metavar="PATH",
        help="Custom JSONL output path",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Seed for reproducibility (default: 42)",
    )
    parser.add_argument(
        "--resume",
        type=str,
        default=None,
        metavar="PATH",
        help="\U0001f504 Resume: path to previous output JSONL.",
    )
    parser.add_argument(
        "--gap-dir",
        type=str,
        default=None,
        metavar="DIR",
        help="Directory containing master documents (default: data/Gap relative to project root)",
    )
    parser.add_argument(
        "--taxonomy",
        type=str,
        default=None,
        metavar="PATH",
        help="Path to agentic_taxonomy.yaml (default: auto-resolved from project root)",
    )
    parser.add_argument(
        "--raw-dir",
        type=str,
        default="data/raw/homeassistant-main_txt",
        metavar="DIR",
        help="Input directory with packed .txt files (default: data/raw/homeassistant-main_txt)",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point for the CLI."""
    import asyncio

    from src.factory.agentic_prompt_builder import (
        HA_ERROR_TEMPLATES,
        LEGACY_2023_PATTERNS,
        TOOLS_DEFINITION,
        load_taxonomy,
    )
    from src.factory.agentic_runner import main_async

    args = parse_args()
    random.seed(args.seed)

    # Resolve base_dir (project root: 3 levels up from this file)
    base_dir = Path(__file__).resolve().parent.parent.parent

    # Resolve taxonomy path
    if args.taxonomy:
        taxonomy_path = Path(args.taxonomy)
    else:
        taxonomy_path = (
            base_dir
            / "configs"
            / "taxonomy"
            / "home_assistant"
            / "hacs_expert"
            / "agentic_taxonomy.yaml"
        )

    if not taxonomy_path.exists():
        raise FileNotFoundError(
            f"Taxonomy file not found: {taxonomy_path}. "
            "Use --taxonomy to specify the correct path."
        )

    load_taxonomy(taxonomy_path)
    logger.info(
        "Taxonomy loaded: %d error templates, %d legacy patterns, %d tools",
        len(HA_ERROR_TEMPLATES),
        len(LEGACY_2023_PATTERNS),
        len(TOOLS_DEFINITION),
    )

    # Resolve gap directory
    if args.gap_dir:
        args._gap_dir = Path(args.gap_dir)
    else:
        args._gap_dir = base_dir / "data" / "Gap"

    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
