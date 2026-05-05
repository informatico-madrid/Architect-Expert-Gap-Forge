#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
AEGF (Architect-Expert-Gap-Forge) V10.0 — Async Diversified Architect Edition
===============================================================================
BASE: V9 / V17.5 (Hybrid Architect)
KEY FEATURES:
1. DATASET DIVERSIFICATION:
   - 50% Evolved Nominal examples (Evol-Instruct: easy/medium/hard)
   - 30% Contrast / Correction examples (2023 vs 2026)
   - 20% Error Recovery examples
2. ASYNC SCALING WITH SEMAPHORE:
   - asyncio + AsyncOpenAI for max throughput on Blackwell (2x RTX 5090)
   - Configurable workers via --workers (default 8)
3. TEST MODE:
   - --test N: Process only N total fragments to validate the pipeline
4. GOLD INJECTION: Original source code is ALWAYS injected as correct output.
5. OUTPUT FORMAT:
   {"id": "...", "conversation": [...], "metadata": {...}, "filter_text": "..."}
6. PROMPT TAXONOMY: All Spanish prompt text loaded from external YAML taxonomy
   (configs/taxonomy/home_assistant/hacs_expert/prompts_taxonomy.yaml).
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
from pathlib import Path
from string import Template
from typing import List, Dict, Tuple, Optional

import yaml
from openai import AsyncOpenAI
from tqdm import tqdm

# ======================================================================
# CONFIGURATION
# ======================================================================
DEFAULT_BASE_URL = "http://localhost:8000/v1"
_DEFAULT_API_KEY = os.getenv("API_KEY")
if _DEFAULT_API_KEY is None:
    raise ValueError("API_KEY environment variable is required. Please set it before running.")
DEFAULT_API_KEY = _DEFAULT_API_KEY
DEFAULT_MODEL = "qwen3-5-35b-a3b-nvfp4"
DEFAULT_WORKERS = 8
MAX_RETRIES = 3

OUTPUT_DIR = Path("data/synthetic")
REJECTED_PATH = OUTPUT_DIR / "rejected_v10.jsonl"

# Master document filenames (resolved at runtime via --gap-dir)
_MASTER_GUIDE_FILENAME = "HA_MASTER_GUIDE_2026.md"
_TECHNICAL_CHANGELOG_FILENAME = "technical_changelog_2026.md"
_JINJA_YAML_GUIDE_FILENAME = "HA_JINJA_YAML_GUIDE_2026.md"

# Example type distribution
DIST_NOMINAL = 0.50
DIST_CONTRAST = 0.30
DIST_ERROR_RECOVERY = 0.20

# Evol-Instruct difficulty levels (uniformly distributed within nominal)
EVOL_LEVELS = ["easy", "medium", "hard"]

# ======================================================================
# TAXONOMY LOADING
# ======================================================================
# Module-level containers populated by load_taxonomy() at startup.
_TAX: dict = {}
HA_ERROR_TEMPLATES: list = []
LEGACY_2023_PATTERNS: list = []
JINJA_HA_ERROR_TEMPLATES: list = []
JINJA_LEGACY_2023_PATTERNS: list = []
THEORY_QUESTION_TEMPLATES: list = []
TOOLS_DEFINITION: list = []


def load_taxonomy(path: Path) -> None:
    """Load prompt taxonomy YAML and populate module-level variables.

    Must be called once at startup before any prompt builder is invoked.
    """
    global _TAX, HA_ERROR_TEMPLATES, LEGACY_2023_PATTERNS
    global JINJA_HA_ERROR_TEMPLATES, JINJA_LEGACY_2023_PATTERNS
    global THEORY_QUESTION_TEMPLATES, TOOLS_DEFINITION

    with open(path, "r", encoding="utf-8") as f:
        _TAX = yaml.safe_load(f)

    HA_ERROR_TEMPLATES = _TAX["ha_error_templates"]
    LEGACY_2023_PATTERNS = _TAX["legacy_2023_patterns"]
    JINJA_HA_ERROR_TEMPLATES = _TAX["jinja_ha_error_templates"]
    JINJA_LEGACY_2023_PATTERNS = _TAX["jinja_legacy_2023_patterns"]
    THEORY_QUESTION_TEMPLATES = _TAX["theory_question_templates"]
    TOOLS_DEFINITION = _TAX["tools_definition"]


def _render(template_str: str, **kwargs) -> str:
    """Render a prompt template using safe_substitute ($ placeholders).

    Uses string.Template so that literal { } in JSON examples within
    prompts are left intact — only $var placeholders are substituted.
    """
    return Template(template_str).safe_substitute(**kwargs)


def _prompt(key: str) -> str:
    """Retrieve a prompt template string from the loaded taxonomy.

    Args:
        key: Dot-separated path under 'prompts', e.g. "system.python.base".
    """
    node = _TAX["prompts"]
    for part in key.split("."):
        node = node[part]
    return node


# ======================================================================
# LEGACY CODE DETECTORS (Python integrations)
# ======================================================================
# Applied against frag['original'] BEFORE Gold Injection.
# If any matches, the fragment contains legacy 2023/2024 code and
# Gold Injection is SKIPPED to avoid weight schizophrenia.

LEGACY_CODE_DETECTORS = [
    # --- Storage / Runtime Data ---
    (r"hass\.data\[", "hass.data[] dict pattern -> entry.runtime_data"),
    (r"hass\.data\.setdefault", "hass.data.setdefault() -> entry.runtime_data"),
    # --- Unit Constants Legacy ---
    (
        r"\bTEMP_CELSIUS\b|\bTEMP_FAHRENHEIT\b|\bTEMP_KELVIN\b",
        "Legacy TEMP_* constants -> UnitOfTemperature enum",
    ),
    (
        r"\bUNIT_PERCENTAGE\b|\bPERCENTAGE\b(?=\s*[,\)])",
        "Legacy UNIT_PERCENTAGE -> UnitOfMeasurement enum",
    ),
    (
        r"\bLENGTH_METERS\b|\bLENGTH_KILOMETERS\b|\bLENGTH_MILES\b",
        "Legacy LENGTH_* constants -> UnitOfLength enum",
    ),
    (
        r"\bMASS_GRAMS\b|\bMASS_KILOGRAMS\b|\bVOLUME_LITERS\b",
        "Legacy MASS_*/VOLUME_* constants -> UnitOf* enums",
    ),
    (
        r"\bPRESSURE_BAR\b|\bPRESSURE_PA\b|\bPRESSURE_HPA\b",
        "Legacy PRESSURE_* constants -> UnitOfPressure enum",
    ),
    (
        r"\bENERGY_KILO_WATT_HOUR\b|\bENERGY_WATT_HOUR\b|\bPOWER_WATT\b|\bPOWER_KILO_WATT\b",
        "Legacy ENERGY_*/POWER_* -> UnitOfEnergy/UnitOfPower enums",
    ),
    # --- Setup singular ---
    (
        r"async_forward_entry_setup\b(?!s)",
        "Singular async_forward_entry_setup -> async_forward_entry_setups",
    ),
    # --- String device_class ---
    (
        r'device_class\s*=\s*["\'](?:temperature|humidity|pressure|energy|power|battery|voltage|current)',
        "String literal device_class -> SensorDeviceClass/BinarySensorDeviceClass enum",
    ),
    (r'_attr_device_class\s*=\s*["\']', "String _attr_device_class -> Enum"),
    # --- Synchronous Entity pattern ---
    (r"def update\(self\)", "Synchronous update(self) -> CoordinatorEntity + async"),
    (r"def\s+async_update\(self\)", "Direct async_update -> CoordinatorEntity pattern"),
    # --- YAML-only ---
    (r"PLATFORM_SCHEMA\s*=", "YAML-only PLATFORM_SCHEMA -> ConfigFlow required"),
    # --- Blocking I/O in async ---
    (
        r"requests\.get\(|requests\.post\(|requests\.put\(|requests\.delete\(",
        "Blocking requests.* in code -> aiohttp/async_add_executor_job",
    ),
    (r"(?<!await\s)time\.sleep\(", "Blocking time.sleep() -> await asyncio.sleep()"),
    (r"urllib\.request\.urlopen", "Blocking urllib -> aiohttp"),
    # --- Deprecated state/entity attributes ---
    (r"\bself\._state\s*=", "Legacy self._state = X -> native_value property"),
    (r"\bself\._attr_state\s*=", "Legacy self._attr_state -> native_value property"),
    (r"@property\s*\n\s*def\s+state\(self\)", "Legacy state property -> native_value"),
    # --- Old-style entity registration ---
    (r"add_entities\(\[.*\]\s*,\s*True\)", "Legacy polling=True -> CoordinatorEntity"),
]


# ======================================================================
# LEGACY CODE DETECTORS (Jinja / YAML templates)
# ======================================================================
# Based on HA_JINJA_YAML_GUIDE_2026.md (breaking changes 2024.10 -> 2026.2)

JINJA_LEGACY_CODE_DETECTORS = [
    # --- 2024.10: Singular syntax in automations ---
    (r"^\s*trigger:\s*$", "Singular 'trigger:' -> 'triggers:' (2024.10)"),
    (r"^\s*condition:\s*$", "Singular 'condition:' -> 'conditions:' (2024.10)"),
    (r"^\s*action:\s*$", "Singular 'action:' -> 'actions:' (2024.10)"),
    (
        r"^\s*-\s*platform:\s*(?:state|numeric_state|time|event|mqtt|webhook|sun|zone|tag)\b",
        "Legacy 'platform:' in trigger -> 'trigger:' (2024.10)",
    ),
    # --- 2024.12: Variable this vs value ---
    (r"\bthis\.state\b", "Legacy this.state -> use 'value' variable (2024.12)"),
    (
        r"\bthis\.attributes\b",
        "Legacy this.attributes -> use 'value' or new 'this' semantics (2024.12)",
    ),
    # --- 2024.12: Non-snake_case states ---
    (
        r"==\s*['\"](?:[A-Z][a-z]+\s+[A-Z]|[A-Z]{2,}[a-z])",
        "Non-snake_case state format -> migrate to snake_case (2024.12)",
    ),
    # --- 2025.8: None -> unknown in binary_sensor ---
    (
        r"or\s+None\s*[%}]",
        "Implicit None in binary_sensor -> use explicit 'false' (2025.8)",
    ),
    (
        r"is_state\([^)]*['\"]standby['\"]",
        "State 'standby' removed -> use 'off' (2025.8)",
    ),
    (
        r"state_attr\([^)]*['\"]battery_level['\"]",
        "Attribute 'battery_level' removed -> use dedicated sensor (2025.8)",
    ),
    (
        r"state_attr\([^)]*['\"]battery['\"]",
        "Attribute 'battery' removed -> use dedicated sensor (2025.8)",
    ),
    # --- 2025.12: Legacy template entities ---
    (
        r"platform:\s*template",
        "Legacy 'platform: template' -> root 'template:' syntax (2025.12, dies 2026.6)",
    ),
    (
        r"value_template:",
        "Legacy 'value_template:' -> use 'state:' in modern syntax (2025.12)",
    ),
    # --- Best practices: filters without default ---
    (
        r"\|\s*float\s*[^(]",
        "float without default -> use '| float(0)' with default value",
    ),
    (r"\|\s*int\s*[^(]", "int without default -> use '| int(0)' with default value"),
    # --- as_timestamp legacy ---
    (
        r"\bas_timestamp\b",
        "as_timestamp (epoch float) -> prefer as_datetime (timezone-aware)",
    ),
]


def detect_legacy_patterns(code: str, subtype: str = "code") -> List[str]:
    """Detect legacy 2023/2024 patterns in source code or templates.

    Args:
        code: Source code or template to analyze.
        subtype: 'jinja', 'yaml' for templates; anything else for Python.

    Returns:
        List of descriptions for legacy patterns found.
        Empty list if the code is clean 2026.
    """
    found = []
    is_template = subtype in ("jinja", "yaml")
    detectors = JINJA_LEGACY_CODE_DETECTORS if is_template else LEGACY_CODE_DETECTORS
    # Jinja/YAML detectors use ^ anchors that require MULTILINE
    flags = re.MULTILINE if is_template else 0
    for pattern, description in detectors:
        if re.search(pattern, code, flags):
            found.append(description)
    return found


# ======================================================================
# Logger
# ======================================================================
logger = logging.getLogger("FactoryV10")
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter("[V10 %(levelname)s] %(message)s"))
logger.addHandler(_handler)


# ======================================================================
# MASTER DOCUMENT LOADING  (fail-fast on missing files)
# ======================================================================


def load_master_docs(gap_dir: Path) -> Tuple[str, str, str]:
    """Load master documents from the gap directory.

    Raises FileNotFoundError immediately if any required document is missing.
    """
    master_path = gap_dir / _MASTER_GUIDE_FILENAME
    changelog_path = gap_dir / _TECHNICAL_CHANGELOG_FILENAME
    jinja_path = gap_dir / _JINJA_YAML_GUIDE_FILENAME

    for path, label in [
        (master_path, "Master Guide"),
        (changelog_path, "Technical Changelog"),
        (jinja_path, "Jinja/YAML Guide"),
    ]:
        if not path.exists():
            raise FileNotFoundError(
                f"{label} not found: {path}. "
                f"Use --gap-dir to specify the correct directory."
            )

    master = master_path.read_text(encoding="utf-8", errors="ignore")
    changelog = changelog_path.read_text(encoding="utf-8", errors="ignore")
    jinja_guide = jinja_path.read_text(encoding="utf-8", errors="ignore")
    return master, changelog, jinja_guide


# ======================================================================
# SYSTEM PROMPT BUILDERS
# ======================================================================


def _base_system_block(master: str, changelog: str) -> str:
    """Shared base block for all Python integration system prompts."""
    tools_json = json.dumps(TOOLS_DEFINITION, indent=2, ensure_ascii=False)
    return _render(
        _prompt("system.python.base"),
        tools_json=tools_json,
        master=master,
        changelog=changelog,
    )


def build_system_nominal(master: str, changelog: str) -> str:
    """System prompt for nominal examples (Evol-Instruct)."""
    return _base_system_block(master, changelog) + _prompt(
        "system.python.nominal_suffix"
    )


def build_system_contrast(master: str, changelog: str) -> str:
    """System prompt for contrast examples (2023 vs 2026)."""
    return _base_system_block(master, changelog) + _prompt(
        "system.python.contrast_suffix"
    )


def build_system_error_recovery(master: str, changelog: str) -> str:
    """System prompt for error recovery examples."""
    return _base_system_block(master, changelog) + _prompt(
        "system.python.error_recovery_suffix"
    )


# ======================================================================
# SYSTEM PROMPT BUILDERS — Jinja / YAML templates
# ======================================================================


def _base_system_block_jinja(jinja_guide: str) -> str:
    """Shared base block for Jinja/YAML template system prompts."""
    tools_json = json.dumps(TOOLS_DEFINITION, indent=2, ensure_ascii=False)
    return _render(
        _prompt("system.jinja.base"), tools_json=tools_json, jinja_guide=jinja_guide
    )


def build_system_nominal_jinja(jinja_guide: str) -> str:
    """System prompt for nominal Jinja/YAML template examples."""
    return _base_system_block_jinja(jinja_guide) + _prompt(
        "system.jinja.nominal_suffix"
    )


def build_system_contrast_jinja(jinja_guide: str) -> str:
    """System prompt for Jinja/YAML contrast examples."""
    return _base_system_block_jinja(jinja_guide) + _prompt(
        "system.jinja.contrast_suffix"
    )


def build_system_error_recovery_jinja(jinja_guide: str) -> str:
    """System prompt for Jinja/YAML error recovery examples."""
    return _base_system_block_jinja(jinja_guide) + _prompt(
        "system.jinja.error_recovery_suffix"
    )


# ======================================================================
# USER PROMPT BUILDERS — Python integrations
# ======================================================================


def build_user_nominal(frag: Dict, difficulty: str) -> str:
    """Build user prompt for nominal examples with Evol-Instruct difficulty."""
    subs = dict(
        context=frag["context"],
        virtual_filename=frag["virtual_filename"],
        name=frag["name"],
        skeleton=frag["skeleton"],
    )

    if difficulty == "easy":
        return _render(_prompt("user.python.nominal_easy"), **subs)
    elif difficulty == "medium":
        return _render(_prompt("user.python.nominal_medium"), **subs)
    else:  # hard
        # 50% chance to omit explicit "2026" anchor
        # -> model learns to produce modern code without year dependency
        if random.random() < 0.50:
            # Anchor-free variant: production + best practices only
            variants = _prompt("user.python.nominal_hard_anchor_free")
            return _render(random.choice(variants), **subs)
        else:
            # Variant with explicit "2026" anchor
            return _render(_prompt("user.python.nominal_hard_anchor"), **subs)


def build_user_contrast(frag: Dict) -> str:
    """Build user prompt where user employs 2023 pattern (model must correct)."""
    pattern = random.choice(LEGACY_2023_PATTERNS)
    return _render(
        _prompt("user.python.contrast"),
        context=frag["context"],
        virtual_filename=frag["virtual_filename"],
        name=frag["name"],
        skeleton=frag["skeleton"],
        legacy_code=pattern["legacy_code"],
    )


def build_user_error_recovery(frag: Dict) -> str:
    """Build user prompt with a simulated HA error."""
    err_template = random.choice(HA_ERROR_TEMPLATES)
    # Customize error with fragment data
    error_msg = err_template["error"].format(
        entity=f"sensor.{frag['name'].lower()}",
        component=frag["virtual_filename"].replace(".py", "").replace("/", "."),
        entry_id="abc123def456",
        seconds="12",
        literal="temperature",
        entity_id=f"sensor.{frag['name'].lower()}_value",
    )
    return _render(
        _prompt("user.python.error_recovery"),
        context=frag["context"],
        virtual_filename=frag["virtual_filename"],
        name=frag["name"],
        skeleton=frag["skeleton"],
        error_msg=error_msg,
    )


# ======================================================================
# USER PROMPT BUILDERS — Jinja / YAML templates
# ======================================================================


def build_user_nominal_jinja(frag: Dict, difficulty: str) -> str:
    """Build nominal user prompt for Jinja/YAML templates."""
    subs = dict(
        context=frag["context"],
        virtual_filename=frag["virtual_filename"],
        name=frag["name"],
        skeleton=frag["skeleton"],
    )

    if difficulty == "easy":
        return _render(_prompt("user.jinja.nominal_easy"), **subs)
    elif difficulty == "medium":
        return _render(_prompt("user.jinja.nominal_medium"), **subs)
    else:  # hard
        if random.random() < 0.50:
            variants = _prompt("user.jinja.nominal_hard_anchor_free")
            return _render(random.choice(variants), **subs)
        else:
            return _render(_prompt("user.jinja.nominal_hard_anchor"), **subs)


def build_user_contrast_jinja(frag: Dict) -> str:
    """Build contrast user prompt for Jinja/YAML (legacy -> modern)."""
    # Select legacy pattern coherent with fragment file type
    vfn = frag.get("virtual_filename", "")
    is_yaml_frag = vfn.endswith((".yaml", ".yml")) or frag.get("subtype", "") == "yaml"
    target_ctx = "yaml" if is_yaml_frag else "jinja"
    pool = [
        p for p in JINJA_LEGACY_2023_PATTERNS if p.get("context_type") == target_ctx
    ]
    if not pool:  # defensive fallback
        pool = JINJA_LEGACY_2023_PATTERNS
    pattern = random.choice(pool)
    lang = "yaml" if target_ctx == "yaml" else "jinja"
    return _render(
        _prompt("user.jinja.contrast"),
        context=frag["context"],
        virtual_filename=frag["virtual_filename"],
        name=frag["name"],
        skeleton=frag["skeleton"],
        legacy_code=pattern["legacy_code"],
        lang=lang,
    )


def build_user_error_recovery_jinja(frag: Dict) -> str:
    """Build error recovery user prompt for Jinja/YAML templates."""
    # Select error coherent with fragment file type
    vfn = frag.get("virtual_filename", "")
    is_yaml_frag = vfn.endswith((".yaml", ".yml")) or frag.get("subtype", "") == "yaml"
    target_ctx = "yaml" if is_yaml_frag else "jinja"
    pool = [t for t in JINJA_HA_ERROR_TEMPLATES if t.get("context_type") == target_ctx]
    if not pool:  # defensive fallback
        pool = JINJA_HA_ERROR_TEMPLATES
    err_template = random.choice(pool)
    # Customize error with fragment data
    error_msg = err_template["error"].format(
        entity=frag["name"].lower().replace(" ", "_"),
        domain="sensor",
        template_source=frag["virtual_filename"],
        automation=frag["name"].lower().replace(" ", "_"),
        script=frag["name"].lower().replace(" ", "_"),
        variable="result",
    )
    return _render(
        _prompt("user.jinja.error_recovery"),
        context=frag["context"],
        virtual_filename=frag["virtual_filename"],
        name=frag["name"],
        skeleton=frag["skeleton"],
        error_msg=error_msg,
    )


# ======================================================================
# THEORY: System prompt and user prompt builders
# ======================================================================


def build_system_theory(master: str, changelog: str) -> str:
    """System prompt for theory / doctrine HA 2026 examples."""
    return _render(_prompt("system.theory"), master=master, changelog=changelog)


def get_theory_fragments(master: str, changelog: str) -> List[Dict]:
    """Extract theory fragments (sections) from master documents."""
    fragments = []
    for doc_name, doc_content in [
        ("MASTER_GUIDE", master),
        ("TECHNICAL_CHANGELOG", changelog),
    ]:
        if not doc_content:
            continue
        # Split by level 1 and 2 headers
        sections = re.split(r"(^#{1,2} .+)", doc_content, flags=re.MULTILINE)
        for i in range(1, len(sections), 2):
            header = sections[i].strip()
            body = sections[i + 1] if i + 1 < len(sections) else ""
            title = header.lstrip("#").strip()
            if len(body.strip()) < 100:  # skip minimal sections
                continue
            fragments.append(
                {
                    "name": title,
                    "type": "theory",
                    "subtype": "doc",
                    "section_content": f"{header}\n{body}",
                    "original": f"{header}\n{body}",
                    "source_doc": doc_name,
                    "context": f"Section from {doc_name}",
                    "virtual_filename": f"theory/{doc_name.lower()}.md",
                }
            )
    return fragments


def build_user_theory(theory_frag: Dict) -> Tuple[str, str]:
    """Build a diversified theory user prompt. Returns (user_msg, theory_subtype)."""
    template = random.choice(THEORY_QUESTION_TEMPLATES)
    user_msg = template["template"].format(section_title=theory_frag["name"])
    return user_msg, template["type"]


async def generate_theory_sample_async(
    client: AsyncOpenAI,
    model: str,
    theory_frag: Dict,
    master: str,
    changelog: str,
    semaphore: asyncio.Semaphore,
) -> Dict:
    """Generate a theory sample (no Gold Injection — pure doctrinal knowledge)."""
    system_prompt = build_system_theory(master, changelog)
    user_msg, theory_subtype = build_user_theory(theory_frag)

    last_error = ""
    last_response = ""

    async with semaphore:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = await client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_msg},
                    ],
                    temperature=0.4 if attempt == 1 else 0.2,
                    max_tokens=8192,
                    stop=["<|im_end|>"],
                )
                raw = response.choices[0].message.content
                last_response = raw

                # Extract reasoning and answer
                reasoning = ""
                answer = raw
                if "<think>" in raw and "</think>" in raw:
                    think_part = raw.split("<think>")[1].split("</think>")[0].strip()
                    reasoning = think_part
                    answer = raw.split("</think>")[-1].strip()
                elif "</think>" in raw:
                    reasoning = raw.split("</think>")[0].strip()
                    answer = raw.split("</think>")[-1].strip()

                if len(answer) < 150:
                    raise ValueError(f"Theory answer too short: {len(answer)} chars")

                # Format: reasoning + </think> + answer (no tool_call)
                final_assistant = f"{reasoning}\n</think>\n\n{answer}"

                rep = theory_frag.get("_rep")
                ck_key = make_checkpoint_key(
                    theory_frag["name"], theory_frag["virtual_filename"], rep=rep
                )
                frag_hash = hashlib.md5(
                    f"theory_{theory_frag['name']}_{theory_subtype}_{rep}".encode()
                ).hexdigest()[:12]

                return {
                    "status": "accepted",
                    "sample": {
                        "id": f"v10_theory_{frag_hash}",
                        "conversation": [
                            {"role": "user", "content": user_msg},
                            {"role": "assistant", "content": final_assistant},
                        ],
                        "metadata": {
                            "curation": {"kept": True},
                            "factory_version": "v10.0",
                            "example_type": "theory",
                            "theory_subtype": theory_subtype,
                            "section_name": theory_frag["name"],
                            "source_doc": theory_frag["source_doc"],
                            "checkpoint_key": ck_key,
                        },
                        "filter_text": final_assistant,
                    },
                }

            except Exception as e:
                last_error = str(e)
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(0.5 * attempt)
                    continue

    return {
        "status": "rejected",
        "reason": f"Theory failed after {MAX_RETRIES} tries. Last: {last_error}",
        "raw_full_response": last_response,
        "fragment_name": theory_frag["name"],
        "example_type": "theory",
        "checkpoint_key": make_checkpoint_key(
            theory_frag["name"],
            theory_frag["virtual_filename"],
            rep=theory_frag.get("_rep"),
        ),
    }


# ======================================================================
# POST-VALIDATION OF MODEL OUTPUT
# ======================================================================

# Legacy patterns FORBIDDEN in model-generated code.
# Stricter than source detectors: if the model produces these patterns
# in its output, the example is toxic for training.
OUTPUT_POISON_DETECTORS = [
    # Returning None where it should be false (HA 2025.8)
    (r"\{\{-?\s*None\s*-?\}\}", "Output returns None (must be false, HA 2025.8)"),
    # as_timestamp in generated code (deprecated)
    (
        r"\bas_timestamp\s*\(",
        "Output uses as_timestamp() (deprecated, use as_datetime)",
    ),
    # platform: template in generated code (deprecated 2025.12)
    (r"platform:\s*template", "Output uses 'platform: template' (deprecated 2025.12)"),
    # Singular syntax in generated code
    (r"^\s*trigger:\s*\n\s*-", "Output uses singular 'trigger:' (deprecated 2024.10)"),
    (
        r"^\s*condition:\s*\n\s*-",
        "Output uses singular 'condition:' (deprecated 2024.10)",
    ),
    (r"^\s*action:\s*\n\s*-", "Output uses singular 'action:' (deprecated 2024.10)"),
    # func() callable in Jinja (impossible — macro params are not callable)
    (r"\{\{-?\s*func\s*\(", "Output invokes func() as callable (impossible in Jinja2)"),
    # Hallucinated private helper: _private_macro() not defined in fragment
    (r"\{\{-?\s*_\w+\s*\(", "Output calls undefined private helper (_helper())"),
]


def post_validate_output(
    generated_code: str, example_type: str, subtype: str = "code"
) -> List[str]:
    """Validate model-generated code for toxic patterns.

    For CONTRAST/ERROR_RECOVERY examples, the model should produce modern code.
    If its output contains legacy patterns, it's toxic.
    For NOMINAL with gold_injection, the code is replaced so this doesn't apply.

    Returns:
        List of toxic pattern descriptions found.
        Empty list if the output is clean.
    """
    found = []
    flags = re.MULTILINE
    for pattern, description in OUTPUT_POISON_DETECTORS:
        if re.search(pattern, generated_code, flags):
            found.append(description)
    return found


# ======================================================================
# RAW -> JSON PARSER (inherited from V9, improved)
# ======================================================================


def parse_raw_response(text: str) -> Tuple[Dict, str]:
    """Surgical parser: extracts RAW content and packages it as valid JSON.

    Supports <write_action> and fallback to <tool_call>.
    """
    # 1. Extract Reasoning
    reasoning = ""
    if "<think>" in text:
        try:
            parts = text.split("<think>")
            if "</think>" in parts[1]:
                reasoning = parts[1].split("</think>")[0].strip()
        except (IndexError, ValueError):
            pass

    # 2. Extract Action Block (XML-like)
    if "<write_action>" not in text:
        if "<tool_call>" in text:
            try:
                tool_part = text.split("<tool_call>")[1].split("</tool_call>")[0]
                return json.loads(tool_part), reasoning
            except (IndexError, json.JSONDecodeError, ValueError):
                pass
        raise ValueError("No <write_action> or <tool_call> found")

    action_block = text.split("<write_action>")[1].split("</write_action>")[0]

    # 3. Extract Path
    path_match = re.search(r"<path>(.*?)</path>", action_block, re.DOTALL)
    if not path_match:
        raise ValueError("Missing <path> tag")
    file_path = path_match.group(1).strip()

    # 4. Extract Content
    try:
        start_tag = "<content>"
        end_tag = "</content>"
        start_idx = action_block.index(start_tag) + len(start_tag)
        end_idx = action_block.rindex(end_tag)
        file_content = action_block[start_idx:end_idx].strip("\n")
    except ValueError:
        raise ValueError("Malformed <content> block")

    return {
        "name": "write_to_file",
        "arguments": {"path": file_path, "content": file_content},
    }, reasoning


# ======================================================================
# CHUNKING AND FRAGMENTATION (inherited from V9)
# ======================================================================


def get_file_chunks(content: str) -> List[Tuple[str, str]]:
    """Split packed .txt file into (filename, code) tuples."""
    parts = re.split(r"--- FILE: (.*?) ---\n", content)
    chunks = []
    for i in range(1, len(parts), 2):
        if i + 1 < len(parts):
            chunks.append((parts[i].strip(), parts[i + 1].strip()))
    return chunks


def get_fragments(
    filename: str, code: str, allowed_extensions: Optional[set] = None
) -> List[Dict]:
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


# ======================================================================
# LDI VALIDATION (V17.2 Dynamic)
# ======================================================================


def validate_ldi(
    code_len: int, reasoning_len: int, f_subtype: str
) -> Tuple[bool, float, str]:
    """Validate code-to-reasoning Length Density Index."""
    if reasoning_len == 0:
        return False, 0.0, "Zero reasoning"
    ldi = round(code_len / reasoning_len, 3)

    if f_subtype in ["test", "doc", "jinja", "yaml"]:
        if reasoning_len < 50:
            return False, ldi, "Reasoning too short for doc/test/template"
        return True, ldi, "Pass (Doc/Test/Template Mode)"

    K_FACTOR = 1200
    BASE_THRESHOLD = 0.10
    dynamic_limit = BASE_THRESHOLD * (code_len / (code_len + K_FACTOR))

    if code_len > 0 and code_len < 100 and ldi > 0.01:
        return True, ldi, "Pass (Micro-Snippet Exception)"

    if ldi < dynamic_limit:
        return False, ldi, f"Verbosity (LDI {ldi} < Dynamic {round(dynamic_limit, 3)})"

    return True, ldi, f"Pass (Dynamic Threshold {round(dynamic_limit, 3)})"


# ======================================================================
# EXAMPLE TYPE ASSIGNMENT
# ======================================================================


def assign_example_type(
    frag: Dict, has_legacy: bool = False
) -> Tuple[str, Optional[str]]:
    """Assign an example type to the fragment based on distribution:
      50% nominal (easy/medium/hard), 30% contrast, 20% error_recovery
    Returns: (type, evol_difficulty | None)

    ANTI-SCHIZOPHRENIA FILTER:
    If has_legacy=True, the gold code contains 2023/2024 patterns.
    In that case we FORCE contrast or error_recovery (NEVER nominal),
    because in contrast/error_recovery the model MUST correct the legacy
    pattern, and Gold Injection is SKIPPED (model generates 2026 code).
    Assigning nominal with legacy gold = weight schizophrenia.
    """
    if has_legacy:
        # Legacy gold is PERFECT for teaching correction (contrast/error_recovery)
        # but TOXIC for nominal (think=2026 + gold=legacy = schizophrenia)
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


# ======================================================================
# ASYNC SAMPLE GENERATION
# ======================================================================


async def generate_sample_async(
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
    jinja_guide: str = "",
) -> Dict:
    """Generate a sample asynchronously, respecting the concurrency semaphore.

    If has_legacy=True, Gold Injection is SKIPPED — the model generates its own
    corrected 2026 code. This prevents injecting obsolete code as 'gold'.

    For Jinja/YAML fragments (subtype in ['jinja', 'yaml']), uses template-specific
    prompt builders with JINJA_YAML_GUIDE as truth anchor.
    """

    # === BIFURCATION: Jinja/YAML vs Python ===
    is_template = frag.get("subtype") in ("jinja", "yaml")

    if is_template:
        # Template-specific prompt builders for Jinja/YAML
        if example_type == "nominal":
            system_prompt = build_system_nominal_jinja(jinja_guide)
            user_msg = build_user_nominal_jinja(frag, evol_difficulty)
        elif example_type == "contrast":
            system_prompt = build_system_contrast_jinja(jinja_guide)
            user_msg = build_user_contrast_jinja(frag)
        else:  # error_recovery
            system_prompt = build_system_error_recovery_jinja(jinja_guide)
            user_msg = build_user_error_recovery_jinja(frag)
    else:
        # Python prompt builders (original behavior)
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

                response = await client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_msg},
                    ],
                    temperature=temp,
                    max_tokens=16384,
                    stop=["<|im_end|>"],
                )
                raw_content = response.choices[0].message.content
                last_response = raw_content

                # Robust parsing
                tool_json, reasoning = parse_raw_response(raw_content)

                # LDI Validation
                code_len = len(tool_json["arguments"]["content"])
                is_valid, ldi, msg = validate_ldi(
                    code_len, len(reasoning), frag["subtype"]
                )

                if not is_valid:
                    raise ValueError(f"LDI Fail: {msg}")

                # === POST-VALIDATION OF MODEL OUTPUT ===
                generated_code = tool_json["arguments"]["content"]
                poison_patterns = post_validate_output(
                    generated_code, example_type, frag.get("subtype", "code")
                )

                # === CONDITIONAL GOLD INJECTION ===
                # If fragment has legacy patterns, do NOT inject gold
                # (avoids schizophrenia: think=2026, code=legacy)
                gold_injected = False
                cot_schizophrenia = False
                if not has_legacy:
                    # -- Detect CoT schizophrenia --
                    # Model reasoned correctly but its output contains toxic
                    # patterns. Even if we inject gold, the pair
                    # (toxic-CoT + gold-code) teaches the model to hallucinate
                    # private helpers or use deprecated APIs in reasoning.
                    if poison_patterns:
                        cot_schizophrenia = True
                        logger.warning(
                            "CoT SCHIZOPHRENIA [%s] (%s): output has %d "
                            "toxic patterns before gold injection: %s",
                            frag["name"],
                            example_type,
                            len(poison_patterns),
                            "; ".join(poison_patterns)[:200],
                        )
                        # Do NOT clear poison_patterns -> is_kept=False propagates
                    else:
                        # Clean output -> safe gold injection
                        poison_patterns = []
                    # Inject original source code (gold) as final output
                    tool_json["arguments"]["content"] = frag["original"]
                    gold_injected = True
                else:
                    # Legacy detected -> keep model code (2026)
                    # Model was already instructed to correct/migrate
                    logger.debug(
                        "GOLD SKIP [%s] legacy detected: %s",
                        frag["name"],
                        "; ".join(legacy_patterns or [])[:200],
                    )

                # Rebuild assistant message in training format
                # NOTE: No opening <think> — only closing </think>,
                # consistent with Platinum V18 format for SFT.
                final_assistant_msg = (
                    f"{reasoning}\n</think>"
                    f"<tool_call>\n{json.dumps(tool_json)}\n</tool_call>"
                )

                # Generate unique ID and checkpoint key
                frag_hash = hashlib.md5(
                    f"{frag['name']}_{example_type}_{evol_difficulty or ''}".encode()
                ).hexdigest()[:12]
                sample_id = f"v10_{example_type}_{frag_hash}"
                ck_key = make_checkpoint_key(frag["name"], frag["virtual_filename"])

                # filter_text = full reasoning (for posterior dedup)
                filter_text = (
                    f"{reasoning}\n\n{final_assistant_msg.split('</think>')[-1]}"
                )

                # === AUTO CURATION: flag toxic samples ===
                is_kept = True
                poison_reasons = []
                if poison_patterns:
                    is_kept = False
                    poison_reasons = poison_patterns
                    logger.warning(
                        "POISON [%s] (%s) %d toxic patterns in output: %s",
                        frag["name"],
                        example_type,
                        len(poison_patterns),
                        "; ".join(poison_patterns)[:200],
                    )

                return {
                    "status": "accepted",
                    "sample": {
                        "id": sample_id,
                        "conversation": [
                            {"role": "user", "content": user_msg},
                            {"role": "assistant", "content": final_assistant_msg},
                        ],
                        "metadata": {
                            "curation": {
                                "kept": is_kept,
                                **(
                                    {
                                        "poison_patterns": poison_reasons,
                                        "auto_rejected": True,
                                        **(
                                            {"cot_schizophrenia": True}
                                            if cot_schizophrenia
                                            else {}
                                        ),
                                    }
                                    if poison_reasons
                                    else {}
                                ),
                            },
                            "factory_version": "v10.0",
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
                    await asyncio.sleep(0.5 * attempt)  # backoff
                    continue

    return {
        "status": "rejected",
        "reason": f"Failed after {MAX_RETRIES} tries. Last: {last_error}",
        "raw_full_response": last_response,
        "fragment_name": frag["name"],
        "example_type": example_type,
        "checkpoint_key": make_checkpoint_key(frag["name"], frag["virtual_filename"]),
    }


# ======================================================================
# CHECKPOINT / RESUME
# ======================================================================


def make_checkpoint_key(
    frag_name: str, virtual_filename: str, rep: Optional[int] = None
) -> str:
    """Generate deterministic checkpoint key for a fragment.

    Does NOT depend on example_type or evol_difficulty (which are random).
    This way, when resuming, the same fragment always generates the same key
    regardless of what type it was assigned before the crash.
    """
    raw = f"{frag_name}::{virtual_filename}"
    if rep is not None:
        raw += f"::rep{rep}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def load_checkpoint(output_path: Path, rejected_path: Path) -> set:
    """Load checkpoint keys from existing JSONL files.

    Scans both the output (accepted) and rejected files to avoid
    reprocessing either.

    Returns:
        Set of already-processed checkpoint_keys.
    """
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
                        # Accepted: metadata.checkpoint_key
                        ck = record.get("metadata", {}).get("checkpoint_key")
                        # Rejected: checkpoint_key at top level
                        if not ck:
                            ck = record.get("checkpoint_key")
                        if ck:
                            done_keys.add(ck)
                    except json.JSONDecodeError:
                        logger.warning(
                            "Checkpoint: invalid JSON at %s line %d", path, line_num
                        )
        except Exception as e:
            logger.warning("Checkpoint: error reading %s: %s", path, e)
    return done_keys


# ======================================================================
# ASYNC-SAFE FILE WRITERS
# ======================================================================


class AsyncFileWriter:
    """Thread-safe JSONL writer with asyncio lock."""

    def __init__(self, path: Path):
        self.path = path
        self._lock = asyncio.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    async def write(self, record: Dict):
        async with self._lock:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ======================================================================
# PROGRESS TRACKER
# ======================================================================


class ProgressTracker:
    """Async-safe progress tracker with tqdm."""

    def __init__(self, total: int, mode: str = "code"):
        self.total = total
        self.mode = mode
        self.accepted = 0
        self.rejected = 0
        self.by_type = {"nominal": 0, "contrast": 0, "error_recovery": 0, "theory": 0}
        self.by_difficulty = {"easy": 0, "medium": 0, "hard": 0}
        self.legacy_detected = 0
        self.gold_injected = 0
        self.gold_skipped = 0
        self._lock = asyncio.Lock()
        desc = "V10 Theory" if mode == "theory" else "V10 Generating"
        self.pbar = tqdm(
            total=total, desc=desc, unit="sample", ncols=220, dynamic_ncols=False
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
                f"T={self.by_type.get('theory', 0)}, "
                f"GI={self.gold_injected}, GS={self.gold_skipped}"
            )

    def close(self):
        self.pbar.close()

    def summary(self) -> str:
        lines = [
            f"\n{'=' * 60}",
            f"SUMMARY V10.0 {'THEORY' if self.mode == 'theory' else 'ASYNC DIVERSIFIED'}",
            f"{'=' * 60}",
            f"  Total processed: {self.accepted + self.rejected}",
            f"  Accepted:        {self.accepted}",
            f"  Rejected:        {self.rejected}",
            "",
            "  By type:",
            f"    Nominal (Evol):   {self.by_type.get('nominal', 0)}",
            f"    Contrast 23->26:  {self.by_type.get('contrast', 0)}",
            f"    Error Recovery:   {self.by_type.get('error_recovery', 0)}",
            f"    Theory (Doctrine):{self.by_type.get('theory', 0)}",
        ]
        if self.mode != "theory":
            lines += [
                "",
                "  Evol-Instruct breakdown:",
                f"    Easy:   {self.by_difficulty.get('easy', 0)}",
                f"    Medium: {self.by_difficulty.get('medium', 0)}",
                f"    Hard:   {self.by_difficulty.get('hard', 0)}",
                "",
                "  ANTI-SCHIZOPHRENIA FILTER:",
                f"    Legacy detected in: {self.legacy_detected} fragments",
                f"    Gold Injection OK:  {self.gold_injected} (clean 2026 code)",
                f"    Gold Injection SKIP:{self.gold_skipped} (legacy -> model generates 2026)",
            ]
        lines.append(f"{'=' * 60}")
        return "\n".join(lines)


# ======================================================================
# MAIN ASYNC PIPELINE
# ======================================================================


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
    jinja_guide: str = "",
):
    """Process a fragment: assign type, generate, write result.

    Runs detect_legacy_patterns() to determine if the gold code contains
    2023/2024 patterns, then passes that info to assign_example_type()
    and generate_sample_async() for the anti-schizophrenia filter.

    For Jinja/YAML fragments, uses template-specific detectors and prompts.
    """
    # Detect legacy patterns in the fragment's gold code
    # Uses Jinja detectors if fragment is a template, Python otherwise
    frag_subtype = frag.get("subtype", "code")
    legacy_patterns = detect_legacy_patterns(
        frag.get("original", ""), subtype=frag_subtype
    )
    has_legacy = len(legacy_patterns) > 0

    if has_legacy:
        logger.debug(
            "LEGACY detected in '%s' [%s]: %s",
            frag["name"],
            frag_subtype,
            "; ".join(legacy_patterns)[:200],
        )

    # Assign type (if legacy -> force contrast/error_recovery)
    example_type, evol_difficulty = assign_example_type(frag, has_legacy=has_legacy)

    result = await generate_sample_async(
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
        jinja_guide=jinja_guide,
    )

    if result["status"] == "accepted":
        sample = result["sample"]
        is_kept = sample["metadata"].get("curation", {}).get("kept", True)
        if is_kept:
            await writer_ok.write(sample)
        else:
            # Auto-rejected by post-validation (poison patterns)
            await writer_bad.write(
                {
                    "frag": sample["metadata"].get("fragment_name", "unknown"),
                    "type": sample["metadata"].get("example_type", "unknown"),
                    "reason": "auto_rejected_poison",
                    "poison_patterns": sample["metadata"]["curation"].get(
                        "poison_patterns", []
                    ),
                    "legacy_detected": has_legacy,
                    "legacy_patterns": legacy_patterns,
                    "checkpoint_key": sample["metadata"].get("checkpoint_key", ""),
                    "sample": sample,
                }
            )
            logger.info(
                "SEPARATED -> rejected [%s] (%s): %s",
                sample["metadata"].get("fragment_name", "?"),
                sample["metadata"].get("example_type", "?"),
                "; ".join(sample["metadata"]["curation"].get("poison_patterns", []))[
                    :150
                ],
            )
        gold_injected = sample["metadata"].get("gold_injected", True)
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


async def main_async(args):
    """Main async pipeline entry point."""
    # Load master documents (fail-fast if missing)
    master, changelog, jinja_guide = load_master_docs(args._gap_dir)
    logger.info(
        "Master Guide: %d chars | Changelog: %d chars | Jinja Guide: %d chars",
        len(master),
        len(changelog),
        len(jinja_guide),
    )

    # Configure async client
    client = AsyncOpenAI(base_url=args.base_url, api_key=args.api_key)

    # ================================================================
    # THEORY MODE: Pure doctrine dataset from MASTER_GUIDE/CHANGELOG
    # ================================================================
    if args.theory:
        logger.info("THEORY MODE: Generating HA 2026 doctrine dataset")
        theory_frags = get_theory_fragments(master, changelog)

        if not theory_frags:
            logger.error("No sections found in MASTER_GUIDE/CHANGELOG")
            return

        # Multiply fragments by diversified repetitions
        # Each section is processed theory_reps times with different random questions
        theory_reps = args.theory_reps
        expanded_frags = []
        for frag in theory_frags:
            for rep in range(theory_reps):
                expanded_frags.append({**frag, "_rep": rep})

        if args.test:
            expanded_frags = expanded_frags[: args.test]
            logger.info("TEST MODE THEORY: Limited to %d fragments", args.test)

        logger.info(
            "Theory: %d sections x %d reps = %d examples | %d workers",
            len(theory_frags),
            theory_reps,
            len(expanded_frags),
            args.workers,
        )

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = OUTPUT_DIR / f"v10_theory_{timestamp}.jsonl"
        rejected_path = OUTPUT_DIR / f"v10_theory_rejected_{timestamp}.jsonl"
        if args.output:
            output_path = Path(args.output)

        # RESUME: load checkpoint if exists
        done_keys = set()
        if args.resume:
            output_path = Path(args.resume)
            stem = output_path.stem
            rejected_path = (
                output_path.parent
                / f"{stem.replace('theory', 'theory_rejected')}.jsonl"
            )
            if not rejected_path.exists():
                rejected_path = output_path.parent / f"{stem}_rejected.jsonl"
            done_keys = load_checkpoint(output_path, rejected_path)
            if done_keys:
                before = len(expanded_frags)
                expanded_frags = [
                    tf
                    for tf in expanded_frags
                    if make_checkpoint_key(
                        tf["name"], tf["virtual_filename"], rep=tf.get("_rep")
                    )
                    not in done_keys
                ]
                logger.info(
                    "RESUME: %d already processed, %d pending (of %d total)",
                    before - len(expanded_frags),
                    len(expanded_frags),
                    before,
                )
                if not expanded_frags:
                    logger.info("All fragments already processed. Nothing to do.")
                    return

        writer_ok = AsyncFileWriter(output_path)
        writer_bad = AsyncFileWriter(rejected_path)
        semaphore = asyncio.Semaphore(args.workers)
        tracker = ProgressTracker(len(expanded_frags), mode="theory")

        logger.info("Theory Output: %s", output_path)

        async def process_theory(tfrag):
            result = await generate_theory_sample_async(
                client, args.model, tfrag, master, changelog, semaphore
            )
            if result["status"] == "accepted":
                await writer_ok.write(result["sample"])
            else:
                await writer_bad.write(
                    {
                        "frag": result.get("fragment_name", "unknown"),
                        "type": "theory",
                        "reason": result["reason"],
                        "checkpoint_key": result.get("checkpoint_key", ""),
                        "full_response": result.get("raw_full_response", "")[:5000],
                    }
                )
            await tracker.record(
                result["status"], "theory", None, gold_injected=False, has_legacy=False
            )

        tasks = [process_theory(tf) for tf in expanded_frags]
        await asyncio.gather(*tasks)

        tracker.close()
        print(tracker.summary())
        return

    # ================================================================
    # NORMAL MODE: Diversified code dataset with legacy filter
    # ================================================================

    # Collect fragments from all raw files
    raw_dir = Path(args.raw_dir)
    all_files = sorted(list(raw_dir.glob("*.txt")))
    if args.limit:
        all_files = all_files[: args.limit]

    # Parse extension filter (if provided)
    allowed_ext = None
    if args.extensions:
        allowed_ext = set()
        for ext in args.extensions:
            e = ext.strip().lower()
            if not e.startswith("."):
                e = "." + e
            allowed_ext.add(e)
        logger.info("Extension filter active: %s", allowed_ext)

    logger.info("Scanning %d files in %s...", len(all_files), raw_dir)

    all_fragments = []
    for file_path in all_files:
        try:
            chunks = get_file_chunks(file_path.read_text(errors="ignore"))
            for v_name, code in chunks:
                all_fragments.extend(
                    get_fragments(v_name, code, allowed_extensions=allowed_ext)
                )
        except Exception as e:
            logger.warning("Error processing %s: %s", file_path, e)

    logger.info("Total fragments discovered: %d", len(all_fragments))

    # Test mode: limit fragments
    if args.test:
        all_fragments = all_fragments[: args.test]
        logger.info("TEST MODE: Limited to %d fragments", args.test)

    if not all_fragments:
        logger.error("No fragments found. Check data/raw/")
        return

    # Pre-scan: count fragments with legacy for info
    legacy_count = sum(
        1
        for f in all_fragments
        if detect_legacy_patterns(
            f.get("original", ""), subtype=f.get("subtype", "code")
        )
    )
    clean_count = len(all_fragments) - legacy_count
    logger.info(
        "Pre-scan: %d clean fragments (Gold OK) | %d with legacy (Gold SKIP)",
        clean_count,
        legacy_count,
    )

    # Configure output
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_path = OUTPUT_DIR / f"v10_diversified_{timestamp}.jsonl"
    rejected_path = OUTPUT_DIR / f"v10_rejected_{timestamp}.jsonl"

    if args.output:
        output_path = Path(args.output)

    # RESUME: load checkpoint if exists
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
                "RESUME: %d already processed, %d pending (of %d total)",
                before - len(all_fragments),
                len(all_fragments),
                before,
            )
            if not all_fragments:
                logger.info("All fragments already processed. Nothing to do.")
                return

    writer_ok = AsyncFileWriter(output_path)
    writer_bad = AsyncFileWriter(rejected_path)
    semaphore = asyncio.Semaphore(args.workers)
    tracker = ProgressTracker(len(all_fragments), mode="code")

    logger.info(
        "V10 ASYNC DIVERSIFIED: %d fragments | %d workers | model: %s",
        len(all_fragments),
        args.workers,
        args.model,
    )
    logger.info("Output: %s", output_path)
    logger.info("Rejected: %s", rejected_path)
    logger.info(
        "Target distribution: Nominal %.0f%% | Contrast %.0f%% | Error Recovery %.0f%%",
        DIST_NOMINAL * 100,
        DIST_CONTRAST * 100,
        DIST_ERROR_RECOVERY * 100,
    )

    # Launch all tasks with concurrency semaphore
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
            jinja_guide=jinja_guide,
        )
        for frag in all_fragments
    ]

    # Execute with gather (semaphore controls actual concurrency)
    await asyncio.gather(*tasks)

    tracker.close()
    print(tracker.summary())


# ======================================================================
# CLI
# ======================================================================


def parse_args():
    parser = argparse.ArgumentParser(
        description="AEGF (Architect-Expert-Gap-Forge) V10 - Async Diversified Architect",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage examples:
  # Test mode: 3 fragments, 4 workers
  python production_v10.py --test 3 --workers 4

  # Full production: 16 workers for Blackwell
  python production_v10.py --workers 16

  # Limit to 10 raw files
  python production_v10.py --limit 10 --workers 8

  # RESUME interrupted run (continues where it left off)
  python production_v10.py --resume data/synthetic/v10_diversified_20260223_092107.jsonl --workers 16

  # THEORY dataset (HA 2026 doctrine)
  python production_v10.py --theory --workers 8

  # Resume interrupted theory
  python production_v10.py --theory --resume data/synthetic/v10_theory_20260223_100000.jsonl

  # Theory with more repetitions per section
  python production_v10.py --theory --theory-reps 5 --workers 16

  # Quick theory test
  python production_v10.py --theory --test 3 --workers 4

  # Custom model and output
  python production_v10.py --model qwen3-32b --output data/my_dataset.jsonl

  # Process Jinja2 templates from custom folder
  python production_v10.py --raw-dir data/raw/homeassistant-jinja --extensions .jinja .jinja2 .yaml .yml --workers 16

  # Combine: custom folder + extensions + quick test
  python production_v10.py --raw-dir data/raw/homeassistant-jinja --extensions .jinja .jinja2 --test 10 --workers 4

  # Custom gap directory for master documents
  python production_v10.py --gap-dir /path/to/gap/docs --workers 16
        """,
    )
    parser.add_argument(
        "--test",
        type=int,
        default=None,
        metavar="N",
        help="Test mode: process only N total fragments for quick validation",
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
        help=f"Number of parallel async workers (default: {DEFAULT_WORKERS})",
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
        "--api-key", type=str, default=DEFAULT_API_KEY, help="Server API key"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        metavar="PATH",
        help="Custom JSONL output path",
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="Seed for reproducibility (default: 42)"
    )
    parser.add_argument(
        "--resume",
        type=str,
        default=None,
        metavar="PATH",
        help="Resume run: path to previous output JSONL. "
        "Reads already-processed checkpoint_keys and skips those fragments.",
    )
    parser.add_argument(
        "--raw-dir",
        type=str,
        default="data/raw/homeassistant-main_txt",
        metavar="DIR",
        help="Input directory with packed .txt files (default: data/raw/homeassistant-main_txt)",
    )
    parser.add_argument(
        "--extensions",
        type=str,
        nargs="+",
        default=None,
        metavar="EXT",
        help="Filter only files with these extensions inside .txt packs "
        "(e.g. --extensions .jinja .jinja2 .yaml .yml). Processes all if not specified.",
    )
    parser.add_argument(
        "--theory",
        action="store_true",
        default=False,
        help="Theory mode: generate pure doctrine dataset from MASTER_GUIDE and CHANGELOG",
    )
    parser.add_argument(
        "--theory-reps",
        type=int,
        default=3,
        metavar="R",
        help="Repetitions per section in --theory mode (default: 3, generates diverse questions)",
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
        help="Path to prompts_taxonomy.yaml (default: auto-resolved from project root)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    random.seed(args.seed)

    # Resolve project base directory (data_factory/)
    base_dir = Path(__file__).resolve().parent.parent.parent

    # Load prompt taxonomy
    if args.taxonomy:
        taxonomy_path = Path(args.taxonomy)
    else:
        taxonomy_path = (
            base_dir
            / "configs"
            / "taxonomy"
            / "home_assistant"
            / "hacs_expert"
            / "prompts_taxonomy.yaml"
        )
    if not taxonomy_path.exists():
        raise FileNotFoundError(f"Taxonomy file not found: {taxonomy_path}")
    load_taxonomy(taxonomy_path)
    logger.info("Taxonomy loaded: %s (%d keys)", taxonomy_path.name, len(_TAX))

    # Resolve gap directory for master documents
    if args.gap_dir:
        args._gap_dir = Path(args.gap_dir)
    else:
        args._gap_dir = base_dir / "data" / "Gap"

    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
