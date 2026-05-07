#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0
"""Anchor Dataset Builder — generate anchor samples for LLM evaluation."""

__version__ = "0.1.0"

# --- Exceptions ---
from infrastructure.anchor_dataset.errors import (
    AnchorDatasetError,
    ValidationError,
    ProviderError,
    SerializationError,
    SeedError,
    CheckpointError,
)

# --- Schema ---
from infrastructure.anchor_dataset.anchor_dataset_schema import (
    DSPY_FIELD_MAP,
    jsonl_to_dspy_examples,
)

# --- Config ---
from infrastructure.anchor_dataset.config import (
    QualitySettings,
    apply_calibration,
)

# --- Seed loader ---
from infrastructure.anchor_dataset.seed_loader import (
    NormalizedSeed,
    load_seeds,
)

# --- Sample generator ---
from infrastructure.anchor_dataset.sample_generator import (
    SampleConfig,
    SampleConfigGenerator,
    PromptBuilder,
)

# --- Providers ---
from infrastructure.anchor_dataset.anchor_providers import (
    AnchorProvider,
    VLLMProvider,
    OpenAIProvider,
    GeminiProvider,
    PROVIDER_MAP,
    get_provider,
    ConfigurationError,
)

# --- Quality ---
from infrastructure.anchor_dataset.quality import (
    QualityResult,
    QualityChecker,
    CircuitBreaker,
)

# --- Persistence ---
from infrastructure.anchor_dataset.failed_sample_logger import (
    FailedSampleEntry,
    FailedSampleLogger,
)
from infrastructure.anchor_dataset.checkpoint import (
    CheckpointData,
    CheckpointManager,
)

# --- Export ---
from infrastructure.anchor_dataset.exporter import (
    AnchorRecord,
    AnchorManifest,
    JSONLExporter,
)

# --- Synthesis ---
from infrastructure.anchor_dataset.seed_synthesizer import (
    SeedSynthesizer,
)

# --- Startup ---
from infrastructure.anchor_dataset.startup import (
    AnchorsConfig,
    StartupValidator,
)

__all__ = [
    # Version
    "__version__",
    # Exceptions
    "AnchorDatasetError",
    "ValidationError",
    "ProviderError",
    "SerializationError",
    "ConfigurationError",
    "SeedError",
    "CheckpointError",
    # Schema
    "AnchorRecord",
    "AnchorManifest",
    "DSPY_FIELD_MAP",
    "jsonl_to_dspy_examples",
    # Config
    "AnchorsConfig",
    "QualitySettings",
    "apply_calibration",
    # Seed loader
    "NormalizedSeed",
    "load_seeds",
    # Sample generator
    "SampleConfig",
    "SampleConfigGenerator",
    "PromptBuilder",
    # Providers
    "AnchorProvider",
    "VLLMProvider",
    "OpenAIProvider",
    "GeminiProvider",
    "PROVIDER_MAP",
    "get_provider",
    # Quality
    "QualityResult",
    "QualityChecker",
    "CircuitBreaker",
    # Persistence
    "FailedSampleEntry",
    "FailedSampleLogger",
    "CheckpointData",
    "CheckpointManager",
    # Export
    "JSONLExporter",
    # Synthesis
    "SeedSynthesizer",
    # Startup
    "StartupValidator",
]
