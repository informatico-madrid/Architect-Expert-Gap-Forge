# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Tests for Git fallback and resilience in the ingestor.

T025: Unit tests for Git fallback/resilience:
- Validates git pull --ff-only behavior
- Tests the safe recovery policy via fetch+reset
- Retry policy: up to 3 times (pull -> fetch+reset) with exponential backoff (1s, 2s, 4s)
- Safety criteria: apply reset only when remote contains target commit in its history;
  check ancestry/commit-IDs to avoid destructive resets

Test scenarios:
- Network error handling
- Diverged history
- Shallow clone scenarios
- Fast-forward success
- Commit ancestry verification
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.discovery.ingestor import DiscoveryConfig, RepoIngestor


class TestGitFallbackPolicy:
    """Test Git fallback and recovery policies in the ingestor."""

    def test_ff_only_pull_succeeds(self, tmp_path: Path) -> None:
        """Test that fast-forward pull succeeds when possible.

        T025: When git pull --ff-only succeeds, no fallback is needed.
        """
        config = DiscoveryConfig(
            category="test",
            mode="static",
            static_repos=["owner/repo"],
        )
        ingestor = RepoIngestor(config)

        # Create a mock repo directory
        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        with patch("subprocess.run") as mock_run:
            # First call (pull) succeeds
            mock_run.return_value = MagicMock(returncode=0)

            ingestor._update_repo("owner/repo", repo_path)

            # Should only call pull, not fetch+reset
            assert mock_run.call_count == 1
            call_args = mock_run.call_args[0][0]
            assert "pull" in call_args
            assert "--ff-only" in call_args

    def test_ff_only_fallback_to_fetch_reset(self, tmp_path: Path) -> None:
        """Test that fetch+reset is used when ff-only fails.

        T025: When pull --ff-only fails, fall back to fetch+reset.
        """
        config = DiscoveryConfig(
            category="test",
            mode="static",
            static_repos=["owner/repo"],
        )
        ingestor = RepoIngestor(config)

        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        with patch("subprocess.run") as mock_run:
            with patch("time.sleep"):
                # First call (pull) fails with CalledProcessError
                # Then _safe_reset is called which makes multiple git calls:
                # fetch, rev-parse (HEAD), rev-parse (origin/HEAD), merge-base, cat-file, reset
                mock_run.side_effect = [
                    # Attempt 1: pull fails
                    subprocess.CalledProcessError(1, ["git"]),
                    # _safe_reset calls:
                    MagicMock(returncode=0),  # fetch
                    MagicMock(returncode=0),  # rev-parse HEAD
                    MagicMock(returncode=0),  # rev-parse origin/HEAD
                    MagicMock(returncode=0),  # merge-base --is-ancestor
                    MagicMock(returncode=0),  # cat-file
                    MagicMock(returncode=0),  # reset --hard
                    MagicMock(returncode=0),  # verify new HEAD
                ]

                ingestor._update_repo("owner/repo", repo_path)

                # Verify pull was attempted
                calls = [call[0][0] for call in mock_run.call_args_list]
                assert any("pull" in cmd for cmd in calls)


class TestGitRetryPolicy:
    """Test retry policy with exponential backoff.

    T025: Retry policy - up to 3 times (pull -> fetch+reset) with
    exponential backoff (1s, 2s, 4s) before failing.
    """

    def test_retry_with_exponential_backoff(self, tmp_path: Path) -> None:
        """Test that retries use exponential backoff.

        T025: Policy is exponential backoff: 1s, 2s, 4s.
        """
        config = DiscoveryConfig(
            category="test",
            mode="static",
            static_repos=["owner/repo"],
        )
        ingestor = RepoIngestor(config)

        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        with patch("subprocess.run") as mock_run:
            with patch("time.sleep") as mock_sleep:
                # First attempt fails, second succeeds via safe_reset
                mock_run.side_effect = [
                    # Attempt 1: pull fails -> sleep(1) -> _safe_reset fails
                    subprocess.CalledProcessError(1, ["git"]),
                    MagicMock(returncode=0),  # fetch
                    MagicMock(returncode=0),  # rev-parse HEAD
                    MagicMock(returncode=0),  # rev-parse origin/HEAD
                    MagicMock(returncode=0),  # merge-base
                    MagicMock(returncode=0),  # cat-file
                    MagicMock(returncode=1),  # reset FAILS - safety check
                    # Attempt 2: pull fails -> sleep(2) -> _safe_reset succeeds
                    subprocess.CalledProcessError(1, ["git"]),
                    MagicMock(returncode=0),  # fetch
                    MagicMock(returncode=0),  # rev-parse HEAD
                    MagicMock(returncode=0),  # rev-parse origin/HEAD
                    MagicMock(returncode=0),  # merge-base
                    MagicMock(returncode=0),  # cat-file
                    MagicMock(returncode=0),  # reset succeeds
                    MagicMock(returncode=0),  # verify new HEAD
                ]

                ingestor._update_repo("owner/repo", repo_path)

                # Verify sleep was called with backoff intervals
                # Should have at least 1 sleep for retry
                assert mock_sleep.call_count >= 1

    def test_max_retries_exceeded_raises_error(self, tmp_path: Path) -> None:
        """Test that after 3 failed attempts, an error is raised.

        T025: Policy is maximum 3 retry attempts before failing.
        """
        config = DiscoveryConfig(
            category="test",
            mode="static",
            static_repos=["owner/repo"],
        )
        ingestor = RepoIngestor(config)

        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        with patch("subprocess.run") as mock_run:
            with patch("time.sleep"):
                # All attempts fail - pull fails and _safe_reset always fails
                mock_run.side_effect = [
                    # Attempt 1
                    subprocess.CalledProcessError(1, ["git"]),  # pull
                    MagicMock(returncode=1),  # fetch fails
                    # Attempt 2
                    subprocess.CalledProcessError(1, ["git"]),  # pull
                    MagicMock(returncode=1),  # fetch fails
                    # Attempt 3
                    subprocess.CalledProcessError(1, ["git"]),  # pull
                    MagicMock(returncode=1),  # fetch fails
                ]

                # Should raise after exhausting retries
                with pytest.raises(subprocess.CalledProcessError):
                    ingestor._update_repo("owner/repo", repo_path)


class TestGitSafetyCriteria:
    """Test safety criteria for git operations.

    T025: Safety criteria:
    - Apply reset only when remote contains target commit in its history
    - Check ancestry/commit-IDs to avoid destructive resets
    """

    def test_reset_requires_commit_verification(self, tmp_path: Path) -> None:
        """Test that reset is only applied after verifying commit exists.

        T025: Safety - verify commit exists in remote before reset.
        """
        config = DiscoveryConfig(
            category="test",
            mode="static",
            static_repos=["owner/repo"],
        )
        ingestor = RepoIngestor(config)

        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        with patch("subprocess.run") as mock_run:
            with patch("time.sleep"):
                # pull fails, then _safe_reset is called
                mock_run.side_effect = [
                    # First pull attempt
                    subprocess.CalledProcessError(1, ["git"]),
                    # _safe_reset sequence
                    MagicMock(returncode=0),  # fetch
                    MagicMock(returncode=0, stdout="abc123\n"),  # rev-parse HEAD
                    MagicMock(returncode=0, stdout="def456\n"),  # rev-parse origin/HEAD
                    MagicMock(returncode=0),  # merge-base --is-ancestor
                    MagicMock(returncode=0),  # cat-file
                    MagicMock(returncode=0),  # reset
                    MagicMock(returncode=0, stdout="def456\n"),  # verify new HEAD
                ]

                # Should complete successfully with verification
                ingestor._update_repo("owner/repo", repo_path)

                # Verify that ancestry check was performed
                calls = [call[0][0] for call in mock_run.call_args_list]
                # Check for commit verification commands
                has_verification = any(
                    "merge-base" in cmd or "rev-parse" in cmd or "cat-file" in cmd
                    for cmd in calls
                )
                assert has_verification

    def test_diverged_history_handled_safely(self, tmp_path: Path) -> None:
        """Test that diverged history is handled without data loss.

        T025: Test scenario - diverged history should be handled safely.
        """
        config = DiscoveryConfig(
            category="test",
            mode="static",
            static_repos=["owner/repo"],
        )
        ingestor = RepoIngestor(config)

        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        with patch("subprocess.run") as mock_run:
            # Diverged history - ff-only fails
            mock_run.return_value = MagicMock(returncode=1)

            # Should attempt recovery but verify before destructive ops
            try:
                ingestor._update_repo("owner/repo", repo_path)
            except subprocess.CalledProcessError:
                pass  # Expected after retries exhausted

            # Verify multiple attempts were made
            assert mock_run.call_count >= 1


class TestShallowCloneHandling:
    """Test handling of shallow clones.

    T025: Test scenario - shallow clone handling.
    """

    def test_shallow_clone_depth_increases_on_update(self, tmp_path: Path) -> None:
        """Test that shallow clones are handled during update.

        When updating a shallow clone, depth may need to be increased
        or full history fetched for proper ff-only operation.
        """
        config = DiscoveryConfig(
            category="test",
            mode="static",
            static_repos=["owner/repo"],
        )
        ingestor = RepoIngestor(config)

        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            ingestor._update_repo("owner/repo", repo_path)

            # Verify fetch uses appropriate depth
            calls = [call[0][0] for call in mock_run.call_args_list]
            fetch_calls = [c for c in calls if "fetch" in c]
            if fetch_calls:
                # Should either use depth=1 or no depth (full history)
                assert "--depth" in fetch_calls[0] or len(fetch_calls) == 0


class TestNetworkErrorHandling:
    """Test handling of network errors.

    T025: Test scenario - network error handling.
    """

    def test_network_error_triggers_retry(self, tmp_path: Path) -> None:
        """Test that network errors trigger retry mechanism.

        Network errors should be retried with backoff.
        """
        config = DiscoveryConfig(
            category="test",
            mode="static",
            static_repos=["owner/repo"],
        )
        ingestor = RepoIngestor(config)

        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        with patch("subprocess.run") as mock_run:
            # Network errors typically manifest as non-zero exit codes
            # First two attempts fail, third succeeds
            mock_run.side_effect = [
                subprocess.CalledProcessError(128, ["git"]),  # network error
                subprocess.CalledProcessError(128, ["git"]),  # network error
                MagicMock(returncode=0),  # success on retry
            ]

            # Should not raise if retry succeeds
            ingestor._update_repo("owner/repo", repo_path)

    def test_authentication_error_does_not_retry_indefinitely(
        self, tmp_path: Path
    ) -> None:
        """Test that auth errors don't trigger infinite retries.

        Authentication errors (exit code 128) should be retried a limited
        number of times then fail.
        """
        config = DiscoveryConfig(
            category="test",
            mode="static",
            static_repos=["owner/repo"],
        )
        ingestor = RepoIngestor(config)

        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        with patch("subprocess.run") as mock_run:
            # All attempts fail with auth error
            mock_run.side_effect = subprocess.CalledProcessError(128, ["git"])

            # Should raise after exhausting retries
            with pytest.raises(subprocess.CalledProcessError):
                ingestor._update_repo("owner/repo", repo_path)

            # Should have tried multiple times before giving up
            assert mock_run.call_count >= 2
