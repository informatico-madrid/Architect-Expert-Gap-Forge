#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Architect-Expert-Gap-Forge (AEGF) - Dataset Mixer Module

Mixes specialized and anchor datasets with configurable token proportions,
applies deterministic shuffling, and generates composition reports.

Location: src/curation/dataset_mixer.py

Note U1: Token counting uses tiktoken (cl100k_base) as an approximation.
Maximum drift is ~3% compared to Qwen3 tokenizer. If exact counting is required,
use transformers.AutoTokenizer with Qwen3 model.

SPDX-License-Identifier: Apache-2.0
Copyright 2026 AEGF
"""

from __future__ import annotations

import json
import logging
import random
from dataclasses import dataclass
from pathlib import Path

import tiktoken

from src.curation.anchor_dataset_downloader import load_anchor_configs
from src.curation.format_normalizer import FormatNormalizer
from src.utils.schema import CompositionReport, DatasetRecord

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================


@dataclass(slots=True, frozen=True)
class DatasetMixerConfig:
    """Configuration for DatasetMixer.

    Attributes:
        specialized_pct: Target percentage for specialized dataset tokens (default: 30.0).
        anchor_pct: Target percentage for anchor dataset tokens (default: 70.0).
        shuffle_seed: Random seed for deterministic shuffling.
        target_records: Optional target total number of records after mixing.
    """

    specialized_pct: float = 30.0
    anchor_pct: float = 70.0
    shuffle_seed: int = 42
    target_records: int | None = None


# =============================================================================
# DATASET MIXER
# =============================================================================


class DatasetMixer:
    """Mixes specialized and anchor datasets with configurable proportions.

    This class provides:
    - Token-based subsampling to achieve target proportions (default 30/70)
    - Deterministic shuffling with configurable seed
    - JSONL export with ChatML format
    - Composition report generation

    Example:
        >>> config = DatasetMixerConfig(specialized_pct=30.0, anchor_pct=70.0, shuffle_seed=42)
        >>> mixer = DatasetMixer(config)
        >>> mixed = mixer.mix(specialized_records, anchor_records)
        >>> mixer.export(mixed, Path("output.jsonl"))
        >>> report = mixer.generate_report(mixed)
    """

    def __init__(
        self,
        config: DatasetMixerConfig,
        tokenizer_model: str = "cl100k_base",
    ) -> None:
        """Initialize the DatasetMixer.

        Args:
            config: Configuration for mixing behavior.
            tokenizer_model: TikToken model for token counting.
                Note: Using cl100k_base as approximation (drift ~3% vs Qwen3).
        """
        self._config = config
        self._tokenizer = tiktoken.get_encoding(tokenizer_model)

    @property
    def config(self) -> DatasetMixerConfig:
        """Return the mixer configuration."""
        return self._config

    def _count_tokens(self, records: list[DatasetRecord]) -> int:
        """Count total tokens in records.

        Args:
            records: List of DatasetRecord objects.

        Returns:
            Total token count.
        """
        total = 0
        for record in records:
            # Use token_count from metadata if available
            token_count = record.metadata.get("token_count")
            if token_count is not None:
                total += token_count
            else:
                # Fallback: calculate from content
                content = " ".join(m.content for m in record.messages)
                total += len(self._tokenizer.encode(content))
        return total

    def _subsample_by_tokens(
        self,
        records: list[DatasetRecord],
        target_tokens: int,
    ) -> list[DatasetRecord]:
        """Subsample records to fit within target token budget.

        Selects records in order until the token budget is exhausted.

        Args:
            records: List of DatasetRecord objects.
            target_tokens: Maximum number of tokens to include.

        Returns:
            List of records within token budget.
        """
        selected = []
        total_tokens = 0

        for record in records:
            token_count = record.metadata.get("token_count", 0)
            if token_count == 0:
                # Calculate if not available
                content = " ".join(m.content for m in record.messages)
                token_count = len(self._tokenizer.encode(content))

            if total_tokens + token_count <= target_tokens:
                selected.append(record)
                total_tokens += token_count

        logger.info(
            "Subsampled %d records with %d tokens (target: %d)",
            len(selected),
            total_tokens,
            target_tokens,
        )

        return selected

    def mix(
        self,
        specialized: list[DatasetRecord],
        anchor: list[DatasetRecord],
    ) -> list[DatasetRecord]:
        """Mix specialized and anchor datasets with target proportions.

        Args:
            specialized: List of specialized DatasetRecord objects.
            anchor: List of anchor DatasetRecord objects.

        Returns:
            Mixed list of DatasetRecord objects.
        """
        # Calculate current tokens
        specialized_tokens = self._count_tokens(specialized)
        anchor_tokens = self._count_tokens(anchor)

        logger.info(
            "Initial tokens - specialized: %d, anchor: %d",
            specialized_tokens,
            anchor_tokens,
        )

        # Calculate target tokens for anchor to achieve desired proportion
        # specialized_tokens / total = specialized_pct / 100
        # anchor_tokens_adjusted = specialized_tokens * anchor_pct / specialized_pct
        if specialized_tokens > 0 and self._config.specialized_pct > 0:
            target_anchor_tokens = int(
                specialized_tokens * self._config.anchor_pct / self._config.specialized_pct
            )

            # Subsample anchor if needed
            if anchor_tokens > target_anchor_tokens:
                anchor = self._subsample_by_tokens(anchor, target_anchor_tokens)
                anchor_tokens = self._count_tokens(anchor)

        # Also subsample specialized if it exceeds target (for target_records)
        if self._config.target_records is not None:
            total_records = len(specialized) + len(anchor)
            if total_records > self._config.target_records:
                # Calculate how many to keep from each (proportional)
                spec_ratio = len(specialized) / total_records

                target_specialized = int(self._config.target_records * spec_ratio)
                target_anchor = self._config.target_records - target_specialized

                if len(specialized) > target_specialized:
                    specialized = specialized[:target_specialized]
                if len(anchor) > target_anchor:
                    anchor = anchor[:target_anchor]

                logger.info(
                    "Subsampled to target records: specialized=%d, anchor=%d",
                    len(specialized),
                    len(anchor),
                )

        # Combine records
        mixed = specialized + anchor

        # Shuffle deterministically
        random.seed(self._config.shuffle_seed)
        random.shuffle(mixed)

        # Calculate final proportions
        final_spec_tokens = self._count_tokens(specialized)
        final_anchor_tokens = self._count_tokens(anchor)
        final_total = final_spec_tokens + final_anchor_tokens

        if final_total > 0:
            final_spec_pct = (final_spec_tokens / final_total) * 100
            final_anchor_pct = (final_anchor_tokens / final_total) * 100

            logger.info(
                "Final mix: %d records, specialized=%.1f%%, anchor=%.1f%%",
                len(mixed),
                final_spec_pct,
                final_anchor_pct,
            )

        return mixed

    def export(
        self,
        records: list[DatasetRecord],
        output_path: Path,
    ) -> None:
        """Export records to JSONL format.

        Args:
            records: List of DatasetRecord objects to export.
            output_path: Path to the output JSONL file.

        Raises:
            IOError: If the file cannot be written.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            for record in records:
                f.write(record.model_dump_json() + "\n")

        logger.info("Exported %d records to %s", len(records), output_path)

    def generate_report(
        self,
        records: list[DatasetRecord],
        discarded_count: int = 0,
        discarded_reasons: dict[str, int] | None = None,
    ) -> CompositionReport:
        """Generate composition report for the mixed dataset.

        Args:
            records: List of DatasetRecord objects.
            discarded_count: Number of discarded records.
            discarded_reasons: Dictionary of discard reasons and counts.

        Returns:
            CompositionReport with dataset composition statistics.
        """
        # Calculate records by origin
        records_by_origin: dict[str, int] = {}
        type_distribution: dict[str, int] = {}
        token_counts_by_origin: dict[str, int] = {}

        for record in records:
            origin = record.metadata.get("origin", "unknown")
            rec_type = record.metadata.get("type", "unknown")

            records_by_origin[origin] = records_by_origin.get(origin, 0) + 1
            type_distribution[rec_type] = type_distribution.get(rec_type, 0) + 1

            # Calculate tokens
            token_count = record.metadata.get("token_count")
            if token_count is None:
                content = " ".join(m.content for m in record.messages)
                token_count = len(self._tokenizer.encode(content))

            token_counts_by_origin[origin] = (
                token_counts_by_origin.get(origin, 0) + token_count
            )

        # Calculate token percentages
        total_tokens = sum(token_counts_by_origin.values())
        token_pct_by_origin: dict[str, float] = {}

        if total_tokens > 0:
            for origin, tokens in token_counts_by_origin.items():
                token_pct_by_origin[origin] = (tokens / total_tokens) * 100

        return CompositionReport(
            records_by_origin=records_by_origin,
            token_pct_by_origin=token_pct_by_origin,
            type_distribution=type_distribution,
            discarded_count=discarded_count,
            discarded_reasons=discarded_reasons or {},
        )

    def export_report(
        self,
        report: CompositionReport,
        report_path: Path,
    ) -> None:
        """Export composition report to JSON file.

        Args:
            report: CompositionReport to export.
            report_path: Path to the output JSON file.
        """
        report_path.parent.mkdir(parents=True, exist_ok=True)

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report.model_dump_json(indent=2) + "\n")

        logger.info("Exported composition report to %s", report_path)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def load_specialized_records(jsonl_path: Path) -> list[DatasetRecord]:
    """Load specialized records from JSONL file.

    Args:
        jsonl_path: Path to specialized JSONL file.

    Returns:
        List of DatasetRecord objects.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file format is invalid.
    """
    if not jsonl_path.exists():
        raise FileNotFoundError(f"Specialized JSONL not found: {jsonl_path}")

    records = []
    normalizer = FormatNormalizer()

    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue

            try:
                data = json.loads(line)
                # Normalize to DatasetRecord
                record = normalizer.convert(data)
                records.append(record)
            except Exception as e:
                logger.warning("Failed to parse record: %s", e)
                continue

    logger.info("Loaded %d specialized records from %s", len(records), jsonl_path)
    return records


def create_mixer(
    specialized_jsonl: Path,
    anchor_configs_path: Path,
    output_path: Path,
    seed: int = 42,
    target_records: int | None = None,
    specialized_pct: float = 30.0,
    anchor_pct: float = 70.0,
) -> tuple[DatasetMixer, list[DatasetRecord], list[DatasetRecord]]:
    """Create a DatasetMixer and load required data.

    This is a convenience function that:
    1. Loads specialized records from JSONL
    2. Loads anchor dataset configs
    3. Downloads anchor datasets
    4. Creates the mixer

    Args:
        specialized_jsonl: Path to specialized JSONL file.
        anchor_configs_path: Path to anchor configs YAML.
        output_path: Path for output JSONL.
        seed: Random seed for shuffling.
        target_records: Optional target record count.
        specialized_pct: Target specialized percentage.
        anchor_pct: Target anchor percentage.

    Returns:
        Tuple of (DatasetMixer, specialized_records, anchor_records).
    """
    # Load specialized records
    specialized = load_specialized_records(specialized_jsonl)

    # Load anchor configs and download
    anchor_configs = load_anchor_configs(anchor_configs_path)

    from src.curation.anchor_dataset_downloader import AnchorDatasetDownloader

    downloader = AnchorDatasetDownloader(anchor_configs)
    anchor = downloader.download_all()

    # Create mixer
    config = DatasetMixerConfig(
        specialized_pct=specialized_pct,
        anchor_pct=anchor_pct,
        shuffle_seed=seed,
        target_records=target_records,
    )
    mixer = DatasetMixer(config)

    return mixer, specialized, anchor
