#!/usr/bin/env python3
# Copyright 2026 Bunker AI
# SPDX-License-Identifier: Apache-2.0
# -*- coding: utf-8 -*-
"""Tests for seed_loader — load_seeds function."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
import yaml

from infrastructure.anchor_dataset.seed_loader import (
    NormalizedSeed,
    load_seeds,
)


class TestLoadSeedsExistingYaml:
    """Test loading existing YAML with correct NormalizedSeed objects."""

    def test_loads_default_fixture(self):
        """load_seeds with default path loads seeds from the fixture."""
        seeds = load_seeds()
        assert len(seeds) > 0

        # Default seeds have domain "home_assistant"
        for seed in seeds:
            assert isinstance(seed, NormalizedSeed)

    def test_home_assistant_seeds_correct_domain(self):
        """Top-level 'seeds' list → home_assistant domain."""
        seeds = load_seeds()
        ha_seeds = [s for s in seeds if s.domain == "home_assistant"]
        # The fixture has 8 seeds
        assert len(ha_seeds) == 8

    def test_php_legacy_seeds_correct_domain(self):
        """'php_legacy_seeds' list → php_legacy domain."""
        seeds = load_seeds()
        php_seeds = [s for s in seeds if s.domain == "php_legacy"]
        # The fixture has 5 php_legacy seeds
        assert len(php_seeds) == 5

    def test_seed_fields_normalized(self):
        """NormalizedSeed fields are properly coerced to expected types."""
        seeds = load_seeds()
        ha_seed = [s for s in seeds if s.domain == "home_assistant"][0]
        assert isinstance(ha_seed.seed_id, str)
        assert isinstance(ha_seed.domain, str)
        assert isinstance(ha_seed.category, str)
        assert isinstance(ha_seed.complexity, str)
        assert isinstance(ha_seed.context, str)
        assert isinstance(ha_seed.question, str)
        assert isinstance(ha_seed.expected_patterns, list)
        assert len(ha_seed.expected_patterns) > 0

    def test_context_and_question_stripped(self):
        """context and question have leading/trailing whitespace stripped."""
        seeds = load_seeds()
        for seed in seeds:
            assert seed.context == seed.context.strip()
            assert seed.question == seed.question.strip()

    def test_all_seed_ids_present(self):
        """All seed IDs from the fixture are loaded."""
        seeds = load_seeds()
        ids = {s.seed_id for s in seeds}
        expected = {f"ha_seed_{i:03d}" for i in range(1, 9)}
        expected.update({f"php_legacy_seed_{i:03d}" for i in range(1, 6)})
        assert ids == expected


class TestLoadSeedsMissingFile:
    """Test missing file returns empty list with INFO log."""

    def test_missing_file_returns_empty_list(self):
        """load_seeds with non-existent file returns []."""
        result = load_seeds(seed_file=Path("/nonexistent/path/seeds.yaml"))
        assert result == []

    def test_missing_file_logs_info(self, caplog):
        """load_seeds logs INFO when file is missing."""
        with caplog.at_level(logging.INFO):
            load_seeds(seed_file=Path("/nonexistent/path/seeds.yaml"))
        assert any("not found" in record.message.lower() for record in caplog.records)


class TestLoadSeedsIdempotent:
    """Test idempotent loads."""

    def test_multiple_loads_return_same_length(self):
        """Calling load_seeds multiple times returns consistent results."""
        first = load_seeds()
        second = load_seeds()
        assert len(first) == len(second)

    def test_multiple_loads_return_independent_lists(self):
        """Each call returns a new list (no shared state)."""
        first = load_seeds()
        second = load_seeds()
        assert first is not second
        # Modifying one does not affect the other
        first.clear()
        assert len(second) > 0


class TestLoadSeedsMalformedYaml:
    """Test malformed YAML handling."""

    def test_invalid_yaml_returns_empty(self, tmp_path):
        """Malformed YAML file returns empty list (yaml.safe_load raises)."""
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text("{{{{invalid yaml::::")
        with pytest.raises(Exception):
            load_seeds(seed_file=bad_yaml)

    def test_empty_file_returns_empty(self, tmp_path):
        """Empty YAML file (empty dict) returns empty list."""
        empty_yaml = tmp_path / "empty.yaml"
        empty_yaml.write_text("")
        result = load_seeds(seed_file=empty_yaml)
        assert result == []

    def test_missing_seeds_key_returns_empty(self, tmp_path):
        """YAML without 'seeds' key returns empty list."""
        no_seeds = tmp_path / "no_seeds.yaml"
        no_seeds.write_text(yaml.dump({"other_key": "value"}))
        result = load_seeds(seed_file=no_seeds)
        assert result == []

    def test_non_dict_root_returns_empty(self, tmp_path):
        """YAML with non-dict root returns empty list."""
        list_yaml = tmp_path / "list.yaml"
        list_yaml.write_text(yaml.dump(["item1", "item2"]))
        result = load_seeds(seed_file=list_yaml)
        assert result == []
