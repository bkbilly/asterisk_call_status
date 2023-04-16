"""The Asterisk Call Status integration models."""

from __future__ import annotations
from dataclasses import dataclass
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator


@dataclass
class AsteriskCallStatusData:
    """Data for the Parrot Olympe integration."""

    title: str
    device: None
    coordinator: DataUpdateCoordinator
