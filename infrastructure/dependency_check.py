#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# AEGF (Architect-Expert-Gap-Forge)
# Copyright (c) 2026
# SPDX-License-Identifier: Apache-2.0
#
# Dependency compatibility validation script.
# Parses requirements.txt, verifies imports, checks pip conflicts.
# Exit code 0 = all checks pass, 1 = any failure.

from __future__ import annotations

import logging
import re
import subprocess
import sys
from dataclasses import dataclass, field
from importlib.util import find_spec
from pathlib import Path
from types import ModuleType  # type: ignore[assignment]  # ModuleType, not Module
from typing import NoReturn

__all__: list[str] = []

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ImportResult:
    """Result of verifying whether a module can be imported.

    Attributes:
        package: Nombre del paquete en requirements.txt (e.g. "dspy").
        module: Nombre del m&#243;dulo para import-check (e.g. "dspy" or "langchain_core").
        found: True si el m&#243;dulo est&#225; disponible.
        spec: El ModuleSpec retornado por find_spec, o None si no se encontr&#243;.
    """

    package: str
    module: str
    found: bool
    spec: ModuleType | None = None  # type: ignore[assignment]


@dataclass(frozen=True)
class CheckResult:
    """Consolidated result of a verification check.

    Attributes:
        ok: True si no hay fallos.
        failures: Lista de descripciones de fallos.
    """

    ok: bool
    failures: list[str] = field(default_factory=list)

    @classmethod
    def ok_result(cls) -> CheckResult:
        """Return a successful CheckResult with no failures."""
        return cls(ok=True, failures=[])

    def add_failure(self, msg: str) -> CheckResult:
        """Add a failure and return a new CheckResult (immutability)."""
        return CheckResult(ok=False, failures=self.failures + [msg])


# Mapping of package name (requirements.txt) to Python module name(s).
# If a package is not here, package_name == module_name is assumed.
PACKAGE_IMPORT_MAP: dict[str, tuple[str, ...]] = {
    "dspy": ("dspy",),
    "langgraph": ("langgraph", "langgraph.checkpoint.memory"),
    "langgraph-prebuilt": ("langgraph_prebuilt",),
    "langchain-core": ("langchain_core",),
    "google-genai": ("google_genai", "google.genai"),
    "huggingface-hub": ("huggingface_hub",),
    "python-dotenv": ("dotenv",),
    "pydantic": ("pydantic",),
    "pyyaml": ("yaml",),
    "pytest-cov": ("coverage",),
    "psutil": ("psutil",),
    "openai": ("openai",),
    "numpy": ("numpy",),
    "datasets": ("datasets",),
    "tiktoken": ("tiktoken",),
    "httpx": ("httpx",),
    "click": ("click",),
    "tqdm": ("tqdm",),
    "requests": ("requests",),
    "packaging": ("packaging",),
    "fsspec": ("fsspec",),
}

# Packages that are optional and should be skipped if not installed.
# These are declared in requirements.txt but are not required for core functionality.
OPTIONAL_PACKAGES: frozenset[str] = frozenset(("google-genai",))


def parse_requirements(path: Path) -> list[str]:
    """Extract package names from a requirements.txt file.

    Parses each line with regex, ignoring comments, includes (-r),
    options (--index-url), and blank lines. Package names are returned
    without versions (only the canonical name).

    Args:
        path: Path to the requirements.txt file.

    Returns:
        List of package names in lowercase canonical form.

    Raises:
        FileNotFoundError: If the file does not exist.
        PermissionError: If the file cannot be read.
    """
    pattern = re.compile(
        r"^([a-zA-Z0-9_][a-zA-Z0-9._-]*)"  # package name (PEP 503-ish)
        r"(?:[><=!~].*)?"  # optional version spec
        r"\s*$"  # optional whitespace
    )
    lines = path.read_text(encoding="utf-8").splitlines()
    packages: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("-"):
            continue
        match = pattern.match(stripped)
        if match:
            packages.append(match.group(1).lower())
    return packages


def _resolve_module(package_name: str) -> tuple[str, ...]:
    """Resolve module name(s) for a package.

    Args:
        package_name: Canonical package name (e.g. "dspy", "huggingface-hub").

    Returns:
        Tuple of module names to verify. Falls back to (package_name,) if
        the package is not in PACKAGE_IMPORT_MAP.
    """
    return PACKAGE_IMPORT_MAP.get(package_name, (package_name,))


def check_imports(packages: list[str]) -> CheckResult:
    """Verify that each package from requirements.txt can be imported.

    For each package, attempts find_spec for each mapped module.
    Does NOT execute imports -- only checks module existence.

    Args:
        packages: List of package names from parse_requirements().

    Returns:
        CheckResult with failure details (if any).
    """
    failures: list[str] = []

    for package in packages:
        if package in OPTIONAL_PACKAGES:
            logger.info("Skipping optional package: %s", package)
            continue
        modules = _resolve_module(package)
        for module_name in modules:
            spec = find_spec(module_name)
            if spec is None:
                failures.append(
                    f"import not found: module '{module_name}' "
                    f"(package: '{package}')"
                )

    return CheckResult(ok=len(failures) == 0, failures=failures)


def check_pip_conflicts() -> CheckResult:
    """Verify version conflicts with `pip check`.

    Runs `python -m pip check` in the current environment. If pip reports
    conflicts, parses the output to build a CheckResult with descriptive
    failure messages.

    Returns:
        CheckResult.ok=True if no conflicts, CheckResult.ok=False with
        list of conflict messages.
    """
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pip", "check"],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except FileNotFoundError:
        return CheckResult(
            ok=False,
            failures=["pip not found in the environment"],
        )
    except subprocess.TimeoutExpired:
        return CheckResult(
            ok=False,
            failures=["pip check exceeded timeout (120s)"],
        )

    if proc.returncode != 0:
        errors: list[str] = []
        for line in proc.stderr.splitlines() + proc.stdout.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                errors.append(stripped)
        return CheckResult(ok=False, failures=errors)

    return CheckResult.ok_result()


def _die(msg: str) -> NoReturn:
    """Print an error message to stderr and exit with code 1."""
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def main(argv: list[str] | None = None) -> int:
    """Main entry point. Configures logging and runs checks.

    Args:
        argv: Command-line arguments (for testing). Unused currently.

    Returns:
        0 if all checks pass, 1 if any fail.
    """
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        level=logging.INFO,
    )

    project_root = Path(__file__).resolve().parent.parent
    requirements_path = project_root / "requirements.txt"

    logger.info("Starting dependency verification")

    # 1. Parse requirements.txt
    try:
        packages = parse_requirements(requirements_path)
    except (FileNotFoundError, PermissionError) as exc:
        logger.error("Could not read %s: %s", requirements_path, exc)
        _die(str(exc))

    logger.info("Packages found in requirements.txt: %d", len(packages))

    # 2. Check imports
    import_result = check_imports(packages)
    if not import_result.ok:
        logger.error("Import failures: %s", import_result.failures)
        for msg in import_result.failures:
            print(f"  FAIL: {msg}", file=sys.stderr)
        return 1

    logger.info("All imports verified successfully")

    # 3. Check pip conflicts
    pip_result = check_pip_conflicts()
    if not pip_result.ok:
        logger.error("Pip conflicts: %s", pip_result.failures)
        for msg in pip_result.failures:
            print(f"  FAIL: {msg}", file=sys.stderr)
        return 1

    logger.info("No version conflicts detected")
    print("OK: All dependency checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
