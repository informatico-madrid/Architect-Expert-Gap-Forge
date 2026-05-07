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
import json
import logging
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from infrastructure.baselines._shared import (
    BaselineError,
    _sanitize_output_dict,
    check_output_lock,
    release_lock,
    validate_input_file,
    write_output_atomic,
    _is_float_like,
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


def _derive_composite(scores: dict[str, float]) -> float:
    """Derive composite score from judge_scores dict using SCORING_WEIGHTS.

    Prefers pre-computed composite_score when available (FR-002.5).

    Args:
        scores: Dict of dimension names to float scores.

    Returns:
        Computed composite score.
    """
    if "composite_score" in scores:
        return scores["composite_score"]
    total = 0.0
    for dim, weight in SCORING_WEIGHTS.items():
        total += scores.get(dim, 0.0) * weight
    return total


def _impl(args: argparse.Namespace) -> int:
    """Actual implementation logic.

    Args:
        args: Parsed argparse namespace.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    logger.info("spearman baseline CLI initialized")

    dataset = Path(args.dataset)
    output = Path(args.output)

    # --- Input validation pipeline ---
    try:
        validate_input_file(dataset)
    except BaselineError as e:
        _die(str(e))

    # Read and parse JSON
    try:
        raw = json.loads(dataset.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        _die(f"Invalid JSON in dataset: {e}")
    except OSError as e:
        _die(f"Cannot read dataset file: {e}")

    # Validate JSON has required keys
    if "baseline_composites" not in raw:
        _die("Missing required key 'baseline_composites' in dataset JSON")
    if "adapter_composites" not in raw:
        _die("Missing required key 'adapter_composites' in dataset JSON")

    baseline_raw = raw["baseline_composites"]
    adapter_raw = raw["adapter_composites"]

    # Validate both values are lists
    if not isinstance(baseline_raw, list):
        _die(f"'baseline_composites' must be a list, got {type(baseline_raw).__name__}")
    if not isinstance(adapter_raw, list):
        _die(f"'adapter_composites' must be a list, got {type(adapter_raw).__name__}")

    # Validate raw array lengths match before zip silently truncates
    if len(baseline_raw) != len(adapter_raw):
        _die(
            f"Array length mismatch: baseline has {len(baseline_raw)} entries, "
            f"adapter has {len(adapter_raw)} entries"
        )

    # Derive composites: handle pre-computed composites or judge_scores
    # None/null entries are accepted (treated as NaN, filtered later)
    baseline_composites: list[float | None] = []
    adapter_composites: list[float | None] = []

    for i, (b_entry, a_entry) in enumerate(zip(baseline_raw, adapter_raw)):
        # If entries are dicts with judge_scores, derive composite
        if isinstance(b_entry, dict):
            baseline_composites.append(_derive_composite(b_entry))
        elif b_entry is None or _is_float_like(b_entry):
            baseline_composites.append(float(b_entry) if b_entry is not None else None)
        else:
            _die(
                f"baseline_composites[{i}] has invalid type {type(b_entry).__name__}, expected float"
            )

        if isinstance(a_entry, dict):
            adapter_composites.append(_derive_composite(a_entry))
        elif a_entry is None or _is_float_like(a_entry):
            adapter_composites.append(float(a_entry) if a_entry is not None else None)
        else:
            _die(
                f"adapter_composites[{i}] has invalid type {type(a_entry).__name__}, expected float"
            )

    # Validate lengths are equal
    if len(baseline_composites) != len(adapter_composites):
        _die(
            f"Array length mismatch: baseline has {len(baseline_composites)} values, "
            f"adapter has {len(adapter_composites)} values"
        )

    # Filter NaN/None values, preserving index pairing
    paired_b: list[float] = []
    paired_a: list[float] = []
    for b, a in zip(baseline_composites, adapter_composites):
        b_nan = b is None or (isinstance(b, float) and math.isnan(b))
        a_nan = a is None or (isinstance(a, float) and math.isnan(a))
        if not (b_nan or a_nan):
            paired_b.append(b)
            paired_a.append(a)

    n = len(paired_b)
    logger.info("Validated %d records after NaN filtering", n)

    # --- Dry-run mode ---
    if args.dry_run:
        file_path = dataset.resolve()
        file_size = file_path.stat().st_size
        method = "exact" if n < 10 else "asymptotic"

        print(f"Input file: {file_path}")
        print(f"File size: {file_size} bytes")
        print(f"Records (after NaN filtering): {n}")
        print(f"Expected method: {method}")

        if n < 3:
            if n == 0:
                print("Edge case: No valid data points after NaN filtering")
            elif n == 1:
                print("Edge case: Single data point -- correlation is undefined")
            else:
                print("Edge case: Only 2 data points -- correlation is always +-1.0")

        print("DRY RUN complete. No output file written.")
        return 0

    # --- No-overwrite check ---
    if output.exists() and output.stat().st_size > 0:
        if args.no_overwrite:
            _die(
                f"Output file already exists: {output}. "
                f"Use --no-overwrite to prevent overwriting."
            )
        else:
            print(
                f"Output file exists: {output}. Overwriting.",
                file=sys.stderr,
            )

    # --- Output directory creation ---
    os.makedirs(output.parent, exist_ok=True)

    # ── Task 1.10: Spearman computation, edge cases, and atomic output ──

    # 1. Edge case detection BEFORE scipy call
    if n == 0:
        status = "no_valid_data"
        score = None
        p_value = None
        reason = "All data points are NaN or non-numeric"
        score_description = "rho: Spearman rank correlation, range [-1, 1]"
    elif n == 1:
        status = "single_sample_undefined"
        score = None
        p_value = None
        reason = "Single sample — correlation is undefined"
        score_description = "rho: Spearman rank correlation, range [-1, 1]"
    elif n == 2:
        status = "insufficient_samples"
        score = None
        p_value = None
        reason = "rho for 2 points is always ±1.0 (perfect correlation), meaningless for baseline"
        score_description = "rho: Spearman rank correlation, range [-1, 1]"
    else:
        # Check for constant input
        b_constant = all(math.isclose(paired_b[0], v) for v in paired_b)
        a_constant = all(math.isclose(paired_a[0], v) for v in paired_a)
        if b_constant or a_constant:
            status = "constant_input"
            score = 0.0
            p_value = 1.0
            reason = "One or both arrays contain constant values"
            score_description = "rho: Spearman rank correlation, range [-1, 1]"
        else:
            reason = None
            # 2. Determine method: n<10 → "exact", n>=10 → "asymptotic"
            method = "exact" if n < 10 else "asymptotic"
            logger.info("Computing Spearman rho (n=%d, method=%s)", n, method)

            # 3. Call scipy.stats.spearmanr (method param added in scipy 1.18)
            from scipy.stats import spearmanr
            import scipy

            _scipy_has_method = tuple(
                int(x) for x in scipy.__version__.split(".")[:2]
            ) >= (1, 18)
            if _scipy_has_method:
                result = spearmanr(paired_b, paired_a, method=method)
            else:
                result = spearmanr(paired_b, paired_a)
            rho = float(result.correlation)
            p_val = float(result.pvalue)

            # 4. Clamp rho to [-1.0, 1.0]
            if rho < -1.0 or rho > 1.0:
                logger.warning("rho outside [-1, 1]: %.6f — clamping", rho)
                rho = max(-1.0, min(1.0, rho))

            score = round(rho, 10)
            p_value = round(p_val, 10)
            status = "ok"
            score_description = "rho: Spearman rank correlation, range [-1, 1]"

    # 5. Build output JSON
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    output_dict = {
        "schema_version": "1",
        "type": "spearman_baseline",
        "timestamp": timestamp,
        "score": score,
        "status": status,
        "score_description": score_description,
        "details": {
            "method": "exact" if n < 10 else ("asymptotic" if n >= 10 else None),
            "n": n,
            "p_value": None,
            "reason": reason if status != "ok" else None,
        },
    }

    # Overwrite p_value with actual value when available
    if status in ("ok", "constant_input"):
        output_dict["details"]["p_value"] = p_value

    # 6. Sanitize output dict (handles NaN/inf → null, numpy floats)
    output_dict = _sanitize_output_dict(output_dict)

    # 7. Validate output parent directory is NOT a symlink (R1 fix)
    output_parent = Path(args.output).resolve().parent
    if output_parent.is_symlink():
        _die(
            f"Output directory is a symlink: {output_parent}. "
            "Refusing to write to symlinked paths for security."
        )

    # 8. Acquire lock, write atomically, release lock
    lock_path = check_output_lock(output)
    try:
        write_output_atomic(output, output_dict)
    finally:
        release_lock(lock_path)

    print(f"Wrote output to {output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
