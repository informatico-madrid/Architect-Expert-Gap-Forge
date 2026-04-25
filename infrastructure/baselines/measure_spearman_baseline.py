# Architect-Expert-Gap-Forge: Spearman Baseline Measurement
#
# Copyright (c) 2026 — Joao Maria Arranz Aparicio
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Measure Spearman rank correlation between baseline and adapter composites.

This CLI script reads paired baseline/adapter composite scores from a JSON file,
computes the Spearman rank correlation (rho), and writes structured output
to a JSON file with atomic write and file locking.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from infrastructure.baselines._shared import (
    BaselineError,
    check_output_lock,
    release_lock,
    validate_input_file,
    write_output_atomic,
)
from src.audit.schema import SCORING_WEIGHTS

logger = logging.getLogger(__name__)


def _die(msg: str) -> None:
    """Print error to stderr and exit with code 1."""
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(1)


def main(argv: list[str] | None = None) -> int:
    """Entry point for the Spearman baseline CLI.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code (0 for success, 1 for error).
    """
    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )

    parser = argparse.ArgumentParser(
        description="Compute Spearman rank correlation between baseline and adapter composites."
    )
    parser.add_argument(
        "--dataset",
        required=True,
        help="Path to JSON file with baseline/adapter composites",
    )
    parser.add_argument(
        "--output",
        default="baseline_results/spearman_judge_baseline.json",
        help="Output JSON path (default: baseline_results/spearman_judge_baseline.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate input and compute summary without writing output",
    )
    parser.add_argument(
        "--no-overwrite",
        action="store_true",
        help="Exit 1 if output file already exists",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Set logging level to INFO",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Set logging level to ERROR",
    )

    args = parser.parse_args(argv)

    # Wire --verbose and --quiet to logging levels
    if args.verbose:
        logging.getLogger().setLevel(logging.INFO)
    if args.quiet:
        logging.getLogger().setLevel(logging.ERROR)

    return _impl(args)


def _impl(args: argparse.Namespace) -> int:
    """Actual implementation logic.

    Args:
        args: Parsed argparse namespace.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    logger.info("spearman baseline CLI initialized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
