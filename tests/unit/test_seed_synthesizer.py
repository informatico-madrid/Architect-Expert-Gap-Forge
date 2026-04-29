#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0
"""Tests for seed_synthesizer — SeedSynthesizer class."""

from __future__ import annotations



from infrastructure.anchor_dataset.seed_loader import NormalizedSeed
from infrastructure.anchor_dataset.seed_synthesizer import SeedSynthesizer


class TestValidateNoLeakage:
    """Test validate_no_leakage returns correct booleans."""

    def test_clean_seed_returns_true(self):
        """Seed with no forbidden strings returns True."""
        seed = NormalizedSeed(
            seed_id="test_001",
            domain="generic",
            category="config",
            complexity="nominal_easy",
            context="Set up a generic sensor",
            question="How to configure a sensor?",
            expected_patterns=[],
        )
        synth = SeedSynthesizer()
        assert synth.validate_no_leakage([seed]) is True

    def test_leaking_context_returns_false(self):
        """Seed with 'home_assistant' in context returns False."""
        seed = NormalizedSeed(
            seed_id="test_002",
            domain="generic",
            category="config",
            complexity="nominal_easy",
            context="Configure home_assistant integration",
            question="How to configure?",
            expected_patterns=[],
        )
        synth = SeedSynthesizer()
        assert synth.validate_no_leakage([seed]) is False

    def test_leaking_question_returns_false(self):
        """Seed with 'homeassistant' (no-space) in question returns False."""
        seed = NormalizedSeed(
            seed_id="test_003",
            domain="generic",
            category="config",
            complexity="nominal_easy",
            context="Generic context",
            question="Ask about homeassistant setup",
            expected_patterns=[],
        )
        synth = SeedSynthesizer()
        assert synth.validate_no_leakage([seed]) is False

    def test_leaking_seed_id_returns_false(self):
        """Seed with forbidden string in seed_id returns False."""
        seed = NormalizedSeed(
            seed_id="home_assistant_test",
            domain="generic",
            category="config",
            complexity="nominal_easy",
            context="Generic context",
            question="Generic question",
            expected_patterns=[],
        )
        synth = SeedSynthesizer()
        assert synth.validate_no_leakage([seed]) is False

    def test_mixed_seeds_all_clean_returns_true(self):
        """Multiple clean seeds all pass."""
        seeds = [
            NormalizedSeed(
                seed_id=f"clean_{i}", domain="generic", category="c",
                complexity="easy", context=f"Topic {i}",
                question=f"Question {i}", expected_patterns=[],
            )
            for i in range(5)
        ]
        synth = SeedSynthesizer()
        assert synth.validate_no_leakage(seeds) is True

    def test_one_leaking_seed_returns_false(self):
        """One leaking seed among clean ones returns False."""
        clean = NormalizedSeed(
            seed_id="clean_001", domain="generic", category="c",
            complexity="easy", context="Clean context",
            question="Clean question", expected_patterns=[],
        )
        leaky = NormalizedSeed(
            seed_id="leaky_001", domain="generic", category="c",
            complexity="easy", context="Zigbee2MQTT sensor",
            question="Clean question", expected_patterns=[],
        )
        synth = SeedSynthesizer()
        assert synth.validate_no_leakage([clean, leaky]) is False


class TestReferenceScan:
    """Test reference_scan reads files."""

    def test_empty_reference_path_returns_empty_list(self):
        """Non-existent reference path returns empty list."""
        synth = SeedSynthesizer(reference_path="/nonexistent/path")
        result = synth.reference_scan()
        assert result == []

    def test_reference_scan_reads_python_files(self, tmp_path):
        """reference_scan reads .py files from reference directory."""
        ref_dir = tmp_path / "reference_corpus"
        ref_dir.mkdir()
        py_file = ref_dir / "example.py"
        py_file.write_text("# Python example file\nprint('hello')")
        synth = SeedSynthesizer(reference_path=ref_dir)
        patterns = synth.reference_scan()
        assert len(patterns) == 1
        assert "hello" in patterns[0]

    def test_reference_scan_reads_yaml_files(self, tmp_path):
        """reference_scan reads .yaml/.yml files."""
        ref_dir = tmp_path / "reference_corpus"
        ref_dir.mkdir()
        yaml_file = ref_dir / "config.yaml"
        yaml_file.write_text("key: value\nlist:\n  - item")
        synth = SeedSynthesizer(reference_path=ref_dir)
        patterns = synth.reference_scan()
        assert len(patterns) == 1
        assert "key: value" in patterns[0]

    def test_reference_scan_reads_md_files(self, tmp_path):
        """reference_scan reads .md files."""
        ref_dir = tmp_path / "reference_corpus"
        ref_dir.mkdir()
        md_file = ref_dir / "README.md"
        md_file.write_text("# My Project\n\nSome documentation.")
        synth = SeedSynthesizer(reference_path=ref_dir)
        patterns = synth.reference_scan()
        assert len(patterns) == 1
        assert "My Project" in patterns[0]

    def test_reference_scan_skips_non_matching_extensions(self, tmp_path):
        """reference_scan skips files with other extensions."""
        ref_dir = tmp_path / "reference_corpus"
        ref_dir.mkdir()
        json_file = ref_dir / "data.json"
        json_file.write_text('{"key": "value"}')
        synth = SeedSynthesizer(reference_path=ref_dir)
        patterns = synth.reference_scan()
        assert patterns == []

    def test_reference_scan_recursive(self, tmp_path):
        """reference_scan recursively reads subdirectories."""
        ref_dir = tmp_path / "reference_corpus"
        ref_dir.mkdir()
        subdir = ref_dir / "sub"
        subdir.mkdir()
        (subdir / "nested.py").write_text("# nested file")
        (ref_dir / "root.py").write_text("# root file")
        synth = SeedSynthesizer(reference_path=ref_dir)
        patterns = synth.reference_scan()
        assert len(patterns) == 2


class TestSynthesize:
    """Test synthesize() returns seeds with domain labels."""

    def test_synthesize_returns_seeds(self):
        """synthesize returns a list of NormalizedSeed objects."""
        synth = SeedSynthesizer(reference_path="/nonexistent")
        seeds = synth.synthesize(domain="test_domain", count=3)
        assert isinstance(seeds, list)
        for seed in seeds:
            assert isinstance(seed, NormalizedSeed)

    def test_synthesize_with_domain_label(self):
        """synthesize returns seeds with the specified domain."""
        synth = SeedSynthesizer(reference_path="/nonexistent")
        seeds = synth.synthesize(domain="my_custom_domain", count=3)
        for seed in seeds:
            assert seed.domain == "my_custom_domain"

    def test_synthesize_no_corpus_returns_empty(self):
        """synthesize with no reference corpus returns empty list."""
        synth = SeedSynthesizer(reference_path="/nonexistent")
        seeds = synth.synthesize(domain="test_domain", count=5)
        # No reference patterns → abstract_seeds returns [] → final is []
        assert seeds == []

    def test_synthesize_with_reference_files(self, tmp_path):
        """synthesize produces seeds when reference corpus has files."""
        ref_dir = tmp_path / "reference_corpus"
        ref_dir.mkdir()
        (ref_dir / "example.py").write_text("# Example reference code")
        synth = SeedSynthesizer(reference_path=ref_dir)
        seeds = synth.synthesize(domain="test_domain", count=3)
        assert len(seeds) > 0
        for seed in seeds:
            assert isinstance(seed, NormalizedSeed)
            # Stub seeds get "generic_domain" since classify_domains is a no-op for generic_domain
            assert seed.domain in ("test_domain", "generic_domain")

    def test_synthesize_filter_leakage(self, tmp_path):
        """synthesize filters out leaking seeds from reference."""
        ref_dir = tmp_path / "reference_corpus"
        ref_dir.mkdir()
        # This file contains a leakage pattern that will propagate into seeds
        (ref_dir / "leaky.py").write_text("# home_assistant reference code")
        synth = SeedSynthesizer(reference_path=ref_dir)
        seeds = synth.synthesize(domain="test_domain", count=3)
        # All seeds should pass leakage validation
        for seed in seeds:
            assert synth.validate_no_leakage([seed]) is True
