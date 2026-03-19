# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Metadata Enricher Module
======================
Provides metadata computation, bundle writing, and processing orchestration
for the AEGF processor. Handles the main RepoProcessor class and all
bundle emission logic.

Author: Joao Maria Arranz Aparicio
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from src.utils.extractors import get_adapter
from src.utils.extractors.base import ParseError
from src.utils.metrics import get_metrics

from src.discovery.file_scanner import (
    ANCHOR_FILENAMES,
    BACKEND_REPOS,
    GOLD_PATTERNS,
    LOGIC_ONLY_MIN_CHARS,
    MAX_SIZE_BACKEND,
    MAX_SIZE_FRONTEND,
    MIN_SIZE,
    discover_modules,
    find_governance_files,
    find_readme,
    find_test,
)
from src.discovery.fragment_parser import (
    Module,
    ModuleFile,
    build_module,
    extract_local_imports,
    make_arch_header,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)


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
# Pydantic Config
# ---------------------------------------------------------------------------


class ProcessingConfig(BaseModel):
    """Configuration for the RepoProcessor."""

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
    extensions: set[str] = Field(default={".py", ".md"})
    ignore_patterns: set[str] = Field(
        default={".git", "__pycache__", "venv", "node_modules", ".tox", "eggs"}
    )
    backend_repos: set[str] = Field(default_factory=lambda: set(BACKEND_REPOS))
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
    anchor_filenames: set[str] = Field(
        default_factory=lambda: set(ANCHOR_FILENAMES),
        description="Filenames that serve as module anchors",
    )
    module_overrides: Optional[Dict[str, Dict[str, Any]]] = Field(
        default=None,
        description="Manual overrides for module discovery: {module_name: {enabled, path, anchor_type}}",
    )
    sc001_timeout_s: float = Field(
        default=5.0,
        description="SC-001 timeout in seconds for PHP processing benchmark (AMD Threadripper baseline; override for non-reference hardware)",
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
        gov_files = find_governance_files(repo_path)
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
            self._stats["modules_found"] += len(modules)

            for mod in modules:
                self._emit_module(
                    mod, repo_path, prefix, size_limit, repo_prefix=prefix
                )

        except RepoAbortError as e:
            self._stats["parse_errors_aborted"] += 1
            # Add to needs_manual_review for tracking
            self._stats["needs_manual_review"].append(
                {
                    "repo": repo_name,
                    "file": str(e.file_path),
                    "reason": "parse_error_abort",
                    "error": str(e.parse_error),
                }
            )
            logger.warning("Aborted repository due to parse error: %s", repo_name)

    # ------------------------------------------------------------------
    # Module discovery
    # ------------------------------------------------------------------
    def _discover_modules(self, root: Path) -> List[Module]:
        """Discover modules using the configured strategy."""
        if self.cfg.module_discovery_strategy == "directory_scan":
            return self._discover_modules_directory_scan(root)
        return discover_modules(
            root=root,
            strategy=self.cfg.module_discovery_strategy,
            ignore_patterns=self.cfg.ignore_patterns,
            extensions=self.cfg.extensions,
            anchor_filenames=self.cfg.anchor_filenames,
            module_overrides=self.cfg.module_overrides,
            build_module_func=self._build_module,
        )

    def _discover_modules_directory_scan(self, root: Path) -> List[Module]:
        """Discover modules by scanning recursively for PHP files (directory_scan strategy).

        Scans root with Path.rglob("*.php"), excludes vendor/, node_modules/,
        tests/, and cache/ directories, then groups files by parent directory.
        Each directory containing at least one .php file becomes a module.

        Args:
            root: Repository root directory to scan.

        Returns:
            List of Module instances for each directory containing PHP files.
        """
        _EXCLUDE_DIRS = {"vendor", "node_modules", "tests", "cache"}

        # Collect all PHP files, excluding known non-source dirs
        php_files: list[Path] = []
        for php_file in root.rglob("*.php"):
            # Exclude by checking any path component against _EXCLUDE_DIRS
            if not any(part in _EXCLUDE_DIRS for part in php_file.parts):
                php_files.append(php_file)

        # Group files by parent directory (each dir → one module)
        dir_to_files: dict[Path, list[Path]] = {}
        for php_file in php_files:
            parent = php_file.parent
            dir_to_files.setdefault(parent, []).append(php_file)

        modules: List[Module] = []
        for mod_dir, files in dir_to_files.items():
            try:
                module = self._build_module(mod_dir, anchor_type="directory_scan")
                modules.append(module)
            except Exception as exc:
                logger.warning("Could not build module for %s: %s", mod_dir, exc)

        logger.info(
            "directory_scan: found %d module directories in %s", len(modules), root
        )
        return modules

    def _build_module(
        self, mod_dir: Path, anchor_type: str, manifest: Optional[dict] = None
    ) -> Module:
        """Build a Module from a directory."""
        return build_module(
            mod_dir=mod_dir,
            anchor_type=anchor_type,
            extensions=self.cfg.extensions,
            ignore_patterns=self.cfg.ignore_patterns,
            manifest=manifest,
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
            inherited = find_readme(mod.path, repo_root)
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
                        local_imports = extract_local_imports(content)
                        dependencies = []
                    else:
                        # Fallback: use the old method
                        local_imports = extract_local_imports(content)

            # Try TIPO 1 first: if there is an exact matching test, always emit
            # as a FUNCTIONAL_UNIT regardless of MIN_SIZE (teaching tests is valuable).
            test_file = find_test(mf.path, repo_root, size_limit)
            if test_file:
                entity_id = f"{prefix}_{mf.path.stem}"
                header = make_arch_header(
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
                header = make_arch_header(
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
    # Governance emitter
    # ------------------------------------------------------------------
    def _emit_governance(
        self,
        repo_prefix: str,
        repo_root: Path,
        gov_files: List[Path],
    ) -> None:
        """Write a TIPO 5 GOVERNANCE_RULES bundle to target_root/_governance/."""
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
        """Write a persistent report of files/repos that need manual review."""
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
    # Backward-compatible methods (moved to fragment_parser.py)
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
        """Build the [ARCH_HEADER] block for a bundle.

        This method is kept for backward compatibility.
        Delegates to make_arch_header from fragment_parser.
        """
        return make_arch_header(
            mod=mod,
            mf=mf,
            local_imports=local_imports,
            ftype=ftype,
            repo_prefix=repo_prefix,
            dependencies=dependencies,
        )
