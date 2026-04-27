#!/usr/bin/env python3
# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# SPDX-License-Identifier: Apache-2.0

"""
Regression tests for _sanitize_generated_reasoning() corruption issue.

Tests verify that the sanitization function correctly removes code blocks
while PRESERVING technical identifiers that were previously deleted.

These tests MUST FAIL with the current regex pattern and PASS after the fix.
"""

from src.curation.backtracking_helpers import _sanitize_generated_reasoning


class TestSanitizePreservesIdentifiers:
    """Verify that technical identifiers are preserved, not deleted."""

    def test_preserves_home_assistant_identifiers(self) -> None:
        """Technical identifiers must NOT be removed."""
        text = (
            "El problema está en las constantes globales tipo string para "
            "`device_class` o `unit_of_measurement`. "
            "Debes usar `SensorDeviceClass` y `UnitOfTemperature` en su lugar."
        )
        result = _sanitize_generated_reasoning(text)

        # All identifiers MUST be preserved
        assert "`device_class`" in result, "device_class identifier was deleted!"
        assert "`unit_of_measurement`" in result, (
            "unit_of_measurement identifier was deleted!"
        )
        assert "`SensorDeviceClass`" in result, (
            "SensorDeviceClass identifier was deleted!"
        )
        assert "`UnitOfTemperature`" in result, (
            "UnitOfTemperature identifier was deleted!"
        )

    def test_preserves_async_function_names(self) -> None:
        """Async function names must be preserved."""
        text = (
            "Debes usar `async_forward_entry_setups` en lugar de "
            "`async_forward_entry_setup` (deprecated). "
            "Ambas funciones son críticas para la integración."
        )
        result = _sanitize_generated_reasoning(text)

        assert "`async_forward_entry_setups`" in result, (
            "async_forward_entry_setups was deleted!"
        )
        assert "`async_forward_entry_setup`" in result, (
            "async_forward_entry_setup was deleted!"
        )

    def test_preserves_config_entry_exceptions(self) -> None:
        """Exception class names must be preserved."""
        text = (
            "Cuando falla la autenticación, lanza `ConfigEntryAuthFailed`. "
            "Para errores de conexión, usa `ConfigEntryNotReady` o `UpdateFailed`."
        )
        result = _sanitize_generated_reasoning(text)

        assert "`ConfigEntryAuthFailed`" in result, "ConfigEntryAuthFailed was deleted!"
        assert "`ConfigEntryNotReady`" in result, "ConfigEntryNotReady was deleted!"
        assert "`UpdateFailed`" in result, "UpdateFailed was deleted!"

    def test_preserves_data_attributes(self) -> None:
        """Data attribute references must be preserved."""
        # Note: hass.data[DOMAIN] contains executable syntax [DOMAIN], so it's expected
        # to be partially removed. But the identifier hass.data itself should be preserved
        # in other contexts without the executable bracket notation.
        text = (
            "Usa `entry.runtime_data` en lugar de construir manualmente con `hass.data`. "
            "El atributo `runtime_data` es la forma moderna de almacenar datos."
        )
        result = _sanitize_generated_reasoning(text)

        assert "`hass.data`" in result, "hass.data identifier was deleted!"
        assert "`entry.runtime_data`" in result, "entry.runtime_data was deleted!"
        assert "`runtime_data`" in result, "runtime_data was deleted!"

    def test_preserves_entity_classes(self) -> None:
        """Entity class names must be preserved."""
        text = (
            "Tu clase debe heredar de `CoordinatorEntity` en lugar de `Entity`. "
            "También puedes usar `SensorEntity` para sensores específicos."
        )
        result = _sanitize_generated_reasoning(text)

        assert "`CoordinatorEntity`" in result, "CoordinatorEntity was deleted!"
        assert "`Entity`" in result, "Entity was deleted!"
        assert "`SensorEntity`" in result, "SensorEntity was deleted!"

    def test_preserves_decorators(self) -> None:
        """Python decorators must be preserved."""
        text = (
            "Usa `@callback` para marcar métodos callback en lugar de "
            "`@property`. El decorador `@callback` es más eficiente."
        )
        result = _sanitize_generated_reasoning(text)

        assert "`@callback`" in result, "@callback decorator was deleted!"
        assert "`@property`" in result, "@property decorator was deleted!"

    def test_preserves_multiword_identifiers(self) -> None:
        """Multi-word technical identifiers must be preserved."""
        text = (
            "Reemplaza `async_add_executor_job` con la nueva API. "
            "También migra `async_update_immediately` a `async_request_refresh`."
        )
        result = _sanitize_generated_reasoning(text)

        assert "`async_add_executor_job`" in result, (
            "async_add_executor_job was deleted!"
        )
        assert "`async_update_immediately`" in result, (
            "async_update_immediately was deleted!"
        )
        assert "`async_request_refresh`" in result, "async_request_refresh was deleted!"


class TestSanitizeRemovesCodeBlocks:
    """Verify that actual code blocks are still removed."""

    def test_removes_fenced_code_blocks(self) -> None:
        """Triple-backtick fenced code blocks MUST be removed."""
        text = (
            "Aquí está el código incorrecto:\n"
            "```python\nasync def setup(hass):\n    hass.data[DOMAIN] = {}\n```\n"
            "Debesremplazarlo con entry.runtime_data."
        )
        result = _sanitize_generated_reasoning(text)

        # Code block should be gone
        assert "```python" not in result, "Fenced code block not removed!"
        assert "hass.data[DOMAIN]" not in result, "Code inside fences not removed!"
        # But explanation text should remain
        assert "Debes" in result, "Explanation text was removed!"
        assert "entry.runtime_data" in result, (
            "Technical identifier in explanation was deleted!"
        )

    def test_removes_tool_call_blocks(self) -> None:
        """Tool-call XML blocks MUST be removed."""
        text = (
            "El LLM generó esto incorrectamente:\n"
            '<tool_call>{"name": "write_to_file", "path": "test.py"}</tool_call>\n'
            "No deberías incluir tool_calls en el razonamiento."
        )
        result = _sanitize_generated_reasoning(text)

        assert "<tool_call>" not in result, "Tool-call block not removed!"
        assert "write_to_file" not in result, "Tool-call content not removed!"
        # Explanation should remain
        assert "razonamiento" in result, "Explanation was removed!"

    def test_removes_remaining_tags(self) -> None:
        """Stray XML/HTML tags should be removed."""
        text = (
            "El código tiene un problema <tag_error>aquí</tag_error> "
            "pero el identificador `MyClass` es válido."
        )
        result = _sanitize_generated_reasoning(text)

        assert "<tag_error>" not in result, "XML tag not removed!"
        assert "</tag_error>" not in result, "XML tag not removed!"
        # But identifier should remain
        assert "`MyClass`" in result, "Technical identifier was deleted!"

    def test_collapses_multiple_newlines(self) -> None:
        """Multiple blank lines should be collapsed."""
        text = "Primera línea.\n\n\n\nSegunda línea con `identifier`."
        result = _sanitize_generated_reasoning(text)

        assert "\n\n\n\n" not in result, "Multiple newlines not collapsed!"
        assert "`identifier`" in result, "Identifier was deleted!"


class TestSanitizeEdgeCases:
    """Test edge cases and complex scenarios."""

    def test_mixed_content_preservation(self) -> None:
        """All safe content must be preserved in mixed scenarios."""
        text = (
            "Usa `async_forward_entry_setups` como se muestra:\n"
            "```python\nawait hass.config_entries.async_forward_entry_setups(entry, platforms)\n```\n"
            "En lugar de su versión deprecated `async_forward_entry_setup`."
        )
        result = _sanitize_generated_reasoning(text)

        # Code block removed
        assert "await hass" not in result, "Python code not removed!"
        # But identifiers preserved
        assert "`async_forward_entry_setups`" in result, (
            "Main function identifier deleted!"
        )
        assert "`async_forward_entry_setup`" in result, (
            "Deprecated function name deleted!"
        )

    def test_preserves_technical_content_outside_fences(self) -> None:
        """Inline code outside fences must be preserved."""
        text = (
            "Reemplaza `hass.data` con esto:\n"
            "```\nold_code = hass.data[DOMAIN]\n```\n"
            "Usa `entry.runtime_data` en su lugar."
        )
        result = _sanitize_generated_reasoning(text)

        # In-text identifiers preserved
        assert "`hass.data`" in result, (
            "Inline identifier from description was deleted!"
        )
        assert "`entry.runtime_data`" in result, "Alternative identifier was deleted!"
        # Fenced code removed
        assert "old_code" not in result, "Code inside fences not removed!"

    def test_empty_input(self) -> None:
        """Empty input should return empty string."""
        result = _sanitize_generated_reasoning("")
        assert result == "", "Empty input handling broken!"

    def test_preserves_solution_identifiers(self) -> None:
        """Identifiers in the solution (after </think>) must be preserved."""
        text = (
            "El archivo debe ser:\n"
            "```python\nclass MyEntity(CoordinatorEntity):\n    pass\n```\n"
            "que hereda de `CoordinatorEntity` correctamente."
        )
        result = _sanitize_generated_reasoning(text)

        # Code fences removed
        assert "class MyEntity" not in result, "Code inside fences not removed!"
        # But identifier in explanation preserved
        assert "`CoordinatorEntity`" in result, "Identifier in explanation was deleted!"


class TestOriginalCorruptionPattern:
    """Test the exact corruption patterns from the forensic analysis."""

    def test_spanish_device_class_corruption(self) -> None:
        """Reproduces the exact corruption from forensic report."""
        original = (
            "el problema está en las constantes globales tipo string para "
            "`device_class` o `unit_of_measurement`"
        )

        result = _sanitize_generated_reasoning(original)

        # This was the corruption: "para  o " (words deleted, spaces remain)
        assert "para  o" not in result, "Corruption pattern detected (double space)!"
        assert "`device_class`" in result, "device_class was deleted (CORRUPTION)!"
        assert "`unit_of_measurement`" in result, (
            "unit_of_measurement was deleted (CORRUPTION)!"
        )

    def test_ha_identifier_preservation(self) -> None:
        """All Home Assistant identifiers from forensics must be preserved."""
        identifiers = [
            "`async_forward_entry_setups`",
            "`entry.runtime_data`",
            "`runtime_data`",
            "`UpdateFailed`",
            "`ConfigEntryNotReady`",
            "`ConfigEntryAuthFailed`",
            "`hass.data`",
            "`SensorDeviceClass`",
            "`async_forward_entry_setup`",
            "`CoordinatorEntity`",
            "`@callback`",
            "`device_class`",
        ]

        text = "Identifiers: " + ", ".join(identifiers)
        result = _sanitize_generated_reasoning(text)

        for ident in identifiers:
            assert ident in result, (
                f"Critical identifier {ident} was DELETED (CORRUPTION)!"
            )
