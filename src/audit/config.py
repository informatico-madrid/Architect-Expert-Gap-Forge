#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
AEGF Audit Configuration Module
================================
Centralizes configuration constants and lazy singletons for the audit pipeline.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml

from src.audit.inference import InferenceRouter
from src.audit.prompt_manager import PromptManager

# ======================================================================
# LOGGING
# ======================================================================

logger = logging.getLogger(__name__)

# ======================================================================
# CONFIGURATION PATHS
# ======================================================================

_CONFIG_PATH = Path("configs/stage_5_evaluation/eval_config.yaml")
_PATTERNS_CONFIG_PATH = Path("configs/stage_5_evaluation/ha_patterns.yaml")

# ======================================================================
# LAZY SINGLETON STORAGE
# ======================================================================

_config_cache: dict[str, Any] | None = None
_prompt_mgr: PromptManager | None = None
_router: InferenceRouter | None = None


# ======================================================================
# CONFIGURATION — YAML + env overrides
# ======================================================================


def _load_config() -> dict[str, Any]:
    """Load evaluation config from YAML, with environment variable overrides."""
    if _CONFIG_PATH.exists():
        with open(_CONFIG_PATH, "r", encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh) or {}
    else:
        logger.warning("Config not found at %s — using defaults", _CONFIG_PATH)
        cfg = {}

    # Env overrides (AEGF_ prefix)
    _env = {
        "api_url": os.getenv("AEGF_VLLM_API_URL"),
        "audit_dir": os.getenv("AEGF_AUDIT_DIR"),
        "sample_size": os.getenv("AEGF_SAMPLE_SIZE"),
        "base_model": os.getenv("AEGF_BASE_MODEL"),
        "adapter_model": os.getenv("AEGF_ADAPTER_MODEL"),
        "judge_model": os.getenv("AEGF_JUDGE_MODEL"),
        "max_tokens": os.getenv("AEGF_MAX_TOKENS"),
        "temperature": os.getenv("AEGF_TEMPERATURE"),
        "retries": os.getenv("AEGF_RETRIES"),
        "retry_delay": os.getenv("AEGF_RETRY_DELAY"),
        "professor_backend": os.getenv("AEGF_PROFESSOR_BACKEND"),
        "inference_backend": os.getenv("AEGF_INFERENCE_BACKEND"),
        "gemini_model": os.getenv("AEGF_GEMINI_MODEL"),
        "professor_max_tokens": os.getenv("AEGF_PROFESSOR_MAX_TOKENS"),
        "inference_max_tokens": os.getenv("AEGF_INFERENCE_MAX_TOKENS"),
    }
    for k, v in _env.items():
        if v is not None:
            # Coerce numeric types
            if k in (
                "sample_size",
                "max_tokens",
                "retries",
                "professor_max_tokens",
                "inference_max_tokens",
            ):
                cfg[k] = int(v)
            elif k in ("temperature", "retry_delay"):
                cfg[k] = float(v)
            else:
                cfg[k] = v

    return cfg


def _get_config() -> dict[str, Any]:
    """Lazy singleton for configuration dict."""
    global _config_cache
    if _config_cache is None:
        _config_cache = _load_config()
    return _config_cache


def _get_prompt_manager() -> PromptManager:
    """Lazy singleton for PromptManager."""
    global _prompt_mgr
    if _prompt_mgr is None:
        _prompt_mgr = PromptManager()
    return _prompt_mgr


def _get_inference_router() -> InferenceRouter:
    """Lazy singleton for InferenceRouter."""
    global _router
    if _router is None:
        _router = InferenceRouter()
    return _router


# ======================================================================
# CONFIGURATION CONSTANTS
# ======================================================================
# AEGF §5.3: No import-time side effects. Constants are defined as plain
# literals here and must NOT call _get_config() at module level. Code that
# needs runtime-overridable values must call _get_config() inside a function.
DEFAULT_API_URL: str = "http://localhost:8000/v1"
DEFAULT_AUDIT_DIR: str = "data/audit"
DEFAULT_SAMPLE_SIZE: int = 5
DEFAULT_BASE_MODEL: str = "qwen3-30b-a3b-thinking-fp8"
DEFAULT_ADAPTER_MODEL: str = "platinum_adapter"
DEFAULT_JUDGE_MODEL: str = "qwen3-30b-a3b-thinking-fp8"
DEFAULT_MAX_TOKENS: int = 65536
DEFAULT_TEMPERATURE: float = 0.6
DEFAULT_RETRIES: int = 3
DEFAULT_RETRY_DELAY: float = 5.0
DEFAULT_PROFESSOR_BACKEND: str = "auto"
DEFAULT_INFERENCE_BACKEND: str = "vllm"
DEFAULT_GEMINI_MODEL: str = "gemini-2.5-flash"
DEFAULT_PROFESSOR_MAX_TOKENS: int = 65536
DEFAULT_INFERENCE_MAX_TOKENS: int = 65536
# Maximum characters sent to the judge per response. Responses beyond this limit
# are truncated before submission. Must be large enough to cover any legitimate
# model output (empirical max ~22 K); 32 K gives ample headroom while capping
# clearly degenerate runaway generations (>100 K).
JUDGE_RESPONSE_TRUNCATION_LIMIT: int = 65536
