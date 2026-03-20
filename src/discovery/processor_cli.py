# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Processor CLI Module
===================
Command-line interface for the AEGF Module-Aware Processor.
Provides the main entry point for running the processor from the command line.

Author: Joao Maria Arranz Aparicio
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv

from src.discovery.metadata_enricher import ProcessingConfig, RepoProcessor
from src.utils.rich_helpers import (
    create_table,
    get_console,
)

# --- Project Root ---
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)


def configure_logger(level: int = logging.INFO) -> None:
    """Configure logging for the processor.

    Args:
        level: Logging level (default: INFO)
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M",
    )


def parse_args(args: Optional[list] = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        args: Optional list of arguments (default: sys.argv)

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="AEGF Module-Aware Processor V2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--config", "-c", required=True, help="Path to YAML configuration"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )
    return parser.parse_args(args)


def main(args: Optional[list] = None) -> int:
    """Main entry point for the CLI.

    Args:
        args: Optional list of arguments (default: sys.argv)

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Load environment variables
    load_dotenv()

    # Parse arguments
    parsed = parse_args(args)

    # Configure logging
    log_level = logging.DEBUG if parsed.verbose else logging.INFO
    configure_logger(log_level)

    # Resolve config path relative to PROJECT_ROOT if relative
    config_path = (
        Path(parsed.config)
        if Path(parsed.config).is_absolute()
        else PROJECT_ROOT / parsed.config
    )

    # Validate config file exists
    if not config_path.exists():
        logger.error("Config not found: %s", config_path)
        return 1

    # Rich console setup
    console = get_console()

    # Initialize config for header display
    config: Optional[ProcessingConfig] = None

    try:
        # Load configuration
        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f)

        # Handle Path serialization from YAML
        if "base_dir" in config_data and isinstance(config_data["base_dir"], str):
            config_data["base_dir"] = Path(config_data["base_dir"])

        config = ProcessingConfig(**config_data)

        # Rich startup header
        console.print("\n[bold blue]=== AEGF Module-Aware Processor ===[/bold blue]")
        console.print(f"[cyan]Base Directory:[/cyan] {config.base_dir}")
        console.print(f"[cyan]Category:[/cyan] {config.category}")
        console.print(f"[cyan]Raw Subdir:[/cyan] {config.raw_subdir}")
        console.print(f"[cyan]Output Subdir:[/cyan] {config.output_subdir}")
        console.print(f"[cyan]Profile:[/cyan] {config.profile}\n")

        # Run processor
        processor = RepoProcessor(config)
        processor.run()

        # Rich summary table
        console.print("[bold green]=== Processing Summary ===[/bold green]")
        summary_table = create_table(title="[bold cyan]Processor Results[/bold cyan]")
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", justify="right")
        summary_table.add_row("Modules Found", str(processor._stats.get("modules_found", 0)))
        summary_table.add_row("Type 1 Units", str(processor._stats.get("TYPE1_FUNCTIONAL_UNIT", 0)))
        summary_table.add_row("Type 3 Logic Only", str(processor._stats.get("TYPE3_LOGIC_ONLY", 0)))
        summary_table.add_row("Type 4 Blueprints", str(processor._stats.get("TYPE4_MODULE_BLUEPRINT", 0)))
        summary_table.add_row("Type 5 Governance", str(processor._stats.get("TYPE5_GOVERNANCE_RULES", 0)))
        summary_table.add_row("Parse Errors", str(processor._stats.get("parse_errors", 0)))
        console.print(summary_table)
        console.print(f"\n[cyan]Output:[/cyan] {config.base_dir / config.output_subdir}\n")

        logger.info("Processor completed successfully")
        return 0

    except Exception as e:
        logger.critical("Processor failed: %s", e)
        console.print(f"\n[bold red]Error:[/bold red] {e}\n")
        if parsed.verbose:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
