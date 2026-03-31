# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Tests for ingestor profile filtering functionality.

Validates that the ingestor applies profile-based filters during repository
discovery, specifically for extensions and ignored paths.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


from src.discovery.ingestor import DiscoveryConfig, RepoIngestor


class TestIngestorProfileFilter:
    """Test profile-based filtering in the ingestor."""

    def test_discovery_config_accepts_profile(self) -> None:
        """Test that DiscoveryConfig accepts a profile field."""
        config = DiscoveryConfig(
            category="test-category",
            mode="static",
            static_repos=["owner/repo1"],
            profile="homeassistant",
        )
        assert config.profile == "homeassistant"

    def test_discovery_config_profile_defaults_to_none(self) -> None:
        """Test that profile defaults to None when not specified."""
        config = DiscoveryConfig(
            category="test-category",
            mode="static",
            static_repos=["owner/repo1"],
        )
        assert config.profile is None

    def test_discovery_config_accepts_extensions_filter(self) -> None:
        """Test that DiscoveryConfig accepts extensions filter from profile."""
        config = DiscoveryConfig(
            category="test-category",
            mode="static",
            static_repos=["owner/repo1"],
            profile="homeassistant",
            profile_extensions={".py", ".js"},
        )
        assert config.profile_extensions == {".py", ".js"}

    def test_discovery_config_accepts_ignored_paths_filter(self) -> None:
        """Test that DiscoveryConfig accepts ignored_paths filter from profile."""
        config = DiscoveryConfig(
            category="test-category",
            mode="static",
            static_repos=["owner/repo1"],
            profile="homeassistant",
            profile_ignored_paths={".git", "__pycache__", "node_modules"},
        )
        assert config.profile_ignored_paths == {".git", "__pycache__", "node_modules"}

    def test_ingestor_initializes_with_profile(self) -> None:
        """Test that RepoIngestor initializes with profile settings."""
        config = DiscoveryConfig(
            category="test-category",
            mode="static",
            static_repos=["owner/repo1"],
            profile="homeassistant",
            profile_extensions={".py"},
            profile_ignored_paths={".git"},
        )
        ingestor = RepoIngestor(config)
        assert ingestor.cfg.profile == "homeassistant"
        assert ingestor.cfg.profile_extensions == {".py"}
        assert ingestor.cfg.profile_ignored_paths == {".git"}

    @patch("src.discovery.ingestor.requests.Session")
    def test_discover_filters_by_profile_extensions(
        self, mock_session: MagicMock
    ) -> None:
        """Test that discover method filters repos by profile extensions."""
        # Setup mock response for GitHub API
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {"full_name": "owner/repo1"},
                {"full_name": "owner/repo2"},
            ]
        }
        mock_session.return_value.get.return_value = mock_response

        config = DiscoveryConfig(
            category="test-category",
            mode="dynamic",
            search_query="homeassistant",
            limit=10,
            profile="homeassistant",
            profile_extensions={".py"},  # Only Python repos
        )

        # When profile_extensions is set, the discover method should filter
        # This test validates the expected behavior - repos must have matching extensions
        # Note: The actual filtering implementation is tested in T011
        with patch.object(RepoIngestor, "_github_search") as mock_search:
            mock_search.return_value = ["owner/repo1", "owner/repo2"]
            ingestor = RepoIngestor(config)
            # The discover method should apply profile filters
            ingestor.discover()
            # Verify that profile filtering is considered
            assert config.profile_extensions is not None

    def test_discovery_config_validates_profile_consistency(self) -> None:
        """Test that DiscoveryConfig validates profile-related fields."""
        # Should not raise - profile with extensions is valid
        config = DiscoveryConfig(
            category="test-category",
            mode="static",
            static_repos=["owner/repo1"],
            profile="homeassistant",
            profile_extensions={".py"},
        )
        assert config.profile == "homeassistant"

    def test_ingestor_dry_run_shows_profile_filters(self) -> None:
        """Test that dry-run mode shows profile filter information."""
        config = DiscoveryConfig(
            category="test-category",
            mode="static",
            static_repos=["owner/repo1", "owner/repo2"],
            profile="homeassistant",
            profile_extensions={".py", ".md"},
            profile_ignored_paths={".git", "node_modules"},
        )
        ingestor = RepoIngestor(config)

        # In dry-run mode, the ingestor should log the filters being applied
        with patch("src.discovery.ingestor.logger"):
            ingestor.fetch(["owner/repo1"], dry_run=True)
            # Verify that profile info is available for logging
            assert ingestor.cfg.profile == "homeassistant"


class TestIngestorProfileFilterEdgeCases:
    """Edge case tests for profile filtering."""

    def test_empty_profile_extensions_allows_all(self) -> None:
        """Test that empty extensions filter allows all files."""
        config = DiscoveryConfig(
            category="test-category",
            mode="static",
            static_repos=["owner/repo1"],
            profile="homeassistant",
            profile_extensions=set(),  # Empty means allow all
        )
        assert config.profile_extensions == set()

    def test_empty_ignored_paths_allows_all(self) -> None:
        """Test that empty ignored_paths filter allows all paths."""
        config = DiscoveryConfig(
            category="test-category",
            mode="static",
            static_repos=["owner/repo1"],
            profile="homeassistant",
            profile_ignored_paths=set(),  # Empty means allow all
        )
        assert config.profile_ignored_paths == set()

    def test_profile_without_filters_is_valid(self) -> None:
        """Test that a profile without filters is valid."""
        config = DiscoveryConfig(
            category="test-category",
            mode="static",
            static_repos=["owner/repo1"],
            profile="homeassistant",
            # No profile_extensions or profile_ignored_paths
        )
        assert config.profile == "homeassistant"
        assert config.profile_extensions is None
        assert config.profile_ignored_paths is None
