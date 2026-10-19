"""Shared entity plumbing for Mosquito Diffuser entities."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN
from .coordinator import MosquitoDiffuserCoordinator


class MosquitoDiffuserEntity:
    """Mixin: unique id, device info and push-based coordinator listeners."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, coordinator: MosquitoDiffuserCoordinator, key: str) -> None:
        """Initialize device/unique-id attributes from the coordinator."""
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            name=coordinator.entry.title,
            manufacturer="Mosquito Diffuser",
            model="Cartridge usage monitor",
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe this entity to coordinator updates."""
        self.coordinator.async_add_listener(self.async_write_ha_state)
        self.async_on_remove(
            lambda: self.coordinator.async_remove_listener(self.async_write_ha_state)
        )
