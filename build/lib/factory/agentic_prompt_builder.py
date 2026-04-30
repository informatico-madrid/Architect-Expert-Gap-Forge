#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
AEGF V10-MT Prompt Builder — Multi-Turn Diversified Architect Edition
=====================================================================
[STATUS: EXPERIMENTAL]
Provides prompt construction utilities for multi-turn agentic training data.
"""

import ast
import hashlib
import json
import logging
import random
import re
from pathlib import Path
from string import Template
from typing import Any, Dict, List, Optional, Tuple

import yaml
from pydantic import BaseModel, ValidationError

# ══════════════════════════════════════════════════════════════════════
# LOGGER
# ══════════════════════════════════════════════════════════════════════
logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════
# Master document filenames (resolved dynamically from --gap-dir)
_MASTER_GUIDE_FILENAME = "HA_MASTER_GUIDE_2026.md"
_TECHNICAL_CHANGELOG_FILENAME = "technical_changelog_2026.md"

# ══════════════════════════════════════════════════════════════════════
# PYDANTIC MODEL FOR TOOL_CALL VALIDATION
# ══════════════════════════════════════════════════════════════════════


class ToolCallModel(BaseModel):
    """Pydantic model for validating tool call JSON."""

    name: str
    arguments: Dict[str, Any]


# ══════════════════════════════════════════════════════════════════════
# TAXONOMY — populated by load_taxonomy()
# ══════════════════════════════════════════════════════════════════════
_TAX: Dict[str, Any] = {}
HA_ERROR_TEMPLATES: List[Dict] = []
LEGACY_2023_PATTERNS: List[Dict] = []
TOOLS_DEFINITION: List[Dict] = []
_TOOLS_JSON: str = "[]"


def load_taxonomy(path: Path) -> None:
    """Load the YAML taxonomy and populate module-level data lists."""
    global _TAX, HA_ERROR_TEMPLATES, LEGACY_2023_PATTERNS
    global TOOLS_DEFINITION, _TOOLS_JSON

    with open(path, "r", encoding="utf-8") as fh:
        _TAX = yaml.safe_load(fh)

    HA_ERROR_TEMPLATES = _TAX["ha_error_templates"]
    LEGACY_2023_PATTERNS = _TAX["legacy_2023_patterns"]
    TOOLS_DEFINITION = _TAX["tools_definition"]
    _TOOLS_JSON = json.dumps(TOOLS_DEFINITION, indent=2, ensure_ascii=False)


def _prompt(key: str) -> str:
    """Dot-separated key access into _TAX['prompts'], e.g. 'system.base'."""
    node = _TAX["prompts"]
    for part in key.split("."):
        node = node[part]
    return node


def _render(template_str: str, **kwargs: Any) -> str:
    """Render a prompt template using string.Template (safe with JSON braces)."""
    return Template(template_str).safe_substitute(**kwargs)


# ══════════════════════════════════════════════════════════════════════
# LEGACY CODE DETECTORS (regex patterns — kept in Python)
# ══════════════════════════════════════════════════════════════════════
LEGACY_CODE_DETECTORS = [
    (r"hass\.data\[", "hass.data[] dict pattern → entry.runtime_data"),
    (r"hass\.data\.setdefault", "hass.data.setdefault() → entry.runtime_data"),
    (
        r"\bTEMP_CELSIUS\b|\bTEMP_FAHRENHEIT\b|\bTEMP_KELVIN\b",
        "Legacy TEMP_* constants → UnitOfTemperature enum",
    ),
    (
        r"\bUNIT_PERCENTAGE\b|\bPERCENTAGE\b(?=\s*[,\)])",
        "Legacy UNIT_PERCENTAGE → UnitOfMeasurement enum",
    ),
    (
        r"\bLENGTH_METERS\b|\bLENGTH_KILOMETERS\b|\bLENGTH_MILES\b",
        "Legacy LENGTH_* constants → UnitOfLength enum",
    ),
    (
        r"\bMASS_GRAMS\b|\bMASS_KILOGRAMS\b|\bVOLUME_LITERS\b",
        "Legacy MASS_*/VOLUME_* constants → UnitOf* enums",
    ),
    (
        r"\bPRESSURE_BAR\b|\bPRESSURE_PA\b|\bPRESSURE_HPA\b",
        "Legacy PRESSURE_* constants → UnitOfPressure enum",
    ),
    (
        r"\bENERGY_KILO_WATT_HOUR\b|\bENERGY_WATT_HOUR\b|\bPOWER_WATT\b|\bPOWER_KILO_WATT\b",
        "Legacy ENERGY_*/POWER_* → UnitOfEnergy/UnitOfPower enums",
    ),
    (
        r"async_forward_entry_setup\b(?!s)",
        "Singular async_forward_entry_setup → async_forward_entry_setups",
    ),
    (
        r"device_class\s*=\s*[\"'](?:temperature|humidity|pressure|energy|power|battery|voltage|current)",
        "String literal device_class → SensorDeviceClass enum",
    ),
    (r"_attr_device_class\s*=\s*[\"']", "String _attr_device_class → Enum"),
    (r"def update\(self\)", "Synchronous update(self) → CoordinatorEntity + async"),
    (r"def\s+async_update\(self\)", "Direct async_update → CoordinatorEntity pattern"),
    (r"PLATFORM_SCHEMA\s*=", "YAML-only PLATFORM_SCHEMA → ConfigFlow required"),
    (
        r"requests\.get\(|requests\.post\(|requests\.put\(|requests\.delete\(",
        "Blocking requests.* → aiohttp/async_add_executor_job",
    ),
    (r"(?<!await\s)time\.sleep\(", "Blocking time.sleep() → await asyncio.sleep()"),
    (r"urllib\.request\.urlopen", "Blocking urllib → aiohttp"),
    (r"\bself\._state\s*=", "Legacy self._state = X → native_value property"),
    (r"\bself\._attr_state\s*=", "Legacy self._attr_state → native_value property"),
    (r"@property\s*\n\s*def\s+state\(self\)", "Legacy state property → native_value"),
    (r"add_entities\(\[.*\]\s*,\s*True\)", "Legacy polling=True → CoordinatorEntity"),
]


def detect_legacy_patterns(code: str) -> List[str]:
    """Detect legacy 2023/2024 patterns in source code.

    Returns:
        List of descriptions. Empty if code is clean.
    """
    found = []
    for pattern, description in LEGACY_CODE_DETECTORS:
        if re.search(pattern, code):
            found.append(description)
    return found


# ══════════════════════════════════════════════════════════════════════
# MASTER DOCUMENT LOADING — Fail-Fast
# ══════════════════════════════════════════════════════════════════════


def load_master_docs(gap_dir: Path) -> Tuple[str, str]:
    """Load master documents from gap_dir. Raises FileNotFoundError if missing."""
    master_path = gap_dir / _MASTER_GUIDE_FILENAME
    changelog_path = gap_dir / _TECHNICAL_CHANGELOG_FILENAME

    if not master_path.exists():
        raise FileNotFoundError(
            f"Master Guide not found: {master_path}. "
            "Use --gap-dir to specify the correct directory."
        )
    if not changelog_path.exists():
        raise FileNotFoundError(
            f"Technical Changelog not found: {changelog_path}. "
            "Use --gap-dir to specify the correct directory."
        )

    master = master_path.read_text(encoding="utf-8", errors="ignore")
    changelog = changelog_path.read_text(encoding="utf-8", errors="ignore")
    return master, changelog


# ══════════════════════════════════════════════════════════════════════
# SYSTEM PROMPT BUILDERS — Multi-Turn Diversified
# ══════════════════════════════════════════════════════════════════════


def _base_system_block(master: str, changelog: str) -> str:
    """Shared base block: tools, multi-turn grammar, truth anchors."""
    return _render(
        _prompt("system.base"),
        tools_json=_TOOLS_JSON,
        master=master,
        changelog=changelog,
    )


def build_system_nominal(master: str, changelog: str) -> str:
    """System prompt for nominal trajectories (Evol-Instruct)."""
    return _base_system_block(master, changelog) + _prompt("system.nominal_suffix")


def build_system_contrast(master: str, changelog: str) -> str:
    """System prompt for contrast trajectories (2023 → 2026)."""
    return _base_system_block(master, changelog) + _prompt("system.contrast_suffix")


def build_system_error_recovery(master: str, changelog: str) -> str:
    """System prompt for error recovery trajectories."""
    return _base_system_block(master, changelog) + _prompt(
        "system.error_recovery_suffix"
    )


# ══════════════════════════════════════════════════════════════════════
# USER PROMPT BUILDERS BY TYPE
# ══════════════════════════════════════════════════════════════════════


def build_user_nominal(frag: Dict[str, Any], difficulty: str) -> str:
    """Build user prompt for nominal examples with Evol-Instruct."""
    tpl_vars = dict(
        context=frag["context"],
        virtual_filename=frag["virtual_filename"],
        name=frag["name"],
        skeleton=frag["skeleton"],
    )

    if difficulty == "easy":
        return _render(_prompt("user.nominal_easy"), **tpl_vars)
    elif difficulty == "medium":
        return _render(_prompt("user.nominal_medium"), **tpl_vars)
    else:  # hard
        if random.random() < 0.50:
            # Anchor-free variant: pick one of 3
            variants = _prompt("user.nominal_hard_anchor_free")
            return _render(random.choice(variants), **tpl_vars)
        else:
            return _render(_prompt("user.nominal_hard_anchor"), **tpl_vars)


def build_user_contrast(frag: Dict[str, Any]) -> str:
    """Build user prompt where user uses 2023 pattern (model must correct)."""
    pattern = random.choice(LEGACY_2023_PATTERNS)
    return _render(
        _prompt("user.contrast"),
        context=frag["context"],
        virtual_filename=frag["virtual_filename"],
        name=frag["name"],
        skeleton=frag["skeleton"],
        legacy_code=pattern["legacy_code"].strip(),
    )


def build_user_error_recovery(frag: Dict[str, Any]) -> str:
    """Build user prompt with a simulated HA error."""
    err_template = random.choice(HA_ERROR_TEMPLATES)
    error_msg = err_template["error"].format(
        entity=f"sensor.{frag['name'].lower()}",
        component=frag["virtual_filename"].replace(".py", "").replace("/", "."),
        entry_id="abc123def456",
        seconds="12",
        literal="temperature",
        entity_id=f"sensor.{frag['name'].lower()}_value",
    )
    return _render(
        _prompt("user.error_recovery"),
        context=frag["context"],
        virtual_filename=frag["virtual_filename"],
        name=frag["name"],
        skeleton=frag["skeleton"],
        error_msg=error_msg,
    )


# ══════════════════════════════════════════════════════════════════════
# CHUNKING & FRAGMENTATION
# ══════════════════════════════════════════════════════════════════════


def get_file_chunks(content: str) -> List[Tuple[str, str]]:
    """Split raw text files by '--- FILE: ... ---' markers."""
    parts = re.split(r"--- FILE: (.*?) ---\n", content)
    chunks = []
    for i in range(1, len(parts), 2):
        if i + 1 < len(parts):
            chunks.append((parts[i].strip(), parts[i + 1].strip()))
    return chunks


def get_fragments(filename: str, code: str) -> List[Dict[str, Any]]:
    """Extract AST/markdown fragments from a single file."""
    fragments = []
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
                    "skeleton": f"# {filename}\n[Generate full technical documentation]",
                    "original": code,
                    "context": "HA Documentation",
                    "virtual_filename": filename,
                }
            )

    # OTHER: Raw file (no AST, no markdown)
    else:
        chunks = code.split("\n\n")
        for i, chunk in enumerate(chunks):
            if len(chunk.strip()) > 50:
                fragments.append(
                    {
                        "name": f"{filename}#{i + 1}",
                        "type": "raw",
                        "subtype": "text",
                        "skeleton": f"# Fragment {i + 1} of {filename}\n[Generate content]",
                        "original": chunk,
                        "context": f"File: {filename}",
                        "virtual_filename": filename,
                    }
                )

    return fragments


# ══════════════════════════════════════════════════════════════════════
# LDI VALIDATION (Line Density Index)
# ══════════════════════════════════════════════════════════════════════


def validate_ldi(
    code_len: int, reasoning_len: int, subtype: str = None, f_subtype: str = None
) -> Tuple[bool, float, str]:
    """Validate Length-Density Index: code vs reasoning ratio.

    Args:
        code_len: Length of the code in characters.
        reasoning_len: Length of the reasoning in characters.
        subtype: Type of the fragment (code, test, doc). Alias: f_subtype.
        f_subtype: Alias for subtype parameter.

    Returns:
        Tuple of (is_valid, ldi_value, message)
    """
    # Handle f_subtype alias
    if subtype is None and f_subtype is not None:
        subtype = f_subtype
    if subtype is None:
        subtype = "code"  # Default to code type

    if reasoning_len == 0:
        return False, 0.0, "Zero reasoning"
    ldi = round(code_len / reasoning_len, 3)

    if subtype in ["test", "doc"]:
        if reasoning_len < 50:
            return False, ldi, "Reasoning too short for doc/test"
        return True, ldi, "Pass (Doc/Test Mode)"

    K_FACTOR = 1200
    BASE_THRESHOLD = 0.10
    dynamic_limit = BASE_THRESHOLD * (code_len / (code_len + K_FACTOR))

    if code_len > 0 and code_len < 100 and ldi >= 0.01:
        return True, ldi, "Pass (Micro-Snippet Exception)"

    if ldi < dynamic_limit:
        return False, ldi, f"Verbosity (LDI {ldi} < Dynamic {round(dynamic_limit, 3)})"

    return True, ldi, f"Pass (Dynamic Threshold {round(dynamic_limit, 3)})"


# ══════════════════════════════════════════════════════════════════════
# EXAMPLE TYPE ASSIGNMENT (Evol-Instruct difficulty)
# ══════════════════════════════════════════════════════════════════════


# Type distribution (identical to V10)
DIST_NOMINAL = 0.50
DIST_CONTRAST = 0.30
DIST_ERROR_RECOVERY = 0.20

# Evol-Instruct difficulty levels
EVOL_LEVELS = ["easy", "medium", "hard"]


def assign_example_type(
    frag: Dict[str, Any], has_legacy: bool = False
) -> Tuple[str, Optional[str]]:
    """Assign example type and Evol-Instruct difficulty.

    If has_legacy is True, forces contrast or error_recovery (not nominal).

    Returns:
        Tuple of (example_type, evol_difficulty)
        evol_difficulty is None for contrast/error_recovery types.
    """
    if has_legacy:
        # Legacy code → contrast or error_recovery (cannot be nominal)
        return random.choice(["contrast", "error_recovery"]), None

    # Sample type by distribution
    r = random.random()
    if r < DIST_NOMINAL:
        return "nominal", random.choice(EVOL_LEVELS)
    elif r < DIST_NOMINAL + DIST_CONTRAST:
        return "contrast", None
    else:
        return "error_recovery", None


# ══════════════════════════════════════════════════════════════════════
# TEXT EXTRACTION & VALIDATION
# ══════════════════════════════════════════════════════════════════════


def extract_and_validate(text: str) -> Tuple[Optional[ToolCallModel], str]:
    """Extract tool_call JSON from LLM response and validate with Pydantic.

    Also extracts reasoning from <|thinking|> or <|thought|> tags.

    Returns:
        Tuple of (ToolCallModel or None, reasoning_text)
    """
    # Extract reasoning
    reasoning = ""
    if "<think>" in text and "</think>" in text:
        reasoning = text.split("<think>")[1].split("</think>")[0].strip()
    elif "</think>" in text:
        reasoning = text.split("</think>")[0].strip()

    if "<tool_call>" not in text or "</tool_call>" not in text:
        return None, reasoning

    try:
        raw_json = text.split("<tool_call>")[1].split("</tool_call>")[0].strip()
        data = json.loads(raw_json)
        return ToolCallModel(**data), reasoning
    except (IndexError, json.JSONDecodeError, ValidationError):
        return None, reasoning


# ══════════════════════════════════════════════════════════════════════
# CHECKPOINT / RESUME
# ══════════════════════════════════════════════════════════════════════


def make_checkpoint_key(
    frag_name: str, virtual_filename: str, rep: Optional[int] = None
) -> str:
    """Deterministic key (does NOT depend on example_type/evol_difficulty)."""
    raw = f"{frag_name}::{virtual_filename}"
    if rep is not None:
        raw += f"::rep{rep}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def load_checkpoint(output_path: Path, rejected_path: Path) -> set:
    """Load already-processed checkpoint keys."""
    done_keys = set()
    for path in [output_path, rejected_path]:
        if not path.exists():
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        ck = record.get("metadata", {}).get("checkpoint_key")
                        if not ck:
                            ck = record.get("checkpoint_key")
                        if ck:
                            done_keys.add(ck)
                    except json.JSONDecodeError:
                        logger.warning(
                            "Checkpoint: invalid JSON in %s line %d", path, line_num
                        )
        except Exception as e:
            logger.warning("Checkpoint: error reading %s: %s", path, e)
    return done_keys
