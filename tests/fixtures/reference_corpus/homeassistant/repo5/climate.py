# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0
"""
Home Assistant climate component - fixture for recall measurement.
"""

from enum import Enum
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_NAME,
    TEMP_CELSIUS,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback


SUPPORT_FLAGS = (
    ClimateEntityFeature.TARGET_TEMPERATURE
    | ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
    | ClimateEntityFeature.HVAC_MODE
)

HVAC_MODES = [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL, HVACMode.AUTO]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up climate platform."""
    climate = MyClimate(config_entry)
    async_add_entities([climate])


class MyPresetMode(Enum):
    """Preset modes for the climate device."""

    NONE = "none"
    ECO = "eco"
    AWAY = "away"
    BOOST = "boost"


class MyClimate(ClimateEntity):
    """Representation of a climate device."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize the climate device."""
        self._attr_name = config_entry.data[CONF_NAME]
        self._attr_temperature_unit = TEMP_CELSIUS
        self._attr_hvac_modes = HVAC_MODES
        self._attr_supported_features = SUPPORT_FLAGS
        self._attr_preset_modes = [mode.value for mode in MyPresetMode]
        self._current_temperature: float | None = None
        self._target_temperature: float | None = None
        self._hvac_mode: HVACMode = HVACMode.OFF

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self._current_temperature

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        return self._target_temperature

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC mode."""
        return self._hvac_mode

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is not None:
            self._target_temperature = temperature
            await self._send_command("set_temperature", temperature)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new HVAC mode."""
        self._hvac_mode = hvm_mode
        await self._send_command("set_hvac_mode", hvac_mode.value)

    async def _send_command(self, command: str, value: Any) -> None:
        """Send command to the device."""
        # Simulated API call
        pass
