#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Architect-Expert-Gap-Forge (AEGF) - Hard Query Builder

Generates hard queries with abstract objectives (no tool names or implementation hints).
Loads templates and forbidden terms from configs/stage_2_factory/prompts/hard_query_templates.yaml.

SPDX-License-Identifier: Apache-2.0
Copyright 2026 AEGF
"""

from __future__ import annotations

import logging
import random
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Default template path
_DEFAULT_TEMPLATES_PATH: Path = Path(
    "configs/stage_2_factory/prompts/hard_query_templates.yaml"
)


class HardQueryTemplateLoader:
    """Loads hard query templates from YAML."""

    def __init__(self, templates_path: Path | str | None = None) -> None:
        """Initialize and load templates.

        Args:
            templates_path: Optional custom path to templates YAML file.
        """
        path = Path(templates_path) if templates_path else _DEFAULT_TEMPLATES_PATH

        if not path.exists():
            logger.warning("Template file not found: %s, using defaults", path)
            self._templates = self._default_templates()
        else:
            with open(path, encoding="utf-8") as fh:
                self._templates = yaml.safe_load(fh) or {}

    def load_templates(self) -> dict[str, Any]:
        """Return loaded templates."""
        return self._templates

    def get_forbidden_terms(self) -> list[str]:
        """Return forbidden terms list from templates."""
        return self._templates.get("forbidden_terms", [])

    def get_template_names(self) -> list[str]:
        """Return available template names."""
        return list(self._templates.get("templates", {}).keys())

    def get_template(self, name: str) -> str:
        """Return a specific template by name."""
        templates = self._templates.get("templates", {})
        return templates.get(name, {}).get("template", "")

    def get_use_case_config(self, use_case: str) -> dict[str, Any]:
        """Return configuration for a specific use case."""
        return self._templates.get("use_cases", {}).get(use_case, {})

    def get_validator_config(self) -> dict[str, Any]:
        """Return validator configuration."""
        return self._templates.get("validator", {})

    def _default_templates(self) -> dict[str, Any]:
        """Return default templates when file is missing."""
        return {
            "forbidden_terms": [
                "async_forward_entry_setups",
                "DataUpdateCoordinator",
                "llama al servicio",
                "usa el componente",
                "async_setup_entry",
            ],
            "templates": {
                "problem_focused": {
                    "template": "Objetivo: {objective}\n\nContexto: {context}",
                },
            },
            "use_cases": {
                "home_assistant": {
                    "objective_templates": [
                        "El sistema debe mantener sincronizado el estado entre dispositivos",
                    ],
                },
            },
            "validator": {
                "min_abstractness": 0.7,
                "check_forbidden": True,
            },
        }


class HardQueryBuilder:
    """Builds hard queries with abstract objectives.

    Hard queries describe the final goal WITHOUT mentioning specific tools,
    classes, or implementation steps. This forces the model to reason
    autonomously about the solution approach.

    Attributes:
        use_case: The use case domain (e.g., home_assistant, php_legacy)
    """

    def __init__(
        self,
        use_case: str,
        templates_path: Path | str | None = None,
        seed: int | None = None,
    ) -> None:
        """Initialize the hard query builder.

        Args:
            use_case: The use case domain
            templates_path: Optional custom path to templates YAML
            seed: Optional random seed for reproducibility
        """
        self.use_case = use_case
        self._loader = HardQueryTemplateLoader(templates_path)
        self._templates = self._loader.load_templates()
        self._forbidden_terms = self._loader.get_forbidden_terms()
        self._validator_config = self._loader.get_validator_config()
        self._use_case_config = self._loader.get_use_case_config(use_case)

        if seed is not None:
            random.seed(seed)

    @property
    def forbidden_terms(self) -> list[str]:
        """Return the list of forbidden terms from config."""
        return self._forbidden_terms

    def build(self, seed_data: dict[str, Any]) -> str:
        """Build an abstract hard query from seed data.

        Transforms seed data into an abstract objective description
        that doesn't mention specific tools or implementation steps.

        Args:
            seed_data: Seed data containing seed_id, category, context, question, etc.

        Returns:
            Abstract hard query string suitable for model input
        """
        seed_id = seed_data.get("seed_id", "unknown")
        category = seed_data.get("category", "")
        context = seed_data.get("context", "")
        question = seed_data.get("question", "")

        # Get template names and select one randomly
        template_names = self._loader.get_template_names()
        if not template_names:
            template_names = ["problem_focused"]

        selected_template = random.choice(template_names)
        template_str = self._loader.get_template(selected_template)

        # Get use-case specific context templates
        context_templates = self._use_case_config.get(
            "context_templates",
            ["Existe un sistema que necesita ser implementado"],
        )

        # Select random background (objective_templates used in _transform_to_abstract)
        background = random.choice(context_templates)

        # Format the template with abstract content
        # Use the CATEGORY as the objective descriptor (abstract)
        # and the CONTEXT as background (also abstract from seed)
        #
        # We transform the explicit question into an abstract objective
        # by focusing on the CATEGORY (domain) rather than the specific question
        abstract_objective = self._transform_to_abstract(category, context)

        # Format the prompt using the template
        if "objective" in template_str and "context" in template_str:
            prompt = template_str.format(
                objective=abstract_objective,
                context=context,  # Seed context is already abstract per test fixtures
            )
        elif "outcome" in template_str and "available" in template_str:
            prompt = template_str.format(
                outcome=abstract_objective,
                available=context,
                expected_result="El sistema debe funcionar correctamente",
            )
        elif "question" in template_str and "background" in template_str:
            prompt = template_str.format(
                question=question,  # Original question - may need transformation
                background=background,
                desired_state="el resultado esperado",
            )
        elif "requirement" in template_str and "constraints" in template_str:
            prompt = template_str.format(
                requirement=abstract_objective,
                constraints="Sin usar implementaciones específicas",
            )
        else:
            # Fallback to simple format
            prompt = f"Objetivo: {abstract_objective}\n\nContexto: {context}"

        logger.debug("Built hard query for seed %s: %s", seed_id, prompt[:100])

        return prompt

    def _transform_to_abstract(self, category: str, context: str) -> str:
        """Transform category/context into abstract objective description.

        Args:
            category: The category from seed (e.g., "dual_mode_integration")
            context: The context from seed (abstract description)

        Returns:
            Abstract objective description
        """
        # Transform category name into human-readable abstract objective
        # Replace underscores and convert to Spanish objective
        category_words = category.replace("_", " ")

        # Map common patterns to abstract objectives
        if "coordinator" in category.lower():
            abstract = "El sistema debe coordinar actualizaciones de datos automáticamente"
        elif "integration" in category.lower():
            abstract = "El sistema debe integrar componentes de forma autónoma"
        elif "entity" in category.lower():
            abstract = "El sistema debe gestionar entidades con verificación de tipos"
        elif "protocol" in category.lower():
            abstract = "El sistema debe implementar protocolos de comunicación"
        elif "websocket" in category.lower():
            abstract = "El sistema debe mantener comunicación bidireccional"
        elif "bluetooth" in category.lower():
            abstract = "El sistema debe recibir datos de dispositivos externos"
        elif "rest" in category.lower():
            abstract = "El sistema debe consumir servicios externos"
        else:
            # Generic abstract transformation
            abstract = f"El sistema debe manejar {category_words} de forma autónoma"

        return abstract

    def validate_prompt(self, text: str) -> bool:
        """Validate that a prompt meets abstractness requirements.

        Checks for:
        - Forbidden terms (tool names, imperative verbs)
        - Imperative construction patterns

        Args:
            text: The prompt text to validate

        Returns:
            True if prompt is valid (abstract), False otherwise
        """
        text_lower = text.lower()

        # Check for forbidden terms
        if self._validator_config.get("check_forbidden", True):
            for term in self._forbidden_terms:
                if term.lower() in text_lower:
                    logger.debug("Rejected prompt containing forbidden term: %s", term)
                    return False

        # Check for imperative verbs if enabled
        if self._validator_config.get("check_imperative", True):
            imperative_patterns = [
                "implementa usando",
                "crea una clase",
                "define la función",
                "sigue estos pasos",
                "primero haz",
                "después haz",
                "para resolver esto:",
                "necesitas usar",
                "debes usar",
            ]
            for pattern in imperative_patterns:
                if pattern in text_lower:
                    logger.debug("Rejected prompt containing imperative: %s", pattern)
                    return False

        return True

    def build_with_validation(self, seed_data: dict[str, Any]) -> str:
        """Build a hard query and validate it.

        Generates a hard query and validates it meets abstractness requirements.
        If validation fails, retries with a different template up to 3 times.

        Args:
            seed_data: Seed data for building the query

        Returns:
            Valid abstract hard query string

        Raises:
            ValueError: If no valid prompt can be generated after retries
        """
        max_retries = 3

        for attempt in range(max_retries):
            prompt = self.build(seed_data)

            if self.validate_prompt(prompt):
                return prompt

            logger.warning(
                "Attempt %d: Prompt validation failed for seed %s, retrying",
                attempt + 1,
                seed_data.get("seed_id", "unknown"),
            )

        raise ValueError(
            f"Could not generate valid abstract prompt for seed {seed_data.get('seed_id', 'unknown')} "
            f"after {max_retries} attempts"
        )


__all__ = ["HardQueryBuilder", "HardQueryTemplateLoader"]
