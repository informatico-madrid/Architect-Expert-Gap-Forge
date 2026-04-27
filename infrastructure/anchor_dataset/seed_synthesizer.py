#!/usr/bin/env python3
# Copyright 2026 Bunker AI
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from infrastructure.anchor_dataset.seed_loader import NormalizedSeed

logger = logging.getLogger(__name__)

# Forbidden strings that indicate leakage from reference corpus
LEAKAGE_PATTERNS = [
    r"(?i)home\.assistant",
    r"(?i)home_assistant",
    r"(?i)homeassistant",
    r"(?i)ha\.config",
    r"(?i)hass\.io",
    r"(?i)iot\.core",
    r"(?i)smart\.home",
    r"(?i)zigbee2mqtt",
    r"(?i)zwave",
]


class SeedSynthesizer:
    def __init__(
        self,
        reference_path: str | Path = "tests/fixtures/reference_corpus",
        llm_client: Any = None,
    ):
        self.reference_path = Path(reference_path)
        self._llm_client = llm_client
        self._leakage_re = [re.compile(p) for p in LEAKAGE_PATTERNS]

    def reference_scan(self) -> list[str]:
        """Read code files from reference corpus, return list of patterns."""
        patterns = []
        if not self.reference_path.exists():
            logger.info("No reference corpus at %s", self.reference_path)
            return patterns
        for root, _dirs, files in self.reference_path.walk():
            for fname in files:
                if fname.endswith((".py", ".yaml", ".yml", ".md")):
                    fpath = root / fname
                    try:
                        content = fpath.read_text()[:500]  # First 500 chars
                        patterns.append(content)
                    except OSError:
                        pass
        return patterns

    def abstract_seeds(
        self, patterns: list[str], count: int = 10
    ) -> list[NormalizedSeed]:
        """Call LLM to abstract patterns into normalized seeds. For POC, return stubs."""
        if not self._llm_client:
            # POC fallback: return stub seeds from patterns
            seeds = []
            for i, pat in enumerate(patterns[:count]):
                seeds.append(
                    NormalizedSeed(
                        seed_id=f"synth_{i:03d}",
                        domain="generic_domain",
                        category="config",
                        complexity="nominal_easy",
                        context=pat[:100] if pat else "General configuration",
                        question="How to configure properly?",
                        expected_patterns=[],
                    )
                )
            return seeds
        # LLM path would go here in production
        return []

    def classify_domains(self, seeds: list[NormalizedSeed]) -> list[NormalizedSeed]:
        """Assign domain labels to seeds."""
        for seed in seeds:
            if seed.domain == "generic_domain":
                # Keep as generic
                pass
        return seeds

    def filter_leakage(self, seeds: list[NormalizedSeed]) -> list[NormalizedSeed]:
        """Remove seeds that leak reference corpus content."""
        return [s for s in seeds if self.validate_no_leakage([s])]

    def validate_no_leakage(self, seeds: list[NormalizedSeed]) -> bool:
        """Check seeds for forbidden strings. Returns True if clean, False if leaking."""
        for seed in seeds:
            text = f"{seed.context} {seed.question} {seed.seed_id}".lower()
            for pattern in self._leakage_re:
                if pattern.search(text):
                    return False
        return True

    def validate_freshness(self, seeds: list[NormalizedSeed]) -> list[NormalizedSeed]:
        """Ensure seeds are fresh (not copies of existing seed_examples)."""
        # POC: return as-is
        return seeds

    def synthesize(self, domain: str, count: int = 5) -> list[NormalizedSeed]:
        """Full synthesis pipeline for a domain."""
        patterns = self.reference_scan()
        abstracted = self.abstract_seeds(patterns, count=count * 2)
        classified = self.classify_domains(abstracted)
        filtered = self.filter_leakage(classified)
        if len(filtered) < count:
            logger.warning(
                "Synthesis for %s produced %d seeds (expected %d)",
                domain,
                len(filtered),
                count,
            )
        fresh = self.validate_freshness(filtered[:count])
        return fresh
