"""Low-cartridge binary sensor for the Mosquito Diffuser integration."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory

from .const import DOMAIN
from .coordinator import MosquitoDiffuserCoordinator
from .entity import MosquitoDiffuserEntity


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    """Set up the low-cartridge warning."""
    coordinator: MosquitoDiffuserCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([LowCartridgeBinarySensor(coordinator)])


class LowCartridgeBinarySensor(MosquitoDiffuserEntity, BinarySensorEntity):
    """On when the remaining cartridge percentage drops to the threshold."""

    _attr_name = "Low"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: MosquitoDiffuserCoordinator) -> None:
        super().__init__(coordinator, "low")

    @property
    def is_on(self) -> bool:
        return self.coordinator.remaining_pct <= self.coordinator.low_threshold

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "remaining_pct": round(self.coordinator.remaining_pct, 0),
            "threshold_pct": self.coordinator.low_threshold,
            "outlet_entity": self.coordinator.outlet_entity,
        }
