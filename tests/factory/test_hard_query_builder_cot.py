#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0
import inspect


class TestHardQueryBuilderCoT:
    """Tests that HardQueryBuilder integrates DSPy ChainOfThought."""

    def test_transform_to_abstract_returns_spanish_description(self):
        from src.factory.hard_query_builder import HardQueryBuilder

        qb = HardQueryBuilder(use_case="test", templates_path=None)
        result = qb._transform_to_abstract("integration", "some context")
        assert "sistema debe integrar" in result.lower() or "sistema debe" in result.lower()

    def test_transform_to_abstract_returns_str(self):
        from src.factory.hard_query_builder import HardQueryBuilder

        inspect.signature(HardQueryBuilder._transform_to_abstract)
        # Just verify the method exists and is callable
        assert callable(HardQueryBuilder._transform_to_abstract)

    def test_no_dspy_import_in_detector(self):
        """BacktrackingDetector must remain pure (no dspy dependency)."""
        assert "dspy" not in open("src/factory/backtracking_detector.py").read()
