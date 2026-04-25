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
import json
import logging
import math
import sys
from datetime import datetime, timezone
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
    _sanitize_output_dict,
)
from src.audit.calibration_schema import CALIBRATION_GRID

logger = logging.getLogger(__name__)


def _die(msg: str) -> None:
    """Print error to stderr and exit with code 1."""
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(1)


def _compute_grid_info(grid: dict) -> tuple[int, dict]:
    """Compute profiles_tested from CALIBRATION_GRID.

    profiles_tested = product of len(v) for all v in grid.values()
    MUST NOT hard-code the value 4500
    """
    profiles_tested = math.prod(len(v) for v in grid.values()) if grid else 0
    grid_config = {k: v for k, v in grid.items()}
    return profiles_tested, grid_config


def main(argv: list[str] | None = None) -> int:
    """Entry point: parse args, log setup, dispatch to _impl."""
    logging.basicConfig(
        level=logging.WARNING, format="%(levelname)s: %(message)s", stream=sys.stderr
    )
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

    try:
        return _impl(args)
    except BaselineError as e:
        _die(str(e))


def _impl(args: argparse.Namespace) -> int:
    """MIPRO compile baseline logic."""
    # ── Step 1: Parse CALIBRATION_GRID ────────────────────────────────────
    profiles_tested, grid_config = _compute_grid_info(CALIBRATION_GRID)
    logger.info("Grid parsed: %d profiles_tested", profiles_tested)

    # ── Step 2: Mode selection (measured vs estimated) ────────────────────
    source = "estimated"
    score = None
    estimated = True
    total_iterations = profiles_tested * args.num_prompts

    if args.dataset:
        dataset_path = Path(args.dataset)
        try:
            validate_input_file(dataset_path)
        except BaselineError as e:
            logger.error("Dataset validation failed: %s", e)
            return 1
        try:
            report = json.loads(dataset_path.read_text(encoding="utf-8"))
            exec_time = report.get("statistics", {}).get("execution_time_seconds")
            if exec_time is not None and isinstance(exec_time, (int, float)):
                score = float(exec_time)
                source = "measured"
                estimated = False
                logger.info("Measured mode: execution_time_seconds = %.2f", score)
            else:
                logger.warning(
                    "CalibrationReport missing execution_time_seconds; "
                    "falling back to estimated mode"
                )
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            raise BaselineError(
                f"Dataset exists but is invalid: {dataset_path}. "
                "Cannot fall back to estimated mode when a dataset is explicitly provided."
            )

    if score is None:
        score = total_iterations * args.avg_latency
        logger.warning(
            "WARNING: This is an ESTIMATED duration based on placeholder values. "
            "Actual compile time may differ significantly."
        )

    # ── Step 3: Dry-run ──────────────────────────────────────────────────
    if args.dry_run:
        print(
            f"Dataset: {args.dataset or '(estimated mode)'} "
            f"(profiles_tested={profiles_tested}, total_iterations={total_iterations})"
        )
        print(
            f"Estimated mode: {source} | avg_latency={args.avg_latency}s | duration={score:.2f}s"
        )
        print(f"Target output: {args.output}")
        print("DRY RUN complete. No output file written.")
        return 0

    # ── Step 4: Output path validation ───────────────────────────────────
    output_path = Path(args.output)
    output_parent = output_path.parent.resolve()

    # no-overwrite check
    if args.no_overwrite and output_path.exists() and output_path.stat().st_size > 0:
        raise BaselineError(
            f"Output file already exists: {output_path}. "
            "Remove it or drop --no-overwrite."
        )

    # Validate output parent is NOT a symlink (security)
    if output_parent.is_symlink():
        raise BaselineError(
            f"Output directory is a symlink: {output_parent}. "
            "Refusing to write to symlinked paths for security."
        )

    if not output_parent.is_dir():
        raise BaselineError(f"Output directory does not exist: {output_parent}")

    # ── Step 5: Build output dict ────────────────────────────────────────
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    output_dict = {
        "schema_version": "1",
        "type": "mipro_compile",
        "timestamp": timestamp,
        "score": score,
        "status": "ok",
        "score_description": "duration_seconds: wall-clock compile time in seconds",
        "details": {
            "grid_config": grid_config,
            "total_iterations": total_iterations,
            "profiles_tested": profiles_tested,
            "source": source,
            "avg_latency_seconds": args.avg_latency,
            "duration_seconds": score,
            "estimated": estimated,
        },
    }

    # ── Step 6: Atomic write ─────────────────────────────────────────────
    lock_path = check_output_lock(output_path)
    try:
        sanitized = _sanitize_output_dict(output_dict)
        write_output_atomic(output_path, sanitized)
    finally:
        release_lock(lock_path)

    print(f"Wrote output to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
