# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0
"""
Home Assistant light component - sample fixture for recall measurement.
"""

import logging
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP,
    PLATFORM_SCHEMA,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import requests

from .const import DEFAULT_PORT, DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        CONF_HOST: str,
        CONF_PORT: int,
        CONF_NAME: str,
    }
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the light platform."""
    host = config_entry.data[CONF_HOST]
    port = config_entry.data.get(CONF_PORT, DEFAULT_PORT)
    name = config_entry.data[CONF_NAME]

    lights = [MyLight(name, host, port)]
    async_add_entities(lights)


class MyLight(LightEntity):
    """Representation of a MyLight smart bulb."""

    def __init__(self, name: str, host: str, port: int) -> None:
        """Initialize the light."""
        self._name = name
        self._host = host
        self._port = port
        self._brightness: int | None = None
        self._color_temp: int | None = None
        self._state = False

    @property
    def name(self) -> str:
        """Return the display name of the light."""
        return self._name

    @property
    def brightness(self) -> int | None:
        """Return the brightness of this light between 0 and 255."""
        return self._brightness

    @property
    def color_temp(self) -> int | None:
        """Return the color temperature in mireds."""
        return self._color_temp

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        return self._state

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        color_temp = kwargs.get(ATTR_COLOR_TEMP)

        # API call to turn on
        url = f"http://{self._host}:{self._port}/api/light/on"
        payload = {}
        if brightness is not None:
            payload["brightness"] = brightness
        if color_temp is not None:
            payload["color_temp"] = color_temp

        try:
            requests.post(url, json=payload, timeout=10)
            self._state = True
            self._brightness = brightness
            self._color_temp = color_temp
        except requests.RequestException as err:
            _LOGGER.error("Failed to turn on light: %s", err)

    async def async_turn_off(self) -> None:
        """Turn the light off."""
        url = f"http://{self._host}:{self._port}/api/light/off"
        try:
            requests.post(url, timeout=10)
            self._state = False
        except requests.RequestException as err:
            _LOGGER.error("Failed to turn off light: %s", err)

    async def async_update(self) -> None:
        """Fetch new state data for this light."""
        url = f"http://{self._host}:{self._port}/api/light/status"
        try:
            response = requests.get(url, timeout=10)
            data = response.json()
            self._state = data.get("on", False)
            self._brightness = data.get("brightness")
        except (requests.RequestException, ValueError) as err:
            _LOGGER.error("Error fetching light state: %s", err)
