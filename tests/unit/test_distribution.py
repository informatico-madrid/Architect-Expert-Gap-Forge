#!/usr/bin/env python3
# Copyright 2026 Bunker AI
# SPDX-License-Identifier: Apache-2.0
"""Tests for SampleConfigGenerator distribution math and determinism."""
from __future__ import annotations

from collections import Counter

import pytest

from infrastructure.anchor_dataset.sample_generator import (
    SampleConfig,
    SampleConfigGenerator,
    _distribute,
    _DIFFICULTY_FRACTIONS,
    _DIFFICULTY_TURNS,
    _DOMAIN_PCTS,
)
from infrastructure.anchor_dataset.seed_loader import NormalizedSeed


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sample_seed(seed_id: str, domain: str) -> NormalizedSeed:
    return NormalizedSeed(
        seed_id=seed_id,
        domain=domain,
        category="general",
        complexity="nominal_easy",
        context="test",
        question="test question",
        expected_patterns=[],
    )


# ---------------------------------------------------------------------------
# Domain distribution tests
# ---------------------------------------------------------------------------


class TestDomainDistribution:
    """Verify floor-based rounding produces exact domain counts."""

    @pytest.mark.parametrize(
        "count, expected",
        [
            (50, {"home_assistant": 20, "php_legacy": 15, "generic_domain": 10, "other": 5}),
            (110, {"home_assistant": 44, "php_legacy": 33, "generic_domain": 22, "other": 11}),
            (200, {"home_assistant": 80, "php_legacy": 60, "generic_domain": 40, "other": 20}),
        ],
    )
    def test_domain_counts(self, count: int, expected: dict[str, int]) -> None:
        seeds = [
            _sample_seed("ha_1", "home_assistant"),
            _sample_seed("ha_2", "home_assistant"),
            _sample_seed("php_1", "php_legacy"),
        ]
        gen = SampleConfigGenerator(seeds, seed=42)
        configs = gen.generate_configs(count)

        assert len(configs) == count
        domain_counts = Counter(c.domain for c in configs)

        for domain, want in expected.items():
            assert domain_counts[domain] == want, (
                f"{domain}: expected {want}, got {domain_counts[domain]}"
            )

        # Verify percentages match spec
        for domain, pct in _DOMAIN_PCTS:
            frac = domain_counts[domain] / count
            assert abs(frac - pct) < 0.02, f"{domain} fraction {frac} differs from {pct}"


class TestDistributionRounding:
    """Test the internal _distribute helper directly."""

    def test_floor_rounding_exact(self) -> None:
        result = _distribute(100, _DOMAIN_PCTS)
        assert result == {"home_assistant": 40, "php_legacy": 30, "generic_domain": 20, "other": 10}

    def test_floor_rounding_partial(self) -> None:
        result = _distribute(10, _DOMAIN_PCTS)
        assert result["home_assistant"] == 4
        assert result["php_legacy"] == 3
        assert result["generic_domain"] == 2
        assert result["other"] == 1
        assert sum(result.values()) == 10

    def test_sum_equals_total(self) -> None:
        for count in [1, 7, 13, 37, 99, 150, 250]:
            for pcts in [_DOMAIN_PCTS, _DIFFICULTY_FRACTIONS]:
                result = _distribute(count, pcts)
                assert sum(result.values()) == count

    def test_largest_remainder(self) -> None:
        """Remainder goes to largest fractional parts first."""
        result = _distribute(7, [
            ("a", 0.4),
            ("b", 0.3),
            ("c", 0.2),
            ("d", 0.1),
        ])
        # floor: a=2,b=2,c=1,d=0 sum=5 remainder=2
        # frac: a=0.8,d=0.7,c=0.4,b=0.1 → a(+1),d(+1)
        assert result["a"] == 3
        assert result["c"] == 1
        assert result["b"] == 2
        assert result["d"] == 1
        assert sum(result.values()) == 7


# ---------------------------------------------------------------------------
# Difficulty distribution tests
# ---------------------------------------------------------------------------


class TestDifficultyDistribution:
    """Verify difficulty is 30/50/20 per domain."""

    def test_difficulty_distribution(self) -> None:
        seeds = [
            _sample_seed("ha_1", "home_assistant"),
            _sample_seed("php_1", "php_legacy"),
        ]
        gen = SampleConfigGenerator(seeds, seed=42)
        configs = gen.generate_configs(100)

        domain_diff = Counter()
        for c in configs:
            domain_diff[(c.domain, c.difficulty)] += 1

        # Check each domain has correct difficulty split
        for domain in {"home_assistant", "php_legacy", "generic_domain", "other"}:
            domain_total = sum(v for k, v in domain_diff.items() if k[0] == domain)
            if domain_total == 0:
                continue

            easy = sum(v for k, v in domain_diff.items() if k == (domain, "easy"))
            medium = sum(v for k, v in domain_diff.items() if k == (domain, "medium"))
            hard = sum(v for k, v in domain_diff.items() if k == (domain, "hard"))

            assert easy + medium + hard == domain_total

            # Verify fractions are within tolerance
            assert abs(easy / domain_total - 0.30) < 0.02, f"{domain} easy fraction off"
            assert abs(medium / domain_total - 0.50) < 0.02, f"{domain} medium fraction off"
            assert abs(hard / domain_total - 0.20) < 0.02, f"{domain} hard fraction off"

    def test_difficulty_sum_per_domain(self) -> None:
        seeds = [_sample_seed("ha_1", "home_assistant")]
        gen = SampleConfigGenerator(seeds, seed=42)
        configs = gen.generate_configs(50)

        ha_configs = [c for c in configs if c.domain == "home_assistant"]
        diff_counts = Counter(c.difficulty for c in ha_configs)
        assert sum(diff_counts.values()) == len(ha_configs)


# ---------------------------------------------------------------------------
# Turn count tests
# ---------------------------------------------------------------------------


class TestTurnCount:
    """Verify turn_count matches difficulty mapping: easy=3, medium=4, hard=5."""

    def test_turn_counts(self) -> None:
        seeds = [
            _sample_seed("ha_1", "home_assistant"),
            _sample_seed("php_1", "php_legacy"),
        ]
        gen = SampleConfigGenerator(seeds, seed=42)
        configs = gen.generate_configs(100)

        for c in configs:
            expected_turns = _DIFFICULTY_TURNS[c.difficulty]
            assert c.turn_count == expected_turns, (
                f"{c.domain}/{c.difficulty}: expected turns={expected_turns}, got {c.turn_count}"
            )

    def test_turn_count_mapping(self) -> None:
        """Confirm the source mapping is correct."""
        assert _DIFFICULTY_TURNS == {"easy": 3, "medium": 4, "hard": 5}

    def test_all_difficulties_present(self) -> None:
        seeds = [_sample_seed("ha_1", "home_assistant")]
        gen = SampleConfigGenerator(seeds, seed=42)
        configs = gen.generate_configs(100)

        difficulties = {c.difficulty for c in configs}
        assert difficulties == {"easy", "medium", "hard"}

        for diff in ["easy", "medium", "hard"]:
            turns = _DIFFICULTY_TURNS[diff]
            diff_configs = [c for c in configs if c.difficulty == diff]
            assert all(c.turn_count == turns for c in diff_configs)


# ---------------------------------------------------------------------------
# Determinism tests
# ---------------------------------------------------------------------------


class TestDeterminism:
    """Verify same seed produces identical output."""

    def test_deterministic_ordering(self) -> None:
        seeds = [
            _sample_seed("ha_1", "home_assistant"),
            _sample_seed("ha_2", "home_assistant"),
            _sample_seed("php_1", "php_legacy"),
        ]
        gen1 = SampleConfigGenerator(seeds, seed=42)
        gen2 = SampleConfigGenerator(seeds, seed=42)

        configs1 = gen1.generate_configs(50)
        configs2 = gen2.generate_configs(50)

        assert len(configs1) == len(configs2)

        for i, (c1, c2) in enumerate(zip(configs1, configs2)):
            assert c1.sample_id == c2.sample_id, f"idx={i}"
            assert c1.domain == c2.domain, f"idx={i}"
            assert c1.difficulty == c2.difficulty, f"idx={i}"
            assert c1.turn_count == c2.turn_count, f"idx={i}"

    def test_different_seed_different_order(self) -> None:
        seeds = [
            _sample_seed("ha_1", "home_assistant"),
            _sample_seed("ha_2", "home_assistant"),
        ]
        gen1 = SampleConfigGenerator(seeds, seed=42)
        gen2 = SampleConfigGenerator(seeds, seed=99)

        configs1 = gen1.generate_configs(50)
        configs2 = gen2.generate_configs(50)

        # Counts should be identical
        counter1 = Counter((c.domain, c.difficulty) for c in configs1)
        counter2 = Counter((c.domain, c.difficulty) for c in configs2)
        assert counter1 == counter2

        # Order should differ (at least some configs are in different positions)
        any_different = False
        for c1, c2 in zip(configs1, configs2):
            if c1.sample_id != c2.sample_id:
                any_different = True
                break
        assert any_different, "Different seeds should produce different orderings"

    def test_reproducibility_across_calls(self) -> None:
        seeds = [_sample_seed("ha_1", "home_assistant")]
        gen = SampleConfigGenerator(seeds, seed=42)

        run1 = gen.generate_configs(50)
        run2 = gen.generate_configs(50)

        assert len(run1) == len(run2)
        for c1, c2 in zip(run1, run2):
            assert c1.sample_id == c2.sample_id
            assert c1.domain == c2.domain
            assert c1.difficulty == c2.difficulty

    def test_different_count_different_configs(self) -> None:
        seeds = [_sample_seed("ha_1", "home_assistant")]
        gen = SampleConfigGenerator(seeds, seed=42)

        small = gen.generate_configs(10)
        large = gen.generate_configs(100)

        assert len(small) == 10
        assert len(large) == 100
