#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0


class TestForbiddenTerms:
    """Tests for forbidden term detection in HardQueryBuilder."""

    def test_forbidden_terms_list_exists(self):
        """Forbidden terms list should be defined."""
        from src.factory.hard_query_builder import HardQueryBuilder

        assert hasattr(HardQueryBuilder, "forbidden_terms")

    def test_forbidden_terms_are_strings(self):
        """All forbidden terms should be strings."""
        from src.factory.hard_query_builder import HardQueryBuilder

        builder = HardQueryBuilder(use_case="home_assistant")
        terms = builder.forbidden_terms
        assert isinstance(terms, list)
        assert all(isinstance(t, str) for t in terms)
        assert len(terms) > 0
