#!/usr/bin/env python3
# Copyright 2026 Bunker AI
# SPDX-License-Identifier: Apache-2.0
"""Anchor dataset builder — main CLI entry point."""

from __future__ import annotations

import argparse
import os
import json
import logging
import sys
import datetime
import time
from collections import Counter
from pathlib import Path

# Ensure `infrastructure.` imports resolve when this script runs in-place.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)


def _generate_id(cfg_idx: int) -> str:
    """Generate a deterministic sample ID from config index."""
    return f"sample_{cfg_idx:03d}"

def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser with 12 CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Anchor dataset builder — generate labeled anchor samples"
    )
    parser.add_argument(
        "--count", type=int, default=50,
        help="Number of samples to generate (default: 50)",
    )
    parser.add_argument(
        "--provider", choices=["vllm", "openai", "gemini"],
        default="vllm", help="LLM provider (default: vllm)",
    )
    parser.add_argument(
        "--output-dir", default="outputs",
        help="Output directory (default: outputs)",
    )
    parser.add_argument(
        "--vllm-url", default="http://localhost:8000",
        help="vLLM endpoint URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--temperature", type=float, default=0.4,
        help="Sampling temperature (default: 0.4)",
    )
    parser.add_argument(
        "--max-tokens", type=int, default=8192,
        help="Max output tokens (default: 8192)",
    )
    parser.add_argument(
        "--domain-distribution", default=None,
        help='Domain distribution JSON (default: HA=40, PHP=30, GD=20, Other=10)',
    )
    parser.add_argument(
        "--difficulty-distribution", default=None,
        help='Difficulty distribution JSON (default: easy=30, medium=50, hard=20)',
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="Random seed (default: 42)",
    )
    parser.add_argument(
        "--resume", action="store_true", default=False,
        help="Resume from checkpoint if available",
    )
    parser.add_argument(
        "--no-overwrite", action="store_true", default=False,
        help="Exit 1 if output file already exists",
    )
    parser.add_argument(
        "--output-file", default="anchor_dataset.jsonl",
        help="Output file name (default: anchor_dataset.jsonl)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", default=False,
        help="Validate and log planned distribution, then exit 0",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    # 1. Startup validation
    from infrastructure.anchor_dataset.config import AnchorsConfig
    from infrastructure.anchor_dataset.startup import StartupValidator

    config = AnchorsConfig(
        count=args.count,
        provider=args.provider,
        output_dir=args.output_dir,
        vllm_url=args.vllm_url,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        domain_distribution=args.domain_distribution,
        difficulty_distribution=args.difficulty_distribution,
        seed=args.seed,
        resume=args.resume,
        no_overwrite=args.no_overwrite,
        output_file=args.output_file,
    )

    validator = StartupValidator()
    warnings = validator.dry_run(config)
    for w in warnings:
        logger.warning("Validation: %s", w)

    # 2. Seed loading
    from infrastructure.anchor_dataset.seed_loader import load_seeds

    seeds = load_seeds()
    logger.info("Loaded %d seeds", len(seeds))

    if args.dry_run:
        print("Would generate {} samples (dry-run)".format(args.count))
        print("Provider: {}".format(config.provider))
        _print_distribution(args.count, config)
        print("Seeds loaded: {}".format(len(seeds)))
        for w in warnings:
            print("  Warning: {}".format(w))
        return 0

    # 2.5. Overwrite protection
    output_path = Path(config.output_dir) / config.output_file
    if output_path.exists():
        if config.no_overwrite:
            print(
                "Output file exists: {}. Aborting.".format(output_path),
                file=sys.stderr,
            )
            return 1
        else:
            print(
                "Output file exists: {}. Overwriting.".format(output_path),
                file=sys.stderr,
            )

    # 3. Seed synthesis for unseeded domains
    from infrastructure.anchor_dataset.seed_synthesizer import SeedSynthesizer

    seed_domains = {s.domain for s in seeds}
    needed = [d for d in ("generic_domain", "other") if d not in seed_domains]

    if needed:
        synth = SeedSynthesizer()
        extra: list = []
        for domain in needed:
            try:
                added = synth.synthesize(domain, count=10)
                extra.extend(added)
                logger.info(
                    "Synthesized %d seeds for %s", len(added), domain,
                )
            except Exception:
                logger.warning("Synthesis failed for %s", domain)
        if extra:
            seeds.extend(extra)
            logger.info(
                "Total seeds after synthesis: %d (added %d)",
                len(seeds), len(extra),
            )

    # 4. Config generation
    from infrastructure.anchor_dataset.sample_generator import (
        PromptBuilder,
        SampleConfigGenerator,
    )

    try:
        _domain_dist = json.loads(
            config.domain_distribution or '{"home_assistant": 0.4, "php_legacy": 0.3, "generic_domain": 0.2, "other": 0.1}'
        )
    except json.JSONDecodeError as exc:
        logger.error("Invalid domain_distribution JSON: %s", exc)
        return 1

    try:
        _diff_dist = json.loads(
            config.difficulty_distribution or '{"easy": 0.3, "medium": 0.5, "hard": 0.2}'
        )
    except json.JSONDecodeError as exc:
        logger.error("Invalid difficulty_distribution JSON: %s", exc)
        return 1

    generator = SampleConfigGenerator(seeds=seeds, seed=args.seed)
    configs = generator.generate_configs(count=args.count)

    logger.info(
        "Generated %d configs", len(configs),
    )

    if not configs:
        logger.error("No configs generated — check seed availability")
        return 1

    prompt_builder = PromptBuilder(seeds=seeds)

    # 5. Generation loop
    from infrastructure.anchor_dataset.anchor_providers import get_provider
    from infrastructure.anchor_dataset.failed_sample_logger import FailedSampleLogger
    from infrastructure.anchor_dataset.quality import CircuitBreaker, QualityChecker
    from infrastructure.anchor_dataset.checkpoint import (
        CheckpointManager,
        CheckpointData,
    )
    from infrastructure.anchor_dataset.exporter import JSONLExporter
    # AnchorManifest used in exporter.generate_manifest

    provider = get_provider(config.provider, config)
    quality_checker = QualityChecker(threshold=0.3)
    circuit_breaker = CircuitBreaker()

    quality_enabled = True

    records: list = []
    successful = 0
    failed = 0

    # Failed-sample logger: output next to the main output file
    failed_log_path = Path(config.output_dir) / "failed_samples.jsonl"
    failed_logger = FailedSampleLogger(log_path=failed_log_path)

    # Checkpoint tracking
    cp_path = Path(config.output_dir) / f".checkpoint_{Path(config.output_file).stem}.json"
    cp_manager = CheckpointManager()
    completed_ids: set[str] = set()
    failed_ids: dict[str, str] = {}
    sample_counter = 0
    domain_remaining: dict[str, int] = dict(Counter(cfg.domain for cfg in configs))

    # Resume from checkpoint if requested
    if config.resume and cp_path.exists():
        loaded = cp_manager.load(cp_path)
        if loaded:
            completed_ids = loaded.completed_ids
            failed_ids = loaded.failed_ids
            sample_counter = loaded.sample_counter
            domain_remaining = loaded.domain_allocation_remaining.copy()
            id_to_config = {_generate_id(i): c for i, c in enumerate(configs)}
            _failed_configs = [
                id_to_config[fid]
                for fid in failed_ids
                if fid in id_to_config
            ]
            logger.info(
                "Resuming from checkpoint: %d completed, %d failed, %d samples generated",
                len(completed_ids), len(failed_ids), sample_counter,
            )

            for fid in failed_ids:
                if fid in id_to_config:
                    cfg = id_to_config[fid]
                    idx = int(fid.split("_")[1])
                    logger.info(
                        "Re-attempting failed sample: %s",
                        fid,
                    )
                    try:
                        system, user = prompt_builder.build(cfg)
                        record = provider.generate(system, user, timeout=30.0)
                    except Exception:
                        record = None

                    if record is not None:
                        records.append(record)
                        successful += 1
                        passed = quality_checker.check(record, cfg.turn_count).passed if quality_enabled else True
                        circuit_breaker.record_result(passed)
                    else:
                        failed += 1

    logger.info(
        "Starting generation: %d samples, provider=%s",
        len(configs), config.provider,
    )

    checkpoint_data = None

    try:
        for idx, cfg in enumerate(configs):
            # Skip completed IDs from previous run
            cfg_id = _generate_id(idx)
            if cfg_id in completed_ids:
                logger.info("Skipping completed: %s", cfg_id)
                continue
            system, user = prompt_builder.build(cfg)

            record = None
            failure_reason = None
            raw_response = ""

            for attempt in range(3):
                try:
                    record = provider.generate(system, user, timeout=30.0)
                    if record is not None:
                        break
                    failure_reason = "provider_error"
                    if attempt < 2:
                        logger.debug(
                            "Sample %d attempt %d failed (%s), retrying...",
                            idx, attempt + 1, failure_reason,
                        )
                        time.sleep(1)
                        continue
                except Exception as exc:
                    record = None
                    failure_reason = "provider_error"
                    raw_response = str(exc)
                    if attempt < 2:
                        continue

            if record is None:
                failed_logger.log(
                    sample_id=f"sample_{idx:04d}",
                    domain=cfg.domain,
                    difficulty=cfg.difficulty,
                    failure_reason=failure_reason or "provider_error",
                    provider=provider.name,
                    attempt=attempt,
                    raw_response=raw_response,
                )
                failed += 1
                continue

            completed_ids.add(cfg_id)
            sample_counter += 1
            domain_remaining[cfg.domain] = domain_remaining.get(cfg.domain, 0) - 1

            # Quality check and circuit breaker
            if quality_enabled:
                qpassed = quality_checker.check(record, cfg.turn_count).passed
                circuit_breaker.record_result(qpassed)
                if circuit_breaker.should_switch():
                    logger.warning("Circuit breaker triggered — switching provider")
                    config.provider = "fallback" if config.provider != "fallback" else config.provider

            # Save checkpoint after each successful generation for crash recovery
            checkpoint_data = CheckpointData(
                completed_ids=completed_ids,
                failed_ids=failed_ids,
                provider_active=provider.name,
                sample_counter=sample_counter,
                domain_allocation_remaining=domain_remaining,
                timestamp=datetime.datetime.utcnow().isoformat(),
                circuit_breaker_triggered=circuit_breaker.triggered,
                next_variant_map={},
            )
            cp_manager.save(cp_path, checkpoint_data)

            if (idx + 1) % 10 == 0:
                logger.info(
                    "Progress: %d/%d (success=%d, failed=%d)",
                    idx + 1, len(configs), successful, failed,
                )

            if circuit_breaker.should_switch():
                logger.warning(
                    "Circuit breaker triggered at batch %d, failure_rate=%.2f",
                    idx + 1, circuit_breaker.get_failure_rate(),
                )
                circuit_breaker.try_reset()

    except KeyboardInterrupt:
        # Save any pending checkpoint before exit
        if checkpoint_data is not None:
            cp_manager.save(cp_path, checkpoint_data)
        logger.info("Interrupted — checkpoint saved at %s", cp_path)
        return 1

    # 6. Export
    output_path = Path(config.output_dir) / config.output_file
    output_path.parent.mkdir(parents=True, exist_ok=True)

    exporter = JSONLExporter()
    exporter.write_all(records, output_path)

    manifest = exporter.generate_manifest(
        records, provider.name, circuit_breaker.triggered, failed,
    )
    manifest_path = Path(str(output_path) + "_manifest.json")
    with manifest_path.open("w") as f:
        json.dump(manifest.model_dump(), f, indent=2)

    # Summary
    print("Generation complete: {} samples".format(len(records)))
    print("  Output: {}".format(output_path))
    print("  Successful: {}, Failed: {}".format(successful, failed))
    print("  CB triggered: {}".format(circuit_breaker.triggered))

    dist = Counter(r.domain for r in records)
    print("  Domain distribution: HA={} PHP={} GD={} Other={}".format(
        dist.get("home_assistant", 0),
        dist.get("php_legacy", 0),
        dist.get("generic_domain", 0),
        dist.get("other", 0),
    ))

    return 0


def _print_distribution(count: int, config) -> None:
    """Print planned domain/difficulty distribution."""
    from infrastructure.anchor_dataset.sample_generator import (
        _distribute,
        _DOMAIN_PCTS,
        _DIFFICULTY_FRACTIONS,
        _DIFFICULTY_TURNS,
    )

    dist_text = config.domain_distribution or '{"home_assistant": 0.4, "php_legacy": 0.3, "generic_domain": 0.2, "other": 0.1}'
    try:
        domain_pcts = [(d, p) for d, p in json.loads(dist_text).items()]
    except json.JSONDecodeError:
        domain_pcts = _DOMAIN_PCTS

    dist_text2 = config.difficulty_distribution or '{"easy": 0.3, "medium": 0.5, "hard": 0.2}'
    try:
        diff_fractions = [(d, p) for d, p in json.loads(dist_text2).items()]
    except json.JSONDecodeError:
        diff_fractions = _DIFFICULTY_FRACTIONS

    domain_counts = _distribute(count, domain_pcts)
    print("\nPlanned domain distribution:")
    for domain, n in domain_counts.items():
        print("  {}={}".format(domain, n))

    print("\nPlanned difficulty breakdown:")
    for domain, dcount in domain_counts.items():
        diff_counts = _distribute(dcount, diff_fractions)
        parts = []
        for diff, dcount in diff_counts.items():
            parts.append(
                "{} ({} turns)={}".format(diff, _DIFFICULTY_TURNS.get(diff, "?"), dcount),
            )
        print("  {}: {}".format(domain, ", ".join(parts)))


def _main() -> int:
    """Entry point — with graceful import error handling."""
    try:
        return main()
    except ImportError as exc:
        print(
            "ERROR: Import failed — {}\n"
            "Install dependencies: pip install pydantic httpx requests".format(exc),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(_main())
