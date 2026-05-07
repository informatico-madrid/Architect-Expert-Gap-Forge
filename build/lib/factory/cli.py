#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
CLI entry point for AEGF V11 production pipeline.

This module provides command-line interface for the diversified code generation
pipeline with support for theory mode, checkpoint/resume, and configurable workers.
"""

import argparse
import logging
import random
import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


# Custom logging helpers -------------------------------------------------


class _FragmentWarningDowngrader(logging.Filter):
    """Downgrade specific warning messages to INFO.

    Used to silence or reduce noise for messages that are expected by design
    (e.g. "Fragment extraction error"). The filter mutates the record so
    downstream handlers will render it as INFO instead of WARNING.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            msg = ""
        if "Fragment extraction error" in msg and record.levelno == logging.WARNING:
            record.levelno = logging.INFO
            record.levelname = "INFO"
        return True


class _LivePanelHandler(logging.Handler):
    """Logging handler that updates a Rich Live panel with the last message.

    The handler expects to receive a running `rich.live.Live` instance as
    the `live` keyword argument when constructed.
    """

    def __init__(self, live):
        super().__init__()
        self.live = live

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
        except Exception:
            msg = record.getMessage()
        try:
            from rich.panel import Panel

            panel = Panel(msg, title="[bold magenta]Último log[/]", border_style="cyan")
            # Use live.update to refresh the fixed panel area
            self.live.update(panel)
        except Exception:
            # If Live is unavailable, fallback to stdout
            print(msg, file=sys.stderr)



from src.factory.config import (
    DEFAULT_API_KEY,
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    DEFAULT_WORKERS,
)
from src.factory.pipeline_runner import main_async

logger = logging.getLogger(__name__)

# Rich console for terminal output
_console: Console | None = None


def get_console() -> Console:
    """Get or create the Rich console instance."""
    global _console
    if _console is None:
        _console = Console()
    return _console


def configure_logger(
    level: str = "INFO",
    use_rich: bool = True,
    downgrade_fragment_warnings: bool = True,
    live: object | None = None,
    console: Console | None = None,
) -> None:
    """Configure root logger.

    Args:
        level: Logging level name (DEBUG/INFO/...).
        use_rich: When True, install RichHandler for pretty logging.
        downgrade_fragment_warnings: When True, apply a filter that
            downgrades "Fragment extraction error" warnings to INFO.
        live: Optional Rich Live instance. If provided, a handler will
            update the live panel with the last log message.
        console: Optional Rich Console instance (used by RichHandler).
    """
    # Normalise level
    level_name = (level or "INFO").upper()
    root_logger = logging.getLogger()

    # Remove existing handlers to avoid duplicate output when reconfiguring
    for h in list(root_logger.handlers):
        root_logger.removeHandler(h)

    try:
        lvl = getattr(logging, level_name)
    except Exception:
        lvl = logging.INFO
    root_logger.setLevel(lvl)

    # Install Rich handler when requested and available
    if use_rich:
        try:
            from rich.logging import RichHandler

            rich_handler = RichHandler(rich_tracebacks=True, show_time=False)
            if downgrade_fragment_warnings:
                rich_handler.addFilter(_FragmentWarningDowngrader())
            root_logger.addHandler(rich_handler)
        except Exception:
            # Fallback to standard stream handler
            stream = logging.StreamHandler(sys.stdout)
            stream.setFormatter(logging.Formatter("[V11 %(levelname)s] %(message)s"))
            if downgrade_fragment_warnings:
                stream.addFilter(_FragmentWarningDowngrader())
            root_logger.addHandler(stream)
    else:
        stream = logging.StreamHandler(sys.stdout)
        stream.setFormatter(logging.Formatter("[V11 %(levelname)s] %(message)s"))
        if downgrade_fragment_warnings:
            stream.addFilter(_FragmentWarningDowngrader())
        root_logger.addHandler(stream)

    # If a Live panel was provided, add a handler that updates it with the
    # latest formatted message (keeps the terminal area fixed).
    if live is not None:
        live_handler = _LivePanelHandler(live)
        live_handler.setLevel(logging.INFO)
        # Use a concise formatter for the live panel
        live_handler.setFormatter(logging.Formatter("[V11 %(levelname)s] %(message)s"))
        root_logger.addHandler(live_handler)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the production pipeline.

    Returns:
        argparse.Namespace: Parsed arguments object.
    """
    parser = argparse.ArgumentParser(
        description="AEGF (Architect-Expert-Gap-Forge) V11 - Module-Aware Two-Pass",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage examples:
  # Test mode: 3 fragments, 4 workers
  python -m src.factory.cli --test 3 --workers 4

  # Full production: 16 workers for Blackwell
  python -m src.factory.cli --workers 16

  # Limit to 10 raw files
  python -m src.factory.cli --limit 10 --workers 8

  # RESUME interrupted run (continues where it left off)
  python -m src.factory.cli --resume data/synthetic/v11_diversified_20260223_092107.jsonl --workers 16

  # THEORY dataset (HA 2026 doctrine)
  python -m src.factory.cli --theory --workers 8

  # Resume interrupted theory
  python -m src.factory.cli --theory --resume data/synthetic/v11_theory_20260223_100000.jsonl

  # Theory with more repetitions per section
  python -m src.factory.cli --theory --theory-reps 5 --workers 16

  # Quick theory test
  python -m src.factory.cli --theory --test 3 --workers 4

  # Custom model and output
  python -m src.factory.cli --model qwen3-32b --output data/my_dataset.jsonl

  # Process Jinja2 templates from custom folder
  python -m src.factory.cli --raw-dir data/raw/homeassistant-jinja --extensions .jinja .jinja2 .yaml .yml --workers 16

  # Combine: custom folder + extensions + quick test
  python -m src.factory.cli --raw-dir data/raw/homeassistant-jinja --extensions .jinja .jinja2 --test 10 --workers 4

  # Custom gap directory for master documents
  python -m src.factory.cli --gap-dir /path/to/gap/docs --workers 16
        """,
    )
    parser.add_argument(
        "--test",
        type=int,
        default=None,
        metavar="N",
        help="Test mode: process only N total fragments for quick validation",
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
        help=f"Number of parallel async workers (default: {DEFAULT_WORKERS})",
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
        "--api-key", type=str, default=DEFAULT_API_KEY, help="Server API key"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        metavar="PATH",
        help="Custom JSONL output path",
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="Seed for reproducibility (default: 42)"
    )
    parser.add_argument(
        "--think-filter",
        dest="think_filter",
        action="store_true",
        default=True,
        help="Apply inline think-block distillation before writing (default: enabled)",
    )
    parser.add_argument(
        "--no-think-filter",
        dest="think_filter",
        action="store_false",
        help="Disable inline think-block distillation",
    )
    parser.add_argument(
        "--think-filter-min-chars",
        type=int,
        default=5000,
        metavar="N",
        help="Only distil think blocks >= N chars (default: 5000)",
    )
    parser.add_argument(
        "--resume",
        type=str,
        default=None,
        metavar="PATH",
        help="Resume run: path to previous output JSONL. "
        "Reads already-processed checkpoint_keys and skips those fragments.",
    )
    parser.add_argument(
        "--raw-dir",
        type=str,
        default="data/raw/homeassistant-main_txt",
        metavar="DIR",
        help="Input directory with packed .txt files (default: data/raw/homeassistant-main_txt)",
    )
    parser.add_argument(
        "--extensions",
        type=str,
        nargs="+",
        default=None,
        metavar="EXT",
        help="Filter only files with these extensions inside .txt packs "
        "(e.g. --extensions .jinja .jinja2 .yaml .yml). Processes all if not specified.",
    )
    parser.add_argument(
        "--theory",
        action="store_true",
        default=False,
        help="Theory mode: generate pure doctrine dataset from MASTER_GUIDE and CHANGELOG",
    )
    parser.add_argument(
        "--theory-reps",
        type=int,
        default=3,
        metavar="R",
        help="Repetitions per section in --theory mode (default: 3, generates diverse questions)",
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
        help="Path to prompts_taxonomy.yaml (default: auto-resolved from project root)",
    )
    # Logging / UI control
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Logging level (default: INFO)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        default=False,
        help="Quiet mode: set logging to ERROR",
    )
    parser.add_argument(
        "--no-rich",
        action="store_true",
        default=False,
        help="Disable Rich-formatted output (use plain logging)",
    )
    parser.add_argument(
        "--no-downgrade-fragment-warnings",
        dest="downgrade_fragment_warnings",
        action="store_false",
        default=True,
        help="Do not downgrade 'Fragment extraction error' warnings to INFO",
    )
    parser.add_argument(
        "--no-live",
        action="store_true",
        default=False,
        help="Disable the Rich live panel UI even when Rich is enabled",
    )
    return parser.parse_args()


def display_startup_panel(args: argparse.Namespace) -> None:
    """Display a startup panel with pipeline configuration.

    Args:
        args: Parsed command-line arguments.
    """
    console = get_console()

    # Build configuration summary
    config_lines = [
        f"[bold]Workers:[/bold]\t{args.workers}",
        f"[bold]Model:[/bold]\t{args.model}",
        f"[bold]Base URL:[/bold]\t{args.base_url}",
        f"[bold]Seed:[/bold]\t{args.seed}",
    ]

    if args.theory:
        config_lines.extend(
            [
                "[bold]Mode:[/bold]\tTHEORY",
                f"[bold]Repetitions:[/bold]\t{args.theory_reps}",
            ]
        )
    else:
        config_lines.extend(
            [
                "[bold]Mode:[/bold]\tNORMAL",
                f"[bold]Output:[/bold]\t{args.output or 'auto-generated'}",
            ]
        )

    config_text = "\n".join(config_lines)

    panel_title = "[bold cyan]AEGF Factory Pipeline - V11[/bold cyan]"
    console.print(
        Panel(
            config_text,
            title=panel_title,
            border_style="cyan",
            padding=(1, 2),
        )
    )


def display_summary_panel(stats: dict) -> None:
    """Display a summary panel after pipeline completion.

    Args:
        stats: Dictionary with pipeline statistics.
    """
    console = get_console()

    # Build summary table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")

    for metric, value in stats.items():
        table.add_row(metric, str(value))

    panel = Panel(
        table,
        title="[bold green]Pipeline Summary[/]",
        border_style="green",
        padding=(1, 2),
    )
    console.print(panel)


def main() -> None:
    """Main entry point for the CLI.

    Loads environment variables, configures logging, parses arguments,
    and runs the async pipeline.
    """
    # Load environment variables from .env file if present
    load_dotenv()

    # Parse args early so logger/UI can be configured accordingly
    args = parse_args()
    random.seed(args.seed)

    console = get_console()

    # Decide whether to use Rich (only when not explicitly disabled and
    # when stdout looks like a terminal).
    use_rich = (not args.no_rich) and console.is_terminal

    # Optionally start a Live panel that will be updated with the latest
    # log message. We only enable Live when Rich is available and enabled.
    live = None
    if use_rich and (not args.no_live):
        try:
            from rich.live import Live

            initial_panel = Panel("Iniciando...", title="[bold cyan]AEGF Pipeline - V11[/]")
            live = Live(initial_panel, console=console, refresh_per_second=4)
            live.start()
        except Exception:
            live = None

    # Configure logger with requested options
    effective_level = "ERROR" if args.quiet else args.log_level
    configure_logger(
        level=effective_level,
        use_rich=use_rich,
        downgrade_fragment_warnings=args.downgrade_fragment_warnings,
        live=live,
        console=console,
    )

    # Display Rich startup panel
    display_startup_panel(args)

    # Resolve project base directory (data_factory/)
    base_dir = Path(__file__).resolve().parent.parent.parent

    # Resolve taxonomy path if provided (pipeline_runner handles loading internally)
    if args.taxonomy:
        taxonomy_path = Path(args.taxonomy)
        if not taxonomy_path.exists():
            raise FileNotFoundError(f"Taxonomy file not found: {taxonomy_path}")
        logger.info("Using taxonomy: %s", taxonomy_path)

    # Resolve gap directory for master documents
    if args.gap_dir:
        args._gap_dir = Path(args.gap_dir)
    else:
        args._gap_dir = base_dir / "data" / "Gap"

    if not args._gap_dir.exists():
        logger.warning("Gap directory not found: %s", args._gap_dir)

    # Run the async pipeline
    import asyncio

    try:
        asyncio.run(main_async(args))
    finally:
        # Ensure live panel is stopped cleanly
        if live is not None:
            try:
                live.stop()
            except Exception:
                pass


if __name__ == "__main__":
    main()
