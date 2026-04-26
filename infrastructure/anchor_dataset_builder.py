#!/usr/bin/env python3
# Copyright 2026 Bunker AI
# SPDX-License-Identifier: Apache-2.0
"""Anchor dataset builder — main CLI entry point."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter
from pathlib import Path

logger = logging.getLogger(__name__)


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
    from infrastructure.anchor_dataset.config import AnchorsConfig, QualitySettings, apply_calibration
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
        domain_dist = json.loads(
            config.domain_distribution or '{"home_assistant": 0.4, "php_legacy": 0.3, "generic_domain": 0.2, "other": 0.1}'
        )
    except json.JSONDecodeError as exc:
        logger.error("Invalid domain_distribution JSON: %s", exc)
        return 1

    try:
        diff_dist = json.loads(
            config.difficulty_distribution or '{"easy": 0.3, "medium": 0.5, "hard": 0.2}'
        )
    except json.JSONDecodeError as exc:
        logger.error("Invalid difficulty_distribution JSON: %s", exc)
        return 1

    generator = SampleConfigGenerator(seeds=seeds, seed=args.seed)
    configs = generator.generate_configs(configs_count=args.count)

    logger.info(
        "Generated %d configs", len(configs),
    )

    if not configs:
        logger.error("No configs generated — check seed availability")
        return 1

    prompt_builder = PromptBuilder(seeds=seeds)

    # 5. Generation loop
    from infrastructure.anchor_dataset.anchor_providers import get_provider
    from infrastructure.anchor_dataset.quality import CircuitBreaker, QualityChecker
    from infrastructure.anchor_dataset.checkpoint import (
        CheckpointManager,
        CheckpointData,
    )
    from infrastructure.anchor_dataset.exporter import JSONLExporter
    from infrastructure.anchor_dataset.anchor_dataset_schema import AnchorManifest

    provider = get_provider(config.provider, config)
    quality_checker = QualityChecker(threshold=0.3)
    circuit_breaker = CircuitBreaker()

    quality_enabled = True

    records: list = []
    successful = 0
    failed = 0

    logger.info(
        "Starting generation: %d samples, provider=%s",
        len(configs), config.provider,
    )

    for idx, cfg in enumerate(configs):
        try:
            system, user = prompt_builder.build(cfg)
            record = provider.generate(system, user)
        except Exception:
            record = None
            failed += 1
            continue

        if record is not None:
            if quality_enabled:
                calibration_fn = apply_calibration
                qresult = quality_checker.check(record, cfg.turn_count)
                quality_score = calibration_fn(qresult.score)
                record = record.model_copy(
                    update={
                        "expected_quality_score": quality_score,
                    },
                )

            records.append(record)
            circuit_breaker.record_result(qresult.passed if quality_enabled else True)
            successful += 1
        else:
            failed += 1

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
