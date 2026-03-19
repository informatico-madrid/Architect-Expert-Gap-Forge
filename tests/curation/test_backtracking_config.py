"""Tests for backtracking_config module."""

import tempfile
from pathlib import Path

import pytest

from src.curation.backtracking_config import (
    BacktrackingConfig,
    PipelineReport,
    load_backtracking_config,
)


class TestBacktrackingConfig:
    """Tests for BacktrackingConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = BacktrackingConfig()
        assert config.max_tokens == 4000
        assert config.excluded_types == ("theory",)
        assert config.vllm_api_url == "http://localhost:8000/v1"
        assert config.vllm_model == "qwen3-30b-a3b-thinking-fp8"
        assert config.temperature == 0.6

    def test_custom_values(self):
        """Test custom configuration values."""
        config = BacktrackingConfig(
            max_tokens=5000,
            temperature=0.8,
            batch_size=20,
        )
        assert config.max_tokens == 5000
        assert config.temperature == 0.8
        assert config.batch_size == 20


class TestPipelineReport:
    """Tests for PipelineReport dataclass."""

    def test_create_report(self):
        """Test creating a pipeline report."""
        report = PipelineReport(
            total_input=100,
            filtered_out=10,
            rewritten=50,
            pass_through=30,
            failed=5,
            rejected=3,
            total_output=80,
            strategy_counts={"nominal": 30, "contrast": 20},
        )
        assert report.total_input == 100
        assert report.rewritten == 50
        assert report.total_output == 80


class TestLoadBacktrackingConfig:
    """Tests for load_backtracking_config function."""

    def test_load_config(self, tmp_path):
        """Test loading configuration from YAML file."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
max_tokens: 6000
temperature: 0.7
batch_size: 15
""")
        config = load_backtracking_config(config_file)
        assert config.max_tokens == 6000
        assert config.temperature == 0.7
        assert config.batch_size == 15

    def test_load_config_with_list_excluded_types(self, tmp_path):
        """Test loading config with excluded_types as list (should convert to tuple)."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
excluded_types:
  - theory
  - error_recovery
max_tokens: 5000
""")
        config = load_backtracking_config(config_file)
        assert config.excluded_types == ("theory", "error_recovery")
        assert config.max_tokens == 5000

    def test_load_config_unknown_fields(self, tmp_path):
        """Test loading config with unknown fields (should be filtered)."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
max_tokens: 5000
unknown_field: value
another_unknown: 123
""")
        config = load_backtracking_config(config_file)
        assert config.max_tokens == 5000
        # Unknown fields should be ignored (not raise)

    def test_load_empty_config(self, tmp_path):
        """Test loading empty config file (should use defaults)."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("")
        config = load_backtracking_config(config_file)
        # Should use defaults
        assert config.max_tokens == 4000
        assert config.temperature == 0.6
