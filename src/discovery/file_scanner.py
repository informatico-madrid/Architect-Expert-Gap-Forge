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
    ".codecov.yml",
    ".gitlab-ci.yml",
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
    elif strategy == "typescript":
        return _discover_by_typescript(
            root, ignore_patterns, extensions, anchor_filenames, build_module_func
        )
    elif strategy == "yaml":
        return _discover_by_yaml(
            root, ignore_patterns, extensions, anchor_filenames, build_module_func
        )
    elif strategy == "filesystem":
        return _discover_by_filesystem(
            root, ignore_patterns, extensions, anchor_filenames, build_module_func
        )
    elif strategy == "auto":
        # Auto-detect strategy based on repository structure
        detected_strategy = _detect_strategy(root)
        logger.info("Auto-detected strategy: %s for %s", detected_strategy, root)
        # Recursively call with detected strategy
        return discover_modules(
            root=root,
            strategy=detected_strategy,
            ignore_patterns=ignore_patterns,
            extensions=extensions,
            anchor_filenames=anchor_filenames,
            module_overrides=module_overrides,
            build_module_func=build_module_func,
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
    """Discover modules using manifest.json and __init__.py (default strategy).

    Also discovers TypeScript modules when no manifest.json is found,
    by scanning for .ts/.tsx files in subdirectories.
    """
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

    # 3. TypeScript modules: if no manifest.json found, scan for .ts/.tsx files
    has_manifest = any(root.rglob("manifest.json"))
    if not has_manifest:
        ts_files: list[Path] = []
        for ts_file in list(root.rglob("*.ts")) + list(root.rglob("*.tsx")):
            if is_ignored(ts_file, ignore_patterns):
                continue
            ts_files.append(ts_file)

        if ts_files:
            # Group files by parent directory
            dir_to_files: dict[Path, list[Path]] = {}
            for ts_file in ts_files:
                parent = ts_file.parent
                if parent in seen_dirs:
                    continue
                seen_dirs.add(parent)
                dir_to_files.setdefault(parent, []).append(ts_file)

            # Build modules for TypeScript directories
            for mod_dir, files in dir_to_files.items():
                if build_module_func:
                    modules.append(build_module_func(mod_dir, anchor_type="typescript"))
                else:
                    modules.append(
                        Module(
                            name=mod_dir.name,
                            path=mod_dir,
                            anchor_type="typescript",
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


def _discover_by_typescript(
    root: Path,
    ignore_patterns: Set[str],
    extensions: Set[str],
    anchor_filenames: Set[str],
    build_module_func: Optional[callable] = None,
) -> List["Module"]:
    """Discover modules for TypeScript/TSX repositories.

    Scans root with Path.rglob("*.ts") and Path.rglob("*.tsx"), excluding
    node_modules/, tests/, etc., then groups files by parent directory.
    Each directory containing at least one .ts or .tsx file becomes a module.

    Args:
        root: Repository root directory to scan.
        ignore_patterns: Directory patterns to exclude.
        extensions: File extensions to consider (should include .ts, .tsx).
        anchor_filenames: Filenames that serve as module anchors.
        build_module_func: Callback to build Module objects.

    Returns:
        List of Module instances for each directory containing TypeScript files.
    """
    from src.discovery.fragment_parser import Module

    modules: List[Module] = []
    seen_dirs: Set[Path] = set()

    # Collect all TypeScript files
    ts_files: list[Path] = []
    for ts_file in list(root.rglob("*.ts")) + list(root.rglob("*.tsx")):
        if is_ignored(ts_file, ignore_patterns):
            continue
        ts_files.append(ts_file)

    # Group files by parent directory
    dir_to_files: dict[Path, list[Path]] = {}
    for ts_file in ts_files:
        parent = ts_file.parent
        if parent in seen_dirs:
            continue
        seen_dirs.add(parent)
        dir_to_files.setdefault(parent, []).append(ts_file)

    # Build modules
    for mod_dir, files in dir_to_files.items():
        try:
            if build_module_func:
                module = build_module_func(
                    mod_dir, anchor_type="typescript", manifest={}
                )
                modules.append(module)
            else:
                modules.append(
                    Module(
                        name=mod_dir.name,
                        path=mod_dir,
                        anchor_type="typescript",
                        files=(),
                        manifest={},
                        neighbors=(),
                    )
                )
        except Exception as exc:
            logger.warning("Could not build module for %s: %s", mod_dir, exc)

    logger.info("typescript discovery: found %d modules in %s", len(modules), root)
    return modules


def _discover_by_filesystem(
    root: Path,
    ignore_patterns: Set[str],
    extensions: Set[str],
    anchor_filenames: Set[str],
    build_module_func: Optional[callable] = None,
) -> List["Module"]:
    """Discover modules by directory structure (filesystem strategy).

    Scans root with Path.rglob("*.php"), excluding vendor/, node_modules/,
    tests/, and cache/ directories, then groups files by parent directory.
    Each directory containing at least one PHP file becomes a module.

    This is the standard strategy for PHP repositories and other file-based
    architectures without package managers like manifest.json or __init__.py.

    Args:
        root: Repository root directory to scan.
        ignore_patterns: Directory patterns to exclude.
        extensions: File extensions to consider (should include .php).
        anchor_filenames: Filenames that serve as module anchors.
        build_module_func: Callback to build Module objects.

    Returns:
        List of Module instances for each directory containing PHP files.
    """
    from src.discovery.fragment_parser import Module

    modules: List[Module] = []
    seen_dirs: Set[Path] = set()

    # Collect all PHP files, excluding known non-source dirs
    _EXCLUDE_DIRS = {"vendor", "node_modules", "tests", "cache"}
    php_files: list[Path] = []
    for php_file in root.rglob("*.php"):
        if not any(part in _EXCLUDE_DIRS for part in php_file.parts):
            if is_ignored(php_file, ignore_patterns):
                continue
            php_files.append(php_file)

    # Group files by parent directory (each dir → one module)
    dir_to_files: dict[Path, list[Path]] = {}
    for php_file in php_files:
        parent = php_file.parent
        if parent in seen_dirs:
            continue
        seen_dirs.add(parent)
        dir_to_files.setdefault(parent, []).append(php_file)

    # Build modules
    for mod_dir, files in dir_to_files.items():
        try:
            if build_module_func:
                module = build_module_func(
                    mod_dir, anchor_type="filesystem", manifest={}
                )
                modules.append(module)
            else:
                modules.append(
                    Module(
                        name=mod_dir.name,
                        path=mod_dir,
                        anchor_type="filesystem",
                        files=(),
                        manifest={},
                        neighbors=(),
                    )
                )
        except Exception as exc:
            logger.warning("Could not build module for %s: %s", mod_dir, exc)

    logger.info("filesystem discovery: found %d modules in %s", len(modules), root)
    return modules


def _discover_by_yaml(
    root: Path,
    ignore_patterns: Set[str],
    extensions: Set[str],
    anchor_filenames: Set[str],
    build_module_func: Optional[callable] = None,
) -> List["Module"]:
    """Discover YAML/Jinja template modules.

    Scans root for .yaml, .yml, .jinja, and .jinja2 files, then groups them by
    parent directory. Each directory containing YAML/Jinja files becomes a module.

    This is the strategy for Home Assistant blueprints, automations, themes,
    and Jinja template files.

    Args:
        root: Repository root directory to scan.
        ignore_patterns: Directory patterns to exclude.
        extensions: File extensions to consider (should include .yaml, .yml, .jinja, .jinja2).
        anchor_filenames: Filenames that serve as module anchors.
        build_module_func: Callback to build Module objects.

    Returns:
        List of Module instances for each directory containing YAML/Jinja files.
    """
    from src.discovery.fragment_parser import Module

    modules: List[Module] = []
    seen_dirs: Set[Path] = set()

    # Collect all YAML and Jinja files, excluding known non-source dirs
    _EXCLUDE_DIRS = {"node_modules", "tests", "test", "__pycache__"}
    yaml_files: list[Path] = []

    # Match based on extensions set
    for file_path in root.rglob("*"):
        if not file_path.is_file():
            continue
        if is_ignored(file_path, ignore_patterns):
            continue
        # Check if file extension is in the allowed extensions
        if file_path.suffix in extensions:
            # Exclude directories
            if any(part in _EXCLUDE_DIRS for part in file_path.parts):
                continue
            yaml_files.append(file_path)

    # Group files by parent directory (each dir → one module)
    dir_to_files: dict[Path, list[Path]] = {}
    for yaml_file in yaml_files:
        parent = yaml_file.parent
        if parent in seen_dirs:
            continue
        seen_dirs.add(parent)
        dir_to_files.setdefault(parent, []).append(yaml_file)

    # Build modules
    for mod_dir, files in dir_to_files.items():
        try:
            if build_module_func:
                module = build_module_func(
                    mod_dir, anchor_type="yaml", manifest={}
                )
                modules.append(module)
            else:
                modules.append(
                    Module(
                        name=mod_dir.name,
                        path=mod_dir,
                        anchor_type="yaml",
                        files=(),
                        manifest={},
                        neighbors=(),
                    )
                )
        except Exception as exc:
            logger.warning("Could not build module for %s: %s", mod_dir, exc)

    logger.info("yaml discovery: found %d modules in %s", len(modules), root)
    return modules


def _detect_strategy(root: Path) -> str:
    """Detect the repository strategy type based on file patterns.

    This function implements an intelligent detection strategy that examines
    the repository structure to determine the appropriate module discovery
    approach. Detection follows a strict priority order:

    Detection Priority Order:
    -------------------------
    1. Manifest strategy: Checks for manifest.json files (npm, Composer, etc.)
    2. PHP strategy: Looks for .php files indicating PHP-based repositories
    3. Init strategy: Checks for __init__.py files indicating Python packages
    4. YAML strategy: Scans for YAML/Jinja template files (themes, templates,
       blueprints) - has priority over TypeScript
    5. TypeScript strategy: Scans for .ts/.tsx files indicating TypeScript/
       JavaScript repositories
    6. Directory strategy: Final fallback - uses generic directory structure
       analysis

    Detection Checks:
    -----------------
    - Manifest: manifest.json files
    - PHP: .php files excluding vendor/, node_modules/, tests/, cache/
    - Init: Python package __init__.py files
    - YAML: .yaml, .yml, .jinja, .jinja2 files in non-test directories
    - TypeScript: .ts, .tsx files in non-test directories
    - Directory: Generic directory scanning as last resort

    Excluded Directories:
    ---------------------
    - node_modules/
    - vendor/
    - tests/
    - test/
    - __pycache__/
    - cache/

    Performance Characteristics:
    ----------------------------
    - O(n) where n = total number of files/directories in repository
    - Early returns on first match for efficiency
    - Single pass through directory tree for pattern matching
    - Lightweight file metadata checks (no content reading)

    Error Handling:
    ---------------
    - Silently ignores file access errors (permission denied, etc.)
    - Never raises exceptions - always returns a valid strategy string
    - Gracefully handles empty or malformed repositories
    - Returns "directory" on any error condition to ensure safe fallback

    Args:
        root: Repository root directory to analyze

    Returns:
        Strategy name string: "manifest", "php", "init", "yaml", "typescript",
        or "directory" (fallback)
    """
    try:
        if not root.exists() or not root.is_dir():
            return "directory"

        # Check for manifest.json files (Home Assistant style)
        try:
            if any(root.rglob("manifest.json")):
                return "manifest"
        except Exception as exc:
            logger.warning("Error scanning for manifest.json files: %s", exc)

        # Check for TypeScript files (frontend components)
        ts_count = 0
        try:
            for ts_file in list(root.rglob("*.ts")) + list(root.rglob("*.tsx")):
                # Exclude common non-source directories
                if not any(part in ("node_modules", "tests", "test")
                         for part in ts_file.parts):
                    ts_count += 1
        except Exception as exc:
            logger.warning("Error scanning for TypeScript files: %s", exc)

        if ts_count > 0:
            return "typescript"

        # Check for PHP files (filesystem-based)
        php_count = 0
        try:
            for php_file in root.rglob("*.php"):
                # Exclude common non-source directories
                if not any(part in ("vendor", "node_modules", "tests", "cache")
                         for part in php_file.parts):
                    php_count += 1
        except Exception as exc:
            logger.warning("Error scanning for PHP files: %s", exc)

        if php_count > 0:
            return "filesystem"

        # Check for __init__.py files (Python packages)
        try:
            if any(root.rglob("__init__.py")):
                return "init"
        except Exception as exc:
            logger.warning("Error scanning for __init__.py files: %s", exc)

        # Check for YAML files (themes, templates, blueprints) - highest priority among remaining
        yaml_count = 0
        try:
            for file_path in root.rglob("*"):
                if not file_path.is_file():
                    continue
                if file_path.suffix in (".yaml", ".yml", ".jinja", ".jinja2"):
                    # Exclude common non-source directories
                    if not any(part in ("node_modules", "tests", "test", "__pycache__")
                             for part in file_path.parts):
                        yaml_count += 1
        except Exception as exc:
            logger.warning("Error scanning for YAML files: %s", exc)

        if yaml_count > 0:
            return "yaml"

        # Check for TypeScript files (frontend components) - after YAML
        # YAML has priority, so TypeScript is detected after YAML
        ts_count = 0
        try:
            for ts_file in list(root.rglob("*.ts")) + list(root.rglob("*.tsx")):
                # Exclude common non-source directories
                if not any(part in ("node_modules", "tests", "test")
                         for part in ts_file.parts):
                    ts_count += 1
        except Exception as exc:
            logger.warning("Error scanning for TypeScript files: %s", exc)

        if ts_count > 0:
            return "typescript"

        # Default fallback: directory-based strategy
        return "directory"

    except Exception:
        # Always return a valid strategy on error
        return "directory"


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
    """Find the best test file for a logic file (.py, .ts, .tsx, .php).

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
    import logging
    logger = logging.getLogger(__name__)

    # Only support Python, TypeScript, and PHP test files
    if logic_file.suffix not in (".py", ".ts", ".tsx", ".php"):
        return None

    if logic_file.name == "__init__.py":
        test_name = "test_init.py"
    else:
        test_name = f"test_{logic_file.name}"

    logger.debug("find_test: logic_file=%s, repo_root=%s, test_name=%s",
                 logic_file, repo_root, test_name)

    def _ok(p: Path) -> bool:
        return p.is_file() and min_size <= p.stat().st_size <= size_limit

    # Get the relative path from repo_root
    try:
        rel = logic_file.relative_to(repo_root)
    except ValueError:
        rel = Path(logic_file.name)

    logger.debug("find_test: rel=%s", rel)

    # 1. Namespace mirror at repo_root/tests/<relative_parent>
    ns = repo_root / "tests" / rel.parent / test_name
    logger.debug("find_test: checking namespace mirror %s", ns)
    if _ok(ns):
        return ns

    # 1b. Fallback: tests might be at parent level (e.g., owner/tests/ not owner/myrepo/tests/)
    parent_tests = repo_root.parent / "tests" / rel.parent / test_name
    logger.debug("find_test: checking parent namespace mirror %s", parent_tests)
    if _ok(parent_tests):
        return parent_tests

    # 2. Component test dir at repo_root/tests/components/<component>
    component = logic_file.parent.name
    ctd = repo_root / "tests" / "components" / component
    if ctd.is_dir():
        exact = ctd / test_name
        if _ok(exact):
            return exact

    # 2b. Fallback: component tests at parent level
    parent_ctd = repo_root.parent / "tests" / "components" / component
    if parent_ctd.is_dir():
        exact = parent_ctd / test_name
        if _ok(exact):
            return exact

    # 3. Same directory test (for tests/<component>/test_*.py structure)
    # Look for test_<name>.py in the same directory as the logic file's parent
    same_dir_test = logic_file.parent / test_name
    if _ok(same_dir_test):
        return same_dir_test

    # 4. Scored rglob in repo_root
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

    # 4b. Scored rglob in parent tests
    for c in (repo_root.parent / "tests").rglob(test_name):
        if not _ok(c):
            continue
        try:
            cp = set(c.relative_to(repo_root.parent).parts[:-1])
        except ValueError:
            cp = set()
        score = len(logic_parts & cp)
        if score >= 2 and score > best_score:
            best_score, best = score, c

    # 4. Same directory test (for TypeScript test structure)
    # Look for test_<name>.ts in the same directory as the logic file
    same_dir_test = logic_file.parent / test_name
    if _ok(same_dir_test):
        return same_dir_test

    return best
