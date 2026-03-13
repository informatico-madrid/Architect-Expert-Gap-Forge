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
import os
import sys
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv

from src.discovery.metadata_enricher import ProcessingConfig, RepoProcessor

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

    # Validate config file exists
    if not os.path.exists(parsed.config):
        logger.error("Config not found: %s", parsed.config)
        return 1

    try:
        # Load configuration
        with open(parsed.config, "r") as f:
            config_data = yaml.safe_load(f)

        # Handle Path serialization from YAML
        if "base_dir" in config_data and isinstance(config_data["base_dir"], str):
            config_data["base_dir"] = Path(config_data["base_dir"])

        config = ProcessingConfig(**config_data)

        # Run processor
        processor = RepoProcessor(config)
        processor.run()

        logger.info("Processor completed successfully")
        return 0

    except Exception as e:
        logger.critical("Processor failed: %s", e)
        if parsed.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
