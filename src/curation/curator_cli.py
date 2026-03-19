#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""AEGF — Curator CLI Module.

Command-line interface for the NeMo Curator Suite pipeline.
"""

from __future__ import annotations

import argparse
import glob
import logging
import os
import shutil
import sys
import tempfile
from datetime import datetime
from typing import List, Optional

from src.curation import curator_pipeline
from src.curation.curator_pipeline import (
    CurationStats,
    _NEMO_AVAILABLE,
    load_jsonl,
    run_nemo_filter_pipeline,
    save_report,
    write_jsonl,
)
from src.curation import dedup_filter
from src.curation.dedup_filter import exact_dedup, semantic_dedup
from src.curation import quality_filter
from src.curation.quality_filter import structural_quality_filter
from src.curation.dataset_mixer import (
    DatasetMixer,
    DatasetMixerConfig,
    load_specialized_records,
)

# Re-export defaults for CLI
DEFAULT_MIN_WORDS = curator_pipeline.DEFAULT_MIN_WORDS
DEFAULT_MAX_SYMBOL_RATIO = curator_pipeline.DEFAULT_MAX_SYMBOL_RATIO
DEFAULT_MAX_NON_ALPHA_RATIO = curator_pipeline.DEFAULT_MAX_NON_ALPHA_RATIO
DEFAULT_MAX_URL_RATIO = curator_pipeline.DEFAULT_MAX_URL_RATIO
DEFAULT_MAX_NO_ENDMARK_RATIO = curator_pipeline.DEFAULT_MAX_NO_ENDMARK_RATIO
DEFAULT_MAX_BOILERPLATE_RATIO = curator_pipeline.DEFAULT_MAX_BOILERPLATE_RATIO
DEFAULT_MAX_REPEATED_LINES = curator_pipeline.DEFAULT_MAX_REPEATED_LINES
DEFAULT_MAX_NGRAM_RATIO = curator_pipeline.DEFAULT_MAX_NGRAM_RATIO
DEFAULT_NGRAM_SIZE = curator_pipeline.DEFAULT_NGRAM_SIZE

DEFAULT_MIN_THINK_CHARS = quality_filter.DEFAULT_MIN_THINK_CHARS
DEFAULT_LDI_MIN_RATIO = quality_filter.DEFAULT_LDI_MIN_RATIO

DEFAULT_DEDUP_THRESHOLD = dedup_filter.DEFAULT_DEDUP_THRESHOLD
DEFAULT_QUALITY_CUTOFF = dedup_filter.DEFAULT_QUALITY_CUTOFF
DEFAULT_MINHASH_PERMS = dedup_filter.DEFAULT_MINHASH_PERMS
DEFAULT_SHINGLE_K = dedup_filter.DEFAULT_SHINGLE_K

DEFAULT_REPORTS_DIR = curator_pipeline.DEFAULT_REPORTS_DIR

logger = logging.getLogger(__name__)


# ===========================================================================
# CLI
# ===========================================================================


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nemo_curator_suite",
        description=(
            "AEGF NeMo Curator Suite -- four-phase quality curation for JSONL datasets.\n\n"
            "Phases:\n"
            "  --exact-dedup   Phase 0: SHA-256 exact deduplication\n"
            "  --filter        Phase 1: NeMo Curator quality filters (container required)\n"
            "  --structural    Phase 2: Syntax, think-depth, LDI, meta-speech filters\n"
            "  --dedup         Phase 3: MinHash-LSH semantic deduplication\n\n"
            "⚠️  Phase 1 requires the aegf_curator container:\n"
            "    cd deploy/docker && docker compose up -d curator\n"
            "    docker exec -it aegf_curator bash\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    io = parser.add_argument_group("I/O")
    io.add_argument("--input", help="Source JSONL file.")
    io.add_argument("--output", help="Output JSONL file.")
    io.add_argument(
        "--reports-dir",
        default=DEFAULT_REPORTS_DIR,
        metavar="DIR",
        help=f"Directory for JSON statistics (default: {DEFAULT_REPORTS_DIR}).",
    )

    phases = parser.add_argument_group("Pipeline phases (at least one required)")
    phases.add_argument(
        "--exact-dedup",
        dest="do_exact_dedup",
        action="store_true",
        help="Phase 0: exact SHA-256 deduplication.",
    )
    phases.add_argument(
        "--filter",
        dest="do_filter",
        action="store_true",
        help="Phase 1: NeMo Curator quality-filter pipeline (needs container).",
    )
    phases.add_argument(
        "--structural",
        dest="do_structural",
        action="store_true",
        help="Phase 2: structural quality gate (syntax, LDI, think-depth).",
    )
    phases.add_argument(
        "--dedup",
        dest="do_dedup",
        action="store_true",
        help="Phase 3: MinHash-LSH semantic deduplication.",
    )

    ex = parser.add_argument_group("Execution")
    ex.add_argument(
        "--apply",
        action="store_true",
        help="Write output file. Without this flag runs in dry-run mode.",
    )
    ex.add_argument(
        "--sample",
        type=int,
        default=0,
        metavar="N",
        help="Process only first N records for quick validation (0 = all).",
    )

    ft = parser.add_argument_group("Phase 1 -- NeMo filter thresholds")
    ft.add_argument("--min-words", type=int, default=DEFAULT_MIN_WORDS)
    ft.add_argument("--max-symbol-ratio", type=float, default=DEFAULT_MAX_SYMBOL_RATIO)
    ft.add_argument(
        "--max-non-alpha-ratio", type=float, default=DEFAULT_MAX_NON_ALPHA_RATIO
    )
    ft.add_argument("--max-url-ratio", type=float, default=DEFAULT_MAX_URL_RATIO)
    ft.add_argument(
        "--max-no-endmark-ratio", type=float, default=DEFAULT_MAX_NO_ENDMARK_RATIO
    )
    ft.add_argument(
        "--max-boilerplate-ratio", type=float, default=DEFAULT_MAX_BOILERPLATE_RATIO
    )
    ft.add_argument(
        "--max-repeated-lines", type=float, default=DEFAULT_MAX_REPEATED_LINES
    )
    ft.add_argument("--max-ngram-ratio", type=float, default=DEFAULT_MAX_NGRAM_RATIO)
    ft.add_argument("--ngram-size", type=int, default=DEFAULT_NGRAM_SIZE)

    st = parser.add_argument_group("Phase 2 -- Structural filter thresholds")
    st.add_argument(
        "--min-think-chars",
        type=int,
        default=DEFAULT_MIN_THINK_CHARS,
        help=f"Minimum chars in <think> block (default: {DEFAULT_MIN_THINK_CHARS}).",
    )
    st.add_argument(
        "--ldi-min-ratio",
        type=float,
        default=DEFAULT_LDI_MIN_RATIO,
        help=f"Minimum LDI ratio on <tool_call> block (default: {DEFAULT_LDI_MIN_RATIO}).",
    )
    st.add_argument(
        "--no-attempt-check",
        dest="no_attempt_check",
        action="store_true",
        help="Disable attempt_completion check (use for single-turn / production_v11 data).",
    )

    dt = parser.add_argument_group("Phase 3 -- Dedup thresholds")
    dt.add_argument(
        "--dedup-threshold",
        type=float,
        default=DEFAULT_DEDUP_THRESHOLD,
        help=f"MinHash similarity threshold (default: {DEFAULT_DEDUP_THRESHOLD}).",
    )
    dt.add_argument(
        "--quality-cutoff",
        type=float,
        default=DEFAULT_QUALITY_CUTOFF,
        help=f"Minimum heuristic quality score (default: {DEFAULT_QUALITY_CUTOFF}).",
    )
    dt.add_argument(
        "--minhash-perms",
        type=int,
        default=DEFAULT_MINHASH_PERMS,
        help=f"Number of MinHash permutations (default: {DEFAULT_MINHASH_PERMS}).",
    )
    dt.add_argument(
        "--shingle-k",
        type=int,
        default=DEFAULT_SHINGLE_K,
        help=f"Character shingle size (default: {DEFAULT_SHINGLE_K}).",
    )

    # Mix datasets command arguments
    mx = parser.add_argument_group("Mix datasets (Stage 3)")
    mx.add_argument(
        "--mix-datasets",
        dest="do_mix_datasets",
        action="store_true",
        help="Run mix-datasets command to combine specialized and anchor datasets.",
    )
    mx.add_argument(
        "--specialized-jsonl",
        type=str,
        help="Path to specialized dataset JSONL file.",
    )
    mx.add_argument(
        "--anchor-configs",
        type=str,
        help="Path to anchor dataset configs YAML file.",
    )
    mx.add_argument(
        "--output-jsonl",
        dest="output_jsonl",
        type=str,
        help="Output path for mixed JSONL file.",
    )
    mx.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for deterministic shuffling (default: 42).",
    )
    mx.add_argument(
        "--target-records",
        type=int,
        default=None,
        help="Target total number of records after mixing.",
    )
    mx.add_argument(
        "--report",
        type=str,
        help="Output path for composition report JSON.",
    )
    mx.add_argument(
        "--specialized-pct",
        type=float,
        default=30.0,
        help="Target percentage for specialized dataset tokens (default: 30.0).",
    )
    mx.add_argument(
        "--anchor-pct",
        type=float,
        default=70.0,
        help="Target percentage for anchor dataset tokens (default: 70.0).",
    )

    return parser


# ===========================================================================
# Main
# ===========================================================================


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Handle mix-datasets command separately
    if args.do_mix_datasets:
        return _run_mix_datasets(args, parser)

    # Validate arguments for regular pipeline phases
    if not any(
        [args.do_exact_dedup, args.do_filter, args.do_structural, args.do_dedup]
    ):
        parser.error(
            "At least one phase required: --exact-dedup / --filter / --structural / --dedup / --mix-datasets"
        )

    # Validate required I/O for regular phases
    if not args.input:
        parser.error("--input is required for pipeline phases")
    if not args.output:
        parser.error("--output is required for pipeline phases")

    if not os.path.exists(args.input):
        logger.error("Input file not found: %s", args.input)
        return 1

    dry_run = not args.apply
    phases = "+".join(
        x
        for x, f in [
            ("exact-dedup", args.do_exact_dedup),
            ("filter", args.do_filter),
            ("structural", args.do_structural),
            ("dedup", args.do_dedup),
        ]
        if f
    )
    logger.info(
        "AEGF NeMo Curator Suite | phases=%s | input=%s | dry_run=%s | sample=%d",
        phases,
        args.input,
        dry_run,
        args.sample,
    )

    stats = CurationStats()
    current_path = args.input

    temp_files: List[str] = []
    temp_dirs: List[str] = []

    def _next_temp() -> str:
        """Create a guaranteed-unique temp FILE and register it for cleanup."""
        tmp = tempfile.NamedTemporaryFile(
            suffix=".jsonl", prefix="aegf_cur_", delete=False
        )
        path = tmp.name
        tmp.close()
        temp_files.append(path)
        return path

    def _next_temp_dir() -> str:
        """Create a guaranteed-unique temp DIRECTORY and register it for cleanup.

        NeMo Curator's JsonlWriter expects a directory path, not a file path.
        """
        d = tempfile.mkdtemp(prefix="aegf_nemo_out_")
        temp_dirs.append(d)
        return d

    def _merge_jsonl_dir(src_dir: str, dest_file: str) -> int:
        """Merge all *.jsonl shards written by NeMo into a single flat file.

        Returns the total number of records written.
        """
        count = 0
        shards = sorted(glob.glob(os.path.join(src_dir, "*.jsonl")))
        if not shards:
            # NeMo may nest one level deeper
            shards = sorted(
                glob.glob(os.path.join(src_dir, "**", "*.jsonl"), recursive=True)
            )
        with open(dest_file, "w", encoding="utf-8") as fout:
            for shard in shards:
                with open(shard, "r", encoding="utf-8") as fin:
                    for line in fin:
                        line = line.strip()
                        if line:
                            fout.write(line + "\n")
                            count += 1
        return count

    # -----------------------------------------------------------------------
    # Phase 0 -- Exact dedup (in-memory)
    # -----------------------------------------------------------------------
    if args.do_exact_dedup:
        logger.info("Phase 0 -- Exact deduplication")
        records = load_jsonl(current_path, sample=args.sample)
        stats.total_input = stats.total_input or len(records)
        records = exact_dedup(records, stats)
        if not dry_run:
            tmp = _next_temp()
            write_jsonl(tmp, records)
            current_path = tmp
        else:
            logger.info(
                "[DRY-RUN] Would continue with %d records after exact dedup",
                len(records),
            )

    # -----------------------------------------------------------------------
    # Phase 1 -- NeMo Curator filter (requires container)
    # -----------------------------------------------------------------------
    if args.do_filter:
        if not _NEMO_AVAILABLE:
            logger.error(
                "nemo-curator not installed.\n"
                "Run inside aegf_curator container:\n"
                "  cd deploy/docker && docker compose up -d curator\n"
                "  docker exec -it aegf_curator bash"
            )
            return 1
        if dry_run:
            logger.info("[DRY-RUN] Would run NeMo filter pipeline on: %s", current_path)
        else:
            logger.info("Phase 1 -- NeMo Curator filtering")
            # JsonlWriter requires a DIRECTORY -- use mkdtemp, not a .jsonl file
            nemo_dir = _next_temp_dir()
            pre_nemo_count = sum(
                1 for line in open(current_path, "r", encoding="utf-8") if line.strip()
            )
            run_nemo_filter_pipeline(
                input_path=current_path,
                output_path=nemo_dir,
                min_words=args.min_words,
                max_symbol_ratio=args.max_symbol_ratio,
                max_non_alpha_ratio=args.max_non_alpha_ratio,
                max_url_ratio=args.max_url_ratio,
                max_no_endmark_ratio=args.max_no_endmark_ratio,
                max_boilerplate_ratio=args.max_boilerplate_ratio,
                max_repeated_lines=args.max_repeated_lines,
                max_ngram_ratio=args.max_ngram_ratio,
                ngram_size=args.ngram_size,
            )
            # Merge NeMo shards -> single flat JSONL for next phase
            nemo_merged = _next_temp()
            post_nemo_count = _merge_jsonl_dir(nemo_dir, nemo_merged)
            removed_by_nemo = pre_nemo_count - post_nemo_count
            stats.nemo_filtered += removed_by_nemo
            logger.info(
                "Phase 1 complete: %d --> %d records (%d removed by NeMo filters)",
                pre_nemo_count,
                post_nemo_count,
                removed_by_nemo,
            )
            current_path = nemo_merged

    # -----------------------------------------------------------------------
    # Phase 2 -- Structural quality gate (in-memory)
    # -----------------------------------------------------------------------
    if args.do_structural:
        logger.info("Phase 2 -- Structural quality filter")
        if stats.total_input == 0:
            records = load_jsonl(current_path, sample=args.sample)
            stats.total_input = len(records)
        else:
            records = load_jsonl(current_path, sample=args.sample)
        records = structural_quality_filter(
            records,
            stats,
            min_think_chars=args.min_think_chars,
            ldi_min_ratio=args.ldi_min_ratio,
            check_attempt_completion=not args.no_attempt_check,
        )
        if not dry_run:
            tmp = _next_temp()
            write_jsonl(tmp, records)
            current_path = tmp
        else:
            logger.info(
                "[DRY-RUN] Would continue with %d records after structural filter",
                len(records),
            )

    # -----------------------------------------------------------------------
    # Phase 3 -- Semantic dedup (in-memory)
    # -----------------------------------------------------------------------
    if args.do_dedup:
        logger.info("Phase 3 -- Semantic deduplication")
        if stats.total_input == 0:
            records = load_jsonl(current_path, sample=args.sample)
            stats.total_input = len(records)
        else:
            records = load_jsonl(current_path, sample=args.sample)
        records = semantic_dedup(
            records,
            stats,
            threshold=args.dedup_threshold,
            quality_cutoff=args.quality_cutoff,
            num_perm=args.minhash_perms,
            shingle_k=args.shingle_k,
        )
        if not dry_run:
            tmp = _next_temp()
            write_jsonl(tmp, records)
            current_path = tmp
        else:
            logger.info(
                "[DRY-RUN] Would continue with %d records after semantic dedup",
                len(records),
            )

    # -----------------------------------------------------------------------
    # Finalize
    # -----------------------------------------------------------------------
    if dry_run:
        logger.info("[DRY-RUN] Final output not written (use --apply to write)")
        stats.total_output = 0
    else:
        # Move final temp to requested output
        shutil.copy(current_path, args.output)
        stats.total_output = sum(
            1 for line in open(args.output, "r", encoding="utf-8") if line.strip()
        )
        logger.info(
            "Final output written: %s (%d records)", args.output, stats.total_output
        )

    # Cleanup
    for f in temp_files:
        try:
            os.unlink(f)
        except OSError:
            pass
    for d in temp_dirs:
        try:
            shutil.rmtree(d)
        except OSError:
            pass

    # Report
    stats.print_report()
    if args.reports_dir:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        report_path = save_report(
            stats.as_dict(), args.reports_dir, f"curation_{timestamp}.json"
        )
        logger.info("Report saved: %s", report_path)

    return 0


# =============================================================================
# Mix Datasets Command
# =============================================================================


def _run_mix_datasets(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    """Run the mix-datasets command.

    Args:
        args: Parsed command-line arguments.
        parser: ArgumentParser for error reporting.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    from pathlib import Path

    # Validate required arguments
    if not args.specialized_jsonl:
        parser.error("--specialized-jsonl is required for --mix-datasets")
    if not args.anchor_configs:
        parser.error("--anchor-configs is required for --mix-datasets")
    if not args.output_jsonl:
        parser.error("--output-jsonl is required for --mix-datasets")

    specialized_path = Path(args.specialized_jsonl)
    anchor_configs_path = Path(args.anchor_configs)
    output_path = Path(args.output_jsonl)
    report_path = Path(args.report) if args.report else None

    # Validate input files exist
    if not specialized_path.exists():
        logger.error("Specialized JSONL not found: %s", specialized_path)
        return 1
    if not anchor_configs_path.exists():
        logger.error("Anchor configs not found: %s", anchor_configs_path)
        return 1

    logger.info(
        "Running mix-datasets: specialized=%s, anchors=%s, output=%s",
        specialized_path,
        anchor_configs_path,
        output_path,
    )

    try:
        # Create mixer and load data
        config = DatasetMixerConfig(
            specialized_pct=args.specialized_pct,
            anchor_pct=args.anchor_pct,
            shuffle_seed=args.seed,
            target_records=args.target_records,
        )
        mixer = DatasetMixer(config)

        # Load specialized records
        specialized_records = load_specialized_records(specialized_path)
        logger.info("Loaded %d specialized records", len(specialized_records))

        # Load anchor configs and download
        from src.curation.anchor_dataset_downloader import (
            AnchorDatasetDownloader,
            load_anchor_configs,
        )

        anchor_configs = load_anchor_configs(anchor_configs_path)
        downloader = AnchorDatasetDownloader(anchor_configs)
        anchor_records = downloader.download_all()
        logger.info("Downloaded %d anchor records", len(anchor_records))

        # Mix datasets
        mixed_records = mixer.mix(specialized_records, anchor_records)
        logger.info("Mixed dataset has %d records", len(mixed_records))

        # Export to JSONL
        mixer.export(mixed_records, output_path)
        logger.info("Exported mixed dataset to %s", output_path)

        # Generate and export report
        report = mixer.generate_report(mixed_records)
        logger.info(
            "Composition report: records_by_origin=%s, token_pct_by_origin=%s",
            report.records_by_origin,
            report.token_pct_by_origin,
        )

        if report_path:
            mixer.export_report(report, report_path)
            logger.info("Exported composition report to %s", report_path)

        return 0

    except Exception as e:
        logger.error("Error running mix-datasets: %s", e)
        import traceback

        traceback.print_exc()
        return 1


# For backwards compatibility
if __name__ == "__main__":
    sys.exit(main())
