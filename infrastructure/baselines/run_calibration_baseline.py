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
    write_output_atomic,
    check_output_lock,
    release_lock,
    _sanitize_output_dict,
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


def _parse_ldi_source(path: Path, threshold: float) -> tuple[float | None, float | None]:
    """Parse an LDI source file (JSON or JSONL) and compute mean + pass rate.

    Returns:
        (mean_ldi, ldi_pass_rate) — both None if no valid numeric LDI values.
        LDI pass rate is computed as count(ldi >= threshold) / count(valid_numeric_ldi).
    """
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Try JSONL: one JSON object per line
        records: list[dict[str, Any]] = []
        for line in raw.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                logger.warning("Skipping invalid JSONL line: %s", e)
        data = records

    if not isinstance(data, list):
        data = [data]

    ldi_values: list[float] = []
    for record in data:
        if not isinstance(record, dict):
            continue
        raw_val = record.get("ldi")
        if raw_val is None:
            continue
        try:
            ldi_values.append(float(raw_val))
        except (TypeError, ValueError):
            logger.warning("Non-numeric LDI value (%s) — excluding from mean/pass_rate", raw_val)

    if not ldi_values:
        return None, None

    mean_ldi = sum(ldi_values) / len(ldi_values)
    ldi_pass_rate = sum(1 for v in ldi_values if v >= threshold) / len(ldi_values)
    return mean_ldi, ldi_pass_rate


def _impl(args: argparse.Namespace) -> int:
    """Calibration baseline logic: validate, parse, detect stage, extract metrics.

    Returns:
        0 on success, 1 on error.
    """
    # ── Input validation: dataset ─────────────────────────────────────────
    dataset_path = Path(args.dataset)
    try:
        validate_input_file(dataset_path)
    except BaselineError as e:
        logger.error("Dataset validation failed: %s", e)
        return 1

    # ── Input validation: LDI source (if provided) ────────────────────────
    ldi_path = Path(args.ldi_source) if args.ldi_source else None
    if ldi_path is not None:
        try:
            validate_input_file(ldi_path)
        except BaselineError as e:
            logger.error("LDI source validation failed: %s", e)
            return 1

    # ── Parse dataset JSON ────────────────────────────────────────────────
    try:
        raw = dataset_path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse dataset JSON: %s", e)
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

    # ── LDI parsing ───────────────────────────────────────────────────────
    mean_ldi: float | None = None
    ldi_pass_rate: float | None = None
    ldi_record_count = 0

    if ldi_path is not None:
        try:
            mean_ldi, ldi_pass_rate = _parse_ldi_source(ldi_path, args.ldi_threshold)
            # Count records for dry-run reporting
            try:
                ldi_raw = ldi_path.read_text(encoding="utf-8")
                ldi_data = json.loads(ldi_raw)
                if isinstance(ldi_data, list):
                    ldi_record_count = len(ldi_data)
                else:
                    ldi_record_count = 1
            except (json.JSONDecodeError, Exception):
                # JSONL fallback — count non-empty lines
                ldi_record_count = sum(1 for line in ldi_raw.strip().splitlines() if line.strip())
        except Exception as e:
            logger.warning("LDI source failed: %s — treating as missing", e)
            mean_ldi = None
            ldi_pass_rate = None
    else:
        logger.warning("--ldi-source not provided; mean_ldi and ldi_pass_rate will be null")

    # ── Coherence extraction ──────────────────────────────────────────────
    coherences: list[float | None] = []
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
                coherences.append(float(val))
            else:
                coherences.append(None)
        else:
            # Stage 5: coherence is null (not derived from composite_score)
            coherences.append(None)

    # Compute mean coherence (skip None values)
    valid_coherences = [c for c in coherences if c is not None]
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

    # ── Dry-run: report and exit ──────────────────────────────────────────
    if args.dry_run:
        info = f"Dataset: {dataset_path} ({dataset_path.stat().st_size} bytes, {len(results)} records)"
        logger.info("%s", info)
        logger.info("Detected stage: %s", stage)
        if mean_coherence is not None:
            logger.info("Mean coherence: %.6f", mean_coherence)
        else:
            logger.info("Mean coherence: N/A (no valid values)")
        if ldi_path is not None:
            logger.info("LDI source: %s (%d records)", ldi_path, ldi_record_count)
            if mean_ldi is not None:
                logger.info("Mean LDI: %.6f", mean_ldi)
            else:
                logger.info("Mean LDI: N/A (no valid numeric values)")
            if ldi_pass_rate is not None:
                logger.info("LDI pass rate (>= %.2f): %.6f", args.ldi_threshold, ldi_pass_rate)
            else:
                logger.info("LDI pass rate: N/A")
        else:
            logger.info("LDI source: not provided")
        logger.info("DRY RUN complete. No output file written.")
        return 0

    # ── Build output JSON ─────────────────────────────────────────────────
    now = datetime.now(timezone.utc)
    grid_config = {k: v for k, v in CALIBRATION_GRID.items()}

    output: dict[str, Any] = {
        "schema_version": "1",
        "type": "calibration_baseline",
        "timestamp": now.strftime("%Y-%m-%dT%H:%M:%S") + "Z",
        "score": round(mean_composite, 6) if mean_composite is not None else None,
        "status": "ok",
        "score_description": "mean_coherence: average coherence score, range [0, 1]",
        "details": {
            "mean_coherence": round(mean_coherence, 6) if mean_coherence is not None else None,
            "mean_ldi": round(mean_ldi, 6) if mean_ldi is not None else None,
            "ldi_pass_rate": round(ldi_pass_rate, 6) if ldi_pass_rate is not None else None,
            "grid_config": grid_config,
            "data_stage": stage,
            "n_entries": len(results),
        },
    }

    # ── Output: no-overwrite check ────────────────────────────────────────
    output_path = Path(args.output)
    if args.no_overwrite and output_path.exists():
        logger.error("Output file already exists: %s", output_path)
        return 1

    # ── Output: validate parent dir is not a symlink ──────────────────────
    output_parent = output_path.resolve().parent
    if output_parent.is_symlink():
        logger.error("Output directory is a symlink: %s — refusing to write", output_parent)
        return 1

    # ── Output: atomic write with lock ────────────────────────────────────
    lock_path = check_output_lock(output_path)
    try:
        sanitized = _sanitize_output_dict(output)
        write_output_atomic(output_path, sanitized)
    finally:
        release_lock(lock_path)

    logger.info("Wrote output to %s", output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
