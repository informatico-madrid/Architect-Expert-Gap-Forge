# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
PHP Legacy Adapter Module
========================
Provides the PhpLegacyAdapter class for extracting PHP fragments from legacy
PHP codebases (osCommerce, WordPress, ZenCart, etc.).

This adapter implements the ExtractorAdapter protocol and wraps a 3-stage
parallel pipeline for efficient processing of PHP repositories:
- Stage 1: ThreadPoolExecutor for IO reads
- Stage 2: ProcessPoolExecutor for CPU-bound fragmentation
- Stage 3: ThreadPoolExecutor for writes

Author: Joao Maria Arranz Aparicio
"""

from __future__ import annotations

import logging
import os
import re
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path
from typing import List, Optional

from src.utils.extractors.base import (
    Dependency,
    ParseError,
    ParseResult,
)

logger = logging.getLogger(__name__)


# Module-level worker function for ProcessPoolExecutor (must be picklable)
# This is defined at module level to ensure pickle compatibility
def _process_php_fragment_worker(args: tuple) -> dict:
    """
    Worker function for processing a single PHP file fragment.

    This function runs in a separate process and handles CPU-bound
    fragmentation work.

    Args:
        args: Tuple of (path_str, content, profile_name)

    Returns:
        Dict with fragment information or error details
    """
    path_str, content, profile_name = args

    # Import here to avoid import-time side effects and ensure picklability
    from src.discovery.php_fragmenter import process_php_file
    from pathlib import Path

    try:
        path = Path(path_str)
        fragments = process_php_file(path, content, profile_name)

        return {
            "success": True,
            "path": path_str,
            "fragments": [
                {
                    "name": f.name,
                    "fragment_type": f.fragment_type,
                    "raw_content": f.raw_content,
                    "legacy_action": f.legacy_action,
                    "preamble_ref": f.preamble_ref,
                    "dependencies": f.dependencies,
                    "platform_hints": f.platform_hints,
                    "signatures": f.signatures,  # Include signatures for LEGACY_SIGNATURES section
                }
                for f in fragments
            ],
        }
    except Exception as e:
        return {
            "success": False,
            "path": path_str,
            "error": str(e),
        }


class PhpLegacyAdapter:
    """Adapter for parsing legacy PHP files and extracting fragments.

    This adapter implements the ExtractorAdapter protocol and provides:
    - Single file parsing via parse_file()
    - Dependency extraction via extract_dependencies()
    - 3-stage parallel pipeline for batch repository processing:
      * Stage 1: ThreadPoolExecutor(max_workers=32) for IO reads
      * Stage 2: ProcessPoolExecutor(os.cpu_count(), chunksize=50) for CPU fragmentation
      * Stage 3: ThreadPoolExecutor(max_workers=16) for writes

    The adapter uses the php_fragmenter module for core fragmentation logic.

    Attributes:
        _io_workers: Number of workers for IO read stage (default: 32)
        _cpu_workers: Number of workers for CPU fragmentation stage
        _write_workers: Number of workers for write stage (default: 16)
        _default_profile: Default platform profile name (default: "generic_php")
    """

    # Regex patterns for extracting dependencies from PHP files
    _INCLUDE_PATTERN = re.compile(
        r"(?:include|include_once|require|require_once)\s*\(?\s*['\"]([^'\"]+)['\"]"
    )
    _GLOBAL_VAR_PATTERN = re.compile(r"\bglobal\s+\$([a-zA-Z_][a-zA-Z0-9_]*)")
    _FUNCTION_CALL_PATTERN = re.compile(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(")

    def __init__(
        self,
        io_workers: int = 32,
        cpu_workers: Optional[int] = None,
        write_workers: int = 16,
        default_profile: str = "generic_php",
    ) -> None:
        """Initialize the PhpLegacyAdapter.

        Args:
            io_workers: Number of workers for IO read stage (default: 32)
            cpu_workers: Number of workers for CPU fragmentation stage
                        (default: os.cpu_count())
            write_workers: Number of workers for write stage (default: 16)
            default_profile: Default platform profile name (default: "generic_php")
        """
        self._io_workers = io_workers
        self._cpu_workers = cpu_workers or os.cpu_count() or 4
        self._write_workers = write_workers
        self._default_profile = default_profile

        logger.debug(
            "PhpLegacyAdapter initialized: io_workers=%d, cpu_workers=%d, "
            "write_workers=%d, default_profile=%s",
            self._io_workers,
            self._cpu_workers,
            self._write_workers,
            self._default_profile,
        )

    @property
    def max_workers(self) -> int:
        """Return max workers configuration for compatibility."""
        return self._io_workers

    def parse_file(self, file_path: Path) -> ParseResult:
        """Parse a PHP file and return its content and metadata.

        This method reads the PHP file and extracts basic information.
        For full fragmentation, use the batch processing methods.

        Args:
            file_path: Path to the PHP file to parse.

        Returns:
            ParseResult containing parsed content and metadata.
            The ast_tree is None for PHP (non-AST language).

        Raises:
            ParseError: If the file cannot be read or parsed.
        """
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            raise ParseError(
                file_path=file_path,
                line=1,
                message=f"Failed to read file: {str(e)}",
            )

        # Extract dependencies from the file
        dependencies = self._extract_file_dependencies(content)

        return ParseResult(
            file_path=file_path,
            ast_tree=None,  # PHP doesn't use AST in the same way
            raw_content=content,
            dependencies=tuple(dependencies),
        )

    def extract_dependencies(self, file_path: Path) -> List[Dependency]:
        """Extract dependencies from a PHP file.

        This method extracts include/require statements, global variables,
        and function calls as dependencies.

        Args:
            file_path: Path to the PHP file to analyze.

        Returns:
            List of Dependency objects found in the file.

        Raises:
            ParseError: If the file cannot be read.
        """
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            raise ParseError(
                file_path=file_path,
                line=1,
                message=f"Failed to read file: {str(e)}",
            )

        return self._extract_file_dependencies(content)

    def _extract_file_dependencies(self, content: str) -> List[Dependency]:
        """Extract dependencies from PHP source content.

        Args:
            content: PHP source code content.

        Returns:
            List of Dependency objects.
        """
        dependencies: List[Dependency] = []
        seen: set = set()

        # Extract include/require statements
        for match in self._INCLUDE_PATTERN.finditer(content):
            path = match.group(1)
            if path not in seen:
                seen.add(path)
                dependencies.append(
                    Dependency(
                        name=path,
                        module_type="relative",
                        source_module=match.group(0),
                    )
                )

        # Extract global variables (common in legacy PHP)
        for match in self._GLOBAL_VAR_PATTERN.finditer(content):
            var_name = f"${match.group(1)}"
            if var_name not in seen:
                seen.add(var_name)
                dependencies.append(
                    Dependency(
                        name=var_name,
                        module_type="unknown",
                        source_module=f"global {var_name}",
                    )
                )

        # Extract known PHP function calls that are legacy patterns
        legacy_funcs = {
            "tep_db_query": "oscommerce",
            "tep_session_register": "oscommerce",
            "zen_db_perform": "zencart",
            "zen_redirect": "zencart",
            "$wpdb->prepare": "wordpress",
            "$wpdb->get_results": "wordpress",
            "add_action": "wordpress",
            "add_filter": "wordpress",
            "mysql_query": "legacy",
            "mysqli_query": "legacy",
        }

        for match in self._FUNCTION_CALL_PATTERN.finditer(content):
            func_name = match.group(1)
            if func_name in legacy_funcs and func_name not in seen:
                seen.add(func_name)
                dependencies.append(
                    Dependency(
                        name=func_name,
                        module_type=legacy_funcs[func_name],
                        source_module=func_name,
                    )
                )

        return dependencies

    def process_repository(
        self,
        repo_path: Path,
        output_dir: Path,
        profile_name: Optional[str] = None,
    ) -> List[Path]:
        """Process an entire PHP repository using the 3-stage pipeline.

        This method orchestrates the full processing pipeline:
        1. Stage 1 (IO): Read all PHP files using ThreadPoolExecutor
        2. Stage 2 (CPU): Fragment files using ProcessPoolExecutor
        3. Stage 3 (Write): Write bundles using ThreadPoolExecutor

        Args:
            repo_path: Root directory of the PHP repository.
            output_dir: Directory to write bundle files to.
            profile_name: Platform profile name (e.g., "oscommerce", "wordpress").
                        Defaults to self._default_profile.

        Returns:
            List of paths to created bundle files.
        """
        profile = profile_name or self._default_profile
        output_dir.mkdir(parents=True, exist_ok=True)

        # Find all PHP files (exclude common non-source directories)
        php_files = self._find_php_files(repo_path)
        logger.info("Found %d PHP files in %s", len(php_files), repo_path)

        if not php_files:
            return []

        # Stage 1: Read all files using ThreadPoolExecutor (IO-bound)
        logger.debug("Stage 1: Reading %d PHP files", len(php_files))
        file_contents: List[tuple[Path, str]] = []
        with ThreadPoolExecutor(max_workers=self._io_workers) as executor:
            futures = {executor.submit(self._read_php_file, f): f for f in php_files}
            for future in futures:
                file_path = futures[future]
                try:
                    content = future.result()
                    if content:
                        file_contents.append((file_path, content))
                except Exception as e:
                    logger.warning("Failed to read %s: %s", file_path, e)

        logger.debug("Stage 1 complete: %d files read successfully", len(file_contents))

        if not file_contents:
            return []

        # Stage 2: Process files using ProcessPoolExecutor (CPU-bound)
        logger.debug("Stage 2: Fragmenting %d files", len(file_contents))
        worker_args = [(str(path), content, profile) for path, content in file_contents]

        all_fragments: List[tuple[Path, dict]] = []
        with ProcessPoolExecutor(max_workers=self._cpu_workers) as executor:
            results = executor.map(
                _process_php_fragment_worker, worker_args, chunksize=50
            )
            for result in results:
                if result.get("success"):
                    path = Path(result["path"])
                    all_fragments.append((path, result))
                else:
                    logger.warning(
                        "Failed to process %s: %s",
                        result.get("path"),
                        result.get("error"),
                    )

        logger.debug("Stage 2 complete: %d files processed", len(all_fragments))

        # Stage 3: Write bundles using ThreadPoolExecutor (IO-bound)
        logger.debug("Stage 3: Writing %d bundles", len(all_fragments))
        written_files: List[Path] = []

        def write_fragment_bundle(args: tuple) -> Optional[Path]:
            """Write fragment bundles for a processed file."""
            path, result = args
            # Import here to ensure we're in the right context
            from src.discovery.php_fragmenter import PhpFragment, write_bundle

            try:
                for frag_data in result.get("fragments", []):
                    fragment = PhpFragment(
                        name=frag_data["name"],
                        fragment_type=frag_data["fragment_type"],
                        source_file=path,
                        start_line=1,
                        end_line=len(frag_data["raw_content"].splitlines()),
                        raw_content=frag_data["raw_content"],
                        legacy_action=frag_data["legacy_action"],
                        preamble_ref=frag_data["preamble_ref"],
                        dependencies=frag_data.get("dependencies", ()),
                        platform_hints=frag_data.get("platform_hints", ()),
                        signatures=frag_data.get(
                            "signatures", ()
                        ),  # Pass signatures to bundle
                    )
                    output_path = write_bundle(fragment, output_dir)
                    written_files.append(output_path)
                return None
            except Exception as e:
                logger.warning("Failed to write bundle for %s: %s", path, e)
                return None

        with ThreadPoolExecutor(max_workers=self._write_workers) as executor:
            list(executor.map(write_fragment_bundle, all_fragments))

        # Stage 4: Build include graph and emit MODULE_BLUEPRINT bundles for hub files
        logger.debug(
            "Stage 4: Building include graph and emitting MODULE_BLUEPRINT bundles"
        )
        blueprint_files = self._emit_hub_blueprints(
            file_contents, all_fragments, output_dir
        )
        written_files.extend(blueprint_files)

        logger.info(
            "Processing complete: %d bundles written to %s",
            len(written_files),
            output_dir,
        )
        return written_files

    def _emit_hub_blueprints(
        self,
        file_contents: List[tuple[Path, str]],
        all_fragments: List[tuple[Path, dict]],
        output_dir: Path,
    ) -> List[Path]:
        """Build include graph and emit MODULE_BLUEPRINT bundles for hub files.

        This method identifies files that are included by many other files (hub files)
        and emits MODULE_BLUEPRINT bundles documenting their role in the architecture.

        Args:
            file_contents: List of (file_path, content) tuples from Stage 1
            all_fragments: List of processed fragment results from Stage 2
            output_dir: Directory to write blueprint bundles to

        Returns:
            List of paths to created blueprint bundle files
        """
        from src.discovery.php_include_graph import (
            build_include_graph,
            get_hub_files,
        )

        # Build the include graph from processed files
        file_map = {path: content for path, content in file_contents}
        graph = build_include_graph(file_map)

        # Get hub files (included by 5 or more other files)
        hub_files = get_hub_files(graph, threshold=5)

        if not hub_files:
            logger.debug("No hub files found in repository")
            return []

        logger.info(
            "Found %d hub files, emitting MODULE_BLUEPRINT bundles", len(hub_files)
        )

        blueprint_files: List[Path] = []
        for hub_file in hub_files:
            # Get files that include this hub (reverse neighbors)
            reverse_neighbors = list(graph.reverse_neighbors(hub_file))
            in_degree = graph.get_in_degree(hub_file)

            # Create the MODULE_BLUEPRINT bundle content
            blueprint_path = self._write_module_blueprint(
                hub_file=hub_file,
                including_files=reverse_neighbors,
                in_degree=in_degree,
                output_dir=output_dir,
            )
            if blueprint_path:
                blueprint_files.append(blueprint_path)

        return blueprint_files

    def _write_module_blueprint(
        self,
        hub_file: str,
        including_files: List[str],
        in_degree: int,
        output_dir: Path,
    ) -> Optional[Path]:
        """Write a MODULE_BLUEPRINT bundle for a hub file.

        Args:
            hub_file: Path to the hub file
            including_files: List of files that include this hub
            in_degree: Number of files that include this hub
            output_dir: Directory to write the bundle to

        Returns:
            Path to the written blueprint file, or None if write fails
        """
        import hashlib

        # Create a safe filename from the hub path
        hub_path = Path(hub_file)
        safe_name = hub_path.stem.replace(" ", "_").replace("/", "_").replace("\\", "_")
        entity_id = f"{safe_name}_blueprint"

        # Build the MODULE_BLUEPRINT content
        lines: List[str] = []

        # Header
        lines.append("=== LOGICAL ENTITY: {} ===".format(entity_id))
        lines.append("Context: PHP Legacy Repository Knowledge Base")
        lines.append("Type: MODULE_BLUEPRINT")
        lines.append("")

        # MODULE_MAP section
        lines.append("[MODULE_MAP]")
        lines.append("MODULE: {}".format(hub_file))
        lines.append("ANCHOR: hub_file")
        lines.append("ROLE: central_include")
        lines.append("IN_DEGREE: {}".format(in_degree))
        lines.append("")

        # DEPENDENCIES - files that include this hub
        lines.append("[INCLUDED_BY]")
        for including_file in sorted(including_files):
            lines.append("  - {}".format(including_file))
        lines.append("")

        # Add summary count
        lines.append("[SUMMARY]")
        lines.append("Total files including this hub: {}".format(len(including_files)))
        lines.append("")

        # Calculate a hash for the preamble reference (empty for blueprints)
        preamble_hash = hashlib.sha256(hub_file.encode()).hexdigest()

        # Add minimal ARCH_HEADER for compatibility with Stage 2
        lines.append("[ARCH_HEADER]")
        lines.append("MODULE: {}".format(hub_file))
        lines.append("FILE_ROLE: hub")
        lines.append("FRAGMENT_TYPE: MODULE_BLUEPRINT")
        lines.append("LANGUAGE: php")
        lines.append("PLATFORM: php_legacy")
        lines.append(
            "DEPENDENCIES: {}".format(
                ", ".join(sorted(including_files)) if including_files else "none"
            )
        )
        lines.append("NEIGHBORS: {}".format(len(including_files)))
        lines.append("PREAMBLE_REF: {}".format(preamble_hash))
        lines.append("")

        content = "\n".join(lines)

        # Write the file
        try:
            output_path = output_dir / "{}.txt".format(entity_id)
            output_path.write_text(content, encoding="utf-8")
            logger.debug("Wrote MODULE_BLUEPRINT: %s", output_path)
            return output_path
        except Exception as e:
            logger.warning("Failed to write MODULE_BLUEPRINT for %s: %s", hub_file, e)
            return None

    def _find_php_files(self, repo_path: Path) -> List[Path]:
        """Find all PHP files in a repository.

        Excludes common non-source directories: vendor/, node_modules/,
        tests/, cache/, .git/

        Args:
            repo_path: Root directory to search.

        Returns:
            List of Path objects for PHP files.
        """
        exclude_dirs = {
            "vendor",
            "node_modules",
            "tests",
            "test",
            "cache",
            ".git",
            ".github",
            "docs",
            "static",
            "uploads",
        }

        php_files: List[Path] = []
        for path in repo_path.rglob("*.php"):
            # Check if any parent directory is in exclude list
            if not any(part in exclude_dirs for part in path.parts):
                php_files.append(path)

        return sorted(php_files)

    def _read_php_file(self, file_path: Path) -> Optional[str]:
        """Read a PHP file with error handling.

        Args:
            file_path: Path to the PHP file.

        Returns:
            File content as string, or None if read fails.
        """
        try:
            return file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            logger.warning("Failed to read %s: %s", file_path, e)
            return None
