#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0
"""
Anchor Dataset — Sample Config Generator

Generate SampleConfig objects with exact domain/difficulty distribution
using floor-based rounding. Seed-based deterministic generation.

SPDX-License-Identifier: Apache-2.0
Copyright 2026 AEGF
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from .seed_loader import NormalizedSeed


# ── Data classes ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SampleConfig:
    """Frozen config for a single anchor sample."""

    sample_id: str
    domain: str
    difficulty: str
    turn_count: int
    seed_reference: str | None = None
    domain_context: str = ""
    target_provider: str = "vllm"


# ── Distribution helpers ──────────────────────────────────────────────────────

_DOMAIN_PCTS: list[tuple[str, float]] = [
    ("home_assistant", 0.40),
    ("php_legacy", 0.30),
    ("generic_domain", 0.20),
    ("other", 0.10),
]

_DIFFICULTY_FRACTIONS: list[tuple[str, float]] = [
    ("easy", 0.30),
    ("medium", 0.50),
    ("hard", 0.20),
]

_DIFFICULTY_TURNS: dict[str, int] = {
    "easy": 3,
    "medium": 4,
    "hard": 5,
}


def _distribute(total: int, pcts: list[tuple[str, float]]) -> dict[str, int]:
    """Floor-based rounding with largest-remainder remainder distribution.

    For *total*=50, *pcts*=[("a",0.4),("b",0.3),("c",0.2),("d",0.1)]:
        floor → a=20, b=15, c=10, d=5 → sum=50, remainder=0
    For *total*=7, *pcts*=[("a",0.4),("b",0.3),("c",0.2),("d",0.1)]:
        floor → a=2, b=2, c=1, d=0 → sum=5, remainder=2
        fractional → d=0.1(+1), c=0.2(+1) → final a=2,b=2,c=2,d=1
    """
    floors: dict[str, int] = {}
    frac: dict[str, float] = {}
    for name, pct in pcts:
        floors[name] = int(total * pct)
        frac[name] = total * pct - floors[name]

    remainder = total - sum(floors.values())
    if remainder > 0:
        ranked = sorted(frac, key=lambda n: frac[n], reverse=True)
        for i in range(remainder):
            floors[ranked[i]] += 1

    return floors


# ── Generator ─────────────────────────────────────────────────────────────────


@dataclass
class SampleConfigGenerator:
    """Generate SampleConfig objects with deterministic distribution."""

    seeds: list[NormalizedSeed] = field(default_factory=list)
    seed: int = 42

    def __post_init__(self) -> None:
        self._domain_pools: dict[str, list[NormalizedSeed]] = {}
        for s in self.seeds:
            self._domain_pools.setdefault(s.domain, []).append(s)
        self._domain_cycles: dict[str, int] = {}
        for d in self._domain_pools:
            self._domain_cycles[d] = 0

    def generate_configs(self, count: int) -> list[SampleConfig]:
        """Generate *count* SampleConfigs with exact domain/difficulty distribution.

        Domains: home_assistant 40%, php_legacy 30%, generic_domain 20%, other 10%
        Difficulty per domain: easy 30% (turns=3), medium 50% (turns=4), hard 20% (turns=5)
        """
        # Reset cycles so repeated calls are deterministic
        for d in self._domain_cycles:
            self._domain_cycles[d] = 0

        domain_counts = _distribute(count, _DOMAIN_PCTS)

        configs: list[SampleConfig] = []
        sample_idx = 0

        for domain, dcount in domain_counts.items():
            diff_counts = _distribute(dcount, _DIFFICULTY_FRACTIONS)
            for difficulty, dcount_val in diff_counts.items():
                turn_count = _DIFFICULTY_TURNS[difficulty]
                for _ in range(dcount_val):
                    sid = f"anchor_001_{sample_idx:03d}"

                    # Seed reference: cycle through matching domain seeds
                    pool = self._domain_pools.get(domain, [])
                    if pool:
                        cycle = self._domain_cycles[domain]
                        self._domain_cycles[domain] = (cycle + 1) % len(pool)
                        seed_ref = pool[cycle].seed_id
                    else:
                        seed_ref = None

                    cfg = SampleConfig(
                        sample_id=sid,
                        domain=domain,
                        difficulty=difficulty,
                        turn_count=turn_count,
                        seed_reference=seed_ref,
                    )
                    configs.append(cfg)
                    sample_idx += 1

        random.Random(self.seed).shuffle(configs)
        return configs


class PromptBuilder:
    """Build system and user prompts with few-shot examples from seeds."""

    SYSTEM_TEMPLATE = """\
DOMAIN: {domain}
CATEGORY: {category}
DIFFICULTY: {difficulty}

FEW-SHOT EXAMPLES:
{few_shot}

QUALITY CONSTRAINTS:
- Anti-laziness: No placeholders like '...', '# TODO', 'pass # implement', '# resto del codigo'
- Turn count must be exactly {turn_count} turns
- Self-assessed quality must be >= 0.3
- Tool calls must follow [TOOL_CALL:...] syntax
"""

    USER_TEMPLATE = """\
Generate an anchor sample for the following configuration:
- Domain: {domain}
- Difficulty: {difficulty}
- Turn count: {turn_count}
- Context: {domain_context}
"""

    def __init__(self, seeds: list[NormalizedSeed]):
        self.seeds = seeds

    def build(self, config: SampleConfig) -> tuple[str, str]:
        """Build (system_prompt, user_prompt) tuple for *config*.

        Returns all template variables filled with concrete values.
        """
        matching = [s for s in self.seeds if s.domain == config.domain]
        if not matching:
            matching = self.seeds[:3]

        few_shot = "\n\n".join(
            f"Seed: {s.seed_id}\nContext: {s.context}\nQuestion: {s.question}"
            for s in matching[:3]
        )

        system = self.SYSTEM_TEMPLATE.format(
            domain=config.domain,
            category=matching[0].category if matching else "general",
            difficulty=config.difficulty,
            few_shot=few_shot,
            turn_count=config.turn_count,
        )

        user = self.USER_TEMPLATE.format(
            domain=config.domain,
            difficulty=config.difficulty,
            turn_count=config.turn_count,
            domain_context=config.domain_context or "General configuration management",
        )

        return system, user
