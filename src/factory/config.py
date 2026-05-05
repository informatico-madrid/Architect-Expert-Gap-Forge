#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
AEGF Factory Configuration Module
==================================
Centralizes configuration constants, type definitions, and detector patterns
for the data factory pipeline.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import TypedDict

import yaml

from src.utils.exceptions import ConfigValidationError

# ======================================================================
# LOGGING
# ======================================================================
import logging

logger = logging.getLogger(__name__)

# ======================================================================
# CONFIGURATION CONSTANTS
# ======================================================================
DEFAULT_BASE_URL = "http://localhost:8000/v1"
_DEFAULT_API_KEY = os.getenv("API_KEY")
if _DEFAULT_API_KEY is None:
    raise ValueError("API_KEY environment variable is required. Please set it before running.")
DEFAULT_API_KEY = _DEFAULT_API_KEY
DEFAULT_MODEL = "qwen3-5-35b-a3b-nvfp4"
DEFAULT_WORKERS = 8
MAX_RETRIES = 3

OUTPUT_DIR = Path("data/synthetic")
REJECTED_PATH = OUTPUT_DIR / "rejected_v11.jsonl"

# Master document filenames (resolved at runtime via --gap-dir)
_MASTER_GUIDE_FILENAME = "HA_MASTER_GUIDE_2026.md"
_TECHNICAL_CHANGELOG_FILENAME = "technical_changelog_2026.md"
_JINJA_YAML_GUIDE_FILENAME = "HA_JINJA_YAML_GUIDE_2026.md"

# Example type distribution
DIST_NOMINAL = 0.50
DIST_CONTRAST = 0.30
DIST_ERROR_RECOVERY = 0.20

# Evol-Instruct difficulty levels (uniformly distributed within nominal)
EVOL_LEVELS = ["easy", "medium", "hard"]

# ======================================================================
# TYPE DEFINITIONS
# ======================================================================


@dataclass(slots=True, frozen=True)
class TaxonomyState:
    """Immutable container for prompt taxonomy data.

    Populated by load_taxonomy() at startup.
    """

    prompts: dict = field(default_factory=dict)
    ha_error_templates: list = field(default_factory=list)
    jinja_variants: list = field(default_factory=list)
    theory_taxonomy: dict = field(default_factory=dict)


class GeneratedSample(TypedDict):
    """Output format for generated training samples."""

    id: str
    conversation: list[dict]
    metadata: dict
    filter_text: str


# ======================================================================
# LEGACY CODE DETECTORS (Python integrations)
# ======================================================================
# Applied against frag['original'] BEFORE Gold Injection.
# If any matches, the fragment contains legacy 2023/2024 code and
# Gold Injection is SKIPPED to avoid weight schizophrenia.

LEGACY_CODE_DETECTORS = [
    # --- Storage / Runtime Data ---
    (r"hass\.data\[", "hass.data[] dict pattern -> entry.runtime_data"),
    (r"hass\.data\.setdefault", "hass.data.setdefault() -> entry.runtime_data"),
    # --- Unit Constants Legacy ---
    (
        r"\bTEMP_CELSIUS\b|\bTEMP_FAHRENHEIT\b|\bTEMP_KELVIN\b",
        "Legacy TEMP_* constants -> UnitOfTemperature enum",
    ),
    (
        r"\bUNIT_PERCENTAGE\b|\bPERCENTAGE\b(?=\s*[,\)])",
        "Legacy UNIT_PERCENTAGE -> UnitOfMeasurement enum",
    ),
    (
        r"\bLENGTH_METERS\b|\bLENGTH_KILOMETERS\b|\bLENGTH_MILES\b",
        "Legacy LENGTH_* constants -> UnitOfLength enum",
    ),
    (
        r"\bMASS_GRAMS\b|\bMASS_KILOGRAMS\b|\bVOLUME_LITERS\b",
        "Legacy MASS_*/VOLUME_* constants -> UnitOf* enums",
    ),
    (
        r"\bPRESSURE_BAR\b|\bPRESSURE_PA\b|\bPRESSURE_HPA\b",
        "Legacy PRESSURE_* constants -> UnitOfPressure enum",
    ),
    (
        r"\bENERGY_KILO_WATT_HOUR\b|\bENERGY_WATT_HOUR\b|\bPOWER_WATT\b|\bPOWER_KILO_WATT\b",
        "Legacy ENERGY_*/POWER_* -> UnitOfEnergy/UnitOfPower enums",
    ),
    # --- Setup singular ---
    (
        r"async_forward_entry_setup\b(?!s)",
        "Singular async_forward_entry_setup -> async_forward_entry_setups",
    ),
    # --- String device_class ---
    (
        r'device_class\s*=\s*["\'](?:temperature|humidity|pressure|energy|power|battery|voltage|current)',
        "String literal device_class -> SensorDeviceClass/BinarySensorDeviceClass enum",
    ),
    (r'_attr_device_class\s*=\s*["\']', "String _attr_device_class -> Enum"),
    # --- Synchronous Entity pattern ---
    (r"def update\(self\)", "Synchronous update(self) -> CoordinatorEntity + async"),
    (r"def\s+async_update\(self\)", "Direct async_update -> CoordinatorEntity pattern"),
    # --- YAML-only ---
    (r"PLATFORM_SCHEMA\s*=", "YAML-only PLATFORM_SCHEMA -> ConfigFlow required"),
    # --- Blocking I/O in async ---
    (
        r"requests\.get\(|requests\.post\(|requests\.put\(|requests\.delete\(",
        "Blocking requests.* in code -> aiohttp/async_add_executor_job",
    ),
    (r"(?<!await\s)time\.sleep\(", "Blocking time.sleep() -> await asyncio.sleep()"),
    (r"urllib\.request\.urlopen", "Blocking urllib -> aiohttp"),
    # --- Deprecated state/entity attributes ---
    (r"\bself\._state\s*=", "Legacy self._state = X -> native_value property"),
    (r"\bself\._attr_state\s*=", "Legacy self._attr_state -> native_value property"),
    (r"@property\s*\n\s*def\s+state\(self\)", "Legacy state property -> native_value"),
    # --- Old-style entity registration ---
    (r"add_entities\(\[.*\]\s*,\s*True\)", "Legacy polling=True -> CoordinatorEntity"),
]


# ======================================================================
# LEGACY CODE DETECTORS (Jinja / YAML templates)
# ======================================================================
# Based on HA_JINJA_YAML_GUIDE_2026.md (breaking changes 2024.10 -> 2026.2)

JINJA_LEGACY_CODE_DETECTORS = [
    # --- 2024.10: Singular syntax in automations ---
    (r"^\s*trigger:\s*$", "Singular 'trigger:' -> 'triggers:' (2024.10)"),
    (r"^\s*condition:\s*$", "Singular 'condition:' -> 'conditions:' (2024.10)"),
    (r"^\s*action:\s*$", "Singular 'action:' -> 'actions:' (2024.10)"),
    (
        r"^\s*-\s*platform:\s*(?:state|numeric_state|time|event|mqtt|webhook|sun|zone|tag)\b",
        "Legacy 'platform:' in trigger -> 'trigger:' (2024.10)",
    ),
    # --- 2024.12: Variable this vs value ---
    (r"\bthis\.state\b", "Legacy this.state -> use 'value' variable (2024.12)"),
    (
        r"\bthis\.attributes\b",
        "Legacy this.attributes -> use 'value' or new 'this' semantics (2024.12)",
    ),
    # --- 2024.12: Non-snake_case states ---
    (
        r"==\s*['\"](?:[A-Z][a-z]+\s+[A-Z]|[A-Z]{2,}[a-z])",
        "Non-snake_case state format -> migrate to snake_case (2024.12)",
    ),
    # --- 2025.8: None -> unknown in binary_sensor ---
    (
        r"or\s+None\s*[%}]",
        "Implicit None in binary_sensor -> use explicit 'false' (2025.8)",
    ),
    (
        r"is_state\([^)]*['\"]standby['\"]",
        "State 'standby' removed -> use 'off' (2025.8)",
    ),
    (
        r"state_attr\([^)]*['\"]battery_level['\"]",
        "Attribute 'battery_level' removed -> use dedicated sensor (2025.8)",
    ),
    (
        r"state_attr\([^)]*['\"]battery['\"]",
        "Attribute 'battery' removed -> use dedicated sensor (2025.8)",
    ),
    # --- 2025.12: Legacy template entities ---
    (
        r"platform:\s*template",
        "Legacy 'platform: template' -> root 'template:' syntax (2025.12, dies 2026.6)",
    ),
    (
        r"value_template:",
        "Legacy 'value_template:' -> use 'state:' in modern syntax (2025.12)",
    ),
    # --- Best practices: filters without default ---
    (
        r"\|\s*float\s*[^(]",
        "float without default -> use '| float(0)' with default value",
    ),
    (r"\|\s*int\s*[^(]", "int without default -> use '| int(0)' with default value"),
    # --- as_timestamp legacy ---
    (
        r"\bas_timestamp\b",
        "as_timestamp (epoch float) -> prefer as_datetime (timezone-aware)",
    ),
]


# ======================================================================
# OUTPUT POISON DETECTORS
# ======================================================================
# Legacy patterns FORBIDDEN in model-generated code.
# Stricter than source detectors: if the model produces these patterns
# in its output, the example is toxic for training.

OUTPUT_POISON_DETECTORS = [
    # Returning None where it should be false (HA 2025.8)
    (r"\{\{-?\s*None\s*-?\}\}", "Output returns None (must be false, HA 2025.8)"),
    # as_timestamp in generated code (deprecated)
    (
        r"\bas_timestamp\s*\(",
        "Output uses as_timestamp() (deprecated, use as_datetime)",
    ),
    # platform: template in generated code (deprecated 2025.12)
    (r"platform:\s*template", "Output uses 'platform: template' (deprecated 2025.12)"),
    # Singular syntax in generated code
    (r"^\s*trigger:\s*\n\s*-", "Output uses singular 'trigger:' (deprecated 2024.10)"),
    (
        r"^\s*condition:\s*\n\s*-",
        "Output uses singular 'condition:' (deprecated 2024.10)",
    ),
    (r"^\s*action:\s*\n\s*-", "Output uses singular 'action:' (deprecated 2024.10)"),
    # func() callable in Jinja (impossible — macro params are not callable)
    (r"\{\{-?\s*func\s*\(", "Output invokes func() as callable (impossible in Jinja2)"),
    # Hallucinated private helper: _private_macro() not defined in fragment
    (r"\{\{-?\s*_\w+\s*\(", "Output calls undefined private helper (_helper())"),
]


# ======================================================================
# TEACHER MODEL CONFIG (T005)
# ======================================================================


@dataclass(slots=True, frozen=True)
class TeacherModelConfig:
    """Configuration for the external Teacher model API.

    Supports OpenAI-compatible, Anthropic, and Google Gemini providers.
    """

    provider: str = "openai"
    model_name: str = "gpt-4o"
    api_key_env: str = "OPENAI_API_KEY"
    base_url: str | None = None
    request_delay_ms: int = 500
    max_retries: int = 5
    backoff_factor: int = 2
    request_timeout_seconds: int = 120
    checkpoint_path: str = "data/checkpoints/trajectories.json"


@dataclass(slots=True, frozen=True)
class TrajectoryConfig:
    """Configuration for trajectory generation parameters."""

    min_turns: int = 3
    max_turns: int = 10
    error_probability: float = 0.7
    cascade_probability: float = 0.3
    tool_format: str = "auto"


@dataclass(slots=True, frozen=True)
class HardQueryConfig:
    """Configuration for hard query mode."""

    enabled: bool = False
    ratio: float = 0.2


@dataclass(slots=True, frozen=True)
class DatasetConfig:
    """Configuration for dataset generation and output."""

    use_case: str = "home_assistant"
    target_specialized_records: int = 12000
    target_total_records: int = 40000
    output_path: str = "data/stage_2_output/trajectories.jsonl"
    taxonomy_path: str = "configs/stage_2_factory/taxonomy/home_assistant/agentic_taxonomy.yaml"
    trajectory: TrajectoryConfig = field(default_factory=TrajectoryConfig)
    hard_query: HardQueryConfig = field(default_factory=HardQueryConfig)


@dataclass(slots=True, frozen=True)
class OutputConfig:
    """Configuration for output behavior."""

    verbose: bool = True
    progress_interval: int = 100
    dry_run: bool = False


@dataclass(slots=True, frozen=True)
class FactoryConfig:
    """Complete factory configuration combining all sections."""

    teacher_model: TeacherModelConfig = field(default_factory=TeacherModelConfig)
    dataset: DatasetConfig = field(default_factory=DatasetConfig)
    output: OutputConfig = field(default_factory=OutputConfig)


def load_teacher_config(path: Path) -> TeacherModelConfig:
    """Load teacher model configuration from a YAML file.

    Args:
        path: Path to the configuration YAML file.

    Returns:
        TeacherModelConfig populated from the YAML file.

    Raises:
        ConfigValidationError: If the config file is missing or invalid.
    """
    if not path.exists():
        raise ConfigValidationError(f"Config file not found: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigValidationError(f"Invalid YAML in config file {path}: {e}") from e

    if data is None:
        raise ConfigValidationError(f"Config file is empty: {path}")

    teacher_model_data = data.get("teacher_model", {})
    return TeacherModelConfig(
        provider=teacher_model_data.get("provider", "openai"),
        model_name=teacher_model_data.get("model_name", "gpt-4o"),
        api_key_env=teacher_model_data.get("api_key_env", "OPENAI_API_KEY"),
        base_url=teacher_model_data.get("base_url"),
        request_delay_ms=teacher_model_data.get("request_delay_ms", 500),
        max_retries=teacher_model_data.get("max_retries", 5),
        backoff_factor=teacher_model_data.get("backoff_factor", 2),
        request_timeout_seconds=teacher_model_data.get("request_timeout_seconds", 120),
        checkpoint_path=teacher_model_data.get(
            "checkpoint_path", "data/checkpoints/trajectories.json"
        ),
    )


def load_dataset_config(path: Path) -> DatasetConfig:
    """Load dataset configuration from a YAML file.

    Args:
        path: Path to the configuration YAML file.

    Returns:
        DatasetConfig populated from the YAML file.

    Raises:
        ConfigValidationError: If the config file is missing or invalid.
    """
    if not path.exists():
        raise ConfigValidationError(f"Config file not found: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigValidationError(f"Invalid YAML in config file {path}: {e}") from e

    if data is None:
        raise ConfigValidationError(f"Config file is empty: {path}")

    dataset_data = data.get("dataset", {})
    trajectory_data = dataset_data.get("trajectory", {})
    hard_query_data = dataset_data.get("hard_query", {})

    return DatasetConfig(
        use_case=dataset_data.get("use_case", "home_assistant"),
        target_specialized_records=dataset_data.get("target_specialized_records", 12000),
        target_total_records=dataset_data.get("target_total_records", 40000),
        output_path=dataset_data.get(
            "output_path", "data/stage_2_output/trajectories.jsonl"
        ),
        taxonomy_path=dataset_data.get(
            "taxonomy_path",
            "configs/stage_2_factory/taxonomy/home_assistant/agentic_taxonomy.yaml",
        ),
        trajectory=TrajectoryConfig(
            min_turns=trajectory_data.get("min_turns", 3),
            max_turns=trajectory_data.get("max_turns", 10),
            error_probability=trajectory_data.get("error_probability", 0.7),
            cascade_probability=trajectory_data.get("cascade_probability", 0.3),
            tool_format=trajectory_data.get("tool_format", "auto"),
        ),
        hard_query=HardQueryConfig(
            enabled=hard_query_data.get("enabled", False),
            ratio=hard_query_data.get("ratio", 0.2),
        ),
    )


def load_factory_config(path: Path) -> FactoryConfig:
    """Load complete factory configuration from a YAML file.

    Args:
        path: Path to the configuration YAML file.

    Returns:
        FactoryConfig populated from the YAML file.

    Raises:
        ConfigValidationError: If the config file is missing or invalid.
    """
    teacher_config = load_teacher_config(path)
    dataset_config = load_dataset_config(path)

    output_data = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if data:
            output_data = data.get("output", {})
    except yaml.YAMLError:  # pragma: no cover - unlikely in practice with controlled configs
        pass  # Use defaults if output section is missing

    output_config = OutputConfig(
        verbose=output_data.get("verbose", True),
        progress_interval=output_data.get("progress_interval", 100),
        dry_run=output_data.get("dry_run", False),
    )

    return FactoryConfig(
        teacher_model=teacher_config,
        dataset=dataset_config,
        output=output_config,
    )

