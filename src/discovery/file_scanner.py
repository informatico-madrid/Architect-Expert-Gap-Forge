# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Discovery File Scanner Module
=============================
Provides filesystem traversal and module discovery functionality for the AEGF
processor. Handles various strategies for discovering modules within repositories.

Author: Joao Maria Arranz Aparicio
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set

if TYPE_CHECKING:
    from src.discovery.fragment_parser import Module

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
GOVERNANCE_FILENAMES: Set[str] = {
    "CLAUDE.md",
    "AGENTS.md",
    ".cursorrules",
    ".clinerules",
}


# ---------------------------------------------------------------------------
# Module Discovery Functions
# ---------------------------------------------------------------------------


def discover_modules(
    root: Path,
    strategy: str,
    ignore_patterns: Set[str],
    extensions: Set[str],
    anchor_filenames: Set[str],
    module_overrides: Optional[Dict[str, Dict[str, Any]]] = None,
    build_module_func: Optional[callable] = None,
) -> List["Module"]:
    """Walk root and return a list of Module objects.

    The discovery strategy is determined by the strategy parameter:
    - 'manifest': detect modules via manifest.json and __init__.py (default)
    - 'init': detect modules via __init__.py only
    - 'directory': detect modules via directory structure with __init__.py
    - 'manual_mapping': use explicit module_overrides for discovery

    Args:
        root: Root directory to scan for modules
        strategy: Module discovery strategy to use
        ignore_patterns: Patterns to ignore during discovery
        extensions: File extensions to consider
        anchor_filenames: Filenames that serve as module anchors
        module_overrides: Optional manual overrides for module discovery
        build_module_func: Callback function to build Module objects
    """
    # Apply module_overrides if provided (applies to all strategies)
    if module_overrides:
        modules = _discover_with_overrides(
            root,
            module_overrides,
            ignore_patterns,
            extensions,
            anchor_filenames,
            build_module_func,
        )
        if modules:
            # If manual_mapping strategy, only return override-based modules
            if strategy == "manual_mapping":
                return modules
            # For other strategies, merge overrides into results
            return _merge_with_overrides(
                modules,
                module_overrides,
                ignore_patterns,
                extensions,
                anchor_filenames,
                build_module_func,
            )

    # Route to appropriate strategy
    if strategy == "directory":
        return _discover_by_directory(
            root, ignore_patterns, extensions, anchor_filenames, build_module_func
        )
    elif strategy == "manual_mapping":
        # No overrides provided - fall back to manifest/init
        return _discover_by_init(
            root, ignore_patterns, extensions, anchor_filenames, build_module_func
        )
    elif strategy == "init":
        return _discover_by_init(
            root, ignore_patterns, extensions, anchor_filenames, build_module_func
        )
    else:
        # Default: manifest strategy
        return _discover_by_manifest_and_init(
            root, ignore_patterns, extensions, anchor_filenames, build_module_func
        )


def _discover_by_manifest_and_init(
    root: Path,
    ignore_patterns: Set[str],
    extensions: Set[str],
    anchor_filenames: Set[str],
    build_module_func: Optional[callable] = None,
) -> List["Module"]:
    """Discover modules using manifest.json and __init__.py (default strategy)."""
    from src.discovery.fragment_parser import Module

    modules: List[Module] = []
    seen_dirs: Set[Path] = set()

    # 1. manifest.json = official module (strongest anchor)
    for manifest_path in root.rglob("manifest.json"):
        if is_ignored(manifest_path, ignore_patterns):
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
        if build_module_func:
            modules.append(
                build_module_func(
                    mod_dir, anchor_type="manifest", manifest=manifest_data
                )
            )
        else:
            modules.append(
                Module(
                    name=mod_dir.name,
                    path=mod_dir,
                    anchor_type="manifest",
                    files=(),
                    manifest=manifest_data,
                    neighbors=(),
                )
            )

    # 2. __init__.py = package anchor (only if not already covered by manifest)
    for init_path in root.rglob("__init__.py"):
        if is_ignored(init_path, ignore_patterns):
            continue
        mod_dir = init_path.parent
        if mod_dir in seen_dirs:
            continue
        seen_dirs.add(mod_dir)
        if build_module_func:
            modules.append(build_module_func(mod_dir, anchor_type="init"))
        else:
            modules.append(
                Module(
                    name=mod_dir.name,
                    path=mod_dir,
                    anchor_type="init",
                    files=(),
                    manifest={},
                    neighbors=(),
                )
            )

    return modules


def _discover_by_init(
    root: Path,
    ignore_patterns: Set[str],
    extensions: Set[str],
    anchor_filenames: Set[str],
    build_module_func: Optional[callable] = None,
) -> List["Module"]:
    """Discover modules using __init__.py files only."""
    from src.discovery.fragment_parser import Module

    modules: List[Module] = []
    seen_dirs: Set[Path] = set()

    for init_path in root.rglob("__init__.py"):
        if is_ignored(init_path, ignore_patterns):
            continue
        mod_dir = init_path.parent
        if mod_dir in seen_dirs:
            continue
        seen_dirs.add(mod_dir)
        if build_module_func:
            modules.append(build_module_func(mod_dir, anchor_type="init"))
        else:
            modules.append(
                Module(
                    name=mod_dir.name,
                    path=mod_dir,
                    anchor_type="init",
                    files=(),
                    manifest={},
                    neighbors=(),
                )
            )

    return modules


def _discover_by_directory(
    root: Path,
    ignore_patterns: Set[str],
    extensions: Set[str],
    anchor_filenames: Set[str],
    build_module_func: Optional[callable] = None,
) -> List["Module"]:
    """Discover modules based on directory structure.

    Finds all directories containing __init__.py files, treating each
    as a module. Similar to _discover_by_init but the intent is different
    (directory structure-based vs package-based).
    """
    from src.discovery.fragment_parser import Module

    modules: List[Module] = []
    seen_dirs: Set[Path] = set()

    # Find all directories with __init__.py
    for init_path in root.rglob("__init__.py"):
        if is_ignored(init_path, ignore_patterns):
            continue
        mod_dir = init_path.parent
        if mod_dir in seen_dirs:
            continue
        seen_dirs.add(mod_dir)
        if build_module_func:
            modules.append(build_module_func(mod_dir, anchor_type="directory"))
        else:
            modules.append(
                Module(
                    name=mod_dir.name,
                    path=mod_dir,
                    anchor_type="directory",
                    files=(),
                    manifest={},
                    neighbors=(),
                )
            )

    return modules


def _discover_with_overrides(
    root: Path,
    module_overrides: Dict[str, Dict[str, Any]],
    ignore_patterns: Set[str],
    extensions: Set[str],
    anchor_filenames: Set[str],
    build_module_func: Optional[callable] = None,
) -> List["Module"]:
    """Discover modules based on explicit module_overrides configuration."""
    from src.discovery.fragment_parser import Module

    modules: List[Module] = []

    for module_name, override_config in module_overrides.items():
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

        if build_module_func:
            modules.append(
                build_module_func(
                    mod_dir, anchor_type=anchor_type, manifest=manifest_data
                )
            )
        else:
            modules.append(
                Module(
                    name=mod_dir.name,
                    path=mod_dir,
                    anchor_type=anchor_type,
                    files=(),
                    manifest=manifest_data,
                    neighbors=(),
                )
            )

    return modules


def _merge_with_overrides(
    discovered_modules: List["Module"],
    module_overrides: Dict[str, Dict[str, Any]],
    ignore_patterns: Set[str],
    extensions: Set[str],
    anchor_filenames: Set[str],
    build_module_func: Optional[callable] = None,
) -> List["Module"]:
    """Merge discovered modules with module_overrides configuration.

    Removes modules that are disabled in overrides, and adds any modules
    defined exclusively in overrides.
    """
    from src.discovery.fragment_parser import Module  # noqa: F401

    if not module_overrides:
        return discovered_modules

    result: List[Module] = []
    seen_names: Set[str] = set()

    # First, add override-defined modules
    for module_name, override_config in module_overrides.items():
        if not override_config.get("enabled", True):
            continue

        module_path = override_config.get("path")
        if module_path:
            # This module is defined in overrides - add it if not already discovered
            if module_name not in {m.name for m in discovered_modules}:
                mod_dir = override_config.get("path")
                if mod_dir:
                    continue
        seen_names.add(module_name)

    # Then, add discovered modules that are not disabled
    for mod in discovered_modules:
        override = module_overrides.get(mod.name)
        if override is not None:
            if not override.get("enabled", True):
                logger.debug("Module %s disabled via override, skipping", mod.name)
                continue
        result.append(mod)

    return result


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def is_ignored(p: Path, ignore_patterns: Set[str]) -> bool:
    """Check if a path should be ignored based on ignore patterns.

    Args:
        p: Path to check
        ignore_patterns: Set of patterns to ignore

    Returns:
        True if the path should be ignored
    """
    return any(ig in p.parts for ig in ignore_patterns)


def find_readme(start: Path, repo_root: Path) -> Optional[Path]:
    """Walk up from *start*'s parent to repo_root looking for a README file.

    The start directory itself is already scanned by _build_module, so we
    begin one level above to avoid re-finding the same (absent) README.
    Stops at repo_root (inclusive) or when leaving it.

    Args:
        start: Starting directory to search from
        repo_root: Root directory of the repository

    Returns:
        Path to README file if found, None otherwise
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


def find_governance_files(repo_root: Path) -> List[Path]:
    """Return governance files present directly at *repo_root*.

    Only the repository root is checked — governance rules at subdirectory
    level would be component-specific and would need a separate mechanism.
    Files returned in deterministic (sorted) order.

    Args:
        repo_root: Root directory of the repository

    Returns:
        List of governance file paths
    """
    found: List[Path] = []
    for name in sorted(GOVERNANCE_FILENAMES):
        candidate = repo_root / name
        if candidate.is_file():
            found.append(candidate)
    return found


def find_test(
    logic_file: Path,
    repo_root: Path,
    size_limit: int,
    min_size: int = MIN_SIZE,
) -> Optional[Path]:
    """Find the best test file for a logic .py file.

    Priority:
    1. Namespace mirror: repo_root/tests/<relative_parent>/test_<name>
    2. Component test dir: repo_root/tests/components/<component>/test_<name>
    2b. Any test_*.py in the same component test dir (largest)
    3. Scored rglob with score >= 2
    Returns None if nothing qualifies.

    Args:
        logic_file: Path to the logic file
        repo_root: Root directory of the repository
        size_limit: Maximum file size to consider
        min_size: Minimum file size to consider

    Returns:
        Path to best matching test file, or None
    """
    if logic_file.suffix != ".py":
        return None

    if logic_file.name == "__init__.py":
        test_name = "test_init.py"
    else:
        test_name = f"test_{logic_file.name}"

    def _ok(p: Path) -> bool:
        return p.is_file() and min_size <= p.stat().st_size <= size_limit

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
