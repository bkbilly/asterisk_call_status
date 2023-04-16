"""Platform for sensor integration."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging

from homeassistant import config_entries
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    TIME_SECONDS,
    SIGNAL_STRENGTH_DECIBELS,
    LENGTH_METERS,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=1)


@dataclass
class AsteriskCallStatusSensorEntityDescription(SensorEntityDescription):
    """Provide a description of a Asterisk Call Status sensor."""

    # For backwards compat, allow description to override unique ID key to use
    unique_id: str | None = None


SENSORS = (
    AsteriskCallStatusSensorEntityDescription(
        key="status",
        name="Status",
        unique_id="asterisk_call_status_status",
        icon="mdi:phone-outline",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        AsteriskCallStatusSensor(data.coordinator, data.device, description)
        for description in SENSORS
    )


class AsteriskCallStatusSensor(CoordinatorEntity, SensorEntity):
    """Implementation of the Asterisk Call Status sensor."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, device, description):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self.device = device

        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self.device.address)},
            manufacturer="Asterisk",
            name="Asterisk Call Status",
        )

        self._attr_unique_id = (
            f"{self.device.address}_{description.unique_id}"
        )

    @property
    def native_value(self) -> float | None:
        """Return sensor state."""
        value = self.device.get_results().get(self.entity_description.key)
        return value

    @property
    def extra_state_attributes(self):
        """Return entity specific state attributes."""
        return self.device.get_results()
