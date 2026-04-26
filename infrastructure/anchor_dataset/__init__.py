"""Anchor Dataset Builder — generate anchor samples for LLM evaluation."""

__version__ = "0.1.0"

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
