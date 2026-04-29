#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0
"""Shared utility for DSPy integration.

Pure bridge between business logic and DSPy predict/chain-of-thought factories.
Returns None when no LM is configured so callers can fall back to templates.
"""

from __future__ import annotations

from typing import Any, Optional, Union

import dspy


def _lm_configured() -> bool:
    """Return True if a default LM is configured in DSPy settings."""
    return dspy.settings.lm is not None


def get_predict(
    signature_class: Any,
    instructions: Optional[str] = None,
) -> Optional[dspy.Predict]:
    """Return a dspy.Predict instance or None.

    When an LM is configured, returns a predictor built from *signature_class*
    with optional custom instructions.  Otherwise returns *None* so the caller
    falls back to template-based behaviour.

    Parameters
    ----------
    signature_class:
        A ``dspy.Signature`` subclass.
    instructions:
        Optional override string that replaces the signature's default
        instructions via ``with_instructions()``.

    Returns
    -------
    dspy.Predict | None
    """
    if not _lm_configured():
        return None

    sig = signature_class
    if instructions is not None:
        sig = signature_class.with_instructions(instructions)
    return dspy.Predict(sig)


def get_chain_of_thought(
    signature_or_str: Union[type, str],
    instructions: Optional[str] = None,
) -> Optional[dspy.ChainOfThought]:
    """Return a dspy.ChainOfThought module or None.

    Parameters
    ----------
    signature_or_str:
        A ``dspy.Signature`` subclass or a signature definition string
        (e.g. ``"category: str, context: str -> abstract_objective: str"``).
    instructions:
        Optional override string.

    Returns
    -------
    dspy.ChainOfThought | None
    """
    if not _lm_configured():
        return None

    if isinstance(signature_or_str, str):
        sig = dspy.Signature(signature_or_str)
    else:
        sig = signature_or_str

    cot = dspy.ChainOfThought(sig)
    if instructions is not None:
        cot = dspy.ChainOfThought(sig.with_instructions(instructions))
    return cot
