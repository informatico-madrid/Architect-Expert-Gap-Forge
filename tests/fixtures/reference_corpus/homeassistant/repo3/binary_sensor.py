# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0
"""
Home Assistant binary sensor component - fixture for recall measurement.
"""


from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType



async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the binary sensor platform."""
    sensors = []
    for name in config.get("sensors", []):
        sensors.append(MyBinarySensor(name))
    async_add_entities(sensors)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensor using config entry."""
    name = config_entry.data[CONF_NAME]
    sensor = MyBinarySensor(name)
    async_add_entities([sensor])


class MyBinarySensor(BinarySensorEntity):
    """Representation of a binary sensor."""

    def __init__(self, name: str) -> None:
        """Initialize the binary sensor."""
        self._name = name
        self._state = False
        self._attr_device_class = BinarySensorDeviceClass.DOOR

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self._name

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        return self._state

    def update(self) -> None:
        """Fetch new state data for the sensor."""
        # Simulated update
        self._state = True
