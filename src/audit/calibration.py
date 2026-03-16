#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""AEGF Calibration Engine — Inference parameter optimization loop.

This module implements the core calibration loop for the Inference Calibration
Suite (Stage 6). It performs a grid search through the parameter space using
the Cartesian product of parameter values, evaluating each configuration using
the Professor Judge and selecting the optimal sampling parameters.

The calibration process:
1. Generates all parameter profile combinations from the grid
2. For each prompt, iterates through all profiles
3. Generates a response using the profile's sampling parameters
4. Scores the response using the Judge (if available)
5. Applies a length penalty for responses under 200 words
6. Selects the best profile based on adjusted composite score

Public API
----------
- ``load_calibration_prompts_from_yaml`` — Load prompts from YAML with parameter extraction.
- ``extract_parameter_targets`` — Map evaluation focus to target parameters.
- ``get_focused_parameters`` — Get unique parameter names from prompts.
- ``validate_parameter_targets`` — Validate parameter targets against known parameters.
- ``analyze_evaluation_focus`` — Analyze evaluation_focus to map focus areas to parameter adjustments.
- ``get_focused_adjustment_strategy`` — Get consolidated adjustment strategy from all prompts.
- ``generate_parameter_adjustments`` — Generate parameter adjustments based on evaluation_focus analysis.
- ``extract_focus_analysis`` — Extract parameter_target/evaluation_focus analysis from prompts for report.
- ``get_parameter_priority_order`` — Determine priority order for parameter values based on focus strategy.
- ``generate_adaptive_profiles`` — Generate profiles prioritized by evaluation_focus relevance.
- ``get_adaptive_parameter_weights`` — Get weighting for each parameter based on focus strategy.
- ``refine_parameter_space`` — Refine parameter grid based on judge feedback.
- ``analyze_parameter_performance`` — Analyze parameter performance from calibration results.
- ``get_refinement_recommendations`` — Generate recommendations for parameter refinement.
- ``generate_calibration_analysis`` — Generate calibration analysis with parameter adjustment recommendations.
- ``save_calibration_analysis`` — Save calibration analysis JSON with parameter adjustment recommendations.
- ``generate_profiles`` — Generate Cartesian product of parameter grids.
- ``filter_noxious_parameter_values`` — Filter out noxious parameter values using quick evaluation.
- ``run_calibration`` — Execute the main calibration loop.
- ``calculate_composite_score`` — Compute weighted score from judge dimensions.
- ``apply_length_penalty`` — Adjust score based on response word count.
- ``CalibrationEngine`` — Main engine class orchestrating the calibration process.
- ``save_calibration_outputs`` — Save report JSON, vLLM config YAML, and calibration analysis JSON.
- ``save_vllm_config`` — Generate vLLM configuration from best profile.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from itertools import product
from typing import Any

from src.audit.calibration_schema import (
    CALIBRATION_GRID,
    MIN_RESPONSE_WORDS,
    SCORING_WEIGHTS,
    VALID_PARAMETERS,
    CalibrationCheckpoint,
    CalibrationPrompt,
    CalibrationReport,
    CalibrationResult,
    SamplingProfile,
)
from src.audit.inference import InferenceRouter
from src.audit.schema import ExamRecord, PromptGenerationError

logger = logging.getLogger(__name__)


# ======================================================================
# YAML Prompt Loading
# ======================================================================


def load_calibration_prompts_from_yaml(
    yaml_path: str,
) -> list[CalibrationPrompt]:
    """Load calibration prompts from a YAML file.

    Parses prompts from YAML format with support for parameter_target
    (comma-separated string or list) and evaluation_focus fields.

    Parameters
    ----------
    yaml_path : str
        Path to the YAML file containing calibration prompts.

    Returns
    -------
    list[CalibrationPrompt]
        List of parsed CalibrationPrompt objects.

    Raises
    ------
    FileNotFoundError
        If the YAML file does not exist.
    yaml.YAMLError
        If the YAML file is malformed.
    """
    import yaml

    if not os.path.isfile(yaml_path):
        raise FileNotFoundError(f"YAML file not found: {yaml_path}")

    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if data is None:
        return []

    # Handle both list format and dict with "prompts" key
    if isinstance(data, dict):
        prompts_list = data.get("prompts", data.get("samples", []))
    else:
        prompts_list = data

    prompts: list[CalibrationPrompt] = []
    for item in prompts_list:
        try:
            prompt = CalibrationPrompt.from_dict(item)
            prompts.append(prompt)
        except (KeyError, ValueError) as e:
            logger.warning("Skipping invalid prompt %s: %s", item.get("id", "unknown"), e)
            continue

    logger.info("Loaded %d calibration prompts from %s", len(prompts), yaml_path)
    return prompts


def extract_parameter_targets(
    prompts: list[CalibrationPrompt],
) -> dict[str, set[str]]:
    """Extract parameter targets from calibration prompts.

    Builds a mapping of evaluation focus areas to the set of parameters
    that should be targeted for each focus.

    Parameters
    ----------
    prompts : list[CalibrationPrompt]
        List of calibration prompts with parameter_target field.

    Returns
    -------
    dict[str, set[str]]
        Dictionary mapping evaluation focus to set of target parameters.
    """
    focus_to_params: dict[str, set[str]] = {}

    for prompt in prompts:
        focus = prompt.evaluation_focus
        if focus not in focus_to_params:
            focus_to_params[focus] = set()
        focus_to_params[focus].update(prompt.get_parameter_target_set())

    return focus_to_params


def get_focused_parameters(
    prompts: list[CalibrationPrompt],
) -> set[str]:
    """Get all unique parameter names targeted across all prompts.

    Parameters
    ----------
    prompts : list[CalibrationPrompt]
        List of calibration prompts.

    Returns
    -------
    set[str]
        Set of unique parameter names (e.g., {"temperature", "top_k", ...}).
    """
    all_params: set[str] = set()
    for prompt in prompts:
        all_params.update(prompt.get_parameter_target_set())
    return all_params


def validate_parameter_targets(
    prompts: list[CalibrationPrompt],
) -> list[str]:
    """Validate parameter targets against known valid parameters.

    Parameters
    ----------
    prompts : list[CalibrationPrompt]
        List of calibration prompts to validate.

    Returns
    -------
    list[str]
        List of validation error messages (empty if all valid).
    """
    errors: list[str] = []
    for prompt in prompts:
        for param in prompt.parameter_target:
            if param not in VALID_PARAMETERS:
                errors.append(
                    f"Prompt '{prompt.id}': invalid parameter '{param}'. "
                    f"Valid parameters: {VALID_PARAMETERS}"
                )
    return errors


# ======================================================================
# Evaluation Focus Analysis
# ======================================================================


# Mapping of evaluation focus keywords to parameter adjustment recommendations
# Each focus area maps to (parameters_to_increase, parameters_to_decrease, reasoning)
EVALUATION_FOCUS_MAPPING: dict[str, tuple[list[str], list[str], str]] = {
    # Exploration & Creativity
    "curiosidad": (
        ["top_k", "temperature"],
        ["presence_penalty"],
        "Higher top_k enables exploration of diverse concepts. Lower presence_penalty allows mentioning new topics.",
    ),
    "exploración": (
        ["top_k", "temperature"],
        ["presence_penalty"],
        "Exploration requires considering diverse options and avoiding topic avoidance.",
    ),
    # Reasoning & Logic
    "razonamiento": (
        ["temperature"],
        ["repetition_penalty"],
        "Moderate temperature allows creative problem-solving while maintaining logical consistency.",
    ),
    "lógica": (
        ["temperature"],
        ["min_p"],
        "Logical reasoning benefits from moderate creativity without overly strict filtering.",
    ),
    # Repetition & Obedience
    "obediencia": (
        ["repetition_penalty"],
        ["temperature"],
        "Higher repetition_penalty forces diverse wording while maintaining task focus.",
    ),
    "repetition penalty": (
        ["repetition_penalty"],
        ["min_p"],
        "Testing how repetition handling affects constraint following.",
    ),
    # Creativity & Innovation
    "creatividad": (
        ["temperature", "top_k"],
        ["repetition_penalty"],
        "Creative generation benefits from higher temperature and diverse token selection.",
    ),
    "innovación": (
        ["temperature", "top_k"],
        ["repetition_penalty", "presence_penalty"],
        "Innovation requires exploring new directions without fear of repetition.",
    ),
    "creativa": (
        ["temperature", "min_p"],
        ["repetition_penalty"],
        "Creative tasks need flexibility while maintaining thematic coherence.",
    ),
    # Consistency
    "consistencia": (
        ["repetition_penalty", "min_p"],
        ["temperature", "top_k"],
        "Consistent output requires stricter repetition control and filtering.",
    ),
    # Emotional & Perspective
    "emocional": (
        ["temperature"],
        ["min_p"],
        "Emotional generation benefits from creative flexibility while maintaining basic coherence.",
    ),
    "perspectiva": (
        ["temperature"],
        ["repetition_penalty"],
        "Taking different perspectives requires creative flexibility without repetitive patterns.",
    ),
    # Narrative & Redundancy
    "redundancia": (
        ["repetition_penalty", "presence_penalty"],
        ["temperature"],
        "Controlling redundancy requires strict penalty settings while maintaining output quality.",
    ),
    "narrativo": (
        ["presence_penalty"],
        ["repetition_penalty"],
        "Balanced narrative needs presence penalty to encourage topic development.",
    ),
    # Ethical & Multilayer
    "ético": (
        ["temperature", "top_k"],
        ["min_p"],
        "Ethical reasoning benefits from considering multiple frameworks with moderate filtering.",
    ),
    "multicapa": (
        ["temperature", "top_k"],
        ["repetition_penalty"],
        "Layered reasoning requires diverse perspectives without getting stuck in patterns.",
    ),
    # Structured Generation
    "estructurada": (
        ["top_k", "min_p"],
        ["temperature"],
        "Structured output benefits from constrained but coherent token selection.",
    ),
    # Fatigue & Conclusion
    "fatiga": (
        ["presence_penalty"],
        ["repetition_penalty"],
        "Preventing output fatigue requires encouraging new topics without excessive repetition control.",
    ),
    "conclusión": (
        ["presence_penalty"],
        ["top_k"],
        "Reaching conclusions benefits from topic development without excessive exploration.",
    ),
    # Balance
    "balance": (
        ["temperature", "top_k"],
        ["repetition_penalty", "presence_penalty"],
        "Balancing consistency and innovation requires moderate values across parameters.",
    ),
}


def analyze_evaluation_focus(
    prompts: list[CalibrationPrompt],
) -> dict[str, dict[str, Any]]:
    """Analyze evaluation_focus fields to map focus areas to parameter adjustments.

    Parses each prompt's evaluation_focus string to identify the primary focus area,
    then maps it to recommended parameter adjustments based on predefined heuristics.

    Parameters
    ----------
    prompts : list[CalibrationPrompt]
        List of calibration prompts with evaluation_focus fields.

    Returns
    -------
    dict[str, dict[str, Any]]
        Dictionary mapping each prompt ID to its focus analysis, including:
        - focus_area: The identified primary focus area (e.g., "creatividad")
        - parameters_to_increase: List of parameters to increase
        - parameters_to_decrease: List of parameters to decrease
        - reasoning: Explanation of why these adjustments are recommended
        - matched_keywords: List of keywords found in the evaluation_focus

    Examples
    --------
    >>> prompts = [CalibrationPrompt(id="p1", question="...", type="investigation",
    ...     parameter_target=["temperature"], evaluation_focus="Razonamiento y Temperatura")]
    >>> result = analyze_evaluation_focus(prompts)
    >>> result["p1"]["parameters_to_increase"]
    ["temperature"]
    """
    analysis: dict[str, dict[str, Any]] = {}

    for prompt in prompts:
        focus_text = prompt.evaluation_focus.lower()
        matched_keywords: list[str] = []
        best_match: str | None = None
        best_confidence: int = 0

        # Find matching focus areas based on keyword presence
        for focus_key, adjustments in EVALUATION_FOCUS_MAPPING.items():
            if focus_key in focus_text:
                matched_keywords.append(focus_key)
                # Longer keyword matches are more specific
                if len(focus_key) > best_confidence:
                    best_confidence = len(focus_key)
                    best_match = focus_key

        # Build analysis result for this prompt
        if best_match and best_match in EVALUATION_FOCUS_MAPPING:
            params_increase, params_decrease, reasoning = EVALUATION_FOCUS_MAPPING[best_match]
            # Filter to only include parameters that are in this prompt's parameter_target
            target_params = set(prompt.get_parameter_target_set())
            filtered_increase = [p for p in params_increase if p in target_params]
            filtered_decrease = [p for p in params_decrease if p in target_params]

            # If no intersection, use the original recommendations
            if not filtered_increase and not filtered_decrease:
                filtered_increase = params_increase
                filtered_decrease = params_decrease

            analysis[prompt.id] = {
                "focus_area": best_match,
                "parameters_to_increase": filtered_increase,
                "parameters_to_decrease": filtered_decrease,
                "reasoning": reasoning,
                "matched_keywords": matched_keywords,
                "confidence": best_confidence / len(focus_text) if focus_text else 0.0,
            }
        else:
            # No match found - return generic analysis
            analysis[prompt.id] = {
                "focus_area": "unknown",
                "parameters_to_increase": [],
                "parameters_to_decrease": [],
                "reasoning": "No specific focus area identified. Use default parameter grid.",
                "matched_keywords": matched_keywords,
                "confidence": 0.0,
            }
            logger.debug(
                "No evaluation_focus match for prompt %s: %s",
                prompt.id,
                prompt.evaluation_focus,
            )

    return analysis


def get_focused_adjustment_strategy(
    prompts: list[CalibrationPrompt],
) -> dict[str, list[str]]:
    """Get consolidated parameter adjustment strategy from all prompts.

    Aggregates parameter adjustment recommendations across all prompts
    to determine which parameters should generally be increased or decreased.

    Parameters
    ----------
    prompts : list[CalibrationPrompt]
        List of calibration prompts to analyze.

    Returns
    -------
    dict[str, list[str]]
        Dictionary with 'increase' and 'decrease' keys, each mapping to
        a list of parameter names recommended for adjustment.
    """
    analysis = analyze_evaluation_focus(prompts)

    increase_counts: dict[str, int] = {}
    decrease_counts: dict[str, int] = {}

    for prompt_analysis in analysis.values():
        for param in prompt_analysis.get("parameters_to_increase", []):
            increase_counts[param] = increase_counts.get(param, 0) + 1
        for param in prompt_analysis.get("parameters_to_decrease", []):
            decrease_counts[param] = decrease_counts.get(param, 0) + 1

    # Get parameters that appear more frequently as increase/decrease
    all_prompts = len(prompts)
    # Use lower threshold: at least 2 prompts or 20% of prompts, whichever is greater
    threshold = max(2, all_prompts // 5) if all_prompts > 0 else 1

    # Parameters recommended for increase in threshold or more prompts
    increase_params = [p for p, count in increase_counts.items() if count >= threshold]
    decrease_params = [p for p, count in decrease_counts.items() if count >= threshold]

    # If still empty, pick the top parameter by count
    if not increase_params and increase_counts:
        top_param = max(increase_counts.items(), key=lambda x: x[1])
        increase_params = [top_param[0]]
    if not decrease_params and decrease_counts:
        top_param = max(decrease_counts.items(), key=lambda x: x[1])
        decrease_params = [top_param[0]]

    return {
        "increase": increase_params,
        "decrease": decrease_params,
        "increase_details": increase_counts,
        "decrease_details": decrease_counts,
    }


def generate_parameter_adjustments(
    prompts: list[CalibrationPrompt],
    base_grid: dict[str, list[Any]] | None = None,
) -> dict[str, Any]:
    """Generate parameter adjustments based on evaluation_focus analysis.

    Analyzes the evaluation_focus fields from calibration prompts and generates
    concrete parameter value adjustments. This narrows the search space by focusing
    on parameters that are most relevant to the evaluation criteria.

    Parameters
    ----------
    prompts : list[CalibrationPrompt]
        List of calibration prompts with evaluation_focus fields.
    base_grid : dict[str, list[Any]] | None
        Base parameter grid to adjust. Defaults to CALIBRATION_GRID.

    Returns
    -------
    dict[str, Any]
        Dictionary containing:
        - adjusted_grid: Modified parameter grid with focused values
        - focus_strategy: The consolidated adjustment strategy
        - per_prompt_analysis: Individual prompt analysis results
        - recommendations: Summary of recommended adjustments

    Examples
    --------
    >>> prompts = [CalibrationPrompt(id="p1", question="...", type="investigation",
    ...     parameter_target=["temperature"], evaluation_focus="Creatividad")]
    >>> result = generate_parameter_adjustments(prompts)
    >>> result["adjusted_grid"]["temperature"]
    [0.6, 0.7, 0.8]  # Higher values for creativity focus
    """
    if base_grid is None:
        base_grid = dict(CALIBRATION_GRID)

    # Get consolidated strategy from all prompts
    strategy = get_focused_adjustment_strategy(prompts)

    # Get individual prompt analysis
    per_prompt_analysis = analyze_evaluation_focus(prompts)

    # Generate adjusted grid based on strategy
    adjusted_grid: dict[str, list[Any]] = {}

    for param_name, param_values in base_grid.items():
        if not param_values:
            adjusted_grid[param_name] = param_values
            continue

        # Determine if this parameter should be adjusted based on strategy
        should_increase = param_name in strategy.get("increase", [])
        should_decrease = param_name in strategy.get("decrease", [])

        if should_increase and not should_decrease:
            # Focus on higher values for this parameter
            adjusted_grid[param_name] = _adjust_for_increase(param_values, param_name)
        elif should_decrease and not should_increase:
            # Focus on lower values for this parameter
            adjusted_grid[param_name] = _adjust_for_decrease(param_values, param_name)
        elif should_increase and should_decrease:
            # Mixed signals - use full range
            adjusted_grid[param_name] = param_values
        else:
            # No specific focus - use original values
            adjusted_grid[param_name] = param_values

    # Build recommendations summary
    recommendations: list[dict[str, Any]] = []
    for param_name in base_grid:
        if param_name in strategy.get("increase", []):
            recommendations.append({
                "parameter": param_name,
                "action": "increase",
                "reason": "Recommended for increase based on evaluation_focus analysis",
                "values": adjusted_grid.get(param_name, []),
            })
        elif param_name in strategy.get("decrease", []):
            recommendations.append({
                "parameter": param_name,
                "action": "decrease",
                "reason": "Recommended for decrease based on evaluation_focus analysis",
                "values": adjusted_grid.get(param_name, []),
            })

    return {
        "adjusted_grid": adjusted_grid,
        "focus_strategy": strategy,
        "per_prompt_analysis": per_prompt_analysis,
        "recommendations": recommendations,
        "base_grid": base_grid,
    }


# ======================================================================
# Adaptive Grid Search
# ======================================================================


def get_parameter_priority_order(
    focus_strategy: dict[str, Any],
) -> dict[str, str]:
    """Determine priority order for parameter values based on focus strategy.

    Maps each parameter to whether its higher or lower values should be
    prioritized based on the evaluation_focus analysis.

    Parameters
    ----------
    focus_strategy : dict[str, Any]
        Strategy from get_focused_adjustment_strategy containing 'increase'
        and 'decrease' lists of parameter names.

    Returns
    -------
    dict[str, str]
        Dictionary mapping parameter names to 'high' or 'low' priority.
        Parameters not in the strategy default to 'medium' (balanced).

    Examples
    --------
    >>> strategy = {"increase": ["temperature"], "decrease": ["top_k"]}
    >>> get_parameter_priority_order(strategy)
    {"temperature": "high", "top_k": "low", "min_p": "medium", ...}
    """
    priority: dict[str, str] = {}

    increase_params = focus_strategy.get("increase", [])
    decrease_params = focus_strategy.get("decrease", [])

    # Default all parameters to medium priority (balanced exploration)
    default_params = ["temperature", "top_k", "min_p", "repetition_penalty", "presence_penalty"]
    for param in default_params:
        priority[param] = "medium"

    # Mark parameters for higher value priority
    for param in increase_params:
        priority[param] = "high"

    # Mark parameters for lower value priority
    for param in decrease_params:
        priority[param] = "low"

    return priority


def _sort_values_by_priority(
    values: list[Any],
    priority: str,
    param_name: str = "",
) -> list[Any]:
    """Sort parameter values based on priority.

    Parameters
    ----------
    values : list[Any]
        Parameter values to sort.
    priority : str
        Priority: 'high' (prefer higher), 'low' (prefer lower), 'medium' (balanced).
    param_name : str
        Parameter name for type-specific handling.

    Returns
    -------
    list[Any]
        Values sorted according to priority.
    """
    try:
        # Convert to float for sorting
        value_pairs = [(v, float(v)) for v in values]
    except (ValueError, TypeError):
        return values

    if priority == "high":
        # Sort descending - higher values first
        value_pairs.sort(key=lambda x: x[1], reverse=True)
    elif priority == "low":
        # Sort ascending - lower values first
        value_pairs.sort(key=lambda x: x[1])
    else:
        # Medium - keep original order or sort by distance from middle
        if len(value_pairs) > 1:
            numeric_values = [v[1] for v in value_pairs]
            mid = (min(numeric_values) + max(numeric_values)) / 2
            # Sort by distance from middle (closest first - balanced exploration)
            value_pairs.sort(key=lambda x: abs(x[1] - mid))

    return [v[0] for v in value_pairs]


def generate_adaptive_profiles(
    prompts: list[CalibrationPrompt] | None = None,
    grid: dict[str, list[Any]] | None = None,
    focus_strategy: dict[str, Any] | None = None,
) -> list[SamplingProfile]:
    """Generate sampling profiles prioritized by evaluation_focus relevance.

    This adaptive grid search uses the evaluation_focus from calibration prompts
    to prioritize parameter combinations that are most relevant to the evaluation
    criteria. Profiles are sorted so that the most promising combinations are
    evaluated first.

    Parameters
    ----------
    prompts : list[CalibrationPrompt] | None
        List of calibration prompts with evaluation_focus fields.
        If provided, the focus strategy will be derived from these prompts.
    grid : dict[str, list[Any]] | None
        Parameter grid to use. Defaults to CALIBRATION_GRID.
    focus_strategy : dict[str, Any] | None
        Pre-computed focus strategy. If not provided, it will be derived
        from prompts if available.

    Returns
    -------
    list[SamplingProfile]
        List of SamplingProfile combinations, ordered by relevance to
        evaluation_focus. The most promising profiles come first.

    Examples
    --------
    >>> prompts = [CalibrationPrompt(id="p1", question="...", type="investigation",
    ...     parameter_target=["temperature"], evaluation_focus="Creatividad")]
    >>> profiles = generate_adaptive_profiles(prompts)
    >>> # Profiles with higher temperature will be tested first
    """
    if grid is None:
        grid = dict(CALIBRATION_GRID)

    # Get focus strategy
    if focus_strategy is None:
        if prompts:
            focus_strategy = get_focused_adjustment_strategy(prompts)
        else:
            focus_strategy = {"increase": [], "decrease": []}

    # Get priority order for each parameter
    priority_order = get_parameter_priority_order(focus_strategy)

    # Create ordered grids based on priority
    ordered_grid: dict[str, list[Any]] = {}
    for param_name, param_values in grid.items():
        if param_values:
            priority = priority_order.get(param_name, "medium")
            ordered_grid[param_name] = _sort_values_by_priority(param_values, priority, param_name)
        else:
            ordered_grid[param_name] = param_values

    # Generate profiles from ordered grid
    # Since we want high-priority values first, we generate combinations
    # where parameters with higher priority are in the outer loop
    keys = list(ordered_grid.keys())
    values = [ordered_grid[k] for k in keys]

    profiles: list[SamplingProfile] = []
    for combo in product(*values):
        profile_dict = dict(zip(keys, combo))
        try:
            profile = SamplingProfile(
                temperature=profile_dict["temperature"],
                top_p=profile_dict.get("top_p", 0.9),
                top_k=profile_dict["top_k"],
                min_p=profile_dict["min_p"],
                repetition_penalty=profile_dict.get("repetition_penalty", 1.0),
                presence_penalty=profile_dict.get("presence_penalty"),
            )
            profiles.append(profile)
        except (ValueError, KeyError) as e:
            logger.warning("Skipping invalid profile combination %s: %s", profile_dict, e)

    return profiles


def get_adaptive_parameter_weights(
    focus_strategy: dict[str, Any],
) -> dict[str, float]:
    """Get weighting for each parameter based on focus strategy.

    Parameters that are recommended for increase/decrease get higher weight,
    meaning their variation has more impact on profile ordering.

    Parameters
    ----------
    focus_strategy : dict[str, Any]
        Strategy from get_focused_adjustment_strategy.

    Returns
    -------
    dict[str, float]
        Dictionary mapping parameter names to weights (0.0 to 1.0).

    Examples
    --------
    >>> strategy = {"increase": ["temperature"], "decrease": ["top_k"]}
    >>> weights = get_adaptive_parameter_weights(strategy)
    >>> weights["temperature"]  # Higher weight for focused parameter
    0.75
    """
    weights: dict[str, float] = {}

    # Base weight for all parameters
    base_weight = 0.25
    focus_boost = 0.5  # Additional weight for focused parameters

    default_params = ["temperature", "top_k", "min_p", "repetition_penalty", "presence_penalty"]

    increase_params = set(focus_strategy.get("increase", []))
    decrease_params = set(focus_strategy.get("decrease", []))

    for param in default_params:
        if param in increase_params or param in decrease_params:
            weights[param] = base_weight + focus_boost
        else:
            weights[param] = base_weight

    return weights


def _adjust_for_increase(values: list[Any], param_name: str = "") -> list[Any]:
    """Adjust parameter values upward for focused parameter increase.

    Shifts the value range upward to explore higher values.

    Parameters
    ----------
    values : list[Any]
        Original parameter values.
    param_name : str
        Parameter name for type-specific clamping.

    Returns
    -------
    list[Any]
        Adjusted values shifted upward.
    """
    # Convert to float for numeric adjustment
    try:
        numeric_values = [float(v) for v in values]
        min_val = min(numeric_values)
        max_val = max(numeric_values)
        range_size = max_val - min_val

        # Shift range upward by 20%
        shift = range_size * 0.2
        adjusted = [round(v + shift, 2) for v in numeric_values]

        # Ensure values stay within reasonable bounds
        adjusted = [_clamp_to_valid_range(v, numeric_values[0], param_name) for v in adjusted]

        return adjusted
    except (ValueError, TypeError):
        return values


def _adjust_for_decrease(values: list[Any], param_name: str = "") -> list[Any]:
    """Adjust parameter values downward for focused parameter decrease.

    Shifts the value range downward to explore lower values.

    Parameters
    ----------
    values : list[Any]
        Original parameter values.
    param_name : str
        Parameter name for type-specific clamping.

    Returns
    -------
    list[Any]
        Adjusted values shifted downward.
    """
    try:
        numeric_values = [float(v) for v in values]
        min_val = min(numeric_values)
        max_val = max(numeric_values)
        range_size = max_val - min_val

        # Shift range downward by 20%
        shift = range_size * 0.2
        adjusted = [round(v - shift, 2) for v in numeric_values]

        # Ensure values stay within reasonable bounds
        adjusted = [_clamp_to_valid_range(v, numeric_values[-1], param_name) for v in adjusted]

        return adjusted
    except (ValueError, TypeError):
        return values


def _clamp_to_valid_range(value: float, original: Any, param_name: str = "") -> float:
    """Clamp a value to valid parameter ranges based on parameter type.

    Parameters
    ----------
    value : float
        The value to clamp.
    original : Any
        Original value to determine parameter type.
    param_name : str
        Parameter name for type-specific clamping.

    Returns
    -------
    float
        Clamped value within valid range.
    """
    # Determine parameter type from original value
    try:
        orig_float = float(original)
        orig_is_int = isinstance(original, int) or (isinstance(original, str) and original.isdigit())

        # Check parameter name first if provided
        if param_name == "top_k":
            return max(1, int(round(value)))
        elif param_name in ("repetition_penalty", "presence_penalty"):
            return max(1.0, min(2.0, value))
        elif param_name in ("temperature", "min_p"):
            return max(0.0, min(2.0, value))

        # Fallback: infer from value
        # top_k is typically > 1 and integer-like
        if orig_is_int and orig_float > 1:
            return max(1, int(round(value)))
        # penalty parameters are > 1.0
        elif orig_float > 1.0:
            return max(1.0, min(2.0, value))
        # temperature/min_p are 0-1
        else:
            return max(0.0, min(2.0, value))
    except (ValueError, TypeError):
        pass

    return value


# ======================================================================
# Parameter Refinement (T042)
# ======================================================================


def refine_parameter_space(
    results: list[CalibrationResult],
    base_grid: dict[str, list[Any]] | None = None,
    top_percent: float = 0.25,
    refinement_factor: float = 0.5,
) -> dict[str, list[Any]]:
    """Refine parameter space based on judge feedback from calibration results.

    Analyzes calibration results to identify which parameter ranges performed best
    and narrows the search space around those values. This enables iterative
    refinement of the parameter grid based on actual judge evaluations.

    Parameters
    ----------
    results : list[CalibrationResult]
        List of calibration results with judge scores.
    base_grid : dict[str, list[Any]] | None
        Base parameter grid to refine. Defaults to CALIBRATION_GRID.
    top_percent : float
        Percentage of top-performing results to consider (default 0.25 = top 25%).
    refinement_factor : float
        How much to narrow the search space (0.5 = narrow by 50%).

    Returns
    -------
    dict[str, list[Any]]
        Refined parameter grid with narrowed ranges.

    Examples
    --------
    >>> results = [
    ...     CalibrationResult(
    ...         profile=SamplingProfile(temperature=0.5, top_p=0.9, top_k=20, min_p=0.02, repetition_penalty=1.1),
    ...         exam_id="p1", judge_scores={"ha_modernity": 0.8, "reasoning_depth": 0.7, "functionality": 0.8, "completeness": 0.7, "style": 0.8},
    ...         composite_score=0.77, adjusted_score=0.77, response_length=250, timestamp="2026-01-01T00:00:00Z"
    ...     ),
    ...     # ... more results with different scores
    ... ]
    >>> refined = refine_parameter_space(results)
    >>> refined["temperature"]  # Narrowed around best-performing temperature
    [0.55, 0.6, 0.65]
    """
    if base_grid is None:
        base_grid = dict(CALIBRATION_GRID)

    if not results:
        logger.warning("No results provided for refinement, returning base grid")
        return base_grid

    # Calculate composite scores for each result if not already done
    scored_results = []
    for r in results:
        score = r.adjusted_score if r.adjusted_score > 0 else r.composite_score
        scored_results.append((score, r))

    # Sort by score descending
    scored_results.sort(key=lambda x: x[0], reverse=True)

    # Take top performing results
    num_top = max(1, int(len(scored_results) * top_percent))
    top_results = scored_results[:num_top]

    logger.info(
        "Refining parameter space using top %d of %d results (%.1f%%)",
        num_top,
        len(scored_results),
        top_percent * 100,
    )

    # Analyze each parameter and find best-performing ranges
    refined_grid: dict[str, list[Any]] = {}

    for param_name in base_grid:
        param_values = base_grid[param_name]

        if not param_values:
            refined_grid[param_name] = param_values
            continue

        # Extract values of this parameter from top results
        param_scores: list[tuple[Any, float]] = []
        for score, result in top_results:
            param_value = getattr(result.profile, param_name, None)
            if param_value is not None:
                param_scores.append((param_value, score))

        if not param_scores:
            # No data for this parameter, use original values
            refined_grid[param_name] = param_values
            continue

        # Calculate weighted average (weight by score)
        total_weight = sum(s for _, s in param_scores)
        if total_weight > 0:
            weighted_avg = sum(v * s for v, s in param_scores) / total_weight
        else:
            weighted_avg = sum(v for v, _ in param_scores) / len(param_scores)

        # Narrow around weighted average
        numeric_values = []
        for v in param_values:
            try:
                numeric_values.append(float(v))
            except (ValueError, TypeError):
                numeric_values.append(v)

        # Find original min/max for numeric parameters
        numeric_originals = [v for v in numeric_values if isinstance(v, (int, float))]
        if numeric_originals:
            min_val = min(numeric_originals)
            max_val = max(numeric_originals)
            range_size = max_val - min_val

            # Narrow the range
            half_range = (range_size * refinement_factor) / 2
            new_min = max(min_val, weighted_avg - half_range)
            new_max = min(max_val, weighted_avg + half_range)

            # Generate refined values (keep same count, just shifted)
            num_values = len(param_values)
            if num_values == 1:
                refined_values = [round(weighted_avg, 2)]
            else:
                step = (new_max - new_min) / (num_values - 1) if num_values > 1 else 0
                refined_values = [round(new_min + i * step, 2) for i in range(num_values)]

            # Clamp to valid ranges
            refined_values = [
                _clamp_to_valid_range(v, param_values[0], param_name)
                for v in refined_values
            ]

            logger.debug(
                "Refined %s: original %s -> refined %s (avg=%.2f)",
                param_name,
                param_values,
                refined_values,
                weighted_avg,
            )

            refined_grid[param_name] = refined_values
        else:
            # Non-numeric parameter, keep original values
            refined_grid[param_name] = param_values

    return refined_grid


def analyze_parameter_performance(
    results: list[CalibrationResult],
) -> dict[str, dict[str, Any]]:
    """Analyze performance of each parameter value based on judge feedback.

    Provides detailed statistics about how each parameter value performed
    across all calibration results.

    Parameters
    ----------
    results : list[CalibrationResult]
        List of calibration results with judge scores.

    Returns
    -------
    dict[str, dict[str, Any]]
        Dictionary mapping parameter names to their performance statistics.
        Each entry contains:
        - values: list of unique values tested
        - performance: dict mapping value -> average score
        - best_value: the value with highest average score
        - best_score: the average score for best_value

    Examples
    --------
    >>> results = [...]  # Calibration results
    >>> analysis = analyze_parameter_performance(results)
    >>> analysis["temperature"]["best_value"]
    0.6
    """
    if not results:
        return {}

    # Group results by parameter
    param_data: dict[str, dict[Any, list[float]]] = {}

    for result in results:
        score = result.adjusted_score if result.adjusted_score > 0 else result.composite_score

        for param_name in ["temperature", "top_k", "min_p", "repetition_penalty"]:
            param_value = getattr(result.profile, param_name, None)
            if param_value is None:
                continue

            if param_name not in param_data:
                param_data[param_name] = {}

            if param_value not in param_data[param_name]:
                param_data[param_name][param_value] = []

            param_data[param_name][param_value].append(score)

    # Calculate statistics for each parameter
    analysis: dict[str, dict[str, Any]] = {}

    for param_name, value_scores in param_data.items():
        values = list(value_scores.keys())
        performance: dict[str, float] = {}
        best_value = None
        best_avg_score = -1.0

        for value, scores in value_scores.items():
            avg_score = sum(scores) / len(scores) if scores else 0.0
            performance[str(value)] = round(avg_score, 4)

            if avg_score > best_avg_score:
                best_avg_score = avg_score
                best_value = value

        analysis[param_name] = {
            "values": values,
            "performance": performance,
            "best_value": best_value,
            "best_score": round(best_avg_score, 4),
            "sample_count": {str(v): len(s) for v, s in value_scores.items()},
        }

    return analysis


def get_refinement_recommendations(
    results: list[CalibrationResult],
    base_grid: dict[str, list[Any]] | None = None,
) -> dict[str, Any]:
    """Generate recommendations for parameter refinement based on judge feedback.

    Provides actionable recommendations for narrowing the search space
    based on analysis of calibration results.

    Parameters
    ----------
    results : list[CalibrationResult]
        List of calibration results with judge scores.
    base_grid : dict[str, list[Any]] | None
        Base parameter grid. Defaults to CALIBRATION_GRID.

    Returns
    -------
    dict[str, Any]
        Dictionary containing:
        - parameter_analysis: Detailed performance analysis per parameter
        - refined_grid: The narrowed parameter grid
        - recommendations: List of actionable recommendations
        - summary: Overall summary of the analysis
    """
    if base_grid is None:
        base_grid = dict(CALIBRATION_GRID)

    # Analyze parameter performance
    analysis = analyze_parameter_performance(results)

    # Generate refined grid
    refined_grid = refine_parameter_space(results, base_grid)

    # Generate recommendations
    recommendations: list[dict[str, Any]] = []

    for param_name in base_grid:
        if param_name not in analysis:
            continue

        param_analysis = analysis[param_name]
        best_value = param_analysis.get("best_value")
        best_score = param_analysis.get("best_score", 0)

        if best_value is not None:
            original_values = base_grid[param_name]
            refined_values = refined_grid.get(param_name, original_values)

            # Determine recommendation
            if original_values != refined_values:
                recommendations.append({
                    "parameter": param_name,
                    "action": "narrow_range",
                    "reason": f"Best performing value: {best_value} (avg score: {best_score:.2f})",
                    "original_values": original_values,
                    "refined_values": refined_values,
                    "best_value": best_value,
                })
            else:
                recommendations.append({
                    "parameter": param_name,
                    "action": "keep_range",
                    "reason": f"No significant improvement found (best: {best_value}, score: {best_score:.2f})",
                    "original_values": original_values,
                    "refined_values": refined_values,
                    "best_value": best_value,
                })

    # Calculate summary statistics
    total_results = len(results)
    avg_score = sum(r.composite_score for r in results) / total_results if total_results > 0 else 0
    best_result = max(results, key=lambda r: r.adjusted_score) if results else None
    best_score_overall = best_result.adjusted_score if best_result else 0

    summary = {
        "total_results": total_results,
        "average_score": round(avg_score, 4),
        "best_score_overall": round(best_score_overall, 4),
        "best_profile": best_result.profile.to_dict() if best_result else None,
        "parameters_analyzed": list(analysis.keys()),
    }

    return {
        "parameter_analysis": analysis,
        "refined_grid": refined_grid,
        "recommendations": recommendations,
        "summary": summary,
        "base_grid": base_grid,
    }


# ======================================================================
# Focus Analysis Extraction
# ======================================================================


def extract_focus_analysis(
    prompts: list[dict[str, str]],
) -> dict[str, Any]:
    """Extract parameter_target/evaluation_focus analysis from prompts.

    Analyzes calibration prompts to extract and aggregate the intelligent
    parameter targeting analysis based on their metadata fields.

    Parameters
    ----------
    prompts : list[dict[str, str]]
        List of prompts, potentially containing parameter_target and
        evaluation_focus fields.

    Returns
    -------
    dict[str, Any]
        Dictionary containing:
        - has_focus_data: Whether prompts contained focus data
        - focused_parameters: Set of parameters targeted across all prompts
        - evaluation_foci: List of unique evaluation focus values
        - adjustment_strategy: Consolidated parameter adjustment strategy
        - prompts_with_focus: Count of prompts with focus data
        - focus_distribution: Distribution of evaluation foci
    """
    # Convert dict prompts to CalibrationPrompt if they have focus data
    calibration_prompts: list[CalibrationPrompt] = []

    for prompt in prompts:
        # Check if prompt has focus-related fields
        # Handle both string and list formats for parameter_target
        param_target = prompt.get("parameter_target")
        has_param_target = False
        if param_target is not None:
            if isinstance(param_target, str):
                has_param_target = bool(param_target.strip())
            elif isinstance(param_target, list):
                has_param_target = len(param_target) > 0

        eval_focus = prompt.get("evaluation_focus")
        has_eval_focus = False
        if eval_focus is not None and isinstance(eval_focus, str):
            has_eval_focus = bool(eval_focus.strip())

        if has_param_target or has_eval_focus:
            # Convert to CalibrationPrompt for analysis
            # Map common field names to what CalibrationPrompt expects
            cal_prompt_dict = {
                "id": prompt.get("id", "unknown"),
                "question": prompt.get("question", prompt.get("text", prompt.get("prompt", ""))),
                "type": prompt.get("type", "investigation"),
                "parameter_target": prompt.get("parameter_target", ""),
                "evaluation_focus": prompt.get("evaluation_focus", ""),
            }
            try:
                cal_prompt = CalibrationPrompt.from_dict(cal_prompt_dict)
                calibration_prompts.append(cal_prompt)
            except (KeyError, ValueError) as e:
                logger.debug("Skipping prompt without valid focus data: %s", e)

    # If no prompts with focus data, return empty analysis
    if not calibration_prompts:
        return {
            "has_focus_data": False,
            "focused_parameters": [],
            "evaluation_foci": [],
            "adjustment_strategy": {},
            "prompts_with_focus": 0,
            "focus_distribution": {},
        }

    # Extract focused parameters
    focused_params = get_focused_parameters(calibration_prompts)

    # Get unique evaluation foci
    evaluation_foci = list(set(p.evaluation_focus for p in calibration_prompts if p.evaluation_focus))

    # Get adjustment strategy
    adjustment_strategy = get_focused_adjustment_strategy(calibration_prompts)

    # Generate focus distribution
    focus_counts: dict[str, int] = {}
    for prompt in calibration_prompts:
        focus = prompt.evaluation_focus or "unspecified"
        focus_counts[focus] = focus_counts.get(focus, 0) + 1

    # Generate parameter adjustments if prompts have focus
    parameter_adjustments = generate_parameter_adjustments(
        calibration_prompts,
        CALIBRATION_GRID,
    )

    return {
        "has_focus_data": True,
        "focused_parameters": list(focused_params),
        "evaluation_foci": evaluation_foci,
        "adjustment_strategy": adjustment_strategy,
        "prompts_with_focus": len(calibration_prompts),
        "focus_distribution": focus_counts,
        "parameter_adjustments": parameter_adjustments,
    }


# ======================================================================
# Profile Generation
# ======================================================================


def generate_profiles(
    grid: dict[str, list[Any]] | None = None,
) -> list[SamplingProfile]:
    """Generate all sampling profiles from a Cartesian product of parameter grids.

    Parameters
    ----------
    grid : dict[str, list[Any]] | None
        Parameter grid to use. Defaults to CALIBRATION_GRID.

    Returns
    -------
    list[SamplingProfile]
        List of all possible SamplingProfile combinations.
    """
    if grid is None:
        grid = CALIBRATION_GRID

    keys = list(grid.keys())
    values = [grid[k] for k in keys]

    profiles: list[SamplingProfile] = []
    for combo in product(*values):
        profile_dict = dict(zip(keys, combo))
        try:
            profile = SamplingProfile(
                temperature=profile_dict["temperature"],
                top_p=profile_dict["top_p"],
                top_k=profile_dict["top_k"],
                min_p=profile_dict["min_p"],
                repetition_penalty=profile_dict["repetition_penalty"],
                presence_penalty=profile_dict.get("presence_penalty"),
            )
            profiles.append(profile)
        except ValueError as e:
            logger.warning("Skipping invalid profile combination %s: %s", profile_dict, e)

    return profiles


# ======================================================================
# Score Calculation
# ======================================================================


def calculate_composite_score(
    judge_scores: dict[str, float],
    weights: dict[str, float] | None = None,
) -> float:
    """Calculate composite score from judge dimension scores.

    Uses provided weights or defaults to SCORING_WEIGHTS (Stage 5: HA evaluation).
    For Stage 6 calibration, use CALIBRATION_SCORING_WEIGHTS.

    Parameters
    ----------
    judge_scores : dict[str, float]
        Dictionary of judge dimension scores.
    weights : dict[str, float] | None
        Optional weights to use. If None, uses SCORING_WEIGHTS.

    Returns
    -------
    float
        Weighted composite score (0.0 to 1.0).
    """
    from src.audit.schema import CALIBRATION_SCORING_WEIGHTS

    # Detect Stage 6 calibration dimensions vs Stage 5 HA dimensions
    if weights is None:
        if "parameter_effectiveness" in judge_scores:
            weights = CALIBRATION_SCORING_WEIGHTS
        else:
            weights = SCORING_WEIGHTS

    composite = 0.0
    for dimension, weight in weights.items():
        score = judge_scores.get(dimension, 0.0)
        composite += score * weight

    return composite


def count_words(text: str) -> int:
    """Count words in text.

    Parameters
    ----------
    text : str
        Input text to count words in.

    Returns
    -------
    int
        Number of words.
    """
    if not text:
        return 0
    return len(text.split())


def apply_length_penalty(
    composite_score: float,
    response_length: int,
    min_words: int = MIN_RESPONSE_WORDS,
) -> float:
    """Apply penalty for responses shorter than minimum word count.

    Penalizes responses shorter than min_words by reducing the composite score
    proportionally to the shortfall. This discourages lazy/superficial responses.

    Parameters
    ----------
    composite_score : float
        The calculated composite score before penalty.
    response_length : int
        Word count of the response.
    min_words : int
        Minimum acceptable word count (default: 200).

    Returns
    -------
    float
        Adjusted score with penalty applied (can be negative for very short responses).
    """
    if response_length >= min_words:
        return composite_score

    # Calculate penalty proportion (max 50% penalty for very short responses)
    shortfall = min_words - response_length
    penalty_ratio = min(shortfall / min_words, 0.5)

    adjusted = composite_score * (1.0 - penalty_ratio)
    logger.debug(
        "Length penalty applied: %d words (min %d), penalty=%.2f, "
        "adjusted_score=%.3f",
        response_length,
        min_words,
        penalty_ratio,
        adjusted,
    )

    return adjusted


# ======================================================================
# Response Generation with Sampling Parameters
# ======================================================================


def generate_response_with_profile(
    client: Any,
    prompt: str,
    profile: SamplingProfile,
    max_tokens: int = 65536,
    retries: int = 3,
    retry_delay: float = 5.0,
) -> str:
    """Generate a response using the specified sampling profile.

    Parameters
    ----------
    client : BaseInferenceClient
        Inference client to use for generation.
    prompt : str
        Input prompt to generate response from.
    profile : SamplingProfile
        Sampling parameters to use.
    max_tokens : int
        Maximum tokens to generate.
    retries : int
        Number of retry attempts.
    retry_delay : float
        Delay between retries in seconds.

    Returns
    -------
    str
        Generated response text.
    """
    # Use vLLM-specific sampling parameters via the generate method
    # Pass all sampling parameters from the profile to enable proper calibration
    return client.generate_with_retry(
        prompt=prompt,
        system_prompt=None,  # Closed-book: no system prompt
        max_tokens=max_tokens,
        temperature=profile.temperature,
        top_k=profile.top_k,
        min_p=profile.min_p,
        repetition_penalty=profile.repetition_penalty,
        presence_penalty=profile.presence_penalty,
        retries=retries,
        retry_delay=retry_delay,
    )


# ======================================================================
# Calibration Engine
# ======================================================================


class CalibrationEngine:
    """Main engine for inference parameter calibration.

    Orchestrates the calibration process:
    1. Generate all parameter profiles from grid
    2. For each prompt, iterate through all profiles
    3. Generate response with profile parameters
    4. Score response using judge (if available)
    5. Apply length penalty
    6. Track results and select best profile

    Attributes
    ----------
    profiles : list[SamplingProfile]
        All parameter profiles to evaluate.
    prompts : list[dict[str, str]]
        List of prompts to evaluate against.
    student_client : BaseInferenceClient
        Client for generating student responses.
    judge_client : BaseInferenceClient | None
        Optional client for judge scoring.
    results : list[CalibrationResult]
        Results from all profile evaluations.
    """

    def __init__(
        self,
        prompts: list[dict[str, str]],
        profiles: list[SamplingProfile] | None = None,
        student_client: Any | None = None,
        judge_client: Any | None = None,
        checkpoint_dir: str | None = None,
        use_noxious_filter: bool = False,
        noxious_loss_threshold: float = 0.15,
        noxious_aggressiveness: float = 0.5,
    ) -> None:
        """Initialize the calibration engine.

        Parameters
        ----------
        prompts : list[dict[str, str]]
            List of prompts with at least 'id' and 'text' keys.
        profiles : list[SamplingProfile] | None
            Parameter profiles to evaluate. Generated from grid if not provided.
        student_client : Any | None
            Inference client for student model. Created if not provided.
        judge_client : Any | None
            Inference client for judge model. Created if not provided.
        checkpoint_dir : str | None
            Directory to save checkpoints for resume capability.
        use_noxious_filter : bool
            Whether to enable noxious parameter filter for early pruning.
        """
        self.prompts = prompts
        self.profiles = profiles if profiles is not None else generate_profiles()
        self.results: list[CalibrationResult] = []
        self.checkpoint_dir = checkpoint_dir
        self._completed_profiles: set[tuple[int, int]] = set()
        
        # Dynamic noxious filter: track discarded parameter values
        self._discarded_params: dict[str, set[Any]] = {}  # {param: {discarded_values}}
        self._use_noxious_filter = use_noxious_filter
        self._noxious_loss_threshold = noxious_loss_threshold
        # Aggressiveness controls fraction of worst values to drop during
        # pre-resume aggregation (0.0-1.0). Default 0.5 => drop worst 50%.
        self._noxious_aggressiveness = max(0.0, min(1.0, float(noxious_aggressiveness)))

        # Initialize clients
        router = InferenceRouter()
        self.student_client = student_client or router.student()
        self.judge_client = judge_client

        # Try to load checkpoint if directory provided
        self._loaded_checkpoint: CalibrationCheckpoint | None = None
        if checkpoint_dir:
            self._loaded_checkpoint = self._load_checkpoint(checkpoint_dir)
            if self._loaded_checkpoint:
                # Restore state from checkpoint
                self.results = list(self._loaded_checkpoint.all_results)
                self._completed_profiles = {
                    tuple(p) for p in self._loaded_checkpoint.completed_profiles
                }
                # Restore persisted discarded params if present
                try:
                    if getattr(self._loaded_checkpoint, "discarded_params", None):
                        self._discarded_params = {
                            k: set(v) for k, v in self._loaded_checkpoint.discarded_params.items()
                        }
                        logger.info(
                            "Restored %d discarded parameter sets from checkpoint",
                            len(self._discarded_params),
                        )
                except Exception:
                    logger.debug("Failed to restore discarded_params from checkpoint", exc_info=True)
                logger.info(
                    "Resuming from checkpoint: %d iterations already completed (%.1f%%)",
                    len(self._completed_profiles),
                    self._loaded_checkpoint.progress_percentage,
                )
                # Re-derive discarded params from restored results so the noxious filter
                # is active immediately (not just after the first new prompt sweep).
                if self._use_noxious_filter and self.results:
                    self._update_discarded_params(self._noxious_loss_threshold)
                    logger.info(
                        "Noxious filter re-derived from checkpoint: %d param(s) with discarded values",
                        len(self._discarded_params),
                    )

            # Enrich _discarded_params from the noxious pre-filter checkpoint.
            # This provides much richer signal (multi-prompt per-value averages)
            # than the few calibration results in self.results, allowing the
            # dynamic skip to work immediately on --resume.
            if self._use_noxious_filter:
                self._derive_discards_from_noxious_checkpoint(
                    checkpoint_dir, self._noxious_loss_threshold
                )

    def run(
        self,
        max_tokens: int = 65536,
        verbose: bool = True,
        checkpoint_dir: str | None = None,
    ) -> CalibrationReport:
        """Run the full calibration loop.

        Parameters
        ----------
        max_tokens : int
            Maximum tokens to generate per response.
        verbose : bool
            Whether to log progress verbosely.
        checkpoint_dir : str | None
            Directory to save checkpoints for resume capability. If provided,
            saves a checkpoint after each iteration.

        Returns
        -------
        CalibrationReport
            Complete calibration results with best profile.
        """
        # Use checkpoint_dir from parameter or fall back to instance variable
        if checkpoint_dir is not None:
            self.checkpoint_dir = checkpoint_dir

        total_prompts = len(self.prompts)
        total_profiles = len(self.profiles)
        total_iterations = total_prompts * total_profiles

        if verbose:
            logger.info("")
            logger.info("╔" + "═" * 72 + "╗")
            logger.info("║" + " 🔬 INFERENCE PARAMETER CALIBRATION ".center(72) + "║")
            logger.info("╠" + "═" * 72 + "╣")
            logger.info("║  Prompts: %-60d║" % total_prompts)
            logger.info("║  Profiles: %-58d║" % total_profiles)
            logger.info("║  Total iterations: %-53d║" % total_iterations)
            logger.info("╠" + "═" * 72 + "╣")
            # Show parameter grid being used
            logger.info("║  Parameter Grid (sample):".ljust(72) + "║")
            for i, profile in enumerate(self.profiles[:3]):  # Show first 3
                line = f"║    {i+1}: t={profile.temperature:.1f} tp={profile.top_p:.2f} k={profile.top_k} min={profile.min_p:.2f} rep={profile.repetition_penalty:.2f}".ljust(72) + "║"
                logger.info(line)
            if len(self.profiles) > 3:
                line = f"║    ... and {len(self.profiles) - 3} more profiles".ljust(72) + "║"
                logger.info(line)
            logger.info("╚" + "═" * 72 + "╝")
            logger.info("")

        iteration = 0
        best_result: CalibrationResult | None = None  # Track best result for logging
        previous_score: float = 0.0  # Track previous score for comparison

        for prompt_idx, prompt in enumerate(self.prompts):
            prompt_id = prompt.get("id", f"prompt_{prompt_idx}")
            # Support multiple field names: text, prompt, or question
            prompt_text = prompt.get("text", prompt.get("prompt", prompt.get("question", "")))

            if not prompt_text:
                logger.warning("Skipping empty prompt at index %d", prompt_idx)
                continue

            for profile_idx, profile in enumerate(self.profiles):
                # Skip if already completed in previous run (resume capability)
                if (prompt_idx, profile_idx) in self._completed_profiles:
                    # Suppressed to avoid log spam on massive resumes
                    iteration += 1
                    continue

                # Skip profiles whose parameter values have been dynamically discarded
                if self._use_noxious_filter and self._is_profile_noxious(profile):
                    logger.debug(
                        "⏭ [%d/%d] Skipping noxious profile (discarded values active)",
                        iteration + 1,
                        total_iterations,
                    )
                    iteration += 1
                    continue

                iteration += 1

                # Show what prompt is being tested - START line
                prompt_short = prompt_id.replace("calibration_prompt_", "P")
                presence = " presence_penalty=%s" % profile.presence_penalty if profile.presence_penalty is not None else ""
                profile_short = "temperature=%s top_p=%s top_k=%s min_p=%s repetition_penalty=%s%s" % (
                    profile.temperature, profile.top_p, profile.top_k, profile.min_p, profile.repetition_penalty, presence
                )
                
                # Calc dynamically how many profiles are actually alive
                if self._use_noxious_filter:
                    alive_profiles = sum(1 for p in self.profiles if not self._is_profile_noxious(p))
                    active_total = total_prompts * alive_profiles
                else:
                    active_total = total_iterations

                # Show progress header every 50 iterations
                run_index = len(self.results) + 1  # How many we have actually processed/completed
                if run_index % 50 == 1:
                    pct = (run_index / max(1, active_total)) * 100
                    best_score_val = best_result.adjusted_score if best_result else 0.0
                    logger.info("")
                    logger.info("┌" + "─" * 70 + "┐")
                    logger.info("│ 🔄 CALIBRATION PROGRESS: %d/%d activas (%.1f%%)".ljust(71) + "│", run_index, active_total, pct)
                    logger.info("│ 🏆 Best so far: score=%.3f".ljust(71) + "│", best_score_val)
                    logger.info("└" + "─" * 70 + "┘")
                    logger.info("")

                # Build effective grid FROM the actual profiles we're iterating.
                # This prevents a mismatch where the canonical CALIBRATION_GRID
                # contains values that are not present in `self.profiles`
                # (for example when a pre-filter reduced the profile set).
                params = [
                    "temperature",
                    "top_p",
                    "top_k",
                    "min_p",
                    "repetition_penalty",
                    "presence_penalty",
                ]

                # Collect values present in the generated profiles
                profile_values: dict[str, set[Any]] = {p: set() for p in params}
                for p in self.profiles:
                    profile_values["temperature"].add(p.temperature)
                    profile_values["top_p"].add(p.top_p)
                    profile_values["top_k"].add(p.top_k)
                    profile_values["min_p"].add(p.min_p)
                    profile_values["repetition_penalty"].add(p.repetition_penalty)
                    if p.presence_penalty is not None:
                        profile_values["presence_penalty"].add(p.presence_penalty)

                # Remove discarded values (if any) and sort for consistent display
                effective_grid: dict[str, list[Any]] = {}
                for param, vals in profile_values.items():
                    discarded = self._discarded_params.get(param, set())
                    remaining = [v for v in sorted(vals) if v not in discarded]
                    effective_grid[param] = remaining

                # Compact formatting for display and include simple counts for diagnostics
                grid_parts: list[str] = []
                for p, vals in effective_grid.items():
                    vals_str = ",".join(str(x) for x in vals)
                    grid_parts.append(f"{p}=[{vals_str}]")
                grid_str = " | ".join(grid_parts)

                # Diagnostic: counts per parameter value (short) at DEBUG level
                try:
                    diag_parts: list[str] = []
                    for p, vals in effective_grid.items():
                        # build simple count map from existing results to aid debugging
                        counts = {}
                        for v in vals:
                            counts[v] = sum(1 for r in self.results if getattr(r.profile, p) == v)
                        counts_str = ",".join(f"{k}:{counts[k]}" for k in counts)
                        diag_parts.append(f"{p}={{ {counts_str} }}")
                    logger.debug("Active-value counts: %s", " | ".join(diag_parts))
                except Exception:
                    logger.debug("Failed to compute active-value diagnostic counts", exc_info=True)

                logger.info(
                    "▶ [Efectivo %d/%d] %s @ %s",
                    run_index,
                    active_total,
                    prompt_short,
                    profile_short,
                )
                logger.info("    🔎 Active grid: %s", grid_str)

                try:
                    # Generate response with profile parameters
                    response_text = generate_response_with_profile(
                        client=self.student_client,
                        prompt=prompt_text,
                        profile=profile,
                        max_tokens=max_tokens,
                    )

                    response_length = count_words(response_text)

                    # Score with judge if available
                    judge_scores: dict[str, float] = {}
                    if self.judge_client:
                        # For calibration, we use the direct evaluation approach
                        # with parameter_target and evaluation_focus from the prompt
                        parameter_target = prompt.get("parameter_target", "")
                        evaluation_focus = prompt.get("evaluation_focus", "")
                        judge_scores = self._get_judge_scores(
                            prompt_text, response_text, prompt_id,
                            parameter_target, evaluation_focus
                        )

                    # Calculate composite score
                    composite_score = calculate_composite_score(judge_scores)

                    # Apply length penalty
                    adjusted_score = apply_length_penalty(
                        composite_score, response_length
                    )

                    # Create result
                    result = CalibrationResult(
                        profile=profile,
                        exam_id=prompt_id,
                        judge_scores=judge_scores,
                        composite_score=composite_score,
                        adjusted_score=adjusted_score,
                        response_length=response_length,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        response_text=response_text,
                    )

                    self.results.append(result)
                    self._completed_profiles.add((prompt_idx, profile_idx))

                    # Calculate best score so far (BEFORE updating best_result)
                    current_best = best_result.adjusted_score if best_result else 0.0
                    is_best = adjusted_score > current_best

                    # Update best result tracking
                    if best_result is None or adjusted_score > best_result.adjusted_score:
                        best_result = result

                    # Save checkpoint after each iteration
                    if self.checkpoint_dir:
                        self._save_checkpoint(prompt_idx, profile_idx)

                    # Show result with scores - ALWAYS show best so far
                    # Show full judge dimensions (not abbreviated)
                    if judge_scores:
                        judge_details = " | ".join(
                            "%s=%.2f" % (k, v) for k, v in judge_scores.items()
                        )
                    else:
                        judge_details = "no judge scores"

                    # Compare with previous iteration
                    diff = adjusted_score - previous_score
                    if diff > 0:
                        diff_marker = f"↑ +{diff:.3f}"
                    elif diff < 0:
                        diff_marker = f"↓ {diff:.3f}"
                    else:
                        diff_marker = "="
                    previous_score = adjusted_score

                    # Better formatted output with full details
                    logger.info(
                        "    📊 composite=%.3f adjusted=%.3f %s | %s | words=%d",
                        composite_score,
                        adjusted_score,
                        diff_marker,
                        judge_details,
                        response_length,
                    )

                    # Show why this score - parameter target from prompt
                    param_target = prompt.get("parameter_target", "")
                    eval_focus = prompt.get("evaluation_focus", "")
                    if param_target:
                        logger.info("    🎯 Target params: %s", param_target)
                    if eval_focus and len(eval_focus) < 100:
                        logger.info("    💡 Focus: %s", eval_focus[:100])

                    # Show why this score (if it's a new best)
                    if is_best and best_result:
                        best_profile = best_result.profile
                        logger.info(
                            "    🏆 NEW BEST! Profile: temperature=%s top_p=%s top_k=%s min_p=%s repetition_penalty=%s%s",
                            best_profile.temperature, best_profile.top_p, best_profile.top_k,
                            best_profile.min_p, best_profile.repetition_penalty,
                            " presence_penalty=%s" % best_profile.presence_penalty if best_profile.presence_penalty is not None else "",
                        )

                except Exception as e:
                    logger.error(
                        "Error on prompt %s with profile %s: %s",
                        prompt_id,
                        profile,
                        e,
                    )
                    # Continue with next profile
                    continue

            # After each prompt sweep, analyse accumulated scores and discard
            # noxious parameter values so the remaining profiles are skipped.
            if self._use_noxious_filter:
                self._update_discarded_params(self._noxious_loss_threshold)

        # Select best profile
        best_result = self._select_best_profile()

        # Build statistics
        statistics = self._compute_statistics()

        # Extract focus analysis from prompts if they contain parameter_target/evaluation_focus
        focus_analysis = extract_focus_analysis(self.prompts)

        report = CalibrationReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_iterations=len(self.results),
            best_profile=best_result.profile if best_result else self.profiles[0],
            best_score=best_result.adjusted_score if best_result else 0.0,
            all_results=self.results,
            statistics=statistics,
            prompt_count=total_prompts,
            focus_analysis=focus_analysis,
        )

        if verbose:
            logger.info(
                "Calibration complete. Best profile: %s (score=%.3f)",
                report.best_profile,
                report.best_score,
            )

        return report

    def _get_judge_scores(
        self,
        prompt: str,
        response: str,
        exam_id: str,
        parameter_target: str = "",
        evaluation_focus: str = "",
    ) -> dict[str, float]:
        """Get judge scores for a response using direct calibration evaluation.

        Uses the new professor_judge_calibration prompt that evaluates
        response quality directly without baseline comparison.

        Parameters
        ----------
        prompt : str
            The input prompt.
        response : str
            The generated response.
        exam_id : str
            Identifier for the evaluation.
        parameter_target : str
            The parameter target from calibration prompt (e.g., "temperature, top_k").
        evaluation_focus : str
            The evaluation focus from calibration prompt (what to evaluate).

        Returns
        -------
        dict[str, float]
            Judge scores for each dimension.
        """
        import json
        import re
        from src.audit.config import _get_prompt_manager

        try:
            # Get the prompt manager for calibration-specific prompts
            pm = _get_prompt_manager()

            # Use the new calibration-specific judge prompt
            user_msg = pm.format(
                "professor_judge_calibration",
                calibration_question=prompt,
                parameter_target=parameter_target or "general",
                evaluation_focus=evaluation_focus or "General response quality",
                model_response=response,
            )

            # Get the judge client
            client = self.judge_client

            # Call the judge for direct evaluation
            raw = client.generate_with_retry(
                prompt=user_msg,
                system_prompt=pm.system("professor_judge_calibration"),
                max_tokens=8192,
                temperature=0.0,  # Deterministic scoring
                retries=3,
                retry_delay=5.0,
                json_mode=True,
            )
            raw = raw.strip()

            # Clean markdown fences
            cleaned = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
            cleaned = re.sub(r"```\s*$", "", cleaned, flags=re.MULTILINE).strip()

            # Parse JSON response
            try:
                parsed = json.loads(cleaned)
            except json.JSONDecodeError as exc:
                logger.warning(
                    "Judge produced invalid JSON for %s: %s - raw: %s",
                    exam_id, exc, raw[:200]
                )
                return self._neutral_scores()

            # Map the new calibration dimensions to our standard format for composite score
            # These are specifically designed for parameter evaluation
            return {
                "parameter_effectiveness": parsed.get("parameter_effectiveness", 0.5),
                "task_completion": parsed.get("task_completion", 0.5),
                "parameter_alignment": parsed.get("parameter_alignment", 0.5),
                "coherence": parsed.get("coherence", 0.5),
                "style": parsed.get("style", 0.5),
            }

        except Exception as e:
            logger.warning(
                "Judge scoring failed for %s: %s - returning neutral scores",
                exam_id,
                e,
            )
            return self._neutral_scores()

    def _neutral_scores(self) -> dict[str, float]:
        """Return neutral scores for error cases."""
        return {
            "parameter_effectiveness": 0.5,
            "task_completion": 0.5,
            "parameter_alignment": 0.5,
            "coherence": 0.5,
            "style": 0.5,
        }

    def _is_profile_noxious(self, profile: "SamplingProfile") -> bool:
        """Return True if any of the profile's parameter values have been discarded.

        Checks ``self._discarded_params`` which is populated by
        ``_update_discarded_params`` after each prompt sweep.
        """
        if not self._discarded_params:
            return False

        # Map parameters to their values and collect triggers
        param_map: dict[str, Any] = {
            "temperature": profile.temperature,
            "top_p": profile.top_p,
            "top_k": profile.top_k,
            "min_p": profile.min_p,
            "repetition_penalty": profile.repetition_penalty,
            "presence_penalty": profile.presence_penalty,
        }

        triggers: list[str] = []
        for param, discarded_values in self._discarded_params.items():
            val = param_map.get(param)
            if val is not None and val in discarded_values:
                triggers.append(f"{param}={val}")

        if triggers:
            # Keep this at DEBUG level to avoid spamming the user's console during
            # large resumes; set logging to DEBUG to inspect triggers when needed.
            logger.debug("⏭ Skipping noxious profile -> triggers: %s", ", ".join(triggers))
            return True

        return False

    def _update_discarded_params(self, loss_threshold: float = 0.15) -> None:
        """Analyse accumulated results and discard consistently bad parameter values.

        Called after each prompt sweep.  For every tracked parameter, computes
        the average adjusted score per value.  Any value whose average is more
        than ``loss_threshold`` below the current best average for that parameter
        is added to ``self._discarded_params``, causing future profiles that
        contain it to be skipped via ``_is_profile_noxious``.

        Parameters
        ----------
        loss_threshold : float
            Minimum score gap to consider a value noxious (default 0.15).
        """
        if not self.results:
            return

        param_names = [
            "temperature", "top_p", "top_k",
            "min_p", "repetition_penalty", "presence_penalty",
        ]
        # Accumulate per-parameter-value scores from all results so far
        # {param: {value: [adjusted_scores]}}
        value_scores: dict[str, dict[Any, list[float]]] = {p: {} for p in param_names}
        for result in self.results:
            p = result.profile
            val_map: dict[str, Any] = {
                "temperature": p.temperature,
                "top_p": p.top_p,
                "top_k": p.top_k,
                "min_p": p.min_p,
                "repetition_penalty": p.repetition_penalty,
                "presence_penalty": p.presence_penalty,
            }
            for param_name, val in val_map.items():
                if val is None:
                    continue
                bucket = value_scores[param_name]
                if val not in bucket:
                    bucket[val] = []
                bucket[val].append(result.adjusted_score)

        newly_discarded = 0
        for param_name, buckets in value_scores.items():
            if len(buckets) < 2:
                # Not enough diversity to judge
                continue
            # Only consider values that have at least 5 samples to avoid noisy early eliminations
            valid_buckets = {v: s for v, s in buckets.items() if len(s) >= 5}
            if len(valid_buckets) < 2:
                continue
            
            avg_by_val = {v: sum(s) / len(s) for v, s in valid_buckets.items()}
            best_avg = max(avg_by_val.values())
            
            # Sort values from worst to best
            sorted_vals = sorted(avg_by_val.items(), key=lambda x: x[1])
            total_vals = len(sorted_vals)
            if total_vals < 2: continue
            
            # Algoritmo de supresion agresiva (Proporcional):
            # Eliminamos una fracción de los peores (controlada por
            # self._noxious_aggressiveness), siempre que la diferencia con el
            # mejor sea > 0.015 o si superan el threshold absoluto
            # (loss_threshold). Esto fuerza la reducción en resume.
            num_to_discard = max(1, int(total_vals * self._noxious_aggressiveness))
            
            for i, (val, avg) in enumerate(sorted_vals):
                is_already_discarded = val in self._discarded_params.get(param_name, set())
                if is_already_discarded:
                    continue
                    
                diff = best_avg - avg
                # Descartar si excede el threshold estricto, O si está entre los peores rankeados
                if diff > loss_threshold or (diff > 0.015 and i < num_to_discard):
                    self._discarded_params.setdefault(param_name, set()).add(val)
                    newly_discarded += 1
                    logger.info(
                        "🚫 Noxious filter agresivo: %s=%s descartado "
                        "(avg=%.4f vs best=%.4f, delta=%.4f, rank=%d/%d)",
                        param_name, val, avg, best_avg, diff, i+1, total_vals
                    )

            # Guardrail: never discard all candidate values for a parameter.
            # If aggressive rules would remove every candidate, restore the
            # best value so at least one remains available.
            candidate_vals = [v for v, _ in sorted_vals]
            discarded_in_candidates = [v for v in self._discarded_params.get(param_name, set()) if v in candidate_vals]
            if len(discarded_in_candidates) >= len(candidate_vals):
                # Determine best candidate by avg (if available) and keep it
                try:
                    best_val = max(avg_by_val.items(), key=lambda x: x[1])[0]
                    self._discarded_params[param_name].discard(best_val)
                    logger.info(
                        "⚠️ Guardrail: retenido %s=%s para evitar eliminar todas las opciones",
                        param_name,
                        best_val,
                    )
                except Exception:
                    # Fallback: clear all discards for this param (conservative)
                    self._discarded_params.pop(param_name, None)
                    logger.info(
                        "⚠️ Guardrail: no fue posible elegir mejor valor para %s, se restauran opciones",
                        param_name,
                    )

        if newly_discarded:
            skipped_count = sum(
                1 for prof in self.profiles if self._is_profile_noxious(prof)
            )
            logger.info(
                "🧹 %d value(s) newly discarded -> %d/%d profiles will be skipped going forward",
                newly_discarded, skipped_count, len(self.profiles),
            )

    def _derive_discards_from_noxious_checkpoint(
        self,
        checkpoint_dir: str,
        loss_threshold: float,
    ) -> None:
        """Populate ``_discarded_params`` from the noxious pre-filter checkpoint.

        Reads ``noxious_filter_checkpoint.json`` from *checkpoint_dir* and
        applies the same average-delta criterion as ``_update_discarded_params``
        to identify parameter values whose average score is significantly below
        the best average for their parameter.

        This is **critical for ``--resume`` flows**: the pre-filter data (6+
        prompts × all values) provides far richer signal than the handful of
        calibration results accumulated so far, so noxious profiles can be
        skipped from the very first new iteration.

        Parameters
        ----------
        checkpoint_dir : str
            Directory that may contain ``noxious_filter_checkpoint.json``.
        loss_threshold : float
            Delta between the best per-parameter average and a value's average
            above which the value is considered noxious and discarded.
        """
        # Strategy: aggregate all available historic data from the
        # checkpoint directory (latest.json + checkpoint_*.json files)
        # and also apply the dedicated noxious pre-filter if present.
        # This ensures resume uses ALL past evaluations (not just a single
        # latest file) to derive which parameter *values* are bad.

        aggregated_results: list[dict[str, Any]] = []

        # 1) Load latest.json if present
        latest_path = os.path.join(checkpoint_dir, "latest.json")
        if os.path.isfile(latest_path):
            try:
                with open(latest_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    aggregated_results.extend(data.get("all_results", []))
            except Exception:
                logger.debug("Could not read latest.json for aggregation", exc_info=True)

        # 2) Load any checkpoint_*.json files (these may be incremental)
        try:
            for fname in os.listdir(checkpoint_dir):
                if not fname.startswith("checkpoint_") or not fname.endswith(".json"):
                    continue
                full = os.path.join(checkpoint_dir, fname)
                try:
                    with open(full, "r", encoding="utf-8") as f:
                        ck = json.load(f)
                        aggregated_results.extend(ck.get("all_results", []))
                except Exception:
                    logger.debug("Failed reading %s for aggregation", full, exc_info=True)
        except OSError:
            # directory may not exist or be readable
            logger.debug("Checkpoint directory not readable: %s", checkpoint_dir, exc_info=True)

        # 3) Optionally use the specialized noxious filter checkpoint for
        #     stronger per-value per-prompt signal (it contains 'prompt_data').
        checkpoint_file = os.path.join(checkpoint_dir, "noxious_filter_checkpoint.json")
        if os.path.isfile(checkpoint_file):
            try:
                with open(checkpoint_file, "r", encoding="utf-8") as f:
                    nf = json.load(f)
            except Exception:
                nf = None
                logger.debug("Failed to load noxious_filter_checkpoint.json", exc_info=True)

            if nf:
                prompt_data: dict[str, Any] = nf.get("prompt_data", {})
                newly_discarded_pf = 0
                for param, prompts in prompt_data.items():
                    pivot_val: Any = PARAMETER_PIVOTS.get(param)
                    collected: dict[Any, list[float]] = {}
                    for _prompt_key, pdict in prompts.items():
                        pivot_score = pdict.get("pivot_score")
                        if pivot_score is not None and pivot_val is not None:
                            collected.setdefault(pivot_val, []).append(float(pivot_score))
                        for key, score in pdict.items():
                            if key == "pivot_score":
                                continue
                            try:
                                v_float = float(key)
                                v: Any = (
                                    int(v_float)
                                    if v_float == int(v_float) and "." not in key
                                    else v_float
                                )
                            except (ValueError, TypeError):
                                v = key
                            collected.setdefault(v, []).append(float(score))

                    if len(collected) < 2:
                        continue

                    avg_by_val = {v: sum(lst) / len(lst) for v, lst in collected.items() if lst}
                    if not avg_by_val:
                        continue
                    best_avg = max(avg_by_val.values())
                    for val, avg in avg_by_val.items():
                        if val == pivot_val:
                            continue
                        if best_avg - avg > loss_threshold:
                            if val not in self._discarded_params.get(param, set()):
                                self._discarded_params.setdefault(param, set()).add(val)
                                newly_discarded_pf += 1
                                logger.info(
                                    "🚫 Pre-filter derived discard: %s=%s "
                                    "(avg=%.3f vs best=%.3f, delta=%.3f > threshold=%.3f)",
                                    param,
                                    val,
                                    avg,
                                    best_avg,
                                    best_avg - avg,
                                    loss_threshold,
                                )

                if newly_discarded_pf:
                    skipped = sum(1 for p in self.profiles if self._is_profile_noxious(p))
                    logger.info(
                        "🧹 Pre-filter checkpoint: %d value(s) derived -> %d/%d profiles will be skipped from now on",
                        newly_discarded_pf,
                        skipped,
                        len(self.profiles),
                    )

        # 4) If we have aggregated historic results, run a proportional
        #    discard pass over them so resume learns from *all* past runs.
        if aggregated_results:
            param_names = [
                "temperature",
                "top_p",
                "top_k",
                "min_p",
                "repetition_penalty",
                "presence_penalty",
            ]

            value_scores: dict[str, dict[Any, list[float]]] = {p: {} for p in param_names}
            for r in aggregated_results:
                # Support both dict-based results (from checkpoint) and objects
                # If object-like, attempt attribute access defensively.
                try:
                    prof = r.get("profile", {}) if isinstance(r, dict) else getattr(r, "profile", {})
                except Exception:
                    prof = {}
                score = 0.0
                if isinstance(r, dict):
                    score = r.get("adjusted_score", r.get("composite_score", 0.0))
                else:
                    score = getattr(r, "adjusted_score", getattr(r, "composite_score", 0.0))

                for param in param_names:
                    val = None
                    if isinstance(prof, dict):
                        val = prof.get(param)
                    else:
                        val = getattr(prof, param, None)
                    if val is None:
                        continue
                    bucket = value_scores[param]
                    bucket.setdefault(val, []).append(float(score))

            newly_discarded = 0
            for param_name, buckets in value_scores.items():
                valid_buckets = {v: s for v, s in buckets.items() if len(s) >= 2}
                if len(valid_buckets) < 2:
                    continue
                avg_by_val = {v: sum(s) / len(s) for v, s in valid_buckets.items()}
                best_avg = max(avg_by_val.values())
                sorted_vals = sorted(avg_by_val.items(), key=lambda x: x[1])
                total_vals = len(sorted_vals)
                num_to_discard = max(1, int(total_vals * self._noxious_aggressiveness))
                for i, (val, avg) in enumerate(sorted_vals):
                    if val in self._discarded_params.get(param_name, set()):
                        continue
                    diff = best_avg - avg
                    if diff > loss_threshold or (diff > 0.015 and i < num_to_discard):
                        self._discarded_params.setdefault(param_name, set()).add(val)
                        newly_discarded += 1
                        logger.info(
                            "🧹 Pre-resume aggregate discard: %s=%s discarded (avg=%.4f vs best=%.4f, delta=%.4f, rank=%d/%d)",
                            param_name, val, avg, best_avg, diff, i + 1, total_vals,
                        )

                # Guardrail: ensure we do not discard every candidate for a param
                candidate_vals = [v for v, _ in sorted_vals]
                discarded_in_candidates = [v for v in self._discarded_params.get(param_name, set()) if v in candidate_vals]
                if len(discarded_in_candidates) >= len(candidate_vals):
                    try:
                        best_val = max(avg_by_val.items(), key=lambda x: x[1])[0]
                        self._discarded_params[param_name].discard(best_val)
                        logger.info(
                            "⚠️ Guardrail pre-resume: retenido %s=%s para evitar eliminar todas las opciones",
                            param_name,
                            best_val,
                        )
                    except Exception:
                        self._discarded_params.pop(param_name, None)
                        logger.info(
                            "⚠️ Guardrail pre-resume: no fue posible elegir mejor valor para %s, se restauran opciones",
                            param_name,
                        )

            if newly_discarded:
                skipped = sum(1 for p in self.profiles if self._is_profile_noxious(p))
                logger.info(
                    "🧹 Pre-resume aggregate: %d value(s) derived -> %d/%d profiles will be skipped from now on",
                    newly_discarded,
                    skipped,
                    len(self.profiles),
                )

    def _select_best_profile(self) -> CalibrationResult | None:
        """Select the best profile based on adjusted scores.

        Returns
        -------
        CalibrationResult | None
            Result with highest adjusted score, or None if no results.
        """
        if not self.results:
            return None

        return max(self.results, key=lambda r: r.adjusted_score)

    def _compute_statistics(self) -> dict[str, Any]:
        """Compute statistics from calibration results.

        Returns
        -------
        dict[str, Any]
            Statistical summary of calibration results.
        """
        if not self.results:
            return {}

        scores = [r.adjusted_score for r in self.results]
        lengths = [r.response_length for r in self.results]

        return {
            "mean_score": sum(scores) / len(scores),
            "min_score": min(scores),
            "max_score": max(scores),
            "mean_length": sum(lengths) / len(lengths),
            "min_length": min(lengths),
            "max_length": max(lengths),
            "total_results": len(self.results),
        }

    def _save_checkpoint(
        self,
        current_prompt_idx: int,
        current_profile_idx: int,
    ) -> None:
        """Save checkpoint after each iteration for resume capability.

        Parameters
        ----------
        current_prompt_idx : int
            Index of the current prompt being processed.
        current_profile_idx : int
            Index of the current profile being processed.
        """
        import hashlib

        os.makedirs(self.checkpoint_dir, exist_ok=True)

        # Create checkpoint
        checkpoint = CalibrationCheckpoint(
            timestamp=datetime.now(timezone.utc).isoformat(),
            current_prompt_idx=current_prompt_idx,
            current_profile_idx=current_profile_idx,
            completed_profiles=list(self._completed_profiles),
            all_results=self.results.copy(),
            total_profiles=len(self.profiles),
            total_prompts=len(self.prompts),
            discarded_params={k: list(v) for k, v in self._discarded_params.items()},
        )

        # Generate filename based on prompt and profile for easy lookup
        # Use hash to keep filename manageable
        prompt_hash = hashlib.md5(str(current_prompt_idx).encode()).hexdigest()[:8]
        profile_hash = hashlib.md5(str(current_profile_idx).encode()).hexdigest()[:8]
        checkpoint_filename = f"checkpoint_{prompt_hash}_{profile_hash}.json"
        checkpoint_path = os.path.join(self.checkpoint_dir, checkpoint_filename)

        with open(checkpoint_path, "w", encoding="utf-8") as f:
            json.dump(checkpoint.to_dict(), f, indent=2, ensure_ascii=False)

        # Also save latest checkpoint as 'latest.json' for easy recovery
        latest_path = os.path.join(self.checkpoint_dir, "latest.json")
        with open(latest_path, "w", encoding="utf-8") as f:
            json.dump(checkpoint.to_dict(), f, indent=2, ensure_ascii=False)

        logger.debug("Saved checkpoint to %s", checkpoint_path)

    def _load_checkpoint(self, checkpoint_dir: str) -> CalibrationCheckpoint | None:
        """Load checkpoint from directory to resume previous run.

        Parameters
        ----------
        checkpoint_dir : str
            Directory containing checkpoint files.

        Returns
        -------
        CalibrationCheckpoint | None
            Loaded checkpoint if exists and valid, None otherwise.
        """
        if not os.path.isdir(checkpoint_dir):
            return None

        latest_path = os.path.join(checkpoint_dir, "latest.json")
        if not os.path.isfile(latest_path):
            return None

        try:
            with open(latest_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            checkpoint = CalibrationCheckpoint.from_dict(data)

            # Validate checkpoint matches current configuration
            if checkpoint.total_prompts != len(self.prompts):
                logger.warning(
                    "Checkpoint prompt count mismatch: %d vs %d - cannot resume",
                    checkpoint.total_prompts,
                    len(self.prompts),
                )
                return None

            if checkpoint.total_profiles != len(self.profiles):
                logger.warning(
                    "Checkpoint profile count mismatch: %d vs %d - cannot resume",
                    checkpoint.total_profiles,
                    len(self.profiles),
                )
                return None

            logger.info("Loaded checkpoint from %s", latest_path)
            return checkpoint

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning("Failed to load checkpoint from %s: %s", latest_path, e)
            return None


# ======================================================================
# Convenience Functions
# ======================================================================


# Pivot values for quick filter - these are the "safe" defaults
PARAMETER_PIVOTS: dict[str, Any] = {
    "temperature": 0.6,
    "top_p": 0.9,
    "top_k": 20,
    "min_p": 0.0,
    "repetition_penalty": 1.0,
    "presence_penalty": 1.0,
}


def filter_noxious_parameter_values(
    grid: dict[str, list[Any]],
    prompts: list[dict[str, str]],
    student_client: Any,
    judge_client: Any,
    loss_threshold: float = 0.15,
    sample_size: int | None = None,
    verbose: bool = True,
    checkpoint_dir: str | None = None,
) -> dict[str, list[Any]]:
    """Filter out noxious parameter values using quick evaluation.

    This function evaluates each parameter value individually (with other params at pivot)
    to identify values that consistently perform worse than the pivot. Values that lose
    by more than loss_threshold are discarded.

    Algorithm:
    1. For each parameter, create test profiles varying only that parameter
    2. Compare each value vs pivot across all prompts
    3. If value loses in >80% of cases by >loss_threshold, discard it
    4. Return reduced grid

    Supports checkpointing: if checkpoint_dir is provided, saves progress after each
    parameter evaluation and resumes from checkpoint if available.

    Parameters
    ----------
    grid : dict[str, list[Any]]
        Full parameter grid to filter.
    prompts : list[dict[str, str]]
        Prompts to evaluate.
    student_client : Any
        Inference client for student model.
    judge_client : Any
        Inference client for judge model.
    loss_threshold : float
        Minimum score difference to consider a value as "losing" (default: 0.15).
    verbose : bool
        Whether to log progress.
    checkpoint_dir : str | None
        Directory to save checkpoint for resume capability.

    Returns
    -------
    dict[str, list[Any]]
        Filtered grid with noxious values removed.
    """
    from src.audit.config import _get_prompt_manager

    import json
    import re
    import random

    filtered_grid: dict[str, list[Any]] = {}
    pivot_values = PARAMETER_PIVOTS

    # Get prompt manager for judge prompts
    pm = _get_prompt_manager()

    # Checkpoint handling for noxious filter
    checkpoint_data: dict[str, Any] = {}
    checkpoint_file = None
    if checkpoint_dir:
        os.makedirs(checkpoint_dir, exist_ok=True)
        checkpoint_file = os.path.join(checkpoint_dir, "noxious_filter_checkpoint.json")
        if os.path.exists(checkpoint_file):
            try:
                with open(checkpoint_file, "r") as f:
                    checkpoint_data = json.load(f)
                if verbose:
                    logger.info("🔄 Resuming noxious filter from checkpoint...")
                    for param, data in checkpoint_data.get("param_scores", {}).items():
                        scored_count = sum(len(v) for v in data.values()) if data else 0
                        logger.info("   %s: %d scores loaded", param, scored_count)
            except Exception as e:
                if verbose:
                    logger.warning("Failed to load checkpoint: %s", e)
                checkpoint_data = {}

    def save_noxious_checkpoint():
        """Save current noxious filter progress to checkpoint."""
        if checkpoint_file and checkpoint_data:
            try:
                with open(checkpoint_file, "w") as f:
                    json.dump(checkpoint_data, f)
            except Exception as e:
                if verbose:
                    logger.warning("Failed to save checkpoint: %s", e)

    def get_judge_score(prompt_text: str, response: str, prompt_meta: dict) -> float:
        """Get judge score for a response using the judge client."""
        parameter_target = prompt_meta.get("parameter_target", "")
        evaluation_focus = prompt_meta.get("evaluation_focus", "General response quality")
        
        try:
            user_msg = pm.format(
                "professor_judge_calibration",
                calibration_question=prompt_text,
                parameter_target=parameter_target or "general",
                evaluation_focus=evaluation_focus or "General response quality",
                model_response=response,
            )
            
            raw = judge_client.generate_with_retry(
                prompt=user_msg,
                system_prompt=pm.system("professor_judge_calibration"),
                max_tokens=8192,
                temperature=0.0,
                retries=3,
                retry_delay=5.0,
                json_mode=True,
            )
            
            # Clean and parse JSON
            cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
            cleaned = re.sub(r"```\s*$", "", cleaned, flags=re.MULTILINE).strip()
            parsed = json.loads(cleaned)
            
            # Calculate composite score from judge dimensions
            weights = {
                "parameter_effectiveness": 0.2,
                "task_completion": 0.25,
                "parameter_alignment": 0.2,
                "coherence": 0.2,
                "style": 0.15,
            }
            composite = sum(
                parsed.get(dim, 0.5) * weight 
                for dim, weight in weights.items()
            )
            return composite
        except Exception as e:
            logger.debug("Judge scoring failed: %s", e)
            return 0.5  # Neutral score on failure

    if verbose:
        original_combos = 1
        for values in grid.values():
            original_combos *= len(values)
        logger.info("")
        logger.info("=" * 60)
        logger.info("🚀 NOXIOUS PARAMETER FILTER (with Judge)")
        logger.info("=" * 60)
        logger.info("  Original grid: %d combinations", original_combos)
        logger.info("  Prompts to test: %d", len(prompts))
        if sample_size and sample_size > 0 and sample_size < len(prompts):
            logger.info("  Sampling %d/%d prompts for pre-filter (faster)", sample_size, len(prompts))
        logger.info("  Loss threshold: %s", loss_threshold)
        logger.info("  Using real judge for scoring")
        logger.info("")

    for param_name, param_values in grid.items():
        if param_name not in pivot_values:
            filtered_grid[param_name] = param_values
            continue

        pivot = pivot_values[param_name]
        if pivot not in param_values:
            # Pivot not in grid, use first value as pivot
            pivot = param_values[len(param_values) // 2]
            if verbose:
                logger.warning("  ⚠️  Pivot %s not in grid for %s, using %s", pivot, param_name, pivot)

        if verbose:
            logger.info("")
            logger.info("  📊 Testing parameter: %s", param_name)
            logger.info("     Values: %s", param_values)
            logger.info("     Pivot: %s", pivot)

        # Test each value vs pivot - load from checkpoint if available
        value_scores: dict[Any, list[float]] = {v: [] for v in param_values}

        # Calculate total iterations for this parameter for progress display
        _noxious_total = len(prompts) * len(param_values)
        _noxious_done = 0

        # Load from checkpoint if available
        param_checkpoint = checkpoint_data.get("param_scores", {}).get(param_name, {})
        if param_checkpoint and verbose:
            logger.info("     📂 Loaded %d scores from checkpoint", sum(len(v) for v in param_checkpoint.values()))
        
        # Convert checkpoint data to value_scores format
        # JSON keys are always str, so match against str(v) for numeric values
        for ckpt_key, prompt_scores in param_checkpoint.items():
            for v in param_values:
                if str(v) == ckpt_key:
                    value_scores[v] = prompt_scores
                    break

        # Determine which prompt indices to evaluate (supports sampling)
        prompt_indices = list(range(len(prompts)))
        if sample_size and sample_size > 0 and sample_size < len(prompts):
            prompt_indices = random.sample(prompt_indices, sample_size)

        for prompt_idx in prompt_indices:
            prompt = prompts[prompt_idx]
            # Get prompt text and ID
            prompt_id = prompt.get("id", f"prompt_{prompt_idx}")
            prompt_text = prompt.get("question", prompt.get("text", prompt.get("prompt", "")))
            if not prompt_text:
                continue

            # Check if this prompt was already evaluated for all values in checkpoint
            prompt_key = f"prompt_{prompt_idx}"
            param_prompt_data = checkpoint_data.get("prompt_data", {}).get(param_name, {}).get(prompt_key, {})
            
            # Load pivot score from checkpoint if available
            if "pivot_score" in param_prompt_data:
                pivot_score = param_prompt_data["pivot_score"]
                if verbose:
                    logger.info(
                        "     [P%d/%d] %-20s pivot=%-5s → score=%.3f  (cached)",
                        prompt_idx + 1, len(prompts), prompt_id, pivot, pivot_score,
                    )
            else:
                # Generate with pivot profile
                if verbose:
                    logger.info(
                        "     [P%d/%d] %-20s pivot=%-5s → generating...",
                        prompt_idx + 1, len(prompts), prompt_id, pivot,
                    )
                pivot_profile = SamplingProfile(
                    temperature=pivot_values.get("temperature", 0.6),
                    top_p=pivot_values.get("top_p", 0.9),
                    top_k=pivot_values.get("top_k", 20),
                    min_p=pivot_values.get("min_p", 0.0),
                    repetition_penalty=pivot_values.get("repetition_penalty", 1.0),
                    presence_penalty=pivot_values.get("presence_penalty"),
                )

                try:
                    pivot_response = generate_response_with_profile(
                        client=student_client,
                        prompt=prompt_text,
                        profile=pivot_profile,
                    )
                    # Use judge for real quality assessment
                    pivot_score = get_judge_score(prompt_text, pivot_response, prompt)
                except Exception:
                    pivot_score = 0.5

                if verbose:
                    logger.info(
                        "     [P%d/%d] %-20s pivot=%-5s → score=%.3f",
                        prompt_idx + 1, len(prompts), prompt_id, pivot, pivot_score,
                    )

                # Save to checkpoint
                if checkpoint_dir:
                    if "prompt_data" not in checkpoint_data:
                        checkpoint_data["prompt_data"] = {}
                    if param_name not in checkpoint_data["prompt_data"]:
                        checkpoint_data["prompt_data"][param_name] = {}
                    checkpoint_data["prompt_data"][param_name][prompt_key] = {"pivot_score": pivot_score}
                    save_noxious_checkpoint()

            # Test each value of this parameter
            for value in param_values:
                _noxious_done += 1
                _pct = _noxious_done * 100 / _noxious_total if _noxious_total else 0

                if value == pivot:
                    if len(value_scores[value]) <= prompt_idx:
                        value_scores[value].append(pivot_score)
                    continue

                # Check if this value was already evaluated for this prompt
                value_key = str(value)
                if value_key in param_prompt_data:
                    test_score = param_prompt_data[value_key]
                    if len(value_scores[value]) <= prompt_idx:
                        value_scores[value].append(test_score)
                    if verbose:
                        logger.info(
                            "     [%5.1f%%] %s=%-5s  P%d  score=%.3f  (cached)",
                            _pct, param_name, value, prompt_idx + 1, test_score,
                        )
                    continue

                # Create profile with this value
                test_profile_dict = dict(pivot_values)
                test_profile_dict[param_name] = value

                if verbose:
                    logger.info(
                        "     [%5.1f%%] %s=%-5s  P%d  generating...",
                        _pct, param_name, value, prompt_idx + 1,
                    )

                try:
                    test_profile = SamplingProfile(
                        temperature=test_profile_dict.get("temperature", 0.6),
                        top_p=test_profile_dict.get("top_p", 0.9),
                        top_k=test_profile_dict.get("top_k", 20),
                        min_p=test_profile_dict.get("min_p", 0.0),
                        repetition_penalty=test_profile_dict.get("repetition_penalty", 1.0),
                        presence_penalty=test_profile_dict.get("presence_penalty"),
                    )
                    test_response = generate_response_with_profile(
                        client=student_client,
                        prompt=prompt_text,
                        profile=test_profile,
                    )
                    # Use judge for real quality assessment
                    test_score = get_judge_score(prompt_text, test_response, prompt)
                except Exception:
                    test_score = 0.5

                if verbose:
                    logger.info(
                        "     [%5.1f%%] %s=%-5s  P%d  score=%.3f",
                        _pct, param_name, value, prompt_idx + 1, test_score,
                    )

                # Save to checkpoint
                if checkpoint_dir:
                    if "prompt_data" not in checkpoint_data:
                        checkpoint_data["prompt_data"] = {}
                    if param_name not in checkpoint_data["prompt_data"]:
                        checkpoint_data["prompt_data"][param_name] = {}
                    if prompt_key not in checkpoint_data["prompt_data"][param_name]:
                        checkpoint_data["prompt_data"][param_name][prompt_key] = {"pivot_score": pivot_score}
                    checkpoint_data["prompt_data"][param_name][prompt_key][value_key] = test_score
                    save_noxious_checkpoint()

                if len(value_scores[value]) <= prompt_idx:
                    value_scores[value].append(test_score)

        # Analyze results: count how often each value loses to pivot
        good_values = [pivot]
        for value, scores in value_scores.items():
            if value == pivot:
                continue

            if not scores or not value_scores[pivot]:
                # No data, keep value
                good_values.append(value)
                continue

            pivot_avg = sum(value_scores[pivot]) / len(value_scores[pivot])
            value_avg = sum(scores) / len(scores)

            # Count how many times value lost to pivot
            losses = 0
            for i in range(min(len(scores), len(value_scores[pivot]))):
                if value_scores[pivot][i] - scores[i] > loss_threshold:
                    losses += 1

            loss_rate = losses / min(len(scores), len(value_scores[pivot])) if scores else 0

            # Discard if loses >80% of the time
            if loss_rate > 0.8:
                if verbose:
                    # Calculate current combinations
                    current_combos = len(good_values)
                    for p_name, p_vals in filtered_grid.items():
                        if p_name == param_name:
                            current_combos *= len(good_values)
                            break
                        else:
                            current_combos *= len(p_vals)
                    logger.info(
                        "  ❌ NOXIOUS: %s=%s - loss_rate=%.0f%% (avg: value=%.3f vs pivot=%.3f)",
                        param_name, value, loss_rate * 100, value_avg, pivot_avg,
                    )
            else:
                good_values.append(value)

        filtered_grid[param_name] = good_values

    if verbose:
        total_combinations = 1
        for values in filtered_grid.values():
            total_combinations *= len(values)
        original = _calc_combinations(grid)
        reduction = ((original - total_combinations) / original) * 100 if original > 0 else 0

        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ NOXIOUS FILTER COMPLETE")
        logger.info("=" * 60)
        logger.info("  Original grid: %d combinations", original)
        logger.info("  Filtered grid: %d combinations", total_combinations)
        logger.info("  Reduction: %.1f%%", reduction)
        logger.info("")
        logger.info("  Final parameter values:")
        for param, values in filtered_grid.items():
            logger.info("    %s: %s", param, values)
        logger.info("=" * 60)
        logger.info("")

    return filtered_grid


def _calc_combinations(grid: dict[str, list[Any]]) -> int:
    """Calculate total combinations in a grid."""
    result = 1
    for values in grid.values():
        result *= len(values)
    return result


def run_calibration(
    prompts: list[dict[str, str]],
    output_dir: str | None = None,
    grid: dict[str, list[Any]] | None = None,
    student_client: Any | None = None,
    judge_client: Any | None = None,
    verbose: bool = True,
    checkpoint_dir: str | None = None,
    use_prompt_metadata: bool = False,
    use_noxious_filter: bool = False,
    noxious_loss_threshold: float = 0.15,
    noxious_sample_size: int | None = None,
    noxious_aggressiveness: float = 0.5,
) -> CalibrationReport:
    """Run calibration with the given prompts.

    This is a convenience function that creates an engine and runs calibration.

    Parameters
    ----------
    prompts : list[dict[str, str]]
        List of prompts to evaluate.
    output_dir : str | None
        Directory to save results (optional).
    grid : dict[str, list[Any]] | None
        Parameter grid to use.
    student_client : Any | None
        Inference client for student model.
    judge_client : Any | None
        Inference client for judge model.
    verbose : bool
        Whether to log progress.
    checkpoint_dir : str | None
        Directory to save checkpoints for resume capability.
    use_prompt_metadata : bool
        Enable intelligent calibration using parameter_target and evaluation_focus
        from prompts. When True, uses adaptive profile generation that prioritizes
        parameter combinations based on the evaluation focus. (default: False)
    use_noxious_filter : bool
        Enable noxious parameter filter to quickly identify and remove values that
        consistently perform worse than the pivot. This runs a quick evaluation of
        each parameter value individually before the full grid search, dramatically
        reducing iterations for large grids. (default: False)

    Returns
    -------
    CalibrationReport
        Complete calibration results.
    """
    # Resolve effective grid, applying static noxious pre-filter when requested.
    # This eliminates obviously bad parameter values BEFORE generating the full
    # profile list, which dramatically reduces iterations for large grids.
    # CalibrationEngine.run() additionally applies a dynamic mid-run filter
    # (updating _discarded_params after each prompt sweep).
    effective_grid: dict[str, list[Any]] = (
        dict(grid) if grid is not None else dict(CALIBRATION_GRID)
    )
    if use_noxious_filter and student_client is not None and judge_client is not None:
        if verbose:
            logger.info(
                "Running noxious pre-filter on grid (%d combinations) ...",
                _calc_combinations(effective_grid),
            )
        effective_grid = filter_noxious_parameter_values(
            grid=effective_grid,
            prompts=prompts,
            student_client=student_client,
            judge_client=judge_client,
            loss_threshold=noxious_loss_threshold,
            sample_size=(noxious_sample_size if noxious_sample_size and noxious_sample_size > 0 else None),
            checkpoint_dir=checkpoint_dir,
            verbose=verbose,
        )

    # Generate profiles - use adaptive generation if prompt metadata is enabled
    if use_prompt_metadata:
        # Convert prompts to CalibrationPrompt for adaptive profile generation
        calibration_prompts: list[CalibrationPrompt] = []
        for prompt in prompts:
            # Check if prompt has focus-related fields
            param_target = prompt.get("parameter_target")
            eval_focus = prompt.get("evaluation_focus")

            has_focus = False
            if param_target is not None:
                if isinstance(param_target, str):
                    has_focus = bool(param_target.strip())
                elif isinstance(param_target, list):
                    has_focus = len(param_target) > 0

            if eval_focus is not None and isinstance(eval_focus, str):
                has_focus = has_focus or bool(eval_focus.strip())

            if has_focus:
                cal_prompt_dict = {
                    "id": prompt.get("id", "unknown"),
                    "question": prompt.get("question", prompt.get("text", prompt.get("prompt", ""))),
                    "type": prompt.get("type", "investigation"),
                    "parameter_target": param_target,
                    "evaluation_focus": eval_focus,
                }
                calibration_prompts.append(CalibrationPrompt.from_dict(cal_prompt_dict))

        if calibration_prompts:
            if verbose:
                logger.info(
                    "Using adaptive profile generation with %d prompts having focus metadata",
                    len(calibration_prompts),
                )
            profiles = generate_adaptive_profiles(prompts=calibration_prompts, grid=effective_grid)
        else:
            if verbose:
                logger.info(
                    "No prompt metadata found, using standard profile generation"
                )
            profiles = generate_profiles(effective_grid)
    else:
        profiles = generate_profiles(effective_grid)

    engine = CalibrationEngine(
        prompts=prompts,
        profiles=profiles,
        student_client=student_client,
        judge_client=judge_client,
        checkpoint_dir=checkpoint_dir,
        use_noxious_filter=use_noxious_filter,
        noxious_loss_threshold=noxious_loss_threshold,
        noxious_aggressiveness=noxious_aggressiveness,
    )

    report = engine.run(verbose=verbose, checkpoint_dir=checkpoint_dir)

    # Save outputs if directory specified
    if output_dir:
        save_calibration_outputs(report, output_dir, prompts=prompts)

    return report


def generate_calibration_analysis(
    prompts: list[dict[str, Any]],
    report: CalibrationReport,
) -> dict[str, Any]:
    """Generate calibration analysis with parameter adjustment recommendations.

    Creates a comprehensive analysis document containing:
    - Focus analysis extracted from prompts
    - Parameter performance rankings
    - Adjustment recommendations based on evaluation_focus
    - Best profile recommendations with rationale

    Parameters
    ----------
    prompts : list[dict[str, Any]]
        List of prompts used in calibration.
    report : CalibrationReport
        The calibration results containing all profiles tested.

    Returns
    -------
    dict[str, Any]
        Dictionary containing the complete calibration analysis with
        parameter adjustment recommendations.
    """
    # Extract focus analysis from prompts
    focus_analysis = extract_focus_analysis(prompts)

    # Get refinement recommendations
    # Get the original grid from report statistics if available
    base_grid = report.statistics.get("grid") if report.statistics else None
    refinement_recs = get_refinement_recommendations(
        report.all_results,
        base_grid,
    )

    # Analyze parameter performance from results (for the analysis report)
    param_performance = analyze_parameter_performance(report.all_results)

    # Build comprehensive analysis
    analysis = {
        "timestamp": report.timestamp,
        "total_iterations": report.total_iterations,
        "has_focus_data": focus_analysis.get("has_focus_data", False),
        "focus_analysis": {
            "focused_parameters": focus_analysis.get("focused_parameters", []),
            "evaluation_foci": focus_analysis.get("evaluation_foci", []),
            "adjustment_strategy": focus_analysis.get("adjustment_strategy", {}),
            "prompts_with_focus": focus_analysis.get("prompts_with_focus", 0),
            "focus_distribution": focus_analysis.get("focus_distribution", {}),
        },
        "parameter_performance": param_performance,
        "best_profile": {
            "temperature": report.best_profile.temperature,
            "top_k": report.best_profile.top_k,
            "min_p": report.best_profile.min_p,
            "repetition_penalty": report.best_profile.repetition_penalty,
            "presence_penalty": report.best_profile.presence_penalty,
        },
        "refinement_recommendations": refinement_recs,
        "statistics": report.statistics,
    }

    # Add parameter adjustments if focus data was available
    if "parameter_adjustments" in focus_analysis:
        analysis["parameter_adjustments"] = focus_analysis["parameter_adjustments"]

    return analysis


def save_calibration_analysis(
    prompts: list[dict[str, Any]],
    report: CalibrationReport,
    output_dir: str,
) -> None:
    """Save calibration analysis JSON with parameter adjustment recommendations.

    Parameters
    ----------
    prompts : list[dict[str, Any]]
        List of prompts used in calibration.
    report : CalibrationReport
        The calibration results.
    output_dir : str
        Directory to save the analysis file.
    """
    os.makedirs(output_dir, exist_ok=True)

    analysis = generate_calibration_analysis(prompts, report)

    analysis_path = os.path.join(output_dir, "calibration_analysis.json")
    with open(analysis_path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    logger.info("Saved calibration analysis to %s", analysis_path)


def save_calibration_outputs(
    report: CalibrationReport,
    output_dir: str,
    prompts: list[dict[str, Any]] | None = None,
) -> None:
    """Save calibration report and vLLM config to files.

    Parameters
    ----------
    report : CalibrationReport
        Calibration results to save.
    output_dir : str
        Directory to save files in.
    prompts : list[dict[str, Any]] | None
        Optional list of prompts for generating calibration analysis.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Save calibration report JSON
    report_path = os.path.join(output_dir, "calibration_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
    logger.info("Saved calibration report to %s", report_path)

    # Save vLLM config YAML
    config_path = os.path.join(output_dir, "vllm_config.yaml")
    save_vllm_config(report.best_profile, config_path)
    logger.info("Saved vLLM config to %s", config_path)

    # Save calibration analysis JSON with parameter adjustment recommendations
    if prompts is not None:
        save_calibration_analysis(prompts, report, output_dir)


def save_vllm_config(profile: SamplingProfile, output_path: str) -> None:
    """Save vLLM configuration as YAML.

    Parameters
    ----------
    profile : SamplingProfile
        Best sampling profile to save.
    output_path : str
        Path to save YAML config.
    """
    import yaml

    config = {
        "sampling_params": {
            "temperature": profile.temperature,
            "top_k": profile.top_k,
            "min_p": profile.min_p,
            "repetition_penalty": profile.repetition_penalty,
        }
    }

    if profile.presence_penalty is not None:
        config["sampling_params"]["presence_penalty"] = profile.presence_penalty

    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


# ======================================================================
# Main entry point
# ======================================================================


def main() -> None:
    """CLI entry point for calibration."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Run inference parameter calibration"
    )
    parser.add_argument(
        "--prompts",
        required=True,
        help="Path to JSON file containing prompts",
    )
    parser.add_argument(
        "--output-dir",
        default="./calibration_results",
        help="Output directory for results",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from checkpoint if available in output directory",
    )

    args = parser.parse_args()

    # Load prompts
    with open(args.prompts, "r", encoding="utf-8") as f:
        prompts_data = json.load(f)

    # Handle both formats: list or {"prompts": [...]} or {"prompts": [{"id":..., "text":...}]}
    if isinstance(prompts_data, dict):
        prompts = prompts_data.get("prompts", prompts_data.get("samples", []))
    else:
        prompts = prompts_data

    # Determine checkpoint directory for resume functionality
    checkpoint_dir = args.output_dir if args.resume else None

    # Run calibration
    report = run_calibration(
        prompts=prompts,
        output_dir=args.output_dir,
        verbose=args.verbose,
        checkpoint_dir=checkpoint_dir,
    )

    print(f"Calibration complete. Best score: {report.best_score:.3f}")
    print(f"Best profile: {report.best_profile}")

    sys.exit(0)


if __name__ == "__main__":
    main()
