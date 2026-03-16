#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
AEGF Audit CLI Module
=====================
Command-line interface for the AEGF Quality Gate evaluation pipeline.

Supports 6 subcommands:
  - sample: Extract and persist a stratified evaluation sample
  - generate-exam: Professor generates novel exam questions
  - baseline: Run inference with base model
  - adapter: Run inference with LoRA adapter
  - score: LLM-as-Judge scoring + audit report
  - full: Run all 5 stages end-to-end
"""

# ARCH-NOTE: This module exceeds 400 LOC (554 lines) to provide a complete CLI
# with 6 subcommands, argument parsing, config loading, and all stage handlers.
# The monolithic structure is justified as this is a user-facing entry point
# that must remain atomic for discoverability and simple deployment.

from __future__ import annotations

import argparse
import dataclasses
import logging
import sys
import textwrap
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from src.audit.config import (
    DEFAULT_ADAPTER_MODEL,
    DEFAULT_API_URL,
    DEFAULT_AUDIT_DIR,
    DEFAULT_BASE_MODEL,
    DEFAULT_GEMINI_MODEL,
    DEFAULT_INFERENCE_BACKEND,
    DEFAULT_JUDGE_MODEL,
    DEFAULT_MAX_TOKENS,
    DEFAULT_PROFESSOR_BACKEND,
    DEFAULT_RETRY_DELAY,
    DEFAULT_RETRIES,
    DEFAULT_SAMPLE_SIZE,
    DEFAULT_TEMPERATURE,
    _get_config,
)
from src.audit.exam_builder import _format_reference_standards, generate_exam_question
from src.audit.gap_generator import generate_gap_analysis
from src.audit.judge import llm_judge_score, run_inference
from src.audit.persistence import (
    load_exam,
    load_inference,
    load_persisted_sample,
    persist_exam,
    persist_inference,
    persist_sample,
)
from src.audit.sampling import load_dataset, stratified_sample
from src.audit.report_writer import generate_report
from src.audit.calibration import run_calibration
from src.audit.inference import InferenceRouter
from src.audit.schema import AuditReport, ExamRecord, PromptGenerationError, SampleRecord, ScoreCard
from src.audit.scorecard import compute_scorecard
from src.utils.doc_loader import load_master_docs

# ======================================================================
# LOGGING
# ======================================================================

logger = logging.getLogger(__name__)


class CLIError(Exception):
    """Domain exception for CLI validation and runtime errors."""


# Lazy config accessor
CFG = _get_config()


# ======================================================================
# SUB-COMMAND HANDLERS
# ======================================================================


def cmd_sample(args: argparse.Namespace) -> None:
    """Extract and persist a stratified evaluation sample."""
    sample_path = Path(args.audit_dir) / "eval_sample.json"
    if sample_path.exists() and not args.force:
        logger.info(
            "Sample already exists at %s (use --force to regenerate)", sample_path
        )
        samples = load_persisted_sample(args.audit_dir)
    else:
        if not args.dataset:
            raise CLIError("--dataset is required for 'sample' mode")
        records = load_dataset(args.dataset)

        gap_dir = Path(args.gap_dir)
        master, changelog, jinja_guide = load_master_docs(gap_dir)

        samples = stratified_sample(records, args.sample_size)

        # SampleRecord is frozen — use dataclasses.replace() to create enriched copies.
        enriched: list[SampleRecord] = []
        for s in samples:
            replacements: dict[str, str] = {}
            if not (s.reference_standards and s.reference_standards.strip()):
                # Format reference standards using domain-agnostic config-driven logic
                replacements["reference_standards"] = _format_reference_standards(
                    master, changelog, jinja_guide
                )
            # Apply reference_standards first (may be needed by generate_gap_analysis)
            s_enriched = dataclasses.replace(s, **replacements) if replacements else s
            if not (s_enriched.gap_analysis and s_enriched.gap_analysis.strip()):
                try:
                    gap = generate_gap_analysis(
                        s_enriched,
                        master,
                        changelog,
                        jinja_guide,
                        professor_backend=args.professor_backend,
                        gemini_model=args.gemini_model,
                        judge_model=args.judge_model,
                        api_url=args.api_url,
                        retries=args.retries,
                        retry_delay=args.retry_delay,
                        validate=args.validate,
                    )
                    s_enriched = dataclasses.replace(s_enriched, gap_analysis=gap)
                except PromptGenerationError as exc:
                    # Propagated from generate_gap_analysis; tested via mock failure
                    logger.error("Gap analysis generation failed for %s: %s", s.id, exc)
                    raise CLIError(
                        f"Gap analysis generation failed for {s.id}: {exc}"
                    ) from exc
            enriched.append(s_enriched)
        samples = enriched

        persist_sample(samples, args.audit_dir)

    dist = Counter(s.example_type for s in samples)
    logger.info("Sample distribution: %s", dict(dist))


def cmd_generate_exam(args: argparse.Namespace) -> None:
    """Professor model generates novel exam questions from the persisted sample."""
    exam_path = Path(args.audit_dir) / "eval_exam.json"
    if exam_path.exists() and not args.force:
        logger.info("Exam already exists at %s (use --force to regenerate)", exam_path)
        exam_records = load_exam(args.audit_dir)
        logger.info("Loaded %d existing exam questions", len(exam_records))
        return

    samples = load_persisted_sample(args.audit_dir)
    missing = [
        s.id
        for s in samples
        if not (s.reference_standards and s.reference_standards.strip())
        or not (s.gap_analysis and s.gap_analysis.strip())
    ]
    if missing:
        logger.error("Persisted sample has records missing HA metadata: %s", missing)
        raise CLIError(
            "Persisted sample validation failed: all records must include reference_standards and gap_analysis."
        )

    judge_model = args.judge_model
    logger.info(
        "Generating %d exam questions with professor model: %s",
        len(samples),
        judge_model,
    )

    exam_records: list[ExamRecord] = []
    for idx, sample in enumerate(samples, 1):
        logger.info(
            "[%d/%d] Generating exam for %s (%s)",
            idx,
            len(samples),
            sample.id,
            sample.fragment_name,
        )
        try:
            record = generate_exam_question(
                sample=sample,
                judge_model=judge_model,
                api_url=args.api_url,
                retries=args.retries,
                retry_delay=args.retry_delay,
                professor_backend=args.professor_backend,
                gemini_model=args.gemini_model,
                validate=args.validate,
            )
        except PromptGenerationError as exc:
            # Propagated from generate_exam_question; tested via mock failure
            logger.error("Exam generation failed for %s: %s", sample.id, exc)
            raise CLIError(f"Exam generation failed for {sample.id}: {exc}") from exc
        exam_records.append(record)

    persist_exam(exam_records, args.audit_dir)
    generated = sum(
        1 for r in exam_records if r.exam_question and r.exam_question != r.user_prompt
    )
    logger.info(
        "Exam generation complete: %d/%d questions generated by professor",
        generated,
        len(samples),
    )


def cmd_baseline(args: argparse.Namespace) -> None:
    """Run baseline inference on exam questions with the base model."""
    try:
        records = load_exam(args.audit_dir)
        logger.info("Using exam questions for baseline inference")
    except FileNotFoundError:
        logger.warning(
            "No exam found — using original sample prompts (run generate-exam first)"
        )
        records = load_persisted_sample(args.audit_dir)

    results = run_inference(
        records,
        model=args.model or args.base_model,
        api_url=args.api_url,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        retries=args.retries,
        retry_delay=args.retry_delay,
        inference_backend=args.inference_backend,
        gemini_model=args.gemini_model,
    )
    persist_inference(results, "baseline", args.audit_dir)


def cmd_adapter(args: argparse.Namespace) -> None:
    """Run adapter inference on exam questions with the LoRA model."""
    try:
        records = load_exam(args.audit_dir)
        logger.info("Using exam questions for adapter inference")
    except FileNotFoundError:
        logger.warning(
            "No exam found — using original sample prompts (run generate-exam first)"
        )
        records = load_persisted_sample(args.audit_dir)

    results = run_inference(
        records,
        model=args.model or args.adapter_model,
        api_url=args.api_url,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        retries=args.retries,
        retry_delay=args.retry_delay,
        inference_backend=args.inference_backend,
        gemini_model=args.gemini_model,
    )
    persist_inference(results, "adapter", args.audit_dir)


def cmd_score(args: argparse.Namespace) -> None:
    """LLM-as-Judge scores adapter vs baseline and generates the audit report."""
    try:
        exam_records = load_exam(args.audit_dir)
    except FileNotFoundError:
        logger.warning("No exam found — scoring without exam criteria")
        raw_samples = load_persisted_sample(args.audit_dir)
        exam_records = [
            ExamRecord.from_sample(s, exam_question=s.user_prompt) for s in raw_samples
        ]

    baseline_results = load_inference("baseline", args.audit_dir)
    adapter_results = load_inference("adapter", args.audit_dir)

    baseline_map = {r.record_id: r for r in baseline_results}
    adapter_map = {r.record_id: r for r in adapter_results}
    judge_model = args.judge_model

    logger.info(
        "Scoring %d records with judge model: %s", len(exam_records), judge_model
    )
    scorecards: list[ScoreCard] = []
    total = len(exam_records)
    for idx, exam in enumerate(exam_records, 1):
        base_r = baseline_map.get(exam.id)
        adapt_r = adapter_map.get(exam.id)
        if not base_r or not adapt_r:
            logger.warning(
                "[%d/%d] Missing inference for %s — skipping", idx, total, exam.id
            )
            continue
        logger.info("[%d/%d] Judging %s", idx, total, exam.id)
        # First, call the judge to get the normalized response
        judge_resp = llm_judge_score(
            exam=exam,
            baseline_resp=base_r.response,
            adapter_resp=adapt_r.response,
            judge_model=judge_model,
            api_url=args.api_url,
            retries=args.retries,
            retry_delay=args.retry_delay,
            professor_backend=args.professor_backend,
            gemini_model=args.gemini_model,
            validate=args.validate,
        )
        # Then compute the scorecard with the judge response
        sc = compute_scorecard(
            exam=exam,
            judge_resp=judge_resp,
            adapter_resp=adapt_r.response,
        )
        scorecards.append(sc)

    report = AuditReport(
        timestamp=datetime.now(timezone.utc).isoformat(),
        dataset_path=args.dataset or "N/A",
        base_model=baseline_results[0].model_name if baseline_results else "N/A",
        adapter_model=adapter_results[0].model_name if adapter_results else "N/A",
        judge_model=judge_model,
        sample_size=len(exam_records),
        type_distribution=dict(Counter(e.example_type for e in exam_records)),
        scorecards=scorecards,
    )

    report_path, report = generate_report(
        report,
        scorecards,
        exam_records,
        baseline_results,
        adapter_results,
        args.audit_dir,
    )
    print(f"\n{'=' * 64}")
    print(f"  AEGF QUALITY GATE — FINAL GRADE: {report.final_grade}/100")
    print(f"  Verdict: {report.verdict}")
    print(f"  Report:  {report_path}")
    print(f"{'=' * 64}\n")


def cmd_full(args: argparse.Namespace) -> None:
    """Run the full 5-stage evaluation pipeline."""
    if args.validate:
        args.sample_size = 1
        args.force = True
        logger.info(
            "Validate mode: sample_size=1, force=True — minimal-token end-to-end flow test"
        )
    logger.info("=== AEGF Quality Gate — High-Fidelity Exam Pipeline ===")

    logger.info("--- Stage 1/5: Stratified Sampling ---")
    cmd_sample(args)

    logger.info("--- Stage 2/5: Exam Generation (Professor) ---")
    cmd_generate_exam(args)

    logger.info("--- Stage 3/5: Baseline Inference ---")
    args.model = None
    cmd_baseline(args)

    logger.info("--- Stage 4/5: Adapter Inference ---")
    args.model = None
    cmd_adapter(args)

    logger.info("--- Stage 5/5: LLM-as-Judge Scoring ---")
    cmd_score(args)


def cmd_calibrate(args: argparse.Namespace) -> None:
    """Run inference parameter calibration (Stage 6)."""
    import json

    logger.info("=== AEGF Inference Calibration Suite (Stage 6) ===")

    # Load prompts from file or from existing exam/sample
    prompts: list[dict[str, str]] = []

    if args.prompts:
        # Load from provided prompts file (supports both JSON and YAML)
        prompts_path = Path(args.prompts)
        if not prompts_path.exists():
            raise CLIError(f"Prompts file not found: {args.prompts}")

        # Detect format by file extension
        import yaml
        if prompts_path.suffix in [".yaml", ".yml"]:
            with open(prompts_path, "r", encoding="utf-8") as f:
                prompts_data = yaml.safe_load(f)
        else:
            # Default to JSON
            with open(prompts_path, "r", encoding="utf-8") as f:
                prompts_data = json.load(f)

        # Handle both formats: list or {"prompts": [...]} or {"prompts": [{"id":..., "text":...}]}
        if isinstance(prompts_data, dict):
            prompts = prompts_data.get("prompts", prompts_data.get("samples", []))
        else:
            prompts = prompts_data

        logger.info("Loaded %d prompts from %s", len(prompts), args.prompts)
    else:
        # Try to load from existing exam or sample
        try:
            exam_records = load_exam(args.audit_dir)
            prompts = [
                {"id": r.id, "text": r.exam_question or r.user_prompt}
                for r in exam_records
            ]
            logger.info("Loaded %d prompts from existing exam", len(prompts))
        except FileNotFoundError:
            try:
                sample_records = load_persisted_sample(args.audit_dir)
                prompts = [
                    {"id": s.id, "text": s.user_prompt}
                    for s in sample_records
                ]
                logger.info("Loaded %d prompts from existing sample", len(prompts))
            except FileNotFoundError:
                raise CLIError(
                    "No prompts provided (--prompts) and no existing exam/sample found. "
                    "Run 'sample' or 'generate-exam' first, or provide --prompts file."
                )

    if not prompts:
        raise CLIError("No prompts available for calibration")

    # Determine checkpoint directory for resume functionality
    # Always save checkpoint (for resume on interrupt), but only load if --resume is set
    checkpoint_dir = args.output_dir

    # Create router for inference clients
    router = InferenceRouter()

    # Create student client (for generating responses with different parameters)
    # Student always uses vLLM to support sampling parameter calibration
    student_client = router.student(
        backend="vllm",  # Always vLLM for parameter control
        gemini_model=args.gemini_model,
        model=args.judge_model,  # The model being calibrated
        api_url=args.api_url,
    )

    # Create judge client (for evaluating responses)
    judge_client = router.professor(
        backend=args.judge_backend,
        gemini_model=args.gemini_model,
        vllm_model=args.judge_model,
        api_url=args.api_url,
        claude_model=args.claude_model,
    )
    logger.info("Calibration: student=vLLM(model=%s), judge=%s(model=%s)", 
                args.judge_model, args.judge_backend,
                args.claude_model if args.judge_backend == "claude" else args.gemini_model if args.judge_backend == "gemini" else args.judge_model)

    # Run calibration
    report = run_calibration(
        prompts=prompts,
        output_dir=args.output_dir,
        verbose=True,
        checkpoint_dir=checkpoint_dir,
        use_prompt_metadata=args.use_prompt_metadata,
        use_noxious_filter=args.use_noxious_filter,
        noxious_loss_threshold=args.noxious_loss_threshold,
        noxious_sample_size=(args.noxious_sample_size if args.noxious_sample_size > 0 else None),
        noxious_aggressiveness=args.noxious_aggressiveness,
        student_client=student_client,
        judge_client=judge_client,
    )

    # Print summary
    print(f"\n{'=' * 64}")
    print("  AEGF INFERENCE CALIBRATION — COMPLETE")
    print(f"  Best Score: {report.best_score:.3f}")
    print(f"  Best Profile: {report.best_profile}")
    print(f"  Total Iterations: {report.total_iterations}")
    print(f"  Output: {args.output_dir}")
    print(f"{'=' * 64}\n")


# ======================================================================
# ARGUMENT PARSER
# ======================================================================


def _shared_parser() -> argparse.ArgumentParser:
    """Build a parent parser with all shared options."""
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help=f"vLLM API endpoint (default: {DEFAULT_API_URL})",
    )
    shared.add_argument(
        "--audit-dir",
        default=DEFAULT_AUDIT_DIR,
        help=f"Output directory for audit artifacts (default: {DEFAULT_AUDIT_DIR})",
    )
    shared.add_argument(
        "--dataset", default=None, help="Path to the training JSONL dataset"
    )
    shared.add_argument(
        "--model", default=None, help="Model name override for inference"
    )
    shared.add_argument(
        "--base-model",
        default=DEFAULT_BASE_MODEL,
        help=f"Base model identifier (default: {DEFAULT_BASE_MODEL})",
    )
    shared.add_argument(
        "--adapter-model",
        default=DEFAULT_ADAPTER_MODEL,
        help=f"LoRA adapter identifier (default: {DEFAULT_ADAPTER_MODEL})",
    )
    shared.add_argument(
        "--judge-model",
        default=DEFAULT_JUDGE_MODEL,
        help=f"Professor/judge model (default: {DEFAULT_JUDGE_MODEL})",
    )
    shared.add_argument(
        "--professor-backend",
        default=DEFAULT_PROFESSOR_BACKEND,
        choices=["auto", "gemini", "vllm"],
        help="Backend for professor/judge calls (default: auto)",
    )
    shared.add_argument(
        "--gemini-model",
        default=DEFAULT_GEMINI_MODEL,
        help=f"Gemini model name (default: {DEFAULT_GEMINI_MODEL})",
    )
    shared.add_argument(
        "--inference-backend",
        default=DEFAULT_INFERENCE_BACKEND,
        choices=["vllm", "gemini"],
        help="Backend for student inference (default: vllm)",
    )
    shared.add_argument(
        "--validate",
        action="store_true",
        help="1-example end-to-end flow test with minimal token spend",
    )
    shared.add_argument(
        "--sample-size",
        type=int,
        default=DEFAULT_SAMPLE_SIZE,
        help=f"Number of records to sample (default: {DEFAULT_SAMPLE_SIZE})",
    )
    shared.add_argument(
        "--gap-dir",
        default=CFG.get("gap_dir", "data/Gap"),
        help="Path to directory containing HA master docs",
    )
    shared.add_argument(
        "--max-tokens",
        type=int,
        default=DEFAULT_MAX_TOKENS,
        help=f"Max generation tokens (default: {DEFAULT_MAX_TOKENS})",
    )
    shared.add_argument(
        "--temperature",
        type=float,
        default=DEFAULT_TEMPERATURE,
        help=f"Sampling temperature (default: {DEFAULT_TEMPERATURE})",
    )
    shared.add_argument(
        "--retries",
        type=int,
        default=DEFAULT_RETRIES,
        help=f"API retry attempts (default: {DEFAULT_RETRIES})",
    )
    shared.add_argument(
        "--retry-delay",
        type=float,
        default=DEFAULT_RETRY_DELAY,
        help=f"Base retry backoff in seconds (default: {DEFAULT_RETRY_DELAY})",
    )
    shared.add_argument(
        "--force", action="store_true", help="Force regeneration of existing artifacts"
    )
    shared.add_argument(
        "-v", "--verbose", action="store_true", help="Enable debug logging"
    )

    # Calibration-specific arguments
    shared.add_argument(
        "--prompts",
        default=None,
        help="Path to JSON file containing prompts for calibration",
    )
    shared.add_argument(
        "--output-dir",
        default="./calibration_results",
        help="Output directory for calibration results (default: ./calibration_results)",
    )
    shared.add_argument(
        "--resume",
        action="store_true",
        help="Resume from checkpoint if available in output directory",
    )
    shared.add_argument(
        "--use-prompt-metadata",
        action="store_true",
        default=False,
        help="Enable intelligent calibration using parameter_target and evaluation_focus from prompts",
    )
    shared.add_argument(
        "--use-noxious-filter",
        action="store_true",
        default=False,
        help="Enable noxious parameter filter to quickly discard values that consistently perform worse than pivot",
    )
    shared.add_argument(
        "--noxious-loss-threshold",
        type=float,
        default=0.15,
        help="Loss threshold used by the noxious pre-filter (default: 0.15)",
    )
    shared.add_argument(
        "--noxious-sample-size",
        type=int,
        default=0,
        help="If >0, sample this many prompts per parameter during pre-filter (faster). 0 = use all prompts",
    )
    shared.add_argument(
        "--noxious-aggressiveness",
        type=float,
        default=0.5,
        help="Fraction [0.0-1.0] of worst values to discard per-parameter during resume aggregation (default: 0.5)",
    )
    shared.add_argument(
        "--judge-backend",
        default="auto",
        choices=["auto", "gemini", "vllm", "claude"],
        help="Backend for judge calls in calibration (default: auto)",
    )
    shared.add_argument(
        "--claude-model",
        default="MiniMax-M2.5",
        help="Claude model name for judge when using --judge-backend claude (default: MiniMax-M2.5)",
    )

    return shared


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    shared = _shared_parser()

    parser = argparse.ArgumentParser(
        prog="model_evaluator",
        description="AEGF Quality Gate — High-Fidelity Exam-Based Evaluation Pipeline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[shared],
        epilog=textwrap.dedent("""\
            Pipeline stages (run in order or all at once with 'full'):
              1. sample          Extract stratified sample from dataset
              2. generate-exam   Professor generates novel exam questions
              3. baseline        Base model inference on exam questions
              4. adapter         LoRA adapter inference on exam questions
              5. score           LLM-as-Judge scoring + audit report

            Examples:
              # One-shot end-to-end:
              %(prog)s full --dataset data/synthetic/v11_PLATINUM_UNIFORM.jsonl \\
                           --base-model qwen3-30b-a3b-thinking-fp8 \\
                           --adapter-model platinum_adapter

              # Step by step:
              %(prog)s sample        --dataset data/synthetic/v11_PLATINUM_UNIFORM.jsonl
              %(prog)s generate-exam --judge-model qwen3-30b-a3b-thinking-fp8
              %(prog)s baseline      --base-model qwen3-30b-a3b-thinking-fp8
              %(prog)s adapter       --adapter-model platinum_adapter
              %(prog)s score         --judge-model qwen3-30b-a3b-thinking-fp8
        """),
    )

    sub = parser.add_subparsers(dest="mode", help="Evaluation stage")
    sub.add_parser(
        "sample", help="Stage 1: Extract stratified sample", parents=[shared]
    )
    sub.add_parser(
        "generate-exam",
        help="Stage 2: Professor generates exam questions",
        parents=[shared],
    )
    sub.add_parser("baseline", help="Stage 3: Base model inference", parents=[shared])
    sub.add_parser("adapter", help="Stage 4: LoRA adapter inference", parents=[shared])
    sub.add_parser(
        "score", help="Stage 5: LLM-as-Judge scoring + report", parents=[shared]
    )
    sub.add_parser("full", help="Run all 5 stages end-to-end", parents=[shared])
    sub.add_parser(
        "calibrate", help="Stage 6: Inference parameter calibration", parents=[shared]
    )

    return parser


def main() -> None:
    """Entry point for the AEGF Quality Gate evaluator."""
    # Load environment variables at runtime (not import time)
    load_dotenv()

    parser = build_parser()
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s │ %(name)s │ %(levelname)s │ %(message)s",
        datefmt="%H:%M:%S",
    )

    if not args.mode:
        parser.print_help()
        sys.exit(1)

    dispatch = {
        "sample": cmd_sample,
        "generate-exam": cmd_generate_exam,
        "baseline": cmd_baseline,
        "adapter": cmd_adapter,
        "score": cmd_score,
        "full": cmd_full,
        "calibrate": cmd_calibrate,
    }

    handler = dispatch.get(args.mode)
    if handler:
        try:
            handler(args)
        except CLIError as exc:
            logger.error("%s", exc)
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
