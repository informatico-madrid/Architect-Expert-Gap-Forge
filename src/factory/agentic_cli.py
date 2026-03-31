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

from __future__ import annotations

import argparse
import json
import logging
import random
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from tqdm import tqdm

from src.factory.config import load_factory_config
from src.factory.schema import TrajectoryMode
from src.factory.trajectory_generator import TrajectoryGenerator

# ══════════════════════════════════════════════════════════════════════
# RICH TERMINAL OUTPUT
# ══════════════════════════════════════════════════════════════════════

_console: Console | None = None


def get_console() -> Console:
    """Get or create the Rich console instance."""
    global _console
    if _console is None:
        _console = Console()
    return _console


def display_start_panel(use_case: str, mode: str, config_path: str) -> None:
    """Display a startup panel with configuration.

    Args:
        use_case: The use case being processed.
        mode: Generation mode (explicit, hard_query, no_call).
        config_path: Path to configuration file.
    """
    console = get_console()

    config_lines = [
        f"[bold]Use Case:[/bold]\t{use_case}",
        f"[bold]Mode:[/bold]\t{mode}",
        f"[bold]Config:[/bold]\t{config_path}",
    ]

    config_text = "\n".join(config_lines)

    panel_title = "[bold cyan]AEGF V10-MT Trajectory Generator[/]"
    console.print(
        Panel(
            config_text,
            title=panel_title,
            border_style="cyan",
            padding=(1, 2),
        )
    )


def display_summary_panel(records_generated: int, output_path: str, dry_run: bool) -> None:
    """Display a summary panel after generation completion.

    Args:
        records_generated: Number of records generated.
        output_path: Path to output file.
        dry_run: Whether this was a dry run.
    """
    console = get_console()

    # Build summary table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")

    table.add_row("Records Generated", str(records_generated))
    table.add_row("Output Path", output_path)
    table.add_row("Dry Run", "Yes" if dry_run else "No")

    panel = Panel(
        table,
        title="[bold green]Generation Complete[/]",
        border_style="green",
        padding=(1, 2),
    )
    console.print(panel)


def display_error_panel(error_message: str) -> None:
    """Display an error panel.

    Args:
        error_message: The error message to display.
    """
    console = get_console()

    panel = Panel(
        f"[red]{error_message}[/]",
        title="[bold red]Error[/]",
        border_style="red",
        padding=(1, 2),
    )
    console.print(panel)

# ══════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════
DEFAULT_BASE_URL = "http://localhost:8000/v1"
DEFAULT_API_KEY = "sk-master-bunker-2026"
DEFAULT_MODEL = "qwen3-5-35b-a3b-nvfp4"
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
    )

    # Add subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # =========================================================================
    # Legacy mode (default behavior - no subcommand)
    # =========================================================================
    legacy_parser = subparsers.add_parser(
        "run",
        help="Run the legacy generation pipeline (default behavior)",
    )
    legacy_parser.add_argument(
        "--test",
        type=int,
        default=None,
        metavar="N",
        help="Test mode: process only N fragments",
    )
    legacy_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Limit to N raw input files",
    )
    legacy_parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        metavar="W",
        help=f"Async parallel workers (default: {DEFAULT_WORKERS})",
    )
    legacy_parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help=f"Inference model (default: {DEFAULT_MODEL})",
    )
    legacy_parser.add_argument(
        "--base-url",
        type=str,
        default=DEFAULT_BASE_URL,
        help=f"vLLM server URL (default: {DEFAULT_BASE_URL})",
    )
    legacy_parser.add_argument(
        "--api-key",
        type=str,
        default=DEFAULT_API_KEY,
        help="Server API key",
    )
    legacy_parser.add_argument(
        "--output",
        type=str,
        default=None,
        metavar="PATH",
        help="Custom JSONL output path",
    )
    legacy_parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Seed for reproducibility (default: 42)",
    )
    legacy_parser.add_argument(
        "--resume",
        type=str,
        default=None,
        metavar="PATH",
        help="Resume: path to previous output JSONL.",
    )
    legacy_parser.add_argument(
        "--gap-dir",
        type=str,
        default=None,
        metavar="DIR",
        help="Directory containing master documents (default: data/Gap relative to project root)",
    )
    legacy_parser.add_argument(
        "--taxonomy",
        type=str,
        default=None,
        metavar="PATH",
        help="Path to agentic_taxonomy.yaml (default: auto-resolved from project root)",
    )
    legacy_parser.add_argument(
        "--raw-dir",
        type=str,
        default="data/raw/homeassistant-main_txt",
        metavar="DIR",
        help="Input directory with packed .txt files (default: data/raw/homeassistant-main_txt)",
    )

    # =========================================================================
    # Generate-trajectories command (T012)
    # =========================================================================
    traj_parser = subparsers.add_parser(
        "generate-trajectories",
        help="Generate agentic trajectories with error injection (US1)",
    )
    traj_parser.add_argument(
        "--use-case",
        type=str,
        default="home_assistant",
        metavar="NAME",
        help="Use case domain (default: home_assistant)",
    )
    traj_parser.add_argument(
        "--mode",
        type=str,
        default="explicit",
        choices=["explicit", "hard_query", "no_call"],
        metavar="MODE",
        help="Trajectory generation mode (default: explicit)",
    )
    traj_parser.add_argument(
        "--config",
        type=str,
        default=None,
        metavar="PATH",
        help="Path to YAML config file (default: configs/stage_2_factory/config.homeassistant.yaml)",
    )
    traj_parser.add_argument(
        "--output",
        type=str,
        default=None,
        metavar="PATH",
        help="Output JSONL path (overrides config)",
    )
    traj_parser.add_argument(
        "--target-records",
        type=int,
        default=None,
        metavar="N",
        help="Target number of records (overrides config dataset.target_specialized_records)",
    )
    traj_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without writing output (for testing)",
    )
    traj_parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )

    # Set default command to "run" for backward compatibility
    parser.set_defaults(command="run")

    return parser.parse_args()


def main() -> None:
    """Main entry point for the CLI."""
    args = parse_args()

    # Dispatch to appropriate handler based on command
    if args.command == "generate-trajectories":
        main_generate_trajectories(args)
    else:
        # Legacy mode (run command or backward compatibility)
        main_legacy(args)


def main_legacy(args: argparse.Namespace) -> None:
    """Legacy pipeline entry point."""
    import asyncio

    from src.factory.agentic_prompt_builder import (
        HA_ERROR_TEMPLATES,
        LEGACY_2023_PATTERNS,
        TOOLS_DEFINITION,
        load_taxonomy,
    )
    from src.factory.agentic_runner import main_async

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


def main_generate_trajectories(args: argparse.Namespace) -> None:
    """Generate agentic trajectories with error injection (T012).

    Args:
        args: Parsed command-line arguments
    """
    import asyncio
    import sys

    # Resolve base_dir (project root: 3 levels up from this file)
    base_dir = Path(__file__).resolve().parent.parent.parent

    # Determine config path
    if args.config:
        config_path = base_dir / args.config
    else:
        config_path = base_dir / "configs" / "stage_2_factory" / "config.homeassistant.yaml"

    if not config_path.exists():
        console = get_console()
        console.print(f"[bold red]Error:[/] Config file not found: {config_path}")
        sys.exit(1)

    # Load configuration
    try:
        factory_config = load_factory_config(config_path)
    except Exception as e:
        console = get_console()
        console.print(f"[bold red]Error loading config:[/] {e}")
        sys.exit(1)

    # Get config values (use CLI overrides if provided)
    dataset_config = factory_config.dataset
    output_config = factory_config.output

    # CLI overrides
    use_case = args.use_case or dataset_config.use_case
    output_path_str = args.output or dataset_config.output_path
    target_records = args.target_records or dataset_config.target_specialized_records
    is_dry_run = args.dry_run or output_config.dry_run

    # Map mode string to TrajectoryMode enum
    mode_map = {
        "explicit": TrajectoryMode.EXPLICIT,
        "hard_query": TrajectoryMode.HARD_QUERY,
        "no_call": TrajectoryMode.NO_CALL,
    }
    trajectory_mode = mode_map.get(args.mode, TrajectoryMode.EXPLICIT)

    # Determine output path
    output_path = base_dir / output_path_str

    # Display Rich startup panel
    display_start_panel(use_case, args.mode, str(config_path))

    if is_dry_run:
        console = get_console()
        console.print("[bold yellow][DRY RUN][/] No output will be written.")
        return

    # Load seed examples
    seeds_path = base_dir / "tests" / "fixtures" / "seed_examples.yaml"
    if not seeds_path.exists():
        console = get_console()
        console.print(f"[bold red]Error:[/] Seeds file not found: {seeds_path}")
        console.print("[dim]Please create tests/fixtures/seed_examples.yaml with seed data.[/]")
        sys.exit(1)

    try:
        import yaml

        with open(seeds_path, encoding="utf-8") as f:
            seeds_data = yaml.safe_load(f)
    except Exception as e:
        console = get_console()
        console.print(f"[bold red]Error loading seeds:[/] {e}")
        sys.exit(1)

    seeds = seeds_data.get("seeds", [])
    if not seeds:
        console = get_console()
        console.print("[bold red]Error:[/] No seeds found in seed file.")
        sys.exit(1)

    # Initialize trajectory generator
    generator = TrajectoryGenerator(
        use_case=use_case,
        mode=trajectory_mode,
        error_probability=dataset_config.trajectory.error_probability,
        cascade_failure_probability=dataset_config.trajectory.cascade_probability,
        templates_path=base_dir / "configs" / "stage_2_factory" / "prompts" / "trajectory_templates.yaml",
        hard_query_templates_path=base_dir / "configs" / "stage_2_factory" / "prompts" / "hard_query_templates.yaml",
        seed=args.seed,
    )

    # Generate trajectories with Rich progress bar
    console = get_console()
    console.print(f"[bold]Generating {target_records} trajectories...[/]")

    records_to_generate = min(target_records, len(seeds) * 10)  # Reuse seeds if needed

    async def generate_all() -> list[dict]:
        """Generate all trajectories asynchronously."""
        results = []

        with tqdm(total=records_to_generate, desc="Generating", unit="record") as pbar:
            for i in range(records_to_generate):
                seed = seeds[i % len(seeds)].copy()
                seed["seed_id"] = f"{seed.get('seed_id', 'seed')}_{i}"

                trajectory = await generator.generate(seed)

                # Convert to dict for JSONL output
                record = {
                    "seed_id": trajectory.seed_id,
                    "use_case": trajectory.use_case,
                    "mode": trajectory.mode.value,
                    "turns": [
                        {
                            "turn_index": t.turn_index,
                            "turn_type": t.turn_type.value,
                            "content": t.content,
                            "tool_name": t.tool_name,
                            "tool_args": t.tool_args,
                        }
                        for t in trajectory.turns
                    ],
                    "errors": [
                        {
                            "error_type": e.error_type.value,
                            "turn_index": e.turn_index,
                            "description": e.description,
                            "recovery_turn_index": e.recovery_turn_index,
                        }
                        for e in trajectory.errors
                    ],
                    "messages": [{"role": m.role, "content": m.content} for m in trajectory.messages],
                }
                results.append(record)
                pbar.update(1)

        return results

    # Run generation
    results = asyncio.run(generate_all())

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for record in results:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # Display Rich summary panel
    display_summary_panel(len(results), str(output_path), is_dry_run)


if __name__ == "__main__":
    main()
