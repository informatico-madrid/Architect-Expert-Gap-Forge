# Architect-Expert-Gap-Forge (AEGF)
# Copyright (c) 2026 Joao Maria Arranz Aparicio <joao@informatico-madrid.com>
# Source: https://github.com/informatico-madrid/Architect-Expert-Gap-Forge
#
# Licensed under the Apache License, Version 2.0 (the "License");
# SPDX-License-Identifier: Apache-2.0
"""
Home Assistant sensor component - sample fixture for recall measurement.
"""

from datetime import timedelta

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_NAME,
    ENERGY_KILO_WATT_HOUR,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN, MANUFACTURER

import aiohttp
import async_timeout

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    sensors = [
        EnergySensor(coordinator, config_entry),
        PowerSensor(coordinator, config_entry),
    ]
    async_add_entities(sensors)


class EnergySensor(CoordinatorEntity, SensorEntity):
    """Representation of an energy sensor."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = f"{config_entry.data[CONF_NAME]} Energy"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_unit_of_measure = ENERGY_KILO_WATT_HOUR
        self._attr_unique_id = f"{config_entry.unique_id}_energy"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.config_entry.unique_id)},
            manufacturer=MANUFACTURER,
            name=self.coordinator.config_entry.data[CONF_NAME],
        )

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        return self.coordinator.data.get("energy")


class PowerSensor(CoordinatorEntity, SensorEntity):
    """Representation of a power sensor."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = f"{config_entry.data[CONF_NAME]} Power"
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_unit_of_measure = "kW"
        self._attr_unique_id = f"{config_entry.unique_id}_power"

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        return self.coordinator.data.get("power")


class MyDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        api_key: str,
    ) -> None:
        """Initialize the coordinator."""
        self.host = host
        self.api_key = api_key
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=5),
        )

    async def _async_update_data(self) -> dict:
        """Fetch data from API."""
        url = f"http://{self.host}/api/status"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            async with async_timeout.timeout(10):
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers) as response:
                        return await response.json()
        except (aiohttp.ClientError, async_timeout.AsyncTimeoutError) as err:
            raise UpdateError(f"Failed to fetch data: {err}") from err


class UpdateError(Exception):
    """Raised when there's an update error."""
