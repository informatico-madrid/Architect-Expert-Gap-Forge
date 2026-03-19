#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
AEGF Factory Pipeline Runner Module
===================================
Handles async sample generation, fragment processing, and main pipeline orchestration.
"""

import asyncio
import json
import logging
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from openai import AsyncOpenAI

from src.factory.config import (
    DIST_NOMINAL,
    DIST_CONTRAST,
    DIST_ERROR_RECOVERY,
    OUTPUT_DIR,
    TaxonomyState,
)
from src.factory.prompt_builder import (
    build_system_nominal,
    build_system_contrast,
    build_system_error_recovery,
    build_system_nominal_jinja,
    build_system_contrast_jinja,
    build_system_error_recovery_jinja,
    build_system_with_blueprint,
    build_system_theory,
    build_user_nominal,
    build_user_contrast,
    build_user_error_recovery,
    build_user_nominal_jinja,
    build_user_contrast_jinja,
    build_user_error_recovery_jinja,
    build_user_functional_unit,
    build_user_theory,
    detect_legacy_patterns,
    get_theory_fragments,
    load_master_docs,
    load_taxonomy,
    post_validate_output,
)
from src.factory.fragment_extractor import get_v2_fragments, parse_bundle
from src.factory.ldi_validator import assign_example_type, validate_ldi
from src.factory.checkpoint import (
    AsyncFileWriter,
    CheckpointSet,
    ProgressTracker,
    load_checkpoint,
    make_checkpoint_key,
)

# ======================================================================
# LOGGING
# ======================================================================

logger = logging.getLogger(__name__)

# ======================================================================
# PHP VALIDATION JUDGE — Level 1 (T063)
# ======================================================================

_PHP_BINARY: Optional[str] = shutil.which("php")
_REQUIRED_SECTIONS = frozenset(
    ["[DEBT_DIAGNOSTIC]", "[MODERN_PROPOSAL]", "[MAPPING_LOGIC]"]
)
_PHP_CODE_BLOCK_RE = re.compile(r"```php\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)


def validate_php_output(
    generated_content: str,
    frag: Dict[str, Any],
    failures_log: Path,
) -> List[str]:
    """ValidationJudge Level 1 for PHP legacy output.

    Performs two checks:
    1. Structural: asserts presence of [DEBT_DIAGNOSTIC], [MODERN_PROPOSAL],
       [MAPPING_LOGIC] section headers.
    2. Syntax lint: runs ``php -l`` on each ```php ... ``` block found in
       the MODERN_PROPOSAL section (skipped gracefully if ``php`` binary
       is unavailable).

    Failures are appended to *failures_log* as JSON-Lines.

    Args:
        generated_content: Raw LLM output text.
        frag: Fragment dict (for logging context).
        failures_log: Path to ``validation_failures.jsonl`` log file.

    Returns:
        List of failure reason strings (empty → validation passed).
    """
    failures: List[str] = []

    # --- Structural check ---
    for section in _REQUIRED_SECTIONS:
        if section not in generated_content:
            failures.append(f"missing_section:{section}")

    # --- PHP syntax lint ---
    if _PHP_BINARY:
        php_blocks = _PHP_CODE_BLOCK_RE.findall(generated_content)
        for idx, block in enumerate(php_blocks):
            tmp_path: Optional[str] = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    suffix=".php",
                    delete=False,
                    encoding="utf-8",
                ) as tmp:
                    tmp_path = tmp.name
                    # Ensure valid PHP opening tag
                    if not block.lstrip().startswith("<?"):
                        tmp.write("<?php\n")
                    tmp.write(block)
                result = subprocess.run(
                    [_PHP_BINARY, "-l", tmp_path],
                    capture_output=True,
                    text=True,
                    timeout=3,
                )
                if result.returncode != 0:
                    stderr = (result.stderr or result.stdout).strip()
                    failures.append(f"php_syntax_block_{idx}:{stderr[:200]}")
            except subprocess.TimeoutExpired:
                logger.debug(
                    "php -l timed out on block %d for %s", idx, frag.get("name")
                )
            except Exception as exc:
                logger.debug("php lint error on block %d: %s", idx, exc)
            finally:
                if tmp_path:
                    try:
                        Path(tmp_path).unlink(missing_ok=True)
                    except Exception:
                        pass
    else:
        logger.debug(
            "PHP binary not found — skipping syntax lint for %s", frag.get("name")
        )

    # --- Log failures ---
    if failures:
        try:
            failures_log.parent.mkdir(parents=True, exist_ok=True)
            with failures_log.open("a", encoding="utf-8") as fh:
                fh.write(
                    json.dumps(
                        {
                            "fragment": frag.get("name", ""),
                            "virtual_filename": frag.get("virtual_filename", ""),
                            "failures": failures,
                        }
                    )
                    + "\n"
                )
        except OSError as exc:
            logger.warning("Could not write to validation_failures.jsonl: %s", exc)

    return failures


# ======================================================================
# THINK FILTER - LAZY LOADING
# ======================================================================

_think_filter_apply: Optional[Any] = None


def _get_think_filter() -> Optional[Any]:
    """Lazy-load the think filter module.

    Replaces the module-level dynamic import block (lines 49-65 in production_v11.py)
    with a lazy-loading function that is called on first use.

    Returns:
        The apply_to_record function from think_filter module, or None if unavailable.
    """
    global _think_filter_apply
    if _think_filter_apply is not None:
        return _think_filter_apply

    try:
        from src.factory.think_filter import apply_to_record as _think_filter_apply
    except ImportError:
        try:
            import importlib.util as _ilu
            import os as _os

            _tf_path = _os.path.join(_os.path.dirname(__file__), "think_filter.py")
            _tf_spec = _ilu.spec_from_file_location("think_filter", _tf_path)
            _tf_mod = _ilu.module_from_spec(_tf_spec)
            _tf_spec.loader.exec_module(_tf_mod)
            _think_filter_apply = _tf_mod.apply_to_record
        except Exception:
            _think_filter_apply = None  # disabled gracefully if module not found

    return _think_filter_apply


# ======================================================================
# RESPONSE PARSING
# ======================================================================


def parse_raw_response(text: str) -> Tuple[Dict, str]:
    """Surgical parser: extracts RAW content and packages it as valid JSON.

    Supports <write_action> and fallback to <tool_call>.

    Args:
        text: Raw model response text.

    Returns:
        Tuple of (tool_json, reasoning) where tool_json is the parsed tool call
        and reasoning is the extracted chain-of-thought.
    """
    reasoning = ""

    # 1. Extract Reasoning Block (if present)
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
    state: Optional[TaxonomyState] = None,
) -> Dict:
    """Generate a sample asynchronously, respecting the concurrency semaphore.

    If has_legacy=True, Gold Injection is SKIPPED — the model generates its own
    corrected 2026 code. This prevents injecting obsolete code as 'gold'.

    For Jinja/YAML fragments (subtype in ['jinja', 'yaml']), uses template-specific
    prompt builders with JINJA_YAML_GUIDE as truth anchor.

    Args:
        client: AsyncOpenAI client for API calls.
        model: Model identifier to use.
        frag: Fragment dictionary with code and metadata.
        example_type: Type of example (nominal, contrast, error_recovery).
        evol_difficulty: Difficulty level for evol-instruct (easy, medium, hard).
        master: Master guide content.
        changelog: Technical changelog content.
        semaphore: asyncio.Semaphore for concurrency control.
        has_legacy: Whether fragment contains legacy patterns.
        legacy_patterns: List of detected legacy patterns.
        jinja_guide: Jinja/YAML guide content.
        state: TaxonomyState for prompt building.

    Returns:
        Dictionary with status (accepted/rejected) and sample or reason.
    """
    from src.factory.config import MAX_RETRIES

    # Default to empty TaxonomyState if not provided
    if state is None:
        state = TaxonomyState(
            prompts={},
            ha_error_templates=[],
            jinja_variants=[],
            theory_taxonomy=[],
        )

    # === BIFURCATION: Functional Unit / Jinja·YAML / Python ===
    is_functional_unit = frag.get("subtype") == "functional_unit"
    is_template = frag.get("subtype") in ("jinja", "yaml")

    if is_functional_unit:
        # TIPO 1 (v11): Diversified prompts (nominal/contrast/error_recovery)
        # Model learns to evolution both logic and test, or modernize legacy tests.
        _governance = frag.get("governance", "")
        _blueprint = frag.get("blueprint", "")
        _local_imports = frag.get("local_imports", "[]")
        _has_context = bool(_governance or _blueprint)

        if example_type == "nominal":
            if _has_context:
                system_prompt = build_system_with_blueprint(
                    master,
                    changelog,
                    blueprint=_blueprint,
                    local_imports=_local_imports,
                    governance=_governance,
                )
            else:
                system_prompt = build_system_nominal(master, changelog)
            user_msg = build_user_functional_unit(frag, evol_difficulty)
        elif example_type == "contrast":
            # Senior modernizes legacy test/code pair to 2026 patterns
            # User sees: "tengo este código viejo [legacy], modernízalo"
            system_prompt = build_system_contrast(master, changelog)
            user_msg = build_user_contrast(frag)
        else:  # error_recovery
            # Senior diagnoses and fixes a runtime error in test/code pair
            # User sees: "tengo este error [HA error], corrígelo"
            system_prompt = build_system_error_recovery(master, changelog)
            user_msg = build_user_error_recovery(frag)
    elif is_template:
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
        # Python prompt builders — inject blueprint/governance context when available
        _governance = frag.get("governance", "")
        _blueprint = frag.get("blueprint", "")
        _local_imports = frag.get("local_imports", "[]")
        _has_context = bool(_governance or _blueprint)
        if example_type == "nominal":
            if _has_context:
                # Use blueprint+governance-aware system prompt for richer context
                system_prompt = build_system_with_blueprint(
                    master,
                    changelog,
                    blueprint=_blueprint,
                    local_imports=_local_imports,
                    governance=_governance,
                )
            else:
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
                ldi_result = validate_ldi(code_len, len(reasoning), frag["subtype"])

                if not ldi_result.is_valid:
                    raise ValueError(f"LDI Fail: {ldi_result.reason}")

                # === POST-VALIDATION OF MODEL OUTPUT ===
                generated_code = tool_json["arguments"]["content"]
                poison_patterns = post_validate_output(
                    generated_code, example_type, frag.get("subtype", "code")
                )

                # === PHP VALIDATION JUDGE — Level 1 (T063) ===
                if frag.get("type") == "php":
                    _failures_log = OUTPUT_DIR / "validation_failures.jsonl"
                    php_failures = validate_php_output(
                        generated_code, frag, _failures_log
                    )
                    if php_failures:
                        poison_patterns = list(poison_patterns) + [
                            f"php_validation:{r}" for r in php_failures
                        ]

                # === CONDITIONAL GOLD INJECTION ===
                # If fragment has legacy patterns, do NOT inject gold
                # (avoids schizophrenia: think=2026, code=legacy)
                gold_injected = False
                cot_schizophrenia = False
                if not has_legacy:
                    # -- Detect CoT schizophrenia --
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
                    else:
                        # Clean output -> safe gold injection
                        poison_patterns = []
                        # If this is an error_recovery example, DO NOT perform gold injection.
                        # We must always preserve the Teacher's generated code for error_recovery
                        # because it contains the fix/solution to the runtime error presented.
                        if example_type == "error_recovery":
                            final_assistant_msg = (
                                f"{reasoning}\n</minimax:tool_call>"
                                f"<tool_call>\n{json.dumps(tool_json)}\n</tool_call>"
                            )
                            gold_injected = False
                        else:
                            # Gold injection — adapter per type
                            if is_functional_unit:
                                # TIPO 1 (both contrast & nominal): two write_to_file calls (logic + test)
                                # v11: Contrast/error_recovery tests must stay intact for model to learn
                                # It keeps the test, modernizes/fixes the logic, or both.
                                tool_calls = [
                                    {
                                        "name": "write_to_file",
                                        "arguments": {
                                            "path": frag["virtual_filename"],
                                            "content": frag["original"],
                                        },
                                    },
                                    {
                                        "name": "write_to_file",
                                        "arguments": {
                                            "path": frag.get(
                                                "test_filename",
                                                f"tests/{frag['virtual_filename']}",
                                            ),
                                            "content": frag.get("test_original", ""),
                                        },
                                    },
                                ]
                                final_assistant_msg = (
                                    f"{reasoning}\n</minimax:tool_call>"
                                    f"<tool_call>\n{json.dumps(tool_calls)}\n</tool_call>"
                                )
                            else:
                                # TIPO 3 / jinja / yaml — single write_to_file
                                tool_json["arguments"]["content"] = frag["original"]
                                final_assistant_msg = (
                                    f"{reasoning}\n</minimax:tool_call>"
                                    f"<tool_call>\n{json.dumps(tool_json)}\n</tool_call>"
                                )
                            gold_injected = True
                else:
                    # Legacy detected -> keep model code (2026)
                    logger.debug(
                        "GOLD SKIP [%s] legacy detected: %s",
                        frag["name"],
                        "; ".join(legacy_patterns or [])[:200],
                    )
                    final_assistant_msg = (
                        f"{reasoning}\n</minimax:tool_call>"
                        f"<tool_call>\n{json.dumps(tool_json)}\n</tool_call>"
                    )

                # filter_text = full reasoning (for posterior dedup)
                filter_text = (
                    f"{reasoning}\n\n{final_assistant_msg.split('</think>')[-1]}"
                )

                # === AUTO CURATION: flag toxic samples ===
                is_kept = True
                poison_reasons: List[str] = []
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

                # Build metadata first so we can compute canonical sample_id
                ck_key = make_checkpoint_key(frag, None)
                metadata: Dict[str, Any] = {
                    "curation": {
                        "kept": is_kept,
                        "quality_score": 0.0,
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
                    "factory_version": "v11.0",
                    "example_type": example_type,
                    "evol_difficulty": evol_difficulty,
                    "ldi": ldi_result.score,
                    "fragment_name": frag["name"],
                    "source_file": frag["virtual_filename"],
                    "gold_injected": gold_injected,
                    "legacy_detected": has_legacy,
                    "legacy_patterns": legacy_patterns or [],
                    "checkpoint_key": ck_key,
                    # theory-type defaults (schema uniforme)
                    "theory_subtype": "none",
                    "section_name": "none",
                    "source_doc": "none",
                }

                # Canonical sample id must reflect the final example_type/evol_difficulty
                # Use the checkpoint key (already present in metadata) to ensure
                # uniqueness across files/fragments with the same `name`.
                actual_type = metadata.get("example_type", example_type)
                # actual_difficulty intentionally not included here because the
                # checkpoint_key encodes fragment+file identity deterministically.
                sample_id = f"v11_{actual_type}_{ck_key}"

                return {
                    "status": "accepted",
                    "sample": {
                        "id": sample_id,
                        "conversation": [
                            {"role": "user", "content": user_msg},
                            {"role": "assistant", "content": final_assistant_msg},
                        ],
                        "metadata": metadata,
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
        "checkpoint_key": make_checkpoint_key(frag, None),
    }


async def generate_theory_sample_async(
    client: AsyncOpenAI,
    model: str,
    theory_frag: Dict,
    master: str,
    changelog: str,
    semaphore: asyncio.Semaphore,
    state: Optional[TaxonomyState] = None,
) -> Dict:
    """Generate a theory sample (no Gold Injection — pure doctrinal knowledge).

    Args:
        client: AsyncOpenAI client for API calls.
        model: Model identifier to use.
        theory_frag: Theory fragment dictionary with section content.
        master: Master guide content.
        changelog: Technical changelog content.
        semaphore: asyncio.Semaphore for concurrency control.
        state: TaxonomyState for prompt building.

    Returns:
        Dictionary with status (accepted/rejected) and sample or reason.
    """
    from src.factory.config import MAX_RETRIES

    # Default to empty TaxonomyState if not provided
    if state is None:
        state = TaxonomyState(
            prompts={},
            ha_error_templates=[],
            jinja_variants=[],
            theory_taxonomy=[],
        )

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
                    temperature=0.3,
                    max_tokens=8192,
                    stop=["<|im_end|>"],
                )
                raw = response.choices[0].message.content
                last_response = raw

                # Extract reasoning and answer
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
                final_assistant = f"{reasoning}\n</minimax:tool_call>\n\n{answer}"

                rep = theory_frag.get("_rep")
                ck_key = make_checkpoint_key(
                    theory_frag,
                    rep,
                )

                # Use checkpoint_key as canonical id base for theory samples
                # (avoids collisions when different documents share the same section title)
                return {
                    "status": "accepted",
                    "sample": {
                        "id": f"v11_theory_{ck_key}",
                        "conversation": [
                            {"role": "user", "content": user_msg},
                            {"role": "assistant", "content": final_assistant},
                        ],
                        "metadata": {
                            "curation": {"kept": True, "quality_score": 0.0},
                            "factory_version": "v11.0",
                            "example_type": "theory",
                            # theory-specific
                            "theory_subtype": theory_subtype,
                            "section_name": theory_frag["name"],
                            "source_doc": theory_frag["source_doc"],
                            # normal-type defaults (mantiene schema uniforme)
                            "evol_difficulty": "none",
                            "ldi": 0.0,
                            "fragment_name": theory_frag["name"],
                            "source_file": theory_frag.get("virtual_filename", "none"),
                            "gold_injected": False,
                            "legacy_detected": False,
                            "legacy_patterns": [],
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
            theory_frag,
            theory_frag.get("_rep"),
        ),
    }


# ======================================================================
# FRAGMENT PROCESSING
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
    args: Any,
    jinja_guide: str = "",
    state: Optional[TaxonomyState] = None,
):
    """Process a fragment: assign type, generate, write result.

    Runs detect_legacy_patterns() to determine if the gold code contains
    2023/2024 patterns, then passes that info to assign_example_type()
    and generate_sample_async() for the anti-schizophrenia filter.

    For Jinja/YAML fragments, uses template-specific detectors and prompts.

    Args:
        client: AsyncOpenAI client for API calls.
        model: Model identifier to use.
        frag: Fragment dictionary with code and metadata.
        master: Master guide content.
        changelog: Technical changelog content.
        semaphore: asyncio.Semaphore for concurrency control.
        writer_ok: AsyncFileWriter for accepted samples.
        writer_bad: AsyncFileWriter for rejected samples.
        tracker: ProgressTracker for tracking progress.
        args: Command-line arguments object.
        jinja_guide: Jinja/YAML guide content.
        state: TaxonomyState for prompt building.
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
    type_assignment = assign_example_type(frag, has_legacy=has_legacy)
    example_type = type_assignment.example_type
    evol_difficulty = type_assignment.difficulty
    if not evol_difficulty and example_type == "nominal":
        evol_difficulty = "hard"

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
        state=state,
    )

    if result["status"] == "accepted":
        sample = result["sample"]
        # ── REALITY SYNC: use the type/difficulty that was ACTUALLY generated ──
        # generate_sample_async builds sample_id from its own example_type,
        # so reading back from metadata guarantees ID and counter are in sync.
        actual_type = sample["metadata"].get("example_type", example_type)
        actual_difficulty = sample["metadata"].get("evol_difficulty", evol_difficulty)
        if actual_type != example_type:
            logger.info(
                "TYPE SYNC [%s]: assigned=%s → actual=%s (fallback)",
                frag["name"],
                example_type,
                actual_type,
            )
        # Ensure sample ID matches the actual example type (recompute if needed)
        try:
            # Ensure canonical id uses checkpoint_key (unique per fragment+file)
            ck = sample.get("metadata", {}).get("checkpoint_key")
            if not ck:
                # Fallback to deterministic checkpoint generation
                ck = make_checkpoint_key(frag, None)
            new_sample_id = f"v11_{actual_type}_{ck}"
            if sample.get("id") != new_sample_id:
                sample["id"] = new_sample_id
        except Exception as _e:
            logger.debug("Could not ensure sample id for %s: %s", frag["name"], _e)

        is_kept = sample["metadata"].get("curation", {}).get("kept", True)
        if is_kept:
            # ── THINK FILTER: strip redundant reasoning before writing ──
            think_filter_apply = _get_think_filter()
            if think_filter_apply is not None and getattr(args, "think_filter", True):
                sample, _tf_stats = think_filter_apply(
                    sample, min_chars=getattr(args, "think_filter_min_chars", 5000)
                )
                if _tf_stats:
                    logger.debug(
                        "think_filter [%s]: %.1f%% reduction (%d→%d chars)",
                        sample.get("id", "?"),
                        _tf_stats["reduction_pct"],
                        _tf_stats["original_chars"],
                        _tf_stats["distilled_chars"],
                    )
            await writer_ok.write(sample)
        else:
            # Auto-rejected by post-validation (poison patterns)
            await writer_bad.write(
                {
                    "frag": sample["metadata"].get("fragment_name", "unknown"),
                    "type": actual_type,
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
                actual_type,
                "; ".join(sample["metadata"]["curation"].get("poison_patterns", []))[
                    :150
                ],
            )
        gold_injected = sample["metadata"].get("gold_injected", True)
    else:
        # Rejected (all retries failed): use type from result if present
        actual_type = result.get("example_type", example_type)
        actual_difficulty = evol_difficulty
        await writer_bad.write(
            {
                "frag": result.get("fragment_name", "unknown"),
                "type": actual_type,
                "reason": result["reason"],
                "legacy_detected": has_legacy,
                "legacy_patterns": legacy_patterns,
                "checkpoint_key": result.get("checkpoint_key", ""),
                "full_response": result.get("raw_full_response", "")[:5000],
            }
        )
        gold_injected = False

    # ── COUNTERS OF REALITY: tracker sees the actual type, not the planned type ──
    await tracker.record(
        result["status"],
        actual_type,
        actual_difficulty,
        gold_injected=gold_injected,
        has_legacy=has_legacy,
    )


# ======================================================================
# MAIN ASYNC PIPELINE
# ======================================================================


async def main_async(args):
    """Main async pipeline entry point.

    Args:
        args: Command-line arguments object with the following attributes:
            - _gap_dir: Path to gap directory for master documents
            - base_url: API base URL
            - api_key: API key
            - model: Model identifier
            - theory: Whether to run in theory mode
            - theory_reps: Number of theory repetitions
            - test: Test mode limit
            - output: Output file path
            - resume: Resume from checkpoint file
            - workers: Number of concurrent workers
            - raw_dir: Raw directory path
            - limit: Limit number of files
            - extensions: List of allowed extensions
            - think_filter: Whether to apply think filter
            - think_filter_min_chars: Minimum chars for think filter
    """
    # Load taxonomy for prompt building
    # Check if taxonomy is already loaded (e.g., by conftest)
    from src.factory import prompt_builder as _pb

    if _pb._TAX:
        # Taxonomy already loaded, skip loading
        taxonomy_loaded = True
    else:
        # Try to load from configs directory
        taxonomy_loaded = False
        taxonomy_path = Path("configs/stage_2_factory/taxonomy")
        if taxonomy_path.is_file():
            # It's a file - use it directly
            try:
                load_taxonomy(taxonomy_path)
                taxonomy_loaded = True
            except Exception:
                pass  # Use fallback if loading fails
        elif taxonomy_path.is_dir():
            # It's a directory - look for .yaml or .example files
            yaml_files = list(taxonomy_path.glob("**/*.yaml")) + list(
                taxonomy_path.glob("**/*.example")
            )
            if yaml_files:
                # Use the first taxonomy file found
                try:
                    load_taxonomy(yaml_files[0])
                    taxonomy_loaded = True
                except Exception:
                    pass  # Use fallback if loading fails

    if not taxonomy_loaded:
        # Fallback to empty state if taxonomy not found
        state = TaxonomyState(
            prompts={},
            ha_error_templates=[],
            jinja_variants=[],
            theory_taxonomy=[],
        )
    else:
        # load_taxonomy sets global state, but we also create a state object for functions that need it
        state = TaxonomyState(
            prompts={},
            ha_error_templates=[],
            jinja_variants=[],
            theory_taxonomy=[],
        )

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
        output_path = OUTPUT_DIR / f"v11_theory_{timestamp}.jsonl"
        rejected_path = OUTPUT_DIR / f"v11_theory_rejected_{timestamp}.jsonl"

        # --output always controls WHERE to write (highest priority)
        if args.output:
            output_path = Path(args.output)

        # RESUME: only controls WHERE to read checkpoint from.
        # If --output was not specified, also append to the resume file.
        done_keys: CheckpointSet = frozenset()
        if args.resume:
            resume_path = Path(args.resume)
            if not args.output:
                # No explicit output → append new samples to the resume file
                output_path = resume_path
            # Derive rejected path from output_path (never the same as output)
            out_stem = output_path.stem
            rejected_path = output_path.parent / f"{out_stem}_rejected.jsonl"
            # Read checkpoint from the resume file (and its sidecar rejected file)
            resume_rejected = resume_path.parent / f"{resume_path.stem}_rejected.jsonl"
            done_keys = load_checkpoint(resume_path, resume_rejected)
            before = len(expanded_frags)
            expanded_frags = [
                tf
                for tf in expanded_frags
                if make_checkpoint_key(tf, tf.get("_rep")) not in done_keys
            ]
            logger.info(
                "RESUME: %d already processed, %d pending (of %d total) [%d checkpoint keys loaded]",
                before - len(expanded_frags),
                len(expanded_frags),
                before,
                len(done_keys),
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
                client, args.model, tfrag, master, changelog, semaphore, state
            )
            if result["status"] == "accepted":
                # ── THINK FILTER (theory mode) ──
                _tsample = result["sample"]
                think_filter_apply = _get_think_filter()
                if think_filter_apply is not None and getattr(
                    args, "think_filter", True
                ):
                    _tsample, _tf_stats = think_filter_apply(
                        _tsample,
                        min_chars=getattr(args, "think_filter_min_chars", 5000),
                    )
                await writer_ok.write(_tsample)
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

    # V11 TWO-PASS MODULE-AWARE FRAGMENT COLLECTION
    # Pass 1: scan all .txt (recursively), cache blueprints in RAM
    # Pass 2: generate fragments only from FUNCTIONAL_UNIT / LOGIC_ONLY bundles
    raw_dir = Path(args.raw_dir)
    all_txt_files = sorted(raw_dir.rglob("*.txt"))
    if args.limit:
        all_txt_files = all_txt_files[: args.limit]

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

    logger.info(
        "V11 two-pass scan: %d .txt files found in %s", len(all_txt_files), raw_dir
    )

    # ── PASS 1: build blueprint cache and governance cache ──────────
    blueprint_cache: Dict[str, str] = {}
    governance_cache: Dict[str, str] = {}
    functional_bundles: List[Dict] = []
    logic_only_bundles: List[Dict] = []

    for fpath in all_txt_files:
        try:
            txt = fpath.read_text(errors="ignore")
            bundle = parse_bundle(txt)
            btype = bundle["type"]
            if btype == "MODULE_BLUEPRINT":
                # Key by MODULE field (arch from [MODULE_MAP])
                module_name = bundle["arch"].get("MODULE", "")
                if not module_name:
                    # Fallback: remove _blueprint suffix from entity_id
                    module_name = bundle["entity_id"].rsplit("_blueprint", 1)[0]
                if module_name:
                    blueprint_cache[module_name] = txt
                    logger.debug("Blueprint cached: %s", module_name)
            elif btype == "GOVERNANCE_RULES":
                # Key by REPO_PREFIX — applies to all modules from this repo
                repo_prefix = bundle["arch"].get("REPO_PREFIX", "")
                if not repo_prefix:
                    # Fallback: strip _governance suffix from entity_id
                    repo_prefix = bundle["entity_id"].rsplit("_governance", 1)[0]
                if repo_prefix:
                    # Concatenate all governance file contents
                    gov_content = "\n\n".join(
                        f"# {fname}\n{content.strip()}"
                        for fname, content in bundle["files"].items()
                    )
                    governance_cache[repo_prefix] = gov_content
                    logger.info(
                        "Governance cached: %s (%d chars)",
                        repo_prefix,
                        len(gov_content),
                    )
            elif btype == "FUNCTIONAL_UNIT":
                functional_bundles.append(bundle)
            elif btype == "LOGIC_ONLY":
                logic_only_bundles.append(bundle)
            # Unknown type: silently skip
        except Exception as e:
            logger.warning("Parse error %s: %s", fpath, e)

    logger.info(
        "Pass 1 complete: %d blueprints | %d governance | %d FUNCTIONAL_UNIT | %d LOGIC_ONLY",
        len(blueprint_cache),
        len(governance_cache),
        len(functional_bundles),
        len(logic_only_bundles),
    )

    # ── PASS 2: generate fragment dicts ─────────────────────────────
    all_fragments: List[Dict] = []
    for bundle in functional_bundles + logic_only_bundles:
        try:
            all_fragments.extend(
                get_v2_fragments(
                    bundle,
                    blueprint_cache,
                    allowed_extensions=allowed_ext,
                    governance_cache=governance_cache,
                )
            )
        except Exception as e:
            logger.warning(
                "Fragment extraction error [%s]: %s", bundle.get("entity_id", "?"), e
            )

    logger.info("Total fragments discovered: %d", len(all_fragments))

    # Test mode: limit fragments
    if args.test:
        all_fragments = all_fragments[: args.test]
        logger.info("TEST MODE: Limited to %d fragments", args.test)

    if not all_fragments:
        logger.error(
            "No fragments found. Check %s sub-directories for TIPO 1/3 bundles.",
            raw_dir,
        )
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
    output_path = OUTPUT_DIR / f"v11_diversified_{timestamp}.jsonl"
    rejected_path = OUTPUT_DIR / f"v11_rejected_{timestamp}.jsonl"

    # --output always controls WHERE to write (highest priority)
    if args.output:
        output_path = Path(args.output)

    # RESUME: only controls WHERE to read checkpoint from.
    # If --output was not specified, also append to the resume file.
    done_keys: CheckpointSet = frozenset()
    if args.resume:
        resume_path = Path(args.resume)
        if not args.output:
            # No explicit output → append new samples to the resume file
            output_path = resume_path
        # Derive rejected path from output_path (never the same as output)
        out_stem = output_path.stem
        rejected_path = output_path.parent / f"{out_stem}_rejected.jsonl"
        # Read checkpoint from the resume file (and its sidecar rejected file)
        resume_rejected = resume_path.parent / f"{resume_path.stem}_rejected.jsonl"
        done_keys = load_checkpoint(resume_path, resume_rejected)
        before = len(all_fragments)
        all_fragments = [
            f for f in all_fragments if make_checkpoint_key(f, None) not in done_keys
        ]
        logger.info(
            "RESUME: %d already processed, %d pending (of %d total) [%d checkpoint keys loaded]",
            before - len(all_fragments),
            len(all_fragments),
            before,
            len(done_keys),
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
            args,
            jinja_guide=jinja_guide,
            state=state,
        )
        for frag in all_fragments
    ]

    # Execute with gather (semaphore controls actual concurrency)
    await asyncio.gather(*tasks)

    tracker.close()
    print(tracker.summary())
