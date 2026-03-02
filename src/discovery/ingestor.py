# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

""""
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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Set
import requests
import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, model_validator

# --- Logging Setup ---
LOGGER_NAME = "AEGF.Ingestor"
logger = logging.getLogger(LOGGER_NAME)

class DiscoveryConfig(BaseModel):
    """Agnostic schema for repository discovery settings."""
    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)

    # Core Parameters
    category: str = Field(..., description="Target subdirectory name")
    mode: Literal["dynamic", "static"] = Field("static")

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
            self.session.headers.update({"Authorization": f"token {self.cfg.github_token}"})

    def discover(self) -> List[str]:
        """Merges dynamic search results with static repo lists."""
        logger.info(f"Initiating discovery for category: {self.cfg.category}")
        discovered: List[str] = []
        if self.cfg.mode == "dynamic":
            discovered = self._github_search()

        # Deduplication
        seen: Set[str] = set(discovered)
        final_list = list(discovered)

        for repo in self.cfg.static_repos:
            if repo not in seen:
                final_list.append(repo)
                seen.add(repo)

        return final_list[:self.cfg.limit]

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
                "page": page
            }

            if not is_code:
                params.update({"sort": "stars", "order": "desc"})

            response = self.session.get(url, params=params)
            if response.status_code == 403:
                self._handle_backoff(response)
                continue

            if response.status_code != 200:
                logger.error(f"GitHub API Error {response.status_code}: {response.text}")
                break

            items = response.json().get("items", [])
            if not items: break

            for it in items:
                meta = it.get("repository") if is_code else it
                full_name = meta.get("full_name")
                if full_name and full_name not in collected:
                    collected.append(full_name)
                if len(collected) >= self.cfg.limit: break

            page += 1
            time.sleep(1) # Rate limit politeness

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
                logger.info(f"[DRY-RUN] Syncing {repo_id}")
                continue

            if target.exists():
                self._update_repo(repo_id, target)
            else:
                self._clone_repo(repo_id, target)

    def _clone_repo(self, repo_id: str, target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Cloning: {repo_id}")
        subprocess.run(
            ["git", "clone", "--depth", "1", f"https://github.com/{repo_id}", str(target)],
            capture_output=True, check=False
        )

    def _update_repo(self, repo_id: str, target: Path) -> None:
        logger.info(f"Updating: {repo_id}")
        try:
            subprocess.run(["git", "-C", str(target), "pull", "--ff-only"], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            subprocess.run(["git", "-C", str(target), "fetch", "--depth", "1", "origin"], check=False)
            subprocess.run(["git", "-C", str(target), "reset", "--hard", "origin/HEAD"], check=False)

    def _handle_backoff(self, resp: requests.Response) -> None:
        reset_ts = int(resp.headers.get("X-RateLimit-Reset", time.time()))
        wait = max(reset_ts - int(time.time()), 0) + 5
        logger.warning(f"Rate limit hit. Sleeping {wait}s.")
        time.sleep(wait)

    def run(self, dry_run: bool = False) -> List[str]:
        repos = self.discover()
        self.fetch(repos, dry_run=dry_run)
        return repos

if __name__ == "__main__":
    load_dotenv()
    import argparse
    
    parser = argparse.ArgumentParser(description="Agnostic Repo Ingestor")
    parser.add_argument("--config", "-c", required=True, help="Path to YAML config file")
    parser.add_argument("--dry-run", action="store_true")
    
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    with open(args.config, "r") as f:
        config_data = yaml.safe_load(f)
    
    config = DiscoveryConfig(**config_data)
    
    # Environment override for security
    token = os.getenv("GITHUB_TOKEN")
    if token:
        config.github_token = token

    engine = RepoIngestor(config)
    engine.run(dry_run=args.dry_run)