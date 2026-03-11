# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
AEGF Module-Aware Processor  (V2)
==================================
Author : Joao Maria Arranz Aparicio (Architect Mode)
Purpose: Transforms raw repository clones into module-organised, typed
         Logical Entity bundles (.txt) for the AEGF V11+ training pipeline.

Fragment taxonomy
-----------------
  TIPO 1 [FUNCTIONAL_UNIT]   – Code + matching test
  TIPO 3 [LOGIC_ONLY]        – Standalone logic file (long, non-anchor)
  TIPO 4 [MODULE_BLUEPRINT]  – Architecture index: anchor files + README
                               (README searched in module dir, then walked up
                               to repo_root if not found locally)
  TIPO 5 [GOVERNANCE_RULES]  – Repo-level coding standards (CLAUDE.md,
                               AGENTS.md, .cursorrules, .clinerules).
                               One bundle per repository; applies to ALL
                               modules discovered in that same repository.
                               Written to target_root/_governance/.

Every .txt receives an [ARCH_HEADER] block with MODULE, FILE_ROLE,
LOCAL_IMPORTS, NEIGHBORS and REPO_PREFIX so the model learns both the
organisational graph and which governance rules apply.
"""

from __future__ import annotations

import argparse
import ast
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field

from src.utils.extractors import get_adapter
from src.utils.extractors.base import ParseError
from src.utils.metrics import get_metrics


# ---------------------------------------------------------------------------
# Custom Exceptions
# ---------------------------------------------------------------------------
class RepoAbortError(Exception):
    """Raised when a parse error triggers repository-level abort."""

    def __init__(self, repo_name: str, file_path: Path, parse_error: ParseError):
        self.repo_name = repo_name
        self.file_path = file_path
        self.parse_error = parse_error
        super().__init__(
            f"Parse error in {file_path} triggered abort for repository {repo_name}"
        )


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Quality / size constants
# ---------------------------------------------------------------------------
MIN_SIZE = 300  # bytes — skip trivial files for TIPO 1/2
MAX_SIZE_BACKEND = 150_000
MAX_SIZE_FRONTEND = 60_000
BACKEND_REPOS: Set[str] = {"core", "integration", "alarmo"}

GOLD_PATTERNS: List[str] = [
    "ConfigFlow",
    "DataUpdateCoordinator",
    "SensorEntityDescription",
    "LitElement",
    "CoordinatorEntity",
    "SensorEntity",
    "BinarySensorEntity",
    "SwitchEntity",
    "ClimateEntity",
    "async_add_entities",
    "ENTITY_ID_FORMAT",
    "async_setup_entry",
    "DOMAIN",
    "async_setup_platform",
    "async_add_devices",
    "async_remove_devices",
]

# Minimum size (chars) for a file to be TIPO 3 (LOGIC_ONLY) instead of TIPO 4
LOGIC_ONLY_MIN_CHARS = 800

# Architecture / anchor filenames — always captured for TIPO 4 blueprint
ANCHOR_FILENAMES: Set[str] = {
    "manifest.json",
    "const.py",
    "services.yaml",
    "strings.json",
    "icons.json",
    "hacs.json",
}

# Governance / coding-standards filenames — captured as TIPO 5 at repo root.
# These files encode per-repository rules that the model must respect.
GOVERNANCE_FILENAMES: Set[str] = {
    "CLAUDE.md",
    "AGENTS.md",
    ".cursorrules",
    ".clinerules",
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass(slots=True, frozen=True)
class ModuleFile:
    """A single file within a discovered module.

    Note: Uses frozen=True but content is set after creation via object.__setattr__
    to support lazy loading pattern (see line 649). This is an explicit lifecycle
    pattern where content is loaded on-demand during processing.
    """

    path: Path
    role: str = ""  # implementation | test | config | anchor | readme
    content: str = ""
    size: int = 0


@dataclass(slots=True, frozen=True)
class Module:
    """A discovered logical module (integration / package / virtual root).

    Immutable canonical record for module metadata. Use immutable tuples for
    `files` and `neighbors` to prevent accidental mutation at runtime.
    """

    name: str
    path: Path
    anchor_type: str = ""  # manifest | init | infrastructure
    files: Tuple[ModuleFile, ...] = field(default_factory=tuple)
    manifest: dict = field(default_factory=dict)
    neighbors: Tuple[str, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Pydantic config (unchanged interface)
# ---------------------------------------------------------------------------
class ProcessingConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)

    base_dir: Path = Field(default_factory=lambda: Path.cwd())
    raw_subdir: str = Field(..., description="Root directory for raw repository clones")
    output_subdir: str = Field(
        ..., description="Target directory for packaged .txt files"
    )
    category: str = Field(..., description="Category folder to process")
    output_category: Optional[str] = None
    segment_path: Optional[str] = None
    context_prefix: Optional[str] = None
    extensions: Set[str] = Field(default={".py", ".md"})
    ignore_patterns: Set[str] = Field(
        default={".git", "__pycache__", "venv", "node_modules", ".tox", "eggs"}
    )
    backend_repos: Set[str] = Field(default_factory=lambda: set(BACKEND_REPOS))
    profile: str = Field(
        default="homeassistant", description="Profile name for extractor adapter"
    )
    on_parse_error: str = Field(
        default="abort",
        description="Policy for parse errors: abort, skip, mark_and_continue, or fallback",
    )

    # Module discovery configuration
    module_discovery_strategy: str = Field(
        default="manifest",
        description="Strategy for discovering modules: manifest, init, directory, manual_mapping",
    )
    anchor_filenames: Set[str] = Field(
        default_factory=lambda: set(ANCHOR_FILENAMES),
        description="Filenames that serve as module anchors",
    )
    module_overrides: Optional[Dict[str, Dict[str, Any]]] = Field(
        default=None,
        description="Manual overrides for module discovery: {module_name: {enabled, path, anchor_type}}",
    )

    @property
    def final_context_prefix(self) -> str:
        if self.context_prefix:
            return self.context_prefix
        return f"{self.category.replace('-', ' ').title()} Expert"


# =========================================================================
# Main processor
# =========================================================================
class RepoProcessor:
    """Module-aware processor that emits typed .txt bundles."""

    def __init__(self, cfg: ProcessingConfig):
        self.cfg = cfg
        self.source_root = cfg.base_dir / cfg.raw_subdir / cfg.category
        target_folder = cfg.output_category or cfg.category
        self.target_root = cfg.base_dir / cfg.output_subdir / target_folder
        self.target_root.mkdir(parents=True, exist_ok=True)

        # Initialize the extractor adapter for the given profile
        self._adapter = get_adapter(cfg.profile)
        self._on_parse_error = cfg.on_parse_error

        # Initialize metrics collector (T030c)
        self._metrics = get_metrics()

        self._stats = {
            "TYPE1_FUNCTIONAL_UNIT": 0,
            "TYPE3_LOGIC_ONLY": 0,
            "TYPE4_MODULE_BLUEPRINT": 0,
            "TYPE5_GOVERNANCE_RULES": 0,
            "skipped_size": 0,
            "skipped_gold": 0,
            "modules_found": 0,
            "parse_errors": 0,
            "parse_errors_aborted": 0,
            "needs_manual_review": [],
        }

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
    def run(self) -> None:
        if not self.source_root.exists():
            logger.error("Source root missing: %s", self.source_root)
            return

        logger.info("Processing category: %s", self.cfg.category)
        logger.info("Output: %s", self.target_root)

        for owner_dir in sorted(self.source_root.iterdir()):
            if not owner_dir.is_dir():
                continue
            for repo_dir in sorted(owner_dir.iterdir()):
                if not repo_dir.is_dir():
                    continue
                # T030c: Measure repository processing time
                repo_start = time.perf_counter()
                self._process_repository(owner_dir.name, repo_dir)
                repo_latency = time.perf_counter() - repo_start
                self._metrics.record_file_processing_time(repo_dir.name, repo_latency)
                self._metrics.increment_files_processed(repo_dir.name)

        logger.info(
            "Processing complete — "
            + " | ".join(
                f"{k}={len(v) if isinstance(v, list) else v}"
                for k, v in self._stats.items()
            )
        )
        # T009e: Write persistent needs_manual_review report
        self._write_needs_manual_review_report()

    # ------------------------------------------------------------------
    # Repository dispatch
    # ------------------------------------------------------------------
    def _process_repository(self, owner: str, repo_path: Path) -> None:
        repo_name = repo_path.name
        size_limit = (
            MAX_SIZE_BACKEND
            if repo_name in self.cfg.backend_repos
            else MAX_SIZE_FRONTEND
        )
        prefix = f"{owner}_{repo_name}"

        # ── TIPO 5: detect and emit governance rules before module processing ──
        gov_files = self._find_governance_files(repo_path)
        if gov_files:
            self._emit_governance(prefix, repo_path, gov_files)

        try:
            if self.cfg.segment_path:
                split_target = repo_path / self.cfg.segment_path
                if split_target.exists() and split_target.is_dir():
                    for sub_dir in sorted(split_target.iterdir()):
                        if sub_dir.is_dir():
                            self._process_module_dir(
                                sub_dir,
                                repo_path,
                                f"{prefix}_{sub_dir.name}",
                                size_limit,
                                repo_prefix=prefix,
                            )
                    return

            # No segment_path → discover modules in the entire repo
            modules = self._discover_modules(repo_path)
            for mod in modules:
                mod_prefix = f"{prefix}_{mod.name}"
                self._emit_module(
                    mod, repo_path, mod_prefix, size_limit, repo_prefix=prefix
                )
        except RepoAbortError as e:
            # T009d: Abort the entire repository when parse error triggers abort policy
            logger.warning(
                "Repository %s aborted due to parse error in %s: %s",
                repo_name,
                e.file_path,
                e.parse_error,
            )
            # Mark this repo as needing manual review
            self._stats["needs_manual_review"].append(
                {
                    "repo": repo_name,
                    "file": str(e.file_path),
                    "reason": "parse_error_abort",
                    "error": str(e.parse_error),
                }
            )
            # T030c: Emit metrics for parse error
            self._metrics.increment_parse_error(repo_name, self.cfg.profile)
            self._metrics.increment_files_marked(repo_name)
            self._stats["parse_errors_aborted"] += 1

    # ------------------------------------------------------------------
    # Module discovery
    # ------------------------------------------------------------------
    def _discover_modules(self, root: Path) -> List[Module]:
        """Walk root and return a list of Module objects.

        The discovery strategy is determined by self.cfg.module_discovery_strategy:
        - 'manifest': detect modules via manifest.json and __init__.py (default)
        - 'init': detect modules via __init__.py only
        - 'directory': detect modules via directory structure with __init__.py
        - 'manual_mapping': use explicit module_overrides for discovery
        """
        strategy = self.cfg.module_discovery_strategy

        # Apply module_overrides if provided (applies to all strategies)
        if self.cfg.module_overrides:
            modules = self._discover_with_overrides(root)
            if modules:
                # If manual_mapping strategy, only return override-based modules
                if strategy == "manual_mapping":
                    self._stats["modules_found"] += len(modules)
                    return modules
                # For other strategies, merge overrides into results
                return self._merge_with_overrides(modules)

        # Route to appropriate strategy
        if strategy == "directory":
            return self._discover_by_directory(root)
        elif strategy == "manual_mapping":
            # No overrides provided - fall back to manifest/init
            return self._discover_by_init(root)
        elif strategy == "init":
            return self._discover_by_init(root)
        else:
            # Default: manifest strategy
            return self._discover_by_manifest_and_init(root)

    def _discover_by_manifest_and_init(self, root: Path) -> List[Module]:
        """Discover modules using manifest.json and __init__.py (default strategy)."""
        modules: List[Module] = []
        seen_dirs: Set[Path] = set()

        # 1. manifest.json = official module (strongest anchor)
        for manifest_path in root.rglob("manifest.json"):
            if self._is_ignored(manifest_path):
                continue
            mod_dir = manifest_path.parent
            if mod_dir in seen_dirs:
                continue
            seen_dirs.add(mod_dir)
            # Load manifest content and build an immutable Module record
            manifest_data: dict = {}
            try:
                manifest_data = json.loads(manifest_path.read_text(errors="ignore"))
            except Exception:
                manifest_data = {}
            modules.append(
                self._build_module(
                    mod_dir, anchor_type="manifest", manifest=manifest_data
                )
            )

        # 2. __init__.py = package anchor (only if not already covered by manifest)
        for init_path in root.rglob("__init__.py"):
            if self._is_ignored(init_path):
                continue
            mod_dir = init_path.parent
            if mod_dir in seen_dirs:
                continue
            seen_dirs.add(mod_dir)
            modules.append(self._build_module(mod_dir, anchor_type="init"))

        self._stats["modules_found"] += len(modules)
        return modules

    def _discover_by_init(self, root: Path) -> List[Module]:
        """Discover modules using __init__.py files only."""
        modules: List[Module] = []
        seen_dirs: Set[Path] = set()

        for init_path in root.rglob("__init__.py"):
            if self._is_ignored(init_path):
                continue
            mod_dir = init_path.parent
            if mod_dir in seen_dirs:
                continue
            seen_dirs.add(mod_dir)
            modules.append(self._build_module(mod_dir, anchor_type="init"))

        self._stats["modules_found"] += len(modules)
        return modules

    def _discover_by_directory(self, root: Path) -> List[Module]:
        """Discover modules based on directory structure.

        Finds all directories containing __init__.py files, treating each
        as a module. Similar to _discover_by_init but the intent is different
        (directory structure-based vs package-based).
        """
        modules: List[Module] = []
        seen_dirs: Set[Path] = set()

        # Find all directories with __init__.py
        for init_path in root.rglob("__init__.py"):
            if self._is_ignored(init_path):
                continue
            mod_dir = init_path.parent
            if mod_dir in seen_dirs:
                continue
            seen_dirs.add(mod_dir)
            modules.append(self._build_module(mod_dir, anchor_type="directory"))

        self._stats["modules_found"] += len(modules)
        return modules

    def _discover_with_overrides(self, root: Path) -> List[Module]:
        """Discover modules based on explicit module_overrides configuration."""
        modules: List[Module] = []
        if not self.cfg.module_overrides:
            return modules

        for module_name, override_config in self.cfg.module_overrides.items():
            # Check if module is enabled
            if not override_config.get("enabled", True):
                logger.debug("Module %s disabled via override", module_name)
                continue

            # Get explicit path from override
            module_path = override_config.get("path")
            if module_path:
                mod_dir = root / module_path
            else:
                # Fall back to directory name matching module_name
                mod_dir = root / module_name

            # Check if the directory exists
            if not mod_dir.exists() or not mod_dir.is_dir():
                logger.debug("Module path %s does not exist, skipping", mod_dir)
                continue

            anchor_type = override_config.get("anchor_type", "manual")
            manifest_data: dict = {}

            # Try to load manifest if present
            manifest_path = mod_dir / "manifest.json"
            if manifest_path.exists():
                try:
                    manifest_data = json.loads(manifest_path.read_text(errors="ignore"))
                    anchor_type = "manifest"
                except Exception:
                    pass

            modules.append(
                self._build_module(
                    mod_dir, anchor_type=anchor_type, manifest=manifest_data
                )
            )

        return modules

    def _merge_with_overrides(self, discovered_modules: List[Module]) -> List[Module]:
        """Merge discovered modules with module_overrides configuration.

        Removes modules that are disabled in overrides, and adds any modules
        defined exclusively in overrides.
        """
        if not self.cfg.module_overrides:
            return discovered_modules

        result: List[Module] = []
        seen_names: Set[str] = set()

        # First, add override-defined modules
        for module_name, override_config in self.cfg.module_overrides.items():
            if not override_config.get("enabled", True):
                continue

            module_path = override_config.get("path")
            if module_path:
                # This module is defined in overrides - add it if not already discovered
                if module_name not in {m.name for m in discovered_modules}:
                    mod_dir = override_config.get("path")
                    if mod_dir:
                        # This path should have been handled in _discover_with_overrides
                        continue
            seen_names.add(module_name)

        # Then, add discovered modules that are not disabled
        for mod in discovered_modules:
            override = self.cfg.module_overrides.get(mod.name)
            if override is not None:
                if not override.get("enabled", True):
                    logger.debug("Module %s disabled via override, skipping", mod.name)
                    continue
            result.append(mod)

        self._stats["modules_found"] += len(result)
        return result

    def _build_module(
        self, mod_dir: Path, anchor_type: str, manifest: Optional[dict] = None
    ) -> Module:
        """Scan the directory of a discovered module and return an immutable Module record."""
        files_list: List[ModuleFile] = []
        all_names: List[str] = []
        for f in sorted(mod_dir.iterdir()):
            if f.is_file() and f.suffix in (
                self.cfg.extensions | {".json", ".yaml", ".yml"}
            ):
                if self._is_ignored(f):
                    continue
                all_names.append(f.name)
                files_list.append(
                    ModuleFile(
                        path=f,
                        role=self._classify_role(f),
                        size=f.stat().st_size,
                    )
                )

        return Module(
            name=mod_dir.name,
            path=mod_dir,
            anchor_type=anchor_type,
            files=tuple(files_list),
            manifest=manifest or {},
            neighbors=tuple(all_names),
        )

    # ------------------------------------------------------------------
    # Segment-path shortcut  (e.g. homeassistant/components/<component>)
    # ------------------------------------------------------------------
    def _process_module_dir(
        self,
        mod_dir: Path,
        repo_root: Path,
        prefix: str,
        size_limit: int,
        repo_prefix: str = "",
    ) -> None:
        """Process a single segmented component directory as a module."""
        anchor = "manifest" if (mod_dir / "manifest.json").exists() else "init"
        manifest_data: dict = {}
        if anchor == "manifest":
            try:
                manifest_data = json.loads(
                    (mod_dir / "manifest.json").read_text(errors="ignore")
                )
            except Exception:
                manifest_data = {}

        mod = self._build_module(mod_dir, anchor_type=anchor, manifest=manifest_data)
        self._emit_module(mod, repo_root, prefix, size_limit, repo_prefix=repo_prefix)

    # ------------------------------------------------------------------
    # Module emission: generates TIPO 1-4 bundles
    # ------------------------------------------------------------------
    def _emit_module(
        self,
        mod: Module,
        repo_root: Path,
        prefix: str,
        size_limit: int,
        repo_prefix: str = "",
    ) -> None:
        """For one module, emit all applicable fragment types."""
        # Each module gets its own subdirectory inside target_root
        module_dir = self.target_root / mod.name
        module_dir.mkdir(parents=True, exist_ok=True)

        # Separate files by role
        logic_files: List[ModuleFile] = []
        anchor_files: List[ModuleFile] = []
        readme_file: Optional[ModuleFile] = None

        for mf in mod.files:
            if mf.role == "readme":
                readme_file = mf
            elif mf.role == "anchor":
                anchor_files.append(mf)
            elif mf.role == "test":
                pass  # tests are context, not standalone
            else:
                logic_files.append(mf)

        # README inheritance: if no README inside this module dir, walk up to
        # repo_root looking for one (covers HACS-style repos where README.md
        # lives at the repository root, above the custom_components/ subdir).
        # The README is an anchor of TIPO 4 — it never feeds TIPO 2.
        if readme_file is None:
            inherited = self._find_readme(mod.path, repo_root)
            if inherited:
                readme_file = ModuleFile(
                    path=inherited,
                    role="readme",
                    size=inherited.stat().st_size,
                )
                logger.debug("[%s] Inherited README: %s", mod.name, inherited)

        # ------- TIPO 4: MODULE_BLUEPRINT (always first) -------
        # README is always folded into the blueprint when available.
        blueprint_files = list(anchor_files)
        if readme_file:
            blueprint_files.append(readme_file)
        if blueprint_files:
            self._emit_blueprint(mod, blueprint_files, prefix, module_dir)
            self._stats["TYPE4_MODULE_BLUEPRINT"] += 1

        # ------- TIPO 1, 2, 3 for each logic file -------
        for mf in logic_files:
            if mf.path.name in ANCHOR_FILENAMES:
                # Already covered by blueprint
                continue

            # Read content early so we can apply test-based overrides
            try:
                content = mf.path.read_text(encoding="utf-8", errors="ignore")
                # Bypass frozen check for lazy loading pattern
                object.__setattr__(mf, "content", content)
            except Exception as e:
                logger.error("Read error %s: %s", mf.path, e)
                continue

            # Detect local imports for header (needed for all bundle types)
            # Use the adapter to extract dependencies from the file
            local_imports: List[str] = []
            dependencies: List[str] = []
            if mf.path.suffix == ".py":
                try:
                    # Per plan: call parse_file first to handle parse errors explicitly
                    # This follows ParseError-first policy where processor decides the policy
                    parse_result = self._adapter.parse_file(mf.path)
                    deps = parse_result.dependencies
                    # Extract local imports (relative imports) as .py files
                    local_imports = [
                        d.name + ".py" for d in deps if d.module_type == "relative"
                    ]
                    # All dependencies for the header
                    dependencies = [d.name for d in deps]
                except ParseError as e:
                    self._stats["parse_errors"] += 1
                    # T030c: Emit metrics for parse error
                    self._metrics.increment_parse_error(
                        repo_root.name, self.cfg.profile
                    )
                    if self._on_parse_error == "abort":
                        # T009d: Abort the entire repository, not just the file
                        logger.warning(
                            "Parse error in %s, aborting repository: %s",
                            mf.path,
                            e,
                        )
                        # Raise to propagate to repository level
                        raise RepoAbortError(
                            repo_name=repo_root.name, file_path=mf.path, parse_error=e
                        )
                    elif self._on_parse_error == "skip":
                        logger.warning(
                            "Parse error in %s, skipping file: %s", mf.path, e
                        )
                        continue
                    elif self._on_parse_error == "mark_and_continue":
                        # T009f: Mark file as needs_manual_review but continue processing
                        logger.warning(
                            "Parse error in %s, marking for review and continuing: %s",
                            mf.path,
                            e,
                        )
                        self._stats["needs_manual_review"].append(
                            {
                                "repo": repo_root.name,
                                "file": str(mf.path),
                                "reason": "parse_error_marked",
                                "error": str(e),
                            }
                        )
                        # Continue processing but use fallback for dependencies
                        local_imports = self._extract_local_imports(content)
                        dependencies = []
                    else:
                        # Fallback: use the old method
                        local_imports = self._extract_local_imports(content)

            # Try TIPO 1 first: if there is an exact matching test, always emit
            # as a FUNCTIONAL_UNIT regardless of MIN_SIZE (teaching tests is valuable).
            test_file = self._find_test(mf.path, repo_root, size_limit)
            if test_file:
                entity_id = f"{prefix}_{mf.path.stem}"
                header = self._make_arch_header(
                    mod,
                    mf,
                    local_imports,
                    "FUNCTIONAL_UNIT",
                    repo_prefix,
                    dependencies=dependencies,
                )
                self._write_typed_bundle(
                    entity_id,
                    "FUNCTIONAL_UNIT",
                    mf,
                    test_file,
                    mod.path,
                    header,
                    module_dir,
                )
                self._stats["TYPE1_FUNCTIONAL_UNIT"] += 1
                continue

            # No test — now apply the size gate for non-test files
            if mf.size < MIN_SIZE or mf.size > size_limit:
                self._stats["skipped_size"] += 1
                continue

            # Gold pattern filter for .py (keeps legacy behavior for files without tests)
            if mf.path.suffix == ".py" and not any(p in content for p in GOLD_PATTERNS):
                self._stats["skipped_gold"] += 1
                continue

            # TIPO 3: emit as standalone if long enough
            if (
                len(content) >= LOGIC_ONLY_MIN_CHARS
                and mf.path.name not in ANCHOR_FILENAMES
            ):
                entity_id = f"{prefix}_{mf.path.stem}"
                header = self._make_arch_header(
                    mod,
                    mf,
                    local_imports,
                    "LOGIC_ONLY",
                    repo_prefix,
                    dependencies=dependencies,
                )
                self._write_standalone_bundle(
                    entity_id,
                    "LOGIC_ONLY",
                    mf,
                    mod.path,
                    header,
                    module_dir,
                )
                self._stats["TYPE3_LOGIC_ONLY"] += 1

    # ------------------------------------------------------------------
    # TIPO 4 — Blueprint emitter
    # ------------------------------------------------------------------
    def _emit_blueprint(
        self,
        mod: Module,
        anchor_files: List[ModuleFile],
        prefix: str,
        module_dir: Path,
    ) -> None:
        """Write the synthetic MODULE_BLUEPRINT .txt for this module."""
        entity_id = f"{prefix}_blueprint"
        out = module_dir / f"{entity_id}.txt"

        buf: List[str] = [
            f"=== LOGICAL ENTITY: {entity_id} ===",
            f"Context: {self.cfg.final_context_prefix} Knowledge Base",
            "Type: MODULE_BLUEPRINT\n",
        ]

        # MODULE_MAP
        buf.append("[MODULE_MAP]")
        buf.append(f"MODULE: {mod.name}")
        buf.append(f"ANCHOR: {mod.anchor_type}")
        buf.append(f"FILES: {mod.neighbors}")
        buf.append("")

        # DEPENDENCIES (from manifest)
        if mod.manifest:
            buf.append("[DEPENDENCIES]")
            buf.append(f"domain: {mod.manifest.get('domain', 'unknown')}")
            deps = mod.manifest.get("dependencies", [])
            after = mod.manifest.get("after_dependencies", [])
            buf.append(f"dependencies: {deps}")
            buf.append(f"after_dependencies: {after}")
            reqs = mod.manifest.get("requirements", [])
            if reqs:
                buf.append(f"requirements: {reqs}")
            buf.append("")

        # SCHEMA (from services.yaml)
        svc_file = next(
            (f for f in anchor_files if f.path.name == "services.yaml"), None
        )
        if svc_file:
            try:
                content = svc_file.path.read_text(encoding="utf-8", errors="ignore")
                buf.append("[SCHEMA]")
                buf.append(content.strip())
                buf.append("")
            except Exception:
                pass

        # VOCABULARY (from const.py)
        const_file = next((f for f in anchor_files if f.path.name == "const.py"), None)
        if const_file:
            try:
                content = const_file.path.read_text(encoding="utf-8", errors="ignore")
                buf.append("[VOCABULARY]")
                buf.append(content.strip())
                buf.append("")
            except Exception:
                pass

        # README section (always last, for readability)
        readme_af = next((f for f in anchor_files if f.role == "readme"), None)
        if readme_af:
            try:
                content = readme_af.path.read_text(encoding="utf-8", errors="ignore")
                buf.append("[README]")
                buf.append(content.strip())
                buf.append("")
            except Exception as e:
                logger.error("Read error %s: %s", readme_af.path, e)

        # Remaining anchor files (manifest.json, strings.json, __init__.py, etc.)
        for af in anchor_files:
            if af.path.name in ("services.yaml", "const.py") or af.role == "readme":
                continue  # already rendered above
            try:
                content = af.path.read_text(encoding="utf-8", errors="ignore")
                buf.append(f"--- FILE: {af.path.name} ---")
                buf.append(content.strip())
                buf.append("")
            except Exception as e:
                logger.error("Read error %s: %s", af.path, e)

        out.write_text("\n".join(buf), encoding="utf-8")
        logger.debug("Blueprint written: %s", out.name)

    # ------------------------------------------------------------------
    # Bundle writers
    # ------------------------------------------------------------------
    def _write_typed_bundle(
        self,
        entity_id: str,
        ftype: str,
        logic: ModuleFile,
        context_path: Path,
        source_dir: Path,
        header: str,
        module_dir: Path,
    ) -> None:
        """Write a TIPO 1 or TIPO 2 bundle (code + context)."""
        out = module_dir / f"{entity_id}.txt"
        buf = [
            f"=== LOGICAL ENTITY: {entity_id} ===",
            f"Context: {self.cfg.final_context_prefix} Knowledge Base",
            f"Type: {ftype}\n",
            header,
            "",
        ]
        # Logic file
        buf.append(f"--- FILE: {logic.path.name} ---")
        if not logic.content:
            try:
                logic.content = logic.path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                pass
        buf.append(logic.content.strip() + "\n")

        # Context file
        try:
            ctx_content = context_path.read_text(encoding="utf-8", errors="ignore")
            try:
                rel = context_path.relative_to(source_dir)
            except ValueError:
                rel = context_path.name
            buf.append(f"--- FILE: {rel} ---")
            buf.append(ctx_content.strip() + "\n")
        except Exception as e:
            logger.error("Read error %s: %s", context_path, e)

        out.write_text("\n".join(buf), encoding="utf-8")
        logger.debug("Bundle [%s]: %s", ftype, out.name)

    def _write_standalone_bundle(
        self,
        entity_id: str,
        ftype: str,
        logic: ModuleFile,
        source_dir: Path,
        header: str,
        module_dir: Path,
    ) -> None:
        """Write a TIPO 3 bundle (standalone logic)."""
        out = module_dir / f"{entity_id}.txt"
        buf = [
            f"=== LOGICAL ENTITY: {entity_id} ===",
            f"Context: {self.cfg.final_context_prefix} Knowledge Base",
            f"Type: {ftype}\n",
            header,
            "",
        ]
        buf.append(f"--- FILE: {logic.path.name} ---")
        if not logic.content:
            try:
                logic.content = logic.path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                pass
        buf.append(logic.content.strip() + "\n")
        out.write_text("\n".join(buf), encoding="utf-8")
        logger.debug("Bundle [%s]: %s", ftype, out.name)

    # ------------------------------------------------------------------
    # ARCH_HEADER builder
    # ------------------------------------------------------------------
    def _make_arch_header(
        self,
        mod: Module,
        mf: ModuleFile,
        local_imports: List[str],
        ftype: str,
        repo_prefix: str = "",
        dependencies: Optional[List[str]] = None,
    ) -> str:
        """Build the [ARCH_HEADER] block for a bundle."""
        lines = [
            "[ARCH_HEADER]",
            f"MODULE: {mod.name}",
            f"REPO_PREFIX: {repo_prefix}",
            f"FILE_ROLE: {mf.role}",
            f"FRAGMENT_TYPE: {ftype}",
            f"LOCAL_IMPORTS: {local_imports}",
            f"DEPENDENCIES: {dependencies or []}",
            f"NEIGHBORS: {mod.neighbors}",
        ]
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Test file locator  (namespace-aware)
    # ------------------------------------------------------------------
    def _find_test(
        self,
        logic_file: Path,
        repo_root: Path,
        size_limit: int,
    ) -> Optional[Path]:
        """Find the best test file for a logic .py file.

        Priority:
        1. Namespace mirror: repo_root/tests/<relative_parent>/test_<name>
        2. Component test dir: repo_root/tests/components/<component>/test_<name>
        2b. Any test_*.py in the same component test dir (largest)
        3. Scored rglob with score >= 2
        Returns None if nothing qualifies.
        """
        if logic_file.suffix != ".py":
            return None

        if logic_file.name == "__init__.py":
            test_name = "test_init.py"
        else:
            test_name = f"test_{logic_file.name}"

        def _ok(p: Path) -> bool:
            return p.is_file() and MIN_SIZE <= p.stat().st_size <= size_limit

        # relative path from repo_root
        try:
            rel = logic_file.relative_to(repo_root)
        except ValueError:
            rel = Path(logic_file.name)

        # 1. Namespace mirror
        ns = repo_root / "tests" / rel.parent / test_name
        if _ok(ns):
            return ns

        # 2. Component test dir
        component = logic_file.parent.name
        ctd = repo_root / "tests" / "components" / component
        if ctd.is_dir():
            exact = ctd / test_name
            if _ok(exact):
                return exact

        # 3. Scored rglob (min score 2)
        logic_parts = set(rel.parts[:-1])
        best, best_score = None, -1
        for c in repo_root.rglob(test_name):
            if not _ok(c):
                continue
            try:
                cp = set(c.relative_to(repo_root).parts[:-1])
            except ValueError:
                cp = set()
            score = len(logic_parts & cp)
            if score >= 2 and score > best_score:
                best_score, best = score, c

        return best

    def _find_governance_files(self, repo_root: Path) -> List[Path]:
        """Return governance files present directly at *repo_root*.

        Only the repository root is checked — governance rules at subdirectory
        level would be component-specific and would need a separate mechanism.
        Files returned in deterministic (sorted) order.
        """
        found: List[Path] = []
        for name in sorted(GOVERNANCE_FILENAMES):
            candidate = repo_root / name
            if candidate.is_file():
                found.append(candidate)
        return found

    def _emit_governance(
        self,
        repo_prefix: str,
        repo_root: Path,
        gov_files: List[Path],
    ) -> None:
        """Write a TIPO 5 GOVERNANCE_RULES bundle to target_root/_governance/.

        The bundle carries:
          • [GOVERNANCE_HEADER] with REPO_PREFIX and APPLIES_TO
          • One ``--- FILE: <name> ---`` section per governance file

        Production_v11 reads this during Pass 1 to build the governance_cache
        (keyed by repo_prefix) and injects the content into every fragment that
        shares the same REPO_PREFIX.
        """
        gov_dir = self.target_root / "_governance"
        gov_dir.mkdir(parents=True, exist_ok=True)

        entity_id = f"{repo_prefix}_governance"
        out = gov_dir / f"{entity_id}.txt"

        source_names = ", ".join(f.name for f in gov_files)
        buf: List[str] = [
            f"=== LOGICAL ENTITY: {entity_id} ===",
            f"Context: {self.cfg.final_context_prefix} Knowledge Base",
            "Type: GOVERNANCE_RULES\n",
            "[GOVERNANCE_HEADER]",
            f"REPO_PREFIX: {repo_prefix}",
            f"APPLIES_TO: all modules in repository '{repo_prefix}'",
            f"SOURCE_FILES: {source_names}",
            "",
        ]

        for gf in gov_files:
            try:
                content = gf.read_text(encoding="utf-8", errors="ignore").strip()
                buf.append(f"--- FILE: {gf.name} ---")
                buf.append(content)
                buf.append("")
            except Exception as e:
                logger.warning("Governance read error %s: %s", gf, e)

        out.write_text("\n".join(buf), encoding="utf-8")
        self._stats["TYPE5_GOVERNANCE_RULES"] += 1
        logger.info("Governance bundle: %s (%s)", out.name, source_names)

    # ------------------------------------------------------------------
    # Needs Manual Review Report
    # ------------------------------------------------------------------
    def _write_needs_manual_review_report(self) -> None:
        """Write a persistent report of files/repos that need manual review.

        T009e: This report is written to the output directory and contains
        all parse errors that were marked for review (either via abort policy
        or mark_and_continue policy).
        """
        needs_review = self._stats.get("needs_manual_review", [])
        if not needs_review:
            logger.debug("No files require manual review")
            return

        report_dir = self.target_root / "_reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / "needs_manual_review.json"

        report_data = {
            "category": self.cfg.category,
            "profile": self.cfg.profile,
            "on_parse_error_policy": self._on_parse_error,
            "total_items": len(needs_review),
            "items": needs_review,
        }

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, default=str)

        logger.info(
            "Needs manual review report written: %s (%d items)",
            report_path,
            len(needs_review),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _classify_role(self, f: Path) -> str:
        """Determine the semantic role of a file."""
        name = f.name.lower()
        if name in ("readme.md", "readme.rst", "readme.txt"):
            return "readme"
        if f.name in GOVERNANCE_FILENAMES or name in GOVERNANCE_FILENAMES:
            return "governance"
        if name in ANCHOR_FILENAMES or f.suffix in (".json", ".yaml", ".yml"):
            return "anchor"
        if "test" in name:
            return "test"
        if name in ("setup.py", "setup.cfg", "pyproject.toml"):
            return "anchor"
        return "implementation"

    def _is_ignored(self, p: Path) -> bool:
        return any(ig in p.parts for ig in self.cfg.ignore_patterns)

    def _find_readme(self, start: Path, repo_root: Path) -> Optional[Path]:
        """Walk up from *start*'s parent to repo_root looking for a README file.

        The start directory itself is already scanned by _build_module, so we
        begin one level above to avoid re-finding the same (absent) README.
        Stops at repo_root (inclusive) or when leaving it.
        """
        candidate_names = ("README.md", "README.rst", "README.txt", "readme.md")
        try:
            current = start.parent
            repo_str = str(repo_root)
            while True:
                for name in candidate_names:
                    candidate = current / name
                    if candidate.is_file():
                        return candidate
                # Stop when we reach or would exceed repo_root
                if current == repo_root or not str(current).startswith(repo_str):
                    break
                current = current.parent
        except Exception:
            pass
        return None

    @staticmethod
    def _extract_local_imports(code: str) -> List[str]:
        """Extract relative imports as concrete filename.py references.

        ``from .const import X`` → ``const.py``
        ``from .webrtc.helpers import Y`` → ``helpers.py``
        Duplicates are suppressed.
        """
        imports: List[str] = []
        try:
            tree = ast.parse(code)
        except SyntaxError:
            # Fallback regex — strip leading dots and take the last segment
            for m in re.finditer(r"from\s+(\.[.\w]*)\s+import", code):
                raw = m.group(1).lstrip(".")
                if raw:
                    clean = raw.split(".")[-1] + ".py"
                    if clean not in imports:
                        imports.append(clean)
            return imports

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.level and node.level > 0:
                module = node.module or ""
                if module:
                    clean_module = module.split(".")[-1] + ".py"
                    if clean_module not in imports:
                        imports.append(clean_module)
        return imports


# =========================================================================
# CLI
# =========================================================================
if __name__ == "__main__":
    load_dotenv()
    parser = argparse.ArgumentParser(description="AEGF Module-Aware Processor V2")
    parser.add_argument(
        "--config", "-c", required=True, help="Path to YAML configuration"
    )
    args = parser.parse_args()

    if not os.path.exists(args.config):
        logger.error("Config not found: %s", args.config)
        sys.exit(1)

    try:
        with open(args.config, "r") as f:
            config_data = yaml.safe_load(f)
        config = ProcessingConfig(**config_data)
        RepoProcessor(config).run()
    except Exception as e:
        logger.critical("Processor failed: %s", e)
        sys.exit(1)
