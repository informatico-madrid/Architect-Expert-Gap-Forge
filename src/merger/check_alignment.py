# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0
"""
Stage 1 merger script: check_alignment.py

Checks alignment between base model and adapter weights.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table


def get_console() -> Console:
    """Get a shared Console instance for the module."""
    if not hasattr(get_console, "_instance"):
        get_console._instance = Console()
    return get_console._instance  # type: ignore[attr-defined]


def check_alignment(base_model_path: str, adapter_path: str) -> dict:
    """Check alignment between base model and adapter weights.

    Args:
        base_model_path: Path to the base model
        adapter_path: Path to the adapter weights

    Returns:
        Dictionary containing alignment metrics
    """
    # Placeholder implementation
    return {"alignment_score": 0.0, "status": "not_implemented"}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Check alignment between models")
    parser.add_argument("--base-model", required=True, help="Path to base model")
    parser.add_argument("--adapter", required=True, help="Path to adapter")
    args = parser.parse_args()

    result = check_alignment(args.base_model, args.adapter)

    console = get_console()

    # Display results in a table
    table = Table(title="Alignment Check Results")
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="bold")

    table.add_row("Base Model", args.base_model)
    table.add_row("Adapter", args.adapter)
    table.add_row("Alignment Score", f"{result.get('alignment_score', 0.0):.2f}")
    table.add_row("Status", result.get("status", "unknown"))

    console.print("")
    console.print(table)

    # Display summary panel
    summary = (
        f"Alignment check completed.\n"
        f"Score: {result.get('alignment_score', 0.0):.2f}\n"
        f"Status: {result.get('status', 'unknown')}"
    )
    console.print(
        Panel(
            summary,
            title="[green]Summary[/]",
            border_style="green",
        )
    )
