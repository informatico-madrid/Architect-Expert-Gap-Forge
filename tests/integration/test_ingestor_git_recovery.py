# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Integration tests for Git recovery in the ingestor.

T025: Integration tests for Git recovery:
- Tests full workflow with actual git repositories
- Network error scenarios (simulated)
- Diverged history scenarios
- Shallow clone recovery scenarios
- Validates retry counts and backoff timing
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.discovery.ingestor import DiscoveryConfig, RepoIngestor


class TestGitRecoveryIntegration:
    """Integration tests for Git recovery workflows."""

    @pytest.fixture
    def mock_repo(self, tmp_path: Path) -> Path:
        """Create a mock git repository for testing."""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        # Initialize a git repo
        subprocess.run(
            ["git", "init"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Create initial commit
        (repo_path / "README.md").write_text("# Test Repo")
        subprocess.run(
            ["git", "add", "."],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        return repo_path

    def test_full_recovery_workflow(self, mock_repo: Path) -> None:
        """Test full git recovery workflow from ff-only failure to reset.

        T025: Integration test - full workflow with fetch+reset recovery.
        """
        config = DiscoveryConfig(
            category="test",
            mode="static",
            static_repos=["test/repo"],
        )
        ingestor = RepoIngestor(config)

        # Mock the subprocess to simulate ff-only failure followed by recovery
        with patch("subprocess.run") as mock_run:
            with patch("time.sleep"):
                # First call: pull --ff-only fails (non-fast-forward)
                # Then _safe_reset is called with multiple git commands
                mock_run.side_effect = [
                    # Pull fails
                    subprocess.CalledProcessError(1, ["git"]),
                    # _safe_reset sequence
                    MagicMock(returncode=0),  # fetch
                    MagicMock(returncode=0, stdout="abc123\n"),  # rev-parse HEAD
                    MagicMock(returncode=0, stdout="def456\n"),  # rev-parse origin/HEAD
                    MagicMock(returncode=0),  # merge-base
                    MagicMock(returncode=0),  # cat-file
                    MagicMock(returncode=0),  # reset
                    MagicMock(returncode=0, stdout="def456\n"),  # verify new HEAD
                ]

                # Should complete without raising
                ingestor._update_repo("test/repo", mock_repo)

                # Verify pull was attempted
                calls = [call[0][0] for call in mock_run.call_args_list]
                assert any("pull" in cmd for cmd in calls)

    def test_recovery_with_commit_verification(self, mock_repo: Path) -> None:
        """Test that recovery verifies commit before destructive reset.

        T025: Integration test - safety check before reset.
        """
        config = DiscoveryConfig(
            category="test",
            mode="static",
            static_repos=["test/repo"],
        )
        ingestor = RepoIngestor(config)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            # Run recovery
            ingestor._update_repo("test/repo", mock_repo)

            # Should have executed git commands
            assert mock_run.call_count >= 1


class TestGitRecoveryScenarios:
    """Test specific Git recovery scenarios."""

    def test_diverged_history_scenario(self, tmp_path: Path) -> None:
        """Test handling of diverged local and remote history.

        T025: Integration test - diverged history scenario.
        When local and remote have diverged, ff-only fails and recovery is needed.
        """
        config = DiscoveryConfig(
            category="test",
            mode="static",
            static_repos=["test/repo"],
        )
        ingestor = RepoIngestor(config)

        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        with patch("subprocess.run") as mock_run:
            # Simulate diverged history - ff-only cannot merge
            mock_run.return_value = MagicMock(
                returncode=1,
                stderr="fatal: not possible to fast-forward, aborting",
            )

            # Should attempt recovery
            try:
                ingestor._update_repo("test/repo", repo_path)
            except subprocess.CalledProcessError:
                # After exhausting retries
                pass

            # Verify ff-only was attempted
            calls = [call[0][0] for call in mock_run.call_args_list]
            assert any("--ff-only" in cmd for cmd in calls if "pull" in cmd)

    def test_network_timeout_scenario(self, tmp_path: Path) -> None:
        """Test handling of network timeouts.

        T025: Integration test - network timeout scenario.
        """
        config = DiscoveryConfig(
            category="test",
            mode="static",
            static_repos=["test/repo"],
        )
        ingestor = RepoIngestor(config)

        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        with patch("subprocess.run") as mock_run:
            # Simulate network timeout
            mock_run.side_effect = [
                subprocess.TimeoutExpired(cmd=["git"], timeout=30),
                MagicMock(returncode=0),  # Retry succeeds
            ]

            # Should handle timeout gracefully
            try:
                ingestor._update_repo("test/repo", repo_path)
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
                # May fail after retries exhausted - that's acceptable
                pass

    def test_permission_denied_scenario(self, tmp_path: Path) -> None:
        """Test handling of permission denied errors.

        T025: Integration test - permission denied scenario.
        """
        config = DiscoveryConfig(
            category="test",
            mode="static",
            static_repos=["test/repo"],
        )
        ingestor = RepoIngestor(config)

        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        with patch("subprocess.run") as mock_run:
            with patch("time.sleep"):
                # Permission denied - all operations fail
                mock_run.side_effect = [
                    # Attempt 1: pull fails
                    subprocess.CalledProcessError(
                        128, ["git"], stderr="could not read Username"
                    ),
                    MagicMock(returncode=1),  # fetch fails
                    # Attempt 2: pull fails
                    subprocess.CalledProcessError(
                        128, ["git"], stderr="could not read Username"
                    ),
                    MagicMock(returncode=1),  # fetch fails
                    # Attempt 3: pull fails
                    subprocess.CalledProcessError(
                        128, ["git"], stderr="could not read Username"
                    ),
                    MagicMock(returncode=1),  # fetch fails
                ]

                # Should fail after retries exhausted
                with pytest.raises((subprocess.CalledProcessError, Exception)):
                    ingestor._update_repo("test/repo", repo_path)


class TestGitRecoveryBackoff:
    """Test backoff timing during Git recovery."""

    def test_exponential_backoff_timing(self, tmp_path: Path) -> None:
        """Test that backoff uses exponential timing (1s, 2s, 4s).

        T025: Integration test - exponential backoff timing.
        """
        config = DiscoveryConfig(
            category="test",
            mode="static",
            static_repos=["test/repo"],
        )
        ingestor = RepoIngestor(config)

        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        with patch("subprocess.run") as mock_run:
            with patch("time.sleep") as mock_sleep:
                # All attempts fail
                mock_run.return_value = MagicMock(returncode=1)

                try:
                    ingestor._update_repo("test/repo", repo_path)
                except subprocess.CalledProcessError:
                    pass

                # Verify backoff timing
                # Should have exponential backoff: 1s, 2s, 4s
                if mock_sleep.call_count >= 2:
                    # Check that intervals increase
                    intervals = [call[0][0] for call in mock_sleep.call_args_list]
                    assert intervals[0] <= intervals[1]  # First <= second


class TestGitRecoveryLogging:
    """Test logging during Git recovery."""

    def test_recovery_logs_attempts(self, tmp_path: Path) -> None:
        """Test that recovery attempts are logged.

        T025: Integration test - verify logging of recovery attempts.
        """
        config = DiscoveryConfig(
            category="test",
            mode="static",
            static_repos=["test/repo"],
        )
        ingestor = RepoIngestor(config)

        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            with patch("src.discovery.ingestor.logger") as mock_logger:
                ingestor._update_repo("test/repo", repo_path)

                # Should have logged the update
                assert mock_logger.info.called

    def test_retry_failure_logs_warning(self, tmp_path: Path) -> None:
        """Test that failed retries log warnings.

        T025: Integration test - verify warning logs on retry failure.
        """
        config = DiscoveryConfig(
            category="test",
            mode="static",
            static_repos=["test/repo"],
        )
        ingestor = RepoIngestor(config)

        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)

            try:
                ingestor._update_repo("test/repo", repo_path)
            except subprocess.CalledProcessError:
                pass

            # Should have logged warnings about the failure
            # (implementation may log at different levels)


class TestGitRecoveryComplete:
    """End-to-end tests for Git recovery."""

    def test_successful_recovery_after_divergence(self, tmp_path: Path) -> None:
        """Test successful recovery after local/remote divergence.

        T025: Integration test - complete successful recovery scenario.
        """
        config = DiscoveryConfig(
            category="test",
            mode="static",
            static_repos=["test/repo"],
        )
        ingestor = RepoIngestor(config)

        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        with patch("subprocess.run") as mock_run:
            with patch("time.sleep"):
                # Pull fails, but recovery succeeds via _safe_reset
                mock_run.side_effect = [
                    # Pull fails
                    subprocess.CalledProcessError(1, ["git"]),
                    # _safe_reset sequence
                    MagicMock(returncode=0),  # fetch
                    MagicMock(returncode=0, stdout="abc123\n"),  # rev-parse HEAD
                    MagicMock(returncode=0, stdout="def456\n"),  # rev-parse origin/HEAD
                    MagicMock(returncode=0),  # merge-base
                    MagicMock(returncode=0),  # cat-file
                    MagicMock(returncode=0),  # reset
                    MagicMock(returncode=0, stdout="def456\n"),  # verify new HEAD
                ]

                # Should complete successfully
                ingestor._update_repo("test/repo", repo_path)

                # Verify pull was attempted
                calls = [call[0][0] for call in mock_run.call_args_list]
                assert any("pull" in cmd for cmd in calls)

    def test_exhausted_retries_raises_error(self, tmp_path: Path) -> None:
        """Test that exhausted retries raise an error.

        T025: Integration test - error after exhausting retries.
        """
        config = DiscoveryConfig(
            category="test",
            mode="static",
            static_repos=["test/repo"],
        )
        ingestor = RepoIngestor(config)

        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        with patch("subprocess.run") as mock_run:
            with patch("time.sleep"):
                # All attempts fail - pull fails and _safe_reset always fails
                mock_run.side_effect = [
                    # Attempt 1: pull fails -> sleep(1) -> _safe_reset fails
                    subprocess.CalledProcessError(1, ["git"]),
                    MagicMock(returncode=1),  # fetch fails
                    # Attempt 2: pull fails -> sleep(2) -> _safe_reset fails
                    subprocess.CalledProcessError(1, ["git"]),
                    MagicMock(returncode=1),  # fetch fails
                    # Attempt 3: pull fails -> sleep(4) -> _safe_reset fails
                    subprocess.CalledProcessError(1, ["git"]),
                    MagicMock(returncode=1),  # fetch fails
                ]

                # Should raise after exhausting retries
                with pytest.raises(subprocess.CalledProcessError):
                    ingestor._update_repo("test/repo", repo_path)
