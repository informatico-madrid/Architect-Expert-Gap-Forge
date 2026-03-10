# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0
"""
Home Assistant switch component - fixture for recall measurement.
"""

import asyncio
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import aiohttp
from .const import DEFAULT_TIMEOUT


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform."""
    host = config_entry.data[CONF_HOST]
    switch = MySwitch(host)
    async_add_entities([switch])


class MySwitch(SwitchEntity):
    """Representation of a network switch."""

    def __init__(self, host: str) -> None:
        """Initialize the switch."""
        self._host = host
        self._state = False
        self._attr_is_on = False

    @property
    def name(self) -> str:
        """Return the display name of this switch."""
        return f"Switch {self._host}"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self._async_set_state(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self._async_set_state(False)

    async def _async_set_state(self, state: bool) -> None:
        """Set the switch state via API."""
        url = f"http://{self._host}/switch"
        payload = {"state": "on" if state else "off"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, json=payload, timeout=DEFAULT_TIMEOUT
                ) as resp:
                    if resp.status == 200:
                        self._state = state
                        self._attr_is_on = state
        except asyncio.TimeoutError:
            pass
