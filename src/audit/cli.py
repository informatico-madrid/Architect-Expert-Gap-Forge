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
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

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
from src.audit.schema import (
    AuditReport,
    ExamRecord,
    PromptGenerationError,
    SampleRecord,
    ScoreCard,
)
from src.audit.scorecard import compute_scorecard
from src.utils.doc_loader import load_master_docs

# ======================================================================
# LOGGING & RICH CONSOLE
# ======================================================================

logger = logging.getLogger(__name__)

# Rich console instance with TTY auto-detection
_console: Console | None = None


def get_console() -> Console:
    """Get a Rich console instance with auto-detection for TTY."""
    global _console
    if _console is None:
        _console = Console()
    return _console


def print_startup_header(mode: str, description: str) -> None:
    """Print a styled header showing the CLI mode and description."""
    console = get_console()
    console.print(
        Panel(
            f"[bold]{description}[/bold]\n\n[bold cyan]Mode:[/bold cyan] {mode.upper()}",
            title="[bold green]AEGF Quality Gate[/bold green]",
            border_style="green",
            expand=True,
        )
    )


def print_section(title: str, style: str = "bold blue") -> None:
    """Print a section divider with styled text."""
    console = get_console()
    console.print(f"\n[{style}]{'=' * 60}[/]")
    console.print(f"[{style}]  {title}  [/]")
    console.print(f"[{style}]{'=' * 60}[/]\n")


def print_summary_table(metrics: dict[str, str | int | float], title: str = "Summary") -> None:
    """Print a formatted summary table with metrics."""
    console = get_console()
    table = Table(title=f"[bold]{title}[/bold]", show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="cyan", width=20)
    table.add_column("Value", justify="right", style="white")

    for metric, value in metrics.items():
        table.add_row(metric, str(value))

    console.print(table)


def print_success_panel(message: str, title: str = "Success") -> None:
    """Print a success panel with green styling."""
    console = get_console()
    console.print(
        Panel(
            message,
            title=f"[bold green]{title}[/bold green]",
            border_style="green",
            expand=True,
        )
    )


def print_error_panel(message: str, title: str = "Error") -> None:
    """Print an error panel with red styling."""
    console = get_console()
    console.print(
        Panel(
            message,
            title=f"[bold red]{title}[/bold red]",
            border_style="red",
            expand=True,
        )
    )


class CLIError(Exception):
    """Domain exception for CLI validation and runtime errors."""


# Lazy config accessor
CFG = _get_config()


# ======================================================================
# SUB-COMMAND HANDLERS
# ======================================================================


def cmd_sample(args: argparse.Namespace) -> None:
    """Extract and persist a stratified evaluation sample."""
    console = get_console()

    sample_path = Path(args.audit_dir) / "eval_sample.json"
    if sample_path.exists() and not args.force:
        logger.info(
            "Sample already exists at %s (use --force to regenerate)", sample_path
        )
        samples = load_persisted_sample(args.audit_dir)
        print_success_panel(f"Sample already exists at {sample_path}")
        console.print(f"  [bold]Loaded:[/bold] {len(samples)} records")
        dist = Counter(s.example_type for s in samples)
        print_summary_table(dict(dist), "Sample Distribution")
        return

    if not args.dataset:
        raise CLIError("--dataset is required for 'sample' mode")

    records = load_dataset(args.dataset)
    gap_dir = Path(args.gap_dir)
    master, changelog, jinja_guide = load_master_docs(gap_dir)

    samples = stratified_sample(records, args.sample_size)

    # SampleRecord is frozen — use dataclasses.replace() to create enriched copies.
    enriched: list[SampleRecord] = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Processing samples...[/]"),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        transient=True,
    ) as progress:
        total = len(samples)
        task = progress.add_task("Generating gap analysis...", total=total)

        for idx, s in enumerate(samples, 1):
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
            progress.update(task, advance=1)

    samples = enriched
    persist_sample(samples, args.audit_dir)

    # Print summary with Rich table
    dist = Counter(s.example_type for s in samples)
    print_success_panel(
        f"Sample persisted successfully to {sample_path}",
        "Sample Complete",
    )
    print_summary_table(dict(dist), "Sample Distribution")


def cmd_generate_exam(args: argparse.Namespace) -> None:
    """Professor model generates novel exam questions from the persisted sample."""
    console = get_console()
    exam_path = Path(args.audit_dir) / "eval_exam.json"

    if exam_path.exists() and not args.force:
        logger.info("Exam already exists at %s (use --force to regenerate)", exam_path)
        exam_records = load_exam(args.audit_dir)
        print_success_panel(f"Exam already exists at {exam_path}")
        console.print(f"  [bold]Loaded:[/bold] {len(exam_records)} exam questions")
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
    total_samples = len(samples)
    console.print(f"[cyan]Generating {total_samples} exam questions with professor model:[/cyan] {judge_model}")

    exam_records: list[ExamRecord] = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]  {task.description}[/]"),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        transient=False,
    ) as progress:
        task = progress.add_task("Generating exam questions...", total=total_samples)
        for idx, sample in enumerate(samples, 1):
            progress.update(task, description=f"[cyan]{sample.id}[/]")
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
            progress.update(task, advance=1)

    persist_exam(exam_records, args.audit_dir)
    generated = sum(
        1 for r in exam_records if r.exam_question and r.exam_question != r.user_prompt
    )

    # Print summary
    print_success_panel(
        f"Exam persisted to {exam_path}",
        "Exam Generation Complete",
    )
    print_summary_table(
        {
            "Total Questions": total_samples,
            "Professor Generated": f"{generated}/{total_samples}",
        },
        "Exam Summary",
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
    console = get_console()
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

    total = len(exam_records)
    console.print(f"[cyan]Scoring {total} records with judge model:[/cyan] {judge_model}")

    scorecards: list[ScoreCard] = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]  {task.description}[/]"),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        transient=False,
    ) as progress:
        task = progress.add_task("Scoring records...", total=total)
        for idx, exam in enumerate(exam_records, 1):
            progress.update(task, description=f"[cyan]{exam.id}[/]")
            base_r = baseline_map.get(exam.id)
            adapt_r = adapter_map.get(exam.id)
            if not base_r or not adapt_r:
                logger.warning(
                    "[%d/%d] Missing inference for %s — skipping", idx, total, exam.id
                )
                progress.update(task, advance=1)
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
            progress.update(task, advance=1)

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

    # Print Rich formatted final report
    console.print("\n")
    console.print(
        Panel(
            f"[bold]Final Grade:[/bold] {report.final_grade}/100\n\n"
            f"[bold]Verdict:[/bold] {report.verdict}\n\n"
            f"[bold]Report:[/bold] {report_path}",
            title="[bold green]AEGF Quality Gate — Final Report[/bold green]",
            border_style="green",
            expand=True,
        )
    )


def cmd_full(args: argparse.Namespace) -> None:
    """Run the full 5-stage evaluation pipeline."""
    console = get_console()
    if args.validate:
        args.sample_size = 1
        args.force = True
        logger.info(
            "Validate mode: sample_size=1, force=True — minimal-token end-to-end flow test"
        )

    console.print(
        Panel(
            "[bold]Starting Full Pipeline[/bold]\n"
            "[cyan]5 stages:[/cyan]\n"
            "  1. Stratified Sampling\n"
            "  2. Exam Generation (Professor)\n"
            "  3. Baseline Inference\n"
            "  4. Adapter Inference\n"
            "  5. LLM-as-Judge Scoring",
            title="[bold]AEGF Quality Gate Pipeline[/bold]",
            border_style="green",
            expand=True,
        )
    )

    # Track stages with progress
    stages = [
        ("Stage 1/5: Stratified Sampling", cmd_sample),
        ("Stage 2/5: Exam Generation (Professor)", cmd_generate_exam),
        ("Stage 3/5: Baseline Inference", lambda a: cmd_baseline(args)),
        ("Stage 4/5: Adapter Inference", lambda a: cmd_adapter(args)),
        ("Stage 5/5: LLM-as-Judge Scoring", cmd_score),
    ]

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}[/]"),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    ) as progress:
        total_stages = len(stages)
        stage_task = progress.add_task("Running pipeline stages...", total=total_stages)

        for idx, (stage_name, handler) in enumerate(stages, 1):
            progress.update(stage_task, description=f"[cyan]{stage_name}[/]")
            try:
                if handler == cmd_sample or handler == cmd_generate_exam or handler == cmd_score:
                    handler(args)
                else:
                    # For baseline/adapter, we need to reset model
                    original_model = args.model
                    args.model = None
                    handler(args)
                    args.model = original_model
            except Exception as e:
                logger.error("Stage failed: %s", stage_name)
                console.print(f"[red]Stage failed:[/red] {stage_name}")
                raise e
            progress.update(stage_task, advance=1)


def cmd_calibrate(args: argparse.Namespace) -> None:
    """Run inference parameter calibration (Stage 6)."""
    import json

    console = get_console()
    console.print(
        Panel(
            "[bold]Inference Parameter Calibration[/bold]\n"
            "[cyan]Testing parameter combinations[/cyan] to find optimal configuration",
            title="[bold]Stage 6: Calibration[/bold]",
            border_style="blue",
            expand=True,
        )
    )

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
                prompts = [{"id": s.id, "text": s.user_prompt} for s in sample_records]
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
    logger.info(
        "Calibration: student=vLLM(model=%s), judge=%s(model=%s)",
        args.judge_model,
        args.judge_backend,
        args.claude_model
        if args.judge_backend == "claude"
        else args.gemini_model
        if args.judge_backend == "gemini"
        else args.judge_model,
    )

    # Run calibration
    report = run_calibration(
        prompts=prompts,
        output_dir=args.output_dir,
        verbose=True,
        checkpoint_dir=checkpoint_dir,
        use_prompt_metadata=args.use_prompt_metadata,
        use_noxious_filter=args.use_noxious_filter,
        noxious_loss_threshold=args.noxious_loss_threshold,
        noxious_sample_size=(
            args.noxious_sample_size if args.noxious_sample_size > 0 else None
        ),
        noxious_aggressiveness=args.noxious_aggressiveness,
        student_client=student_client,
        judge_client=judge_client,
    )

    # Print Rich formatted summary
    console = get_console()
    console.print("\n")
    console.print(
        Panel(
            f"[bold]Best Score:[/bold] {report.best_score:.3f}\n\n"
            f"[bold]Best Profile:[/bold] {report.best_profile}\n\n"
            f"[bold]Total Iterations:[/bold] {report.total_iterations}\n\n"
            f"[bold]Output:[/bold] {args.output_dir}",
            title="[bold green]AEGF Inference Calibration — Complete[/bold green]",
            border_style="green",
            expand=True,
        )
    )


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

    # Print startup header with Rich
    mode_descriptions = {
        "sample": "Stratified Sampling",
        "generate-exam": "Professor Exam Generation",
        "baseline": "Baseline Inference",
        "adapter": "Adapter Inference",
        "score": "LLM-as-Judge Scoring",
        "full": "Full Pipeline (All Stages)",
        "calibrate": "Inference Parameter Calibration",
    }
    print_startup_header(args.mode, mode_descriptions.get(args.mode, "Unknown Mode"))

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
            print_error_panel(str(exc), "CLI Error")
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
