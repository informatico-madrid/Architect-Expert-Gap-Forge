#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio
# SPDX-License-Identifier: Apache-2.0

"""AEGF Prompt Manager — Loads and formats evaluation templates from YAML.

Externalizes all pipeline prompts to a YAML file to keep orchestration logic
free of multiline strings and hardcoded prompts.
"""
from __future__ import annotations

import logging
from types import MappingProxyType
from pathlib import Path
from typing import Any, Final

import yaml

__all__ = ["PromptManager"]

logger = logging.getLogger("AEGF.PromptManager")

# Default location of the prompt YAML relative to the project root
_DEFAULT_PROMPTS_PATH: Final[Path] = Path("configs/stage_5_evaluation/eval_prompts.yaml")


class PromptManager:
    """Loads prompt templates from YAML and formats them at runtime.

    This class enforces immutability of templates after initial load.
    """

    def __init__(self, prompts_path: Path | str | None = None) -> None:
        """Initialise the manager and load templates into memory."""
        path: Final[Path] = Path(prompts_path) if prompts_path else _DEFAULT_PROMPTS_PATH
        
        if not path.exists():
            raise FileNotFoundError(f"Prompt YAML not found: {path}")

        with open(path, "r", encoding="utf-8") as fh:
            loaded: dict[str, dict[str, str]] = yaml.safe_load(fh) or {}
            
        # Protect against runtime mutation using MappingProxyType
        self._templates: Final = MappingProxyType(loaded)
        logger.debug("Loaded %d prompt groups from %s", len(self._templates), path)

    # -- Public API ----------------------------------------------------------

    def system(self, group: str) -> str:
        """Return the system prompt for a given template group."""
        return self._get(group, "system")

    def user_template(self, group: str) -> str:
        """Return the raw user template (with {placeholders})."""
        return self._get(group, "user")

    def format(self, group: str, **kwargs: Any) -> str:
        """Format the user template with the supplied keyword arguments."""
        template = self._get(group, "user")
        try:
            return template.format(**kwargs)
        except KeyError as exc:
            raise KeyError(
                f"Missing required placeholder {exc} for prompt group '{group}'"
            ) from exc

    def groups(self) -> list[str]:
        """Return the list of available prompt groups."""
        return list(self._templates.keys())

    # -- Internal ------------------------------------------------------------

    def _get(self, group: str, key: str) -> str:
        """Internal selector with strict error messaging."""
        if group not in self._templates:
            raise KeyError(
                f"Unknown prompt group '{group}'. Available: {self.groups()}"
            )
        
        section = self._templates[group]
        if key not in section:
            raise KeyError(f"Prompt group '{group}' has no '{key}' template")
            
        return section[key]