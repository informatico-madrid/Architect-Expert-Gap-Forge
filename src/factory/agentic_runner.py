#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
AEGF V10-MT Runner — Multi-Turn Diversified Architect Edition
=============================================================
[STATUS: EXPERIMENTAL]
Provides async generation loop and file writers for multi-turn agentic training data.
"""

import asyncio
import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI
from tqdm import tqdm

from src.factory.agentic_prompt_builder import (
    assign_example_type,
    build_system_error_recovery,
    build_system_nominal,
    build_system_contrast,
    build_user_error_recovery,
    build_user_nominal,
    build_user_contrast,
    detect_legacy_patterns,
    extract_and_validate,
    load_checkpoint,
    load_master_docs,
    make_checkpoint_key,
    validate_ldi,
)

# ══════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════
DEFAULT_BASE_URL = "http://localhost:8000/v1"
import os
DEFAULT_API_KEY = os.environ.get("DEFAULT_API_KEY", "")
DEFAULT_MODEL = "qwen3-5-35b-a3b-nvfp4"
DEFAULT_WORKERS = 8
MAX_RETRIES = 3

OUTPUT_DIR = Path("data/synthetic")

# Type distribution
DIST_NOMINAL = 0.50
DIST_CONTRAST = 0.30
DIST_ERROR_RECOVERY = 0.20

# ══════════════════════════════════════════════════════════════════════
# LOGGER
# ══════════════════════════════════════════════════════════════════════
logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# ASYNC-SAFE FILE WRITERS
# ══════════════════════════════════════════════════════════════════════


class AsyncFileWriter:
    """Async-safe JSONL writer with asyncio lock."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = asyncio.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    async def write(self, record: Dict[str, Any]) -> None:
        async with self._lock:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ══════════════════════════════════════════════════════════════════════
# PROGRESS TRACKER
# ══════════════════════════════════════════════════════════════════════


class ProgressTracker:
    """Async-safe progress tracker with tqdm."""

    def __init__(self, total: int) -> None:
        self.total = total
        self.accepted = 0
        self.rejected = 0
        self.by_type: Dict[str, int] = {
            "nominal": 0,
            "contrast": 0,
            "error_recovery": 0,
        }
        self.by_difficulty: Dict[str, int] = {"easy": 0, "medium": 0, "hard": 0}
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
    ) -> None:
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

    def close(self) -> None:
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
# ASYNC MULTI-TURN GENERATION (core engine)
# ══════════════════════════════════════════════════════════════════════


async def generate_multiturn_sample_async(
    client: AsyncOpenAI,
    model: str,
    frag: Dict[str, Any],
    example_type: str,
    evol_difficulty: Optional[str],
    master: str,
    changelog: str,
    semaphore: asyncio.Semaphore,
    has_legacy: bool = False,
    legacy_patterns: Optional[List[str]] = None,
) -> Dict[str, Any]:
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
                    f"{reasoning1}\n<think>"
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
                    f"{reasoning2}\n<think>"
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
    frag: Dict[str, Any],
    master: str,
    changelog: str,
    semaphore: asyncio.Semaphore,
    writer_ok: AsyncFileWriter,
    writer_bad: AsyncFileWriter,
    tracker: ProgressTracker,
) -> None:
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


async def main_async(args: Any) -> None:
    """Async entry point: load docs, collect fragments, run pipeline."""
    # Import here to avoid circular imports
    from src.factory.agentic_prompt_builder import (
        get_file_chunks,
        get_fragments,
    )

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
    done_keys: set = set()
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
