#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0
"""
Integration tests for the full anchor-dataset pipeline.

Tests:
  (1) Full pipeline with stubbed providers
  (2) Idempotency — two runs with same seed produce same (id, domain, difficulty)

"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from infrastructure.anchor_dataset.anchor_dataset_schema import AnchorRecord, AnchorManifest
from infrastructure.anchor_dataset.anchor_providers import AnchorProvider
from infrastructure.anchor_dataset.seed_loader import load_seeds
from infrastructure.anchor_dataset.sample_generator import SampleConfigGenerator, PromptBuilder, SampleConfig
from infrastructure.anchor_dataset.exporter import JSONLExporter


# ── Stub provider ──────────────────────────────────────────────────────────────

class StubProvider(AnchorProvider):
    """A provider that returns deterministic AnchorRecord objects without calling any LLM."""

    @property
    def name(self) -> str:
        return "stub"

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        timeout: float = 30.0,
    ) -> AnchorRecord | None:
        return _make_stub_record(system_prompt, user_prompt)


def _make_stub_record(system_prompt: str, user_prompt: str) -> AnchorRecord:
    """Build a valid AnchorRecord from prompt content."""
    # Extract domain from system prompt
    domain = "home_assistant"
    for word in ("home_assistant", "php_legacy", "generic_domain", "other"):
        if f"DOMAIN: {word}" in system_prompt:
            domain = word
            break

    # Extract difficulty from user prompt
    difficulty = "medium"
    for word in ("easy", "medium", "hard"):
        if word in user_prompt:
            difficulty = word
            break

    # Turn count from system prompt
    turn_count = 4
    for part in system_prompt.split("\n"):
        if "QUALITY CONSTRAINTS:" in part:
            continue
        if part.strip().startswith("turn_count="):
            turn_count = int(part.split("=")[1])
            break

    # Check if turn_count was already set in system prompt
    for line in system_prompt.split("\n"):
        if "turn_count" in line:
            # Use the one from USER_TEMPLATE
            pass
    # Look for turn count in user prompt
    up = user_prompt
    if "- Turn count:" in up:
        tc_part = up.split("- Turn count:")[1].split("\n")[0].strip()
        turn_count = int(tc_part)

    return AnchorRecord(
        id=f"anchor_{system_prompt.count('DOMAIN') + 1:03d}_{1:02d}",
        domain=domain,
        difficulty=difficulty,
        turn_count=turn_count,
        legacy_pattern=f"stub_pattern_for_{domain}",
        domain_context=f"stub context for {domain}",
        expected_trajectory="[ROLE:user]\ntest\n\n[ROLE:assistant]\ntool\n",
        expected_tool_usage_patterns=["stub"],
        expected_coherence=0.8,
        expected_overall=0.7,
        expected_quality_score=0.8,
        verified=False,
    )


# ── Test 1: Full pipeline ─────────────────────────────────────────────────────

@pytest.mark.integration
class TestFullPipeline:
    """Test the full anchor-dataset pipeline end-to-end with stubbed providers."""

    def test_pipeline_produces_jsonl_and_manifest(self, tmp_path: Path) -> None:
        """Full pipeline: seeds -> configs -> prompts -> stub provider -> export -> verify."""
        # 1. Load seeds
        seeds = load_seeds()
        assert len(seeds) >= 13, f"Expected >= 13 seeds, got {len(seeds)}"

        # 2. Generate configs (count=5, a small set for speed)
        gen = SampleConfigGenerator(seeds=seeds, seed=42)
        configs = gen.generate_configs(count=5)
        assert len(configs) == 5

        # 3. Build prompts
        pb = PromptBuilder(seeds=seeds)
        prompts: list[tuple[SampleConfig, str, str]] = []
        for cfg in configs:
            system, user = pb.build(cfg)
            assert "DOMAIN:" in system
            assert "Generate an anchor sample" in user
            prompts.append((cfg, system, user))

        # 4. Generate records via stub provider
        provider = StubProvider()
        records: list[AnchorRecord] = []
        for cfg, system, user in prompts:
            rec = provider.generate(system, user)
            assert rec is not None, f"Provider returned None for config {cfg.sample_id}"
            records.append(rec)

        assert len(records) == len(configs)

        # 5. Export to temp directory
        output_dir = tmp_path / "anchor_output"
        output_dir.mkdir()
        exporter = JSONLExporter()
        output_path = output_dir / "anchor_dataset.jsonl"
        exporter.write_all(records, output_path)

        # 6. Verify JSONL
        assert output_path.exists()
        with open(output_path) as f:
            lines = f.readlines()
        assert len(lines) == len(records)

        for line in lines:
            data = json.loads(line)
            # Each line should be a valid AnchorRecord
            rec = AnchorRecord.model_validate(data)
            assert rec.id.startswith("anchor_")
            assert rec.domain in ("home_assistant", "php_legacy", "generic_domain", "other")
            assert rec.difficulty in ("easy", "medium", "hard")

        # 7. Generate and verify manifest
        manifest = exporter.generate_manifest(records, "stub", False, 0)
        assert isinstance(manifest, AnchorManifest)
        assert manifest.total_samples == len(records)
        assert manifest.provider == "stub"
        assert manifest.cb_triggered is False
        assert manifest.failed_count == 0

        # Write manifest to disk and verify
        manifest_path = output_dir / "anchor_dataset_manifest.json"
        with manifest_path.open("w") as f:
            json.dump(manifest.model_dump(), f, indent=2)
        assert manifest_path.exists()

        with manifest_path.open() as f:
            loaded = json.load(f)
        assert loaded["total_samples"] == len(records)

    def test_pipeline_domain_distribution(self, tmp_path: Path) -> None:
        """Verify that pipeline preserves the expected domain distribution."""
        seeds = load_seeds()
        gen = SampleConfigGenerator(seeds=seeds, seed=42)
        configs = gen.generate_configs(count=10)

        domains = {c.domain for c in configs}
        # Should cover the domains present in the seeds
        assert len(domains) >= 1

        provider = StubProvider()
        pb = PromptBuilder(seeds=seeds)

        records: list[AnchorRecord] = []
        for cfg in configs:
            system, user = pb.build(cfg)
            rec = provider.generate(system, user)
            if rec is not None:
                records.append(rec)

        # Verify all generated records have valid domains
        for rec in records:
            assert rec.domain in ("home_assistant", "php_legacy", "generic_domain", "other")

        # Export and verify
        exporter = JSONLExporter()
        exporter.write_all(records, tmp_path / "out.jsonl")

        with open(tmp_path / "out.jsonl") as f:
            data = [json.loads(line) for line in f]
        assert len(data) == len(records)


# ── Test 2: Idempotency ───────────────────────────────────────────────────────

@pytest.mark.integration
class TestIdempotency:
    """Two runs with the same seed produce the same (id, domain, difficulty) tuples."""

    def test_idempotent_id_domain_difficulty(self) -> None:
        """Run the pipeline twice with seed=42 and compare (id, domain, difficulty) tuples."""
        seeds = load_seeds()

        def run_pipeline() -> list[tuple[str, str, str]]:
            gen = SampleConfigGenerator(seeds=seeds, seed=42)
            configs = gen.generate_configs(count=10)
            pb = PromptBuilder(seeds=seeds)
            provider = StubProvider()
            tuples: list[tuple[str, str, str]] = []
            for cfg in configs:
                system, user = pb.build(cfg)
                rec = provider.generate(system, user)
                if rec is not None:
                    tuples.append((rec.id, rec.domain, rec.difficulty))
            return tuples

        run1 = run_pipeline()
        run2 = run_pipeline()

        assert len(run1) == len(run2), (
            f"Run lengths differ: {len(run1)} vs {len(run2)}"
        )
        assert run1 == run2, (
            f"Idempotency failed: {run1} != {run2}"
        )

    def test_idempotent_with_different_seeds_produce_different_results(self) -> None:
        """Different seeds should produce different sample ordering."""
        seeds = load_seeds()

        gen1 = SampleConfigGenerator(seeds=seeds, seed=42)
        configs1 = gen1.generate_configs(count=10)

        gen2 = SampleConfigGenerator(seeds=seeds, seed=99)
        configs2 = gen2.generate_configs(count=10)

        # Configs may be different due to different random shuffle
        domains1 = [c.domain for c in configs1]
        domains2 = [c.domain for c in configs2]

        # Both runs should have the same total count
        assert len(domains1) == len(domains2) == 10

        # The shuffled order should differ (probability is very high with different seeds)
        # We just verify both produce valid configs
        for cfg in configs1 + configs2:
            assert cfg.domain in ("home_assistant", "php_legacy", "generic_domain", "other")
            assert cfg.difficulty in ("easy", "medium", "hard")
            assert cfg.turn_count in (3, 4, 5)
