#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Fragment Extractor Module — AEGF V11.0

This module contains all fragment extraction and parsing functions:
- get_file_chunks: Split packed .txt files into (filename, code) tuples
- parse_bundle: Parse V2 .txt bundles produced by processor.py
- _ast_fragment_list: Extract AST-based fragments from Python files
- get_v2_fragments: Generate training fragments from V2 bundle results
- get_fragments: Extract fragments from files (Python, Jinja, YAML, Markdown)

All functions return list[FragmentTypedDict] from src.schemas.common.
No import-time side effects.
"""

import ast
import hashlib
import logging
import re
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from src.schemas.common import FragmentTypedDict
from src.utils.extractors.base import ParseError

logger = logging.getLogger(__name__)


# ======================================================================
# CHUNKING AND FRAGMENTATION
# ======================================================================


def get_file_chunks(content: str) -> List[Tuple[str, str]]:
    """Split packed .txt file into (filename, code) tuples (V10 backward compat)."""
    parts = re.split(r"--- FILE: (.*?) ---\n", content)
    chunks = []
    for i in range(1, len(parts), 2):
        if i + 1 < len(parts):
            chunks.append((parts[i].strip(), parts[i + 1].strip()))
    return chunks


# ======================================================================
# V11: MODULE-AWARE BUNDLE PARSER
# ======================================================================


def parse_bundle(txt_content: str) -> Dict:
    """Parse a V2 .txt bundle produced by processor.py V2.

    Handles four bundle types:
      - MODULE_BLUEPRINT  : Architecture index (TIPO 4); goes to blueprint_cache only.
      - FUNCTIONAL_UNIT   : Logic + test pair (TIPO 1); generates parallel tool-call samples.
      - LOGIC_ONLY        : Single logic file (TIPO 3); AST-chunked with blueprint context.
      - GOVERNANCE_RULES  : Repo-level coding standards (TIPO 5); goes to governance_cache.

    Returns:
        entity_id : str
        context   : str
        type      : str  (MODULE_BLUEPRINT | FUNCTIONAL_UNIT | LOGIC_ONLY | GOVERNANCE_RULES)
        arch      : dict  (from [ARCH_HEADER] / [MODULE_MAP] / [GOVERNANCE_HEADER])
        files     : dict[filename → raw_content]
    """
    result: Dict = {"entity_id": "", "context": "", "type": "", "arch": {}, "files": {}}

    m = re.search(r"=== LOGICAL ENTITY: (.*?) ===", txt_content)
    if m:
        result["entity_id"] = m.group(1).strip()

    m = re.search(r"^Context:\s*(.+)$", txt_content, re.MULTILINE)
    if m:
        result["context"] = m.group(1).strip()

    m = re.search(r"^Type:\s*(.+)$", txt_content, re.MULTILINE)
    if m:
        result["type"] = m.group(1).strip()

    # ARCH_HEADER (FUNCTIONAL_UNIT / LOGIC_ONLY)
    m = re.search(r"\[ARCH_HEADER\](.*?)(?=\n\[|\n---|$)", txt_content, re.DOTALL)
    if m:
        for line in m.group(1).strip().splitlines():
            if ":" in line:
                key, _, val = line.partition(":")
                result["arch"][key.strip()] = val.strip()

    # MODULE_MAP (MODULE_BLUEPRINT) — fallback when no ARCH_HEADER
    if not result["arch"]:
        m = re.search(r"\[MODULE_MAP\](.*?)(?=\n\[|\n---|$)", txt_content, re.DOTALL)
        if m:
            for line in m.group(1).strip().splitlines():
                if ":" in line:
                    key, _, val = line.partition(":")
                    result["arch"][key.strip()] = val.strip()

    # GOVERNANCE_HEADER (GOVERNANCE_RULES) — fallback when neither present
    if not result["arch"]:
        m = re.search(
            r"\[GOVERNANCE_HEADER\](.*?)(?=\n\[|\n---|$)", txt_content, re.DOTALL
        )
        if m:
            for line in m.group(1).strip().splitlines():
                if ":" in line:
                    key, _, val = line.partition(":")
                    result["arch"][key.strip()] = val.strip()

    # T034: Generic section discovery loop — capture unknown sections as extra_<name>
    # Known sections: ARCH_HEADER, MODULE_MAP, GOVERNANCE_HEADER (already parsed above)
    # The \n--- sentinel prevents --- FILE: fragment bodies from leaking into extra_* keys
    KNOWN_SECTIONS = {"ARCH_HEADER", "MODULE_MAP", "GOVERNANCE_HEADER"}
    generic_sections = re.findall(
        r"\[([A-Z_]+)\](.*?)(?=\n\[|\n---|$)", txt_content, re.DOTALL
    )
    for section_name, section_content in generic_sections:
        if section_name not in KNOWN_SECTIONS:
            # Store unknown sections as extra_<name> keys in result dict
            result[f"extra_{section_name.lower()}"] = section_content.strip()

    # File chunks after the header section
    parts = re.split(r"--- FILE: (.*?) ---\n", txt_content)
    for i in range(1, len(parts), 2):
        if i + 1 < len(parts):
            result["files"][parts[i].strip()] = parts[i + 1]

    return result


def _ast_fragment_list(
    logic_fname: str,
    logic_code: str,
    context_str: str,
    extra_fields: Dict,
) -> List[FragmentTypedDict]:
    """Extract AST-based fragment dicts from a Python logic file.

    Returns one dict per top-level class/function.
    Raises ParseError if AST parsing fails (FR-006).
    """
    frags: List[FragmentTypedDict] = []
    try:
        tree = ast.parse(logic_code)
    except SyntaxError as e:
        raise ParseError(
            file_path=Path(logic_fname),
            line=e.lineno or 1,
            message=f"SyntaxError: {e.msg}",
        )

    imports = [
        ast.unparse(n) for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))
    ]
    ctx = "\n".join(imports) or context_str
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            node_copy = ast.parse(ast.unparse(node)).body[0]
            placeholder = "... # [Expert HA 2026 Implementation]"
            if isinstance(node_copy, ast.ClassDef):
                for item in node_copy.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        item.body = [ast.Expr(value=ast.Constant(value=placeholder))]
            else:
                node_copy.body = [ast.Expr(value=ast.Constant(value=placeholder))]
            frags.append(
                {
                    **extra_fields,
                    "name": node.name,
                    "skeleton": ast.unparse(node_copy),
                    "original": ast.unparse(node),
                    "context": ctx,
                }
            )

    if not frags:
        # Empty file - raise ParseError instead of fallback (FR-006)
        raise ParseError(
            file_path=Path(logic_fname),
            line=1,
            message="No top-level classes or functions found",
        )

    return frags


def _php_fragment_list(
    logic_fname: str,
    logic_code: str,
    context_str: str,
    extra_fields: Dict,
) -> List[FragmentTypedDict]:
    """Extract fragment dicts from a pre-divided PHP bundle.

    PHP bundles arrive pre-divided (fragmentation done in Phase 3), so this
    function returns exactly one element per --- FILE: chunk, no AST re-parsing.

    legacy_signatures and implicit_deps arrive pre-populated in extra_fields
    (via T035/T039).

    Raises ParseError if logic_code is empty.
    """
    if not logic_code or not logic_code.strip():
        raise ParseError(
            file_path=Path(logic_fname),
            line=1,
            message="Empty logic_code: PHP bundle has no content",
        )

    # PHP bundles are pre-fragmented by Phase 3 - return one element per chunk
    # The fragment name comes from the filename stem, content is as-is
    fragment_name = Path(logic_fname).stem

    return [
        {
            **extra_fields,
            "name": fragment_name,
            "skeleton": logic_code,
            "original": logic_code,
            "context": context_str,
        }
    ]


def resolve_preamble_ref(
    arch: dict,
    bundle_cache: dict[str, str],
) -> str:
    """
    Resolve a PREAMBLE_REF SHA-256 hash back to its preamble content (T072 / FR-022 / R-011).

    Reads ``arch.get("PREAMBLE_REF", "")`` (64-char hex SHA-256).  If set,
    reverses the hash by scanning ``bundle_cache`` values for one whose SHA-256
    digest matches.  If found and the content is large (token proxy:
    ``len(content) // 4 > 800``), truncates to first ``800 * 4 = 3200`` chars.

    Args:
        arch: Parsed ARCH_HEADER dict (from ``parse_bundle``).
        bundle_cache: Dict mapping bundle keys to raw preamble/bootstrap content.

    Returns:
        Preamble content string (possibly truncated), or ``""`` when
        PREAMBLE_REF is absent or the hash cannot be resolved.

    Examples:
        >>> import hashlib
        >>> content = "<?php define('VERSION', '2.3');\\n"
        >>> h = hashlib.sha256(content.encode()).hexdigest()
        >>> arch = {"PREAMBLE_REF": h}
        >>> resolve_preamble_ref(arch, {h: content})
        "<?php define('VERSION', '2.3');\\n"

        >>> resolve_preamble_ref({"PREAMBLE_REF": "deadbeef"}, {})
        ''

        >>> resolve_preamble_ref({}, {})
        ''
    """
    preamble_ref = arch.get("PREAMBLE_REF", "")
    if not preamble_ref or len(preamble_ref) != 64:
        return ""

    # Build reverse-lookup: sha256(value) → value
    reverse_map = {
        hashlib.sha256(v.encode()).hexdigest(): v
        for v in bundle_cache.values()
    }

    content = reverse_map.get(preamble_ref, "")
    if not content:
        return ""

    # Truncate oversized preambles (token proxy: 4 chars ≈ 1 token, cap at 800 tokens)
    _MAX_TOKENS = 800
    if len(content) // 4 > _MAX_TOKENS:
        content = content[:_MAX_TOKENS * 4]

    return content


# Extension Mapper: dispatch by file extension to appropriate fragmenter
_EXTENSION_FRAGMENTERS: Dict[str, Callable[..., List[FragmentTypedDict]]] = {
    ".py": _ast_fragment_list,
    ".php": _php_fragment_list,
}


def get_v2_fragments(
    bundle: Dict,
    blueprint_cache: Dict[str, str],
    allowed_extensions: Optional[set] = None,
    governance_cache: Optional[Dict[str, str]] = None,
    bundle_cache: Optional[Dict[str, str]] = None,
) -> List[FragmentTypedDict]:
    """Generate training-ready fragment dicts from a V2 parse_bundle result.

    MODULE_BLUEPRINT  → []  (cached, no direct training samples)
    GOVERNANCE_RULES  → []  (cached in governance_cache, no direct samples)
    FUNCTIONAL_UNIT   → frags with subtype='functional_unit' (parallel gold injection)
    LOGIC_ONLY        → AST or whole-file frags with blueprint + governance context
    """
    if governance_cache is None:
        governance_cache = {}
    if bundle_cache is None:
        bundle_cache = {}

    btype = bundle["type"]
    if btype in ("MODULE_BLUEPRINT", "GOVERNANCE_RULES"):
        return []

    arch = bundle["arch"]
    module_name = arch.get("MODULE", "")
    repo_prefix = arch.get("REPO_PREFIX", "")
    blueprint_content = blueprint_cache.get(module_name, "")
    governance_content = governance_cache.get(repo_prefix, "")
    local_imports_raw = arch.get("LOCAL_IMPORTS", "[]")

    # T035: inject extra_legacy_signatures for Teacher prompt ${legacy_signatures}
    legacy_signatures_content = bundle.get("extra_legacy_signatures", "")

    # T072: resolve PREAMBLE_REF → preamble content for ${preamble} injection
    preamble_content = resolve_preamble_ref(arch, bundle_cache)

    def _vname(fname: str) -> str:
        return f"{module_name}_{fname}" if module_name else fname

    if btype == "FUNCTIONAL_UNIT":
        filenames = list(bundle["files"].keys())
        logic_fname = next((f for f in filenames if not f.startswith("test_")), None)
        test_fname = next((f for f in filenames if f.startswith("test_")), None)

        if not logic_fname or not test_fname:
            logger.debug(
                "FUNCTIONAL_UNIT without both files (%s): %s",
                bundle["entity_id"],
                filenames,
            )
            return []

        if allowed_extensions is not None:
            ext = Path(logic_fname).suffix.lower()
            if ext and ext not in allowed_extensions:
                return []

        logic_code = bundle["files"][logic_fname]
        test_code = bundle["files"][test_fname]
        extra = {
            "type": "python",
            "subtype": "functional_unit",
            "virtual_filename": _vname(logic_fname),
            "test_filename": _vname(test_fname),
            "test_original": test_code,
            "blueprint": blueprint_content,
            "local_imports": local_imports_raw,
            "module_name": module_name,
            "governance": governance_content,
            "legacy_signatures": legacy_signatures_content,
            "preamble": preamble_content,
        }

        # Extension Mapper dispatch
        suffix = Path(logic_fname).suffix.lower()
        fragmenter = _EXTENSION_FRAGMENTERS.get(suffix)
        if fragmenter:
            return fragmenter(logic_fname, logic_code, bundle["context"], extra)
        # Fallback to AST for unknown extensions
        return _ast_fragment_list(logic_fname, logic_code, bundle["context"], extra)

    if btype == "LOGIC_ONLY":
        if not bundle["files"]:
            return []
        logic_fname, logic_code = next(iter(bundle["files"].items()))

        if allowed_extensions is not None:
            ext = Path(logic_fname).suffix.lower()
            if ext and ext not in allowed_extensions:
                return []

        # Extension Mapper dispatch - use specialized fragmenter if available
        suffix = Path(logic_fname).suffix.lower()
        fragmenter = _EXTENSION_FRAGMENTERS.get(suffix)
        if fragmenter:
            extra = {
                "type": "php" if suffix == ".php" else "python",
                "subtype": "logic_only",
                "virtual_filename": _vname(logic_fname),
                "blueprint": blueprint_content,
                "local_imports": local_imports_raw,
                "module_name": module_name,
                "governance": governance_content,
                "legacy_signatures": legacy_signatures_content,
                "preamble": preamble_content,
            }
            return fragmenter(logic_fname, logic_code, bundle["context"], extra)

        # Fallback: Re-use existing get_fragments for all subtypes (Python/jinja/yaml)
        base_frags = get_fragments(logic_fname, logic_code, allowed_extensions=None)
        for f in base_frags:
            f["virtual_filename"] = _vname(f["virtual_filename"])
            f["blueprint"] = blueprint_content
            f["local_imports"] = local_imports_raw
            f["module_name"] = module_name
            f["governance"] = governance_content
        return base_frags

    # Unknown type — skip
    logger.debug("Unknown bundle type '%s' in %s", btype, bundle["entity_id"])
    return []


def get_fragments(
    filename: str, code: str, allowed_extensions: Optional[set] = None
) -> List[FragmentTypedDict]:
    """Extract fragments from a file for synthesis.

    If allowed_extensions is provided, only generates fragments for files
    whose extension is in the set (e.g. {".py", ".jinja2"}).
    If None, processes all supported types.
    """
    # Extension filter: if specified, skip undesired files
    if allowed_extensions is not None:
        file_ext = Path(filename).suffix.lower()
        if file_ext and file_ext not in allowed_extensions:
            return []

    fragments: List[FragmentTypedDict] = []
    is_test = "test_" in filename

    # PYTHON: AST Chunking
    if filename.endswith(".py"):
        try:
            tree = ast.parse(code)
            imports = [
                ast.unparse(n)
                for n in tree.body
                if isinstance(n, (ast.Import, ast.ImportFrom))
            ]
            context_str = "\n".join(imports)
            for node in tree.body:
                if isinstance(
                    node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
                ):
                    node_copy = ast.parse(ast.unparse(node)).body[0]
                    placeholder = "... # [Expert HA 2026 Implementation]"

                    if isinstance(node_copy, ast.ClassDef):
                        for item in node_copy.body:
                            if isinstance(
                                item, (ast.FunctionDef, ast.AsyncFunctionDef)
                            ):
                                item.body = [
                                    ast.Expr(value=ast.Constant(value=placeholder))
                                ]
                    else:
                        node_copy.body = [
                            ast.Expr(value=ast.Constant(value=placeholder))
                        ]

                    fragments.append(
                        {
                            "name": node.name,
                            "type": "python",
                            "subtype": "test" if is_test else "code",
                            "skeleton": ast.unparse(node_copy),
                            "original": ast.unparse(node),
                            "context": context_str,
                            "virtual_filename": filename,
                        }
                    )
        except Exception:
            pass

    # MARKDOWN: Contextual chunking
    elif filename.endswith(".md") or filename == "README":
        if len(code) > 12000:
            headers = re.split(r"(^#{1,2} .*)", code, flags=re.MULTILINE)
            for i in range(1, len(headers), 2):
                header = headers[i]
                body = headers[i + 1] if i + 1 < len(headers) else ""
                if len(body.strip()) > 100:
                    fragments.append(
                        {
                            "name": header.strip("# ").strip(),
                            "type": "readme",
                            "subtype": "doc",
                            "skeleton": f"{header}\n[Detailed Technical Documentation]",
                            "original": f"{header}{body}",
                            "context": "HA Documentation",
                            "virtual_filename": filename,
                        }
                    )
        else:
            fragments.append(
                {
                    "name": f"Full Documentation: {filename}",
                    "type": "readme",
                    "subtype": "doc",
                    "skeleton": f"# {filename}\n[Generate complete technical documentation]",
                    "original": code,
                    "context": "HA Documentation",
                    "virtual_filename": filename,
                }
            )

    # JINJA2 TEMPLATES: Home Assistant logic templates (.jinja, .jinja2, .j2)
    elif filename.endswith((".jinja", ".jinja2", ".j2")):
        jinja_blocks = re.split(
            r"(\{%-?\s*(?:macro|block)\s+\w+[^%]*%\})", code, flags=re.DOTALL
        )
        if len(jinja_blocks) > 2:
            # Has macros/blocks -> one fragment per block
            for i in range(1, len(jinja_blocks), 2):
                block_header = jinja_blocks[i].strip()
                block_body = jinja_blocks[i + 1] if i + 1 < len(jinja_blocks) else ""
                name_match = re.search(r"(?:macro|block)\s+(\w+)", block_header)
                block_name = name_match.group(1) if name_match else f"block_{i // 2}"
                full_block = f"{block_header}\n{block_body}"
                if len(full_block.strip()) < 30:
                    continue
                fragments.append(
                    {
                        "name": block_name,
                        "type": "template",
                        "subtype": "jinja",
                        "skeleton": f"{block_header}\n  {{# [Expert HA 2026 Implementation] #}}",
                        "original": full_block.strip(),
                        "context": f"Jinja2 template: {filename}",
                        "virtual_filename": filename,
                    }
                )
        else:
            # Template without macros/blocks -> single fragment
            if len(code.strip()) > 30:
                fragments.append(
                    {
                        "name": f"Template: {Path(filename).stem}",
                        "type": "template",
                        "subtype": "jinja",
                        "skeleton": f"{{# Template: {filename} #}}\n{{# [Expert HA 2026 Implementation] #}}",
                        "original": code,
                        "context": f"Jinja2 template: {filename}",
                        "virtual_filename": filename,
                    }
                )

    # YAML CONFIG: Home Assistant configuration files (.yaml, .yml)
    elif filename.endswith((".yaml", ".yml")):
        if len(code.strip()) > 50:
            fragments.append(
                {
                    "name": f"Config: {Path(filename).stem}",
                    "type": "config",
                    "subtype": "yaml",
                    "skeleton": f"# {filename}\n# [Complete HA 2026 configuration]",
                    "original": code,
                    "context": f"YAML config: {filename}",
                    "virtual_filename": filename,
                }
            )

    return fragments
