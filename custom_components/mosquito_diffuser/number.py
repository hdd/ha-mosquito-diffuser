"""Cartridge level number entity for the Mosquito Diffuser integration."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode

from .const import DOMAIN
from .coordinator import MosquitoDiffuserCoordinator
from .entity import MosquitoDiffuserEntity


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    """Set up the cartridge level calibration number."""
    coordinator: MosquitoDiffuserCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([CartridgeLevelNumber(coordinator)])


class CartridgeLevelNumber(MosquitoDiffuserEntity, NumberEntity):
    """Current cartridge level in %; setting it calibrates an existing refill."""

    _attr_name = "Cartridge level"
    _attr_icon = "mdi:battery"
    _attr_native_unit_of_measurement = "%"
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: MosquitoDiffuserCoordinator) -> None:
        super().__init__(coordinator, "level")

    @property
    def native_value(self) -> float:
        return round(self.coordinator.remaining_pct, 0)

    async def async_set_native_value(self, value: float) -> None:
        """Calibrate: derive used hours from the level you set."""
        await self.coordinator.async_set_level(value)
