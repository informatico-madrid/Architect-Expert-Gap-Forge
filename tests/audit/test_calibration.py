# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for calibration module helper functions.

Tests simple standalone functions that don't require complex mocking.

Author: Claude Opus 4.6
"""

from __future__ import annotations

import pytest


class TestCalcCombinations:
    """Tests for _calc_combinations function."""

    def test_calc_combinations_empty_grid(self) -> None:
        """Test empty grid returns 1."""
        from src.audit.calibration import _calc_combinations

        result = _calc_combinations({})
        assert result == 1

    def test_calc_combinations_single_param(self) -> None:
        """Test single parameter grid."""
        from src.audit.calibration import _calc_combinations

        grid = {"temperature": [0.5, 0.7, 1.0]}
        result = _calc_combinations(grid)
        assert result == 3

    def test_calc_combinations_multiple_params(self) -> None:
        """Test multiple parameters grid."""
        from src.audit.calibration import _calc_combinations

        grid = {
            "temperature": [0.5, 0.7, 1.0],
            "top_p": [0.8, 0.9],
            "top_k": [40, 80],
        }
        result = _calc_combinations(grid)
        assert result == 3 * 2 * 2  # 12

    def test_calc_combinations_single_value_per_param(self) -> None:
        """Test single value per parameter."""
        from src.audit.calibration import _calc_combinations

        grid = {"temp": [0.7], "top_p": [0.9]}
        result = _calc_combinations(grid)
        assert result == 1 * 1  # 1


class TestCountWords:
    """Tests for count_words function."""

    def test_count_words_empty_string(self) -> None:
        """Test empty string returns 0."""
        from src.audit.calibration import count_words

        result = count_words("")
        assert result == 0

    def test_count_words_none(self) -> None:
        """Test None returns 0."""
        from src.audit.calibration import count_words

        result = count_words(None)  # type: ignore
        assert result == 0

    def test_count_words_single_word(self) -> None:
        """Test single word returns 1."""
        from src.audit.calibration import count_words

        result = count_words("hello")
        assert result == 1

    def test_count_words_multiple_words(self) -> None:
        """Test multiple words."""
        from src.audit.calibration import count_words

        result = count_words("hello world test")
        assert result == 3

    def test_count_words_with_extra_spaces(self) -> None:
        """Test words with extra spaces."""
        from src.audit.calibration import count_words

        result = count_words("  hello   world  ")
        assert result == 2


class TestAdjustForIncrease:
    """Tests for _adjust_for_increase function."""

    def test_adjust_for_increase_basic(self) -> None:
        """Test basic upward adjustment."""
        from src.audit.calibration import _adjust_for_increase

        values = [0.5, 0.7, 1.0]
        result = _adjust_for_increase(values, "temperature")
        assert len(result) == 3
        # Values should be shifted upward
        assert all(result[i] >= values[i] for i in range(len(values)))

    def test_adjust_for_increase_empty_list(self) -> None:
        """Test empty list returns empty list."""
        from src.audit.calibration import _adjust_for_increase

        result = _adjust_for_increase([], "temperature")
        assert result == []

    def test_adjust_for_increase_single_value(self) -> None:
        """Test single value."""
        from src.audit.calibration import _adjust_for_increase

        values = [0.5]
        result = _adjust_for_increase(values, "temperature")
        assert len(result) == 1


class TestAdjustForDecrease:
    """Tests for _adjust_for_decrease function."""

    def test_adjust_for_decrease_basic(self) -> None:
        """Test basic downward adjustment."""
        from src.audit.calibration import _adjust_for_decrease

        values = [0.5, 0.7, 1.0]
        result = _adjust_for_decrease(values, "temperature")
        assert len(result) == 3
        # Values should be shifted downward
        assert all(result[i] <= values[i] for i in range(len(values)))

    def test_adjust_for_decrease_empty_list(self) -> None:
        """Test empty list returns empty list."""
        from src.audit.calibration import _adjust_for_decrease

        result = _adjust_for_decrease([], "temperature")
        assert result == []

    def test_adjust_for_decrease_single_value(self) -> None:
        """Test single value."""
        from src.audit.calibration import _adjust_for_decrease

        values = [0.5]
        result = _adjust_for_decrease(values, "temperature")
        assert len(result) == 1


class TestClampToValidRange:
    """Tests for _clamp_to_valid_range function."""

    def test_clamp_to_valid_range_basic(self) -> None:
        """Test basic clamping."""
        from src.audit.calibration import _clamp_to_valid_range

        result = _clamp_to_valid_range(2.0, 0.5, "temperature")
        assert isinstance(result, float)

    def test_clamp_to_valid_range_already_in_range(self) -> None:
        """Test value already in valid range."""
        from src.audit.calibration import _clamp_to_valid_range

        result = _clamp_to_valid_range(0.7, 0.5, "temperature")
        # Should remain around the same value
        assert 0.5 <= result <= 1.5


class TestSortValuesByPriority:
    """Tests for _sort_values_by_priority function."""

    def test_sort_values_by_priority_empty(self) -> None:
        """Test empty list."""
        from src.audit.calibration import _sort_values_by_priority

        result = _sort_values_by_priority([], "temperature")
        assert result == []

    def test_sort_values_by_priority_basic(self) -> None:
        """Test basic sorting."""
        from src.audit.calibration import _sort_values_by_priority

        values = [0.5, 1.0, 0.7]
        result = _sort_values_by_priority(values, "temperature")
        assert len(result) == 3


