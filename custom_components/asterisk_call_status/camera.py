"""Demo camera platform that has a fake camera."""
from __future__ import annotations

from pathlib import Path

from homeassistant.components.camera import Camera, CameraEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.device_registry import DeviceEntryType

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Demo config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([DemoCamera(data.coordinator, data.device)])


class DemoCamera(Camera):
    """The representation of a Demo camera."""

    def __init__(self, coordinator, device) -> None:
        """Initialize demo camera component."""
        super().__init__()
        self.device = device
        self._attr_unique_id = (
            f"{self.device.address}_asterisk_call_status"
        )
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self.device.address)},
            manufacturer="Asterisk",
            name="Asterisk Call Status",
        )
        self._attr_name = "Asterisk Call Status"

    def camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        return self.device.image
