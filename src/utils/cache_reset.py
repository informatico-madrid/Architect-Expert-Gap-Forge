#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0
"""
Memory cache reset utilities for pytest.

This module provides a centralized function to reset all caches that may
accumulate memory between pytest executions in the Ralph loop.
"""

from __future__ import annotations

import sys
from typing import Dict


def reset_all_caches() -> Dict[str, bool]:
    """
    Reset all known caches that may accumulate memory between pytest runs.

    This function should be called before each pytest execution in the
    Ralph loop to prevent memory growth.

    Returns:
        A dictionary with cache names as keys and True/False indicating
        if each cache was successfully reset.
    """
    results: Dict[str, bool] = {}

    # 1. Reset _adapter_cache in src/utils/extractors/factory.py
    try:
        from src.utils.extractors import factory

        if hasattr(factory, "_adapter_cache"):
            factory._adapter_cache.clear()
            results["adapter_cache"] = True
        else:
            results["adapter_cache"] = False
    except Exception as e:
        results["adapter_cache"] = False
        print(f"Warning: Failed to reset adapter_cache: {e}", file=sys.stderr)

    # 2. Reset _domain_patterns_cache in src/audit/scorecard.py
    try:
        from src.audit import scorecard

        if hasattr(scorecard, "_domain_patterns_cache"):
            scorecard._domain_patterns_cache = None
            results["scorecard_domain_patterns_cache"] = True
        else:
            results["scorecard_domain_patterns_cache"] = False
    except Exception as e:
        results["scorecard_domain_patterns_cache"] = False
        print(
            f"Warning: Failed to reset scorecard_domain_patterns_cache: {e}",
            file=sys.stderr,
        )

    # 3. Reset _domain_patterns_cache in src/audit/model_evaluator.py
    try:
        from src.audit import model_evaluator

        if hasattr(model_evaluator, "_domain_patterns_cache"):
            model_evaluator._domain_patterns_cache = None
            results["model_evaluator_domain_patterns_cache"] = True
        else:
            results["model_evaluator_domain_patterns_cache"] = False
    except Exception as e:
        results["model_evaluator_domain_patterns_cache"] = False
        print(
            f"Warning: Failed to reset model_evaluator_domain_patterns_cache: {e}",
            file=sys.stderr,
        )

    # 4. Reset _router in src/audit/model_evaluator.py
    try:
        from src.audit import model_evaluator

        if hasattr(model_evaluator, "_router"):
            model_evaluator._router = None
            results["model_evaluator_router"] = True
        else:
            results["model_evaluator_router"] = False
    except Exception as e:
        results["model_evaluator_router"] = False
        print(f"Warning: Failed to reset model_evaluator_router: {e}", file=sys.stderr)

    # 5. Reset _prompt_mgr in src/audit/model_evaluator.py
    try:
        from src.audit import model_evaluator

        if hasattr(model_evaluator, "_prompt_mgr"):
            model_evaluator._prompt_mgr = None
            results["model_evaluator_prompt_mgr"] = True
        else:
            results["model_evaluator_prompt_mgr"] = False
    except Exception as e:
        results["model_evaluator_prompt_mgr"] = False
        print(
            f"Warning: Failed to reset model_evaluator_prompt_mgr: {e}", file=sys.stderr
        )

    # 6. Reset _default_metrics in src/utils/metrics.py
    try:
        from src.utils import metrics

        if hasattr(metrics, "_default_metrics"):
            metrics._default_metrics = None
            results["default_metrics"] = True
        else:
            results["default_metrics"] = False
    except Exception as e:
        results["default_metrics"] = False
        print(f"Warning: Failed to reset default_metrics: {e}", file=sys.stderr)

    # 7. Reset taxonomy globals in src/factory/production_v11.py
    try:
        from src.factory import production_v11

        if hasattr(production_v11, "_TAX"):
            production_v11._TAX = {}
        if hasattr(production_v11, "HA_ERROR_TEMPLATES"):
            production_v11.HA_ERROR_TEMPLATES = []
        if hasattr(production_v11, "LEGACY_2023_PATTERNS"):
            production_v11.LEGACY_2023_PATTERNS = []
        if hasattr(production_v11, "JINJA_HA_ERROR_TEMPLATES"):
            production_v11.JINJA_HA_ERROR_TEMPLATES = []
        if hasattr(production_v11, "JINJA_LEGACY_2023_PATTERNS"):
            production_v11.JINJA_LEGACY_2023_PATTERNS = []
        if hasattr(production_v11, "THEORY_QUESTION_TEMPLATES"):
            production_v11.THEORY_QUESTION_TEMPLATES = []
        results["production_v11_taxonomy"] = True
    except Exception as e:
        results["production_v11_taxonomy"] = False
        print(f"Warning: Failed to reset production_v11_taxonomy: {e}", file=sys.stderr)

    # 8. Reset taxonomy globals in src/factory/agentic_gen.py
    try:
        from src.factory import agentic_gen

        if hasattr(agentic_gen, "_TAX"):
            agentic_gen._TAX = {}
        if hasattr(agentic_gen, "HA_ERROR_TEMPLATES"):
            agentic_gen.HA_ERROR_TEMPLATES = []
        if hasattr(agentic_gen, "LEGACY_2023_PATTERNS"):
            agentic_gen.LEGACY_2023_PATTERNS = []
        if hasattr(agentic_gen, "TOOLS_DEFINITION"):
            agentic_gen.TOOLS_DEFINITION = []
        if hasattr(agentic_gen, "_TOOLS_JSON"):
            agentic_gen._TOOLS_JSON = None
        results["agentic_gen_taxonomy"] = True
    except Exception as e:
        results["agentic_gen_taxonomy"] = False
        print(f"Warning: Failed to reset agentic_gen_taxonomy: {e}", file=sys.stderr)

    # 9. Reset InferenceRouter internal cache in src/audit/inference.py
    try:
        # The InferenceRouter class has internal _cache, but we can't easily
        # reset instance caches without recreating the router. This is handled
        # by resetting _router above.
        results["inference_router"] = True
    except Exception as e:
        results["inference_router"] = False
        print(f"Warning: Failed to reset inference_router: {e}", file=sys.stderr)

    return results


def log_memory_usage(prefix: str = "") -> None:
    """
    Log current memory usage for debugging purposes.

    Args:
        prefix: Optional prefix for the log message.
    """
    try:
        import psutil

        process = psutil.Process()
        mem_mb = process.memory_info().rss / 1024 / 1024
        print(f"{prefix}Memory usage: {mem_mb:.1f} MB", file=sys.stderr)
    except ImportError:
        # psutil not available, try alternative
        try:
            import resource

            mem_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            # On Linux, ru_maxrss is in KB; on macOS, it's in bytes
            import platform

            if platform.system() == "Darwin":
                mem_mb = mem_kb / 1024 / 1024
            else:
                mem_mb = mem_kb / 1024
            print(f"{prefix}Memory usage: {mem_mb:.1f} MB", file=sys.stderr)
        except Exception:
            print(f"{prefix}Memory usage: (unavailable)", file=sys.stderr)


__all__ = ["reset_all_caches", "log_memory_usage"]
