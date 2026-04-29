# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""Tests for backtrack_strategy module."""

from src.curation import backtrack_strategy as bs_module


class TestClassifyRewriteStrategy:
    """Tests for classify_rewrite_strategy function."""

    def test_classify_nominal(self):
        """Test classification of nominal example."""
        record = {"example_type": "nominal", "metadata": {"gold_injected": False}}
        result = bs_module.classify_rewrite_strategy(record)
        assert result is not None
        assert isinstance(result, str)

    def test_classify_contrast(self):
        """Test classification of contrast example."""
        record = {"example_type": "contrast", "metadata": {}}
        result = bs_module.classify_rewrite_strategy(record)
        assert result is not None

    def test_classify_error_recovery(self):
        """Test classification of error recovery example."""
        record = {"example_type": "error_recovery", "metadata": {}}
        result = bs_module.classify_rewrite_strategy(record)
        assert result is not None


class TestValidateResolutionNoLegacy:
    """Tests for _validate_resolution_no_legacy function."""

    def test_validate_resolution_valid(self):
        """Test validation with valid resolution."""
        new_think = "This is a valid think block"
        code_rest = "This is a modern implementation using async/await."
        regexes = ()
        result = bs_module._validate_resolution_no_legacy(new_think, code_rest, regexes)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_validate_resolution_empty(self):
        """Test validation with empty resolution."""
        result = bs_module._validate_resolution_no_legacy("", "", ())
        assert isinstance(result, tuple)


class TestLoadLegacyRegexes:
    """Tests for _load_legacy_regexes function."""

    def test_load_legacy_regexes_empty(self):
        """Test loading legacy regexes with empty path."""
        # Should return empty tuple for non-existent path
        result = bs_module._load_legacy_regexes("/nonexistent/path")
        assert isinstance(result, tuple)
        assert len(result) == 0
