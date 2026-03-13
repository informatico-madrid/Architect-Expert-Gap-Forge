#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
AEGF Gap Generator Module
=========================
Generates gap analysis for evaluation samples.
"""

from __future__ import annotations

import logging

from src.audit.config import (
    DEFAULT_API_URL,
    DEFAULT_GEMINI_MODEL,
    DEFAULT_JUDGE_MODEL,
    DEFAULT_PROFESSOR_BACKEND,
    DEFAULT_PROFESSOR_MAX_TOKENS,
    DEFAULT_RETRIES,
    DEFAULT_RETRY_DELAY,
    _get_inference_router,
    _get_prompt_manager,
)
from src.audit.schema import PromptGenerationError, SampleRecord

# ======================================================================
# LOGGING
# ======================================================================

logger = logging.getLogger(__name__)


# ======================================================================
# GAP ANALYSIS
# ======================================================================


def generate_gap_analysis(
    sample: SampleRecord,
    master: str,
    changelog: str,
    jinja_guide: str,
    professor_backend: str = DEFAULT_PROFESSOR_BACKEND,
    gemini_model: str = DEFAULT_GEMINI_MODEL,
    judge_model: str = DEFAULT_JUDGE_MODEL,
    api_url: str = DEFAULT_API_URL,
    retries: int = DEFAULT_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY,
    validate: bool = False,
) -> str:
    """Genera un análisis de gaps en texto plano para un SampleRecord.

    Llama al Professor (Gemini o vLLM) y devuelve directamente el texto
    de la respuesta sin ningún parseo JSON.

    Args:
        sample: The sample record to generate gap analysis for.
        master: Master documentation content.
        changelog: Changelog content.
        jinja_guide: Jinja guide content.
        professor_backend: Backend to use for professor inference.
        gemini_model: Gemini model name.
        judge_model: Judge/vLLM model name.
        api_url: API URL for inference.
        retries: Number of retries for inference.
        retry_delay: Delay between retries in seconds.
        validate: If True, skip the actual inference call.

    Returns:
        The gap analysis text.
    """
    ref_code = sample.reference_response or sample.user_prompt or ""
    if len(ref_code) > 4000:
        ref_code = ref_code[:4000] + "\n... [truncated] ..."

    pm = _get_prompt_manager()
    user_msg = pm.format(
        "gap_analysis",
        fragment_name=sample.fragment_name,
        source_file=sample.source_file,
        reference_code=ref_code,
        master=master[:8000],
        changelog=changelog[:8000],
        jinja=jinja_guide[:3000],
    )

    if validate:
        logger.info(
            "Validate mode: skipping professor call for gap_analysis %s", sample.id
        )
        return f"[validate] gap_analysis placeholder for {sample.fragment_name} ({sample.source_file})"

    client = _get_inference_router().professor(
        backend=professor_backend,
        gemini_model=gemini_model,
        vllm_model=judge_model,
        api_url=api_url,
    )
    raw = client.generate_with_retry(
        prompt=user_msg,
        system_prompt=pm.system("gap_analysis"),
        max_tokens=DEFAULT_PROFESSOR_MAX_TOKENS,
        temperature=0.2,
        retries=retries,
        retry_delay=retry_delay,
    )
    gap_text = raw.strip()
    if not gap_text:
        raise PromptGenerationError(
            f"Professor produced empty gap_analysis for {sample.id}"
        )
    return gap_text
