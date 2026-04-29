#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
UNIT TESTS: Factory Configuration validation tests.

Tests cover:
- load_teacher_config: file not found, invalid YAML, empty config, valid config
- load_dataset_config: file not found, invalid YAML, empty config, valid config
- load_factory_config: file not found, invalid YAML, complete config

Location: tests/factory/test_factory_config.py
"""

import logging
from pathlib import Path

import pytest
import yaml

from src.factory.config import (
    TeacherModelConfig,
    DatasetConfig,
    FactoryConfig,
    TrajectoryConfig,
    HardQueryConfig,
    OutputConfig,
    load_teacher_config,
    load_dataset_config,
    load_factory_config,
)
from src.utils.exceptions import ConfigValidationError

logger = logging.getLogger(__name__)


# =============================================================================
# TEST FIXTURES
# =============================================================================


@pytest.fixture
def temp_config_dir(tmp_path) -> Path:
    """Create a temporary directory for config files."""
    return tmp_path


@pytest.fixture
def valid_teacher_config_yaml(temp_config_dir) -> Path:
    """Create a valid teacher model config YAML file."""
    config_path = temp_config_dir / "teacher_config.yaml"
    config_data = {
        "teacher_model": {
            "provider": "anthropic",
            "model_name": "claude-3-5-sonnet-20241022",
            "api_key_env": "ANTHROPIC_API_KEY",
            "base_url": "https://api.anthropic.com",
            "request_delay_ms": 1000,
            "max_retries": 3,
            "backoff_factor": 2,
            "request_timeout_seconds": 180,
            "checkpoint_path": "data/checkpoints/test_trajectories.json",
        }
    }
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config_data, f)
    return config_path


@pytest.fixture
def valid_dataset_config_yaml(temp_config_dir) -> Path:
    """Create a valid dataset config YAML file."""
    config_path = temp_config_dir / "dataset_config.yaml"
    config_data = {
        "dataset": {
            "use_case": "home_assistant",
            "target_specialized_records": 5000,
            "target_total_records": 20000,
            "output_path": "data/stage_2_output/test_trajectories.jsonl",
            "taxonomy_path": "configs/stage_2_factory/taxonomy/test_taxonomy.yaml",
            "trajectory": {
                "min_turns": 2,
                "max_turns": 8,
                "error_probability": 0.5,
                "cascade_probability": 0.2,
                "tool_format": "openai",
            },
            "hard_query": {
                "enabled": True,
                "ratio": 0.3,
            },
        }
    }
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config_data, f)
    return config_path


@pytest.fixture
def valid_full_config_yaml(temp_config_dir) -> Path:
    """Create a valid complete factory config YAML file."""
    config_path = temp_config_dir / "factory_config.yaml"
    config_data = {
        "teacher_model": {
            "provider": "openai",
            "model_name": "gpt-4o",
            "api_key_env": "OPENAI_API_KEY",
            "base_url": "https://api.openai.com/v1",
            "request_delay_ms": 500,
            "max_retries": 3,
            "backoff_factor": 2,
            "request_timeout_seconds": 120,
            "checkpoint_path": "data/checkpoints/test_trajectories.json",
        },
        "dataset": {
            "use_case": "home_assistant",
            "target_specialized_records": 10000,
            "target_total_records": 30000,
            "output_path": "data/stage_2_output/test_trajectories.jsonl",
            "taxonomy_path": "configs/stage_2_factory/taxonomy/home_assistant/agentic_taxonomy.yaml",
            "trajectory": {
                "min_turns": 3,
                "max_turns": 10,
                "error_probability": 0.7,
                "cascade_probability": 0.3,
                "tool_format": "auto",
            },
            "hard_query": {
                "enabled": False,
                "ratio": 0.2,
            },
        },
        "output": {
            "verbose": False,
            "progress_interval": 50,
            "dry_run": True,
        },
    }
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config_data, f)
    return config_path


@pytest.fixture
def empty_yaml_file(temp_config_dir) -> Path:
    """Create an empty YAML file."""
    config_path = temp_config_dir / "empty.yaml"
    config_path.write_text("")
    return config_path


@pytest.fixture
def invalid_yaml_file(temp_config_dir) -> Path:
    """Create an invalid YAML file."""
    config_path = temp_config_dir / "invalid.yaml"
    config_path.write_text("invalid: yaml: content: [}")
    return config_path


@pytest.fixture
def yaml_with_teacher_missing_fields(temp_config_dir) -> Path:
    """Create a YAML file with teacher_model missing some fields."""
    config_path = temp_config_dir / "partial_teacher.yaml"
    config_data = {
        "teacher_model": {
            "provider": "openai",
            "model_name": "gpt-4o",
        }
    }
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config_data, f)
    return config_path


@pytest.fixture
def yaml_with_dataset_missing_fields(temp_config_dir) -> Path:
    """Create a YAML file with dataset missing nested fields."""
    config_path = temp_config_dir / "partial_dataset.yaml"
    config_data = {
        "dataset": {
            "use_case": "test_case",
            "target_specialized_records": 1000,
        }
    }
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config_data, f)
    return config_path


# =============================================================================
# TEST CLASSES: load_teacher_config
# =============================================================================


class TestLoadTeacherConfig:
    """Tests for load_teacher_config function."""

    def test_load_teacher_config_file_not_found(self, temp_config_dir):
        """Test that ConfigValidationError is raised when config file doesn't exist."""
        non_existent_path = temp_config_dir / "non_existent.yaml"
        with pytest.raises(ConfigValidationError) as exc_info:
            load_teacher_config(non_existent_path)
        assert "Config file not found" in str(exc_info.value)

    def test_load_teacher_config_invalid_yaml(self, invalid_yaml_file):
        """Test that ConfigValidationError is raised for invalid YAML."""
        with pytest.raises(ConfigValidationError) as exc_info:
            load_teacher_config(invalid_yaml_file)
        assert "Invalid YAML" in str(exc_info.value)

    def test_load_teacher_config_empty_file(self, empty_yaml_file):
        """Test that ConfigValidationError is raised for empty config file."""
        with pytest.raises(ConfigValidationError) as exc_info:
            load_teacher_config(empty_yaml_file)
        assert "Config file is empty" in str(exc_info.value)

    def test_load_teacher_config_valid(self, valid_teacher_config_yaml):
        """Test loading valid teacher config returns correct TeacherModelConfig."""
        config = load_teacher_config(valid_teacher_config_yaml)
        assert isinstance(config, TeacherModelConfig)
        assert config.provider == "anthropic"
        assert config.model_name == "claude-3-5-sonnet-20241022"
        assert config.api_key_env == "ANTHROPIC_API_KEY"
        assert config.base_url == "https://api.anthropic.com"
        assert config.request_delay_ms == 1000
        assert config.max_retries == 3
        assert config.backoff_factor == 2
        assert config.request_timeout_seconds == 180
        assert config.checkpoint_path == "data/checkpoints/test_trajectories.json"

    def test_load_teacher_config_defaults(self, yaml_with_teacher_missing_fields):
        """Test that defaults are applied when fields are missing."""
        config = load_teacher_config(yaml_with_teacher_missing_fields)
        assert config.provider == "openai"
        assert config.model_name == "gpt-4o"
        assert config.api_key_env == "OPENAI_API_KEY"
        assert config.base_url is None
        assert config.request_delay_ms == 500
        assert config.max_retries == 5
        assert config.backoff_factor == 2
        assert config.request_timeout_seconds == 120
        assert config.checkpoint_path == "data/checkpoints/trajectories.json"

    def test_load_teacher_config_no_teacher_model_key(self, temp_config_dir):
        """Test loading YAML without teacher_model key uses defaults."""
        config_path = temp_config_dir / "no_teacher.yaml"
        config_data = {"other_key": "value"}
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f)

        config = load_teacher_config(config_path)
        assert config.provider == "openai"
        assert config.model_name == "gpt-4o"


# =============================================================================
# TEST CLASSES: load_dataset_config
# =============================================================================


class TestLoadDatasetConfig:
    """Tests for load_dataset_config function."""

    def test_load_dataset_config_file_not_found(self, temp_config_dir):
        """Test that ConfigValidationError is raised when config file doesn't exist."""
        non_existent_path = temp_config_dir / "non_existent.yaml"
        with pytest.raises(ConfigValidationError) as exc_info:
            load_dataset_config(non_existent_path)
        assert "Config file not found" in str(exc_info.value)

    def test_load_dataset_config_invalid_yaml(self, invalid_yaml_file):
        """Test that ConfigValidationError is raised for invalid YAML."""
        with pytest.raises(ConfigValidationError) as exc_info:
            load_dataset_config(invalid_yaml_file)
        assert "Invalid YAML" in str(exc_info.value)

    def test_load_dataset_config_empty_file(self, empty_yaml_file):
        """Test that ConfigValidationError is raised for empty config file."""
        with pytest.raises(ConfigValidationError) as exc_info:
            load_dataset_config(empty_yaml_file)
        assert "Config file is empty" in str(exc_info.value)

    def test_load_dataset_config_valid(self, valid_dataset_config_yaml):
        """Test loading valid dataset config returns correct DatasetConfig."""
        config = load_dataset_config(valid_dataset_config_yaml)
        assert isinstance(config, DatasetConfig)
        assert config.use_case == "home_assistant"
        assert config.target_specialized_records == 5000
        assert config.target_total_records == 20000
        assert config.output_path == "data/stage_2_output/test_trajectories.jsonl"
        assert (
            config.taxonomy_path
            == "configs/stage_2_factory/taxonomy/test_taxonomy.yaml"
        )

        # Check nested trajectory config
        assert isinstance(config.trajectory, TrajectoryConfig)
        assert config.trajectory.min_turns == 2
        assert config.trajectory.max_turns == 8
        assert config.trajectory.error_probability == 0.5
        assert config.trajectory.cascade_probability == 0.2
        assert config.trajectory.tool_format == "openai"

        # Check nested hard_query config
        assert isinstance(config.hard_query, HardQueryConfig)
        assert config.hard_query.enabled is True
        assert config.hard_query.ratio == 0.3

    def test_load_dataset_config_defaults(self, yaml_with_dataset_missing_fields):
        """Test that defaults are applied when nested fields are missing."""
        config = load_dataset_config(yaml_with_dataset_missing_fields)
        assert config.use_case == "test_case"
        assert config.target_specialized_records == 1000

        # Trajectory defaults
        assert config.trajectory.min_turns == 3
        assert config.trajectory.max_turns == 10
        assert config.trajectory.error_probability == 0.7
        assert config.trajectory.cascade_probability == 0.3
        assert config.trajectory.tool_format == "auto"

        # Hard query defaults
        assert config.hard_query.enabled is False
        assert config.hard_query.ratio == 0.2

    def test_load_dataset_config_no_dataset_key(self, temp_config_dir):
        """Test loading YAML without dataset key uses defaults."""
        config_path = temp_config_dir / "no_dataset.yaml"
        config_data = {"other_key": "value"}
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f)

        config = load_dataset_config(config_path)
        assert config.use_case == "home_assistant"
        assert config.target_specialized_records == 12000


# =============================================================================
# TEST CLASSES: load_factory_config
# =============================================================================


class TestLoadFactoryConfig:
    """Tests for load_factory_config function."""

    def test_load_factory_config_file_not_found(self, temp_config_dir):
        """Test that ConfigValidationError is raised when config file doesn't exist."""
        non_existent_path = temp_config_dir / "non_existent.yaml"
        with pytest.raises(ConfigValidationError) as exc_info:
            load_factory_config(non_existent_path)
        assert "Config file not found" in str(exc_info.value)

    def test_load_factory_config_invalid_yaml(self, invalid_yaml_file):
        """Test that ConfigValidationError is raised for invalid YAML."""
        with pytest.raises(ConfigValidationError) as exc_info:
            load_factory_config(invalid_yaml_file)
        assert "Invalid YAML" in str(exc_info.value)

    def test_load_factory_config_empty_file(self, empty_yaml_file):
        """Test that ConfigValidationError is raised for empty config file."""
        with pytest.raises(ConfigValidationError) as exc_info:
            load_factory_config(empty_yaml_file)
        assert "Config file is empty" in str(exc_info.value)

    def test_load_factory_config_valid(self, valid_full_config_yaml):
        """Test loading valid full factory config returns correct FactoryConfig."""
        config = load_factory_config(valid_full_config_yaml)
        assert isinstance(config, FactoryConfig)

        # Check teacher model
        assert isinstance(config.teacher_model, TeacherModelConfig)
        assert config.teacher_model.provider == "openai"
        assert config.teacher_model.model_name == "gpt-4o"

        # Check dataset
        assert isinstance(config.dataset, DatasetConfig)
        assert config.dataset.use_case == "home_assistant"
        assert config.dataset.target_specialized_records == 10000
        assert config.dataset.target_total_records == 30000

        # Check output
        assert isinstance(config.output, OutputConfig)
        assert config.output.verbose is False
        assert config.output.progress_interval == 50
        assert config.output.dry_run is True

    def test_load_factory_config_partial_with_defaults(
        self, yaml_with_teacher_missing_fields
    ):
        """Test loading partial config with missing fields uses defaults."""
        # This file only has teacher_model with some fields
        config = load_factory_config(yaml_with_teacher_missing_fields)

        # Teacher model should have partial data and defaults
        assert config.teacher_model.provider == "openai"
        assert config.teacher_model.model_name == "gpt-4o"

        # Dataset should use all defaults
        assert config.dataset.use_case == "home_assistant"
        assert config.dataset.target_specialized_records == 12000

        # Output should use defaults
        assert config.output.verbose is True
        assert config.output.progress_interval == 100
        assert config.output.dry_run is False

    def test_load_factory_config_merges_configs(
        self, valid_teacher_config_yaml, valid_dataset_config_yaml
    ):
        """Test that load_factory_config loads from a single file."""
        # Create a combined config
        combined_path = valid_teacher_config_yaml.parent / "combined.yaml"
        with open(valid_teacher_config_yaml) as f:
            teacher_data = yaml.safe_load(f)
        with open(valid_dataset_config_yaml) as f:
            dataset_data = yaml.safe_load(f)

        combined_data = {
            "teacher_model": teacher_data.get("teacher_model", {}),
            "dataset": dataset_data.get("dataset", {}),
            "output": {"verbose": True, "progress_interval": 200, "dry_run": False},
        }
        with open(combined_path, "w") as f:
            yaml.dump(combined_data, f)

        config = load_factory_config(combined_path)

        # Verify teacher_model from first file
        assert config.teacher_model.provider == "anthropic"

        # Verify dataset from second file
        assert config.dataset.target_specialized_records == 5000

        # Verify output
        assert config.output.progress_interval == 200
