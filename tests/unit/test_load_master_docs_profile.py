# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for load_master_docs with profile support.

These tests verify that load_master_docs correctly:
1. Accepts a profile parameter
2. Reads from master_docs_map.yaml for profile-specific document names
3. Falls back to defaults when profile is not in the map
4. Raises FileNotFoundError when required documents are missing
"""

from __future__ import annotations

from pathlib import Path
import pytest
import yaml

from src.factory.prompt_builder import load_master_docs


class TestLoadMasterDocsWithProfile:
    """Tests for load_master_docs with profile parameter."""

    @pytest.fixture
    def gap_dir_with_docs(self, tmp_path: Path) -> Path:
        """Create a gap directory with default master documents."""
        (tmp_path / "HA_MASTER_GUIDE_2026.md").write_text("# Master Guide")
        (tmp_path / "technical_changelog_2026.md").write_text("# Changelog")
        (tmp_path / "HA_JINJA_YAML_GUIDE_2026.md").write_text("# Jinja Guide")
        return tmp_path

    @pytest.fixture
    def gap_dir_with_profile_docs(self, tmp_path: Path) -> Path:
        """Create a gap directory with profile-specific master documents."""
        (tmp_path / "PHP_HEXAGONAL_GUIDE_2026.md").write_text("# PHP Guide")
        (tmp_path / "php_changelog_2026.md").write_text("# PHP Changelog")
        (tmp_path / "PHP_TEMPLATE_GUIDE_2026.md").write_text("# PHP Template Guide")
        return tmp_path

    def test_load_master_docs_default_profile(self, gap_dir_with_docs: Path) -> None:
        """Test load_master_docs with default homeassistant profile."""
        master, changelog, jinja = load_master_docs(gap_dir_with_docs)

        assert master == "# Master Guide"
        assert changelog == "# Changelog"
        assert jinja == "# Jinja Guide"

    def test_load_master_docs_explicit_profile(self, gap_dir_with_docs: Path) -> None:
        """Test load_master_docs with explicit homeassistant profile."""
        master, changelog, jinja = load_master_docs(
            gap_dir_with_docs, profile="homeassistant"
        )

        assert master == "# Master Guide"
        assert changelog == "# Changelog"
        assert jinja == "# Jinja Guide"

    def test_load_master_docs_missing_file_raises(self, tmp_path: Path) -> None:
        """Test load_master_docs raises FileNotFoundError when file is missing."""
        (tmp_path / "HA_MASTER_GUIDE_2026.md").write_text("# Master Guide")
        # Missing changelog and jinja

        with pytest.raises(FileNotFoundError) as exc_info:
            load_master_docs(tmp_path)

        assert "Technical Changelog" in str(exc_info.value)

    def test_load_master_docs_with_config_file(
        self, gap_dir_with_profile_docs: Path, tmp_path: Path
    ) -> None:
        """Test load_master_docs uses config file for profile-specific docs."""
        # Create config directory and file
        config_dir = tmp_path / "configs" / "stage_1_discovery"
        config_dir.mkdir(parents=True)

        config = {
            "profiles": {
                "php_hexagonal": {
                    "master_guide": "PHP_HEXAGONAL_GUIDE_2026.md",
                    "changelog": "php_changelog_2026.md",
                    "jinja_guide": "PHP_TEMPLATE_GUIDE_2026.md",
                }
            }
        }

        (config_dir / "master_docs_map.yaml").write_text(yaml.dump(config))

        # Monkeypatch the config path to use our test config
        import src.factory.prompt_builder as pb_module

        original_config_path = pb_module._MASTER_DOCS_MAP_FILE
        pb_module._MASTER_DOCS_MAP_FILE = str(config_dir / "master_docs_map.yaml")

        try:
            master, changelog, jinja = load_master_docs(
                gap_dir_with_profile_docs, profile="php_hexagonal"
            )

            assert master == "# PHP Guide"
            assert changelog == "# PHP Changelog"
            assert jinja == "# PHP Template Guide"
        finally:
            pb_module._MASTER_DOCS_MAP_FILE = original_config_path

    def test_load_master_docs_unknown_profile_fallback(
        self, gap_dir_with_docs: Path
    ) -> None:
        """Test load_master_docs falls back to defaults for unknown profile."""
        # Without config file, unknown profile should use defaults
        master, changelog, jinja = load_master_docs(
            gap_dir_with_docs, profile="unknown_profile"
        )

        # Should still load the default HA documents
        assert master == "# Master Guide"
        assert changelog == "# Changelog"
        assert jinja == "# Jinja Guide"
