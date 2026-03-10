# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Python AST-based extractor adapter.

This adapter uses Python's built-in ast module to parse Python source files
and extract dependencies. It preserves the behavior of the original
processor._extract_local_imports method while providing a clean interface
through the ExtractorAdapter protocol.
"""

from __future__ import annotations

import ast
import logging
import re
import sys
from pathlib import Path
from typing import Any, List, Set

from src.utils.extractors.base import (
    Dependency,
    ExtractorAdapter,
    ParseError,
    ParseResult,
)

logger = logging.getLogger(__name__)

# Standard library modules - use sys.stdlib_module_names if available (Python 3.11+)
# Otherwise fall back to a curated set of common stdlib modules
if hasattr(sys, "stdlib_module_names"):
    STDLIB_MODULES: Set[str] = set(sys.stdlib_module_names)
else:
    # Curated set of common stdlib modules (Python 3.10 and earlier)
    STDLIB_MODULES = {
        "os",
        "sys",
        "re",
        "json",
        "math",
        "random",
        "datetime",
        "time",
        "collections",
        "itertools",
        "functools",
        "operator",
        "pathlib",
        "typing",
        "abc",
        "copy",
        "io",
        "pickle",
        "shelve",
        "sqlite3",
        "csv",
        "configparser",
        "logging",
        "warnings",
        "threading",
        "multiprocessing",
        "asyncio",
        "subprocess",
        "socket",
        "ssl",
        "email",
        "html",
        "xml",
        "urllib",
        "http",
        "ftplib",
        "smtplib",
        "argparse",
        "optparse",
        "getopt",
        "tempfile",
        "shutil",
        "glob",
        "fnmatch",
        "linecache",
        "tokenize",
        "keyword",
        "ast",
        "dis",
        "inspect",
        "traceback",
        "gc",
        "weakref",
        "types",
        "contextlib",
        "dataclasses",
        "enum",
        "graphlib",
        "pprint",
        "textwrap",
        "unittest",
        "doctest",
        "zipfile",
        "tarfile",
        "gzip",
        "bz2",
        "lzma",
        "zipimport",
        "venv",
        "ensurepip",
        "pkgutil",
        "modulefinder",
        "runpy",
        "code",
        "codeop",
        "fcntl",
        "select",
        "signal",
        "mmap",
        "msvcrt",
        "nt",
        "termios",
        "tty",
        "pty",
        "poll",
        "epoll",
        "stat",
        "statvfs",
        "platform",
        "errno",
        "ctypes",
        "os.path",
        "string",
        "struct",
        "codecs",
        "locale",
        "gettext",
        "parser",
        "symbol",
        "compiler",
    }

# Relative import regex pattern (fallback for syntax errors)
RELATIVE_IMPORT_PATTERN = re.compile(r"from\s+(\.[.\w]*)\s+import")


class PythonAstAdapter:
    """Adapter for parsing Python source files using the ast module.

    This adapter provides:
    - AST-based parsing for valid Python files
    - Dependency extraction (stdlib, external, relative)
    - ParseError-first behavior: raises ParseError on syntax errors by default

    NOTE: The _extract_with_regex() method is a fallback mechanism that is ONLY
    invoked when the processor's on_parse_error policy is set to FALLBACK.
    By default (policy=ABORT), this method is never called.
    """

    def parse_file(self, file_path: Path) -> ParseResult:
        """Parse a Python file and return its content and AST.

        Args:
            file_path: Path to the Python file to parse.

        Returns:
            ParseResult containing parsed content and AST tree.

        Raises:
            ParseError: If the file cannot be parsed.
        """
        try:
            raw_content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            raise ParseError(
                file_path=file_path,
                line=1,
                message=f"Failed to read file: {str(e)}",
            )

        try:
            ast_tree = ast.parse(raw_content, filename=str(file_path))
        except SyntaxError as e:
            raise ParseError(
                file_path=file_path,
                line=e.lineno or 1,
                message=f"Syntax error: {e.msg}",
            )
        except Exception as e:
            raise ParseError(
                file_path=file_path,
                line=1,
                message=f"Failed to parse AST: {str(e)}",
            )

        return ParseResult(
            file_path=file_path,
            ast_tree=ast_tree,
            raw_content=raw_content,
            dependencies=tuple(self._extract_from_ast(ast_tree, raw_content)),
        )

    def extract_dependencies(self, file_path: Path) -> List[Dependency]:
        """Extract dependencies from a Python file.

        This method calls parse_file which enforces ParseError-first policy.
        ParseError propagates to the caller (processor) which handles it
        according to the on_parse_error policy.

        Args:
            file_path: Path to the Python file to analyze.

        Returns:
            List of Dependency objects found in the file.

        Raises:
            ParseError: If the file cannot be parsed.
        """
        # ParseError-first: let parse_file raise ParseError up to the caller
        result = self.parse_file(file_path)
        return list(result.dependencies)

    def _extract_from_ast(self, tree: ast.AST, raw_content: str) -> List[Dependency]:
        """Extract dependencies from an AST tree.

        Args:
            tree: Parsed AST tree.
            raw_content: Raw file content for fallback extraction.

        Returns:
            List of Dependency objects.
        """
        dependencies: List[Dependency] = []
        seen: Set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name.split(".")[0]
                    if name not in seen:
                        seen.add(name)
                        dependencies.append(
                            Dependency(
                                name=name,
                                module_type=self._classify_module(name),
                            )
                        )

            elif isinstance(node, ast.ImportFrom):
                if node.level and node.level > 0:
                    # Relative import
                    module = node.module or ""
                    source = f"from {node.level * '.'}{module} import {', '.join(n.name for n in node.names)}"
                    name = module.split(".")[-1] if module else node.names[0].name
                    if name not in seen:
                        seen.add(name)
                        dependencies.append(
                            Dependency(
                                name=name,
                                module_type="relative",
                                source_module=source,
                            )
                        )
                elif node.module:
                    # Absolute import
                    name = node.module.split(".")[0]
                    if name not in seen:
                        seen.add(name)
                        dependencies.append(
                            Dependency(
                                name=name,
                                module_type=self._classify_module(name),
                            )
                        )

        return dependencies

    def _extract_with_regex(self, file_path: Path) -> List[Dependency]:
        """Fallback regex-based extraction for files with parse errors.

        WARNING: This method is only invoked when the processor's on_parse_error
        policy is set to FALLBACK. It is NOT called by default.

        This mimics the original processor._extract_local_imports fallback.

        Args:
            file_path: Path to the file.

        Returns:
            List of Dependency objects extracted via regex.
        """
        dependencies: List[Dependency] = []
        seen: Set[str] = set()

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return dependencies  # Return empty if we can't read the file

        # Extract relative imports using regex

        # Extract regex
        for match in RELATIVE_IMPORT_PATTERN.finditer(content):
            raw = match.group(1).lstrip(".")
            if raw:
                name = raw.split(".")[-1]
                source = match.group(0)
                if name not in seen:
                    seen.add(name)
                    dependencies.append(
                        Dependency(
                            name=name + ".py",
                            module_type="relative",
                            source_module=source,
                        )
                    )

        # Simple import regex
        import_pattern = re.compile(r"^import\s+([\w.]+)", re.MULTILINE)
        for match in import_pattern.finditer(content):
            name = match.group(1).split(".")[0]
            if name not in seen:
                seen.add(name)
                dependencies.append(
                    Dependency(
                        name=name,
                        module_type=self._classify_module(name),
                    )
                )

        return dependencies

    @staticmethod
    def _classify_module(name: str) -> str:
        """Classify a module as stdlib or external.

        Args:
            name: Module name to classify.

        Returns:
            "stdlib" if it's a known standard library module,
            "external" otherwise.
        """
        # Check for common third-party modules
        common_external = {
            "requests",
            "numpy",
            "pandas",
            "django",
            "flask",
            "fastapi",
            "sqlalchemy",
            "pytest",
            "pydantic",
            "dotenv",
            "tqdm",
            "yaml",
            "aiohttp",
            "httpx",
            "cryptography",
            "PIL",
            "pillow",
            "torch",
            "tensorflow",
            "sklearn",
            "scipy",
            "matplotlib",
            "seaborn",
            "plotly",
            "streamlit",
            "gradio",
            "transformers",
            "datasets",
        }

        if name in common_external:
            return "external"
        if name in STDLIB_MODULES:
            return "stdlib"
        return "external"  # Default to external if unknown
