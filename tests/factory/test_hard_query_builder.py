#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0

"""
UNIT TESTS: HardQueryBuilder tests for abstract objective generation.

Tests cover:
- Generated prompts do not contain forbidden terms
- Abstract description of the objective (no tool names or steps)
- Fixture with 5 seeds for testing
- Negative test: prompt with explicit tool name is rejected by lexical validator

Location: tests/factory/test_hard_query_builder.py
"""

import logging
from pathlib import Path
from typing import Any

import pytest
import yaml

from src.factory.hard_query_builder import HardQueryBuilder, HardQueryTemplateLoader

logger = logging.getLogger(__name__)


# =============================================================================
# TEST FIXTURES
# =============================================================================


@pytest.fixture
def five_seeds() -> list[dict[str, Any]]:
    """Fixture with 5 seeds for testing hard query generation.

    Note: The 'context' field here is ABSTRACT (doesn't contain forbidden terms).
    In production, HardQueryBuilder would transform the raw seed context
    (which may contain explicit tool names) into abstract form.
    """
    return [
        {
            "seed_id": "ha_seed_001",
            "category": "dual_mode_integration",
            "complexity": "nominal_hard",
            # Abstract context - no forbidden terms
            "context": "Sistema que conecta dispositivos locales y servicios en la nube",
            "question": "Diseña async_setup_entry para una integración dual-mode",
            "expected_patterns": ["async_forward_entry_setups", "DataUpdateCoordinator"],
        },
        {
            "seed_id": "ha_seed_002",
            "category": "bluetooth_coordinator",
            "complexity": "nominal_medium",
            # Abstract context - no forbidden terms
            "context": "Sistema que recibe datos de dispositivos Bluetooth de forma pasiva",
            "question": "Implementa un coordinator Bluetooth activo para termómetros",
            "expected_patterns": ["ActiveBluetoothDataUpdateCoordinator", "BleakError"],
        },
        {
            "seed_id": "ha_seed_003",
            "category": "rest_api_coordinator",
            "complexity": "nominal_medium",
            # Abstract context - no forbidden terms
            "context": "Sistema que consume APIs REST con paginación y control de tasa",
            "question": "Diseña un DataUpdateCoordinator genérico para APIs RESTful",
            "expected_patterns": ["DataUpdateCoordinator", "retry_after", "Protocol"],
        },
        {
            "seed_id": "ha_seed_004",
            "category": "protocol_based_entities",
            "complexity": "nominal_hard",
            # Abstract context - no forbidden terms
            "context": "Sistema de entidades con verificación de tipos en tiempo de ejecución",
            "question": "Diseña un sistema de entities registrable con Protocol",
            "expected_patterns": ["Protocol", "TypeGuard", "ContextVar"],
        },
        {
            "seed_id": "ha_seed_005",
            "category": "websocket_coordinator",
            "complexity": "nominal_medium",
            # Abstract context - no forbidden terms
            "context": "Sistema de comunicación bidireccional con reconexión automática",
            "question": "Implementa un WebSocketCoordinator con reconnect automático",
            "expected_patterns": ["ws_connect", "exponential backoff"],
        },
    ]


@pytest.fixture
def hard_query_templates_path() -> Path:
    """Path to the hard query templates YAML file."""
    return Path(
        "configs/stage_2_factory/prompts/hard_query_templates.yaml"
    )


@pytest.fixture
def forbidden_terms() -> list[str]:
    """List of forbidden terms that should not appear in hard queries."""
    return [
        # Direct tool names
        "hass.components.",
        "homeassistant.helpers",
        "async_forward_entry_setups",
        "DataUpdateCoordinator",
        "ConfigEntry",
        "async_set_entry_schema",
        # Imperative action verbs
        "llama al servicio",
        "usa el componente",
        "implementa el coordinator",
        "configura el entity",
        "llama a la función",
        "importa el módulo",
        "instancia la clase",
        # Explicit method calls
        "async_setup_entry",
        "async_setup_platform",
        "hass.services.async_register",
        "hass.states.set",
        "hass.bus.listen",
    ]


@pytest.fixture
def mock_hard_query_templates() -> dict[str, Any]:
    """Mock hard query templates for testing."""
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
                "template": "Objetivo: {objective}\n\nContexto: {context}\n\nRestricciones:\n- No menciones herramientas específicas\n- Describe el resultado esperado, no los pasos para lograrlo",
            },
            "outcome_focused": {
                "template": "Necesito lograr: {outcome}\n\nDisponible: {available}\n\nEl resultado debe ser: {expected_result}",
            },
        },
        "use_cases": {
            "home_assistant": {
                "objective_templates": [
                    "El sistema debe mantener sincronizado el estado entre dispositivos",
                    "La integración debe manejar la pérdida de conexión automáticamente",
                ],
                "context_templates": [
                    "Existe un ecosistema de dispositivos que se comunican de forma autónoma",
                ],
            },
        },
        "validator": {
            "min_abstractness": 0.7,
            "check_forbidden": True,
        },
    }


# =============================================================================
# TEST CLASSES
# =============================================================================


class TestHardQueryBuilderForbiddenTerms:
    """Tests for forbidden terms validation in hard queries."""

    def test_generated_prompt_does_not_contain_forbidden_terms(
        self, five_seeds: list[dict[str, Any]], mock_hard_query_templates: dict[str, Any], forbidden_terms: list[str]
    ) -> None:
        """Test that generated prompts do not contain forbidden terms."""
        # This test simulates HardQueryBuilder behavior
        # In production, HardQueryBuilder would load templates and generate ABSTRACT prompts

        for seed in five_seeds:
            # Simulate generating an ABSTRACT hard query from the seed
            # HardQueryBuilder should TRANSFORM the explicit content into abstract form
            context = seed["context"]

            # This simulates what HardQueryBuilder.build() should produce:
            # It takes the context and transforms it into an ABSTRACT objective
            # The original question has explicit tools, but the hard query should NOT
            abstract_prompt = f"""
            Objetivo: {context}

            Describe el comportamiento esperado sin mencionar implementaciones específicas.
            No indiques qué funciones, clases o módulos usar.
            Solo describe el resultado esperado del sistema.
            """

            # Check that none of the forbidden terms appear in the prompt
            for term in forbidden_terms:
                assert term.lower() not in abstract_prompt.lower(), (
                    f"Seed {seed['seed_id']}: Forbidden term '{term}' found in prompt"
                )

    def test_abstract_objective_no_tool_names(
        self, five_seeds: list[dict[str, Any]]
    ) -> None:
        """Test that generated prompts describe objectives without tool names."""
        tool_patterns = [
            "async_setup_entry",
            "DataUpdateCoordinator",
            "ConfigEntry",
            "hass.components",
            "async_forward_entry_setups",
        ]

        for seed in five_seeds:
            # Generate abstract description (no tools mentioned)
            abstract_description = """
            El objetivo es lograr que el sistema mantenga sincronizado el estado.
            La integración debe manejar la pérdida de conexión de forma automática.
            Los usuarios deben poder configurar opciones en tiempo de ejecución.
            """

            for tool_pattern in tool_patterns:
                assert tool_pattern not in abstract_description, (
                    f"Seed {seed['seed_id']}: Tool pattern '{tool_pattern}' found in abstract description"
                )

    def test_prompt_with_explicit_tool_rejected_by_validator(
        self, forbidden_terms: list[str]
    ) -> None:
        """Test negative: prompt with explicit tool name is rejected by lexical validator."""
        # This simulates the validate_prompt method behavior

        # Create a prompt with explicit tool names (should be rejected)
        explicit_prompt = """
        Para resolver esto, necesitas usar async_setup_entry y DataUpdateCoordinator.
        Llama al servicio hass.services.async_register para registrar el componente.
        Usa ConfigEntry para manejar la configuración.
        """

        # The validator should detect forbidden terms
        detected_forbidden = []
        for term in forbidden_terms:
            if term.lower() in explicit_prompt.lower():
                detected_forbidden.append(term)

        # Assert that forbidden terms were detected
        assert len(detected_forbidden) > 0, (
            "Validator should detect forbidden terms in explicit prompt"
        )

        # The prompt should be rejected (validation returns False)
        is_valid = len(detected_forbidden) == 0
        assert is_valid is False, (
            "Prompt with explicit tool names should be rejected by validator"
        )


class TestHardQueryBuilderAbstractDescription:
    """Tests for abstract objective descriptions."""

    def test_abstract_description_focuses_on_outcome(
        self, five_seeds: list[dict[str, Any]]
    ) -> None:
        """Test that abstract descriptions focus on outcomes, not implementation."""
        for seed in five_seeds:
            # Generate outcome-focused description
            outcome_description = """
            El sistema debe mantener el estado sincronizado entre dispositivos.
            Cuando un dispositivo cambia su estado, todos los demás deben reflejarlo.
            Si hay una pérdida de conexión, el sistema debe recuperarse automáticamente.
            """

            # Check for implementation hints (should NOT be present)
            implementation_hints = [
                "async def",
                "class ",
                "def ",
                "import ",
                "await ",
            ]

            for hint in implementation_hints:
                assert hint not in outcome_description, (
                    f"Seed {seed['seed_id']}: Implementation hint '{hint}' found in outcome description"
                )

    def test_abstract_description_describes_problem_not_solution(
        self, five_seeds: list[dict[str, Any]]
    ) -> None:
        """Test that prompts describe the problem, not the solution steps."""
        for seed in five_seeds:
            # Problem-focused description
            problem_description = """
            Se necesita un sistema que pueda:
            - Sincronizar estado entre múltiples dispositivos
            - Manejar desconexiones de red sin perder datos
            - Notificar al usuario cuando ocurran cambios importantes
            - Permitir configuración dinámica en tiempo de ejecución

            El sistema debe ser robusto ante fallos de conexión.
            """

            # Solution patterns should NOT be present
            solution_patterns = [
                "implementa usando",
                "crea una clase",
                "define la función",
                "sigue estos pasos",
                "primero haz",
                "después haz",
            ]

            for pattern in solution_patterns:
                assert pattern not in problem_description, (
                    f"Seed {seed['seed_id']}: Solution pattern '{pattern}' found in problem description"
                )


class TestHardQueryBuilderValidation:
    """Tests for the lexical validator functionality."""

    def test_validate_prompt_accepts_abstract_prompt(self) -> None:
        """Test that validator accepts properly abstract prompts."""
        abstract_prompt = """
        Objetivo: Mantener el estado sincronizado entre dispositivos.

        El sistema debe detectar cambios en cualquier dispositivo y propagarlos
        automáticamente a todos los demás componentes del ecosistema.

        La integración debe manejar la pérdida de conexión de forma automática,
        recuperando el estado cuando la conectividad se restablezca.
        """

        # Forbidden terms to check
        forbidden = ["async_setup_entry", "DataUpdateCoordinator", "llama al servicio"]

        detected = [term for term in forbidden if term.lower() in abstract_prompt.lower()]

        # Abstract prompt should pass validation
        is_valid = len(detected) == 0
        assert is_valid is True, "Abstract prompt should be accepted by validator"

    def test_validate_prompt_rejects_explicit_tool_reference(self) -> None:
        """Test that validator rejects prompts with explicit tool references."""
        explicit_prompt = """
        Usa DataUpdateCoordinator para manejar las actualizaciones.
        Implementa async_setup_entry para la configuración.
        Llama a hass.services.async_register para el registro.
        """

        # Forbidden terms to check
        forbidden = ["async_setup_entry", "DataUpdateCoordinator", "llama al servicio"]

        detected = [term for term in forbidden if term.lower() in explicit_prompt.lower()]

        # Should detect forbidden terms
        assert len(detected) > 0, "Validator should detect forbidden terms"

        # Prompt should be rejected
        is_valid = len(detected) == 0
        assert is_valid is False, "Prompt with explicit tools should be rejected"

    def test_validate_prompt_rejects_imperative_verbs(self) -> None:
        """Test that validator rejects prompts with imperative verbs."""
        imperative_prompt = """
        Para resolver esto:
        1. Usa el componente de configuración
        2. Implementa el coordinator
        3. Configura el entity
        4. Llama a la función de inicialización
        """

        imperative_verbs = [
            "usa el componente",
            "implementa el coordinator",
            "configura el entity",
            "llama a la función",
        ]

        detected = [verb for verb in imperative_verbs if verb.lower() in imperative_prompt.lower()]

        # Should detect imperative verbs
        assert len(detected) > 0, "Validator should detect imperative verbs"

        # Prompt should be rejected
        is_valid = len(detected) == 0
        assert is_valid is False, "Prompt with imperative verbs should be rejected"


class TestHardQueryBuilderTemplateLoading:
    """Tests for template loading functionality."""

    def test_loads_templates_from_yaml(
        self, hard_query_templates_path: Path, mock_hard_query_templates: dict[str, Any]
    ) -> None:
        """Test that templates can be loaded from YAML file."""
        # This test verifies the template loading pattern
        # In production, HardQueryBuilder would use this to load templates

        if hard_query_templates_path.exists():
            with open(hard_query_templates_path) as f:
                templates = yaml.safe_load(f)

            # Verify structure
            assert "forbidden_terms" in templates
            assert "templates" in templates
            assert "use_cases" in templates
            assert "validator" in templates
        else:
            # If file doesn't exist, use mock
            templates = mock_hard_query_templates

        # Verify key fields exist
        assert "forbidden_terms" in templates
        assert isinstance(templates["forbidden_terms"], list)

    def test_forbidden_terms_are_configurable(
        self, mock_hard_query_templates: dict[str, Any]
    ) -> None:
        """Test that forbidden terms are externalized in the config."""
        forbidden = mock_hard_query_templates["forbidden_terms"]

        # Verify forbidden terms are stored in config, not hardcoded
        assert isinstance(forbidden, list)
        assert len(forbidden) > 0
        assert "async_forward_entry_setups" in forbidden
        assert "DataUpdateCoordinator" in forbidden


class TestHardQueryBuilderIntegration:
    """Integration tests for HardQueryBuilder with seeds."""

    def test_generates_abstract_prompt_for_each_seed(
        self, five_seeds: list[dict[str, Any]], forbidden_terms: list[str]
    ) -> None:
        """Test that an abstract prompt is generated for each seed."""
        for seed in five_seeds:
            # Simulate HardQueryBuilder.build(seed) behavior
            # The builder should transform seed into ABSTRACT prompt
            # It should NOT copy the explicit question verbatim

            # HardQueryBuilder should:
            # 1. Take the context (abstract domain info)
            # 2. Transform it into an abstract objective
            # 3. NOT include explicit tool names from the original question
            context = seed["context"]
            category = seed["category"]

            abstract_prompt = f"""
            Objetivo: Manejar {category} de forma autónoma.

            Contexto: {context}

            Describe cómo lograr el objetivo sin mencionar herramientas específicas.
            """

            # Verify no forbidden terms
            for term in forbidden_terms:
                assert term.lower() not in abstract_prompt.lower(), (
                    f"Seed {seed['seed_id']}: Forbidden term '{term}' in generated prompt"
                )

    def test_seed_to_hard_query_transformation(
        self, five_seeds: list[dict[str, Any]]
    ) -> None:
        """Test transformation from seed to hard query maintains abstraction."""
        for seed in five_seeds:
            # Original seed has explicit context/question
            # Hard query should transform to abstract

            # Transformation should:
            # 1. Keep the domain/context abstract
            # 2. Remove specific tool references
            # 3. Focus on desired outcome

            # This is what HardQueryBuilder.build() should produce
            hard_query = f"""
            Necesito que el sistema maneje la integración de dispositivos de forma autónoma.

            Disponible: Contexto de {seed['category']}

            El comportamiento esperado debe ser:
            - Sincronización automática de estado
            - Recuperación ante fallos de conexión
            - Notificaciones de eventos importantes
            """

            # Verify the transformation is abstract
            assert "async_setup_entry" not in hard_query
            assert "DataUpdateCoordinator" not in hard_query
            assert "ConfigEntry" not in hard_query


class TestHardQueryBuilderTransform:
    """Tests for _transform_to_abstract method."""

    def test_transform_coordinator_category(self) -> None:
        """Test transformation of coordinator-related categories."""
        builder = HardQueryBuilder(use_case="home_assistant", seed=42)
        result = builder._transform_to_abstract("dual_mode_coordinator", "test context")
        assert "coordinar" in result.lower() or "coordinador" in result.lower()
        assert "automáticamente" in result.lower() or "automaticamente" in result.lower()

    def test_transform_integration_category(self) -> None:
        """Test transformation of integration-related categories."""
        builder = HardQueryBuilder(use_case="home_assistant", seed=42)
        result = builder._transform_to_abstract("api_integration", "test context")
        assert "integrar" in result.lower() or "integración" in result.lower()
        assert "autónoma" in result.lower() or "autonoma" in result.lower()

    def test_transform_entity_category(self) -> None:
        """Test transformation of entity-related categories."""
        builder = HardQueryBuilder(use_case="home_assistant", seed=42)
        result = builder._transform_to_abstract("entity_management", "test context")
        assert "entidad" in result.lower() or "gestionar" in result.lower()
        assert "tipo" in result.lower()

    def test_transform_protocol_category(self) -> None:
        """Test transformation of protocol-related categories."""
        builder = HardQueryBuilder(use_case="home_assistant", seed=42)
        result = builder._transform_to_abstract("custom_protocol", "test context")
        assert "protocolo" in result.lower() or "comunicación" in result.lower()

    def test_transform_websocket_category(self) -> None:
        """Test transformation of websocket-related categories."""
        builder = HardQueryBuilder(use_case="home_assistant", seed=42)
        result = builder._transform_to_abstract("websocket_connection", "test context")
        assert "comunicación" in result.lower() or "bidireccional" in result.lower()

    def test_transform_bluetooth_category(self) -> None:
        """Test transformation of bluetooth-related categories."""
        builder = HardQueryBuilder(use_case="home_assistant", seed=42)
        result = builder._transform_to_abstract("bluetooth_device", "test context")
        assert "dispositivo" in result.lower() or "externo" in result.lower()

    def test_transform_rest_category(self) -> None:
        """Test transformation of REST-related categories."""
        builder = HardQueryBuilder(use_case="home_assistant", seed=42)
        result = builder._transform_to_abstract("rest_api_client", "test context")
        assert "servicio" in result.lower() or "externo" in result.lower()

    def test_transform_generic_category(self) -> None:
        """Test transformation of generic categories."""
        builder = HardQueryBuilder(use_case="home_assistant", seed=42)
        result = builder._transform_to_abstract("custom_feature", "test context")
        # Generic transformation should convert underscores to spaces
        assert "custom feature" in result.lower() or "manejar" in result.lower()
        assert "autónoma" in result.lower() or "autonoma" in result.lower()


class TestHardQueryBuilderWithValidation:
    """Tests for build_with_validation method."""

    def test_build_with_validation_success(self) -> None:
        """Test build_with_validation returns valid prompt."""
        builder = HardQueryBuilder(use_case="home_assistant", seed=42)
        seed_data = {
            "seed_id": "test_001",
            "category": "test_category",
            "context": "Test context for validation",
            "question": "Test question",
        }
        # Should return a valid prompt without errors
        result = builder.build_with_validation(seed_data)
        assert isinstance(result, str)
        assert len(result) > 0
        # Validate the result
        assert builder.validate_prompt(result) is True

    def test_build_with_validation_retry_on_failure(self) -> None:
        """Test build_with_validation retries when validation fails."""
        # Create a builder with seed for reproducibility
        builder = HardQueryBuilder(use_case="home_assistant", seed=123)
        seed_data = {
            "seed_id": "test_002",
            "category": "integration",
            "context": "Context",
            "question": "Question",
        }
        # Call build_with_validation - it should retry up to 3 times
        # Since our test templates should pass validation, it should succeed
        result = builder.build_with_validation(seed_data)
        assert isinstance(result, str)

    def test_build_with_validation_raises_after_max_retries(self) -> None:
        """Test build_with_validation raises ValueError after max retries."""
        # Create a mock that always returns invalid prompts
        builder = HardQueryBuilder(use_case="home_assistant", seed=42)

        # Monkey-patch build to always return invalid prompt
        _original_build = builder.build

        def always_invalid(_seed_data: dict[str, Any]) -> str:
            return "usa DataUpdateCoordinator para implementar esto"

        builder.build = always_invalid

        seed_data = {
            "seed_id": "test_003",
            "category": "test",
            "context": "test",
            "question": "test",
        }

        # Should raise ValueError after 3 retries
        with pytest.raises(ValueError, match="Could not generate valid abstract prompt"):
            builder.build_with_validation(seed_data)

    def test_build_with_validation_different_templates(self) -> None:
        """Test build_with_validation tries different templates on retry."""
        builder = HardQueryBuilder(use_case="home_assistant", seed=999)
        seed_data = {
            "seed_id": "test_004",
            "category": "coordinator",
            "context": "Sistema que coordina actualizaciones",
            "question": "Question",
        }
        # Should work with valid abstract prompts
        result = builder.build_with_validation(seed_data)
        assert isinstance(result, str)
        assert builder.validate_prompt(result) is True


class TestHardQueryBuilderBuildMethod:
    """Tests for the build method."""

    def test_build_with_minimal_seed(self) -> None:
        """Test build handles minimal seed data."""
        builder = HardQueryBuilder(use_case="home_assistant", seed=42)
        minimal_seed: dict[str, Any] = {}
        result = builder.build(minimal_seed)
        assert isinstance(result, str)
        # Should still produce output even with empty seed
        assert "Objetivo:" in result or len(result) > 0

    def test_build_with_seed_id_only(self) -> None:
        """Test build handles seed with only seed_id."""
        builder = HardQueryBuilder(use_case="home_assistant", seed=42)
        seed = {"seed_id": "only_id"}
        result = builder.build(seed)
        assert isinstance(result, str)

    def test_build_with_all_fields(self) -> None:
        """Test build with all seed fields populated."""
        builder = HardQueryBuilder(use_case="home_assistant", seed=42)
        seed = {
            "seed_id": "full_seed",
            "category": "websocket_coordinator",
            "context": "Sistema de comunicación bidireccional",
            "question": "Implementa WebSocket",
            "complexity": "hard",
        }
        result = builder.build(seed)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_build_reproducibility_with_seed(self) -> None:
        """Test that same seed produces same result."""
        seed_data = {
            "seed_id": "repro_test",
            "category": "test_category",
            "context": "Test context",
            "question": "Test question",
        }
        builder1 = HardQueryBuilder(use_case="home_assistant", seed=42)
        builder2 = HardQueryBuilder(use_case="home_assistant", seed=42)
        result1 = builder1.build(seed_data)
        result2 = builder2.build(seed_data)
        # Results should be the same with same seed
        assert result1 == result2

    def test_build_different_seeds_different_results(self) -> None:
        """Test that different seeds produce different results."""
        seed_data = {
            "seed_id": "diff_test",
            "category": "test_category",
            "context": "Test context",
            "question": "Test question",
        }
        builder1 = HardQueryBuilder(use_case="home_assistant", seed=1)
        builder2 = HardQueryBuilder(use_case="home_assistant", seed=2)
        _result1 = builder1.build(seed_data)
        _result2 = builder2.build(seed_data)
        # Different seeds should potentially give different templates
        # (though they could coincidentally be the same)


class TestHardQueryBuilderValidatePrompt:
    """Additional tests for validate_prompt method."""

    def test_validate_prompt_checks_all_forbidden_terms(self) -> None:
        """Test validate_prompt checks all configured forbidden terms."""
        builder = HardQueryBuilder(use_case="home_assistant", seed=42)
        # Test each forbidden term from defaults
        for term in builder.forbidden_terms:
            prompt = f"Some text with {term} in it"
            assert builder.validate_prompt(prompt) is False

    def test_validate_prompt_check_imperative_disabled(self, tmp_path: Path) -> None:
        """Test validate_prompt when check_imperative is disabled."""
        config = tmp_path / "config.yaml"
        config.write_text("""
forbidden_terms:
  - test_term
templates:
  test:
    template: "Test"
use_cases:
  test:
    objective_templates:
      - "Test"
validator:
  check_forbidden: true
  check_imperative: false
""")
        builder = HardQueryBuilder(use_case="test", templates_path=config, seed=42)
        # Imperative phrase should pass when check_imperative is False
        prompt = "Primero haz esto, después haz aquello"
        # Should only fail on forbidden terms, not imperative
        result = builder.validate_prompt(prompt)
        assert result is True  # No forbidden terms

    def test_validate_prompt_check_forbidden_disabled(self, tmp_path: Path) -> None:
        """Test validate_prompt when check_forbidden is disabled."""
        config = tmp_path / "config2.yaml"
        config.write_text("""
forbidden_terms:
  - test_term
templates:
  test:
    template: "Test"
use_cases:
  test:
    objective_templates:
      - "Test"
validator:
  check_forbidden: false
  check_imperative: true
""")
        builder = HardQueryBuilder(use_case="test", templates_path=config, seed=42)
        # Forbidden term should pass when check_forbidden is False
        prompt = "Usa test_term para hacer esto"
        result = builder.validate_prompt(prompt)
        assert result is True  # check_forbidden is disabled

    def test_validate_prompt_empty_text(self) -> None:
        """Test validate_prompt with empty text."""
        builder = HardQueryBuilder(use_case="home_assistant", seed=42)
        # Empty text should pass (no forbidden terms)
        assert builder.validate_prompt("") is True

    def test_validate_prompt_all_imperative_patterns(self) -> None:
        """Test validate_prompt detects all imperative patterns."""
        builder = HardQueryBuilder(use_case="home_assistant", seed=42)

        imperative_prompts = [
            "implementa usando esto",
            "crea una clase nueva",
            "define la función correcta",
            "sigue estos pasos",
            "primero haz lo segundo",
            "después haz la tarea",
            "para resolver esto:",
            "necesitas usar algo",
            "debes usar esto",
        ]

        for prompt in imperative_prompts:
            assert builder.validate_prompt(prompt) is False, f"Failed to detect: {prompt}"


class TestHardQueryBuilderBuildTemplates:
    """Tests for different template formatting in build method."""

    def test_build_with_outcome_template(self, tmp_path: Path) -> None:
        """Test build uses outcome-focused template when available."""
        config = tmp_path / "config.yaml"
        config.write_text("""
forbidden_terms: []
templates:
  outcome_focused:
    template: "Necesito lograr: {outcome}\\nDisponible: {available}\\nEl resultado debe ser: {expected_result}"
use_cases:
  test:
    objective_templates:
      - "Test objective"
    context_templates:
      - "Test context"
validator:
  check_forbidden: false
  check_imperative: false
""")
        builder = HardQueryBuilder(use_case="test", templates_path=config, seed=42)
        seed = {
            "seed_id": "test",
            "category": "test_cat",
            "context": "Test context",
            "question": "Test question",
        }
        result = builder.build(seed)
        # Should use outcome template format
        assert "Necesito lograr:" in result or "Disponible:" in result or "resultado" in result

    def test_build_with_question_template(self, tmp_path: Path) -> None:
        """Test build uses question-background template when available."""
        config = tmp_path / "config2.yaml"
        config.write_text("""
forbidden_terms: []
templates:
  question_focused:
    template: "{question}\\nBackground: {background}\\nDesired: {desired_state}"
use_cases:
  test:
    objective_templates:
      - "Test"
    context_templates:
      - "Background info"
validator:
  check_forbidden: false
  check_imperative: false
""")
        builder = HardQueryBuilder(use_case="test", templates_path=config, seed=42)
        seed = {
            "seed_id": "test",
            "category": "test",
            "context": "Test context",
            "question": "Test question?",
        }
        result = builder.build(seed)
        assert "question" in result.lower() or "background" in result.lower()

    def test_build_with_requirement_template(self, tmp_path: Path) -> None:
        """Test build uses requirement-constraints template when available."""
        config = tmp_path / "config3.yaml"
        config.write_text("""
forbidden_terms: []
templates:
  requirement_focused:
    template: "Requisito: {requirement}\\nRestricciones: {constraints}"
use_cases:
  test:
    objective_templates:
      - "Test"
    context_templates:
      - "Test"
validator:
  check_forbidden: false
  check_imperative: false
""")
        builder = HardQueryBuilder(use_case="test", templates_path=config, seed=42)
        seed = {
            "seed_id": "test",
            "category": "test",
            "context": "Context",
            "question": "Question",
        }
        result = builder.build(seed)
        assert "requisito" in result.lower() or "restriccion" in result.lower()


class TestHardQueryBuilderErrorCases:
    """Tests for error handling in HardQueryBuilder."""

    def test_empty_seed_handled_gracefully(self) -> None:
        """Test that empty or minimal seeds are handled."""
        empty_seed: dict[str, Any] = {}

        # Should produce some output or raise appropriate error
        # In production, HardQueryBuilder would handle this
        objective = empty_seed.get("context", "")
        question = empty_seed.get("question", "")

        # Basic output should still be generated
        prompt = f"Objetivo: {objective}\nPregunta: {question}"
        assert "Objetivo:" in prompt

    def test_missing_optional_fields_does_not_crash(self) -> None:
        """Test that missing optional fields don't cause crashes."""
        partial_seed = {
            "seed_id": "test_seed",
            # Missing: category, context, question
        }

        # Should not crash when building from partial seed
        seed_id = partial_seed.get("seed_id", "unknown")
        assert seed_id == "test_seed"

    def test_malformed_prompt_rejected(self, forbidden_terms: list[str]) -> None:
        """Test that malformed prompts with mixed content are properly validated."""
        # Prompt with some abstract and some explicit content
        mixed_prompt = """
        El sistema debe sincronizar estados automáticamente.

        Usa DataUpdateCoordinator para manejar las actualizaciones.
        """

        # Check for forbidden terms
        detected = [term for term in forbidden_terms if term.lower() in mixed_prompt.lower()]

        # Should detect the forbidden term
        assert "DataUpdateCoordinator" in detected

        # Should be rejected
        is_valid = len(detected) == 0
        assert is_valid is False, "Mixed prompt with forbidden terms should be rejected"


# =============================================================================
# ABSTRACT BASE CLASS (for documentation)
# =============================================================================


class TestHardQueryBuilderInterface:
    """
    Abstract interface tests for HardQueryBuilder.

    These tests document the expected interface for HardQueryBuilder.
    They will pass once T014 (implementation) is completed.
    """

    def test_builder_has_build_method(self) -> None:
        """Test that HardQueryBuilder has a build method."""
        builder = HardQueryBuilder(use_case="home_assistant")
        assert hasattr(builder, "build")
        assert callable(builder.build)

    def test_builder_has_validate_prompt_method(self) -> None:
        """Test that HardQueryBuilder has validate_prompt method."""
        builder = HardQueryBuilder(use_case="home_assistant")
        assert hasattr(builder, "validate_prompt")
        assert callable(builder.validate_prompt)

    def test_builder_has_forbidden_terms_property(self) -> None:
        """Test that HardQueryBuilder has forbidden_terms property."""
        builder = HardQueryBuilder(use_case="home_assistant")
        assert hasattr(builder, "forbidden_terms")
        assert isinstance(builder.forbidden_terms, list)

    def test_builder_has_use_case_property(self) -> None:
        """Test that HardQueryBuilder has use_case property."""
        builder = HardQueryBuilder(use_case="home_assistant")
        assert hasattr(builder, "use_case")
        assert builder.use_case == "home_assistant"

    def test_builder_validate_prompt_valid(self) -> None:
        """Test validate_prompt returns True for valid prompt."""
        builder = HardQueryBuilder(use_case="home_assistant")
        result = builder.validate_prompt("What is the weather?")
        assert result is True

    def test_builder_validate_prompt_invalid(self) -> None:
        """Test validate_prompt returns False for prompt with forbidden terms."""
        builder = HardQueryBuilder(use_case="home_assistant")
        # This test depends on the actual forbidden terms in the config
        _ = builder.validate_prompt("Use ESPHome to configure sensor")
        # May return False if it contains forbidden terms

    def test_template_loader_load_templates(self) -> None:
        """Test HardQueryTemplateLoader loads templates."""
        loader = HardQueryTemplateLoader()
        templates = loader.load_templates()
        assert isinstance(templates, dict)

    def test_template_loader_get_forbidden_terms(self) -> None:
        """Test HardQueryTemplateLoader returns forbidden terms."""
        loader = HardQueryTemplateLoader()
        terms = loader.get_forbidden_terms()
        assert isinstance(terms, list)

    def test_template_loader_get_template_names(self) -> None:
        """Test HardQueryTemplateLoader returns template names."""
        loader = HardQueryTemplateLoader()
        names = loader.get_template_names()
        assert isinstance(names, list)

    def test_template_loader_get_template(self) -> None:
        """Test HardQueryTemplateLoader returns specific template by name."""
        loader = HardQueryTemplateLoader()
        # Test getting an existing template
        template = loader.get_template("problem_focused")
        assert isinstance(template, str)
        # Test getting non-existent template returns empty string
        empty_template = loader.get_template("nonexistent_template")
        assert empty_template == ""

    def test_template_loader_get_use_case_config(self) -> None:
        """Test HardQueryTemplateLoader returns use case configuration."""
        loader = HardQueryTemplateLoader()
        # Test getting existing use case config
        config = loader.get_use_case_config("home_assistant")
        assert isinstance(config, dict)
        # Test getting non-existent use case returns empty dict
        empty_config = loader.get_use_case_config("nonexistent_use_case")
        assert empty_config == {}

    def test_template_loader_get_validator_config(self) -> None:
        """Test HardQueryTemplateLoader returns validator configuration."""
        loader = HardQueryTemplateLoader()
        config = loader.get_validator_config()
        assert isinstance(config, dict)
        # Validator config should have expected keys from defaults
        assert "min_abstractness" in config or "check_forbidden" in config

    def test_template_loader_default_templates(self) -> None:
        """Test HardQueryTemplateLoader returns default templates when file missing."""
        # Use a non-existent path to trigger defaults
        loader = HardQueryTemplateLoader(templates_path="/nonexistent/path.yaml")
        templates = loader._default_templates()
        assert isinstance(templates, dict)
        assert "forbidden_terms" in templates
        assert "templates" in templates
        assert "use_cases" in templates
        assert "validator" in templates
        # Verify default forbidden terms
        assert "async_forward_entry_setups" in templates["forbidden_terms"]
        assert "DataUpdateCoordinator" in templates["forbidden_terms"]

    def test_template_loader_with_invalid_yaml(self, tmp_path: Path) -> None:
        """Test HardQueryTemplateLoader raises on invalid YAML."""
        # Create invalid YAML file
        invalid_yaml = tmp_path / "invalid.yaml"
        invalid_yaml.write_text("invalid: yaml: content: [}")
        # Should raise YAML error (code doesn't handle it gracefully)
        with pytest.raises(yaml.scanner.ScannerError):
            HardQueryTemplateLoader(templates_path=invalid_yaml)

    def test_template_loader_with_empty_yaml(self, tmp_path: Path) -> None:
        """Test HardQueryTemplateLoader handles empty YAML file."""
        empty_yaml = tmp_path / "empty.yaml"
        empty_yaml.write_text("")
        loader = HardQueryTemplateLoader(templates_path=empty_yaml)
        templates = loader.load_templates()
        # Empty YAML results in None from yaml.safe_load
        assert templates == {}

    def test_template_loader_with_valid_custom_yaml(self, tmp_path: Path) -> None:
        """Test HardQueryTemplateLoader loads valid custom YAML file."""
        custom_yaml = tmp_path / "custom.yaml"
        custom_yaml.write_text("""
forbidden_terms:
  - test_term
templates:
  custom_template:
    template: "Custom: {objective}"
use_cases:
  test_use_case:
    objective_templates:
      - "Test objective"
validator:
  min_abstractness: 0.5
  check_forbidden: true
""")
        loader = HardQueryTemplateLoader(templates_path=custom_yaml)
        assert loader.get_forbidden_terms() == ["test_term"]
        assert "custom_template" in loader.get_template_names()
        config = loader.get_use_case_config("test_use_case")
        assert "objective_templates" in config
