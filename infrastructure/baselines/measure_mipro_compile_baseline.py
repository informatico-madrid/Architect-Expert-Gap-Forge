# Architect-Expert-Gap-Forge: MIPRO Compile Baseline Measurement
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

"""MIPRO compile time baseline measurement — CLI scaffold."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from infrastructure.baselines._shared import (
    BaselineError,
    validate_input_file,
)

logger = logging.getLogger(__name__)


def _die(msg: str) -> None:
    """Print error to stderr and exit with code 1."""
    logger.error(msg)
    sys.exit(1)


def main(argv: list[str] | None = None) -> int:
    """Entry point: parse args, log setup, dispatch to _impl."""
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s", stream=sys.stderr)
    parser = argparse.ArgumentParser(
        description="Compute MIPRO compile-time baseline metrics."
    )
    parser.add_argument(
        "--dataset",
        default=None,
        help="Path to CalibrationReport JSON (measured mode)",
    )
    parser.add_argument(
        "--num-prompts",
        type=int,
        default=6,
        help="Number of prompts for estimate (default: 6)",
    )
    parser.add_argument(
        "--avg-latency",
        type=float,
        default=0.5,
        help="Average latency per iteration (default: 0.5)",
    )
    parser.add_argument(
        "--output",
        default="baseline_results/mipro_compile_baseline.json",
        help="Output JSON path (default: baseline_results/mipro_compile_baseline.json)",
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

    if args.verbose:
        logging.getLogger().setLevel(logging.INFO)
    if args.quiet:
        logging.getLogger().setLevel(logging.ERROR)

    # Validate num-prompts must be positive
    if args.num_prompts < 1:
        _die("num-prompts must be positive")

    # Clamp avg-latency to 0 if negative
    if args.avg_latency < 0:
        logger.warning("Clamping avg-latency from %s to 0.0", args.avg_latency)
        args.avg_latency = 0.0

    return _impl(args)


def _impl(args: argparse.Namespace) -> int:
    """MIPRO compile baseline logic (placeholder)."""
    logger.info("MIPRO compile baseline CLI scaffold — placeholder")
    logger.info("Dataset: %s", args.dataset)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
