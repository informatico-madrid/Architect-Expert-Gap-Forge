# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Fragment Parser Module
=====================
Provides data classes and parsing functions for module files.
Handles AST/text parsing, file classification, and import extraction.

Author: Joao Maria Arranz Aparicio
"""

from __future__ import annotations

import ast
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Import constants from file_scanner
from src.discovery.file_scanner import (
    ANCHOR_FILENAMES,
    GOVERNANCE_FILENAMES,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class ModuleFile:
    """A single file within a discovered module.

    Note: Uses frozen=True but content is set after creation via object.__setattr__
    to support lazy loading pattern. This is an explicit lifecycle pattern where
    content is loaded on-demand during processing.
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
    anchor_type: str = ""
    files: Tuple[ModuleFile, ...] = ()
    manifest: Dict[str, Any] = field(default_factory=dict)
    neighbors: Tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# File Classification Functions
# ---------------------------------------------------------------------------


def classify_role(f: Path) -> str:
    """Determine the semantic role of a file.

    Args:
        f: Path to the file

    Returns:
        Role string: readme, governance, anchor, test, or implementation
    """
    name = f.name.lower()
    if name in ("readme.md", "readme.rst", "readme.txt"):
        return "readme"
    if f.name in GOVERNANCE_FILENAMES or name in GOVERNANCE_FILENAMES:
        return "governance"
    if name in ANCHOR_FILENAMES or f.suffix in (".json", ".yaml", ".yml"):
        return "anchor"
    # __init__.py is a package anchor (Python modules)
    if name == "__init__.py":
        return "anchor"
    if "test" in name:
        return "test"
    if name in ("setup.py", "setup.cfg", "pyproject.toml"):
        return "anchor"
    return "implementation"


# ---------------------------------------------------------------------------
# Import Extraction Functions
# ---------------------------------------------------------------------------


def extract_local_imports(code: str) -> List[str]:
    """Extract relative imports as concrete filename.py references.

    ``from .const import X`` → ``const.py``
    ``from .webrtc.helpers import Y`` → ``helpers.py``
    Duplicates are suppressed.

    Args:
        code: Python source code to parse

    Returns:
        List of local import filenames
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


# ---------------------------------------------------------------------------
# Module Builder Functions
# ---------------------------------------------------------------------------


def build_module(
    mod_dir: Path,
    anchor_type: str,
    extensions: set,
    ignore_patterns: set,
    manifest: Optional[Dict[str, Any]] = None,
) -> Module:
    """Scan the directory of a discovered module and return an immutable Module record.

    Args:
        mod_dir: Directory containing the module
        anchor_type: Type of anchor used for discovery
        extensions: Set of file extensions to consider
        ignore_patterns: Patterns to ignore
        manifest: Optional manifest data

    Returns:
        Module instance
    """
    from src.discovery.file_scanner import is_ignored

    files_list: List[ModuleFile] = []
    all_names: List[str] = []
    for f in sorted(mod_dir.iterdir()):
        if f.is_file() and f.suffix in (extensions | {".json", ".yaml", ".yml"}):
            if is_ignored(f, ignore_patterns):
                continue
            all_names.append(f.name)
            files_list.append(
                ModuleFile(
                    path=f,
                    role=classify_role(f),
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


def make_arch_header(
    mod: Module,
    mf: ModuleFile,
    local_imports: List[str],
    ftype: str,
    repo_prefix: str = "",
    dependencies: Optional[List[str]] = None,
) -> str:
    """Build the [ARCH_HEADER] block for a bundle.

    Args:
        mod: Module instance
        mf: ModuleFile instance
        local_imports: List of local imports
        ftype: Fragment type
        repo_prefix: Repository prefix
        dependencies: Optional list of dependencies

    Returns:
        Formatted arch header string
    """
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
