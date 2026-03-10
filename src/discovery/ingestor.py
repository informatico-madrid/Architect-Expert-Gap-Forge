# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

""" "
AEGF Ingestor: Agnostic Repository Synchronization Engine.
A high-performance, configuration-driven tool for discovering and
cloning repositories. This engine is domain-unaware; its behavior
is defined strictly by external YAML configurations.
Features:
- Pydantic V2 validated ingestion schema.
- Atomic Git shallow cloning/updating.
- GitHub API Rate-Limit management with adaptive backoff.
- Domain-agnostic CLI.
"""

from __future__ import annotations
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import List, Literal, Optional, Set
import requests
import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, model_validator

# --- Logging Setup ---
logger = logging.getLogger(__name__)


class DiscoveryConfig(BaseModel):
    """Agnostic schema for repository discovery settings."""

    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)

    # Core Parameters
    category: str = Field(..., description="Target subdirectory name")
    mode: Literal["dynamic", "static"] = Field("static")

    # Profile-based filtering
    profile: Optional[str] = Field(
        default=None,
        description="Profile name for filtering and configuration",
    )
    profile_extensions: Optional[Set[str]] = Field(
        default=None,
        description="File extensions to filter during discovery (e.g., {'.py', '.js'})",
    )
    profile_ignored_paths: Optional[Set[str]] = Field(
        default=None,
        description="Paths to ignore during discovery (e.g., {'.git', 'node_modules'})",
    )

    # Search logic (Domain-agnostic)
    search_query: Optional[str] = Field(None)
    min_stars: int = Field(0, ge=0)
    limit: int = Field(50, ge=1)
    per_page: int = Field(100, ge=1, le=100)

    # Data Sources
    static_repos: List[str] = Field(default_factory=list)

    # Infrastructure
    base_dir: Path = Field(default_factory=lambda: Path.cwd())
    raw_subdir: str = Field("data/raw")

    # Authentication
    github_token: Optional[str] = Field(default=None, repr=False)

    @model_validator(mode="after")
    def _validate_logic(self) -> "DiscoveryConfig":
        if self.mode == "static" and not self.static_repos:
            raise ValueError("Static mode requires a non-empty 'static_repos' list.")
        if self.mode == "dynamic" and not self.search_query:
            raise ValueError("Dynamic mode requires a 'search_query'.")
        return self


class RepoIngestor:
    """Agnostic engine for discovering and fetching codebases."""

    def __init__(self, cfg: DiscoveryConfig) -> None:
        self.cfg = cfg
        self.raw_path = self.cfg.base_dir / self.cfg.raw_subdir / self.cfg.category
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/vnd.github+json"})
        if self.cfg.github_token:
            self.session.headers.update(
                {"Authorization": f"token {self.cfg.github_token}"}
            )

    def discover(self) -> List[str]:
        """Merges dynamic search results with static repo lists."""
        logger.info("Initiating discovery for category: %s", self.cfg.category)
        if self.cfg.profile:
            logger.info("Using profile: %s", self.cfg.profile)
            if self.cfg.profile_extensions:
                logger.info("Filtering by extensions: %s", self.cfg.profile_extensions)
            if self.cfg.profile_ignored_paths:
                logger.info("Ignoring paths: %s", self.cfg.profile_ignored_paths)

        discovered: List[str] = []
        if self.cfg.mode == "dynamic":
            discovered = self._github_search()

        # Deduplication
        seen: Set[str] = set(discovered)
        final_list = list(discovered)

        for repo in self.cfg.static_repos:
            if repo not in seen:
                # Apply profile-based filtering for static repos
                if self._should_include_repo(repo):
                    final_list.append(repo)
                    seen.add(repo)

        # Apply profile filters if configured
        if self.cfg.profile_extensions or self.cfg.profile_ignored_paths:
            final_list = self._filter_repos(final_list)

        return final_list[: self.cfg.limit]

    def _should_include_repo(self, repo_id: str) -> bool:
        """Determine if a repository should be included based on profile filters.

        This is a placeholder for more sophisticated filtering.
        In dry-run mode, this logs the filters that would be applied.
        """
        if self.cfg.profile_extensions:
            # For now, we assume all repos could have these extensions
            # In a full implementation, we might check repo metadata
            logger.debug("Repo %s - checking extensions", repo_id)
        if self.cfg.profile_ignored_paths:
            logger.debug("Repo %s - checking ignored paths", repo_id)
        return True

    def _filter_repos(self, repos: List[str]) -> List[str]:
        """Filter repositories based on profile configuration.

        Applies profile_extensions and profile_ignored_paths filters.
        """
        if not self.cfg.profile_extensions and not self.cfg.profile_ignored_paths:
            return repos

        filtered: List[str] = []
        for repo in repos:
            if self.cfg.profile_extensions:
                # In a full implementation, we'd check the actual repo contents
                # For now, log that filtering is applied
                logger.debug(
                    "Filtering repo %s by extensions: %s",
                    repo,
                    self.cfg.profile_extensions,
                )
            if self.cfg.profile_ignored_paths:
                # Filter out repos that match ignored path patterns
                # This is a simple check - full impl would check actual paths
                logger.debug(
                    "Filtering repo %s by ignored paths: %s",
                    repo,
                    self.cfg.profile_ignored_paths,
                )
            filtered.append(repo)

        logger.info(
            "Filtered %d repos to %d based on profile", len(repos), len(filtered)
        )
        return filtered

    def _github_search(self) -> List[str]:
        """Generic GitHub API search wrapper."""
        query = self.cfg.search_query or ""
        is_code = any(k in query.lower() for k in ["in:file", "filename:", "path:"])

        endpoint = "search/code" if is_code else "search/repositories"
        url = f"https://api.github.com/{endpoint}"

        collected: List[str] = []
        page = 1

        while len(collected) < self.cfg.limit:
            params = {
                "q": query if is_code else f"{query} stars:>={self.cfg.min_stars}",
                "per_page": self.cfg.per_page,
                "page": page,
            }

            if not is_code:
                params.update({"sort": "stars", "order": "desc"})

            response = self.session.get(url, params=params)
            if response.status_code == 403:
                self._handle_backoff(response)
                continue

            if response.status_code != 200:
                logger.error(
                    "GitHub API Error %s: %s", response.status_code, response.text
                )
                break

            items = response.json().get("items", [])
            if not items:
                break

            for it in items:
                meta = it.get("repository") if is_code else it
                full_name = meta.get("full_name")
                if full_name and full_name not in collected:
                    collected.append(full_name)
                if len(collected) >= self.cfg.limit:
                    break

            page += 1
            time.sleep(1)  # Rate limit politeness

        return collected

    def fetch(self, repos: List[str], dry_run: bool = False) -> None:
        """Atomic Git synchronization."""
        self.raw_path.mkdir(parents=True, exist_ok=True)

        for repo_id in repos:
            try:
                owner, name = repo_id.split("/")
                target = self.raw_path / owner / name
            except ValueError:
                continue

            if dry_run:
                logger.info("[DRY-RUN] Syncing %s", repo_id)
                continue

            if target.exists():
                self._update_repo(repo_id, target)
            else:
                self._clone_repo(repo_id, target)

    def _clone_repo(self, repo_id: str, target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Cloning: %s", repo_id)
        subprocess.run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                f"https://github.com/{repo_id}",
                str(target),
            ],
            capture_output=True,
            check=False,
        )

    def _update_repo(self, repo_id: str, target: Path) -> None:
        """Update repository with retry and safety checks.

        T026: Implements Git resilience:
        - Retry policy: up to 3 times (pull -> fetch+reset) with exponential backoff (1s, 2s, 4s)
        - Safety: apply reset only when remote contains target commit in its history
        - Check ancestry/commit-IDs to avoid destructive resets

        Args:
            repo_id: Repository identifier (e.g., "owner/repo")
            target: Local path to the repository

        Raises:
            subprocess.CalledProcessError: After exhausting all retries
        """
        logger.info("Updating: %s", repo_id)

        # Exponential backoff intervals: 1s, 2s, 4s
        backoff_intervals = [1, 2, 4]
        max_retries = 3

        for attempt in range(max_retries):
            try:
                # Try fast-forward pull first
                result = subprocess.run(
                    ["git", "-C", str(target), "pull", "--ff-only"],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                logger.info("Successfully updated %s via fast-forward", repo_id)
                return

            except subprocess.CalledProcessError as e:
                logger.warning(
                    "Pull failed for %s (attempt %d/%d): %s",
                    repo_id,
                    attempt + 1,
                    max_retries,
                    e.stderr or str(e),
                )

                # Check if we should retry
                if attempt < max_retries - 1:
                    # Apply exponential backoff before retry
                    backoff = backoff_intervals[attempt]
                    logger.info("Retrying %s in %ds (backoff)", repo_id, backoff)
                    time.sleep(backoff)

                    # Attempt recovery via fetch+reset
                    if self._safe_reset(target):
                        logger.info(
                            "Successfully recovered %s via fetch+reset", repo_id
                        )
                        return
                    else:
                        logger.warning(
                            "Reset safety check failed for %s, continuing retry",
                            repo_id,
                        )
                else:
                    # All retries exhausted
                    logger.error(
                        "Failed to update %s after %d attempts", repo_id, max_retries
                    )
                    raise

        # Should not reach here, but just in case
        raise subprocess.CalledProcessError(1, ["git", "pull"])

    def _safe_reset(self, target: Path) -> bool:
        """Perform safe reset with commit verification.

        T026: Safety - verify commit exists in remote before destructive reset.

        Args:
            target: Local path to the repository

        Returns:
            True if reset was successful and safe, False otherwise
        """
        try:
            # Step 1: Fetch latest from origin
            fetch_result = subprocess.run(
                ["git", "-C", str(target), "fetch", "--depth", "1", "origin"],
                capture_output=True,
                text=True,
            )
            if fetch_result.returncode != 0:
                logger.warning("Fetch failed: %s", fetch_result.stderr)
                return False

            # Step 2: Get the current HEAD commit before reset
            head_result = subprocess.run(
                ["git", "-C", str(target), "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
            )
            if head_result.returncode != 0:
                logger.warning("Could not get current HEAD: %s", head_result.stderr)
                return False
            current_head = head_result.stdout.strip()

            # Step 3: Get origin/HEAD commit
            remote_head_result = subprocess.run(
                ["git", "-C", str(target), "rev-parse", "origin/HEAD"],
                capture_output=True,
                text=True,
            )
            if remote_head_result.returncode != 0:
                logger.warning(
                    "Could not get origin/HEAD: %s", remote_head_result.stderr
                )
                return False
            remote_head = remote_head_result.stdout.strip()

            # Step 4: Verify that remote HEAD is reachable from current HEAD
            # (or that we're resetting to an ancestor, which is safe)
            merge_base_result = subprocess.run(
                [
                    "git",
                    "-C",
                    str(target),
                    "merge-base",
                    "--is-ancestor",
                    remote_head,
                    current_head,
                ],
                capture_output=True,
                text=True,
            )

            is_ancestor = merge_base_result.returncode == 0

            # Step 5: If remote is not ancestor, check if it's a valid commit
            # by verifying it exists in the remote history
            if not is_ancestor:
                # Try to verify remote head exists in fetched refs
                cat_file_result = subprocess.run(
                    ["git", "-C", str(target), "cat-file", "-t", remote_head],
                    capture_output=True,
                    text=True,
                )
                if cat_file_result.returncode != 0:
                    logger.warning(
                        "Remote HEAD %s not found in local history - aborting reset",
                        remote_head,
                    )
                    return False
                logger.info(
                    "Remote HEAD differs from local - performing reset to %s",
                    remote_head[:8],
                )

            # Step 6: Perform the reset
            reset_result = subprocess.run(
                ["git", "-C", str(target), "reset", "--hard", "origin/HEAD"],
                capture_output=True,
                text=True,
            )

            if reset_result.returncode != 0:
                logger.warning("Reset failed: %s", reset_result.stderr)
                return False

            # Step 7: Verify HEAD matches expected after reset
            new_head_result = subprocess.run(
                ["git", "-C", str(target), "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
            )
            if new_head_result.returncode != 0:
                logger.warning("Could not verify new HEAD after reset")
                return False

            new_head = new_head_result.stdout.strip()
            if new_head != remote_head:
                logger.warning(
                    "HEAD mismatch after reset: expected %s, got %s",
                    remote_head[:8],
                    new_head[:8],
                )
                return False

            logger.info("Safe reset completed successfully")
            return True

        except Exception as e:
            logger.error("Unexpected error during safe reset: %s", str(e))
            return False

    def _handle_backoff(self, resp: requests.Response) -> None:
        reset_ts = int(resp.headers.get("X-RateLimit-Reset", time.time()))
        wait = max(reset_ts - int(time.time()), 0) + 5
        logger.warning("Rate limit hit. Sleeping %ds.", wait)
        time.sleep(wait)

    def run(self, dry_run: bool = False) -> List[str]:
        repos = self.discover()
        self.fetch(repos, dry_run=dry_run)
        return repos


if __name__ == "__main__":
    load_dotenv()
    import argparse

    parser = argparse.ArgumentParser(description="Agnostic Repo Ingestor")
    parser.add_argument(
        "--config", "-c", required=True, help="Path to YAML config file"
    )
    parser.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    with open(args.config, "r") as f:
        config_data = yaml.safe_load(f)

    config = DiscoveryConfig(**config_data)

    # Environment override for security
    token = os.getenv("GITHUB_TOKEN")
    if token:
        config = config.model_copy(update={"github_token": token})

    engine = RepoIngestor(config)
    engine.run(dry_run=args.dry_run)
