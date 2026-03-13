#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
Prompt Builder Module — AEGF V11.0
===================================
Single-responsibility module for all prompt construction functions used
by the factory pipeline.  Contains taxonomy loading, legacy detection,
output validation, master-doc loading, and every system/user prompt builder.
"""

import json
import logging
import random
import re
from pathlib import Path
from string import Template
from typing import Any, Dict, List, Optional, Tuple

import yaml

from src.factory.config import (
    JINJA_LEGACY_CODE_DETECTORS,
    LEGACY_CODE_DETECTORS,
    OUTPUT_POISON_DETECTORS,
    TaxonomyState,
)
from src.schemas.common import FragmentTypedDict

logger = logging.getLogger(__name__)

# ======================================================================
# MODULE STATE  (populated by load_taxonomy / set_test_state)
# ======================================================================
_TAX: dict = {}
HA_ERROR_TEMPLATES: list = []
LEGACY_2023_PATTERNS: list = []
JINJA_HA_ERROR_TEMPLATES: list = []
JINJA_LEGACY_2023_PATTERNS: list = []
THEORY_QUESTION_TEMPLATES: list = []
TOOLS_DEFINITION: list = []

# Default master document filenames (resolved at runtime via --gap-dir)
_DEFAULT_MASTER_DOCS = {
    "master_guide": "HA_MASTER_GUIDE_2026.md",
    "changelog": "technical_changelog_2026.md",
    "jinja_guide": "HA_JINJA_YAML_GUIDE_2026.md",
}
_MASTER_DOCS_MAP_FILE = "master_docs_map.yaml"


# ======================================================================
# TAXONOMY LOADING
# ======================================================================


def load_taxonomy(path: Path) -> TaxonomyState:
    """Load prompt taxonomy YAML and populate module-level variables.

    Must be called once at startup before any prompt builder is invoked.

    Args:
        path: Path to the taxonomy YAML file.

    Returns:
        TaxonomyState with the loaded data.
    """
    global _TAX, HA_ERROR_TEMPLATES, LEGACY_2023_PATTERNS
    global JINJA_HA_ERROR_TEMPLATES, JINJA_LEGACY_2023_PATTERNS
    global THEORY_QUESTION_TEMPLATES, TOOLS_DEFINITION

    with open(path, "r", encoding="utf-8") as f:
        _TAX = yaml.safe_load(f)

    HA_ERROR_TEMPLATES = _TAX.get("ha_error_templates", [])
    LEGACY_2023_PATTERNS = _TAX.get("legacy_2023_patterns", [])
    JINJA_HA_ERROR_TEMPLATES = _TAX.get("jinja_ha_error_templates", [])
    JINJA_LEGACY_2023_PATTERNS = _TAX.get("jinja_legacy_2023_patterns", [])
    THEORY_QUESTION_TEMPLATES = _TAX.get("theory_question_templates", [])
    TOOLS_DEFINITION = _TAX.get("tools_definition", [])

    return TaxonomyState(
        prompts=_TAX.get("prompts", {}),
        ha_error_templates=HA_ERROR_TEMPLATES,
        jinja_variants=JINJA_HA_ERROR_TEMPLATES,
        theory_taxonomy=_TAX,
    )


def set_test_state(state: Optional[TaxonomyState] = None) -> None:
    """Set module taxonomy state for testing.

    When called after load_taxonomy(), this is typically a no-op since
    load_taxonomy() already populates the module globals.
    Provided for API compatibility with test fixtures.
    """
    pass


# ======================================================================
# TEMPLATE HELPERS
# ======================================================================


def _render(template_str: str, **kwargs: Any) -> str:
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
# LEGACY CODE DETECTION
# ======================================================================


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
    flags = re.MULTILINE if is_template else 0
    for pattern, description in detectors:
        if re.search(pattern, code, flags):
            found.append(description)
    return found


# ======================================================================
# POST-VALIDATION OF MODEL OUTPUT
# ======================================================================


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
# MASTER DOCUMENT LOADING  (fail-fast on missing files)
# ======================================================================


def load_master_docs(
    gap_dir: Path, profile: str = "homeassistant"
) -> Tuple[str, str, str]:
    """Load master documents from the gap directory based on profile.

    Reads the master_docs_map.yaml to determine which master documents to load
    for the given profile. Falls back to default HA documents if no mapping exists.

    Args:
        gap_dir: Path to the gap directory containing master documents.
        profile: Profile name (e.g., "homeassistant", "php_hexagonal").
                 Defaults to "homeassistant".

    Returns:
        Tuple of (master_guide, changelog, jinja_guide) content strings.

    Raises:
        FileNotFoundError: If any required document is missing.
    """
    config_path = Path("configs/stage_1_discovery") / _MASTER_DOCS_MAP_FILE

    master_docs_config = _DEFAULT_MASTER_DOCS.copy()
    if config_path.exists():
        try:
            config_data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            if config_data and profile in config_data.get("profiles", {}):
                profile_docs = config_data["profiles"][profile]
                master_docs_config.update(profile_docs)
        except Exception:
            pass

    master_path = gap_dir / master_docs_config["master_guide"]
    changelog_path = gap_dir / master_docs_config["changelog"]
    jinja_path = gap_dir / master_docs_config["jinja_guide"]

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
# SYSTEM PROMPT BUILDERS — Python integrations
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


def build_user_nominal(frag: FragmentTypedDict, difficulty: str) -> str:
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
        if random.random() < 0.50:
            variants = _prompt("user.python.nominal_hard_anchor_free")
            return _render(random.choice(variants), **subs)
        else:
            return _render(_prompt("user.python.nominal_hard_anchor"), **subs)


def build_user_contrast(frag: FragmentTypedDict) -> str:
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


def build_user_error_recovery(frag: FragmentTypedDict) -> str:
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
    vfn = frag.get("virtual_filename", "")
    is_yaml_frag = vfn.endswith((".yaml", ".yml")) or frag.get("subtype", "") == "yaml"
    target_ctx = "yaml" if is_yaml_frag else "jinja"
    pool = [
        p for p in JINJA_LEGACY_2023_PATTERNS if p.get("context_type") == target_ctx
    ]
    if not pool:
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
    vfn = frag.get("virtual_filename", "")
    is_yaml_frag = vfn.endswith((".yaml", ".yml")) or frag.get("subtype", "") == "yaml"
    target_ctx = "yaml" if is_yaml_frag else "jinja"
    pool = [t for t in JINJA_HA_ERROR_TEMPLATES if t.get("context_type") == target_ctx]
    if not pool:
        pool = JINJA_HA_ERROR_TEMPLATES
    err_template = random.choice(pool)
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
# V11: FUNCTIONAL UNIT (TIPO 1) PROMPT BUILDERS
# ======================================================================


def build_system_with_blueprint(
    master: str,
    changelog: str,
    blueprint: str = "",
    local_imports: str = "[]",
    governance: str = "",
) -> str:
    """System prompt for FUNCTIONAL_UNIT fragments — injects blueprint and governance context.

    If blueprint is non-empty, appends the module architecture overview so
    the model understands the surrounding integration before generating code.

    If governance is non-empty, appends the repository coding-standards block.
    The governance rules always come LAST (highest authority) so the model
    gives them precedence over any legacy patterns it may encounter in the code.
    """
    base = _base_system_block(master, changelog)
    if blueprint:
        ctx_block = _render(
            _prompt("system.python.blueprint_context"),
            blueprint=blueprint,
            local_imports=local_imports,
        )
        base = base + ctx_block
    if governance:
        gov_block = _render(
            _prompt("system.python.governance_context"),
            governance_rules=governance,
        )
        base = base + gov_block
    return base + _prompt("system.python.nominal_suffix")


def build_user_functional_unit(frag: Dict, difficulty: Optional[str] = None) -> str:
    """Build user prompt for FUNCTIONAL_UNIT (logic + test) fragments."""
    return _render(
        _prompt("user.python.functional_unit"),
        context=frag["context"],
        virtual_filename=frag["virtual_filename"],
        name=frag["name"],
        skeleton=frag["skeleton"],
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
        sections = re.split(r"(^#{1,2} .+)", doc_content, flags=re.MULTILINE)
        for i in range(1, len(sections), 2):
            header = sections[i].strip()
            body = sections[i + 1] if i + 1 < len(sections) else ""
            title = header.lstrip("#").strip()
            if len(body.strip()) < 100:
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


# ======================================================================
# PHP LEGACY: Doctrine + snippet loader (T062)
# ======================================================================

def load_php_legacy_doctrine(base_dir: Optional[Path] = None) -> str:
    """Load the master Symfony hexagonal doctrine document for PHP legacy prompts.

    Reads ``configs/stage_2_factory/taxonomy/php_legacy/master_symfony_hex.md``
    relative to ``base_dir`` (defaults to CWD).

    Args:
        base_dir: Base directory to resolve the doctrine path from (default: cwd).

    Returns:
        Doctrine content string, or ``""`` if the file does not exist.
    """
    root = base_dir or Path.cwd()
    doctrine_path = root / "configs" / "stage_2_factory" / "taxonomy" / "php_legacy" / "master_symfony_hex.md"
    if not doctrine_path.exists():
        logger.warning("PHP doctrine file not found: %s", doctrine_path)
        return ""
    return doctrine_path.read_text(encoding="utf-8", errors="ignore")


def load_php_platform_snippet(platform: str, base_dir: Optional[Path] = None) -> str:
    """Load the platform-specific snippet for PHP legacy prompts.

    Reads ``configs/stage_2_factory/taxonomy/php_legacy/snippets/{platform}.md``
    relative to ``base_dir`` (defaults to CWD).

    Args:
        platform: Platform name (e.g. ``"oscommerce"``, ``"wordpress"``).
        base_dir: Base directory to resolve the snippet path from (default: cwd).

    Returns:
        Platform snippet content string, or ``""`` if the file does not exist.
    """
    root = base_dir or Path.cwd()
    snippet_path = root / "configs" / "stage_2_factory" / "taxonomy" / "php_legacy" / "snippets" / f"{platform}.md"
    if not snippet_path.exists():
        logger.warning("PHP platform snippet not found for '%s': %s", platform, snippet_path)
        # Fall back to generic_php
        fallback = root / "configs" / "stage_2_factory" / "taxonomy" / "php_legacy" / "snippets" / "generic_php.md"
        if fallback.exists():
            return fallback.read_text(encoding="utf-8", errors="ignore")
        return ""
    return snippet_path.read_text(encoding="utf-8", errors="ignore")


def build_system_php_legacy(
    arch: Dict,
    blueprint: str = "",
    base_dir: Optional[Path] = None,
) -> str:
    """Build system prompt for a PHP legacy LOGIC_ONLY or FUNCTIONAL_UNIT bundle.

    Activated when ``arch["LANGUAGE"] == "php"``.  Loads:
    - ``master_symfony_hex.md`` as ``${doctrine}``
    - ``snippets/{platform}.md`` as ``${platform_snippet}`` (PLATFORM field)

    Then renders ``system.php_legacy.context`` template from ``taxonomy.yaml``.

    Args:
        arch: Parsed ARCH_HEADER dict (from ``parse_bundle``).
        blueprint: Optional module blueprint context string.
        base_dir: Base directory for resolving taxonomy files (default: cwd).

    Returns:
        System prompt string, or empty string if LANGUAGE != "php".
    """
    if arch.get("LANGUAGE", "").lower() != "php":
        return ""

    doctrine = load_php_legacy_doctrine(base_dir)
    platform = arch.get("PLATFORM", "generic_php")
    platform_snippet = load_php_platform_snippet(platform, base_dir)

    # Render system prompt using taxonomy.yaml template
    try:
        template_str = _prompt("system.php_legacy.context")
        return _render(
            template_str,
            doctrine=doctrine,
            platform_snippet=platform_snippet,
            blueprint=blueprint,
            platform=platform,
            legacy_action=arch.get("LEGACY_ACTION", ""),
        )
    except Exception as exc:
        logger.warning("Could not render PHP legacy system prompt: %s", exc)
        # Fallback: return doctrine + snippet inline
        return (
            f"# PHP Legacy Modernization Expert\n\n"
            f"## Symfony Hexagonal Architecture\n{doctrine}\n\n"
            f"## Platform Anti-Patterns ({platform})\n{platform_snippet}"
        )


__all__ = [
    "build_system_nominal",
    "build_system_contrast",
    "build_system_error_recovery",
    "build_system_nominal_jinja",
    "build_system_contrast_jinja",
    "build_system_error_recovery_jinja",
    "build_system_with_blueprint",
    "build_system_theory",
    "build_user_nominal",
    "build_user_contrast",
    "build_user_error_recovery",
    "build_user_nominal_jinja",
    "build_user_contrast_jinja",
    "build_user_error_recovery_jinja",
    "build_user_functional_unit",
    "build_user_theory",
    "detect_legacy_patterns",
    "get_theory_fragments",
    "load_master_docs",
    "load_taxonomy",
    "post_validate_output",
    "set_test_state",
    "load_php_legacy_doctrine",
    "load_php_platform_snippet",
    "build_system_php_legacy",
    "_render",
    "_prompt",
]
