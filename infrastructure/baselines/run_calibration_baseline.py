# Architect-Expert-Gap-Forge: Baseline Measurement — Calibration CLI
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

"""Calibration baseline measurement CLI — scaffold."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from infrastructure.baselines._shared import (
    BaselineError,
    validate_input_file,
)
from src.audit.calibration_schema import CALIBRATION_GRID
from src.audit.schema import CALIBRATION_SCORING_WEIGHTS

logger = logging.getLogger(__name__)

# ── Stage detection ──────────────────────────────────────────────────────

STAGE_6_KEYS = {"parameter_effectiveness", "coherence", "parameter_alignment", "task_completion", "style"}


def detect_stage(results: list[dict[str, Any]]) -> str:
    """Detect whether calibration results are Stage 5, Stage 6, or mixed.

    Args:
        results: List of calibration result entries.

    Returns:
        "stage6" if any entry has Stage 6 keys,
        "stage5" if no entries have Stage 6 keys,
        "unknown" if results is empty.
    """
    if not results:
        return "unknown"

    has_stage6: list[bool] = []
    for entry in results:
        js = entry.get("judge_scores", {})
        has_stage6_keys = bool(set(js.keys()) & STAGE_6_KEYS)
        has_stage6.append(has_stage6_keys)

    if any(has_stage6):
        if not all(has_stage6):
            logger.warning(
                "Mixed-stage data detected; using Stage 6 weight set for all entries"
            )
        return "stage6"

    return "stage5"


def _die(msg: str) -> None:
    """Print error to stderr and exit with code 1."""
    logger.error(msg)
    sys.exit(1)


def main(argv: list[str] | None = None) -> int:
    """Entry point: parse args, log setup, dispatch to _impl."""
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s", stream=sys.stderr)
    parser = argparse.ArgumentParser(
        description="Compute calibration baseline metrics from scoring results."
    )
    parser.add_argument(
        "--dataset",
        required=True,
        help="Path to JSON file with calibration results",
    )
    parser.add_argument(
        "--ldi-source",
        default=None,
        help="Path to JSON/JSONL file with LDI scores",
    )
    parser.add_argument(
        "--ldi-threshold",
        type=float,
        default=0.01,
        help="LDI pass threshold (default: 0.01)",
    )
    parser.add_argument(
        "--output",
        default="baseline_results/calibration_baseline.json",
        help="Output JSON path (default: baseline_results/calibration_baseline.json)",
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

    return _impl(args)


def _impl(args: argparse.Namespace) -> int:
    """Calibration baseline logic: validate, parse, detect stage, extract metrics.

    Returns:
        0 on success, 1 on error.
    """
    # ── Input validation ──────────────────────────────────────────────────
    dataset_path = Path(args.dataset)
    try:
        validate_input_file(dataset_path)
    except BaselineError as e:
        logger.error("Validation failed: %s", e)
        return 1

    # ── Parse JSON ────────────────────────────────────────────────────────
    try:
        raw = dataset_path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse JSON: %s", e)
        return 1

    # Handle both formats: {"calibration_results": [...]} and top-level [{...}, ...]
    if isinstance(data, dict):
        results: list[dict[str, Any]] = data.get("calibration_results", [])
    elif isinstance(data, list):
        results = data
    else:
        logger.error("Expected JSON object or array at top level")
        return 1

    if not results:
        logger.error("Calibration results list is empty")
        return 1

    # ── Stage detection ───────────────────────────────────────────────────
    stage = detect_stage(results)
    logger.info("Detected calibration stage: %s", stage)
    logger.info("Number of results: %d", len(results))

    # ── Dry-run: report and exit ──────────────────────────────────────────
    if args.dry_run:
        logger.info("Dry-run complete — stage=%s, results=%d", stage, len(results))
        return 0

    # ── Coherence extraction ──────────────────────────────────────────────
    coherenties: list[float | None] = []
    for entry in results:
        if stage == "stage6":
            js = entry.get("judge_scores", {})
            val = js.get("coherence")
            if val is not None:
                if not (0.0 <= val <= 1.0):
                    logger.warning(
                        "Coherence value out of [0,1] range: %s — including in mean",
                        val,
                    )
                coherenties.append(float(val))
            else:
                coherenties.append(None)
        else:
            # Stage 5: coherence is null (not derived from composite_score)
            coherenties.append(None)

    # Compute mean coherence (skip None values)
    valid_coherences = [c for c in coherenties if c is not None]
    mean_coherence = sum(valid_coherences) / len(valid_coherences) if valid_coherences else None

    # ── Composite score computation ───────────────────────────────────────
    composite_scores: list[float | None] = []
    for entry in results:
        if stage == "stage6":
            js = entry.get("judge_scores", {})
            score = sum(
                float(js.get(dim, 0.0)) * weight
                for dim, weight in CALIBRATION_SCORING_WEIGHTS.items()
            )
            composite_scores.append(score)
        else:
            # Stage 5: use pre-computed composite_score from fixture
            val = entry.get("composite_score")
            composite_scores.append(float(val) if val is not None else None)

    valid_composites = [s for s in composite_scores if s is not None]
    mean_composite = sum(valid_composites) / len(valid_composites) if valid_composites else None

    # ── Build output ──────────────────────────────────────────────────────
    now = datetime.now(timezone.utc)
    output = {
        "baseline_type": "calibration",
        "generated_at": now.isoformat(),
        "stage": stage,
        "result_count": len(results),
        "metrics": {
            "mean_composite_score": round(mean_composite, 6) if mean_composite is not None else None,
            "mean_coherence": round(mean_coherence, 6) if mean_coherence is not None else None,
        },
    }

    # ── Write output (or dry-run already exited above) ────────────────────
    output_path = Path(args.output)
    if args.no_overwrite and output_path.exists():
        logger.error("Output file already exists: %s", output_path)
        return 1

    from infrastructure.baselines._shared import write_output_atomic, _sanitize_output_dict

    sanitized = _sanitize_output_dict(output)
    write_output_atomic(output_path, sanitized)
    logger.info("Baseline written to %s", output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
