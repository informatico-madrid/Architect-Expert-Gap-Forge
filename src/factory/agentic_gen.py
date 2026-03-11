#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
AEGF (Architect-Expert-Gap-Forge) V10-MT — Multi-Turn Diversified Architect Edition
==================================================================================
[STATUS: EXPERIMENTAL]
Generates multi-turn agentic training data with tool-call grammar:
  Turn 1: user request
  Turn 2: assistant write_to_file (with Gold Injection)
  Turn 3: tool response (simulated)
  Turn 4: assistant attempt_completion
"""

import ast
import asyncio
import json
import logging
import random
import re
import sys
import argparse
import hashlib
import time
import yaml
from pathlib import Path
from string import Template
from typing import List, Dict, Any, Tuple, Optional

from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError
from tqdm import tqdm

# ══════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════
DEFAULT_BASE_URL = "http://localhost:8000/v1"
DEFAULT_API_KEY = "sk-master-bunker-2026"
DEFAULT_MODEL = "qwen3-30b-a3b-thinking-fp8"
DEFAULT_WORKERS = 8
MAX_RETRIES = 3

OUTPUT_DIR = Path("data/synthetic")
REJECTED_PATH = OUTPUT_DIR / "rejected_v10mt.jsonl"

# Master document filenames (resolved dynamically from --gap-dir)
_MASTER_GUIDE_FILENAME = "HA_MASTER_GUIDE_2026.md"
_TECHNICAL_CHANGELOG_FILENAME = "technical_changelog_2026.md"

# Type distribution (identical to V10)
DIST_NOMINAL = 0.50
DIST_CONTRAST = 0.30
DIST_ERROR_RECOVERY = 0.20

# Evol-Instruct difficulty levels
EVOL_LEVELS = ["easy", "medium", "hard"]

# ══════════════════════════════════════════════════════════════════════
# PYDANTIC MODEL FOR TOOL_CALL VALIDATION
# ══════════════════════════════════════════════════════════════════════


class ToolCallModel(BaseModel):
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


def _render(template_str: str, **kwargs) -> str:
    """Render a prompt template using string.Template (safe with JSON braces)."""
    return Template(template_str).safe_substitute(**kwargs)


# ══════════════════════════════════════════════════════════════════════
# LEGACY CODE DETECTORS  (regex patterns — kept in Python)
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
# LOGGER
# ══════════════════════════════════════════════════════════════════════
logger = logging.getLogger("FactoryV10MT")
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter("[V10-MT %(levelname)s] %(message)s"))
logger.addHandler(_handler)

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


def build_user_nominal(frag: Dict, difficulty: str) -> str:
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


def build_user_contrast(frag: Dict) -> str:
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


def build_user_error_recovery(frag: Dict) -> str:
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


def get_fragments(filename: str, code: str) -> List[Dict]:
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
    return fragments


# ══════════════════════════════════════════════════════════════════════
# LDI VALIDATION (V17.2 Dynamic — ported from V10)
# ══════════════════════════════════════════════════════════════════════


def validate_ldi(
    code_len: int, reasoning_len: int, f_subtype: str
) -> Tuple[bool, float, str]:
    """Validate Length-Density Index: code vs reasoning ratio."""
    if reasoning_len == 0:
        return False, 0.0, "Zero reasoning"
    ldi = round(code_len / reasoning_len, 3)

    if f_subtype in ["test", "doc"]:
        if reasoning_len < 50:
            return False, ldi, "Reasoning too short for doc/test"
        return True, ldi, "Pass (Doc/Test Mode)"

    K_FACTOR = 1200
    BASE_THRESHOLD = 0.10
    dynamic_limit = BASE_THRESHOLD * (code_len / (code_len + K_FACTOR))

    if code_len > 0 and code_len < 100 and ldi > 0.01:
        return True, ldi, "Pass (Micro-Snippet Exception)"

    if ldi < dynamic_limit:
        return False, ldi, f"Verbosity (LDI {ldi} < Dynamic {round(dynamic_limit, 3)})"

    return True, ldi, f"Pass (Dynamic Threshold {round(dynamic_limit, 3)})"


# ══════════════════════════════════════════════════════════════════════
# EXAMPLE TYPE ASSIGNMENT
# ══════════════════════════════════════════════════════════════════════


def assign_example_type(
    frag: Dict, has_legacy: bool = False
) -> Tuple[str, Optional[str]]:
    """Assign type by V10 distribution: 50% nominal, 30% contrast, 20% error_recovery.

    ANTI-SCHIZOPHRENIA FILTER:
    If has_legacy=True, FORCE contrast or error_recovery (NEVER nominal).
    """
    if has_legacy:
        if random.random() < 0.60:
            return "contrast", None
        else:
            return "error_recovery", None

    roll = random.random()
    if roll < DIST_NOMINAL:
        difficulty = random.choice(EVOL_LEVELS)
        return "nominal", difficulty
    elif roll < DIST_NOMINAL + DIST_CONTRAST:
        return "contrast", None
    else:
        return "error_recovery", None


# ══════════════════════════════════════════════════════════════════════
# EXTRACTION & PYDANTIC VALIDATION
# ══════════════════════════════════════════════════════════════════════


def extract_and_validate(text: str) -> Tuple[Optional[ToolCallModel], str]:
    """Extract reasoning and strictly validate <tool_call> JSON."""
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


# ══════════════════════════════════════════════════════════════════════
# ASYNC-SAFE FILE WRITERS
# ══════════════════════════════════════════════════════════════════════


class AsyncFileWriter:
    """Async-safe JSONL writer with asyncio lock."""

    def __init__(self, path: Path):
        self.path = path
        self._lock = asyncio.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    async def write(self, record: Dict):
        async with self._lock:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ══════════════════════════════════════════════════════════════════════
# PROGRESS TRACKER
# ══════════════════════════════════════════════════════════════════════


class ProgressTracker:
    """Async-safe progress tracker with tqdm."""

    def __init__(self, total: int):
        self.total = total
        self.accepted = 0
        self.rejected = 0
        self.by_type = {"nominal": 0, "contrast": 0, "error_recovery": 0}
        self.by_difficulty = {"easy": 0, "medium": 0, "hard": 0}
        self.legacy_detected = 0
        self.gold_injected = 0
        self.gold_skipped = 0
        self._lock = asyncio.Lock()
        self.pbar = tqdm(
            total=total,
            desc="\U0001f680 V10-MT Generating",
            unit="sample",
            ncols=220,
            dynamic_ncols=False,
        )

    async def record(
        self,
        status: str,
        example_type: str,
        difficulty: Optional[str],
        gold_injected: bool = True,
        has_legacy: bool = False,
    ):
        async with self._lock:
            if status == "accepted":
                self.accepted += 1
                self.by_type[example_type] = self.by_type.get(example_type, 0) + 1
                if difficulty:
                    self.by_difficulty[difficulty] = (
                        self.by_difficulty.get(difficulty, 0) + 1
                    )
                if has_legacy:
                    self.legacy_detected += 1
                if gold_injected:
                    self.gold_injected += 1
                else:
                    self.gold_skipped += 1
            else:
                self.rejected += 1
            self.pbar.update(1)
            self.pbar.set_postfix_str(
                f"OK={self.accepted}, KO={self.rejected}, "
                f"N={self.by_type.get('nominal', 0)}, "
                f"C={self.by_type.get('contrast', 0)}, "
                f"E={self.by_type.get('error_recovery', 0)}, "
                f"GI={self.gold_injected}, GS={self.gold_skipped}"
            )

    def close(self):
        self.pbar.close()

    def summary(self) -> str:
        lines = [
            f"\n{'=' * 60}",
            "\U0001f4ca SUMMARY V10-MT (MULTI-TURN DIVERSIFIED)",
            f"{'=' * 60}",
            f"  Total processed: {self.accepted + self.rejected}",
            f"  \u2705 Accepted:      {self.accepted}",
            f"  \u274c Rejected:      {self.rejected}",
            "",
            "  By type:",
            f"    Nominal (Evol):   {self.by_type.get('nominal', 0)}",
            f"    Contrast 23\u219226:   {self.by_type.get('contrast', 0)}",
            f"    Error Recovery:   {self.by_type.get('error_recovery', 0)}",
            "",
            "  Evol-Instruct breakdown:",
            f"    Easy:   {self.by_difficulty.get('easy', 0)}",
            f"    Medium: {self.by_difficulty.get('medium', 0)}",
            f"    Hard:   {self.by_difficulty.get('hard', 0)}",
            "",
            "  \U0001f6e1\ufe0f  ANTI-SCHIZOPHRENIA FILTER:",
            f"    Legacy detected in:  {self.legacy_detected} fragments",
            f"    Gold Injection OK:   {self.gold_injected} (clean 2026 code)",
            f"    Gold Injection SKIP: {self.gold_skipped} (legacy → model generates 2026)",
            f"{'=' * 60}",
        ]
        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════
# ASYNC MULTI-TURN GENERATION  (core engine)
# ══════════════════════════════════════════════════════════════════════


async def generate_multiturn_sample_async(
    client: AsyncOpenAI,
    model: str,
    frag: Dict,
    example_type: str,
    evol_difficulty: Optional[str],
    master: str,
    changelog: str,
    semaphore: asyncio.Semaphore,
    has_legacy: bool = False,
    legacy_patterns: Optional[List[str]] = None,
) -> Dict:
    """Generate a 4-turn MULTI-TURN sample.

    Difference from V10:
    - V10 makes 1 LLM call → 2-turn conversation (user → assistant)
    - V10-MT makes 2 LLM calls → 4-turn trajectory:
        Turn 1: user request
        Turn 2: assistant + tool_call (write_to_file) — with Gold Injection
        Turn 3: tool response (simulated)
        Turn 4: assistant + tool_call (attempt_completion)

    Gold Injection is applied in Turn 2, identical to V10.
    """
    # Select system prompt and user prompt by type
    if example_type == "nominal":
        system_prompt = build_system_nominal(master, changelog)
        user_msg = build_user_nominal(frag, evol_difficulty)
    elif example_type == "contrast":
        system_prompt = build_system_contrast(master, changelog)
        user_msg = build_user_contrast(frag)
    else:  # error_recovery
        system_prompt = build_system_error_recovery(master, changelog)
        user_msg = build_user_error_recovery(frag)

    last_error = ""
    last_response = ""

    async with semaphore:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                temp = 0.3 if attempt == 1 else 0.1

                # ══ LLM CALL 1: Tool Call (write_to_file) ══
                response1 = await client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_msg},
                    ],
                    temperature=temp,
                    max_tokens=16384,
                    stop=["<|im_end|>"],
                )
                raw1 = response1.choices[0].message.content
                last_response = raw1

                # Extract and validate with Pydantic
                tool_call, reasoning1 = extract_and_validate(raw1)
                if not tool_call:
                    raise ValueError("JSON Validation Failed in Tool Call (Turn 2)")

                if tool_call.name != "write_to_file":
                    raise ValueError(
                        f"Expected write_to_file, got {tool_call.name} (Turn 2)"
                    )

                # LDI validation
                code_content = tool_call.arguments.get("content", "")
                code_len = len(code_content)
                is_valid, ldi, msg = validate_ldi(
                    code_len, len(reasoning1), frag["subtype"]
                )
                if not is_valid:
                    raise ValueError(f"LDI Fail: {msg}")

                # ══ CONDITIONAL GOLD INJECTION (identical to V10) ══
                gold_injected = False
                if not has_legacy:
                    # Clean 2026 code → safe Gold Injection
                    tool_call.arguments["content"] = frag["original"]
                    gold_injected = True
                else:
                    # Legacy detected → keep model's 2026 code
                    logger.debug(
                        "⚠️  GOLD SKIP [%s] legacy detected: %s",
                        frag["name"],
                        "; ".join(legacy_patterns or [])[:200],
                    )

                # Rebuild Turn 2 (assistant with tool_call post-Gold-Injection)
                tool_json_injected = {
                    "name": tool_call.name,
                    "arguments": tool_call.arguments,
                }
                turn2_content = (
                    f"{reasoning1}\n</think>"
                    f"<tool_call>\n{json.dumps(tool_json_injected, ensure_ascii=False)}\n</tool_call>"
                )

                # Turn 3: Simulated tool response
                turn3_content = json.dumps(
                    {
                        "status": "success",
                        "message": f"Archivo {tool_call.arguments.get('path', 'unknown')} escrito correctamente.",
                        "bytes_written": len(
                            json.dumps(
                                tool_call.arguments.get("content", ""),
                                ensure_ascii=False,
                            )
                        ),
                    },
                    ensure_ascii=False,
                )

                # ══ LLM CALL 2: Closure (attempt_completion) ══
                response2 = await client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_msg},
                        {"role": "assistant", "content": turn2_content},
                        {"role": "tool", "content": turn3_content},
                    ],
                    temperature=0.1,
                    max_tokens=4096,
                    stop=["<|im_end|>"],
                )
                raw2 = response2.choices[0].message.content

                closure_call, reasoning2 = extract_and_validate(raw2)
                if not closure_call:
                    raise ValueError("JSON Validation Failed in Closure (Turn 4)")
                if closure_call.name != "attempt_completion":
                    raise ValueError(
                        f"Expected attempt_completion, got {closure_call.name} (Turn 4)"
                    )

                # Rebuild Turn 4
                closure_json = {
                    "name": closure_call.name,
                    "arguments": closure_call.arguments,
                }
                turn4_content = (
                    f"{reasoning2}\n</think>"
                    f"<tool_call>\n{json.dumps(closure_json, ensure_ascii=False)}\n</tool_call>"
                )

                # Generate IDs
                frag_hash = hashlib.md5(
                    f"{frag['name']}_{example_type}_{evol_difficulty or ''}".encode()
                ).hexdigest()[:12]
                sample_id = f"v10mt_{example_type}_{frag_hash}"
                ck_key = make_checkpoint_key(frag["name"], frag["virtual_filename"])

                # filter_text (for downstream dedup)
                filter_text = f"{reasoning1}\n\n{turn2_content.split('</think>')[-1]}"

                return {
                    "status": "accepted",
                    "sample": {
                        "id": sample_id,
                        "conversation": [
                            {"role": "user", "content": user_msg},
                            {"role": "assistant", "content": turn2_content},
                            {"role": "tool", "content": turn3_content},
                            {"role": "assistant", "content": turn4_content},
                        ],
                        "metadata": {
                            "curation": {"kept": True},
                            "factory_version": "v10.0-mt",
                            "example_type": example_type,
                            "evol_difficulty": evol_difficulty,
                            "ldi": ldi,
                            "fragment_name": frag["name"],
                            "source_file": frag["virtual_filename"],
                            "gold_injected": gold_injected,
                            "legacy_detected": has_legacy,
                            "legacy_patterns": legacy_patterns or [],
                            "checkpoint_key": ck_key,
                        },
                        "filter_text": filter_text,
                    },
                }

            except Exception as e:
                last_error = str(e)
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(0.5 * attempt)
                    continue

    return {
        "status": "rejected",
        "reason": f"Failed after {MAX_RETRIES} tries. Last: {last_error}",
        "raw_full_response": last_response,
        "fragment_name": frag["name"],
        "example_type": example_type,
        "checkpoint_key": make_checkpoint_key(frag["name"], frag["virtual_filename"]),
    }


# ══════════════════════════════════════════════════════════════════════
# MAIN PIPELINE: PROCESS FRAGMENT
# ══════════════════════════════════════════════════════════════════════


async def process_fragment(
    client: AsyncOpenAI,
    model: str,
    frag: Dict,
    master: str,
    changelog: str,
    semaphore: asyncio.Semaphore,
    writer_ok: AsyncFileWriter,
    writer_bad: AsyncFileWriter,
    tracker: ProgressTracker,
):
    """Process a fragment: detect legacy, assign type, generate multi-turn, write."""
    # Detect legacy patterns in the fragment's gold code
    legacy_patterns = detect_legacy_patterns(frag.get("original", ""))
    has_legacy = len(legacy_patterns) > 0

    if has_legacy:
        logger.debug(
            "\U0001f50d LEGACY detected in '%s': %s",
            frag["name"],
            "; ".join(legacy_patterns)[:200],
        )

    # Assign type (if legacy → force contrast/error_recovery)
    example_type, evol_difficulty = assign_example_type(frag, has_legacy=has_legacy)

    result = await generate_multiturn_sample_async(
        client,
        model,
        frag,
        example_type,
        evol_difficulty,
        master,
        changelog,
        semaphore,
        has_legacy=has_legacy,
        legacy_patterns=legacy_patterns,
    )

    if result["status"] == "accepted":
        await writer_ok.write(result["sample"])
        gold_injected = result["sample"]["metadata"].get("gold_injected", True)
    else:
        await writer_bad.write(
            {
                "frag": result.get("fragment_name", "unknown"),
                "type": result.get("example_type", "unknown"),
                "reason": result["reason"],
                "legacy_detected": has_legacy,
                "legacy_patterns": legacy_patterns,
                "checkpoint_key": result.get("checkpoint_key", ""),
                "full_response": result.get("raw_full_response", "")[:5000],
            }
        )
        gold_injected = False

    await tracker.record(
        result["status"],
        example_type,
        evol_difficulty,
        gold_injected=gold_injected,
        has_legacy=has_legacy,
    )


# ══════════════════════════════════════════════════════════════════════
# MAIN ASYNC
# ══════════════════════════════════════════════════════════════════════


async def main_async(args):
    """Async entry point: load docs, collect fragments, run pipeline."""
    # Load master documents (fail-fast)
    master, changelog = load_master_docs(args._gap_dir)
    logger.info(
        "Master Guide: %d chars | Changelog: %d chars", len(master), len(changelog)
    )

    # Configure async client
    client = AsyncOpenAI(base_url=args.base_url, api_key=args.api_key)

    # Collect fragments from all raw files (identical to V10)
    raw_dir = Path(args.raw_dir)
    all_files = sorted(list(raw_dir.glob("*.txt")))
    if args.limit:
        all_files = all_files[: args.limit]

    logger.info("Scanning %d files in %s...", len(all_files), raw_dir)

    all_fragments = []
    for file_path in all_files:
        try:
            chunks = get_file_chunks(file_path.read_text(errors="ignore"))
            for v_name, code in chunks:
                all_fragments.extend(get_fragments(v_name, code))
        except Exception as e:
            logger.warning("Error processing %s: %s", file_path, e)

    logger.info("Total fragments discovered: %d", len(all_fragments))

    # Test mode
    if args.test:
        all_fragments = all_fragments[: args.test]
        logger.info("\U0001f9ea TEST MODE: Limited to %d fragments", args.test)

    if not all_fragments:
        logger.error("No fragments found. Check data/raw/")
        return

    # Pre-scan: count fragments with legacy
    legacy_count = sum(
        1 for f in all_fragments if detect_legacy_patterns(f.get("original", ""))
    )
    clean_count = len(all_fragments) - legacy_count
    logger.info(
        "\U0001f6e1\ufe0f  Pre-scan: %d clean fragments (Gold OK) | %d with legacy (Gold SKIP)",
        clean_count,
        legacy_count,
    )

    # Configure output
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_path = OUTPUT_DIR / f"v10mt_diversified_{timestamp}.jsonl"
    rejected_path = OUTPUT_DIR / f"v10mt_rejected_{timestamp}.jsonl"

    if args.output:
        output_path = Path(args.output)

    # RESUME
    done_keys = set()
    if args.resume:
        output_path = Path(args.resume)
        stem = output_path.stem
        rejected_path = (
            output_path.parent / f"{stem.replace('diversified', 'rejected')}.jsonl"
        )
        if not rejected_path.exists():
            rejected_path = output_path.parent / f"{stem}_rejected.jsonl"
        done_keys = load_checkpoint(output_path, rejected_path)
        if done_keys:
            before = len(all_fragments)
            all_fragments = [
                f
                for f in all_fragments
                if make_checkpoint_key(f["name"], f["virtual_filename"])
                not in done_keys
            ]
            logger.info(
                "\U0001f504 RESUME: %d already processed, %d pending (of %d total)",
                before - len(all_fragments),
                len(all_fragments),
                before,
            )
            if not all_fragments:
                logger.info("\u2705 All fragments already processed. Nothing to do.")
                return

    writer_ok = AsyncFileWriter(output_path)
    writer_bad = AsyncFileWriter(rejected_path)
    semaphore = asyncio.Semaphore(args.workers)
    tracker = ProgressTracker(len(all_fragments))

    logger.info(
        "\U0001f680 V10-MT MULTI-TURN DIVERSIFIED: %d fragments | %d workers | model: %s",
        len(all_fragments),
        args.workers,
        args.model,
    )
    logger.info("\U0001f4c1 Output: %s", output_path)
    logger.info("\U0001f4c1 Rejected: %s", rejected_path)
    logger.info(
        "\U0001f4ca Target distribution: Nominal %.0f%% | Contrast %.0f%% | Error Recovery %.0f%%",
        DIST_NOMINAL * 100,
        DIST_CONTRAST * 100,
        DIST_ERROR_RECOVERY * 100,
    )

    # Launch all tasks
    tasks = [
        process_fragment(
            client,
            args.model,
            frag,
            master,
            changelog,
            semaphore,
            writer_ok,
            writer_bad,
            tracker,
        )
        for frag in all_fragments
    ]

    await asyncio.gather(*tasks)

    tracker.close()
    print(tracker.summary())


# ══════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════


def parse_args():
    parser = argparse.ArgumentParser(
        description="AEGF (Architect-Expert-Gap-Forge) V10-MT — Multi-Turn Diversified Architect",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test mode: 3 fragments, 4 workers
  python agentic_gen.py --test 3 --workers 4

  # Full production: 16 workers for Blackwell
  python agentic_gen.py --workers 16

  # Limit to 10 raw files
  python agentic_gen.py --limit 10 --workers 8

  # RESUME interrupted execution
  python agentic_gen.py --resume data/synthetic/v10mt_diversified_20260223.jsonl --workers 16

  # Custom model and output
  python agentic_gen.py --model qwen3-32b --output data/my_dataset.jsonl
        """,
    )
    parser.add_argument(
        "--test",
        type=int,
        default=None,
        metavar="N",
        help="\U0001f9ea Test mode: process only N fragments",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Limit to N raw input files",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        metavar="W",
        help=f"Async parallel workers (default: {DEFAULT_WORKERS})",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help=f"Inference model (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default=DEFAULT_BASE_URL,
        help=f"vLLM server URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=DEFAULT_API_KEY,
        help="Server API key",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        metavar="PATH",
        help="Custom JSONL output path",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Seed for reproducibility (default: 42)",
    )
    parser.add_argument(
        "--resume",
        type=str,
        default=None,
        metavar="PATH",
        help="\U0001f504 Resume: path to previous output JSONL.",
    )
    parser.add_argument(
        "--gap-dir",
        type=str,
        default=None,
        metavar="DIR",
        help="Directory containing master documents (default: data/Gap relative to project root)",
    )
    parser.add_argument(
        "--taxonomy",
        type=str,
        default=None,
        metavar="PATH",
        help="Path to agentic_taxonomy.yaml (default: auto-resolved from project root)",
    )
    parser.add_argument(
        "--raw-dir",
        type=str,
        default="data/raw/homeassistant-main_txt",
        metavar="DIR",
        help="Input directory with packed .txt files (default: data/raw/homeassistant-main_txt)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    random.seed(args.seed)

    # Resolve base_dir (project root: 3 levels up from this file)
    base_dir = Path(__file__).resolve().parent.parent.parent

    # Resolve taxonomy path
    if args.taxonomy:
        taxonomy_path = Path(args.taxonomy)
    else:
        taxonomy_path = (
            base_dir
            / "configs"
            / "taxonomy"
            / "home_assistant"
            / "hacs_expert"
            / "agentic_taxonomy.yaml"
        )

    if not taxonomy_path.exists():
        raise FileNotFoundError(
            f"Taxonomy file not found: {taxonomy_path}. "
            "Use --taxonomy to specify the correct path."
        )

    load_taxonomy(taxonomy_path)
    logger.info(
        "Taxonomy loaded: %d error templates, %d legacy patterns, %d tools",
        len(HA_ERROR_TEMPLATES),
        len(LEGACY_2023_PATTERNS),
        len(TOOLS_DEFINITION),
    )

    # Resolve gap directory
    if args.gap_dir:
        args._gap_dir = Path(args.gap_dir)
    else:
        args._gap_dir = base_dir / "data" / "Gap"

    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
